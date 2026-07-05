#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$ROOT_DIR/.ft710-server.pid"
LOG_FILE="$ROOT_DIR/logs/ft710-server.log"

if [[ ! -f "$PID_FILE" ]]; then
  echo "FT-710 server is not running: no PID file"
  exit 0
fi

pid="$(cat "$PID_FILE" 2>/dev/null || true)"
if [[ -z "$pid" ]]; then
  rm -f "$PID_FILE"
  echo "FT-710 server is not running: empty PID file removed"
  exit 0
fi

if ! kill -0 "$pid" 2>/dev/null; then
  rm -f "$PID_FILE"
  echo "FT-710 server is not running: stale PID file removed"
  exit 0
fi

echo "Stopping FT-710 server: pid $pid"
kill "$pid"

for _ in {1..20}; do
  if ! kill -0 "$pid" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo "FT-710 server stopped"
    exit 0
  fi
  sleep 0.25
done

echo "Process did not stop gracefully; sending SIGKILL"
kill -9 "$pid" 2>/dev/null || true
rm -f "$PID_FILE"
echo "FT-710 server stopped"
echo "Log: $LOG_FILE"
