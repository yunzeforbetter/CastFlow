"""Skill directory validation against SKILL_ITERATION standards."""

import os
import re

def _read_file(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()

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

EXPECTED_MD = (
    "EXAMPLES.md",
    "ITERATION_GUIDE.md",
    "SKILL.md",
    "SKILL_MEMORY.md",
)

_WHEN_RE = re.compile(
    r"use when|use only|when the user|用于|当用户",
    re.IGNORECASE,
)
_YIELD_RE = re.compile(r"\bNOT\b|not for|让位", re.IGNORECASE)
_SENTENCE_RE = re.compile(r"[.!?。]|use when|when the user|用于", re.IGNORECASE)
_IDENT_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
_DUMP_STOP = frozenset(
    "use when the user says not for or and a an to of in this from "
    "with without only load while".split()
)
_PUSHY_RE = re.compile(
    r"even if (they|the user)|whenever the user mentions|"
    r"make sure to use this skill whenever|即使(没|不)|即使用户没",
    re.IGNORECASE,
)
_PROGRAMMER_DESC_MAX = 280
_DESC_MAX = 240
_NOT_CLAUSE_MAX = 1
_ALLOWED_YAML_KEYS = frozenset(("name", "description"))
_NEXT_YAML_KEY = re.compile(r"^[A-Za-z0-9_-]+:")
_NOT_TOKEN_RE = re.compile(r"\bNOT\b")


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


def extract_yaml_description(skill_content):
    """Return the YAML description scalar from SKILL.md, or empty string."""
    text = skill_content.lstrip()
    if not text.startswith("---"):
        return ""
    rest = text[3:]
    end = rest.find("\n---")
    fm = rest if end < 0 else rest[:end]
    lines = fm.splitlines()
    desc_lines = []
    in_desc = False
    for line in lines:
        if not in_desc:
            if line.startswith("description:"):
                in_desc = True
                rest_line = line[len("description:"):].strip()
                if rest_line in (">", "|", ""):
                    continue
                desc_lines.append(rest_line)
            continue
        if _NEXT_YAML_KEY.match(line) and not line.startswith((" ", "\t")):
            break
        stripped = line.strip()
        if stripped:
            desc_lines.append(stripped)
    return " ".join(desc_lines)


def extract_yaml_frontmatter_keys(skill_content):
    """Return top-level YAML keys from SKILL.md frontmatter."""
    text = skill_content.lstrip()
    if not text.startswith("---"):
        return []
    rest = text[3:]
    end = rest.find("\n---")
    fm = rest if end < 0 else rest[:end]
    keys = []
    for line in fm.splitlines():
        if _NEXT_YAML_KEY.match(line) and not line.startswith((" ", "\t")):
            keys.append(line.split(":", 1)[0])
    return keys


def frontmatter_key_errors(skill_content):
    """Reject host-ignored extra keys such as when-to-use."""
    extra = [
        k for k in extract_yaml_frontmatter_keys(skill_content)
        if k not in _ALLOWED_YAML_KEYS
    ]
    if extra:
        return [
            "SKILL.md YAML has extra key(s): {}; only name and description".format(
                ", ".join(extra)
            )
        ]
    return []


def description_shape_errors(description, skill_name=None):
    """Recall/sensitivity checks: spoken when-to-use + NOT/yield; no keyword dumps.

    Returns a list of error strings (empty if the description is acceptable).
    """
    compact = " ".join((description or "").split())
    if not compact:
        return ["SKILL.md description is empty"]
    errors = []
    has_when = bool(_WHEN_RE.search(compact))
    has_yield = bool(_YIELD_RE.search(compact))
    tokens = _IDENT_RE.findall(compact)
    content_tokens = [t for t in tokens if t.lower() not in _DUMP_STOP]
    looks_dump = (
        not has_when
        and not _SENTENCE_RE.search(compact)
        and len(content_tokens) >= 4
    )
    if looks_dump:
        errors.append(
            "SKILL.md description is a keyword dump; "
            "use spoken when-to-use sentences"
        )
    elif not has_when:
        errors.append(
            "SKILL.md description missing spoken when-to-use "
            "(e.g. Use when ...)"
        )
    if not has_yield:
        errors.append(
            "SKILL.md description missing NOT/yield "
            "(when not to use / sibling skill)"
        )
    if _PUSHY_RE.search(compact):
        errors.append(
            "SKILL.md description is pushy/over-recall "
            "(even-if / whenever-mentions); keep module-specific names"
        )
    not_count = len(_NOT_TOKEN_RE.findall(compact))
    if not_count > _NOT_CLAUSE_MAX:
        errors.append(
            "SKILL.md description lists too many NOT clauses; "
            "keep one distinctive yield, put the rest in the body"
        )
    name = (skill_name or "").strip().lower()
    is_programmer = (
        name.startswith("programmer-") and name.endswith("-skill")
    )
    limit = _PROGRAMMER_DESC_MAX if is_programmer else _DESC_MAX
    if len(compact) > limit:
        if is_programmer:
            errors.append(
                "programmer skill description too long (false-recall); "
                "keep module name/id plus a short NOT"
            )
        else:
            errors.append(
                "SKILL.md description too long (always-on context); "
                "keep WHAT + WHEN + one NOT"
            )
    return errors


def _extra_markdown(skill_path, top_md):
    extra = [f for f in top_md if f not in EXPECTED_MD]
    for dirpath, dirnames, filenames in os.walk(skill_path):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        rel = os.path.relpath(dirpath, skill_path)
        if rel == ".":
            continue
        for fname in filenames:
            if fname.endswith(".md"):
                extra.append(os.path.join(rel, fname).replace("\\", "/"))
    return extra


def validate_skill_dir(skill_path):
    """Validate a single skill directory.

    Returns (errors, warnings, skipped).
    Four role files missing -> skipped (not a generated CastFlow skill).
    Four role files plus extra markdown -> error (invalid generated layout).
    """
    errors = []
    warnings = []

    if not os.path.isdir(skill_path):
        return ["Not a directory"], [], True

    md_files = sorted(f for f in os.listdir(skill_path) if f.endswith(".md"))
    missing = [name for name in EXPECTED_MD if name not in md_files]
    if missing:
        return [], [], True

    extra_md = _extra_markdown(skill_path, md_files)
    if extra_md:
        errors.append(
            "extra markdown not allowed in generated skill: {}".format(
                ", ".join(extra_md)
            )
        )

    file_contents = {}
    for fname in EXPECTED_MD:
        file_contents[fname] = _read_file(os.path.join(skill_path, fname))

    skill_content = file_contents["SKILL.md"]
    if not ("name:" in skill_content[:500] and "description:" in skill_content[:500]):
        errors.append("SKILL.md missing YAML metadata (name/description)")
    else:
        errors.extend(frontmatter_key_errors(skill_content))
        errors.extend(
            description_shape_errors(
                extract_yaml_description(skill_content),
                skill_name=os.path.basename(os.path.normpath(skill_path)),
            )
        )

    for fname in EXPECTED_MD:
        content = file_contents[fname]
        if "{{" in content and "}}" in content:
            errors.append("{} has residual placeholder(s)".format(fname))

    for fname in EXPECTED_MD:
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

    for fname in EXPECTED_MD:
        if fname not in SIZE_LIMITS:
            continue
        content = file_contents[fname]
        size = _count_size_units(content)
        limit = SIZE_LIMITS[fname]
        if size > limit:
            warnings.append(
                "{} size {} units exceeds recommended {} (excluding code fences); "
                "delete or merge in place, do not add files".format(
                    fname, size, limit
                )
            )

    return errors, warnings, False


def _skills_roots(project_root):
    runtime = os.path.join(project_root, ".castflow-runtime", "skills")
    mirrored = os.path.join(project_root, ".claude", "skills")
    roots = []
    if os.path.isdir(runtime):
        roots.append(runtime)
    elif os.path.isdir(mirrored):
        roots.append(mirrored)
    return roots


def validate_all(project_root):
    """Validate four-file skills under runtime (preferred) or .claude/skills/."""
    print("\n=== Validation Report ===\n")
    roots = _skills_roots(project_root)
    if not roots:
        print("  [FAIL] no skills directory (.castflow-runtime/skills or .claude/skills)")
        return False
    skills_dir = roots[0]
    print("  Root: {}".format(skills_dir))

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
