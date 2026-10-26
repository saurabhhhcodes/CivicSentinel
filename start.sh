#!/usr/bin/env bash
# CivicSentinel Root Wrapper for macOS / Linux / AWS EC2
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/CivicSentinel_Complete_Project"
exec ./start.sh "$@"
