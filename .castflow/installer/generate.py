"""Generation logic: copy core files and merge root CLAUDE.md.

Cold start (bootstrap-skill): **Phase A** only in this module — copy harness to `.claude/`,
merge project root `CLAUDE.md`. Project-level skills (architect, debug, profiler,
programmer-*) are **not** generated here; models write `.castflow-runtime/skills/...`
via skill-creator following `SKILL_ITERATION.md` (see `CastFlow/bootstrap-skill/SKILL.md`).
"""

import os
import sys

from .paths import CLAUDE, find_harness_dir
from .io_ops import safe_copy_file, safe_copy_dir
from .hook_config import merge_cursor_hooks, merge_claude_settings

CORE_FILE_COPIES = [
    ("core/skills/SKILL_ITERATION.md", "skills/SKILL_ITERATION.md"),
    ("core/skills/GLOBAL_SKILL_MEMORY.md", "skills/GLOBAL_SKILL_MEMORY.md"),
    ("core/protocols/validated-protocol.md", "protocols/validated-protocol.md"),
    ("core/traces/README.md", "traces/README.md"),
    ("core/traces/config/hooks.config.json", "traces/config/hooks.config.json"),
]

CORE_DIR_COPIES = [
    ("core/skills/skill-creator", "skills/skill-creator"),
    ("core/skills/origin-evolve-skill", "skills/origin-evolve-skill"),
    ("core/hooks", "hooks"),
]


def copy_core_files(project_root, manifest, dry_run, backup_session=None):
    print("\n=== Copying core files ===")
    merge_mode = manifest.get("merge_mode", "full")
    harness_dir = find_harness_dir()

    for src_rel, dst_rel in CORE_FILE_COPIES:
        src = os.path.join(harness_dir, src_rel)
        dst = os.path.join(project_root, CLAUDE, dst_rel)
        safe_copy_file(src, dst, merge_mode, dry_run, backup_session)

    for src_rel, dst_rel in CORE_DIR_COPIES:
        src = os.path.join(harness_dir, src_rel)
        dst = os.path.join(project_root, CLAUDE, dst_rel)
        safe_copy_dir(src, dst, merge_mode, dry_run, backup_session)

    print("\n=== Seeding trace config ===")
    limits_dst = os.path.join(project_root, CLAUDE, "traces", "config", "limits.json")
    if os.path.isfile(limits_dst):
        print("  [SKIP]   {} (user config preserved)".format(limits_dst))
    else:
        limits_src = os.path.join(harness_dir, "core", "traces", "config", "limits.json")
        safe_copy_file(limits_src, limits_dst, "full", dry_run, backup_session)

    print("\n=== Merging hook configs ===")
    merge_cursor_hooks(
        os.path.join(project_root, ".cursor", "hooks.json"), dry_run)
    merge_claude_settings(
        os.path.join(project_root, CLAUDE, "settings.json"), dry_run)


def merge_root_claude(
        project_root, manifest, dry_run, backup_session=None, harness_merge_choice=None):
    """Write root CLAUDE.md / AGENTS.md from ROOT_RULES via manager adapters."""
    from manager.config import load_config
    from manager import adapters as adapters_mod
    cfg = load_config(project_root)
    evolution_on = bool(cfg.get("evolution", {}).get("enabled", True))
    ads = cfg.get("adapters") or {"claude": True, "codex": True}
    written = adapters_mod._write_root_rules(
        project_root, evolution_on, ads, dry_run)
    if dry_run:
        print("  [DRY]    root rules ({})".format(len(written)))
    else:
        print("  [OK]     root rules via ROOT_RULES.template.md")


def phase_a(project_root, manifest, dry_run, backup_session=None, harness_merge_choice=None):
    """Phase A: core sync to `.claude/` and root CLAUDE.md."""
    print("\n=== Phase A: core + CLAUDE.md ===")
    copy_core_files(project_root, manifest, dry_run, backup_session)

    print("\n=== Generating CLAUDE.md (Phase A) ===")
    merge_root_claude(
        project_root, manifest, dry_run, backup_session, harness_merge_choice,
    )


def generate_all(project_root, manifest, dry_run, backup_session=None,
                 harness_merge_choice=None):
    """Full bootstrap: Phase A only (no installer merge of project-level skills)."""
    phase_a(project_root, manifest, dry_run, backup_session, harness_merge_choice)


def run_phase_a_subset(project_root, manifest, target, dry_run,
                       backup_session=None, harness_merge_choice=None):
    """Phase A subset only: 'claude_md' (not full scaffold)."""
    if target == "claude_md":
        print("\n=== CLAUDE.md only (Phase A subset) ===")
        merge_root_claude(
            project_root, manifest, dry_run, backup_session, harness_merge_choice,
        )
        return

    print("Error: Invalid run_phase_a_subset target: {}".format(target))
    sys.exit(1)
