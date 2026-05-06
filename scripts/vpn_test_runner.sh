#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  vpn_test_runner.sh --vps-ip <IP> [options]

Required:
  --vps-ip <IP>              VPN server public IP

Optional:
  --ssh-user <USER>          For handover notes (default: root)
  --reality-sni <DOMAIN>     SNI to validate Reality behavior
  --direct-ip <IP>           Expected local/direct IP for RU resources
  --report <PATH>            Markdown report path
  --run-iperf                Run iperf3 tests (expects iperf3 server on VPS)
  --iperf-port <PORT>        iperf3 port (default: 5201)
  --iperf-seconds <SEC>      iperf3 duration per test (default: 30)
  --skip-nmap                Skip nmap checks
  -h, --help                 Show help

Example:
  ./scripts/vpn_test_runner.sh \
    --vps-ip 1.2.3.4 \
    --reality-sni www.cloudflare.com \
    --direct-ip 203.0.113.10 \
    --run-iperf
EOF
}

VPS_IP=""
SSH_USER="root"
REALITY_SNI=""
DIRECT_IP=""
RUN_IPERF=0
IPERF_PORT="5201"
IPERF_SECONDS="30"
SKIP_NMAP=0
REPORT="${PWD}/vpn-test-report-$(date +%Y%m%d-%H%M%S).md"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --vps-ip) VPS_IP="${2:-}"; shift 2 ;;
    --ssh-user) SSH_USER="${2:-}"; shift 2 ;;
    --reality-sni) REALITY_SNI="${2:-}"; shift 2 ;;
    --direct-ip) DIRECT_IP="${2:-}"; shift 2 ;;
    --report) REPORT="${2:-}"; shift 2 ;;
    --run-iperf) RUN_IPERF=1; shift ;;
    --iperf-port) IPERF_PORT="${2:-}"; shift 2 ;;
    --iperf-seconds) IPERF_SECONDS="${2:-}"; shift 2 ;;
    --skip-nmap) SKIP_NMAP=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$VPS_IP" ]]; then
  echo "Error: --vps-ip is required" >&2
  usage
  exit 1
fi

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

section() {
  echo "" >> "$REPORT"
  echo "## $1" >> "$REPORT"
  echo "" >> "$REPORT"
}

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  echo "- PASS: $1" >> "$REPORT"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  echo "- FAIL: $1" >> "$REPORT"
}

warn() {
  WARN_COUNT=$((WARN_COUNT + 1))
  echo "- WARN: $1" >> "$REPORT"
}

code_block() {
  local lang="$1"
  shift
  echo "" >> "$REPORT"
  echo '```'"$lang" >> "$REPORT"
  printf "%s\n" "$*" >> "$REPORT"
  echo '```' >> "$REPORT"
}

capture_cmd() {
  local cmd="$1"
  local out rc
  set +e
  out="$(bash -lc "$cmd" 2>&1)"
  rc=$?
  set -e
  printf "%s" "$out"
  return $rc
}

first_valid_ipv4() {
  grep -Eo '([0-9]{1,3}\.){3}[0-9]{1,3}' \
    | awk -F'.' '$1<=255 && $2<=255 && $3<=255 && $4<=255 {print; exit}'
}

extract_yandex_ipv4() {
  capture_cmd 'curl -4fsSL https://yandex.ru/internet' \
    | tr '<' '\n' \
    | awk -F'>' '/IPv4-адрес/{flag=1} flag && /([0-9]{1,3}\.){3}[0-9]{1,3}/{print $NF; exit}' \
    | first_valid_ipv4
}

ping_jitter_test() {
  local label="$1"
  local target="$2"
  local file="$3"
  local count="$4"
  local interval="$5"
  local cmd

  cmd="ping -c ${count} -i ${interval} ${target}"
  capture_cmd "$cmd" > "$file" || true
  if grep -q 'time=' "$file"; then
    local avg jitter loss
    avg="$(awk -F'time=' '/time=/{split($2,a," ");s+=a[1];n++} END{if(n) printf "%.2f"; else print "NA"}' "$file")"
    jitter="$(awk -F'time=' '/time=/{split($2,a," ");t=a[1];if(p!=""){d=t-p; if(d<0)d=-d; s+=d; n++} p=t} END{if(n) printf "%.2f"; else print "NA"}' "$file")"
    loss="$(grep -Eo '[0-9.]+% packet loss' "$file" | tail -n 1 || true)"
    pass "${label}: ping completed (avg=${avg}ms, jitter=${jitter}ms, loss=${loss:-unknown})"
    code_block text "$(tail -n 8 "$file")"
  else
    warn "${label}: ICMP likely blocked on this network; jitter test by ping is inconclusive"
    code_block text "$(tail -n 40 "$file")"
  fi
}

mkdir -p "$(dirname "$REPORT")"
cat > "$REPORT" <<EOF
# VPN Technical Test Report

- Timestamp: $(date '+%Y-%m-%d %H:%M:%S %Z')
- Host OS: $(uname -a)
- VPS IP: ${VPS_IP}
- SSH User (handover notes): ${SSH_USER}
- Reality SNI: ${REALITY_SNI:-not provided}
- Expected Direct IP: ${DIRECT_IP:-not provided}

EOF

section "0) Prerequisites"
for c in curl awk grep sed ping; do
  if command -v "$c" >/dev/null 2>&1; then
    pass "binary available: $c"
  else
    fail "binary missing: $c"
  fi
done

for c in dig nmap openssl iperf3 tcpdump; do
  if command -v "$c" >/dev/null 2>&1; then
    pass "optional binary available: $c"
  else
    warn "optional binary missing: $c"
  fi
done

section "1) Split Tunneling Checks"
LOCAL_IP="$(capture_cmd 'curl -4fsS https://api.ipify.org || true' | first_valid_ipv4 || true)"
GLOBAL_IP="$(capture_cmd 'curl -4fsS https://ifconfig.me/ip || true' | first_valid_ipv4 || true)"
YANDEX_IP="$(extract_yandex_ipv4 || true)"

echo "- Local public IP (api.ipify): \`${LOCAL_IP:-N/A}\`" >> "$REPORT"
echo "- Global echo IP (ifconfig.me): \`${GLOBAL_IP:-N/A}\`" >> "$REPORT"
echo "- Yandex seen IP (parsed): \`${YANDEX_IP:-N/A}\`" >> "$REPORT"

if [[ -n "$GLOBAL_IP" && -n "$YANDEX_IP" ]]; then
  if [[ "$GLOBAL_IP" != "$YANDEX_IP" ]]; then
    pass "Global and Yandex IP differ (split behavior is likely active)"
  else
    fail "Global and Yandex IP are identical (split behavior is not visible)"
  fi
else
  warn "Could not parse one or both IPs from global/Yandex checks"
fi

if [[ -n "$DIRECT_IP" && -n "$YANDEX_IP" ]]; then
  if [[ "$YANDEX_IP" == "$DIRECT_IP" ]]; then
    pass "Yandex matches expected direct IP"
  else
    fail "Yandex does not match expected direct IP (${DIRECT_IP})"
  fi
fi

if [[ -n "$DIRECT_IP" && -n "$GLOBAL_IP" ]]; then
  if [[ "$GLOBAL_IP" != "$DIRECT_IP" ]]; then
    pass "Global echo differs from expected direct IP (traffic likely via VPN)"
  else
    fail "Global echo equals expected direct IP (VPN routing likely broken)"
  fi
fi

section "1.1) DNS Resolution / Loop Risk"
if command -v dig >/dev/null 2>&1; then
  D_YA_DEF="$(capture_cmd 'dig +short yandex.ru | head -n 1' || true)"
  D_GO_DEF="$(capture_cmd 'dig +short google.com | head -n 1' || true)"
  D_YA_YA="$(capture_cmd 'dig @77.88.8.8 +short yandex.ru | head -n 1' || true)"
  D_GO_CF="$(capture_cmd 'dig @1.1.1.1 +short google.com | head -n 1' || true)"

  echo "- dig default yandex.ru: \`${D_YA_DEF:-N/A}\`" >> "$REPORT"
  echo "- dig default google.com: \`${D_GO_DEF:-N/A}\`" >> "$REPORT"
  echo "- dig @77.88.8.8 yandex.ru: \`${D_YA_YA:-N/A}\`" >> "$REPORT"
  echo "- dig @1.1.1.1 google.com: \`${D_GO_CF:-N/A}\`" >> "$REPORT"

  if [[ -n "$D_YA_DEF" && -n "$D_GO_DEF" ]]; then
    pass "Default DNS resolves both RU and global domains"
  else
    fail "Default DNS resolution failed for RU or global domain"
  fi
else
  warn "dig not found, DNS checks skipped"
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  RESOLVER_INFO="$(capture_cmd "scutil --dns | sed -n '1,80p'" || true)"
else
  RESOLVER_INFO="$(capture_cmd "resolvectl status 2>/dev/null | sed -n '1,80p' || cat /etc/resolv.conf" || true)"
fi
code_block text "$RESOLVER_INFO"
warn "DNS loop is best validated live with: sudo tcpdump -ni any '(udp port 53 or tcp port 53 or tcp port 853)'"

section "2) Stability on Wi-Fi / LTE Handover"
echo "- Manual handover checklist:" >> "$REPORT"
echo "  1) Open: \`ssh -o ServerAliveInterval=10 -o ServerAliveCountMax=6 ${SSH_USER}@${VPS_IP}\`" >> "$REPORT"
echo "  2) Start tmux on server and long transfer." >> "$REPORT"
echo "  3) Switch Wi-Fi -> LTE (and back), validate session continuity in tmux." >> "$REPORT"
echo "  4) Mark reconnect time and packet loss spikes." >> "$REPORT"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

PING_IDLE="$TMP_DIR/ping_idle.log"
PING_LOAD="$TMP_DIR/ping_load.log"

ping_jitter_test "Idle latency/jitter" "${VPS_IP}" "$PING_IDLE" "30" "0.2"

LOAD_CMD='curl -L --max-time 90 https://speed.cloudflare.com/__down?bytes=200000000 -o /dev/null'
if capture_cmd "$LOAD_CMD" > "$TMP_DIR/load.log" &
then
  LOAD_PID=$!
  sleep 2
  ping_jitter_test "Under-load latency/jitter" "${VPS_IP}" "$PING_LOAD" "30" "0.2"
  wait "$LOAD_PID" || true
else
  warn "Could not start load generation command"
fi

section "3) DPI / Active Probing Visibility"
if [[ "$SKIP_NMAP" -eq 0 ]]; then
  if command -v nmap >/dev/null 2>&1; then
    NMAP_SV="$(capture_cmd "nmap -Pn -sV --version-all -p 443 ${VPS_IP}" || true)"
    code_block text "$NMAP_SV"
    NMAP_SSL="$(capture_cmd "nmap -Pn --script ssl-cert,ssl-enum-ciphers -p 443 ${VPS_IP}" || true)"
    code_block text "$NMAP_SSL"
    pass "nmap scans executed"
  else
    warn "nmap not installed, skipping active probing checks"
  fi
else
  warn "nmap checks were explicitly skipped (--skip-nmap)"
fi

if command -v openssl >/dev/null 2>&1; then
  if [[ -n "$REALITY_SNI" ]]; then
    SSL_OK="$(capture_cmd "echo | openssl s_client -connect ${VPS_IP}:443 -servername ${REALITY_SNI} -tls1_3 2>&1 | sed -n '1,30p'" || true)"
    SSL_BAD="$(capture_cmd "echo | openssl s_client -connect ${VPS_IP}:443 -servername bad.example.com -tls1_3 2>&1 | sed -n '1,30p'" || true)"
    code_block text "$SSL_OK"
    code_block text "$SSL_BAD"
    pass "openssl SNI comparison completed"
  else
    warn "Reality SNI not provided; openssl SNI comparison skipped"
  fi
else
  warn "openssl not found"
fi

echo "" >> "$REPORT"
echo "Recommended Reality SNI candidates to test in RU:" >> "$REPORT"
echo "- \`www.cloudflare.com\`" >> "$REPORT"
echo "- \`dash.cloudflare.com\`" >> "$REPORT"
echo "- \`www.microsoft.com\`" >> "$REPORT"
echo "- \`www.office.com\`" >> "$REPORT"
echo "- \`www.apple.com\`" >> "$REPORT"
echo "- \`www.bing.com\`" >> "$REPORT"
echo "- \`www.wikipedia.org\`" >> "$REPORT"

section "4) MTU Optimization"
MTU_TARGET="${VPS_IP}"
PAYLOADS="1472 1464 1452 1440 1420 1412 1400 1380"
MAX_OK=0

echo "| Payload | Result |" >> "$REPORT"
echo "|---:|:---|" >> "$REPORT"
for s in $PAYLOADS; do
  if [[ "$(uname -s)" == "Darwin" ]]; then
    CMD="ping -D -s ${s} -c 2 ${MTU_TARGET}"
  else
    CMD="ping -M do -s ${s} -c 2 ${MTU_TARGET}"
  fi
  if capture_cmd "$CMD" > "$TMP_DIR/mtu_${s}.log"; then
    echo "| ${s} | OK |" >> "$REPORT"
    MAX_OK="$s"
  else
    echo "| ${s} | FAIL |" >> "$REPORT"
  fi
done

if [[ "$MAX_OK" -gt 0 ]]; then
  MTU=$((MAX_OK + 28))
  pass "MTU probe completed (max payload=${MAX_OK}, recommended MTU=${MTU})"
else
  warn "MTU probe failed for all payload sizes (ICMP/DF likely filtered)"
fi

section "5) Speed Stress (iperf3)"
if [[ "$RUN_IPERF" -eq 1 ]]; then
  if command -v iperf3 >/dev/null 2>&1; then
    I1="$(capture_cmd "iperf3 -c ${VPS_IP} -p ${IPERF_PORT} -P 4 -t ${IPERF_SECONDS} -R" || true)"
    I2="$(capture_cmd "iperf3 -c ${VPS_IP} -p ${IPERF_PORT} -P 4 -t ${IPERF_SECONDS}" || true)"
    I3="$(capture_cmd "iperf3 -c ${VPS_IP} -p ${IPERF_PORT} -u -b 50M -t ${IPERF_SECONDS}" || true)"
    code_block text "$I1"
    code_block text "$I2"
    code_block text "$I3"
    pass "iperf3 tests executed"
  else
    warn "iperf3 is not installed locally; install it and rerun with --run-iperf"
  fi
else
  warn "iperf3 tests skipped (use --run-iperf). On VPS run: iperf3 -s -p ${IPERF_PORT}"
fi

section "Summary"
echo "- PASS: ${PASS_COUNT}" >> "$REPORT"
echo "- FAIL: ${FAIL_COUNT}" >> "$REPORT"
echo "- WARN: ${WARN_COUNT}" >> "$REPORT"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  echo "" >> "$REPORT"
  echo "Overall status: **FAIL**" >> "$REPORT"
  echo "Report generated: ${REPORT}"
  exit 2
fi

echo "" >> "$REPORT"
echo "Overall status: **PASS (with possible WARN items)**" >> "$REPORT"
echo "Report generated: ${REPORT}"
