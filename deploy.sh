#!/usr/bin/env bash
set -euo pipefail

REMOTE="${REMOTE:-root@REDACTED-OLD-HOST}"
REMOTE_DIR="${REMOTE_DIR:-/root/webzooparkbot}"
DOMAIN="89-22-224-52.sslip.io"

echo "[1/5] Build frontend"
npm run build

echo "[2/5] Upload frontend + API"
ssh "$REMOTE" "mkdir -p '${REMOTE_DIR}/dist' '${REMOTE_DIR}/api' '/var/www/webzooparkbot'"
rsync -az --delete ./dist/ "${REMOTE}:${REMOTE_DIR}/dist/"
rsync -az --exclude '__pycache__' --exclude '.venv' ./api/ "${REMOTE}:${REMOTE_DIR}/api/"
ssh "$REMOTE" "rsync -a --delete /root/webzooparkbot/dist/ /var/www/webzooparkbot/ && chown -R caddy:caddy /var/www/webzooparkbot"

echo "[3/5] Install Python deps + DB migration"
ssh "$REMOTE" bash << 'ENDSSH'
cd /root/webzooparkbot/api
[ -x .venv/bin/python ] || python3.12 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python -m pip install -q alembic pymysql >/dev/null 2>&1 || true
echo "[db-backup] Creating MySQL backup before migrations"
bash ./backup_db.sh
.venv/bin/alembic upgrade head
ENDSSH

echo "[4/7] Verify backend startup entrypoints"
ssh "$REMOTE" bash << 'ENDSSH'
cd /root/webzooparkbot
api/.venv/bin/python -c "import api.main"
ENDSSH

echo "[5/7] Align API service entrypoint"
ssh "$REMOTE" bash << 'ENDSSH'
mkdir -p /etc/systemd/system/webzooparkbot-api.service.d
cat > /etc/systemd/system/webzooparkbot-api.service.d/entrypoint.conf <<'EOF'
[Service]
WorkingDirectory=/root/webzooparkbot
ExecStart=
ExecStart=/root/webzooparkbot/api/.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8001
EOF
systemctl daemon-reload
ENDSSH

echo "[6/7] Restart API service"
ssh "$REMOTE" bash << 'ENDSSH'
systemctl restart webzooparkbot-api
for _ in $(seq 1 20); do
    state="$(systemctl is-active webzooparkbot-api || true)"
    if [ "$state" = "active" ]; then
        exit 0
    fi
    if [ "$state" = "failed" ]; then
        systemctl status webzooparkbot-api --no-pager -l || true
        exit 1
    fi
    sleep 1
done
systemctl status webzooparkbot-api --no-pager -l || true
exit 1
ENDSSH

echo "[7/7] Reload Caddy"
ssh "$REMOTE" "systemctl reload caddy && systemctl is-active caddy"

echo ""
echo "Done!"
echo "  App:  https://${DOMAIN}:8443"
echo "  API:  https://${DOMAIN}:8443/api/me"
