#!/usr/bin/env bash
# CastFlow factory launcher (macOS / Linux / Git Bash).
# Double-click castflow.command on macOS, or run: bash castflow.sh
# Optional: bash castflow.sh /path/to/project
# Optional: bash castflow.sh -y /path/to/project   (-y is ignored; kept for bat parity)

CASTFLOW_HOME="$(cd "$(dirname "$0")" && pwd)"
MANAGER="${CASTFLOW_HOME}/.castflow/manager.py"

if [ ! -f "$MANAGER" ]; then
    echo "CastFlow manager not found:"
    echo "  $MANAGER"
    echo "Place this script next to the .castflow folder."
    exit 1
fi

PROJECT=""
if [ "${1-}" = "-y" ]; then
    shift
fi
if [ -n "${1-}" ]; then
    PROJECT="$1"
fi

# Finder-launched .command files get a minimal PATH. Prepend common Python locations.
export PATH="/opt/homebrew/bin:/usr/local/bin:/Library/Frameworks/Python.framework/Versions/Current/bin:${HOME}/.local/bin:${HOME}/.pyenv/shims:${HOME}/.asdf/shims:${PATH}"
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

echo
echo "CastFlow launcher"
if [ -n "$PROJECT" ]; then
    echo "Project: $PROJECT"
else
    echo "A folder picker will open. Choose your game/app folder."
    echo "CastFlow does not need to live inside that folder."
fi
echo "Close this window to stop the console."
echo

PY=""
if command -v python3 >/dev/null 2>&1; then
    PY="python3"
elif command -v python >/dev/null 2>&1; then
    PY="python"
fi

if [ -z "$PY" ]; then
    echo "Python 3 not found. Install Python 3 from python.org or Homebrew"
    echo "(brew install python) and retry. If python3 exists but tkinter is missing,"
    echo "the macOS folder picker still works via osascript."
    exit 1
fi

if [ -n "$PROJECT" ]; then
    exec "$PY" "$MANAGER" --project-root "$PROJECT" launch --from-harness "$CASTFLOW_HOME"
fi
exec "$PY" "$MANAGER" launch --from-harness "$CASTFLOW_HOME"
