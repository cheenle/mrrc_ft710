#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$ROOT_DIR/venv/bin/python"
PID_FILE="$ROOT_DIR/.ft710-server.pid"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/ft710-server.log"

if [[ ! -x "$VENV_PY" ]]; then
  echo "venv not found. Create it first: python3 -m venv venv && venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "FT-710 server is already running: pid $old_pid"
    echo "Log: $LOG_FILE"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

nohup "$VENV_PY" server.py "$@" >>"$LOG_FILE" 2>&1 &
pid="$!"
echo "$pid" > "$PID_FILE"

sleep 1
if kill -0 "$pid" 2>/dev/null; then
  echo "FT-710 server started: pid $pid"
  echo "Log: $LOG_FILE"
  echo "Stop: ./stop.sh"
else
  echo "FT-710 server failed to start. Check: $LOG_FILE" >&2
  rm -f "$PID_FILE"
  exit 1
fi
