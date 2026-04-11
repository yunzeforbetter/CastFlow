#!/usr/bin/env python3
"""
CastFlow Bootstrap - Deterministic File Generator

Reads bootstrap-output/manifest.json and content files, generates the
complete .claude/ framework structure from .castflow/ templates.

Zero external dependencies. Python 3.6+.

Usage:
    python .castflow/bootstrap.py                      # Execute full generation
    python .castflow/bootstrap.py --validate           # Validate .claude/ output
    python .castflow/bootstrap.py --dry-run            # Preview without writing
    python .castflow/bootstrap.py --skill architect    # Generate a single skill
    python .castflow/bootstrap.py --agent building     # Generate a module agent on-demand
"""

import argparse
import difflib
import json
import os
import re
import shutil
import sys


# ============================================================
# Constants
# ============================================================

SUPPORTED_VERSIONS = [1]

HARNESS = ".castflow"
CLAUDE = ".claude"
BOOTSTRAP_OUTPUT = "bootstrap-output"

CORE_FILE_COPIES = [
    ("core/SKILL_RULE.md", "skills/SKILL_RULE.md"),
    ("core/GLOBAL_SKILL_MEMORY.md", "skills/GLOBAL_SKILL_MEMORY.md"),
    ("core/agents/requirement-analysis-agent.md", "agents/requirement-analysis-agent.md"),
    ("core/agents/integration-matching-agent.md", "agents/integration-matching-agent.md"),
    ("core/agents/pipeline-verify-agent.md", "agents/pipeline-verify-agent.md"),
]

CORE_DIR_COPIES = [
    ("core/skills/code-pipeline-skill", "skills/code-pipeline-skill"),
    ("core/skills/skill-creator", "skills/skill-creator"),
    ("core/skills/origin-evolve", "skills/origin-evolve"),
    ("scripts", "scripts"),
]

EMOJI_CHARS = set("\u274c\u2705\u2b50\U0001f4cb\U0001f534\U0001f7e1\U0001f7e2\u2713\u2717\u2192\u2194\u2190\u2193\u2191\u25ba\u25bc\u25b2\u25c4\u25c6\u2605")

DATE_PATTERN = re.compile(r"20[2-3]\d[-/]\d{1,2}[-/]\d{1,2}")


# ============================================================
# File I/O
# ============================================================

def read_file(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()


def safe_write(path, content, merge_mode, dry_run):
    if os.path.exists(path):
        if merge_mode == "full":
            if not dry_run:
                shutil.copy2(path, path + ".bak")
            print("  [BACKUP] {} -> {}.bak".format(path, path))
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


def safe_copy_file(src, dst, merge_mode, dry_run):
    if os.path.exists(dst):
        if merge_mode == "full":
            if not dry_run:
                shutil.copy2(dst, dst + ".bak")
            print("  [BACKUP] {}".format(dst))
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


def safe_copy_dir(src, dst, merge_mode, dry_run):
    if os.path.exists(dst):
        if merge_mode == "full":
            backup = dst + ".bak"
            if not dry_run:
                if os.path.exists(backup):
                    shutil.rmtree(backup)
                shutil.copytree(dst, backup)
            print("  [BACKUP] {}/ -> {}.bak/".format(dst, dst))
        else:
            print("  [SKIP]   {}/ (exists)".format(dst))
            return False

    if dry_run:
        print("  [COPY]   {}/ -> {}/".format(src, dst))
        return True

    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print("  [COPY]   {}/ -> {}/".format(src, dst))
    return True


# ============================================================
# Template Processing
# ============================================================

def replace_placeholders(content, placeholders):
    warnings = []
    for key, value in placeholders.items():
        token = "{{" + key + "}}"
        if token not in content:
            continue
        if value is not None:
            content = content.replace(token, value)
        else:
            warnings.append(key)
    return content, warnings


def process_conditionals(content, tech_stack):
    lines = content.split("\n")
    output = []
    skip = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("<!-- if:"):
            tag = stripped.replace("<!-- if:", "").replace(" -->", "").strip()
            skip = (tag != tech_stack)
            continue
        if stripped == "<!-- endif -->":
            skip = False
            continue
        if not skip:
            output.append(line)
    return "\n".join(output)


def load_content(content_dir, relative_path):
    if not relative_path:
        return None
    path = os.path.join(content_dir, relative_path)
    if os.path.isfile(path):
        return read_file(path).strip()
    return None


# ============================================================
# Placeholder Builders
# ============================================================

def build_claude_placeholders(manifest, content_dir):
    return {
        "NAMING_CONVENTIONS": (
            load_content(content_dir, "claude/naming_conventions.md")
            or manifest.get("naming_conventions", "")
        ),
        "FRAMEWORK_RULES": load_content(content_dir, "claude/framework_rules.md") or "",
        "PROJECT_RULES": load_content(content_dir, "claude/project_rules.md") or "",
    }


def build_architect_placeholders(content_dir):
    return {
        "CONSTRAINT_EXAMPLES": load_content(content_dir, "architect/constraint_examples.md") or "",
        "PATTERN_EXAMPLES": load_content(content_dir, "architect/pattern_examples.md") or "",
        "CONSTRAINT_RULES_SUMMARY": load_content(content_dir, "architect/constraint_rules_summary.md") or "",
        "CONSTRAINT_QUERY_TABLE": load_content(content_dir, "architect/constraint_query_table.md") or "",
        "PATTERN_QUERY_TABLE": load_content(content_dir, "architect/pattern_query_table.md") or "",
        "DESIGN_PATTERNS": load_content(content_dir, "architect/design_patterns.md") or "",
        "HARD_RULES": load_content(content_dir, "architect/hard_rules.md") or "",
        "COMMON_PITFALLS": load_content(content_dir, "architect/common_pitfalls.md") or "",
    }


def build_module_placeholders(module, content_dir):
    mid = module["id"]
    mod_dir = "modules/{}".format(mid)
    return {
        "MODULE_ID": mid,
        "MODULE_DISPLAY_NAME": module["display_name"],
        "MODULE_ARCHITECTURE": load_content(content_dir, "{}/architecture.md".format(mod_dir)) or "",
        "CORE_CLASSES": load_content(content_dir, "{}/core_classes.md".format(mod_dir)) or "",
        "MODULE_RELATIONSHIPS": load_content(content_dir, "{}/relationships.md".format(mod_dir)) or "",
        "MODULE_EXAMPLES": load_content(content_dir, "{}/examples.md".format(mod_dir)) or "",
        "MODULE_HARD_RULES": load_content(content_dir, "{}/hard_rules.md".format(mod_dir)) or "",
        "MODULE_PITFALLS": load_content(content_dir, "{}/pitfalls.md".format(mod_dir)) or "",
    }


def build_agent_placeholders(module):
    mid = module["id"]
    skill_name = "programmer-{}-skill".format(mid)
    return {
        "MODULE_ID": mid,
        "MODULE_DISPLAY_NAME": module["display_name"],
        "MODULE_COLOR": module.get("color", "blue"),
        "MODULE_SKILLS": "- {}".format(skill_name),
        "EXTRA_SKILL_NOTE": " and {}".format(skill_name),
    }


AGENT_TEMPLATE = "templates/agents/programmer.template.md"


def build_debug_placeholders(content_dir):
    return {
        "FOCUS_AREAS": load_content(content_dir, "debug/focus_areas.md") or "",
        "PROJECT_SPECIFIC_CHECKS": load_content(content_dir, "debug/project_checks.md") or "",
        "DEBUG_EXAMPLES": load_content(content_dir, "debug/examples.md") or "",
        "EXTRA_RULES": load_content(content_dir, "debug/extra_rules.md") or "",
        "EXTRA_PITFALLS": load_content(content_dir, "debug/extra_pitfalls.md") or "",
    }


def build_profiler_placeholders(content_dir):
    return {
        "PERFORMANCE_BUDGETS": load_content(content_dir, "profiler/performance_budgets.md") or "",
        "PROJECT_SPECIFIC_OPTIMIZATIONS": load_content(content_dir, "profiler/project_optimizations.md") or "",
        "PROFILER_EXAMPLES": load_content(content_dir, "profiler/examples.md") or "",
        "EXTRA_RULES": load_content(content_dir, "profiler/extra_rules.md") or "",
        "EXTRA_PITFALLS": load_content(content_dir, "profiler/extra_pitfalls.md") or "",
    }


# ============================================================
# Generation
# ============================================================

def copy_core_files(project_root, manifest, dry_run):
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
        safe_copy_file(src, dst, merge_mode, dry_run)

    for src_rel, dst_rel in CORE_DIR_COPIES:
        if profile == "lite" and "code-pipeline" in src_rel:
            print("  [SKIP]   {}/ (profile=lite)".format(dst_rel))
            continue
        src = os.path.join(harness_dir, src_rel)
        dst = os.path.join(project_root, CLAUDE, dst_rel)
        safe_copy_dir(src, dst, merge_mode, dry_run)


def generate_template_dir(harness_dir, output_base, template_subdir, output_subdir,
                          placeholders, tech_stack, merge_mode, dry_run):
    template_path = os.path.join(harness_dir, template_subdir)
    output_path = os.path.join(output_base, output_subdir)

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
        content = process_conditionals(content, tech_stack)

        for w in warnings:
            print("  [WARN]   {{{{{}}}}}: no content file, preserved as-is".format(w))

        safe_write(dst, content, merge_mode, dry_run)


def generate_single_template(harness_dir, dest_path,
                             template_rel, placeholders, tech_stack,
                             merge_mode, dry_run):
    src = os.path.join(harness_dir, template_rel)
    if not os.path.isfile(src):
        print("  [ERROR]  Template not found: {}".format(src))
        return

    content = read_file(src)
    content, warnings = replace_placeholders(content, placeholders)
    content = process_conditionals(content, tech_stack)

    for w in warnings:
        print("  [WARN]   {{{{{}}}}}: no content file, preserved as-is".format(w))

    safe_write(dest_path, content, merge_mode, dry_run)


CLAUDE_BOUNDARY = "<!-- =========="


def merge_claude_md(dest_path, new_content, dry_run):
    if not os.path.isfile(dest_path):
        safe_write(dest_path, new_content, "full", dry_run)
        return

    existing = read_file(dest_path)

    old_harness, old_project = _split_at_boundary(existing)
    new_harness, new_project = _split_at_boundary(new_content)

    if not old_project:
        print("  [MIGRATE] Existing CLAUDE.md has no boundary marker.")
        print("            Scanning for unique sections to preserve...")

        unique = _deduplicate_sections(existing, new_content)

        if unique:
            parts = []
            for h, b in unique:
                section = "{}\n\n{}".format(h, b).strip() if h else b.strip()
                parts.append(section)
            unique_text = "\n\n---\n\n".join(parts)

            new_harness_part, new_project_part = _split_at_boundary(new_content)
            if new_project_part:
                merged = new_harness_part + new_project_part.rstrip("\n") + \
                    "\n\n" + unique_text + "\n"
            else:
                merged = new_content.rstrip("\n") + "\n\n" + unique_text + "\n"
            print("  [MERGE]   {} unique section(s) appended to project section.".format(
                len(unique)))
        else:
            merged = new_content
            print("  [CLEAN]   All existing content covered by template. Using template as-is.")

        if not dry_run:
            backup_path = dest_path + ".migrate-backup"
            with open(backup_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(existing)
            print("  [BACKUP]  Original saved to {}".format(
                os.path.basename(backup_path)))
        safe_write(dest_path, merged, "full", dry_run)
        return

    if old_harness.strip() == new_harness.strip():
        print("  [MATCH]   Harness section unchanged, project section preserved.")
        merged = new_harness + old_project
        safe_write(dest_path, merged, "full", dry_run)
        return

    similarity = difflib.SequenceMatcher(
        None, old_harness.strip(), new_harness.strip()
    ).ratio()
    pct = int(similarity * 100)

    print("  [DIFF]    Harness section differs from template ({}% similar).".format(pct))

    if dry_run:
        print("            (dry-run: would prompt for merge decision)")
        return

    print("")
    print("  Your CLAUDE.md harness section has modifications.")
    print("  Options:")
    print("    1 - Use template version (recommended: keeps framework rules up to date)")
    print("        Your old harness section will be saved to CLAUDE.md.castflow-backup")
    print("    2 - Keep your current version (skip harness update)")
    print("    3 - Merge: use template version + append your differences to project section")
    print("")

    while True:
        try:
            choice = input("  Choose [1/2/3]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelled. CLAUDE.md not modified.")
            return

        if choice in ("1", "2", "3"):
            break
        print("  Please enter 1, 2, or 3.")

    if choice == "1":
        backup_path = dest_path + ".castflow-backup"
        with open(backup_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(old_harness)
        print("  [BACKUP]  Old harness section saved to {}".format(
            os.path.basename(backup_path)))
        merged = new_harness + old_project
        safe_write(dest_path, merged, "full", False)

    elif choice == "2":
        print("  [SKIP]    CLAUDE.md harness section not updated.")

    elif choice == "3":
        backup_path = dest_path + ".castflow-backup"
        with open(backup_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(old_harness)
        print("  [BACKUP]  Old harness section saved to {}".format(
            os.path.basename(backup_path)))

        user_diff = _extract_user_additions(old_harness, new_harness)
        if user_diff:
            merged_project = old_project.rstrip("\n") + "\n\n" + \
                "## Migrated from harness section\n\n" + \
                "<!-- The following content was in your harness section but differs from template. -->\n" + \
                "<!-- Review and reorganize as needed, then remove this comment. -->\n\n" + \
                user_diff + "\n"
            merged = new_harness + merged_project
            print("  [MERGE]   Template harness applied. Your modifications appended to project section.")
        else:
            merged = new_harness + old_project
            print("  [MERGE]   No unique user additions detected. Template harness applied.")
        safe_write(dest_path, merged, "full", False)


def _split_at_boundary(content):
    if CLAUDE_BOUNDARY in content:
        idx = content.index(CLAUDE_BOUNDARY)
        return content[:idx], content[idx:]
    return content, ""


def _extract_user_additions(old_harness, new_harness):
    old_lines = old_harness.strip().splitlines()
    new_lines = new_harness.strip().splitlines()
    new_set = set(line.strip() for line in new_lines if line.strip())

    additions = []
    for line in old_lines:
        if line.strip() and line.strip() not in new_set:
            additions.append(line)

    return "\n".join(additions) if additions else ""


# ============================================================
# Section-level deduplication for MIGRATE path
# ============================================================

_YAML_FRONT = re.compile(r"\A---\n.*?\n---\n*", re.DOTALL)


def _extract_sections(content):
    """Split markdown into sections by ## headings, stripping YAML frontmatter.

    Returns list of (heading, body) tuples. The first entry may have an
    empty heading if there is preamble text before the first ## heading.
    """
    stripped = _YAML_FRONT.sub("", content, count=1)

    sections = []
    heading = ""
    body_lines = []

    for line in stripped.split("\n"):
        if line.startswith("## "):
            if heading or body_lines:
                sections.append((heading, "\n".join(body_lines).strip()))
            heading = line
            body_lines = []
        else:
            body_lines.append(line)

    if heading or body_lines:
        sections.append((heading, "\n".join(body_lines).strip()))

    return sections


def _normalize_for_compare(text):
    """Normalize text for similarity comparison.

    Strips emoji, arrow variants, HTML comments, and collapses whitespace
    so that two versions of the same rule (one with emoji, one without)
    produce a high similarity score.
    """
    for ch in EMOJI_CHARS:
        text = text.replace(ch, "")
    text = text.replace("\u2192", "->")  # arrow normalization
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _deduplicate_sections(existing, new_content, threshold=0.50):
    """Find sections in *existing* that have no close match in *new_content*.

    Returns a list of (heading, body) tuples for genuinely unique sections.
    """
    old_sections = _extract_sections(existing)
    new_sections = _extract_sections(new_content)

    if not old_sections:
        return []

    new_normalized = []
    for h, b in new_sections:
        full = "{}\n{}".format(h, b).strip()
        new_normalized.append(_normalize_for_compare(full))

    unique = []
    for old_h, old_b in old_sections:
        old_full = "{}\n{}".format(old_h, old_b).strip()
        if not old_full:
            continue

        old_norm = _normalize_for_compare(old_full)
        if not old_norm:
            continue

        best_ratio = 0.0
        for new_norm in new_normalized:
            ratio = difflib.SequenceMatcher(None, old_norm, new_norm).ratio()
            if ratio > best_ratio:
                best_ratio = ratio

        label = old_h[:60] if old_h else "(preamble)"
        safe_label = label.encode("ascii", "replace").decode("ascii")
        if best_ratio < threshold:
            unique.append((old_h, old_b))
            print("  [UNIQUE]  {} (best {:.0f}%)".format(safe_label, best_ratio * 100))
        else:
            print("  [DUP]     {} ({:.0f}% match, skipped)".format(
                safe_label, best_ratio * 100))

    return unique


def generate_all(project_root, manifest, dry_run):
    harness_dir = find_harness_dir()
    output_dir = os.path.join(project_root, CLAUDE)
    content_dir = os.path.join(project_root, BOOTSTRAP_OUTPUT, "content")
    merge_mode = manifest.get("merge_mode", "full")
    tech_stack = manifest.get("tech_stack", "")
    modules = manifest.get("modules", [])
    optional = manifest.get("optional_skills", {})
    profile = manifest.get("profile", "standard")

    copy_core_files(project_root, manifest, dry_run)

    print("\n=== Generating CLAUDE.md ===")
    claude_template = os.path.join(harness_dir, "templates/CLAUDE.template.md")
    if os.path.isfile(claude_template):
        claude_content = read_file(claude_template)
        claude_content, _ = replace_placeholders(
            claude_content, build_claude_placeholders(manifest, content_dir))
        claude_content = process_conditionals(claude_content, tech_stack)
        merge_claude_md(os.path.join(project_root, "CLAUDE.md"), claude_content, dry_run)
    else:
        print("  [ERROR]  Template not found: {}".format(claude_template))

    print("\n=== Generating architect-skill ===")
    generate_template_dir(
        harness_dir, output_dir,
        "templates/skills/architect.template", "skills/architect-skill",
        build_architect_placeholders(content_dir),
        tech_stack, merge_mode, dry_run,
    )

    for module in modules:
        mid = module["id"]

        print("\n=== Generating programmer-{}-skill ===".format(mid))
        generate_template_dir(
            harness_dir, output_dir,
            "templates/skills/programmer.template",
            "skills/programmer-{}-skill".format(mid),
            build_module_placeholders(module, content_dir),
            tech_stack, merge_mode, dry_run,
        )

    if optional.get("debug", False):
        print("\n=== Generating debug-skill ===")
        generate_template_dir(
            harness_dir, output_dir,
            "templates/skills/debug.template", "skills/debug-skill",
            build_debug_placeholders(content_dir),
            tech_stack, merge_mode, dry_run,
        )

    if optional.get("profiler", False):
        print("\n=== Generating profiler-skill ===")
        generate_template_dir(
            harness_dir, output_dir,
            "templates/skills/profiler.template", "skills/profiler-skill",
            build_profiler_placeholders(content_dir),
            tech_stack, merge_mode, dry_run,
        )

    copy_templates(project_root, merge_mode, dry_run)
    check_content_quality(content_dir, optional)


def generate_single_skill(project_root, manifest, skill_name, dry_run):
    """Generate a single skill by name (for incremental/parallel workflows)."""
    harness_dir = find_harness_dir()
    output_dir = os.path.join(project_root, CLAUDE)
    content_dir = os.path.join(project_root, BOOTSTRAP_OUTPUT, "content")
    merge_mode = manifest.get("merge_mode", "full")
    tech_stack = manifest.get("tech_stack", "")
    modules = manifest.get("modules", [])
    optional = manifest.get("optional_skills", {})
    profile = manifest.get("profile", "standard")

    if skill_name == "core":
        copy_core_files(project_root, manifest, dry_run)
        return

    if skill_name == "claude":
        print("\n=== Generating CLAUDE.md ===")
        claude_template = os.path.join(harness_dir, "templates/CLAUDE.template.md")
        if os.path.isfile(claude_template):
            claude_content = read_file(claude_template)
            claude_content, _ = replace_placeholders(
                claude_content, build_claude_placeholders(manifest, content_dir))
            claude_content = process_conditionals(claude_content, tech_stack)
            merge_claude_md(os.path.join(project_root, "CLAUDE.md"), claude_content, dry_run)
        else:
            print("  [ERROR]  Template not found: {}".format(claude_template))
        return

    if skill_name == "architect":
        print("\n=== Generating architect-skill ===")
        generate_template_dir(
            harness_dir, output_dir,
            "templates/skills/architect.template", "skills/architect-skill",
            build_architect_placeholders(content_dir),
            tech_stack, merge_mode, dry_run,
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
            tech_stack, merge_mode, dry_run,
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
            tech_stack, merge_mode, dry_run,
        )
        return

    if skill_name == "templates":
        copy_templates(project_root, merge_mode, dry_run)
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
            tech_stack, merge_mode, dry_run,
        )
        return

    print("Error: Unknown skill '{}'. Available: core, claude, architect, debug, profiler, templates, or a module id.".format(skill_name))
    sys.exit(1)


def generate_agent(project_root, manifest, module_id, dry_run):
    """Generate a programmer-agent for a module (called on-demand, not by default)."""
    harness_dir = find_harness_dir()
    output_dir = os.path.join(project_root, CLAUDE)
    merge_mode = manifest.get("merge_mode", "full")
    tech_stack = manifest.get("tech_stack", "")
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
        tech_stack, merge_mode, dry_run,
    )


def copy_templates(project_root, merge_mode, dry_run):
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
            safe_copy_dir(src, dst, merge_mode, dry_run)
        elif os.path.isfile(src):
            safe_copy_file(src, dst, merge_mode, dry_run)


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


# ============================================================
# Validation
# ============================================================

def validate_skill_dir(skill_path):
    errors = []

    if not os.path.isdir(skill_path):
        return ["Not a directory"], True

    md_files = sorted(f for f in os.listdir(skill_path) if f.endswith(".md"))
    expected = ["EXAMPLES.md", "ITERATION_GUIDE.md", "SKILL.md", "SKILL_MEMORY.md"]

    if md_files != expected:
        return [], True  # non-standard structure, skip silently

    skill_content = read_file(os.path.join(skill_path, "SKILL.md"))
    if not ("name:" in skill_content[:500] and "description:" in skill_content[:500]):
        errors.append("SKILL.md missing YAML metadata (name/description)")

    for fname in expected:
        content = read_file(os.path.join(skill_path, fname))
        if "{{" in content and "}}" in content:
            errors.append("{} has residual placeholder(s)".format(fname))

    for fname in expected:
        content = read_file(os.path.join(skill_path, fname))
        found = set(ch for ch in content if ch in EMOJI_CHARS)
        if found:
            codes = ", ".join("U+{:04X}".format(ord(ch)) for ch in sorted(found))
            errors.append("{} contains emoji/symbols ({})".format(fname, codes))

    for fname in ["SKILL_MEMORY.md", "ITERATION_GUIDE.md"]:
        content = read_file(os.path.join(skill_path, fname))
        matches = DATE_PATTERN.findall(content)
        if matches:
            errors.append("{} contains date(s): {}".format(fname, ", ".join(matches)))

    return errors, False


def validate_all(project_root):
    print("\n=== Validation Report ===\n")
    skills_dir = os.path.join(project_root, CLAUDE, "skills")

    if not os.path.isdir(skills_dir):
        print("  [FAIL] {}/skills/ directory not found".format(CLAUDE))
        return False

    all_pass = True
    checked = 0

    for entry in sorted(os.listdir(skills_dir)):
        entry_path = os.path.join(skills_dir, entry)
        if not os.path.isdir(entry_path):
            continue

        errors, skipped = validate_skill_dir(entry_path)

        if skipped:
            continue

        checked += 1
        if errors:
            all_pass = False
            print("  [FAIL]   {}".format(entry))
            for e in errors:
                print("             - {}".format(e))
        else:
            print("  [PASS]   {}".format(entry))

    print("\n  Checked: {} skill(s)".format(checked))
    if all_pass and checked > 0:
        print("  Result:  ALL PASS")
    elif checked == 0:
        print("  Result:  No standard skills found to validate")
    else:
        print("  Result:  SOME FAILED - see above")

    return all_pass


# ============================================================
# Entry Point
# ============================================================

def find_harness_dir():
    """Locate the .castflow/ directory (always relative to this script)."""
    return os.path.dirname(os.path.abspath(__file__))


def find_project_root(explicit_root=None):
    """Locate the project root directory.

    Search strategy:
    1. Explicit --project-root argument (trusted if given)
    2. Walk up from script location looking for .claude/
    3. If not found, use the harness parent's parent as project root
       (e.g. project/CostFlow/.castflow/ -> project root = project/)
       and create .claude/ there
    """
    if explicit_root:
        return os.path.abspath(explicit_root)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    start = os.path.dirname(script_dir)

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


def load_manifest(project_root):
    manifest_path = os.path.join(project_root, BOOTSTRAP_OUTPUT, "manifest.json")

    if not os.path.isfile(manifest_path):
        print("Error: Manifest not found at {}".format(manifest_path))
        print("  AI must generate {}/manifest.json first.".format(BOOTSTRAP_OUTPUT))

        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8-sig") as f:
        manifest = json.load(f)

    version = manifest.get("version")
    if version not in SUPPORTED_VERSIONS:
        print("Error: Manifest version {} not supported (expected {}).".format(
            version, SUPPORTED_VERSIONS))
        sys.exit(1)

    if "modules" not in manifest:
        print("Error: Manifest missing 'modules' field.")
        sys.exit(1)

    seen_ids = set()
    for i, mod in enumerate(manifest["modules"]):
        if "id" not in mod:
            print("Error: Module at index {} missing 'id'.".format(i))
            sys.exit(1)
        if "display_name" not in mod:
            print("Error: Module '{}' missing 'display_name'.".format(mod["id"]))
            sys.exit(1)
        if mod["id"] in seen_ids:
            print("Error: Duplicate module id '{}'.".format(mod["id"]))
            sys.exit(1)
        seen_ids.add(mod["id"])

    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="CastFlow Bootstrap - Deterministic file generator",
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Validate .claude/ output against SKILL_RULE standards",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview operations without writing files",
    )
    parser.add_argument(
        "--skill", type=str, default=None,
        help="Generate a single skill incrementally (e.g. architect, debug, profiler, core, claude, templates, or a module id)",
    )
    parser.add_argument(
        "--agent", type=str, default=None,
        help="Generate a programmer-agent for a module (e.g. --agent building). Requires module in manifest.",
    )
    parser.add_argument(
        "--project-root", type=str, default=None,
        help="Explicit project root path (must contain .claude/ directory).",
    )
    args = parser.parse_args()

    project_root = find_project_root(args.project_root)
    harness_dir = find_harness_dir()
    print("Project root: {}".format(project_root))
    print("Harness dir:  {}".format(harness_dir))

    if args.validate:
        success = validate_all(project_root)
        sys.exit(0 if success else 1)

    manifest = load_manifest(project_root)
    modules_str = ", ".join(m["id"] for m in manifest["modules"])
    print("Manifest v{} | {} | {} | merge={}".format(
        manifest["version"],
        manifest.get("tech_stack", "?"),
        manifest.get("profile", "standard"),
        manifest.get("merge_mode", "full"),
    ))
    print("Modules: {}".format(modules_str))

    if args.dry_run:
        print("\n*** DRY RUN - no files will be written ***")

    if args.agent:
        print("\n=== Agent generation: programmer-{}-agent ===".format(args.agent))
        generate_agent(project_root, manifest, args.agent, args.dry_run)
    elif args.skill:
        print("\n=== Incremental generation: {} ===".format(args.skill))
        generate_single_skill(project_root, manifest, args.skill, args.dry_run)
    else:
        generate_all(project_root, manifest, args.dry_run)

    print("\n=== Generation complete ===")
    if not args.dry_run:
        print("\nRun 'python .castflow/bootstrap.py --validate' to verify output.")


if __name__ == "__main__":
    main()
