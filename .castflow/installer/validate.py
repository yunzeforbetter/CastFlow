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


_OPTIONAL_ROLES = (
    "EXAMPLES.md",
    "SKILL_MEMORY.md",
    "ITERATION_GUIDE.md",
)


def _rel_posix(dirpath, skill_path, fname):
    rel = os.path.relpath(dirpath, skill_path)
    if rel == ".":
        return fname
    return os.path.join(rel, fname).replace("\\", "/")


def _walk_skill_files(skill_path):
    """Return (markdown paths, non-markdown paths) relative to the skill root."""
    markdown = []
    attachments = []
    for dirpath, dirnames, filenames in os.walk(skill_path):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fname in filenames:
            rel = _rel_posix(dirpath, skill_path, fname)
            if fname.endswith(".md"):
                markdown.append(rel)
            else:
                attachments.append(rel)
    return markdown, attachments


def _is_catalog_skill(md_paths):
    """True when this directory uses the catalog slots.

    A subset of the four role names is a catalog skill. Extra markdown is
    still catalog when a role file besides SKILL.md is present, or when the
    extra file sits next to SKILL.md. Nested markdown with only SKILL.md is
    freeform (skill-creator) and stays skipped.
    """
    if "SKILL.md" not in md_paths:
        return False
    extra = [path for path in md_paths if path not in EXPECTED_MD]
    if not extra:
        return True
    if any(path in md_paths for path in _OPTIONAL_ROLES):
        return True
    return any("/" not in path for path in extra)


def _body_without_frontmatter(content):
    text = (content or "").lstrip("\ufeff")
    if text.startswith("---"):
        rest = text[3:]
        end = rest.find("\n---")
        if end >= 0:
            return rest[end + 4:]
    return text


def _is_heading_only(content):
    """True when the body is empty or every remaining line is a heading."""
    lines = [
        line.strip()
        for line in _body_without_frontmatter(content).splitlines()
        if line.strip()
    ]
    if not lines:
        return True
    return all(line.startswith("#") for line in lines)


def _attachment_pointer_errors(attachments, role_text):
    errors = []
    for rel in attachments:
        base = rel.split("/")[-1]
        if rel in role_text or base in role_text:
            continue
        errors.append(
            "attachment has no pointer in a role file: {}".format(rel)
        )
    return errors


def validate_skill_dir(skill_path):
    """Validate a single skill directory.

    Returns (errors, warnings, skipped).
    Catalog shape is SKILL.md plus any subset of the other three role files.
    Missing optional role files are not errors. Freeform directories are skipped.
    Extra markdown, a heading-only role file, or an unpointed attachment fails.
    """
    errors = []
    warnings = []

    if not os.path.isdir(skill_path):
        return ["Not a directory"], [], True

    md_paths, attachments = _walk_skill_files(skill_path)
    if not _is_catalog_skill(md_paths):
        return [], [], True

    extra_md = [path for path in md_paths if path not in EXPECTED_MD]
    if extra_md:
        errors.append(
            "extra markdown not allowed in generated skill: {}".format(
                ", ".join(extra_md)
            )
        )

    file_contents = {}
    for fname in EXPECTED_MD:
        path = os.path.join(skill_path, fname)
        if not os.path.isfile(path):
            continue
        content = _read_file(path)
        if fname != "SKILL.md" and _is_heading_only(content):
            errors.append(
                "{} is an empty or heading-only role file; delete it "
                "instead of leaving a stub".format(fname)
            )
        file_contents[fname] = content

    skill_content = file_contents.get("SKILL.md", "")
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

    for fname, content in file_contents.items():
        if "{{" in content and "}}" in content:
            errors.append("{} has residual placeholder(s)".format(fname))
        found = set(ch for ch in content if ch in EMOJI_CHARS)
        if found:
            codes = ", ".join("U+{:04X}".format(ord(ch)) for ch in sorted(found))
            errors.append("{} contains emoji/symbols ({})".format(fname, codes))

    for fname in ["SKILL_MEMORY.md", "ITERATION_GUIDE.md"]:
        content = file_contents.get(fname)
        if content is None:
            continue
        matches = DATE_PATTERN.findall(content)
        if matches:
            errors.append("{} contains date(s): {}".format(fname, ", ".join(matches)))

    for fname, content in file_contents.items():
        if fname not in SIZE_LIMITS:
            continue
        size = _count_size_units(content)
        limit = SIZE_LIMITS[fname]
        if size > limit:
            warnings.append(
                "{} size {} units exceeds recommended {} (excluding code fences); "
                "delete or merge in place, do not add files".format(
                    fname, size, limit
                )
            )

    errors.extend(
        _attachment_pointer_errors(attachments, "\n".join(file_contents.values()))
    )
    return errors, warnings, False


def _is_programmer_skill_name(name):
    name = (name or "").strip()
    return name.startswith("programmer-") and name.endswith("-skill")


_SOURCE_SUFFIXES = frozenset((
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts",
    ".vue", ".svelte", ".astro", ".py", ".pyw", ".pyi", ".cs", ".csx",
    ".fs", ".fsx", ".fsi", ".vb", ".java", ".kt", ".kts", ".scala",
    ".sc", ".groovy", ".clj", ".cljs", ".cljc", ".c", ".h", ".cc",
    ".cpp", ".cxx", ".hpp", ".hh", ".m", ".mm", ".go", ".rs", ".swift",
    ".dart", ".php", ".rb", ".rake", ".lua", ".ex", ".exs", ".hs",
    ".ml", ".zig", ".nim", ".pl", ".r", ".jl", ".sh", ".ps1", ".sql",
    ".proto", ".sol",
))
_SKIP_SOURCE_DIRS = frozenset((
    ".git", ".castflow", ".castflow-runtime", ".claude", ".agents",
    ".cursor", ".grok", "Library", "Temp", "obj", "node_modules",
    "vendor", "Packages", "__pycache__",
))
_KEYWORDS = frozenset("""
if else elif return throw new void int long short byte bool float double
string object decimal dynamic var let const true false null this base
public private protected internal static for while foreach switch case
break continue catch try finally using namespace class struct enum
interface await async task Task override virtual sealed partial readonly
get set value out ref params in is as not and or typeof sizeof default
checked unchecked lock do from where select group by join on equals into
orderby ascending descending yield when nameof stackalloc fixed unsafe
extern volatile implicit explicit operator event delegate record init
required file global alias fun function def export final abstract
""".split())
_METHOD_SIG_RE = re.compile(
    r"^(?:(?:public|private|protected|internal|static|readonly|const|"
    r"abstract|virtual|override|partial|sealed|extern|unsafe|async|"
    r"export|final|new)\s+)*"
    r"(?:void|int|long|short|byte|bool|float|double|string|object|"
    r"decimal|dynamic|Task|var)\s+\w+\s*\(",
    re.IGNORECASE,
)
_FIELD_RE = re.compile(
    r"^(?:(?:public|private|protected|internal|static|readonly|const|"
    r"volatile)\s+)+[\w.<>,\[\]?]+\s+\w+\s*(?:=|;)",
    re.IGNORECASE,
)
_TYPE_RE = re.compile(r"\b(class|interface|enum|struct|record)\b")
_PUBLISH_RE = re.compile(r"\b(Publish|Invoke)\s*\(")
_SUBSCRIBE_RE = re.compile(r"\b(Subscribe|AddListener)\s*\(|\+=")
_CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_IDENT = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
_PATH_LINE_RE = re.compile(
    r"([A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+):(\d+)"
)
_CALL_KEYWORDS = frozenset((
    "if", "for", "while", "switch", "catch", "return", "lock", "using",
    "sizeof", "typeof", "nameof", "foreach", "new",
))


def _strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*?$", "", text, flags=re.M)
    return text


def _brace_interior(text, open_index):
    depth = 0
    i = open_index
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[open_index + 1:i]
        i += 1
    return ""


def _body_from_signature(file_text, line_index):
    """Return the brace interior after a signature, or None if there is none."""
    lines = file_text.splitlines()
    rest = "\n".join(lines[line_index:])
    brace = rest.find("{")
    semi = rest.find(";")
    if brace < 0:
        return None
    if semi != -1 and semi < brace:
        return None
    return _brace_interior(rest, brace)


def _line_is_method_sig(line):
    return bool(_METHOD_SIG_RE.match(line.strip()))


def _line_kind(line):
    """declaration, empty-or-not is decided by the caller; publish; call; other."""
    stripped = line.strip()
    if _PUBLISH_RE.search(stripped):
        return "publish"
    if _line_is_method_sig(stripped) or _TYPE_RE.search(stripped):
        return "declaration"
    if _FIELD_RE.match(stripped):
        return "declaration"
    if _CALL_RE.search(stripped):
        return "call"
    return "other"


def _iter_source_files(project_root):
    root = os.path.abspath(project_root)
    found = []
    if not os.path.isdir(root):
        return found
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_SOURCE_DIRS]
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in _SOURCE_SUFFIXES:
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root).replace("\\", "/")
            try:
                text = _read_file(full)
            except (OSError, UnicodeError):
                continue
            found.append((rel, text))
    return found


def _resolve_inside(project_root, rel_path):
    root = os.path.abspath(project_root)
    rel = (rel_path or "").replace("\\", "/").lstrip("/")
    full = os.path.normpath(os.path.join(root, rel.replace("/", os.sep)))
    if os.path.commonpath([root, full]) != root:
        return None
    if not os.path.isfile(full):
        return None
    return full


def _cited_line(project_root, sources, ref_text, code_text):
    """Return (rel, line_no, line_text) or None. line_no is 1-based."""
    match = _PATH_LINE_RE.search(ref_text or "")
    if match:
        full = _resolve_inside(project_root, match.group(1))
        if full is None:
            return None
        rel = os.path.relpath(full, os.path.abspath(project_root)).replace("\\", "/")
        text = None
        for src_rel, src_text in sources:
            if src_rel == rel:
                text = src_text
                break
        if text is None:
            try:
                text = _read_file(full)
            except (OSError, UnicodeError):
                return None
        lines = text.splitlines()
        line_no = int(match.group(2))
        if line_no < 1 or line_no > len(lines):
            return None
        return rel, line_no, lines[line_no - 1]
    snippet = ""
    for raw in (code_text or "").splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("```"):
            snippet = stripped
            break
    if not snippet:
        return None
    for rel, text in sources:
        for line_no, line in enumerate(text.splitlines(), 1):
            if snippet in line:
                return rel, line_no, line
    return None


def _example_blocks(examples_text):
    if not examples_text or not examples_text.strip():
        return []
    parts = re.split(r"(?m)^## ", examples_text)
    blocks = []
    for part in parts[1:]:
        fences = re.findall(r"```[^\n]*\n(.*?)```", part, flags=re.S)
        code = "\n".join(fences)
        ref_lines = []
        seen_ref = False
        for line in part.splitlines():
            if line.strip().lower() == "project reference":
                seen_ref = True
                continue
            if seen_ref:
                if not line.strip() or line.startswith("#"):
                    break
                ref_lines.append(line)
        blocks.append({
            "text": part,
            "code": code,
            "ref": "\n".join(ref_lines),
        })
    return blocks


def _param_names(param_src):
    names = []
    for part in (param_src or "").split(","):
        part = re.sub(r"=.*", "", part).strip()
        part = re.sub(r"\b(ref|out|in|params|this)\b", "", part, flags=re.I)
        tokens = _IDENT.findall(part)
        if tokens:
            names.append(tokens[-1])
    return names


def _definitions(sources, name):
    """Yield (params, body_text) for declaration lines of name that have a body."""
    sig = re.compile(r"\b" + re.escape(name) + r"\s*\(([^)]*)\)")
    for _rel, text in sources:
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if not sig.search(line):
                continue
            if not _line_is_method_sig(line):
                continue
            body = _body_from_signature(text, index)
            if body is None:
                continue
            match = sig.search(line)
            yield match.group(1), body


def _gap_tokens(sources, call_line):
    """Identifiers the body uses that the signature does not name."""
    gaps = []
    seen = set()
    for name in _CALL_RE.findall(call_line or ""):
        if name in _CALL_KEYWORDS or name in _KEYWORDS:
            continue
        for params, body in _definitions(sources, name):
            param_names = set(_param_names(params))
            interior = _strip_comments(body)
            if not _IDENT.findall(interior):
                continue
            for token in _IDENT.findall(interior):
                if token in _KEYWORDS or token in param_names or token == name:
                    continue
                if token not in seen:
                    seen.add(token)
                    gaps.append(token)
    return gaps


def _memory_entries(memory_text):
    if not memory_text or not memory_text.strip():
        return []
    parts = re.split(r"(?m)^### ", memory_text)
    entries = []
    for part in parts[1:]:
        heading = part.splitlines()[0].strip() if part.strip() else ""
        if heading.upper().startswith("[RETIRED]"):
            continue
        entries.append(part)
    return entries


def _anchor_symbols(entry_text):
    symbols = []
    for line in entry_text.splitlines():
        if not line.strip().lower().startswith("anchors:"):
            continue
        for bracket in re.findall(r"\[([^\]]+)\]", line):
            for piece in bracket.split(","):
                tail = piece.strip().split(":")[-1].split("/")[-1].strip()
                if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", tail):
                    symbols.append(tail)
    return symbols


def _symbol_greps(sources, symbol):
    pattern = re.compile(r"\b" + re.escape(symbol) + r"\b")
    for _rel, text in sources:
        if pattern.search(text):
            return True
    return False


def _entry_identifiers(entry_text):
    body_lines = []
    for line in entry_text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("anchors:") or stripped.lower().startswith("related:"):
            continue
        body_lines.append(line)
    return _IDENT.findall("\n".join(body_lines))


def _signature_names(sources, call_line):
    names = set()
    for name in _CALL_RE.findall(call_line or ""):
        if name in _CALL_KEYWORDS or name in _KEYWORDS:
            continue
        names.add(name)
        for params, _body in _definitions(sources, name):
            names.update(_param_names(params))
    return names


def check_programmer_skill(skill_dir, project_root):
    """Accept or reject a programmer skill against a source tree.

    Pure: skill text plus the tree. No model call. Empty means accept.
    A missing memory file is accepted when every cited usage is a call site
    and none of those calls has a signature gap.
    """
    skill_dir = os.path.abspath(skill_dir)
    name = os.path.basename(os.path.normpath(skill_dir))
    if not _is_programmer_skill_name(name):
        return []
    sources = _iter_source_files(project_root)
    examples_path = os.path.join(skill_dir, "EXAMPLES.md")
    memory_path = os.path.join(skill_dir, "SKILL_MEMORY.md")
    skill_path = os.path.join(skill_dir, "SKILL.md")
    examples = _read_file(examples_path) if os.path.isfile(examples_path) else ""
    memory = _read_file(memory_path) if os.path.isfile(memory_path) else ""
    skill_md = _read_file(skill_path) if os.path.isfile(skill_path) else ""
    prose = "\n".join((skill_md, examples, memory))
    prose_outside_fences = re.sub(r"```.*?```", "", prose, flags=re.S)
    mentions_registry = bool(re.search(r"\bregistry\b", prose_outside_fences, re.I))

    errors = []
    call_lines = []
    blocks = _example_blocks(examples)
    if not blocks and examples.strip():
        blocks = [{"text": examples, "code": "", "ref": examples}]
    for block in blocks:
        cited = _cited_line(project_root, sources, block.get("ref", ""), block.get("code", ""))
        if cited is None:
            errors.append("call site does not resolve")
            continue
        _rel, _line_no, line_text = cited
        file_text = ""
        for src_rel, src_text in sources:
            if src_rel == _rel:
                file_text = src_text
                break
        if not file_text:
            full = _resolve_inside(project_root, _rel)
            if full:
                file_text = _read_file(full)
        kind = _line_kind(line_text)
        if kind == "publish":
            blob = "\n".join(text for _src, text in sources)
            if not _SUBSCRIBE_RE.search(blob):
                errors.append("call site is a publish with no subscriber")
            else:
                call_lines.append(line_text)
            continue
        if kind == "declaration":
            body = None
            if file_text and _line_is_method_sig(line_text):
                body = _body_from_signature(file_text, _line_no - 1)
            if body is not None and not _IDENT.findall(_strip_comments(body)):
                errors.append("call site is an empty body")
            else:
                errors.append("call site is a declaration")
            continue
        if kind != "call":
            errors.append("call site is a declaration")
            continue
        call_lines.append(line_text)
        if mentions_registry:
            errors.append("call site is written up as a registry")

    gaps = []
    seen_gaps = set()
    signature_names = set()
    for line_text in call_lines:
        signature_names.update(_signature_names(sources, line_text))
        for token in _gap_tokens(sources, line_text):
            if token not in seen_gaps:
                seen_gaps.add(token)
                gaps.append(token)

    entries = _memory_entries(memory)
    if gaps:
        covers = False
        repeats = False
        for entry in entries:
            idents = set(_entry_identifiers(entry))
            if any(token in idents for token in gaps):
                covers = True
            elif idents & signature_names:
                repeats = True
        if not covers and repeats:
            errors.append("signature gap repeats the signature")
        elif not covers:
            errors.append("signature gap missing from memory")

    for entry in entries:
        symbols = _anchor_symbols(entry)
        if not symbols or any(not _symbol_greps(sources, symbol) for symbol in symbols):
            errors.append("memory anchor does not grep")

    # Stable order, no duplicates, so a second run prints the same lines.
    unique = []
    for error in errors:
        if error not in unique:
            unique.append(error)
    return unique


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

        if _is_programmer_skill_name(entry):
            errors = list(errors) + check_programmer_skill(entry_path, project_root)

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
