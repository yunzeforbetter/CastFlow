"""Project root, harness dir, and runtime layout."""

import json
import os
import shutil
import stat

HARNESS_NAME = ".castflow"
RUNTIME_NAME = ".castflow-runtime"

RUNTIME_FILES = {
    "config": "config.json",
    "catalog": "catalog.json",
    "queue": "generate-queue.json",
    "ui_state": "ui-state.json",
    "skills": "skills-disabled.json",
}

RUNTIME_DIRS = ("skills", "memory", "traces", "rules", "hooks", "templates")


def find_harness_dir():
    """Directory that contains this manager package.

    Factory checkout: `<CastFlow>/.castflow`. Seeded project: `<project>/.castflow-runtime`.
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_project_root(explicit_root=None, start=None):
    """Locate the user project root.

    Search order:
    1. Explicit --project-root
    2. Walk up from start (cwd by default) looking for .castflow-runtime/
    3. Walk up looking for .git (the working tree root)
    4. cwd
    Never guesses harness.parent.parent — that previously planted .claude/
    outside the repo when CastFlow itself was the project.
    """
    if explicit_root:
        return os.path.abspath(explicit_root)

    if start is None:
        start = os.getcwd()
    start = os.path.abspath(start)

    runtime_hit = _walk_up_for(start, RUNTIME_NAME)
    if runtime_hit:
        return runtime_hit

    git_hit = _walk_up_for(start, ".git")
    if git_hit:
        return git_hit

    return start


def _walk_up_for(start, name):
    candidate = start
    for _ in range(12):
        target = os.path.join(candidate, name)
        if os.path.isdir(target) or os.path.isfile(target):
            return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent
    return None


def runtime_dir(project_root):
    return os.path.join(project_root, RUNTIME_NAME)


def runtime_path(project_root, key):
    return os.path.join(runtime_dir(project_root), RUNTIME_FILES[key])


def _has_core_skills(harness_dir):
    return os.path.isdir(os.path.join(harness_dir or "", "core", "skills"))


def resolve_factory_harness(project_root=None, castflow_home=None):
    """Harness dir that still has `core/skills` (factory `.castflow`).

    Prefers the running manager when it is the factory. Otherwise uses
    `castflow_home` from runtime config (relative to the project, or absolute).
    Returns None when only a project-vendored runtime manager is available.
    """
    here = find_harness_dir()
    if _has_core_skills(here):
        return here
    home = castflow_home
    if not home and project_root:
        cfg_path = os.path.join(runtime_dir(project_root), RUNTIME_FILES["config"])
        if os.path.isfile(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8-sig") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    home = loaded.get("castflow_home")
            except (ValueError, OSError):
                home = None
    if home:
        if project_root and not os.path.isabs(home):
            home = os.path.normpath(os.path.join(project_root, home))
        for cand in (os.path.join(home, HARNESS_NAME), home):
            if _has_core_skills(cand):
                return cand
    return None


def hooks_dir_for(project_root):
    """Hook scripts the project should run: runtime copy, then factory core."""
    runtime_hooks = os.path.join(runtime_dir(project_root), "hooks")
    if os.path.isfile(os.path.join(runtime_hooks, "trace-collector.py")):
        return runtime_hooks
    legacy = os.path.join(project_root, HARNESS_NAME, "core", "hooks")
    if os.path.isfile(os.path.join(legacy, "trace-collector.py")):
        return legacy
    factory = resolve_factory_harness(project_root)
    if factory:
        return os.path.join(factory, "core", "hooks")
    return os.path.join(find_harness_dir(), "core", "hooks")


def is_factory_checkout(path):
    """True only for the CastFlow source repo, not a seeded project."""
    if not path:
        return False
    return os.path.isfile(os.path.join(path, HARNESS_NAME, "manager.py"))


def factory_root():
    """CastFlow factory checkout, or None when running a project-vendored manager."""
    harness = resolve_factory_harness()
    if harness:
        root = os.path.dirname(harness)
        if is_factory_checkout(root):
            return root
    root = os.path.dirname(find_harness_dir())
    if is_factory_checkout(root):
        return root
    return None


def is_factory_root(path):
    factory = factory_root()
    if not factory or not path:
        return False
    return os.path.normcase(os.path.abspath(path)) == os.path.normcase(
        os.path.abspath(factory))


class FactoryRuntimeError(Exception):
    """Tried to plant seed artifacts inside the CastFlow factory."""


# Discovery trees and root rules belong in the target project only.
FACTORY_SEED_DIRS = (
    RUNTIME_NAME,
    ".claude",
    ".agents",
    ".cursor",
    ".grok",
)
FACTORY_SEED_FILES = (
    "CLAUDE.md",
    "AGENTS.md",
)


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


def _rmtree_nofollow(path):
    """Remove a file/dir/junction without following reparse points into runtime."""
    if not os.path.lexists(path):
        return
    if _is_reparse_point(path):
        try:
            os.unlink(path)
        except OSError:
            try:
                os.rmdir(path)
            except OSError:
                pass
        return
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
        return
    if not os.path.isdir(path):
        return
    try:
        names = os.listdir(path)
    except OSError:
        return
    for name in names:
        _rmtree_nofollow(os.path.join(path, name))
    try:
        os.rmdir(path)
    except OSError:
        shutil.rmtree(path, ignore_errors=True)


def scrub_factory_runtime():
    """Remove seed leftovers from the factory checkout.

    `.castflow-runtime`, `.claude`, `.agents`, `.cursor`, `.grok`, and generated
    root rule files belong only in target projects.
    """
    root = factory_root()
    if not root:
        return False
    removed = False
    for name in FACTORY_SEED_DIRS:
        path = os.path.join(root, name)
        if os.path.lexists(path):
            _rmtree_nofollow(path)
            removed = True
    for name in FACTORY_SEED_FILES:
        path = os.path.join(root, name)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass
            removed = True
    return removed


def reject_factory_runtime(project_root):
    """Refuse to seed or project inside CastFlow; delete leftover artifacts."""
    if not is_factory_root(project_root):
        return
    scrub_factory_runtime()
    raise FactoryRuntimeError(
        "Refusing to create .castflow-runtime / .claude / .agents inside the "
        "CastFlow factory. Pass --project-root <your-game-or-app>. "
        "Leftover factory seed directories were removed."
    )


def ensure_runtime_layout(project_root):
    """Create runtime directories if missing. Returns the runtime root."""
    reject_factory_runtime(project_root)
    root = runtime_dir(project_root)
    os.makedirs(root, exist_ok=True)
    for name in RUNTIME_DIRS:
        os.makedirs(os.path.join(root, name), exist_ok=True)
    traces_config = os.path.join(root, "traces", "config")
    os.makedirs(traces_config, exist_ok=True)
    cross = os.path.join(root, "rules", "cross-cutting.md")
    if not os.path.isfile(cross):
        with open(cross, "w", encoding="utf-8", newline="\n") as f:
            f.write(
                "# Cross-cutting rules\n\n"
                "Promoted only when MEMORY anchors hit two or more project skills.\n"
            )
    return root
