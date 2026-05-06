#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/opt/pocket-accountant-bot/backups"
CONTAINER="deploy-postgres-1"
DB_NAME="accountant"
DB_USER="postgres"
KEEP_DAYS=7

mkdir -p "$BACKUP_DIR"

FILENAME="$BACKUP_DIR/${DB_NAME}_$(date +%Y%m%d_%H%M%S).sql.gz"
docker exec "$CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$FILENAME"

find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$KEEP_DAYS -delete

echo "Backup created: $FILENAME"
