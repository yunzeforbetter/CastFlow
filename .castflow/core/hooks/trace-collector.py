#!/usr/bin/env python3
"""
CastFlow Trace Collector - memory snapshot capture hook.

Triggered on file edit events (Claude Code: PostToolUse/Write|Edit|MultiEdit).
Primary capture path: `.castflow-runtime/memory/*.md` (shared across Claude / Grok / Codex).
Optional inbound: Claude `~/.claude/projects/<slug>/memory/` when config enables it.
Personal `type: user` notes are excluded. Evolution can be disabled in config.json.

Capture gate: first YAML frontmatter fence only. Missing name / unknown type /
type only in the body -> not captured. Quality is ok vs thin (isalnum body).

Zero external dependencies. Python 3.6+.
"""

import json
import os
import re
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)
from _castflow_paths import evolution_enabled, runtime_dir  # noqa: E402
from _homology import parse_anchors  # noqa: E402

TRACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "traces")
MEMORY_SNAPSHOTS_FILE = os.path.join(TRACE_DIR, ".trace_memory_snapshots")
UNFLUSHED_FILE = os.path.join(TRACE_DIR, ".unflushed")

_HOOKS_CONFIG_PATH = os.path.join(TRACE_DIR, "config", "hooks.config.json")

_RUNTIME_MEMORY_RE = re.compile(r"\.castflow-runtime/memory/")
_DEFAULT_MEMORY_DIR_PATTERN = r"\.claude/projects/[^/]+/memory/"
_MEMORY_SNAPSHOT_MAX_BYTES = 8 * 1024
_MEMORY_SNAPSHOTS_MAX = 5
_ALLOWED_TYPES = ("feedback", "project", "reference")
_FRONTMATTER_KEY = re.compile(r"^([A-Za-z][A-Za-z0-9_]*):\s*(.*)$")
_MIN_DESCRIPTION = 8
_MIN_SIGNAL_CHARS = 20


def _load_memory_dir_pattern():
    """Load memory dir pattern from hooks.config.json, fall back to default."""
    memory_pattern = _DEFAULT_MEMORY_DIR_PATTERN
    if os.path.isfile(_HOOKS_CONFIG_PATH):
        try:
            with open(_HOOKS_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data.get("memory_dir_pattern"), str) and data["memory_dir_pattern"]:
                memory_pattern = data["memory_dir_pattern"]
        except (json.JSONDecodeError, OSError):
            pass
    return memory_pattern


try:
    _MEMORY_DIR_RE = re.compile(_load_memory_dir_pattern())
except re.error:
    _MEMORY_DIR_RE = re.compile(_DEFAULT_MEMORY_DIR_PATTERN)


def extract_file_path(event_data):
    """Extract file path from hook event JSON, handling both Cursor and Claude Code formats."""
    if not event_data:
        return None

    for key_path in [
        ["input", "filePath"],
        ["input", "path"],
        ["tool_input", "file_path"],
        ["tool_input", "filePath"],
        ["tool_input", "path"],
    ]:
        obj = event_data
        for key in key_path:
            if isinstance(obj, dict):
                obj = obj.get(key)
            else:
                obj = None
                break
        if obj and isinstance(obj, str):
            return obj

    return None


def _bind_runtime_trace_dir():
    """Point snapshot store at `.castflow-runtime/traces/` when present."""
    global TRACE_DIR, MEMORY_SNAPSHOTS_FILE, UNFLUSHED_FILE, _HOOKS_CONFIG_PATH
    rt = runtime_dir()
    traces = os.path.join(rt, "traces")
    if os.path.isdir(rt):
        TRACE_DIR = traces
        MEMORY_SNAPSHOTS_FILE = os.path.join(TRACE_DIR, ".trace_memory_snapshots")
        UNFLUSHED_FILE = os.path.join(TRACE_DIR, ".unflushed")
        _HOOKS_CONFIG_PATH = os.path.join(TRACE_DIR, "config", "hooks.config.json")


def _is_memory_file(file_path):
    """True if this write is a CastFlow (or optional Claude) memory topic file."""
    normalized = file_path.replace("\\", "/")
    base = os.path.basename(normalized)
    if base == "MEMORY.md":
        return False
    if not base.lower().endswith(".md"):
        return False
    if _RUNTIME_MEMORY_RE.search(normalized):
        return True
    return bool(_MEMORY_DIR_RE.search(normalized))


def _is_runtime_memory_path(file_path):
    return bool(_RUNTIME_MEMORY_RE.search((file_path or "").replace("\\", "/")))


def parse_frontmatter(text):
    """Parse only the first --- ... --- fence. Body `type:` does not count.

    Returns (fields_dict, body) or None if the fence is missing.
    """
    if not text:
        return None
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None
    fields = {}
    for line in lines[1:end]:
        m = _FRONTMATTER_KEY.match(line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    body = "\n".join(lines[end + 1:])
    return fields, body


def signal_char_count(text):
    """Unicode alphanumeric count (str.isalnum), not punctuation."""
    n = 0
    for ch in text or "":
        if ch.isalnum():
            n += 1
    return n


def compute_quality(description, body):
    desc = (description or "").strip()
    if len(desc) >= _MIN_DESCRIPTION and signal_char_count(body) >= _MIN_SIGNAL_CHARS:
        return "ok"
    return "thin"


def _parse_memory_field(text, field):
    """Legacy whole-file scan. Prefer parse_frontmatter for the capture door."""
    parsed = parse_frontmatter(text)
    if parsed:
        fields, _body = parsed
        if field in fields:
            return fields[field]
        return None
    pattern = re.compile(r"^\s*{}:\s*(.+?)\s*$".format(re.escape(field)), re.MULTILINE)
    m = pattern.search(text or "")
    if m:
        return m.group(1).strip()
    return None


def _read_memory_snapshots_store():
    """Read the memory snapshots store into a dict, or {} on any error."""
    if not os.path.isfile(MEMORY_SNAPSHOTS_FILE):
        return {}
    try:
        with open(MEMORY_SNAPSHOTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _touch_unflushed():
    try:
        os.makedirs(os.path.dirname(UNFLUSHED_FILE), exist_ok=True)
        with open(UNFLUSHED_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write("")
    except OSError:
        pass


def _capture_memory_snapshot(file_path):
    """Snapshot a team-valuable memory file into the pending snapshots store.

    Frontmatter gate: first fence only; empty name / unknown type rejected.
    Same slug: runtime path wins over Claude inbound.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return

    parsed = parse_frontmatter(text)
    if parsed is None:
        return
    fields, body = parsed
    mem_type = str(fields.get("type") or "").strip().lower()
    if mem_type not in _ALLOWED_TYPES:
        return
    name = str(fields.get("name") or "").strip()
    if not name:
        return

    raw_bytes = text.encode("utf-8")
    truncated = False
    if len(raw_bytes) > _MEMORY_SNAPSHOT_MAX_BYTES:
        text = raw_bytes[:_MEMORY_SNAPSHOT_MAX_BYTES].decode("utf-8", "ignore")
        truncated = True
        parsed2 = parse_frontmatter(text)
        if parsed2:
            fields, body = parsed2

    description = str(fields.get("description") or "").strip()
    quality = compute_quality(description, body)
    skill = str(fields.get("skill") or "").strip()
    anchors = parse_anchors(fields.get("anchors"))
    slug = name
    is_runtime = _is_runtime_memory_path(file_path)

    store = _read_memory_snapshots_store()
    snapshots = store.get("snapshots", {})
    dropped = int(store.get("dropped", 0))

    if slug in snapshots:
        existing_path = str(snapshots[slug].get("path") or "")
        existing_runtime = _is_runtime_memory_path(existing_path)
        if existing_runtime and not is_runtime:
            return
    elif len(snapshots) >= _MEMORY_SNAPSHOTS_MAX:
        dropped += 1
        store = {"snapshots": snapshots, "dropped": dropped}
        os.makedirs(os.path.dirname(MEMORY_SNAPSHOTS_FILE), exist_ok=True)
        try:
            with open(MEMORY_SNAPSHOTS_FILE, "w", encoding="utf-8", newline="\n") as f:
                json.dump(store, f, ensure_ascii=False)
        except OSError:
            pass
        return

    snapshots[slug] = {
        "type": mem_type,
        "name": slug,
        "description": description,
        "content": text,
        "body": body,
        "path": file_path.replace("\\", "/"),
        "truncated": truncated,
        "quality": quality,
        "skill": skill,
        "anchors": anchors,
    }

    store = {"snapshots": snapshots, "dropped": dropped}
    os.makedirs(os.path.dirname(MEMORY_SNAPSHOTS_FILE), exist_ok=True)
    try:
        with open(MEMORY_SNAPSHOTS_FILE, "w", encoding="utf-8", newline="\n") as f:
            json.dump(store, f, ensure_ascii=False)
        _touch_unflushed()
    except OSError:
        pass


def main():
    try:
        if not evolution_enabled():
            return
        _bind_runtime_trace_dir()

        raw = sys.stdin.read()
        if not raw.strip():
            return

        event_data = json.loads(raw)
        file_path = extract_file_path(event_data)
        if not file_path:
            return

        if _is_memory_file(file_path):
            _capture_memory_snapshot(file_path)

    except Exception:
        pass


if __name__ == "__main__":
    main()
