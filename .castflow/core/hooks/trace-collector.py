#!/usr/bin/env python3
"""
CastFlow Trace Collector - Cross-platform hook script.

Triggered on file edit events (Cursor: afterFileEdit, Claude Code: PostToolUse/Write).
Extracts the edited file path, estimates lines changed, tracks edit count per file,
and detects potential revert/correction patterns.

Buffer format v2: path|lines|edits|flags
  - lines: accumulated lines changed
  - edits: number of edit events for this file
  - flags: comma-separated markers (R=revert detected)

Backward compatible: reads v1 (path|lines) and legacy (path only) formats.

Zero external dependencies. Python 3.6+.
"""

import json
import os
import sys

TRACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "traces")
BUFFER_FILE = os.path.join(TRACE_DIR, ".trace_buffer")
PREV_EDITS_FILE = os.path.join(TRACE_DIR, ".trace_prev_edits")

TRACKED_EXTENSIONS = {".cs"}
EXCLUDED_EXTENSIONS = {".meta", ".asset", ".prefab", ".unity", ".mat", ".anim", ".controller"}

REVERT_SIMILARITY_THRESHOLD = 0.6


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


def estimate_lines_changed(event_data):
    """Best-effort extraction of lines changed from event payload.

    Returns 0 if estimation is not possible.
    """
    for root_key in ("input", "tool_input"):
        root = event_data.get(root_key)
        if not isinstance(root, dict):
            continue

        old = root.get("oldString") or root.get("old_string") or root.get("old_str") or ""
        new = root.get("newString") or root.get("new_string") or root.get("new_str") or ""
        if old or new:
            return max(old.count("\n"), new.count("\n"), 1)

        contents = root.get("contents") or root.get("content") or ""
        if contents and isinstance(contents, str):
            return min(contents.count("\n"), 500)

    return 0


def extract_edit_strings(event_data):
    """Extract old and new strings from the edit event for revert detection."""
    for root_key in ("input", "tool_input"):
        root = event_data.get(root_key)
        if not isinstance(root, dict):
            continue

        old = root.get("oldString") or root.get("old_string") or root.get("old_str") or ""
        new = root.get("newString") or root.get("new_string") or root.get("new_str") or ""
        if old or new:
            return old, new

    return "", ""


def detect_revert(path, old_string, new_string):
    """Detect if this edit reverts a previous edit on the same file.

    Checks if the current old_string is similar to the previous new_string,
    which indicates the AI is correcting its own prior output.
    """
    if not old_string or len(old_string) < 10:
        return False

    prev = _load_prev_edit(path)
    if not prev:
        return False

    old_stripped = old_string.strip()
    prev_stripped = prev.strip()

    if not prev_stripped or not old_stripped:
        return False

    if old_stripped == prev_stripped:
        return True

    if len(old_stripped) > 0 and len(prev_stripped) > 0:
        shorter = min(len(old_stripped), len(prev_stripped))
        longer = max(len(old_stripped), len(prev_stripped))
        if shorter > 20:
            prefix_match = 0
            for i in range(min(shorter, 200)):
                if old_stripped[i] == prev_stripped[i]:
                    prefix_match += 1
                else:
                    break
            if prefix_match / float(longer) > REVERT_SIMILARITY_THRESHOLD:
                return True

    return False


def _load_prev_edit(path):
    """Load the previous new_string for a file from the prev-edits store."""
    if not os.path.isfile(PREV_EDITS_FILE):
        return None
    try:
        with open(PREV_EDITS_FILE, "r", encoding="utf-8") as f:
            store = json.load(f)
        return store.get(path)
    except (json.JSONDecodeError, OSError):
        return None


def _save_prev_edit(path, new_string):
    """Save the new_string for revert detection on next edit."""
    store = {}
    if os.path.isfile(PREV_EDITS_FILE):
        try:
            with open(PREV_EDITS_FILE, "r", encoding="utf-8") as f:
                store = json.load(f)
        except (json.JSONDecodeError, OSError):
            store = {}

    trimmed = new_string[:500] if new_string else ""
    store[path] = trimmed

    if len(store) > 50:
        keys = sorted(store.keys())
        store = {k: store[k] for k in keys[-50:]}

    os.makedirs(os.path.dirname(PREV_EDITS_FILE), exist_ok=True)
    try:
        with open(PREV_EDITS_FILE, "w", encoding="utf-8", newline="\n") as f:
            json.dump(store, f, ensure_ascii=False)
    except OSError:
        pass


def should_track(file_path):
    """Check if the file should be tracked based on extension."""
    _, ext = os.path.splitext(file_path.lower())
    if ext in EXCLUDED_EXTENSIONS:
        return False
    if ext in TRACKED_EXTENSIONS:
        return True
    return False


def normalize_path(file_path):
    """Normalize path separators for consistent storage."""
    return file_path.replace("\\", "/")


def read_existing_buffer():
    """Read existing buffer entries into a dict {path: (lines, edits, flags_set)}.

    Supports v2 (path|lines|edits|flags), v1 (path|lines), and legacy (path) formats.
    """
    entries = {}
    if not os.path.isfile(BUFFER_FILE):
        return entries
    with open(BUFFER_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) >= 4:
                path = parts[0]
                try:
                    lines = int(parts[1])
                except ValueError:
                    lines = 0
                try:
                    edits = int(parts[2])
                except ValueError:
                    edits = 0
                flags = set(parts[3].split(",")) if parts[3] else set()
                flags.discard("")
            elif len(parts) == 2:
                path = parts[0]
                try:
                    lines = int(parts[1])
                except ValueError:
                    lines = 0
                edits = 1
                flags = set()
            else:
                path = parts[0]
                lines = 0
                edits = 1
                flags = set()

            if path in entries:
                prev_lines, prev_edits, prev_flags = entries[path]
                entries[path] = (prev_lines + lines, prev_edits + edits, prev_flags | flags)
            else:
                entries[path] = (lines, edits, flags)
    return entries


def write_buffer(entries):
    """Write all buffer entries to file in v2 format."""
    os.makedirs(os.path.dirname(BUFFER_FILE), exist_ok=True)
    with open(BUFFER_FILE, "w", encoding="utf-8", newline="\n") as f:
        for path, (lines, edits, flags) in entries.items():
            flags_str = ",".join(sorted(flags)) if flags else ""
            f.write("{}|{}|{}|{}\n".format(path, lines, edits, flags_str))


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return

        event_data = json.loads(raw)
        file_path = extract_file_path(event_data)
        if not file_path:
            return

        if not should_track(file_path):
            return

        normalized = normalize_path(file_path)
        lines_changed = estimate_lines_changed(event_data)

        old_str, new_str = extract_edit_strings(event_data)
        is_revert = detect_revert(normalized, old_str, new_str)

        if new_str:
            _save_prev_edit(normalized, new_str)

        entries = read_existing_buffer()
        if normalized in entries:
            prev_lines, prev_edits, prev_flags = entries[normalized]
            new_flags = set(prev_flags)
            if is_revert:
                new_flags.add("R")
            entries[normalized] = (prev_lines + lines_changed, prev_edits + 1, new_flags)
        else:
            new_flags = set()
            if is_revert:
                new_flags.add("R")
            entries[normalized] = (lines_changed, 1, new_flags)

        write_buffer(entries)

    except Exception:
        pass


if __name__ == "__main__":
    main()
