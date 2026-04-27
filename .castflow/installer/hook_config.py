"""Hook configuration merging for Cursor and Claude Code."""

import json
import os

TRACE_HOOK_MARKERS = (".claude/hooks/trace-", "run-python.sh trace-")

_RUN = "bash .claude/hooks/run-python.sh"

CURSOR_HOOK_ENTRIES = {
    "afterFileEdit": {"command": "{} trace-collector.py".format(_RUN)},
    "stop": {"command": "{} trace-flush.py".format(_RUN)},
}

CLAUDE_HOOK_ENTRIES = {
    "PostToolUse": {
        "matcher": "Write",
        "hooks": [{"type": "command", "command": "{} trace-collector.py".format(_RUN)}],
    },
    "Stop": {
        "hooks": [{"type": "command", "command": "{} trace-flush.py".format(_RUN)}],
    },
}


def _has_trace_hook(entries):
    """Check if any entry in a hook array already references trace hooks."""
    for entry in entries:
        cmd = entry.get("command", "")
        if any(m in cmd for m in TRACE_HOOK_MARKERS):
            return True
        for sub in entry.get("hooks", []):
            sub_cmd = sub.get("command", "")
            if any(m in sub_cmd for m in TRACE_HOOK_MARKERS):
                return True
    return False


def merge_cursor_hooks(dst_path, dry_run):
    """Merge CastFlow trace hooks into .cursor/hooks.json."""
    data = {"version": 1, "hooks": {}}
    created = True

    if os.path.isfile(dst_path):
        created = False
        try:
            with open(dst_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            print("  [WARN]   {} is corrupt, will recreate".format(dst_path))
            data = {"version": 1, "hooks": {}}
            created = True

    if "hooks" not in data:
        data["hooks"] = {}

    changed = False
    for event_name, entry in CURSOR_HOOK_ENTRIES.items():
        if event_name not in data["hooks"]:
            data["hooks"][event_name] = []
        if not _has_trace_hook(data["hooks"][event_name]):
            data["hooks"][event_name].append(entry)
            changed = True

    if not changed and not created:
        print("  [OK]     {} (trace hooks already present)".format(dst_path))
        return

    if dry_run:
        label = "CREATE" if created else "MERGE"
        print("  [{}]  {}".format(label, dst_path))
        return

    parent = os.path.dirname(dst_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(dst_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    label = "CREATE" if created else "MERGE"
    print("  [{}]  {}".format(label, dst_path))


def merge_claude_settings(dst_path, dry_run):
    """Merge CastFlow trace hooks into .claude/settings.json."""
    data = {"hooks": {}}
    created = True

    if os.path.isfile(dst_path):
        created = False
        try:
            with open(dst_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            print("  [WARN]   {} is corrupt, will recreate".format(dst_path))
            data = {"hooks": {}}
            created = True

    if "hooks" not in data:
        data["hooks"] = {}

    changed = False
    for event_name, entry in CLAUDE_HOOK_ENTRIES.items():
        if event_name not in data["hooks"]:
            data["hooks"][event_name] = []
        if not _has_trace_hook(data["hooks"][event_name]):
            data["hooks"][event_name].append(entry)
            changed = True

    if not changed and not created:
        print("  [OK]     {} (trace hooks already present)".format(dst_path))
        return

    if dry_run:
        label = "CREATE" if created else "MERGE"
        print("  [{}]  {}".format(label, dst_path))
        return

    parent = os.path.dirname(dst_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(dst_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    label = "CREATE" if created else "MERGE"
    print("  [{}]  {}".format(label, dst_path))
