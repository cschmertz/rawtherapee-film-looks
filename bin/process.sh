#!/bin/zsh
# Stable entry point; the implementation lives in Python for strict parsing,
# portable profile materialization, and actionable error reporting.
set -e
BIN="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$BIN/process.py" "$@"
