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
