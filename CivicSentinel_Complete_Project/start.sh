#!/usr/bin/env bash
# ==============================================================================
# CivicSentinel — Agentic Visual Infrastructure Intelligence Platform
# OpenCV AI Competition 2026 Powered by AWS
# 1-Click Startup for macOS, Linux, and AWS EC2 (x86_64 and Graviton ARM64)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "  CivicSentinel — Unified Single-Port Deployment (Port 8000)"
echo "  OpenCV AI Competition 2026 Powered by AWS"
echo "============================================================"

# 1. Locate Python 3.10+
PYTHON_BIN=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        PY_VER=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
        MAJOR=$(echo "$PY_VER" | cut -d. -f1)
        MINOR=$(echo "$PY_VER" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
            PYTHON_BIN="$cmd"
            echo "[OK] Found compatible Python: $PYTHON_BIN (v$PY_VER)"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "[ERROR] Python 3.10+ is required but not found in PATH."
    exit 1
fi

# 2. Setup Environment Variables
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "[Setup] Copying .env.example to .env..."
    cp .env.example .env
fi

# 3. Create Virtual Environment if missing
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[Setup] Creating virtual environment in $VENV_DIR..."
    if command -v uv >/dev/null 2>&1; then
        uv venv "$VENV_DIR" --python "$PYTHON_BIN"
    else
        "$PYTHON_BIN" -m venv "$VENV_DIR"
    fi
fi

# Activate virtualenv
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# 4. Install backend dependencies
echo "[Setup] Checking and installing dependencies..."
if command -v uv >/dev/null 2>&1; then
    uv pip install -r backend/requirements.txt
else
    pip install --upgrade pip >/dev/null 2>&1 || true
    pip install -r backend/requirements.txt
fi

# 5. Build React 18 Frontend if dist is missing
if [ ! -f "frontend/dist/index.html" ]; then
    if command -v npm >/dev/null 2>&1; then
        echo "[Build] Compiling frontend application into frontend/dist..."
        (cd frontend && npm install && npm run build)
    else
        echo "[WARNING] npm not found and frontend/dist/index.html missing. UI may not be served."
    fi
fi

export PYTHONPATH="$SCRIPT_DIR"

echo ""
echo "============================================================"
echo "  CivicSentinel Online: http://127.0.0.1:8000/"
echo "============================================================"
echo "  - Complete Tactical App: http://127.0.0.1:8000/"
echo "  - Dashboard Route:       http://127.0.0.1:8000/dashboard"
echo "  - OpenAPI / Swagger:     http://127.0.0.1:8000/docs"
echo "  - Health Diagnostics:    http://127.0.0.1:8000/health"
echo "  - Real-Time WebSocket:   ws://127.0.0.1:8000/ws"
echo ""
echo "Press Ctrl+C or run ./stop.sh in another terminal to stop."
echo "============================================================"
echo ""

exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
