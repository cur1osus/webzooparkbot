#!/usr/bin/bash
# Entry point for webzooparkbot-bots.service. Mirrors start-api.sh: the unit file stays
# free of the environment plumbing, so both are edited in one place.
#
# Install to /opt/webzooparkbot/start-bots.sh (chmod +x, owned by root).
set -a
. /etc/webzooparkbot.env
set +a
exec /opt/webzooparkbot/api/.venv/bin/python -m api.bots.runner
