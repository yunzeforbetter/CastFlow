"""Cold-start: apply GUI config, then seed + sync. No AI required."""

from __future__ import print_function

import json
import os
import subprocess
import sys

from . import adapters, catalog, config, queue, skills
from .paths import find_harness_dir, find_project_root, runtime_dir

LAUNCH_GUIDE = """
========================================
CastFlow cold start
========================================

[1] Configure  language, adapters, evolution
[2] Optional   check "scan modules and generate skills"
[3] Click      开启冷启动  (write .castflow-runtime/ only)
[4] If checked, paste the prompt (yours or the default) into the AI

Unchecked = install only into .castflow-runtime/. No AI prompt.
Checked = AI scans the whole project (any language) and generates skills.
You can edit the prompt; leave it empty to use the built-in one.
The project does not get a copy of .castflow/. Domain templates are gone.
Already installed? Use 回退冷启动 to start over without deleting source by hand.

Later: open this launcher for the manager (framework / skills / queue).
"""


def print_launch_guide(seeded=False):
    import sys
    text = LAUNCH_GUIDE
    if seeded:
        text = text + "\nThis project is already seeded. Opening the manager.\n"
    else:
        text = text + "\nThis project is not seeded yet. Opening the wizard.\n"
    try:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        buf = getattr(sys.stdout, "buffer", None)
        payload = text.encode(enc, "replace")
        if buf is not None:
            buf.write(payload)
            buf.flush()
        else:
            sys.stdout.write(payload.decode(enc, "replace"))
            sys.stdout.flush()



def is_castflow_checkout(path):
    from .paths import is_factory_checkout
    return is_factory_checkout(path)


def pick_project_directory(initial=None, title=None):
    """Open a native folder dialog. Returns an absolute path, or None if cancelled."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pick_dir.py")
    initial = os.path.abspath(initial) if initial else os.getcwd()
    title = title or "Select project folder"
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.Popen(
            [sys.executable, script, initial, title],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        out, _err = proc.communicate()
    except OSError:
        return None
    if proc.returncode not in (0, None):
        return None
    text = (out or b"").decode("utf-8", "replace").strip()
    if not text:
        return None
    path = os.path.abspath(text)
    if not os.path.isdir(path):
        return None
    return path


def is_git_submodule(path):
    git = os.path.join(path, ".git")
    return os.path.isfile(git)


def looks_like_host_project(path):
    """True when path looks like a game/app repo, not the CastFlow checkout."""
    if not path or not os.path.isdir(path):
        return False
    if is_castflow_checkout(path):
        return False
    try:
        names = os.listdir(path)
    except OSError:
        return False
    lower = set(n.lower() for n in names)
    dir_markers = (
        "src", "assets", "projectsettings", "app", "apps", "lib",
        "packages", "scripts", "source", "runtime",
    )
    if any(n in lower for n in dir_markers):
        return True
    file_markers = (
        "pyproject.toml", "package.json", "cargo.toml", "go.mod",
        "pubspec.yaml", "setup.py", "requirements.txt",
    )
    if any(n in lower for n in file_markers):
        return True
    for name in names:
        ln = name.lower()
        if ln.endswith(".sln") or ln.endswith(".csproj") or ln.endswith(".unity"):
            return True
    return False


def is_seeded(project_root):
    skills = os.path.join(runtime_dir(project_root), "skills")
    return os.path.isfile(os.path.join(skills, "skill-creator", "SKILL.md"))


def resolve_launch_root(explicit=None, harness_checkout=None, start=None):
    """Project root for the bat / launch GUI.

    Submodule checkout (`.git` is a file) -> parent host project.
    Full clone -> this checkout (or an already-seeded runtime above cwd).
    Explicit --project-root always wins.
    """
    if explicit:
        return os.path.abspath(explicit)

    checkout = harness_checkout
    if not checkout:
        checkout = os.path.dirname(find_harness_dir())
    checkout = os.path.abspath(checkout)

    if is_castflow_checkout(checkout):
        parent = os.path.dirname(checkout)
        if parent and parent != checkout and looks_like_host_project(parent):
            return parent
        if is_git_submodule(checkout) and parent and parent != checkout:
            return parent

    return find_project_root(explicit_root=None, start=start)


def apply_setup_options(project_root, options):
    """Write language / adapters / evolution / optional_skills into config.json."""
    options = options or {}
    cfg = config.load_config(project_root)
    language = options.get("language")
    if language:
        raw = str(language).strip()
        cfg["language"] = (
            config.normalize_language(raw) if raw
            else (cfg.get("language") or "en")
        )
    adapters_in = options.get("adapters")
    if isinstance(adapters_in, dict):
        cfg.setdefault("adapters", {}).update(
            dict((k, bool(v)) for k, v in adapters_in.items())
        )
    evo = options.get("evolution")
    if evo is not None:
        if isinstance(evo, dict):
            enabled = bool(evo.get("enabled", True))
        else:
            enabled = bool(evo)
        cfg.setdefault("evolution", {})["enabled"] = enabled
    optional = options.get("optional_skills")
    if isinstance(optional, dict):
        cfg.setdefault("optional_skills", {}).update(
            dict((k, bool(v)) for k, v in optional.items())
        )
    if "generate_skills" in options:
        cfg["generate_skills"] = bool(options.get("generate_skills"))
    if "jev_enabled" in options:
        cfg["jev_enabled"] = bool(options.get("jev_enabled"))
    cfg.pop("jev_key", None)
    cfg.pop("TYPESAFE_API_KEY", None)
    prompt = options.get("generate_prompt")
    if prompt is None:
        prompt = options.get("prompt")
    if prompt is not None:
        cfg["generate_prompt"] = str(prompt).strip()
    return config.save_config(project_root, cfg)


def cold_start(project_root, options=None):
    """Scripted cold start: config + seed + sync.

    Unchecked: copy framework skills and core files. No AI prompt.
    generate_skills: copy files, then return a one-line /goal prompt that
    tells the AI to read the loop-engine file (user text, or the built-in
    default). Module discovery is the AI, not a Python scanner. Does not
    write project skill bodies.
    """
    options = options or {}
    generate_skills = bool(options.get("generate_skills"))
    options = dict(options)
    options["generate_skills"] = generate_skills
    if "prompt" in options and "generate_prompt" not in options:
        options["generate_prompt"] = options.get("prompt")
    jev_key = options.get("jev_key")
    jev_enabled = bool(options.get("jev_enabled"))
    cfg = apply_setup_options(project_root, options)
    seed_report = adapters.seed(project_root)
    jev_report = _sync_jev_module(project_root, jev_enabled, jev_key)
    saved = catalog.load_catalog(project_root)
    queued = queue.load_queue(project_root)
    handoff = ""
    if generate_skills:
        handoff = queue.build_handoff(
            project_root,
            generate=True,
            prompt=cfg.get("generate_prompt"),
        )
    return {
        "ok": True,
        "seeded": is_seeded(project_root),
        "config": cfg,
        "seed": seed_report,
        "catalog": saved,
        "modules": len(saved.get("modules") or []),
        "queued": len(queued.get("items") or []),
        "generate_skills": generate_skills,
        "jev_enabled": jev_enabled,
        "jev": jev_report,
        "handoff": handoff,
    }


def _sync_jev_module(project_root, enabled, key):
    """Copy the standalone Jev module only when the cold-start box is checked."""
    import sys
    from .paths import find_harness_dir
    harness = find_harness_dir()
    if harness not in sys.path:
        sys.path.insert(0, harness)
    try:
        from jev.install import sync_module
    except ImportError:
        return {"enabled": bool(enabled), "missing": True}
    return sync_module(project_root, enabled, key=key)


def _remove_path(path):
    from .paths import _rmtree_nofollow
    if not os.path.lexists(path):
        return False
    _rmtree_nofollow(path)
    return True


def _revert_root_rules_file(path):
    """Drop the CastFlow harness block. Keep a real project section."""
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            text = f.read()
    except OSError:
        return False
    if "CastFlow" not in text:
        return False
    boundary = "<!-- =========="
    if boundary in text:
        tail = text[text.find(boundary):]
        lines = []
        for line in tail.splitlines():
            if line.startswith("<!--"):
                continue
            lines.append(line)
        rest = "\n".join(lines).strip()
        stub = (
            rest.startswith("## Code naming")
            and "Add team conventions below" in rest
            and len(rest) < 400
        )
        if not rest or stub:
            try:
                os.remove(path)
            except OSError:
                return False
            return True
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(rest)
                f.write("\n")
        except OSError:
            return False
        return True
    if "This file is generated from CastFlow" in text or "ROOT_RULES" in text:
        try:
            os.remove(path)
        except OSError:
            return False
        return True
    return False


def _strip_hook_file(path):
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except (ValueError, OSError):
        return False
    if not isinstance(data, dict):
        return False
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return False
    if not adapters._strip_castflow_hooks(hooks):
        return False
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError:
        return False
    return True


def unseed(project_root):
    """Remove CastFlow runtime + projections so cold start can run again.

    Does not delete project source. Drops leftover vendored `.castflow/` and
    project launchers (`castflow.bat` / `castflow.sh` / `castflow.command`;
    manager lives in runtime). Root CLAUDE.md / AGENTS.md keep a non-stub
    project section.
    """
    from .paths import reject_factory_runtime

    reject_factory_runtime(project_root)
    removed = []
    names = [item["name"] for item in skills.inventory(project_root)]
    names.extend(["SKILL_ITERATION.md", "GLOBAL_SKILL_MEMORY.md"])
    skill_rels = (
        os.path.join(".claude", "skills"),
        os.path.join(".agents", "skills"),
        os.path.join(".grok", "skills"),
        os.path.join(".cursor", "skills"),
    )
    for rel in skill_rels:
        dest = os.path.join(project_root, rel)
        if not os.path.isdir(dest):
            continue
        try:
            entries = os.listdir(dest)
        except OSError:
            continue
        for entry in entries:
            if entry not in names and not str(entry).startswith("programmer-"):
                continue
            path = os.path.join(dest, entry)
            if _remove_path(path):
                removed.append(path.replace("\\", "/"))

    extra_files = (
        os.path.join(".grok", "hooks", "castflow.json"),
        os.path.join(".grok", "rules", "evolve-reminder.md"),
        os.path.join(".claude", "rules", "evolve-reminder.md"),
    )
    for rel in extra_files:
        path = os.path.join(project_root, rel)
        if _remove_path(path):
            removed.append(path.replace("\\", "/"))

    _strip_hook_file(os.path.join(project_root, ".claude", "settings.json"))
    _strip_hook_file(os.path.join(project_root, ".cursor", "hooks.json"))
    _revert_root_rules_file(os.path.join(project_root, "CLAUDE.md"))
    _revert_root_rules_file(os.path.join(project_root, "AGENTS.md"))

    rdir = runtime_dir(project_root)
    if _remove_path(rdir):
        removed.append(rdir.replace("\\", "/"))
    from .bundle import remove_project_launchers, remove_stale_project_harness
    if remove_stale_project_harness(project_root):
        removed.append(os.path.join(project_root, ".castflow").replace("\\", "/"))
    removed.extend(remove_project_launchers(project_root))
    return {
        "ok": True,
        "seeded": is_seeded(project_root),
        "removed": removed,
    }


def update_framework(project_root):
    """Refresh CastFlow-owned skills and core files, then sync.

    Leaves project skills (programmer-*, generated architect, etc.) untouched.
    """
    updated = []
    for item in skills.inventory(project_root):
        if item.get("family") != "framework":
            continue
        result = skills.update_skill(project_root, item["name"])
        if result.get("ok"):
            updated.append(item["name"])
    report = adapters.sync(project_root)
    return {
        "ok": True,
        "updated": updated,
        "sync": {"evolution": report.get("evolution")},
    }
