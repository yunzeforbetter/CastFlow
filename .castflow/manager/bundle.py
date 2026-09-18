"""Copy the skill manager into `.castflow-runtime/` so the project is one folder."""

from __future__ import print_function

import os
import shutil
import stat

from .paths import (
    factory_root,
    find_harness_dir,
    is_factory_root,
    runtime_dir,
    _rmtree_nofollow,
)

COPY_NAMES = (
    "manager.py",
    "manager",
    "installer",
)

SKIP_DIR_NAMES = ("__pycache__",)
SKIP_FILE_SUFFIX = (".pyc", ".pyo")

PROJECT_BAT = """@echo off
setlocal EnableExtensions
title CastFlow
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\\" set "ROOT=%ROOT:~0,-1%"
set "MANAGER=%ROOT%\\.castflow-runtime\\manager.py"
if not exist "%MANAGER%" (
    echo CastFlow manager not found:
    echo   %MANAGER%
    echo Run the CastFlow checkout castflow.bat to cold-start this project.
    pause
    exit /b 1
)
echo Project: %ROOT%
echo Close this window to stop the console.
echo.
where py >nul 2>&1
if not errorlevel 1 (
    py -3 "%MANAGER%" --project-root "%ROOT%" ui
    goto after
)
where python >nul 2>&1
if not errorlevel 1 (
    python "%MANAGER%" --project-root "%ROOT%" ui
    goto after
)
where python3 >nul 2>&1
if not errorlevel 1 (
    python3 "%MANAGER%" --project-root "%ROOT%" ui
    goto after
)
echo Python 3 not found.
pause
exit /b 1
:after
if errorlevel 1 (
    echo.
    echo CastFlow exited with an error.
    pause
    exit /b 1
)
endlocal
"""

PROJECT_SH = """#!/usr/bin/env bash
# CastFlow project launcher (macOS / Linux / Git Bash).
ROOT="$(cd "$(dirname "$0")" && pwd)"
MANAGER="${ROOT}/.castflow-runtime/manager.py"
if [ ! -f "$MANAGER" ]; then
    echo "CastFlow manager not found:"
    echo "  $MANAGER"
    echo "Run the CastFlow checkout castflow.sh to cold-start this project."
    exit 1
fi
export PATH="/opt/homebrew/bin:/usr/local/bin:/Library/Frameworks/Python.framework/Versions/Current/bin:${HOME}/.local/bin:${HOME}/.pyenv/shims:${HOME}/.asdf/shims:${PATH}"
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
echo "Project: $ROOT"
echo "Close this window to stop the console."
echo
PY=""
if command -v python3 >/dev/null 2>&1; then
    PY="python3"
elif command -v python >/dev/null 2>&1; then
    PY="python"
fi
if [ -z "$PY" ]; then
    echo "Python 3 not found."
    exit 1
fi
exec "$PY" "$MANAGER" --project-root "$ROOT" ui
"""

PROJECT_COMMAND = """#!/usr/bin/env bash
# macOS Finder double-click entry. Same as castflow.sh.
cd "$(dirname "$0")"
exec bash "./castflow.sh" "$@"
"""

PROJECT_LAUNCHERS = ("castflow.bat", "castflow.sh", "castflow.command")


def _chmod_exec(path):
    try:
        mode = os.stat(path).st_mode
        os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass


def write_project_launchers(project_root):
    """Write Windows + POSIX launchers that open the project manager UI."""
    written = []
    bat_path = os.path.join(project_root, "castflow.bat")
    with open(bat_path, "w", encoding="ascii", newline="\r\n") as f:
        f.write(PROJECT_BAT)
    written.append(bat_path.replace("\\", "/"))
    sh_path = os.path.join(project_root, "castflow.sh")
    with open(sh_path, "w", encoding="ascii", newline="\n") as f:
        f.write(PROJECT_SH)
    _chmod_exec(sh_path)
    written.append(sh_path.replace("\\", "/"))
    cmd_path = os.path.join(project_root, "castflow.command")
    with open(cmd_path, "w", encoding="ascii", newline="\n") as f:
        f.write(PROJECT_COMMAND)
    _chmod_exec(cmd_path)
    written.append(cmd_path.replace("\\", "/"))
    return written


def remove_project_launchers(project_root):
    """Drop seed-written launchers. Returns removed paths (posix-slash)."""
    removed = []
    for name in PROJECT_LAUNCHERS:
        path = os.path.join(project_root, name)
        if not os.path.isfile(path):
            continue
        try:
            os.remove(path)
        except OSError:
            continue
        removed.append(path.replace("\\", "/"))
    return removed


def _copy_tree(src, dst):
    if os.path.isfile(src):
        parent = os.path.dirname(dst)
        if parent:
            os.makedirs(parent, exist_ok=True)
        shutil.copy2(src, dst)
        return 1
    count = 0
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        if name in SKIP_DIR_NAMES or name.endswith(SKIP_FILE_SUFFIX):
            continue
        count += _copy_tree(os.path.join(src, name), os.path.join(dst, name))
    return count


def remove_stale_project_harness(project_root):
    """Drop a leftover vendored `<project>/.castflow/` (not the factory checkout)."""
    dest = os.path.join(project_root, ".castflow")
    if not os.path.lexists(dest):
        return False
    try:
        if os.path.samefile(dest, find_harness_dir()):
            return False
    except OSError:
        pass
    from .paths import is_factory_checkout
    if is_factory_checkout(project_root):
        return False
    _rmtree_nofollow(dest)
    return True


def install_project_manager(project_root, dry_run=False):
    """Vendor manager + validate into `<project>/.castflow-runtime/` and write launchers."""
    if is_factory_root(project_root):
        return {"ok": False, "skipped": "factory"}
    harness = find_harness_dir()
    dest_root = runtime_dir(project_root)
    try:
        same = os.path.normcase(os.path.abspath(dest_root)) == os.path.normcase(
            os.path.abspath(harness))
    except OSError:
        same = False
    if same:
        return {"ok": False, "skipped": "same-harness"}
    copied = []
    if not dry_run:
        os.makedirs(dest_root, exist_ok=True)
        remove_stale_project_harness(project_root)
    for name in COPY_NAMES:
        src = os.path.join(harness, name)
        if not os.path.exists(src):
            continue
        dst = os.path.join(dest_root, name)
        copied.append(name)
        if not dry_run:
            _copy_tree(src, dst)
    bat_path = os.path.join(project_root, "castflow.bat")
    launchers = []
    if not dry_run:
        launchers = write_project_launchers(project_root)
    else:
        launchers = [
            os.path.join(project_root, name).replace("\\", "/")
            for name in PROJECT_LAUNCHERS
        ]
    return {
        "ok": True,
        "dest": dest_root.replace("\\", "/"),
        "bat": bat_path.replace("\\", "/"),
        "sh": os.path.join(project_root, "castflow.sh").replace("\\", "/"),
        "launchers": launchers,
        "copied": copied,
        "factory": (factory_root() or "").replace("\\", "/"),
    }
