#!/usr/bin/env bash
# CivicSentinel Root Wrapper Stop Script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/CivicSentinel_Complete_Project"
exec ./stop.sh "$@"
