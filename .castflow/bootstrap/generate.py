"""Generation logic: copy core files, generate skills from templates, check quality."""

import os
import shutil

from .paths import CLAUDE, BOOTSTRAP_OUTPUT, find_harness_dir
from .io_ops import read_file, safe_write, safe_copy_file, safe_copy_dir
from .templates import replace_placeholders, process_conditionals
from .placeholders import (
    build_claude_placeholders, build_architect_placeholders,
    build_module_placeholders, build_agent_placeholders,
    build_debug_placeholders, build_profiler_placeholders,
)
from .claude_merge import merge_claude_md
from .hook_config import merge_cursor_hooks, merge_claude_settings

CORE_FILE_COPIES = [
    ("core/SKILL_ITERATION.md", "skills/SKILL_ITERATION.md"),
    ("core/GLOBAL_SKILL_MEMORY.md", "skills/GLOBAL_SKILL_MEMORY.md"),
    ("core/protocols/idp-protocol.md", "skills/protocols/idp-protocol.md"),
    ("core/protocols/validated-protocol.md", "skills/protocols/validated-protocol.md"),
    ("core/agents/requirement-analysis-agent.md", "agents/requirement-analysis-agent.md"),
    ("core/agents/integration-matching-agent.md", "agents/integration-matching-agent.md"),
    ("core/agents/pipeline-verify-agent.md", "agents/pipeline-verify-agent.md"),
    ("core/traces/README.md", "traces/README.md"),
    ("core/traces/hooks.config.json", "traces/hooks.config.json"),
]

CORE_DIR_COPIES = [
    ("core/skills/code-pipeline-skill", "skills/code-pipeline-skill"),
    ("core/skills/skill-creator", "skills/skill-creator"),
    ("core/skills/origin-evolve", "skills/origin-evolve"),
    ("core/hooks", "hooks"),
    ("scripts", "scripts"),
]

AGENT_TEMPLATE = "templates/agents/programmer.template.md"

CRITICAL_CONTENT = {
    "architect": [
        "architect/hard_rules.md",
        "architect/design_patterns.md",
    ],
    "debug": [
        "debug/focus_areas.md",
        "debug/examples.md",
    ],
    "profiler": [
        "profiler/performance_budgets.md",
        "profiler/examples.md",
    ],
}


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
    limits_dst = os.path.join(project_root, CLAUDE, "traces", "limits.json")
    if os.path.isfile(limits_dst):
        print("  [SKIP]   {} (user config preserved)".format(limits_dst))
    else:
        limits_src = os.path.join(harness_dir, "core", "traces", "limits.json")
        safe_copy_file(limits_src, limits_dst, "full", dry_run, backup_session)

    print("\n=== Merging hook configs ===")
    merge_cursor_hooks(
        os.path.join(project_root, ".cursor", "hooks.json"), dry_run)
    merge_claude_settings(
        os.path.join(project_root, CLAUDE, "settings.json"), dry_run)


def generate_template_dir(harness_dir, output_base, template_subdir, output_subdir,
                          placeholders, tech_stack, merge_mode, dry_run,
                          language="zh", backup_session=None):
    template_path = os.path.normpath(os.path.join(harness_dir, template_subdir))
    output_path = os.path.normpath(os.path.join(output_base, output_subdir))

    if not os.path.isdir(template_path):
        print("  [ERROR]  Template directory not found: {}".format(template_path))
        return

    for filename in sorted(os.listdir(template_path)):
        if not filename.endswith(".template.md"):
            continue
        output_name = filename.replace(".template.md", ".md")
        src = os.path.join(template_path, filename)
        dst = os.path.join(output_path, output_name)

        content = read_file(src)
        content, warnings = replace_placeholders(content, placeholders)
        content = process_conditionals(content, tech_stack, language)

        for w in warnings:
            print("  [WARN]   {{{{{}}}}}: no content file, preserved as-is".format(w))

        safe_write(dst, content, merge_mode, dry_run, backup_session)


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
        ("templates/skills/programmer.template", "programmer.template"),
        ("templates/agents/programmer.template.md", "programmer.template.md"),
    ]
    for src_rel, dst_rel in pairs:
        src = os.path.join(harness_dir, src_rel)
        dst = os.path.join(templates_dst, dst_rel)
        if os.path.isdir(src):
            safe_copy_dir(src, dst, merge_mode, dry_run, backup_session)
        elif os.path.isfile(src):
            safe_copy_file(src, dst, merge_mode, dry_run, backup_session)


def check_content_quality(content_dir, optional):
    print("\n=== Content quality check ===")
    warnings = 0

    for skill_key, files in CRITICAL_CONTENT.items():
        if skill_key in ("debug", "profiler") and not optional.get(skill_key, False):
            continue
        for rel_path in files:
            full_path = os.path.join(content_dir, rel_path)
            if not os.path.isfile(full_path):
                print("  [WARN]   Missing: {} (skill content may be empty)".format(rel_path))
                warnings += 1
            else:
                content = read_file(full_path).strip()
                if len(content) < 20:
                    print("  [WARN]   Too short: {} ({} chars)".format(rel_path, len(content)))
                    warnings += 1

    if warnings == 0:
        print("  [OK]     All critical content files present and non-trivial.")
    else:
        print("  [INFO]   {} warning(s). Generated skills may have empty sections.".format(warnings))


def generate_all(project_root, manifest, dry_run, backup_session=None,
                   harness_merge_choice=None):
    harness_dir = find_harness_dir()
    output_dir = os.path.join(project_root, CLAUDE)
    content_dir = os.path.join(project_root, BOOTSTRAP_OUTPUT, "content")
    merge_mode = manifest.get("merge_mode", "full")
    tech_stack = manifest.get("tech_stack", "")
    language = manifest.get("language", "zh")
    modules = manifest.get("modules", [])
    optional = manifest.get("optional_skills", {})

    copy_core_files(project_root, manifest, dry_run, backup_session)

    print("\n=== Generating CLAUDE.md ===")
    claude_template = os.path.join(harness_dir, "templates/CLAUDE.template.md")
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

    print("\n=== Generating architect-skill ===")
    generate_template_dir(
        harness_dir, output_dir,
        "templates/skills/architect.template", "skills/architect-skill",
        build_architect_placeholders(content_dir),
        tech_stack, merge_mode, dry_run, language, backup_session,
    )

    for module in modules:
        mid = module["id"]
        print("\n=== Generating programmer-{}-skill ===".format(mid))
        generate_template_dir(
            harness_dir, output_dir,
            "templates/skills/programmer.template",
            "skills/programmer-{}-skill".format(mid),
            build_module_placeholders(module, content_dir),
            tech_stack, merge_mode, dry_run, language, backup_session,
        )

    if optional.get("debug", False):
        print("\n=== Generating debug-skill ===")
        generate_template_dir(
            harness_dir, output_dir,
            "templates/skills/debug.template", "skills/debug-skill",
            build_debug_placeholders(content_dir),
            tech_stack, merge_mode, dry_run, language, backup_session,
        )

    if optional.get("profiler", False):
        print("\n=== Generating profiler-skill ===")
        generate_template_dir(
            harness_dir, output_dir,
            "templates/skills/profiler.template", "skills/profiler-skill",
            build_profiler_placeholders(content_dir),
            tech_stack, merge_mode, dry_run, language, backup_session,
        )

    copy_templates(project_root, merge_mode, dry_run, backup_session)
    check_content_quality(content_dir, optional)


def generate_single_skill(project_root, manifest, skill_name, dry_run,
                          backup_session=None, harness_merge_choice=None):
    """Generate a single skill by name."""
    harness_dir = find_harness_dir()
    output_dir = os.path.join(project_root, CLAUDE)
    content_dir = os.path.join(project_root, BOOTSTRAP_OUTPUT, "content")
    merge_mode = manifest.get("merge_mode", "full")
    tech_stack = manifest.get("tech_stack", "")
    language = manifest.get("language", "zh")
    modules = manifest.get("modules", [])
    optional = manifest.get("optional_skills", {})

    if skill_name == "core":
        copy_core_files(project_root, manifest, dry_run, backup_session)
        return

    if skill_name == "claude":
        print("\n=== Generating CLAUDE.md ===")
        claude_template = os.path.join(harness_dir, "templates/CLAUDE.template.md")
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
        return

    if skill_name == "architect":
        print("\n=== Generating architect-skill ===")
        generate_template_dir(
            harness_dir, output_dir,
            "templates/skills/architect.template", "skills/architect-skill",
            build_architect_placeholders(content_dir),
            tech_stack, merge_mode, dry_run, language, backup_session,
        )
        return

    if skill_name == "debug":
        if not optional.get("debug", True):
            print("  [SKIP]   debug-skill (not enabled in manifest)")
            return
        print("\n=== Generating debug-skill ===")
        generate_template_dir(
            harness_dir, output_dir,
            "templates/skills/debug.template", "skills/debug-skill",
            build_debug_placeholders(content_dir),
            tech_stack, merge_mode, dry_run, language, backup_session,
        )
        return

    if skill_name == "profiler":
        if not optional.get("profiler", True):
            print("  [SKIP]   profiler-skill (not enabled in manifest)")
            return
        print("\n=== Generating profiler-skill ===")
        generate_template_dir(
            harness_dir, output_dir,
            "templates/skills/profiler.template", "skills/profiler-skill",
            build_profiler_placeholders(content_dir),
            tech_stack, merge_mode, dry_run, language, backup_session,
        )
        return

    if skill_name == "templates":
        copy_templates(project_root, merge_mode, dry_run, backup_session)
        return

    matched = [m for m in modules if m["id"] == skill_name]
    if matched:
        module = matched[0]
        mid = module["id"]
        print("\n=== Generating programmer-{}-skill ===".format(mid))
        generate_template_dir(
            harness_dir, output_dir,
            "templates/skills/programmer.template",
            "skills/programmer-{}-skill".format(mid),
            build_module_placeholders(module, content_dir),
            tech_stack, merge_mode, dry_run, language, backup_session,
        )
        return

    print("Error: Unknown skill '{}'. Available: core, claude, architect, debug, profiler, templates, or a module id.".format(skill_name))
    import sys
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
        import sys
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
