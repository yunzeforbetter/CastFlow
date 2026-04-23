"""Template processing: placeholder replacement and conditional blocks."""

import re

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")


def replace_placeholders(content, placeholders, strict=False):
    """Replace {{KEY}} tokens in content. Returns (content, warnings).

    In strict mode, any token in content that is NOT in placeholders
    raises ValueError (fail-fast for unknown keys).
    """
    warnings = []

    if strict:
        tokens_in_content = set(_PLACEHOLDER_RE.findall(content))
        unknown = tokens_in_content - set(placeholders.keys())
        if unknown:
            raise ValueError(
                "Unknown placeholder(s) in template: {}".format(
                    ", ".join(sorted(unknown))))

    for key, value in placeholders.items():
        token = "{{" + key + "}}"
        if token not in content:
            continue
        if value is not None:
            content = content.replace(token, value)
        else:
            warnings.append(key)
    return content, warnings


def process_conditionals(content, tech_stack, language="zh"):
    """Process conditional blocks: <!-- if:unity --> ... <!-- endif -->

    The language parameter is kept for future conditional-block support
    but is currently unused; multilingual generation is driven by
    bootstrap-skill injecting language into sub-agent prompts.
    """
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
    """Load content file from the bootstrap-output/content directory."""
    import os
    if not relative_path:
        return None
    path = os.path.join(content_dir, relative_path)
    if os.path.isfile(path):
        from .io_ops import read_file
        return read_file(path).strip()
    return None
