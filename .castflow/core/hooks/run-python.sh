#!/usr/bin/env bash
# CastFlow cross-platform Python resolver.
# Usage: run-python.sh <script-name> [args...]
# Resolves python3/python automatically across Linux, macOS, Windows(Git Bash).
# Stdin is passed through to the Python script.

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$HOOK_DIR/$1"
shift

if command -v python3 &>/dev/null; then
    exec python3 "$TARGET" "$@"
elif command -v python &>/dev/null; then
    exec python "$TARGET" "$@"
else
    exit 0
fi
