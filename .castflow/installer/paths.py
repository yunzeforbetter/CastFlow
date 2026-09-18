"""Project root and harness directory discovery."""

import os

HARNESS = ".castflow"
CLAUDE = ".claude"
BOOTSTRAP_OUTPUT = "bootstrap-output"


def find_harness_dir():
    """Locate the .castflow/ directory (always relative to this package)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_project_root(explicit_root=None):
    """Locate the project root directory.

    Search strategy:
    1. Explicit --project-root
    2. Walk up from cwd for .castflow-runtime/ then .git
    3. cwd (never harness.parent.parent — that planted files outside the repo)
    """
    if explicit_root:
        return os.path.abspath(explicit_root)

    start = os.path.abspath(os.getcwd())
    candidate = start
    for _ in range(12):
        if os.path.isdir(os.path.join(candidate, ".castflow-runtime")):
            return candidate
        if os.path.isdir(os.path.join(candidate, ".git")) or os.path.isfile(
                os.path.join(candidate, ".git")):
            return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent
    return start
