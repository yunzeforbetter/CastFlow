"""CLI entry point for CastFlow bootstrap."""

import argparse
import os
import shutil
import sys

from .paths import CLAUDE, find_harness_dir, find_project_root
from .backup import (
    BackupSession, DEFAULT_BACKUP_KEEP, BACKUP_DIR_NAME,
    rotate_backups, cleanup_legacy_bak, ensure_backups_gitignore,
)
from .manifest import load_manifest
from .generate import generate_all, generate_single_skill, generate_agent
from .validate import validate_all


def main():
    parser = argparse.ArgumentParser(
        description="CastFlow Bootstrap - Deterministic file generator",
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Validate .claude/ output against SKILL_ITERATION standards",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview operations without writing files",
    )
    parser.add_argument(
        "--skill", type=str, default=None,
        help="Generate a single skill incrementally",
    )
    parser.add_argument(
        "--agent", type=str, default=None,
        help="Generate a programmer-agent for a module",
    )
    parser.add_argument(
        "--project-root", type=str, default=None,
        help="Explicit project root path",
    )
    parser.add_argument(
        "--no-backup", action="store_true",
        help="Skip backups before overwriting",
    )
    parser.add_argument(
        "--backup-keep", type=int, default=DEFAULT_BACKUP_KEEP,
        help="Retain this many recent backup sessions (default: {}).".format(
            DEFAULT_BACKUP_KEEP,
        ),
    )
    parser.add_argument(
        "--clean-backups", action="store_true",
        help="Delete all backup sessions and exit",
    )
    args = parser.parse_args()

    project_root = find_project_root(args.project_root)
    harness_dir = find_harness_dir()
    print("Project root: {}".format(project_root))
    print("Harness dir:  {}".format(harness_dir))

    backup_session = BackupSession(project_root, enabled=not args.no_backup)

    if args.clean_backups:
        backups_root = os.path.join(project_root, CLAUDE, BACKUP_DIR_NAME)
        if os.path.isdir(backups_root):
            shutil.rmtree(backups_root)
            print("Removed {}".format(backups_root))
        else:
            print("No backup directory found at {}".format(backups_root))
        sys.exit(0)

    if args.validate:
        success = validate_all(project_root)
        sys.exit(0 if success else 1)

    manifest = load_manifest(project_root)
    modules_str = ", ".join(m["id"] for m in manifest["modules"])
    print("Manifest v{} | {} | {} | merge={} | lang={}".format(
        manifest["version"],
        manifest.get("tech_stack", "?"),
        manifest.get("profile", "standard"),
        manifest.get("merge_mode", "full"),
        manifest.get("language", "zh"),
    ))
    print("Modules: {}".format(modules_str))

    if args.dry_run:
        print("\n*** DRY RUN - no files will be written ***")

    cleanup_legacy_bak(project_root, args.dry_run)

    if args.agent:
        print("\n=== Agent generation: programmer-{}-agent ===".format(args.agent))
        generate_agent(project_root, manifest, args.agent, args.dry_run,
                       backup_session)
    elif args.skill:
        print("\n=== Incremental generation: {} ===".format(args.skill))
        generate_single_skill(project_root, manifest, args.skill, args.dry_run,
                              backup_session)
    else:
        generate_all(project_root, manifest, args.dry_run, backup_session)

    print("\n=== Generation complete ===")
    if not args.dry_run:
        if backup_session.enabled:
            rotate_backups(project_root, args.backup_keep)
            ensure_backups_gitignore(project_root, args.dry_run)
            if backup_session.session_dir and os.path.isdir(backup_session.session_dir):
                rel = os.path.relpath(backup_session.session_dir, project_root)
                print("\n  Backups saved to: {}".format(rel))
                print("  Retention: last {} session(s). Use --clean-backups to remove all.".format(
                    args.backup_keep,
                ))
        print("\nRun 'python .castflow/bootstrap.py --validate' to verify output.")
