"""Safe file I/O operations with backup integration."""

import os
import shutil


def read_file(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()


def safe_write(path, content, merge_mode, dry_run, backup_session=None):
    """Write content to path with backup and merge_mode semantics.

    Args:
        backup_session: BackupSession instance (or None to skip backup).
    """
    path = os.path.normpath(path)
    if os.path.exists(path):
        if merge_mode == "full":
            if not dry_run and backup_session:
                backup_session.backup_original(path, dry_run)
            if not dry_run:
                os.remove(path)
            label = "BACKUP" if (backup_session and backup_session.enabled) else "OVERWRITE"
            print("  [{}] {}".format(label, path))
        else:
            print("  [SKIP]   {} (exists, merge_mode={})".format(path, merge_mode))
            return False

    if dry_run:
        print("  [WRITE]  {}".format(path))
        return True

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("  [WRITE]  {}".format(path))
    return True


def safe_copy_file(src, dst, merge_mode, dry_run, backup_session=None):
    if os.path.exists(dst):
        if merge_mode == "full":
            if not dry_run and backup_session:
                backup_session.backup_original(dst, dry_run)
            label = "BACKUP" if (backup_session and backup_session.enabled) else "OVERWRITE"
            print("  [{}] {}".format(label, dst))
        else:
            print("  [SKIP]   {} (exists)".format(dst))
            return False

    if dry_run:
        print("  [COPY]   {} -> {}".format(src, dst))
        return True

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    print("  [COPY]   {} -> {}".format(src, dst))
    return True


def _ignore_hook_configs(directory, contents):
    """Ignore JSON config files when copying the hooks directory."""
    if os.path.basename(directory) == "hooks":
        return [f for f in contents if f.endswith(".json")]
    return []


def safe_copy_dir(src, dst, merge_mode, dry_run, backup_session=None):
    if os.path.exists(dst):
        if merge_mode == "full":
            if not dry_run and backup_session:
                backup_session.backup_original(dst, dry_run)
            label = "BACKUP" if (backup_session and backup_session.enabled) else "OVERWRITE"
            print("  [{}] {}/".format(label, dst))
        else:
            print("  [SKIP]   {}/ (exists)".format(dst))
            return False

    if dry_run:
        print("  [COPY]   {}/ -> {}/".format(src, dst))
        return True

    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=_ignore_hook_configs)
    print("  [COPY]   {}/ -> {}/".format(src, dst))
    return True
