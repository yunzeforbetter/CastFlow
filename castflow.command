#!/usr/bin/env bash
# macOS Finder double-click entry. Same cold start as castflow.sh.
cd "$(dirname "$0")"
exec bash "./castflow.sh" "$@"
