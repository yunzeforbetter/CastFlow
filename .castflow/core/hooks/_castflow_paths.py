"""Locate CastFlow runtime from a hook process (cwd-based, no vendor vars)."""

import json
import os

RUNTIME_NAME = ".castflow-runtime"


def find_project_root(start=None):
    if start is None:
        start = os.getcwd()
    candidate = os.path.abspath(start)
    for _ in range(12):
        if os.path.isdir(os.path.join(candidate, RUNTIME_NAME)):
            return candidate
        if os.path.isdir(os.path.join(candidate, ".git")):
            return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent
    return os.path.abspath(start)


def runtime_dir(project_root=None):
    if project_root is None:
        project_root = find_project_root()
    return os.path.join(project_root, RUNTIME_NAME)


def load_runtime_config(project_root=None):
    path = os.path.join(runtime_dir(project_root), "config.json")
    if not os.path.isfile(path):
        return {"evolution": {"enabled": True}}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"evolution": {"enabled": True}}


def evolution_enabled(project_root=None):
    cfg = load_runtime_config(project_root)
    return bool(cfg.get("evolution", {}).get("enabled", True))
