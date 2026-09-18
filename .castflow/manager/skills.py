"""Runtime skill inventory, retire flags, and update-from-source.

Canonical store is `.castflow-runtime/skills/`. Adapter trees are mirrors.
Retire never deletes the runtime copy; sync skips retired names and removes
them from enabled adapter skill directories.
"""

from __future__ import print_function

import json
import os
import shutil

from .paths import (
    bootstrap_skill_src,
    ensure_runtime_layout,
    find_harness_dir,
    runtime_dir,
    runtime_path,
)

STATE_VERSION = 1

BOOTSTRAP_SKILL_NAME = "bootstrap-skill"

# Seeded from harness `.castflow/core/skills/`.
CORE_SKILL_DIRS = (
    "origin-evolve-skill",
    "skill-creator",
)

# Harness-level retire: never project, strip from runtime on sync.
HARNESS_RETIRED_SKILL_NAMES = (
    "code-pipeline-skill",
    "skill-forge",
)


def empty_state():
    return {"version": STATE_VERSION, "retired": []}


def _normalize_state(data):
    state = empty_state()
    if not isinstance(data, dict):
        return state
    retired = []
    seen = set()
    for name in data.get("retired") or []:
        name = str(name).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        retired.append(name)
    state["retired"] = retired
    state["version"] = STATE_VERSION
    return state


def load_state(project_root):
    path = runtime_path(project_root, "skills")
    if not os.path.isfile(path):
        return empty_state()
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return _normalize_state(data)
    except (json.JSONDecodeError, OSError):
        return empty_state()


def save_state(project_root, state):
    ensure_runtime_layout(project_root)
    path = runtime_path(project_root, "skills")
    payload = _normalize_state(state)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return payload


def retired_names(project_root):
    """User-retired + harness-retired skill directory names."""
    names = set(load_state(project_root).get("retired") or [])
    names.update(HARNESS_RETIRED_SKILL_NAMES)
    return names


def is_retired(project_root, name):
    return name in retired_names(project_root)


def core_skills_src():
    return os.path.join(find_harness_dir(), "core", "skills")


def _is_skill_dir(path):
    return os.path.isdir(path) and os.path.isfile(os.path.join(path, "SKILL.md"))


def skill_kind(name, project_root=None):
    if name == BOOTSTRAP_SKILL_NAME:
        return "bootstrap"
    core_dir = os.path.join(core_skills_src(), name)
    if _is_skill_dir(core_dir):
        return "core"
    return "project"


def source_dir_for(name, project_root):
    kind = skill_kind(name, project_root)
    if kind == "bootstrap":
        return bootstrap_skill_src()
    if kind == "core":
        return os.path.join(core_skills_src(), name)
    return os.path.join(runtime_dir(project_root), "skills", name)


def runtime_skill_dir(project_root, name):
    return os.path.join(runtime_dir(project_root), "skills", name)


def inventory(project_root):
    """Every skill directory in the canonical runtime store that has SKILL.md."""
    skills_root = os.path.join(runtime_dir(project_root), "skills")
    retired = retired_names(project_root)
    items = []
    if not os.path.isdir(skills_root):
        return items
    names = os.listdir(skills_root)
    names.sort()
    for name in names:
        if name.startswith("."):
            continue
        path = os.path.join(skills_root, name)
        if not _is_skill_dir(path):
            continue
        kind = skill_kind(name, project_root)
        src = source_dir_for(name, project_root)
        family = "framework" if kind in ("core", "bootstrap") else "project"
        items.append({
            "name": name,
            "kind": kind,
            "family": family,
            "retired": name in retired,
            "runtime_path": path.replace("\\", "/"),
            "source_path": src.replace("\\", "/"),
            "has_skill_md": True,
        })
    return items


def get_skill(project_root, name):
    for item in inventory(project_root):
        if item["name"] == name:
            return item
    return None


def retire(project_root, name):
    """Mark a named skill retired. Does not delete the runtime copy.

    Projection removal happens on the next sync.
    """
    if not name or not str(name).strip():
        return {"ok": False, "error": "missing skill name"}
    name = str(name).strip()
    item = get_skill(project_root, name)
    if item is None:
        return {"ok": False, "error": "unknown skill", "name": name}
    state = load_state(project_root)
    if name not in state["retired"]:
        state["retired"].append(name)
        save_state(project_root, state)
    return {
        "ok": True,
        "name": name,
        "retired": True,
        "kind": item["kind"],
    }


def restore(project_root, name):
    """Clear the retired flag so the next sync projects the skill again."""
    if not name or not str(name).strip():
        return {"ok": False, "error": "missing skill name"}
    name = str(name).strip()
    item = get_skill(project_root, name)
    if item is None:
        return {"ok": False, "error": "unknown skill", "name": name}
    state = load_state(project_root)
    if name in state["retired"]:
        state["retired"] = [n for n in state["retired"] if n != name]
        save_state(project_root, state)
    return {
        "ok": True,
        "name": name,
        "retired": False,
        "kind": item["kind"],
    }


def update_skill(project_root, name):
    """Refresh a named skill from its source of truth into the runtime store.

    Core skills come from CastFlow harness core; bootstrap-skill from the
    top-level bootstrap-skill pack; project skills already live in runtime.
    """
    if not name or not str(name).strip():
        return {"ok": False, "error": "missing skill name"}
    name = str(name).strip()
    item = get_skill(project_root, name)
    if item is None:
        return {"ok": False, "error": "unknown skill", "name": name}
    dest = runtime_skill_dir(project_root, name)
    src = source_dir_for(name, project_root)
    if not os.path.isdir(src):
        return {
            "ok": False,
            "error": "source missing",
            "name": name,
            "source": src.replace("\\", "/"),
        }
    src_abs = os.path.normcase(os.path.abspath(src))
    dest_abs = os.path.normcase(os.path.abspath(dest))
    if src_abs == dest_abs:
        return {
            "ok": True,
            "name": name,
            "kind": item["kind"],
            "updated": True,
            "noop": True,
            "path": dest.replace("\\", "/"),
        }
    _mirror_tree(src, dest)
    return {
        "ok": True,
        "name": name,
        "kind": item["kind"],
        "updated": True,
        "noop": False,
        "path": dest.replace("\\", "/"),
    }


def _copy_file(src, dst):
    parent = os.path.dirname(dst)
    if parent:
        os.makedirs(parent, exist_ok=True)
    shutil.copy2(src, dst)


def _mirror_tree(src, dst, skip_names=None):
    """Copy src -> dst file-by-file. Does not delete extra dest files."""
    skip_names = skip_names or set()
    if not os.path.isdir(src):
        return 0
    count = 0
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d not in skip_names and d != "__pycache__"]
        rel = os.path.relpath(dirpath, src)
        dest_dir = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(dest_dir, exist_ok=True)
        for fname in filenames:
            if fname.endswith(".pyc") or fname in skip_names:
                continue
            _copy_file(os.path.join(dirpath, fname), os.path.join(dest_dir, fname))
            count += 1
    return count
