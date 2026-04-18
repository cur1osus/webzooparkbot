#!/usr/bin/env bash
set -euo pipefail

REMOTE="${REMOTE:-root@REDACTED-OLD-HOST}"
REMOTE_DIR="${REMOTE_DIR:-/root/webzooparkbot}"
DOMAIN="89-22-224-52.sslip.io"

remote_bash() {
  ssh "$REMOTE" bash -s -- "$REMOTE_DIR"
}

echo "[1/5] Build frontend"
npm run build

echo "[2/5] Upload frontend + API"
ssh "$REMOTE" "mkdir -p '${REMOTE_DIR}/dist' '${REMOTE_DIR}/api' '/var/www/webzooparkbot'"
rsync -az --delete ./dist/ "${REMOTE}:${REMOTE_DIR}/dist/"
rsync -az --exclude '__pycache__' --exclude '.venv' ./api/ "${REMOTE}:${REMOTE_DIR}/api/"
ssh "$REMOTE" "rsync -a --delete '${REMOTE_DIR}/dist/' /var/www/webzooparkbot/ && chown -R caddy:caddy /var/www/webzooparkbot"

echo "[3/5] Install Python deps + DB migration"
remote_bash << 'ENDSSH'
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

cd "$REMOTE_DIR/api"
[ -x .venv/bin/python ] || python3.12 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python -m pip install -q alembic pymysql >/dev/null 2>&1 || true
echo "[db-backup] Creating MySQL backup before migrations"
bash ./backup_db.sh
.venv/bin/alembic upgrade head
ENDSSH

echo "[4/7] Verify backend startup entrypoints"
remote_bash << 'ENDSSH'
set -euo pipefail
REMOTE_DIR="$1"
cd "$REMOTE_DIR"
api/.venv/bin/python -c "import api.main"
ENDSSH

echo "[5/7] Align API service entrypoint"
remote_bash << 'ENDSSH'
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

echo "[6/7] Restart API service"
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
    if curl -fsS http://127.0.0.1:8001/v2/api/health >/dev/null; then
        exit 0
    fi
    sleep 1
done
systemctl status webzooparkbot-api --no-pager -l || true
journalctl -u webzooparkbot-api -n 80 --no-pager || true
exit 1
ENDSSH

echo "[7/7] Reload Caddy"
ssh "$REMOTE" "systemctl reload caddy && systemctl is-active caddy"

echo ""
echo "Done!"
echo "  App:  https://${DOMAIN}:8443"
echo "  API:  https://${DOMAIN}:8443/api/me"
