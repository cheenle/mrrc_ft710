#!/bin/bash
# mrrc_ft710 restart helper
# Usage: ./restart.sh [--foreground]
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV="$SCRIPT_DIR/.venv"
PIP="$VENV/bin/pip"
PYTHON="$VENV/bin/python"

# Source .env so config.py picks up FT710_SERIAL_PORT etc.
# (start.sh does this; restart.sh must too, otherwise config falls back
#  to the default /dev/cu.SLAB_USBtoUART which doesn't exist here.)
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a; source "$SCRIPT_DIR/.env"; set +a
fi

# Create venv if missing
if [ ! -x "$PYTHON" ]; then
    echo "🔧 Creating virtualenv..."
    python3 -m venv "$VENV"
    echo "📦 Installing dependencies..."
    "$PIP" install --quiet -r requirements.txt
fi

# Kill any existing processes
echo "🛑 Stopping old server..."
pkill -f "server.py" 2>/dev/null || true
pkill -f "scope_pipe.py" 2>/dev/null || true
sleep 1

if [ "${1:-}" = "--foreground" ]; then
    echo "🚀 Starting mrrc_ft710 (foreground)..."
    exec "$PYTHON" server.py
else
    echo "🚀 Starting mrrc_ft710 (background)..."
    nohup "$PYTHON" server.py > /tmp/ft710.log 2>&1 &
    PID=$!
    sleep 2
    if kill -0 "$PID" 2>/dev/null; then
        echo "✅ Server running (PID=$PID)"
        tail -5 /tmp/ft710.log
    else
        echo "❌ Server failed to start"
        tail -20 /tmp/ft710.log
        exit 1
    fi
fi
