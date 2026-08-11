#!/usr/bin/env bash
# Throwaway: run every service's pytest suite in a mounted python:3.11-slim
# container (matches the Makefile's --no-deps targets; suites are self-contained
# on SQLite, no infra needed). Shared pip-cache volume + retry loop for network.
set -u
ROOT="$(pwd)"
PYCOMMON="$ROOT/shared/py-common"
CACHE="sctpcrs-pip-cache"
LOGDIR="$ROOT/tmp/testlogs"
mkdir -p "$LOGDIR"
services="auth-service gateway vendor-service risk-service sbom-service compliance-service monitoring-service incident-service"

run_one() {
  s="$1"
  svc="$ROOT/services/$s"
  log="$LOGDIR/$s.log"
  MSYS_NO_PATHCONV=1 docker run --rm \
    -v "$svc":/app \
    -v "$PYCOMMON":/shared/py-common \
    -v "$CACHE":/root/.cache/pip \
    -w /app python:3.11-slim sh -c '
      set -e
      # Build the shared lib from a container-local COPY, never the shared mount:
      # 8 parallel containers building a wheel in the same host dir collide
      # ([Errno 17] File exists on build/...dist-info).
      cp -r /shared/py-common /tmp/pyc
      for i in 1 2 3; do
        pip install -q --cache-dir /root/.cache/pip /tmp/pyc \
          && pip install -q --cache-dir /root/.cache/pip -e ".[test]" && break \
          || { echo "pip attempt $i failed, retrying"; sleep 5; }
      done
      python -m pytest tests -q
    ' > "$log" 2>&1
  echo "SVC_EXIT=$?" >> "$log"
}

for s in $services; do run_one "$s" & done
wait

echo "==== TEST SUMMARY ===="
fail=0
for s in $services; do
  res=$(grep -E "[0-9]+ (passed|failed|error)" "$LOGDIR/$s.log" | grep -v "pip attempt" | tail -1)
  ex=$(grep -oE "SVC_EXIT=[0-9]+" "$LOGDIR/$s.log" | tail -1)
  printf "%-20s %-40s %s\n" "$s" "${res:-<no result line>}" "$ex"
  [ "$ex" = "SVC_EXIT=0" ] || fail=1
done
# tidy editable-install artifacts left in the mounted source dirs
find "$ROOT/services" -maxdepth 2 -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null
echo "==== ALL_GREEN=$([ $fail -eq 0 ] && echo yes || echo no) ===="
