"""Copy the skill manager into `.castflow-runtime/` so the project is one folder."""

from __future__ import print_function

import os
import shutil

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
    """Vendor manager + validate into `<project>/.castflow-runtime/` and write `castflow.bat`."""
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
    if not dry_run:
        with open(bat_path, "w", encoding="ascii", newline="\r\n") as f:
            f.write(PROJECT_BAT)
    return {
        "ok": True,
        "dest": dest_root.replace("\\", "/"),
        "bat": bat_path.replace("\\", "/"),
        "copied": copied,
        "factory": (factory_root() or "").replace("\\", "/"),
    }
