"""Generation logic: copy core files, merge root CLAUDE.md, copy runtime templates.

Cold start (bootstrap-skill): **Phase A** only in this module — copy harness to `.claude/`,
merge project root `CLAUDE.md`, copy long-lived runtime templates. Project-level skills
(architect, debug, profiler, programmer-*) are **not** generated here; models write
`.claude/skills/...` via subagents (see `CastFlow/bootstrap-skill/SKILL.md`).
"""

import os
import sys

from .paths import CLAUDE, BOOTSTRAP_OUTPUT, find_harness_dir
from .io_ops import read_file, safe_write, safe_copy_file, safe_copy_dir
from .templates import replace_placeholders, process_conditionals
from .placeholders import build_claude_placeholders, build_agent_placeholders
from .claude_merge import merge_claude_md
from .hook_config import merge_cursor_hooks, merge_claude_settings

CORE_FILE_COPIES = [
    ("core/skills/SKILL_ITERATION.md", "skills/SKILL_ITERATION.md"),
    ("core/skills/GLOBAL_SKILL_MEMORY.md", "skills/GLOBAL_SKILL_MEMORY.md"),
    ("core/protocols/idp-protocol.md", "protocols/idp-protocol.md"),
    ("core/protocols/validated-protocol.md", "protocols/validated-protocol.md"),
    ("core/agents/requirement-analysis-agent.md", "agents/requirement-analysis-agent.md"),
    ("core/agents/integration-matching-agent.md", "agents/integration-matching-agent.md"),
    ("core/agents/pipeline-verify-agent.md", "agents/pipeline-verify-agent.md"),
    ("core/traces/README.md", "traces/README.md"),
    ("core/traces/config/hooks.config.json", "traces/config/hooks.config.json"),
]

CORE_DIR_COPIES = [
    ("core/skills/code-pipeline-skill", "skills/code-pipeline-skill"),
    ("core/skills/skill-creator", "skills/skill-creator"),
    ("core/skills/origin-evolve-skill", "skills/origin-evolve-skill"),
    ("core/hooks", "hooks"),
    ("core/scripts", "scripts"),
]

AGENT_TEMPLATE = "core/templates/agents/programmer.template.md"


def copy_core_files(project_root, manifest, dry_run, backup_session=None):
    print("\n=== Copying core files ===")
    merge_mode = manifest.get("merge_mode", "full")
    profile = manifest.get("profile", "standard")
    harness_dir = find_harness_dir()

    for src_rel, dst_rel in CORE_FILE_COPIES:
        if profile == "lite" and "agents/" in src_rel:
            print("  [SKIP]   {} (profile=lite)".format(dst_rel))
            continue
        src = os.path.join(harness_dir, src_rel)
        dst = os.path.join(project_root, CLAUDE, dst_rel)
        safe_copy_file(src, dst, merge_mode, dry_run, backup_session)

    for src_rel, dst_rel in CORE_DIR_COPIES:
        if profile == "lite" and "code-pipeline" in src_rel:
            print("  [SKIP]   {}/ (profile=lite)".format(dst_rel))
            continue
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


def generate_single_template(harness_dir, dest_path,
                             template_rel, placeholders, tech_stack,
                             merge_mode, dry_run, language="zh",
                             backup_session=None):
    src = os.path.join(harness_dir, template_rel)
    if not os.path.isfile(src):
        print("  [ERROR]  Template not found: {}".format(src))
        return

    content = read_file(src)
    content, warnings = replace_placeholders(content, placeholders)
    content = process_conditionals(content, tech_stack, language)

    for w in warnings:
        print("  [WARN]   {{{{{}}}}}: no content file, preserved as-is".format(w))

    safe_write(dest_path, content, merge_mode, dry_run, backup_session)


def copy_templates(project_root, merge_mode, dry_run, backup_session=None):
    print("\n=== Copying templates to .claude/templates/ ===")
    harness_dir = find_harness_dir()
    templates_dst = os.path.join(project_root, CLAUDE, "templates")

    pairs = [
        ("core/templates/AUTHORING_GUIDE.md", "AUTHORING_GUIDE.md"),
        ("core/templates/skills/programmer.template", "skills/programmer.template"),
        ("core/templates/agents/programmer.template.md", "agents/programmer.template.md"),
    ]
    for src_rel, dst_rel in pairs:
        src = os.path.join(harness_dir, src_rel)
        dst = os.path.join(templates_dst, dst_rel)
        if os.path.isdir(src):
            safe_copy_dir(src, dst, merge_mode, dry_run, backup_session)
        elif os.path.isfile(src):
            safe_copy_file(src, dst, merge_mode, dry_run, backup_session)


def merge_root_claude(
        project_root, manifest, dry_run, backup_session=None, harness_merge_choice=None):
    """Merge `core/CLAUDE.template.md` into the project root `CLAUDE.md`."""
    harness_dir = find_harness_dir()
    content_dir = os.path.join(project_root, BOOTSTRAP_OUTPUT, "content")
    tech_stack = manifest.get("tech_stack", "")
    language = manifest.get("language", "zh")
    claude_template = os.path.join(harness_dir, "core/CLAUDE.template.md")
    if os.path.isfile(claude_template):
        claude_content = read_file(claude_template)
        claude_content, _ = replace_placeholders(
            claude_content, build_claude_placeholders(manifest, content_dir))
        claude_content = process_conditionals(claude_content, tech_stack, language)
        merge_claude_md(
            os.path.join(project_root, "CLAUDE.md"),
            claude_content,
            dry_run,
            backup_session,
            harness_merge_choice=harness_merge_choice,
        )
    else:
        print("  [ERROR]  Template not found: {}".format(claude_template))


def phase_a(project_root, manifest, dry_run, backup_session=None, harness_merge_choice=None):
    """Phase A: core sync to `.claude/`, root CLAUDE.md, runtime templates (long-lived)."""
    merge_mode = manifest.get("merge_mode", "full")
    print("\n=== Phase A: core + CLAUDE.md + runtime templates ===")
    copy_core_files(project_root, manifest, dry_run, backup_session)

    print("\n=== Generating CLAUDE.md (Phase A) ===")
    merge_root_claude(
        project_root, manifest, dry_run, backup_session, harness_merge_choice,
    )
    copy_templates(project_root, merge_mode, dry_run, backup_session)


def generate_all(project_root, manifest, dry_run, backup_session=None,
                 harness_merge_choice=None):
    """Full bootstrap: Phase A only (no installer merge of project-level skills)."""
    phase_a(project_root, manifest, dry_run, backup_session, harness_merge_choice)


def run_phase_a_subset(project_root, manifest, target, dry_run,
                       backup_session=None, harness_merge_choice=None):
    """Phase A subset only: 'claude_md' or 'templates' (not full scaffold)."""
    merge_mode = manifest.get("merge_mode", "full")

    if target == "claude_md":
        print("\n=== CLAUDE.md only (Phase A subset) ===")
        merge_root_claude(
            project_root, manifest, dry_run, backup_session, harness_merge_choice,
        )
        return

    if target == "templates":
        print("\n=== .claude/templates/ only (Phase A subset) ===")
        copy_templates(project_root, merge_mode, dry_run, backup_session)
        return

    print("Error: Invalid run_phase_a_subset target: {}".format(target))
    sys.exit(1)


def generate_agent(project_root, manifest, module_id, dry_run, backup_session=None):
    """Generate a programmer-agent for a module."""
    harness_dir = find_harness_dir()
    output_dir = os.path.join(project_root, CLAUDE)
    merge_mode = manifest.get("merge_mode", "full")
    tech_stack = manifest.get("tech_stack", "")
    language = manifest.get("language", "zh")
    modules = manifest.get("modules", [])

    matched = [m for m in modules if m["id"] == module_id]
    if not matched:
        print("Error: Module '{}' not found in manifest.".format(module_id))
        sys.exit(1)

    module = matched[0]
    mid = module["id"]
    print("\n=== Generating programmer-{}-agent ===".format(mid))
    generate_single_template(
        harness_dir,
        os.path.join(output_dir, "agents", "programmer-{}-agent.md".format(mid)),
        AGENT_TEMPLATE,
        build_agent_placeholders(module),
        tech_stack, merge_mode, dry_run, language, backup_session,
    )
