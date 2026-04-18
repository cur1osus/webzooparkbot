#!/usr/bin/env bash
set -euo pipefail

DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-zooparkbot}"
DB_PASSWORD="${DB_PASSWORD:?DB_PASSWORD env var is required}"
DB_NAME="${DB_NAME:-zooparkbot}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"

mkdir -p "$BACKUP_DIR"
timestamp="$(date +%Y%m%d_%H%M%S)"
backup_path="${BACKUP_DIR}/${DB_NAME}_pre_mantissa_${timestamp}.sql.gz"

mysqldump \
  --host="$DB_HOST" \
  --port="$DB_PORT" \
  --user="$DB_USER" \
  --password="$DB_PASSWORD" \
  --single-transaction \
  --no-tablespaces \
  --routines \
  --triggers \
  --hex-blob \
  --default-character-set=utf8mb4 \
  "$DB_NAME" | gzip > "$backup_path"

printf '%s\n' "$backup_path"
