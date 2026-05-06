#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/deploy/docker-compose.prod.yml"
START_BOT="${START_BOT:-0}"
IMAGE_NAME="${IMAGE_NAME:-pocket-accountant-bot:prod}"

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  echo ".env not found in $ROOT_DIR" >&2
  exit 1
fi

export DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-0}"
export COMPOSE_DOCKER_CLI_BUILD="${COMPOSE_DOCKER_CLI_BUILD:-0}"

docker compose -f "$COMPOSE_FILE" up -d postgres redis
for _ in {1..30}; do
  if docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U postgres -d accountant >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! docker image inspect python:3.11-slim >/dev/null 2>&1; then
  docker pull python:3.11-slim
fi

docker build -t "$IMAGE_NAME" "$ROOT_DIR"
docker compose -f "$COMPOSE_FILE" run --rm migrate
docker compose -f "$COMPOSE_FILE" up -d --no-deps --force-recreate api worker

if [[ "$START_BOT" == "1" ]]; then
  docker compose -f "$COMPOSE_FILE" up -d --no-deps --force-recreate bot
else
  docker compose -f "$COMPOSE_FILE" stop bot >/dev/null 2>&1 || true
fi
