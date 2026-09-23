"""Copy this module into a project runtime. Never copies or prints `key`."""

from __future__ import print_function

import os
import shutil

_SKIP_NAMES = frozenset(("key", "__pycache__", ".pyc"))
_SKIP_SUFFIXES = (".pyc", ".local")


def source_dir():
    return os.path.dirname(os.path.abspath(__file__))


def dest_dir(project_root):
    return os.path.join(project_root, ".castflow-runtime", "jev")


def _copy_module(src, dst):
    os.makedirs(dst, exist_ok=True)
    copied = []
    for name in sorted(os.listdir(src)):
        if name in _SKIP_NAMES or name.endswith(_SKIP_SUFFIXES):
            continue
        src_path = os.path.join(src, name)
        dst_path = os.path.join(dst, name)
        if os.path.isdir(src_path):
            if name == "__pycache__":
                continue
            copied.extend(_copy_module(src_path, dst_path))
            continue
        shutil.copy2(src_path, dst_path)
        copied.append(dst_path)
    return copied


def _remove_code(dst):
    """Drop the synced module but keep a local key file if the user wrote one."""
    if not os.path.isdir(dst):
        return False
    for name in list(os.listdir(dst)):
        if name == "key":
            continue
        path = os.path.join(dst, name)
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        else:
            try:
                os.remove(path)
            except OSError:
                pass
    return True


def sync_module(project_root, enabled, key=None, dry_run=False):
    """Install or remove the Jev module. `key` is written only to the key file."""
    dst = dest_dir(project_root)
    report = {"enabled": bool(enabled), "dest": dst.replace("\\", "/"), "copied": []}
    if not enabled:
        if not dry_run:
            report["removed"] = _remove_code(dst)
        return report
    if dry_run:
        report["copied"] = ["dry-run"]
        return report
    report["copied"] = [path.replace("\\", "/") for path in _copy_module(source_dir(), dst)]
    if key:
        from .mark import write_project_key
        report["key_written"] = bool(write_project_key(project_root, key))
    else:
        report["key_written"] = False
    return report
