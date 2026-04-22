"""Centralized backup management.

Each bootstrap run creates a timestamped session directory under
.claude/.backups/ holding originals of every overwritten file, preserving
their relative paths. Older sessions are rotated out automatically.
"""

import os
import shutil
from datetime import datetime

from .paths import CLAUDE

BACKUP_DIR_NAME = ".backups"
DEFAULT_BACKUP_KEEP = 3


class BackupSession:
    """Manages backup state for a single bootstrap run.

    Replaces the former global variables (_active_project_root,
    _backup_enabled, _backup_session_dir) with an injectable instance.
    """

    def __init__(self, project_root, enabled=True):
        self._project_root = project_root
        self._enabled = enabled
        self._session_dir = None

    @property
    def enabled(self):
        return self._enabled

    @property
    def project_root(self):
        return self._project_root

    @property
    def session_dir(self):
        return self._session_dir

    def _ensure_session_dir(self):
        if self._session_dir is None:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self._session_dir = os.path.join(
                self._project_root, CLAUDE, BACKUP_DIR_NAME, timestamp,
            )
            os.makedirs(self._session_dir, exist_ok=True)
        return self._session_dir

    def backup_original(self, original_path, dry_run):
        """Copy a file or directory to this session's backup dir.

        Returns the backup path or None.
        """
        if dry_run or not self._enabled:
            return None
        session = self._ensure_session_dir()
        try:
            rel = os.path.relpath(original_path, self._project_root)
        except ValueError:
            return None
        if rel.startswith(".."):
            return None
        dest = os.path.join(session, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.isdir(original_path):
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(original_path, dest)
        else:
            shutil.copy2(original_path, dest)
        return dest


def rotate_backups(project_root, keep):
    """Retain only the N most recent backup session directories."""
    backups_root = os.path.join(project_root, CLAUDE, BACKUP_DIR_NAME)
    if not os.path.isdir(backups_root):
        return
    sessions = sorted(
        d for d in os.listdir(backups_root)
        if os.path.isdir(os.path.join(backups_root, d))
    )
    if len(sessions) <= keep:
        return
    for old in sessions[:-keep]:
        shutil.rmtree(os.path.join(backups_root, old), ignore_errors=True)
        print("  [ROTATE] Removed old backup session: {}".format(old))


def cleanup_legacy_bak(project_root, dry_run):
    """One-time migration: remove legacy in-place .bak files/dirs."""
    claude_root = os.path.join(project_root, CLAUDE)
    if not os.path.isdir(claude_root):
        return
    removed = 0
    for dirpath, dirnames, filenames in os.walk(claude_root):
        if os.path.basename(dirpath) == BACKUP_DIR_NAME:
            dirnames[:] = []
            continue
        for d in list(dirnames):
            if d.endswith(".bak"):
                full = os.path.join(dirpath, d)
                if not dry_run:
                    shutil.rmtree(full, ignore_errors=True)
                removed += 1
                dirnames.remove(d)
        for fn in filenames:
            if fn.endswith(".bak"):
                full = os.path.join(dirpath, fn)
                if not dry_run:
                    try:
                        os.remove(full)
                    except OSError:
                        pass
                removed += 1
    if removed:
        label = "DRY-RUN " if dry_run else ""
        print("  [{}MIGRATE] Removed {} legacy .bak entries from {}/".format(
            label, removed, CLAUDE,
        ))


def ensure_backups_gitignore(project_root, dry_run):
    """Append .backups/ to .claude/.gitignore if missing."""
    if dry_run:
        return
    gitignore_path = os.path.join(project_root, CLAUDE, ".gitignore")
    marker = BACKUP_DIR_NAME + "/"
    existing = ""
    if os.path.isfile(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                existing = f.read()
        except OSError:
            return
        if marker in existing.splitlines():
            return
    prefix = "" if not existing or existing.endswith("\n") else "\n"
    try:
        with open(gitignore_path, "a", encoding="utf-8") as f:
            f.write("{}{}\n".format(prefix, marker))
        print("  [GITIGNORE] Added '{}' to {}/.gitignore".format(marker, CLAUDE))
    except OSError:
        pass
