#!/usr/bin/env bash
set -euo pipefail

REMOTE="${REMOTE:-root@REDACTED-OLD-HOST}"
REMOTE_DIR="${REMOTE_DIR:-/root/webzooparkbot}"
DOMAIN="89-22-224-52.sslip.io"
API_UPSTREAM="${API_UPSTREAM:-127.0.0.1:8001}"

remote_bash() {
  ssh "$REMOTE" bash -s -- "$@"
}

echo "[1/8] Build frontend"
npm run build

echo "[2/8] Upload frontend + API"
ssh "$REMOTE" "mkdir -p '${REMOTE_DIR}/dist' '${REMOTE_DIR}/api' '/var/www/webzooparkbot'"
rsync -az --delete ./dist/ "${REMOTE}:${REMOTE_DIR}/dist/"
rsync -az --exclude '__pycache__' --exclude '.venv' ./api/ "${REMOTE}:${REMOTE_DIR}/api/"
ssh "$REMOTE" "rsync -a --delete '${REMOTE_DIR}/dist/' /var/www/webzooparkbot/ && chown -R caddy:caddy /var/www/webzooparkbot"

echo "[3/8] Install Python deps + migration dry-run + DB migration"
remote_bash "$REMOTE_DIR" << 'ENDSSH'
set -euo pipefail
REMOTE_DIR="$1"

load_service_env() {
    local service="$1"
    local env_line
    env_line="$(systemctl show "$service" --property=Environment --value 2>/dev/null || true)"
    if [ -z "$env_line" ]; then
        return 0
    fi

    python3 - "$env_line" <<'PY'
import shlex
import sys

for item in shlex.split(sys.argv[1]):
    if "=" not in item:
        continue
    key, value = item.split("=", 1)
    if key.startswith(("DB_", "BOT_", "APP_")):
        print(f"export {key}={shlex.quote(value)}")
PY
}

eval "$(load_service_env webzooparkbot-api)"

: "${DB_PASSWORD:?DB_PASSWORD is not configured in webzooparkbot-api systemd environment}"
: "${DB_USER:?DB_USER is not configured in webzooparkbot-api systemd environment}"
: "${DB_NAME:?DB_NAME is not configured in webzooparkbot-api systemd environment}"

DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-3306}"
TMP_DB="${DB_NAME}_deploycheck_$(date +%Y%m%d_%H%M%S)"

mysql_root_cmd() {
    mysql --protocol=socket --user=root "$@"
}

mysql_cmd() {
    mysql \
      --host="$DB_HOST" \
      --port="$DB_PORT" \
      --user="$DB_USER" \
      --password="$DB_PASSWORD" \
      --default-character-set=utf8mb4 \
      "$@"
}

mysqldump_cmd() {
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
      "$@"
}

cleanup_tmp_db() {
    mysql_root_cmd -e "DROP DATABASE IF EXISTS \`$TMP_DB\`" >/dev/null 2>&1 || true
}

trap cleanup_tmp_db EXIT

cd "$REMOTE_DIR/api"
[ -x .venv/bin/python ] || python3.12 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python -m pip install -q alembic pymysql >/dev/null 2>&1 || true

echo "[migration-dry-run] Cloning current DB into temporary schema"
DB_USER_HOSTS="$(mysql_root_cmd -Nse "SELECT Host FROM mysql.user WHERE User = '${DB_USER}'")"
if [ -z "$DB_USER_HOSTS" ]; then
    echo "No MySQL host entries found for DB_USER=$DB_USER" >&2
    exit 1
fi

grant_sql="DROP DATABASE IF EXISTS \`$TMP_DB\`; CREATE DATABASE \`$TMP_DB\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
while IFS= read -r db_host_entry; do
    [ -n "$db_host_entry" ] || continue
    grant_sql+=" GRANT ALL PRIVILEGES ON \`$TMP_DB\`.* TO '${DB_USER}'@'${db_host_entry}';"
done <<< "$DB_USER_HOSTS"
grant_sql+=" FLUSH PRIVILEGES;"
mysql_root_cmd -e "$grant_sql"
mysqldump_cmd "$DB_NAME" | mysql_cmd "$TMP_DB"
env -u DB_URL DB_NAME="$TMP_DB" .venv/bin/alembic upgrade head >/dev/null
cleanup_tmp_db

echo "[db-backup] Creating MySQL backup before migrations"
bash ./backup_db.sh
env -u DB_URL .venv/bin/alembic upgrade head
ENDSSH

echo "[4/8] Verify backend startup entrypoints"
remote_bash "$REMOTE_DIR" << 'ENDSSH'
set -euo pipefail
REMOTE_DIR="$1"
cd "$REMOTE_DIR"
api/.venv/bin/python -c "import api.main"
ENDSSH

echo "[5/8] Align API service entrypoint"
remote_bash "$REMOTE_DIR" << 'ENDSSH'
set -euo pipefail
REMOTE_DIR="$1"
mkdir -p /etc/systemd/system/webzooparkbot-api.service.d
cat > /etc/systemd/system/webzooparkbot-api.service.d/entrypoint.conf <<'EOF'
[Service]
WorkingDirectory=REMOTE_DIR_PLACEHOLDER
ExecStart=
ExecStart=REMOTE_DIR_PLACEHOLDER/api/.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8001
EOF
python3 - "$REMOTE_DIR" <<'PY'
from pathlib import Path
import sys

path = Path("/etc/systemd/system/webzooparkbot-api.service.d/entrypoint.conf")
path.write_text(path.read_text().replace("REMOTE_DIR_PLACEHOLDER", sys.argv[1]))
PY
systemctl daemon-reload
ENDSSH

echo "[6/8] Restart API service"
remote_bash << 'ENDSSH'
set -euo pipefail
systemctl restart webzooparkbot-api
for _ in $(seq 1 20); do
    state="$(systemctl is-active webzooparkbot-api || true)"
    if [ "$state" = "active" ]; then
        break
    fi
    if [ "$state" = "failed" ]; then
        systemctl status webzooparkbot-api --no-pager -l || true
        exit 1
    fi
    sleep 1
done
for _ in $(seq 1 20); do
    if curl -fsS http://127.0.0.1:8001/v2/api/health >/dev/null 2>&1; then
        exit 0
    fi
    sleep 1
done
systemctl status webzooparkbot-api --no-pager -l || true
journalctl -u webzooparkbot-api -n 80 --no-pager || true
exit 1
ENDSSH

echo "[7/8] Align Caddy routes"
remote_bash "$DOMAIN" "$API_UPSTREAM" << 'ENDSSH'
set -euo pipefail
DOMAIN="$1"
API_UPSTREAM="$2"

cat > /etc/caddy/Caddyfile <<'EOF'
{
	https_port 8443
	http_port 80
	auto_https off
}

http://DOMAIN_PLACEHOLDER {
	redir https://{host}:8443{uri} permanent
}

DOMAIN_PLACEHOLDER:8443 {
	tls /etc/caddy/certs/fullchain.pem /etc/caddy/certs/privkey.pem

	handle /v2/api/* {
		reverse_proxy API_UPSTREAM_PLACEHOLDER
	}

	handle /api/* {
		reverse_proxy API_UPSTREAM_PLACEHOLDER
	}

	handle {
		root * /var/www/webzooparkbot

		@hashedAssets path_regexp assets/.*\.(js|css)$
		header @hashedAssets Cache-Control "public, max-age=31536000, immutable"

		@rlottie path /tgsticker/*
		header @rlottie Cache-Control "public, max-age=604800"

		@tgs path_regexp \.tgs$
		header @tgs Cache-Control "public, max-age=86400, stale-while-revalidate=604800"

		@staticOther path_regexp \.(png|jpg|jpeg|gif|svg|ico|webp|woff|woff2)$
		header @staticOther Cache-Control "public, max-age=604800"

		file_server
		try_files {path} /index.html
	}
}
EOF

python3 - "$DOMAIN" "$API_UPSTREAM" <<'PY'
from pathlib import Path
import sys

path = Path("/etc/caddy/Caddyfile")
contents = path.read_text()
contents = contents.replace("DOMAIN_PLACEHOLDER", sys.argv[1])
contents = contents.replace("API_UPSTREAM_PLACEHOLDER", sys.argv[2])
path.write_text(contents)
PY
systemctl reload caddy
systemctl is-active caddy
ENDSSH

echo "[8/8] Verify public routes"
response="$(curl -kfsS "https://${DOMAIN}:8443/v2/api/health")"
python3 - "$response" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
if payload != {"ok": True}:
    raise SystemExit(f"unexpected public health payload: {payload!r}")
PY

echo ""
echo "Done!"
echo "  App:  https://${DOMAIN}:8443"
echo "  API:  https://${DOMAIN}:8443/v2/api/health"
