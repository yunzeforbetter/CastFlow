#!/usr/bin/env python3
"""
CastFlow Trace Collector - memory snapshot capture hook.

Triggered on file edit events (Claude Code: PostToolUse/Write|Edit|MultiEdit).
The ONLY thing this collects is Claude Code auto-memory writes: when the model
writes a topic file under ~/.claude/projects/<slug>/memory/, we snapshot the
team-valuable ones (type feedback/project/reference; user profiles excluded)
into .trace_memory_snapshots for trace-flush to embed into git-tracked trace.md.

Code edits are NOT tracked — the scoring/buffer subsystem was retired in favor
of memory-driven learning accumulation.

Zero external dependencies. Python 3.6+.
"""

import json
import os
import re
import sys

TRACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "traces")
MEMORY_SNAPSHOTS_FILE = os.path.join(TRACE_DIR, ".trace_memory_snapshots")

_HOOKS_CONFIG_PATH = os.path.join(TRACE_DIR, "config", "hooks.config.json")

# Claude Code auto-memory lives under ~/.claude/projects/<slug>/memory/.
# The model writes distilled learnings there via ordinary Write/Edit tools,
# so PostToolUse observes them like any other file write. We snapshot the
# team-valuable ones into trace.md (git-tracked) as raw material for
# origin-evolve to distill later. Overridable via hooks.config.json.
_DEFAULT_MEMORY_DIR_PATTERN = r"\.claude/projects/[^/]+/memory/"
_MEMORY_SNAPSHOT_MAX_BYTES = 8 * 1024
_MEMORY_SNAPSHOTS_MAX = 5
# Personal profile memories (type: user) must never enter the shared git repo.
_MEMORY_EXCLUDED_TYPES = {"user"}


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


def _is_memory_file(file_path):
    """True if this write targets a Claude Code auto-memory topic file.

    Matches the memory dir pattern, requires a .md extension, and excludes
    the MEMORY.md index (index rows carry no experience value).
    """
    normalized = file_path.replace("\\", "/")
    if not _MEMORY_DIR_RE.search(normalized):
        return False
    base = os.path.basename(normalized)
    if base == "MEMORY.md":
        return False
    return base.lower().endswith(".md")


def _parse_memory_field(text, field):
    """Line-level extraction of a frontmatter scalar field (no YAML dependency).

    Handles both top-level (`name: x`) and nested-under-metadata
    (`  type: x`) placement. Returns None if absent.
    """
    pattern = re.compile(r"^\s*{}:\s*(.+?)\s*$".format(re.escape(field)), re.MULTILINE)
    m = pattern.search(text)
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


def _capture_memory_snapshot(file_path):
    """Snapshot a team-valuable memory file into the pending snapshots store.

    Reads the file from disk (PostToolUse fires after the write, so disk is
    current), filters out personal `user`-type memories, dedups by slug
    (last-write-wins), and caps size/count to avoid unbounded growth.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return

    mem_type = _parse_memory_field(text, "type")
    if mem_type in _MEMORY_EXCLUDED_TYPES:
        return  # personal profile — must not enter shared git

    raw_bytes = text.encode("utf-8")
    truncated = False
    if len(raw_bytes) > _MEMORY_SNAPSHOT_MAX_BYTES:
        text = raw_bytes[:_MEMORY_SNAPSHOT_MAX_BYTES].decode("utf-8", "ignore")
        truncated = True

    name = _parse_memory_field(text, "name")
    slug = name or os.path.splitext(os.path.basename(file_path))[0]
    description = _parse_memory_field(text, "description") or ""

    store = _read_memory_snapshots_store()
    snapshots = store.get("snapshots", {})
    dropped = int(store.get("dropped", 0))

    # last-write-wins on slug; only enforce the count cap for genuinely new slugs
    if slug not in snapshots and len(snapshots) >= _MEMORY_SNAPSHOTS_MAX:
        dropped += 1
    else:
        snapshots[slug] = {
            "type": mem_type or "_",
            "name": slug,
            "description": description,
            "content": text,
            "path": file_path.replace("\\", "/"),
            "truncated": truncated,
        }

    store = {"snapshots": snapshots, "dropped": dropped}
    os.makedirs(os.path.dirname(MEMORY_SNAPSHOTS_FILE), exist_ok=True)
    try:
        with open(MEMORY_SNAPSHOTS_FILE, "w", encoding="utf-8", newline="\n") as f:
            json.dump(store, f, ensure_ascii=False)
    except OSError:
        pass


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return

        event_data = json.loads(raw)
        file_path = extract_file_path(event_data)
        if not file_path:
            return

        # The only thing we capture is auto-memory writes. Everything else
        # (code edits, config, etc.) is ignored — no buffer, no scoring.
        if _is_memory_file(file_path):
            _capture_memory_snapshot(file_path)

    except Exception:
        pass


if __name__ == "__main__":
    main()
