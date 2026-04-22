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
    1. Explicit --project-root argument (trusted if given)
    2. Walk up from script location looking for .claude/
    3. If not found, use the harness parent's parent as project root
       and create .claude/ there
    """
    if explicit_root:
        return os.path.abspath(explicit_root)

    harness_dir = find_harness_dir()
    start = os.path.dirname(harness_dir)

    candidate = start
    for _ in range(10):
        if os.path.isdir(os.path.join(candidate, CLAUDE)):
            return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent

    project_root = os.path.dirname(start)
    os.makedirs(os.path.join(project_root, CLAUDE), exist_ok=True)
    print("  [CREATE] {}/ (first bootstrap)".format(
        os.path.join(project_root, CLAUDE)))
    return project_root
