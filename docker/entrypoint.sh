#!/bin/bash
set -e

case "$SERVICE" in
  backend)
    alembic upgrade head
    exec uvicorn backend.app:create_app --factory --host 0.0.0.0 --port 8080
    ;;
  bot)
    exec python -m bot.entrypoint
    ;;
  worker)
    exec python -m worker.entrypoint
    ;;
  *)
    echo "Unknown SERVICE: $SERVICE"
    echo "Set SERVICE to one of: backend, bot, worker"
    exit 1
    ;;
esac
