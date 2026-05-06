#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

WORKSPACE = Path("/root/.openclaw/workspace-kupriyanow-content")
SESSIONS_DIR = Path("/root/.openclaw/agents/personal-content/sessions")
CACHE_DIR = WORKSPACE / "memory" / "pending_posts"
LOG_PATH = WORKSPACE / "memory" / "publish_log.jsonl"
GENERATED_DIR = WORKSPACE / "generated"
OWNER_TARGET = os.environ.get("OPENCLAW_OWNER_TARGET", "72916668")

POST_ID_RE = re.compile(r"(?im)^\s*POST_ID:\s*([^\n\r`]+)")
CHANNEL_RE = re.compile(r"(?im)^\s*CHANNEL:\s*([^\n\r`]+)")
PUBLISH_AT_RE = re.compile(r"(?im)^\s*PUBLISH_AT:\s*([^\n\r`]+)")


def _norm(text: str) -> str:
    return text.replace("\r\n", "\n").replace("```", "").strip()


def _extract_block(text: str, start: str, end_markers: list[str]) -> str:
    start_re = re.compile(rf"(?im)^\s*{re.escape(start)}\s*\n?")
    m = start_re.search(text)
    if not m:
        return ""
    block_start = m.end()
    end_positions: list[int] = []
    for marker in end_markers:
        end_re = re.compile(rf"(?im)^\s*{re.escape(marker)}\s*")
        em = end_re.search(text, block_start)
        if em:
            end_positions.append(em.start())
    block_end = min(end_positions) if end_positions else len(text)
    return text[block_start:block_end].strip()


def parse_post_from_text(raw: str) -> dict[str, Any] | None:
    text = _norm(raw)

    post_id_m = POST_ID_RE.search(text)
    channel_m = CHANNEL_RE.search(text)
    if not post_id_m or not channel_m:
        return None

    post_id = post_id_m.group(1).strip()
    channel = channel_m.group(1).strip()
    publish_at_m = PUBLISH_AT_RE.search(text)
    publish_at = publish_at_m.group(1).strip() if publish_at_m else ""

    post_text = _extract_block(
        text,
        "TEXT:",
        ["IMAGE_PROMPT:", "APPROVAL_MESSAGE:", "INLINE_KEYBOARD_JSON:"],
    )
    image_prompt = _extract_block(
        text, "IMAGE_PROMPT:", ["APPROVAL_MESSAGE:", "INLINE_KEYBOARD_JSON:"]
    )

    if not post_text or not image_prompt:
        return None

    return {
        "post_id": post_id,
        "channel": channel,
        "publish_at": publish_at,
        "text": post_text,
        "image_prompt": image_prompt,
        "source": "session",
    }


def find_post_in_sessions(post_id: str) -> dict[str, Any] | None:
    if not SESSIONS_DIR.exists():
        return None

    files = sorted(SESSIONS_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    needle = f"POST_ID: {post_id}".lower()

    for session_file in files:
        try:
            lines = session_file.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue

        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg = row.get("message") or {}
            if msg.get("role") != "assistant":
                continue

            for item in msg.get("content") or []:
                if item.get("type") != "text":
                    continue
                raw = item.get("text") or ""
                if needle not in raw.lower():
                    continue
                parsed = parse_post_from_text(raw)
                if parsed and parsed.get("post_id") == post_id:
                    parsed["session_file"] = str(session_file)
                    parsed["session_timestamp"] = row.get("timestamp")
                    return parsed

    return None


def cache_path(post_id: str) -> Path:
    return CACHE_DIR / f"{post_id}.json"


def save_cache(post: dict[str, Any]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = cache_path(post["post_id"])
    path.write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")


def load_cache(post_id: str) -> dict[str, Any] | None:
    path = cache_path(post_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def ensure_post(post_id: str) -> dict[str, Any]:
    cached = load_cache(post_id)
    if cached:
        return cached

    found = find_post_in_sessions(post_id)
    if not found:
        raise RuntimeError(f"Пост {post_id} не найден в сессиях и кэше.")

    save_cache(found)
    return found


def find_generated_image(post_id: str) -> Path | None:
    out_dir = GENERATED_DIR / post_id
    if not out_dir.exists():
        return None
    candidates: list[Path] = []
    for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        candidates.extend(out_dir.glob(ext))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def generate_image(post_id: str, prompt: str) -> Path:
    out_dir = GENERATED_DIR / post_id
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "python3",
        "/usr/lib/node_modules/openclaw/skills/openai-image-gen/scripts/gen.py",
        "--model",
        "gpt-image-1",
        "--prompt",
        prompt,
        "--count",
        "1",
        "--size",
        "1024x1536",
        "--quality",
        "high",
        "--out-dir",
        str(out_dir),
    ]
    run = subprocess.run(cmd, capture_output=True, text=True)
    if run.returncode != 0:
        err = (run.stderr or run.stdout or "").strip()
        raise RuntimeError(f"Ошибка генерации изображения: {err}")

    image = find_generated_image(post_id)
    if not image:
        raise RuntimeError("Изображение не найдено после генерации.")

    return image


def send_post(channel: str, text: str, media_path: Path) -> dict[str, Any]:
    media_value = str(media_path)
    if media_path.exists():
        media_value = upload_media(media_path)

    cmd = [
        "openclaw",
        "message",
        "send",
        "--channel",
        "telegram",
        "--target",
        channel,
        "--message",
        text,
        "--media",
        media_value,
        "--json",
    ]
    run = subprocess.run(cmd, capture_output=True, text=True)
    if run.returncode == 0:
        out = (run.stdout or "").strip()
        try:
            return json.loads(out) if out else {"ok": True}
        except json.JSONDecodeError:
            return {"ok": True, "raw": out}

    err = (run.stderr or run.stdout or "").strip()
    # If channel publish is blocked (bot not member), deliver to owner DM as fallback.
    if "bot is not a member of the channel chat" in err and channel != OWNER_TARGET:
        fallback_text = (
            f"⚠️ Канал {channel} недоступен для бота (нет прав публикации). "
            "Отправляю в личный чат владельца.\n\n"
            f"{text}"
        )
        fallback_cmd = [
            "openclaw",
            "message",
            "send",
            "--channel",
            "telegram",
            "--target",
            OWNER_TARGET,
            "--message",
            fallback_text,
            "--media",
            media_value,
            "--json",
        ]
        fallback_run = subprocess.run(fallback_cmd, capture_output=True, text=True)
        if fallback_run.returncode != 0:
            ferr = (fallback_run.stderr or fallback_run.stdout or "").strip()
            raise RuntimeError(
                f"Ошибка отправки в канал и fallback: channel={err}; fallback={ferr}"
            )
        fallback_out = (fallback_run.stdout or "").strip()
        try:
            fallback_result = json.loads(fallback_out) if fallback_out else {"ok": True}
        except json.JSONDecodeError:
            fallback_result = {"ok": True, "raw": fallback_out}
        return {
            "ok": True,
            "fallback": True,
            "channelTarget": channel,
            "ownerTarget": OWNER_TARGET,
            "channelError": err,
            "result": fallback_result,
        }

    raise RuntimeError(f"Ошибка отправки в Telegram: {err}")


def upload_media(path: Path) -> str:
    # Catbox returns direct media URL suitable for Telegram remote fetch.
    cmd = [
        "curl",
        "-fsS",
        "-F",
        "reqtype=fileupload",
        "-F",
        f"fileToUpload=@{path}",
        "https://catbox.moe/user/api.php",
    ]
    run = subprocess.run(cmd, capture_output=True, text=True)
    if run.returncode != 0:
        err = (run.stderr or run.stdout or "").strip()
        raise RuntimeError(f"Ошибка загрузки изображения в URL: {err}")

    url = (run.stdout or "").strip()
    if not url.startswith("http"):
        raise RuntimeError(f"upload API не вернул URL: {url[:300]}")
    return url


def log_event(event: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def cmd_publish(post_id: str, trigger: str) -> dict[str, Any]:
    post = ensure_post(post_id)

    image = generate_image(post_id, post["image_prompt"])
    send_result = send_post(post["channel"], post["text"], image)

    event = {
        "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "action": "publish",
        "trigger": trigger,
        "post_id": post_id,
        "channel": post["channel"],
        "publish_at": post.get("publish_at", ""),
        "image": str(image),
        "result": send_result,
    }
    log_event(event)

    return {
        "ok": True,
        "post_id": post_id,
        "channel": post["channel"],
        "image": str(image),
        "result": send_result,
    }


def cmd_cancel(post_id: str) -> dict[str, Any]:
    path = cache_path(post_id)
    if path.exists():
        path.unlink(missing_ok=True)

    event = {
        "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "action": "cancel",
        "post_id": post_id,
    }
    log_event(event)
    return {"ok": True, "post_id": post_id, "cancelled": True}


def cmd_cache(post_id: str) -> dict[str, Any]:
    post = ensure_post(post_id)
    save_cache(post)
    return {"ok": True, "post_id": post_id, "cached": True}


def main() -> int:
    parser = argparse.ArgumentParser(description="Personal content post operations")
    sub = parser.add_subparsers(dest="cmd", required=True)

    for name in ("publish", "approve", "cancel", "cache"):
        p = sub.add_parser(name)
        p.add_argument("--post-id", required=True)

    args = parser.parse_args()

    try:
        if args.cmd == "publish":
            data = cmd_publish(args.post_id, "publish_now")
        elif args.cmd == "approve":
            data = cmd_publish(args.post_id, "approve")
        elif args.cmd == "cancel":
            data = cmd_cancel(args.post_id)
        elif args.cmd == "cache":
            data = cmd_cache(args.post_id)
        else:
            raise RuntimeError("unknown command")

        print(json.dumps(data, ensure_ascii=False))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
