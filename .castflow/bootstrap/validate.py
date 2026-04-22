"""Skill directory validation against SKILL_ITERATION standards."""

import os
import re

from .io_ops import read_file
from .paths import CLAUDE

EMOJI_CHARS = set(
    "\u274c\u2705\u2b50\U0001f4cb\U0001f534\U0001f7e1\U0001f7e2"
    "\u2713\u2717\u2192\u2194\u2190\u2193\u2191"
    "\u25ba\u25bc\u25b2\u25c4\u25c6\u2605"
)

DATE_PATTERN = re.compile(r"20[2-3]\d[-/]\d{1,2}[-/]\d{1,2}")

SIZE_LIMITS = {
    "SKILL.md": 4000,
    "EXAMPLES.md": 14000,
    "SKILL_MEMORY.md": 9000,
    "ITERATION_GUIDE.md": 4500,
}


def _count_size_units(content):
    """Count non-whitespace characters as a uniform size proxy.

    Excludes fenced code blocks so example-heavy files are not over-penalized.
    """
    in_code = False
    kept = []
    for line in content.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if not in_code:
            kept.append(line)
    text = "".join(kept)
    return sum(1 for ch in text if not ch.isspace())


def validate_skill_dir(skill_path):
    """Validate a single skill directory.

    Returns (errors, warnings, skipped).
    """
    errors = []
    warnings = []

    if not os.path.isdir(skill_path):
        return ["Not a directory"], [], True

    md_files = sorted(f for f in os.listdir(skill_path) if f.endswith(".md"))
    expected = ["EXAMPLES.md", "ITERATION_GUIDE.md", "SKILL.md", "SKILL_MEMORY.md"]

    if md_files != expected:
        return [], [], True

    file_contents = {}
    for fname in expected:
        file_contents[fname] = read_file(os.path.join(skill_path, fname))

    skill_content = file_contents["SKILL.md"]
    if not ("name:" in skill_content[:500] and "description:" in skill_content[:500]):
        errors.append("SKILL.md missing YAML metadata (name/description)")

    for fname in expected:
        content = file_contents[fname]
        if "{{" in content and "}}" in content:
            errors.append("{} has residual placeholder(s)".format(fname))

    for fname in expected:
        content = file_contents[fname]
        found = set(ch for ch in content if ch in EMOJI_CHARS)
        if found:
            codes = ", ".join("U+{:04X}".format(ord(ch)) for ch in sorted(found))
            errors.append("{} contains emoji/symbols ({})".format(fname, codes))

    for fname in ["SKILL_MEMORY.md", "ITERATION_GUIDE.md"]:
        content = file_contents[fname]
        matches = DATE_PATTERN.findall(content)
        if matches:
            errors.append("{} contains date(s): {}".format(fname, ", ".join(matches)))

    for fname in expected:
        if fname not in SIZE_LIMITS:
            continue
        content = file_contents[fname]
        size = _count_size_units(content)
        limit = SIZE_LIMITS[fname]
        if size > limit:
            warnings.append(
                "{} size {} units exceeds recommended {} (excluding code fences); "
                "consider splitting per SKILL_ITERATION.md".format(fname, size, limit)
            )

    return errors, warnings, False


def validate_all(project_root):
    """Validate all skill directories under .claude/skills/."""
    print("\n=== Validation Report ===\n")
    skills_dir = os.path.join(project_root, CLAUDE, "skills")

    if not os.path.isdir(skills_dir):
        print("  [FAIL] {}/skills/ directory not found".format(CLAUDE))
        return False

    all_pass = True
    checked = 0
    total_warnings = 0

    for entry in sorted(os.listdir(skills_dir)):
        entry_path = os.path.join(skills_dir, entry)
        if not os.path.isdir(entry_path):
            continue

        errors, warnings, skipped = validate_skill_dir(entry_path)

        if skipped:
            continue

        checked += 1
        if errors:
            all_pass = False
            print("  [FAIL]   {}".format(entry))
            for e in errors:
                print("             - {}".format(e))
        elif warnings:
            print("  [WARN]   {}".format(entry))
        else:
            print("  [PASS]   {}".format(entry))

        for w in warnings:
            total_warnings += 1
            print("             ! {}".format(w))

    print("\n  Checked: {} skill(s)".format(checked))
    if total_warnings:
        print("  Warnings: {} size warning(s)".format(total_warnings))
    if all_pass and checked > 0:
        print("  Result:  ALL PASS")
    elif checked == 0:
        print("  Result:  No standard skills found to validate")
    else:
        print("  Result:  SOME FAILED - see above")

    return all_pass
