#!/usr/bin/env bash
set -euo pipefail

# Deploys ZooPark to the live "zomserv" host (REDACTED-HOST). This host runs many
# other bots, so this script is deliberately narrow: it writes ONLY into ZooPark's own
# paths and never rewrites the shared /etc/caddy/Caddyfile. ZooPark's Caddy config lives
# in the isolated fragment /etc/caddy/sites/zoopark.caddy, which the main Caddyfile
# already imports via `import /etc/caddy/sites/*.caddy` — so a code deploy touches no
# Caddy config at all.
#
# History: an earlier deploy.sh targeted the decommissioned "servam" host
# (REDACTED-OLD-HOST, dead since 2026-06-20) and rewrote the whole Caddyfile. Do not restore
# that behaviour — on this shared host it would clobber every other bot's routes.
#
# Usage:
#   ./deploy.sh                 # frontend + backend (deps, DB backup, migrations, restart, webhook)
#   ./deploy.sh --frontend-only # rebuild + upload static site only (UI-only changes)
#   ./deploy.sh --backend-only  # API code + migrations + restart + webhook, skip the frontend

REMOTE="${REMOTE:-root@REDACTED-HOST}"
WWW_DIR="${WWW_DIR:-/var/www/zoopark}"
APP_DIR="${APP_DIR:-/opt/webzooparkbot}"
API_DIR="${API_DIR:-${APP_DIR}/api}"
APP_USER="${APP_USER:-zoopark}"
ENV_FILE="${ENV_FILE:-/etc/webzooparkbot.env}"
SERVICE="${SERVICE:-webzooparkbot-api}"
# The AI rivals run as their own unit. Restarted after the API so a failing rival never
# blocks the game from coming back up; skipped without complaint if it isn't installed yet.
BOTS_SERVICE="${BOTS_SERVICE:-webzooparkbot-bots}"
API_UPSTREAM="${API_UPSTREAM:-127.0.0.1:8900}"
DOMAIN="${DOMAIN:-REDACTED-DOMAIN}"
PUBLIC_URL="https://${DOMAIN}"

DO_FRONTEND=1
DO_BACKEND=1
case "${1:-}" in
  --frontend-only) DO_BACKEND=0 ;;
  --backend-only)  DO_FRONTEND=0 ;;
  "" ) ;;
  *) echo "Unknown option: $1" >&2; exit 2 ;;
esac

remote_bash() {
  ssh "$REMOTE" bash -s -- "$@"
}

if [ "$DO_FRONTEND" -eq 1 ]; then
  echo "[frontend 1/2] Build"
  npm run build

  echo "[frontend 2/2] Upload to ${WWW_DIR}"
  # Vite copies public/ into dist/, so dist/ is self-contained and --delete is safe.
  ssh "$REMOTE" "mkdir -p '${WWW_DIR}'"
  rsync -az --delete ./dist/ "${REMOTE}:${WWW_DIR}/"
  ssh "$REMOTE" "chown -R caddy:caddy '${WWW_DIR}'"
fi

if [ "$DO_BACKEND" -eq 1 ]; then
  echo "[backend 1/5] Upload API to ${API_DIR}"
  # --exclude also protects these paths from --delete, so the server-side virtualenv and
  # byte-cache survive. Files land owned by the pushing uid; chown restores the app user.
  ssh "$REMOTE" "mkdir -p '${API_DIR}'"
  rsync -az --delete \
    --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' \
    ./api/ "${REMOTE}:${API_DIR}/"
  ssh "$REMOTE" "chown -R ${APP_USER}:${APP_USER} '${API_DIR}'"

  echo "[backend 2/5] Install deps, back up DB, run migrations"
  remote_bash "$API_DIR" "$APP_USER" "$ENV_FILE" "$APP_DIR" << 'ENDSSH'
set -euo pipefail
API_DIR="$1"; APP_USER="$2"; ENV_FILE="$3"; APP_DIR="$4"

# The env file is root:zoopark 640; we are root here, so we can read it to drive the
# DB backup and to hand a populated environment to the app user's tools.
set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

: "${DB_NAME:?DB_NAME missing from ${ENV_FILE}}"
: "${DB_USER:?DB_USER missing from ${ENV_FILE}}"
: "${BOT_TOKEN:?BOT_TOKEN missing from ${ENV_FILE}}"
: "${TELEGRAM_WEBHOOK_SECRET:?TELEGRAM_WEBHOOK_SECRET missing: Stars payments cannot be verified}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-3306}"
DB_PASSWORD="${DB_PASSWORD:-}"

echo "[deps] pip install (as ${APP_USER})"
runuser -u "$APP_USER" -- "${API_DIR}/.venv/bin/pip" install -q -r "${API_DIR}/requirements.txt"

# Passing --password on the command line would expose it to every user via `ps`.
MYSQL_DEFAULTS_FILE="$(mktemp)"
chmod 600 "$MYSQL_DEFAULTS_FILE"
trap 'rm -f "$MYSQL_DEFAULTS_FILE"' EXIT
cat > "$MYSQL_DEFAULTS_FILE" <<EOF
[client]
host=$DB_HOST
port=$DB_PORT
user=$DB_USER
password=$DB_PASSWORD
EOF

echo "[db-backup] Dumping ${DB_NAME} before migrations"
backup_dir="${APP_DIR}/backups"
mkdir -p "$backup_dir"
backup_file="$backup_dir/${DB_NAME}_$(date +%Y%m%d_%H%M%S).sql.gz"
mysqldump --defaults-extra-file="$MYSQL_DEFAULTS_FILE" \
  --single-transaction --no-tablespaces --routines --triggers --hex-blob \
  --default-character-set=utf8mb4 "$DB_NAME" | gzip -c > "$backup_file"
chmod 600 "$backup_file"
echo "[db-backup] Saved $backup_file"

echo "[migration] alembic upgrade head (as ${APP_USER})"
cd "$API_DIR"
runuser -u "$APP_USER" -- "${API_DIR}/.venv/bin/alembic" upgrade head

echo "[migration] Verifying database is at head"
runuser -u "$APP_USER" -- "${API_DIR}/.venv/bin/python" - <<'PY'
import subprocess

def revisions(*args):
    out = subprocess.check_output([".venv/bin/alembic", *args], text=True)
    return {line.split()[0] for line in out.splitlines() if line.strip() and "INFO" not in line}

heads = revisions("heads")
current = revisions("current")
if current != heads:
    raise SystemExit(f"database revision mismatch: current={sorted(current)} heads={sorted(heads)}")
print(f"[migration] Current revision: {', '.join(sorted(current))}")
PY
ENDSSH

  echo "[backend 3/5] Verify import + restart service"
  remote_bash "$API_DIR" "$APP_USER" "$ENV_FILE" "$APP_DIR" "$SERVICE" "$API_UPSTREAM" << 'ENDSSH'
set -euo pipefail
API_DIR="$1"; APP_USER="$2"; ENV_FILE="$3"; APP_DIR="$4"; SERVICE="$5"; API_UPSTREAM="$6"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

# config.py refuses to import without BOT_TOKEN etc., so this doubles as a config check.
( cd "$APP_DIR" && runuser -u "$APP_USER" --preserve-environment -- \
    "${API_DIR}/.venv/bin/python" -c "import api.main" )

systemctl restart "$SERVICE"
for _ in $(seq 1 20); do
    state="$(systemctl is-active "$SERVICE" || true)"
    [ "$state" = "active" ] && break
    if [ "$state" = "failed" ]; then
        systemctl status "$SERVICE" --no-pager -l || true
        exit 1
    fi
    sleep 1
done
for _ in $(seq 1 20); do
    if curl -fsS "http://${API_UPSTREAM}/api/health" >/dev/null 2>&1; then
        exit 0
    fi
    sleep 1
done
systemctl status "$SERVICE" --no-pager -l || true
journalctl -u "$SERVICE" -n 80 --no-pager || true
exit 1
ENDSSH

  echo "[backend 4/5] Restart AI rivals"
  remote_bash "$ENV_FILE" "$BOTS_SERVICE" << 'ENDSSH'
set -euo pipefail
ENV_FILE="$1"; BOTS_SERVICE="$2"

if ! systemctl list-unit-files "${BOTS_SERVICE}.service" --no-legend | grep -q .; then
    echo "[bots] ${BOTS_SERVICE} is not installed — skipping."
    echo "[bots] To install: copy deploy/webzooparkbot-bots.service and deploy/start-bots.sh,"
    echo "[bots] then: systemctl daemon-reload && systemctl enable --now ${BOTS_SERVICE}"
    exit 0
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

# Not fatal: without a key the rivals fall back to in-character default plans and keep
# playing. Worth saying out loud, because the symptom (bots that never change strategy)
# otherwise looks like a bug in the planner rather than a missing secret.
if [ -z "${ROUTERAI_API_KEY:-}" ]; then
    echo "[bots] WARNING: ROUTERAI_API_KEY is not set in ${ENV_FILE}."
    echo "[bots] The rivals will run on fallback plans and never replan."
fi

systemctl restart "$BOTS_SERVICE"
for _ in $(seq 1 15); do
    state="$(systemctl is-active "$BOTS_SERVICE" || true)"
    [ "$state" = "active" ] && exit 0
    if [ "$state" = "failed" ]; then
        systemctl status "$BOTS_SERVICE" --no-pager -l || true
        journalctl -u "$BOTS_SERVICE" -n 40 --no-pager || true
        exit 1
    fi
    sleep 1
done
echo "[bots] ${BOTS_SERVICE} did not become active in time"
journalctl -u "$BOTS_SERVICE" -n 40 --no-pager || true
exit 1
ENDSSH

  echo "[backend 5/5] Register Telegram webhook"
  remote_bash "$ENV_FILE" "${PUBLIC_URL}/api/telegram/webhook" << 'ENDSSH'
set -euo pipefail
ENV_FILE="$1"; WEBHOOK_URL="$2"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a
: "${BOT_TOKEN:?BOT_TOKEN missing}"
: "${TELEGRAM_WEBHOOK_SECRET:?TELEGRAM_WEBHOOK_SECRET missing}"

# Without this the bot never delivers successful_payment and paying players get nothing.
response="$(curl -fsS "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H 'Content-Type: application/json' \
  -d "$(python3 -c '
import json, sys
print(json.dumps({
    "url": sys.argv[1],
    "secret_token": sys.argv[2],
    "allowed_updates": ["message", "pre_checkout_query"],
}))' "$WEBHOOK_URL" "$TELEGRAM_WEBHOOK_SECRET")")"

python3 - "$response" <<'PY'
import json, sys
payload = json.loads(sys.argv[1])
if not payload.get("ok"):
    raise SystemExit(f"setWebhook failed: {payload!r}")
print("[webhook] registered")
PY
ENDSSH
fi

echo "[verify] Public routes"
# zomserv's Caddy serves a real Let's Encrypt cert for the sslip.io domain, so no -k.
health="$(curl -fsS "${PUBLIC_URL}/api/health")"
python3 - "$health" <<'PY'
import json, sys
payload = json.loads(sys.argv[1])
if payload != {"ok": True}:
    raise SystemExit(f"unexpected public health payload: {payload!r}")
print("[verify] /api/health ok")
PY

if [ "$DO_FRONTEND" -eq 1 ]; then
  served="$(curl -fsS "${PUBLIC_URL}/" | grep -o 'assets/index-[^"]*\.js' | head -1 || true)"
  built="$(grep -o 'assets/index-[^"]*\.js' dist/index.html | head -1 || true)"
  echo "[verify] served bundle: ${served:-none} | built: ${built:-none}"
  if [ -n "$built" ] && [ "$served" != "$built" ]; then
    echo "[verify] WARNING: served bundle does not match the build just uploaded" >&2
  fi
fi

echo ""
echo "Done!"
echo "  App:  ${PUBLIC_URL}"
echo "  API:  ${PUBLIC_URL}/api/health"
