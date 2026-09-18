"""catalog.json: scanned modules + user edits + skill generation state."""

import json
import os
from datetime import datetime, timezone

from .paths import ensure_runtime_layout, runtime_path

CATALOG_VERSION = 1

MODULE_STATUSES = ("candidate", "accepted", "rejected")
SKILL_STATES = ("none", "queued", "ready", "failed")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def empty_catalog():
    return {
        "version": CATALOG_VERSION,
        "scanned_at": "",
        "tech_stack": [],
        "source_roots": [],
        "modules": [],
        "core_skills": {
            "architect": {"enabled": True, "skill_state": "none"},
            "debug": {"enabled": False, "skill_state": "none"},
            "profiler": {"enabled": False, "skill_state": "none"},
        },
    }


def _normalize_module(mod):
    if not isinstance(mod, dict):
        return None
    module_id = str(mod.get("id") or "").strip()
    if not module_id:
        return None
    status = mod.get("status") if mod.get("status") in MODULE_STATUSES else "candidate"
    skill_state = mod.get("skill_state") if mod.get("skill_state") in SKILL_STATES else "none"
    paths = mod.get("paths") or []
    if not isinstance(paths, list):
        paths = [str(paths)]
    paths = [p.replace("\\", "/") for p in paths if p]
    notes = mod.get("notes") if isinstance(mod.get("notes"), str) else ""
    return {
        "id": module_id,
        "name": str(mod.get("name") or module_id),
        "role": str(mod.get("role") or ""),
        "paths": paths,
        "path_glob": str(mod.get("path_glob") or ""),
        "notes": notes,
        "status": status,
        "skill_state": skill_state,
        "file_count": int(mod.get("file_count") or 0),
        "languages": list(mod.get("languages") or []),
        "sample_symbols": list(mod.get("sample_symbols") or []),
        "sample_files": list(mod.get("sample_files") or []),
        "confidence": float(mod.get("confidence") or 0),
        "stale": bool(mod.get("stale", False)),
        "reject_reason": str(mod.get("reject_reason") or ""),
    }


def _normalize_catalog(data):
    catalog = empty_catalog()
    if not isinstance(data, dict):
        return catalog
    catalog["scanned_at"] = str(data.get("scanned_at") or "")
    catalog["tech_stack"] = list(data.get("tech_stack") or [])
    catalog["source_roots"] = list(data.get("source_roots") or [])
    seen = set()
    modules = []
    for raw in data.get("modules") or []:
        mod = _normalize_module(raw)
        if not mod or mod["id"] in seen:
            continue
        seen.add(mod["id"])
        modules.append(mod)
    catalog["modules"] = modules
    core = catalog["core_skills"]
    incoming = data.get("core_skills") or {}
    for key in core:
        src = incoming.get(key) or {}
        if isinstance(src, dict):
            core[key]["enabled"] = bool(src.get("enabled", core[key]["enabled"]))
            state = src.get("skill_state")
            if state in SKILL_STATES:
                core[key]["skill_state"] = state
    catalog["version"] = CATALOG_VERSION
    return catalog


def load_catalog(project_root):
    path = runtime_path(project_root, "catalog")
    if not os.path.isfile(path):
        return empty_catalog()
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return _normalize_catalog(data)
    except (json.JSONDecodeError, OSError):
        return empty_catalog()


def save_catalog(project_root, catalog):
    ensure_runtime_layout(project_root)
    path = runtime_path(project_root, "catalog")
    payload = _normalize_catalog(catalog)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return payload


def merge_scan(existing, scanned):
    """Refresh scan results while preserving user edits.

    Kept on existing modules: name, role, notes, status, skill_state.
    Updated from scan: paths, file_count, languages, samples, confidence.
    New ids become candidate. Missing ids that were accepted stay, marked stale.
    """
    existing = _normalize_catalog(existing)
    scanned = _normalize_catalog(scanned)
    by_id = dict((m["id"], m) for m in existing["modules"])
    merged = []
    seen = set()

    for fresh in scanned["modules"]:
        seen.add(fresh["id"])
        old = by_id.get(fresh["id"])
        if old:
            fresh["name"] = old["name"] or fresh["name"]
            if old["role"]:
                fresh["role"] = old["role"]
            fresh["notes"] = old["notes"]
            fresh["status"] = old["status"]
            fresh["skill_state"] = old["skill_state"]
            fresh["stale"] = False
            fresh["reject_reason"] = old["reject_reason"] if old["status"] == "rejected" else ""
        merged.append(fresh)

    for old in existing["modules"]:
        if old["id"] in seen:
            continue
        if old["status"] == "accepted" or old["skill_state"] in ("queued", "ready"):
            old["stale"] = True
            merged.append(old)

    scanned["modules"] = merged
    scanned["scanned_at"] = scanned.get("scanned_at") or _now()
    # Preserve core_skills enablement from existing catalog
    for key, val in existing["core_skills"].items():
        if key in scanned["core_skills"]:
            scanned["core_skills"][key]["enabled"] = val["enabled"]
            scanned["core_skills"][key]["skill_state"] = val["skill_state"]
    return scanned


def patch_module(catalog, module_id, fields):
    catalog = _normalize_catalog(catalog)
    for mod in catalog["modules"]:
        if mod["id"] != module_id:
            continue
        if "name" in fields and fields["name"] is not None:
            mod["name"] = str(fields["name"]).strip() or mod["name"]
        if "role" in fields and fields["role"] is not None:
            mod["role"] = str(fields["role"])
        if "notes" in fields and fields["notes"] is not None:
            mod["notes"] = str(fields["notes"])
        if "paths" in fields and fields["paths"] is not None:
            paths = fields["paths"]
            if isinstance(paths, str):
                paths = [p.strip() for p in paths.replace(";", ",").split(",") if p.strip()]
            mod["paths"] = [p.replace("\\", "/") for p in paths]
        if "status" in fields and fields["status"] in MODULE_STATUSES:
            mod["status"] = fields["status"]
            if mod["status"] != "rejected":
                mod["reject_reason"] = ""
        if "skill_state" in fields and fields["skill_state"] in SKILL_STATES:
            mod["skill_state"] = fields["skill_state"]
        return catalog, mod
    return catalog, None
