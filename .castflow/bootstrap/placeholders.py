"""Placeholder builders for each template category.

This module is the single source of truth for placeholder keys. Each
``build_*_placeholders`` function declares which placeholders a template
group accepts; their dict keys ARE the schema. There is intentionally no
separate ``placeholders.schema.json`` file - the code is the contract.

Adding a new placeholder requires:
  1. Add the key to the relevant ``build_*_placeholders`` function below.
  2. Reference the placeholder ``{{NEW_KEY}}`` in the corresponding
     ``.template.md`` file.
  3. (Optional) populate the value from a content file via load_content.

Strict mode (``replace_placeholders(..., strict=True)``) compares the
returned dict against the tokens actually present in the template body and
fails fast if the template references unknown keys.
"""

from .templates import load_content


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
