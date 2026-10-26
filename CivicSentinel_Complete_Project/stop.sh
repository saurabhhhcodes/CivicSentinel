#!/usr/bin/env bash
# ==============================================================================
# CivicSentinel — Process Shutdown Script
# ==============================================================================

echo "============================================================"
echo "  CivicSentinel — Stopping Processes on Port 8000"
echo "============================================================"

# Find PIDs on port 8000
PIDS=$(lsof -ti:8000 2>/dev/null || true)

if [ -n "$PIDS" ]; then
    echo "Terminating server process(es) on port 8000: $PIDS..."
    kill -15 $PIDS 2>/dev/null || true
    sleep 1
    # Force kill if still lingering
    REMAINING=$(lsof -ti:8000 2>/dev/null || true)
    if [ -n "$REMAINING" ]; then
        kill -9 $REMAINING 2>/dev/null || true
    fi
    echo "[OK] CivicSentinel stopped."
else
    echo "[INFO] No active process listening on port 8000."
fi
