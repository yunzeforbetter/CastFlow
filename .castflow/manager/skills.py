"""Runtime skill inventory, local disable flags, and update-from-source.

Framework skills live in `.castflow-runtime/skills/` and are replaced from
the factory on seed. Project skills live in `<project>/castflow-skills/`
and are not inside the tree `unseed` deletes. One `resolve_skill_dir`
picks the body of a name: a factory-owned name always uses the runtime
directory, and any same-named project directory is an ignored shadow.
Adapter trees are mirrors of that one body. Disable never deletes the
body; projection skips disabled names. The disable list is local
(gitignored). Skills not in that file are active.
"""

from __future__ import print_function

import json
import os
import shutil

from .paths import (
    ensure_runtime_layout,
    find_harness_dir,
    resolve_factory_harness,
    runtime_dir,
    runtime_path,
)

STATE_VERSION = 1

# Seeded from harness `.castflow/core/skills/`.
CORE_SKILL_DIRS = (
    "origin-evolve-skill",
    "skill-creator",
    "goal-loop-creator",
    "skill-doctor",
)

# Shown in cold-start / Skills console. Keep short; hosts scan description too.
CORE_SKILL_ROLES = {
    "skill-creator": "catalog four-file writer; stops before the eval loop",
    "origin-evolve-skill": "distills memory snapshots into approved skill rules",
    "goal-loop-creator": "long-task converter: requirement to a runnable loop-engine package",
    "skill-doctor": "evaluates and maintains existing skills against current project evidence",
}

# Harness-level retire: never project, strip from runtime on sync.
HARNESS_RETIRED_SKILL_NAMES = (
    "code-pipeline-skill",
    "skill-forge",
    "bootstrap-skill",
)

# Project-authored bodies. Not under `.castflow-runtime/` and not `.castflow/`.
PROJECT_SKILLS_DIRNAME = "castflow-skills"


def empty_state():
    return {"version": STATE_VERSION, "retired": []}


def _normalize_state(data):
    state = empty_state()
    if not isinstance(data, dict):
        return state
    retired = []
    seen = set()
    raw = data.get("disabled")
    if raw is None:
        raw = data.get("retired")
    for name in raw or []:
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
    normalized = _normalize_state(state)
    payload = {
        "version": STATE_VERSION,
        "disabled": list(normalized.get("retired") or []),
    }
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return normalized


def prune_missing_disabled(project_root):
    """Drop disable entries whose skill folder is gone. No-op if unchanged."""
    present = set(item["name"] for item in inventory(project_root))
    state = load_state(project_root)
    kept = [name for name in (state.get("retired") or []) if name in present]
    if kept == list(state.get("retired") or []):
        return state
    state["retired"] = kept
    return save_state(project_root, state)


def retired_names(project_root):
    """User-retired + harness-retired skill directory names."""
    names = set(load_state(project_root).get("retired") or [])
    names.update(HARNESS_RETIRED_SKILL_NAMES)
    return names


def is_retired(project_root, name):
    return name in retired_names(project_root)


def core_skills_src(project_root=None):
    factory = resolve_factory_harness(project_root)
    if factory:
        return os.path.join(factory, "core", "skills")
    return os.path.join(find_harness_dir(), "core", "skills")


def _is_skill_dir(path):
    return os.path.isdir(path) and os.path.isfile(os.path.join(path, "SKILL.md"))


def skill_kind(name, project_root=None):
    if name in CORE_SKILL_DIRS:
        return "core"
    core_dir = os.path.join(core_skills_src(project_root), name)
    if _is_skill_dir(core_dir):
        return "core"
    return "project"


def source_dir_for(name, project_root):
    kind = skill_kind(name, project_root)
    runtime_skill = runtime_skill_dir(project_root, name)
    if kind == "core":
        src = os.path.join(core_skills_src(project_root), name)
        return src if os.path.isdir(src) else runtime_skill
    return project_skill_dir(project_root, name)


def runtime_skill_dir(project_root, name):
    return os.path.join(runtime_dir(project_root), "skills", name)


def project_skills_root(project_root):
    """Directory of project-authored skills. Cold start does not delete it."""
    return os.path.join(project_root, PROJECT_SKILLS_DIRNAME)


def project_skill_dir(project_root, name):
    return os.path.join(project_skills_root(project_root), name)


def resolve_skill_dir(project_root, name):
    """Single body directory for `name`, or None.

    Factory-owned names resolve only to `.castflow-runtime/skills/<name>`
    when that directory has `SKILL.md`. Every other name resolves only to
    `castflow-skills/<name>/` when that directory has `SKILL.md`.
    """
    name = str(name or "").strip()
    if not name or name.startswith(".") or "/" in name or "\\" in name:
        return None
    if skill_kind(name, project_root) == "core":
        path = runtime_skill_dir(project_root, name)
    else:
        path = project_skill_dir(project_root, name)
    if _is_skill_dir(path):
        return path
    return None


def _skill_names_under(root):
    if not os.path.isdir(root):
        return []
    names = []
    try:
        entries = os.listdir(root)
    except OSError:
        return []
    for name in entries:
        if name.startswith(".") or name == "__pycache__":
            continue
        if _is_skill_dir(os.path.join(root, name)):
            names.append(name)
    return names


def inventory(project_root):
    """One row per resolved body. Factory names hide a same-named project dir."""
    retired = retired_names(project_root)
    runtime_names = set(_skill_names_under(
        os.path.join(runtime_dir(project_root), "skills")))
    project_names = set(_skill_names_under(project_skills_root(project_root)))
    items = []
    for name in sorted(runtime_names | project_names):
        body = resolve_skill_dir(project_root, name)
        if body is None:
            continue
        kind = skill_kind(name, project_root)
        src = source_dir_for(name, project_root)
        family = "framework" if kind == "core" else "project"
        role = CORE_SKILL_ROLES.get(name, "")
        item = {
            "name": name,
            "kind": kind,
            "family": family,
            "role": role,
            "retired": name in retired,
            "runtime_path": body.replace("\\", "/"),
            "body_path": body.replace("\\", "/"),
            "source_path": src.replace("\\", "/"),
            "has_skill_md": True,
        }
        if kind == "core" and name in project_names:
            item["collision"] = "ignored-project-shadow"
        items.append(item)
    return items


def get_skill(project_root, name):
    for item in inventory(project_root):
        if item["name"] == name:
            return item
    return None


def retire(project_root, name):
    """Disable a skill on this machine only. Does not delete the runtime copy.

    Projection removal happens on the next projection refresh / sync.
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


def _safe_skill_name(name):
    name = str(name or "").strip()
    if not name or name.startswith("."):
        return None
    if "/" in name or "\\" in name or name in (".", ".."):
        return None
    return name


def _file_inside(root, rel):
    """Absolute path for a relative skill file, or None if it escapes `root`."""
    text = str(rel or "").replace("\\", "/").strip()
    if not text or text.startswith("/") or text.endswith("/"):
        return None
    parts = [part for part in text.split("/") if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        return None
    full = os.path.abspath(os.path.join(root, *parts))
    root_abs = os.path.abspath(root)
    try:
        if os.path.commonpath([root_abs, full]) != root_abs:
            return None
    except ValueError:
        return None
    return full


def write_project_skill(project_root, name, files):
    """Create or update a project skill under `castflow-skills/<name>/`.

    Rejects factory-owned names. Does not copy bytes into
    `.castflow-runtime/` or an adapter tree. A later call updates only the
    named files and leaves the rest of the skill in place.
    """
    name = _safe_skill_name(name)
    if not name:
        return {"ok": False, "error": "bad skill name"}
    if skill_kind(name, project_root) == "core":
        return {"ok": False, "error": "factory-owned", "name": name}
    if not isinstance(files, dict) or not files:
        return {"ok": False, "error": "missing files", "name": name}
    dest = project_skill_dir(project_root, name)
    planned = []
    for raw, content in files.items():
        full = _file_inside(dest, raw)
        if full is None:
            return {"ok": False, "error": "bad path", "name": name, "path": str(raw)}
        if not isinstance(content, str):
            return {"ok": False, "error": "file must be text", "name": name}
        planned.append((full, content, str(raw).replace("\\", "/")))
    os.makedirs(dest, exist_ok=True)
    written = []
    for full, content, rel in planned:
        parent = os.path.dirname(full)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(full, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        written.append(rel)
    if not _is_skill_dir(dest):
        return {
            "ok": False,
            "error": "SKILL.md required",
            "name": name,
            "path": dest.replace("\\", "/"),
        }
    return {
        "ok": True,
        "name": name,
        "kind": "project",
        "path": dest.replace("\\", "/"),
        "files": written,
    }


def update_skill(project_root, name):
    """Refresh a framework skill from factory core into the runtime store.

    Project skills already live in `castflow-skills/`. Updating one is a
    no-op: their bytes are never copied into `.castflow-runtime/`.
    """
    if not name or not str(name).strip():
        return {"ok": False, "error": "missing skill name"}
    name = str(name).strip()
    item = get_skill(project_root, name)
    if item is None:
        return {"ok": False, "error": "unknown skill", "name": name}
    if item.get("kind") != "core":
        body = resolve_skill_dir(project_root, name) or project_skill_dir(
            project_root, name)
        return {
            "ok": True,
            "name": name,
            "kind": item["kind"],
            "updated": True,
            "noop": True,
            "path": body.replace("\\", "/"),
        }
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
