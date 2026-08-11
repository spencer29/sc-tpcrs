#!/usr/bin/env bash
# Re-run risk-service tests only. Heavy ML wheels over a flaky link, so give pip
# a long per-connection timeout and many retries; build the shared lib from a
# container-local copy (never the shared mount).
set -u
ROOT="$(pwd)"
LOG="$ROOT/tmp/testlogs/risk-service.log"
: > "$LOG"
MSYS_NO_PATHCONV=1 docker run --rm \
  -v "$ROOT/services/risk-service":/app \
  -v "$ROOT/shared/py-common":/shared/py-common \
  -v sctpcrs-pip-cache:/root/.cache/pip \
  -w /app python:3.11-slim sh -c '
    set -e
    cp -r /shared/py-common /tmp/pyc
    PIP="pip install -q --cache-dir /root/.cache/pip --timeout 120 --retries 10"
    for i in 1 2 3 4 5; do
      $PIP /tmp/pyc && $PIP -e ".[test]" && break \
        || { echo "=== outer pip attempt $i failed, retrying ==="; sleep 8; }
    done
    python -m pytest tests -q
  ' > "$LOG" 2>&1
echo "SVC_EXIT=$?" >> "$LOG"
find "$ROOT/services/risk-service" -maxdepth 1 -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null
rm -rf "$ROOT/shared/py-common/build" "$ROOT/shared/py-common"/*.egg-info 2>/dev/null
echo "==== risk-service done ===="
grep -E "[0-9]+ (passed|failed|error)" "$LOG" | grep -v "pip attempt" | tail -1
tail -1 "$LOG"
