"""Project runtime skills and hooks onto Claude / Grok / Codex / Cursor trees.

Skill discovery is projected only onto Claude (`.claude/skills`) and Codex
(`.agents/skills`). Grok and Cursor scan those locations and must not get a
second copy under `.grok/skills` or `.cursor/skills`. Hook JSON and
evolve-reminder files for Grok/Cursor are independent of skill trees.
"""

import json
import os
import re
import shutil
import stat
import subprocess
import sys

from .config import load_config
from .paths import (
    find_harness_dir,
    hooks_dir_for,
    resolve_factory_harness,
    runtime_dir,
)
from . import skills as skills_mod

ADAPTER_SKILL_DIRS = {
    "claude": os.path.join(".claude", "skills"),
    "grok": os.path.join(".grok", "skills"),
    "codex": os.path.join(".agents", "skills"),
    "cursor": os.path.join(".cursor", "skills"),
}

# Hosts that need a project skills directory of their own.
SKILL_DISCOVERY_ADAPTERS = ("claude", "codex")

# Grok/Cursor pick up Claude and/or .agents; extra trees here cause duplicate scans.
COMPAT_SKILL_DIRS = {
    "grok": os.path.join(".grok", "skills"),
    "cursor": os.path.join(".cursor", "skills"),
}

# Adapter skill trees are projections of `.castflow-runtime/skills/`. Ignore the
# whole directory (not per-skill): stable across add/retire, covers copy fallback.
GITIGNORE_BEGIN = "# BEGIN CASTFLOW GITIGNORE"
GITIGNORE_END = "# END CASTFLOW GITIGNORE"
GITIGNORE_BLOCK_LINES = (
    "# BEGIN CASTFLOW GITIGNORE (managed - do not edit)",
    "# Projections of .castflow-runtime/skills/. Do not commit symlinks/junctions/copies.",
    ".claude/skills/",
    ".agents/skills/",
    ".grok/skills/",
    ".cursor/skills/",
    "# Per-machine skill disable list. Missing file = every skill active.",
    ".castflow-runtime/skills-disabled.json",
    "# END CASTFLOW GITIGNORE",
)
PROJECTION_INDEX_PATHS = (
    ".claude/skills",
    ".agents/skills",
    ".grok/skills",
    ".cursor/skills",
)

CORE_SKILL_COPY = (
    "SKILL_ITERATION.md",
    "GLOBAL_SKILL_MEMORY.md",
    "MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md",
)

CORE_SKILL_DIRS = skills_mod.CORE_SKILL_DIRS
RETIRED_SKILL_DIRS = skills_mod.HARNESS_RETIRED_SKILL_NAMES


def _python_cmd():
    if os.name == "nt":
        return "py -3"
    return "python3"


def hook_script_ref(script_abs, project_root):
    """Path written into hook JSON.

    Use a project-relative path only when the script lives inside the project.
    CastFlow often sits in another folder or drive — then use an absolute path
    (Windows relpath across drives raises ValueError).
    """
    script_abs = os.path.abspath(script_abs)
    project_root = os.path.abspath(project_root)
    try:
        rel = os.path.relpath(script_abs, project_root)
    except ValueError:
        return script_abs.replace("\\", "/")
    if rel.startswith(".."):
        return script_abs.replace("\\", "/")
    return rel.replace("\\", "/")


def hook_commands(project_root):
    hooks_dir = hooks_dir_for(project_root)
    collector = hook_script_ref(
        os.path.join(hooks_dir, "trace-collector.py"), project_root)
    flush = hook_script_ref(
        os.path.join(hooks_dir, "trace-flush.py"), project_root)
    py = _python_cmd()
    return {
        "collector": '{} "{}"'.format(py, collector),
        "flush": '{} "{}"'.format(py, flush),
        "collector_rel": collector,
        "flush_rel": flush,
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


def _remove_tree(path):
    return _remove_entry(path)


def _is_reparse_point(path):
    if not os.path.lexists(path):
        return False
    if os.path.islink(path):
        return True
    try:
        attrs = os.lstat(path).st_file_attributes
    except (AttributeError, OSError):
        return False
    return bool(attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _remove_entry(path):
    """Remove a file, directory, symlink, or Windows junction without following it."""
    if not os.path.lexists(path):
        return False
    if os.path.islink(path):
        os.unlink(path)
        return True
    if _is_reparse_point(path):
        try:
            os.rmdir(path)
            return True
        except OSError:
            pass
    if os.path.isdir(path):
        shutil.rmtree(path)
        return True
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False


def _already_same(src, dst):
    try:
        return os.path.samefile(src, dst)
    except OSError:
        return False


def _try_symlink(src, dst):
    parent = os.path.dirname(dst)
    rel = os.path.relpath(src, parent)
    os.symlink(rel, dst, target_is_directory=True)
    return os.path.isdir(dst)


def _try_junction(src, dst):
    if os.name != "nt":
        return False
    src_abs = os.path.abspath(src)
    dst_abs = os.path.abspath(dst)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    rc = subprocess.call(
        ["cmd", "/c", "mklink", "/J", dst_abs, src_abs],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    return rc == 0 and os.path.isdir(dst)


def link_or_copy_skill(src, dst):
    """Point dst at src via relative symlink, Windows junction, or file copy.

    Returns 'link' or 'copy'. Replaces an existing dst first. Never follows a
    junction into the runtime store when replacing.
    """
    parent = os.path.dirname(dst)
    if parent:
        os.makedirs(parent, exist_ok=True)
    if os.path.lexists(dst):
        if _already_same(src, dst) and _is_reparse_point(dst):
            return "link"
        _remove_entry(dst)
    try:
        if _try_symlink(src, dst):
            return "link"
    except OSError:
        pass
    _remove_entry(dst)
    if _try_junction(src, dst):
        return "link"
    _remove_entry(dst)
    _mirror_tree(src, dst, skip_names={"__pycache__"})
    return "copy"



def _root_rules_template_path(project_root=None):
    candidates = []
    factory = resolve_factory_harness(project_root)
    if factory:
        candidates.append(os.path.join(
            factory, "core", "templates", "root", "ROOT_RULES.template.md"))
    if project_root:
        candidates.append(os.path.join(
            runtime_dir(project_root), "templates", "ROOT_RULES.template.md"))
    candidates.append(os.path.join(
        find_harness_dir(), "core", "templates", "root", "ROOT_RULES.template.md"))
    for path in candidates:
        if os.path.isfile(path):
            return path
    return candidates[0]


def _render_root_rules(evolution_on, project_root=None):
    path = _root_rules_template_path(project_root)
    with open(path, "r", encoding="utf-8-sig") as f:
        text = f.read()
    keep_evo = "evolution" if evolution_on else "no-evolution"
    drop_evo = "no-evolution" if evolution_on else "evolution"
    # Strip the inactive branch.
    text = _strip_if_block(text, drop_evo)
    text = _keep_if_block(text, keep_evo)
    return text


def _strip_if_block(text, tag):
    start = "<!-- if:{} -->".format(tag)
    end = "<!-- endif:{} -->".format(tag)
    while start in text and end in text:
        i = text.index(start)
        j = text.index(end, i) + len(end)
        # drop following newline
        if j < len(text) and text[j] == "\n":
            j += 1
        text = text[:i] + text[j:]
    return text


def _keep_if_block(text, tag):
    start = "<!-- if:{} -->".format(tag)
    end = "<!-- endif:{} -->".format(tag)
    text = text.replace(start + "\n", "")
    text = text.replace(start, "")
    text = text.replace(end + "\n", "")
    text = text.replace(end, "")
    return text


def _write_root_rules(project_root, evolution_on, adapters, dry_run):
    body = _render_root_rules(evolution_on, project_root=project_root)
    targets = []
    if adapters.get("claude") or adapters.get("grok"):
        targets.append(os.path.join(project_root, "CLAUDE.md"))
    if adapters.get("codex") or adapters.get("grok"):
        targets.append(os.path.join(project_root, "AGENTS.md"))
    # Always write both when any adapter is on — they are the same harness text.
    if not targets:
        targets = [
            os.path.join(project_root, "CLAUDE.md"),
            os.path.join(project_root, "AGENTS.md"),
        ]
    written = []
    for path in targets:
        if dry_run:
            written.append(path)
            continue
        # Seed-friendly: if file exists and has no CastFlow boundary, append
        # a pointer instead of clobbering.
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8-sig") as f:
                existing = f.read()
            if "CastFlow" in existing and "<!-- ==========" in existing:
                # Replace harness portion using the same boundary as installer.
                idx = existing.find("<!-- ==========")
                project_tail = existing[idx:]
                harness = body
                if "<!-- ==========" in harness:
                    harness = harness[: harness.find("<!-- ==========")]
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(harness.rstrip() + "\n\n" + project_tail.lstrip())
                written.append(path)
                continue
            if "CastFlow" in existing:
                written.append(path)
                continue
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
            if not body.endswith("\n"):
                f.write("\n")
        written.append(path)
    return written


def _sync_runtime_support(project_root, factory, dry_run):
    """Copy hooks, module-catalog, ROOT_RULES, evolve-reminder into runtime."""
    if dry_run or not factory:
        return
    rdir = runtime_dir(project_root)
    hooks_src = os.path.join(factory, "core", "hooks")
    if os.path.isdir(hooks_src):
        _mirror_tree(hooks_src, os.path.join(rdir, "hooks"), skip_names={"__pycache__"})
    for name in ("module-catalog.md", "evolve-reminder.md", "evolve-reminder.mdc"):
        src = os.path.join(factory, "core", "rules", name)
        if os.path.isfile(src):
            _copy_file(src, os.path.join(rdir, "rules", name))
    rules_src = os.path.join(
        factory, "core", "templates", "root", "ROOT_RULES.template.md")
    if os.path.isfile(rules_src):
        _copy_file(
            rules_src,
            os.path.join(rdir, "templates", "ROOT_RULES.template.md"),
        )


def _sync_core_into_runtime(project_root, evolution_on, dry_run):
    factory = resolve_factory_harness(project_root)
    dest_root = os.path.join(runtime_dir(project_root), "skills")
    if dry_run:
        return dest_root
    os.makedirs(dest_root, exist_ok=True)
    if not factory:
        return dest_root
    _sync_runtime_support(project_root, factory, dry_run)
    skills_src = os.path.join(factory, "core", "skills")
    for name in CORE_SKILL_COPY:
        src = os.path.join(skills_src, name)
        if os.path.isfile(src):
            _copy_file(src, os.path.join(dest_root, name))
    for dirname in CORE_SKILL_DIRS:
        if dirname == "origin-evolve-skill" and not evolution_on:
            _remove_tree(os.path.join(dest_root, dirname))
            continue
        src = os.path.join(skills_src, dirname)
        if os.path.isdir(src):
            _mirror_tree(src, os.path.join(dest_root, dirname))
    for retired in RETIRED_SKILL_DIRS:
        _remove_tree(os.path.join(dest_root, retired))
    proto_src = os.path.join(factory, "core", "protocols")
    proto_dst = os.path.join(runtime_dir(project_root), "protocols")
    if os.path.isdir(proto_src):
        _mirror_tree(proto_src, proto_dst)
    traces_src = os.path.join(factory, "core", "traces", "config")
    traces_dst = os.path.join(runtime_dir(project_root), "traces", "config")
    if os.path.isdir(traces_src):
        os.makedirs(traces_dst, exist_ok=True)
        for fname in ("limits.json", "hooks.config.json"):
            src = os.path.join(traces_src, fname)
            if os.path.isfile(src):
                _copy_file(src, os.path.join(traces_dst, fname))
    readme_src = os.path.join(factory, "core", "traces", "README.md")
    if os.path.isfile(readme_src):
        _copy_file(readme_src, os.path.join(runtime_dir(project_root), "traces", "README.md"))
    return dest_root


def _skip_projection_names(project_root, evolution_on):
    """Skill directory names that must not appear in adapter trees."""
    skip = set(skills_mod.retired_names(project_root))
    if not evolution_on:
        skip.add("origin-evolve-skill")
    skip.update(RETIRED_SKILL_DIRS)
    return skip


def _iter_runtime_skill_dirs(src):
    if not os.path.isdir(src):
        return
    for entry in os.listdir(src):
        if entry == "__pycache__":
            continue
        src_path = os.path.join(src, entry)
        if os.path.isdir(src_path) and os.path.isfile(
                os.path.join(src_path, "SKILL.md")):
            yield entry, src_path


def _strip_compat_skill_trees(project_root, names, dry_run):
    """Drop CastFlow skill dirs from Grok/Cursor so those hosts cannot scan extra copies."""
    stripped = {}
    for key, rel in COMPAT_SKILL_DIRS.items():
        dest = os.path.join(project_root, rel)
        removed = []
        if os.path.isdir(dest):
            for name in names:
                path = os.path.join(dest, name)
                if os.path.lexists(path):
                    if not dry_run:
                        _remove_entry(path)
                    removed.append(name)
        stripped[key] = {"path": dest, "removed": removed}
    return stripped


def _project_skills(project_root, adapters, dry_run, evolution_on=True):
    src = os.path.join(runtime_dir(project_root), "skills")
    skip = _skip_projection_names(project_root, evolution_on)
    all_names = [name for name, _ in _iter_runtime_skill_dirs(src)]
    projected = {}
    for key in SKILL_DISCOVERY_ADAPTERS:
        rel = ADAPTER_SKILL_DIRS[key]
        dest = os.path.join(project_root, rel)
        if not adapters.get(key):
            projected[key] = {"enabled": False, "path": dest, "skills": []}
            continue
        written = []
        for entry, src_path in _iter_runtime_skill_dirs(src):
            dest_path = os.path.join(dest, entry)
            if entry in skip:
                if not dry_run:
                    _remove_entry(dest_path)
                continue
            if not dry_run:
                link_or_copy_skill(src_path, dest_path)
            written.append(entry)
        if not dry_run:
            wanted = set(written)
            if os.path.isdir(dest):
                try:
                    existing = os.listdir(dest)
                except OSError:
                    existing = []
                for entry in existing:
                    if entry in wanted or entry == "__pycache__":
                        continue
                    _remove_entry(os.path.join(dest, entry))
        projected[key] = {"enabled": True, "path": dest, "skills": written}
    for key, rel in COMPAT_SKILL_DIRS.items():
        dest = os.path.join(project_root, rel)
        projected[key] = {
            "enabled": False,
            "path": dest,
            "skills": [],
            "compat_scan": True,
        }
    projected["_compat_stripped"] = _strip_compat_skill_trees(
        project_root, all_names + list(skip), dry_run)
    return projected


def _write_json(path, data, dry_run):
    if dry_run:
        return
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _merge_claude_settings(project_root, evolution_on, cmds, dry_run):
    path = os.path.join(project_root, ".claude", "settings.json")
    data = {"hooks": {}}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                data = loaded
        except (json.JSONDecodeError, OSError):
            pass
    data.setdefault("hooks", {})
    if evolution_on:
        data["hooks"]["PostToolUse"] = [{
            "matcher": "Edit|MultiEdit|Write|search_replace",
            "hooks": [{"type": "command", "command": cmds["collector"]}],
        }]
        data["hooks"]["Stop"] = [{
            "hooks": [{"type": "command", "command": cmds["flush"]}],
        }]
        _write_json(path, data, dry_run)
    else:
        # Drop CastFlow hook entries; keep unrelated hooks.
        changed = _strip_castflow_hooks(data.get("hooks") or {})
        if changed:
            _write_json(path, data, dry_run)
    return path


def _strip_castflow_hooks(hooks):
    changed = False
    markers = ("trace-collector.py", "trace-flush.py")
    for event, entries in list(hooks.items()):
        if not isinstance(entries, list):
            continue
        kept = []
        for entry in entries:
            blob = json.dumps(entry)
            if any(m in blob for m in markers):
                changed = True
                continue
            kept.append(entry)
        hooks[event] = kept
    return changed


def _write_grok_hooks(project_root, evolution_on, cmds, dry_run):
    path = os.path.join(project_root, ".grok", "hooks", "castflow.json")
    if not evolution_on:
        if os.path.isfile(path) and not dry_run:
            os.remove(path)
        return path
    data = {
        "hooks": {
            "PostToolUse": [{
                "matcher": "search_replace|Write|Edit|MultiEdit",
                "hooks": [{"type": "command", "command": cmds["collector"], "timeout": 15}],
            }],
            "Stop": [{
                "hooks": [{"type": "command", "command": cmds["flush"], "timeout": 30}],
            }],
        }
    }
    _write_json(path, data, dry_run)
    return path


def _merge_cursor_hooks(project_root, evolution_on, cmds, dry_run):
    path = os.path.join(project_root, ".cursor", "hooks.json")
    data = {"version": 1, "hooks": {}}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                data = loaded
        except (json.JSONDecodeError, OSError):
            pass
    data.setdefault("hooks", {})
    if evolution_on:
        data["hooks"]["afterFileEdit"] = [{"command": cmds["collector"]}]
        data["hooks"]["stop"] = [{"command": cmds["flush"]}]
        _write_json(path, data, dry_run)
    else:
        if _strip_castflow_hooks(data.get("hooks") or {}):
            _write_json(path, data, dry_run)
    return path


def _write_evolve_reminder(project_root, adapters, evolution_on, dry_run):
    factory = resolve_factory_harness(project_root)
    rdir = runtime_dir(project_root)
    src_md = ""
    src_mdc = ""
    if factory:
        src_md = os.path.join(factory, "core", "rules", "evolve-reminder.md")
        src_mdc = os.path.join(factory, "core", "rules", "evolve-reminder.mdc")
    if not os.path.isfile(src_md):
        src_md = os.path.join(rdir, "rules", "evolve-reminder.md")
        src_mdc = os.path.join(rdir, "rules", "evolve-reminder.mdc")
    if not os.path.isfile(src_md):
        return []
    written = []
    mapping = []
    if adapters.get("claude"):
        mapping.append((src_md, os.path.join(
            project_root, ".claude", "rules", "evolve-reminder.md")))
    if adapters.get("grok"):
        mapping.append((src_md, os.path.join(
            project_root, ".grok", "rules", "evolve-reminder.md")))
    if adapters.get("cursor") and os.path.isfile(src_mdc):
        mapping.append((src_mdc, os.path.join(
            project_root, ".cursor", "rules", "evolve-reminder.mdc")))
    for src, dest in mapping:
        if evolution_on:
            if not dry_run:
                _copy_file(src, dest)
            written.append(dest)
        else:
            if os.path.isfile(dest) and not dry_run:
                os.remove(dest)
    return written


def _normalize_newlines(text):
    return (text or "").replace("\r\n", "\n").replace("\r", "\n")


def _detect_newline(text):
    if text and "\r\n" in text:
        return "\r\n"
    return "\n"


def gitignore_block_text():
    return "\n".join(GITIGNORE_BLOCK_LINES) + "\n"


def upsert_gitignore_block(existing):
    """Insert or replace the managed CastFlow block. Preserves surrounding text."""
    block = gitignore_block_text()
    text = existing or ""
    nl = _detect_newline(text)
    body = _normalize_newlines(text)
    pattern = re.compile(
        re.escape(GITIGNORE_BEGIN) + r".*?" + re.escape(GITIGNORE_END) + r"(?:\n)?",
        re.DOTALL,
    )
    if GITIGNORE_BEGIN in body and pattern.search(body):
        updated = pattern.sub(block, body, count=1)
    else:
        stripped = body.rstrip("\n")
        if stripped:
            updated = stripped + "\n\n" + block
        else:
            updated = block
    if not updated.endswith("\n"):
        updated += "\n"
    if nl == "\r\n":
        return updated.replace("\n", "\r\n")
    return updated


def ensure_projection_gitignore(project_root, dry_run=False):
    """Keep a stable ignore block for adapter skill trees in the project `.gitignore`.

    Idempotent: does not rewrite when the managed block is already correct.
    Does not list individual skills — add/retire must not dirty `.gitignore`.
    """
    path = os.path.join(project_root, ".gitignore")
    existing = ""
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig") as f:
            existing = f.read()
    updated = upsert_gitignore_block(existing)
    changed = _normalize_newlines(existing) != _normalize_newlines(updated)
    report = {
        "path": path.replace("\\", "/"),
        "changed": changed,
        "dry_run": bool(dry_run),
    }
    if dry_run or not changed:
        return report
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(updated)
    return report


def _git_creationflags():
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def _run_git(project_root, args):
    git = shutil.which("git")
    if not git:
        return None, "", "git not found"
    flags = _git_creationflags()
    try:
        proc = subprocess.Popen(
            [git, "-C", project_root] + list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=flags,
        )
        out, err = proc.communicate()
    except OSError as exc:
        return None, "", str(exc)
    stdout = (out or b"").decode("utf-8", "replace")
    stderr = (err or b"").decode("utf-8", "replace")
    return proc.returncode, stdout, stderr


def untrack_projection_paths(project_root, dry_run=False):
    """Drop already-indexed projection paths without deleting the working tree.

    `.gitignore` does not affect tracked files. Junctions previously added as
    regular directories stay in the index until `git rm --cached`.
    """
    git_meta = os.path.join(project_root, ".git")
    if not os.path.lexists(git_meta):
        return {"skipped": True, "reason": "not a git repo", "removed": []}
    code, listed, err = _run_git(
        project_root, ["ls-files", "-z", "--"] + list(PROJECTION_INDEX_PATHS))
    if code is None:
        return {"skipped": True, "reason": err or "git not found", "removed": []}
    if code != 0:
        return {
            "skipped": True,
            "reason": (err or "git ls-files failed").strip() or "git ls-files failed",
            "removed": [],
        }
    tracked = [p for p in listed.split("\0") if p]
    if not tracked:
        return {"skipped": False, "removed": []}
    report = {
        "skipped": False,
        "removed": tracked,
        "dry_run": bool(dry_run),
        "count": len(tracked),
    }
    if dry_run:
        return report
    rm_code, _out, rm_err = _run_git(
        project_root,
        ["rm", "-r", "-f", "--cached", "--ignore-unmatch", "--quiet", "--"]
        + list(PROJECTION_INDEX_PATHS),
    )
    if rm_code is None:
        report["error"] = rm_err or "git not found"
    elif rm_code != 0:
        report["error"] = (rm_err or "git rm --cached failed").strip()
    return report


def refresh_projections(project_root, dry_run=False):
    """Re-link adapter skill trees from runtime. Does not refresh framework sources.

    New skills (not in the local disable list) are projected. Disabled and
    deleted skills are removed from `.claude/skills` and `.agents/skills`.
    """
    from .paths import reject_factory_runtime
    reject_factory_runtime(project_root)
    dest_root = os.path.join(runtime_dir(project_root), "skills")
    for retired in RETIRED_SKILL_DIRS:
        _remove_tree(os.path.join(dest_root, retired))
    skills_mod.prune_missing_disabled(project_root)
    config = load_config(project_root)
    adapters = config.get("adapters") or {}
    evolution_on = bool(config.get("evolution", {}).get("enabled", True))
    return {
        "evolution": evolution_on,
        "dry_run": dry_run,
        "retired": sorted(skills_mod.retired_names(project_root)),
        "gitignore": ensure_projection_gitignore(project_root, dry_run=dry_run),
        "projected": _project_skills(
            project_root, adapters, dry_run, evolution_on=evolution_on),
    }


def adapter_status(project_root):
    config = load_config(project_root)
    adapters = config.get("adapters") or {}
    evo = bool(config.get("evolution", {}).get("enabled", True))
    status = {
        "evolution": evo,
        "adapters": {},
        "runtime": runtime_dir(project_root),
    }
    for key, rel in ADAPTER_SKILL_DIRS.items():
        dest = os.path.join(project_root, rel)
        status["adapters"][key] = {
            "wanted": bool(adapters.get(key, True)),
            "skills_dir_exists": os.path.isdir(dest),
            "path": dest.replace("\\", "/"),
        }
    return status


def sync(project_root, config=None, dry_run=False):
    """Full projection. Safe to call after seed, evolve toggle, or skill-creator."""
    from .paths import reject_factory_runtime
    reject_factory_runtime(project_root)
    if config is None:
        config = load_config(project_root)
    adapters = config.get("adapters") or {}
    evolution_on = bool(config.get("evolution", {}).get("enabled", True))

    report = {
        "evolution": evolution_on,
        "dry_run": dry_run,
        "python": sys.executable,
    }

    report["runtime_skills"] = _sync_core_into_runtime(project_root, evolution_on, dry_run)
    cmds = hook_commands(project_root)
    report["inventory"] = skills_mod.inventory(project_root)
    report["retired"] = sorted(skills_mod.retired_names(project_root))
    report["projected"] = _project_skills(
        project_root, adapters, dry_run, evolution_on=evolution_on)
    report["gitignore"] = ensure_projection_gitignore(project_root, dry_run=dry_run)
    report["untracked"] = untrack_projection_paths(project_root, dry_run=dry_run)
    report["root_rules"] = _write_root_rules(project_root, evolution_on, adapters, dry_run)

    if adapters.get("claude"):
        report["claude_settings"] = _merge_claude_settings(
            project_root, evolution_on, cmds, dry_run)
    if adapters.get("grok"):
        report["grok_hooks"] = _write_grok_hooks(project_root, evolution_on, cmds, dry_run)
    if adapters.get("cursor"):
        report["cursor_hooks"] = _merge_cursor_hooks(
            project_root, evolution_on, cmds, dry_run)
    report["reminders"] = _write_evolve_reminder(
        project_root, adapters, evolution_on, dry_run)
    return report


def seed(project_root, dry_run=False):
    """Minimal first-run: runtime layout + bootstrap-skill discovery + short rules."""
    from .config import save_config, load_config
    from .paths import (
        ensure_runtime_layout,
        reject_factory_runtime,
        scrub_factory_runtime,
    )

    reject_factory_runtime(project_root)
    ensure_runtime_layout(project_root)
    config = load_config(project_root)
    from .paths import factory_root
    factory = factory_root()
    if factory:
        try:
            rel = os.path.relpath(factory, project_root)
            config["castflow_home"] = rel.replace("\\", "/")
        except ValueError:
            config["castflow_home"] = factory.replace("\\", "/")
    bundled = None
    if not dry_run:
        save_config(project_root, config)
        from .bundle import install_project_manager
        bundled = install_project_manager(project_root)
    report = sync(project_root, config=config, dry_run=dry_run)
    if not dry_run:
        report["manager"] = bundled
        report["factory_runtime_removed"] = scrub_factory_runtime()
    return report
