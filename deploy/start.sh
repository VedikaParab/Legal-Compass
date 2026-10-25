#!/bin/sh
# Runs the mapping API (internal, port 8000) and the assistant backend (public, $PORT) in one container.
set -e
ROOT="${APP_ROOT:-/srv}"
MAPPING_PORT="${MAPPING_PORT:-8000}"
: "${LEGALCOMPASS_API_KEY:=internal-$(date +%s)}"
export LEGALCOMPASS_API_KEY SB_API_KEYS="$LEGALCOMPASS_API_KEY" SB_RATE_KEY=100000 PYTHONUTF8=1
export LEGALCOMPASS_API="http://127.0.0.1:${MAPPING_PORT}"

cd "$ROOT/mapping_api" && PYTHONPATH=src python -m uvicorn sb_api.main:app --host 127.0.0.1 --port "$MAPPING_PORT" --log-level warning &
for i in $(seq 1 90); do
  python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:${MAPPING_PORT}/v1/meta', timeout=2)" 2>/dev/null && break
  sleep 1
done
echo "mapping API ready on ${MAPPING_PORT}"
cd "$ROOT/backend" && exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8100}" --proxy-headers --forwarded-allow-ips="*"
