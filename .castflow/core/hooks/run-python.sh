#!/usr/bin/env bash
# CastFlow cross-platform Python resolver.
# Usage: run-python.sh <script-name> [args...]
# Resolves python3/python/py automatically across Linux, macOS, Windows(Git Bash).
# Stdin is passed through to the Python script.

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$HOOK_DIR/$1"
shift

if command -v python3 &>/dev/null; then
    exec python3 "$TARGET" "$@"
elif command -v python &>/dev/null; then
    exec python "$TARGET" "$@"
elif command -v py &>/dev/null; then
    exec py -3 "$TARGET" "$@"
else
    echo "Error: No Python interpreter found (tried python3, python, py)" >&2
    exit 1
fi
