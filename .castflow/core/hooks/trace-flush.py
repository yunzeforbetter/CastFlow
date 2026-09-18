#!/usr/bin/env python3
"""
CastFlow Trace Flush - Cross-platform hook script.

Triggered when the agent stops (Claude Code: Stop).
Responsibilities (in order):
  1. apply_validated_update  - update validated field for most-recent pending entry
  2. flush_new_trace         - write a new trace entry IF memory snapshots were captured
  3. apply_trace_expiration  - expire stale uncertain trace entries
  4. check_and_compact       - compress trace.md if over threshold (skipped when locked)
  5. check_notify            - passive trigger notification via NOTIFY block in trace.md

Learning model (schema:4 - memory snapshots only):
  The scoring/buffer subsystem was retired. A trace entry is written ONLY when
  the model wrote auto-memory during the session (captured by trace-collector
  into .trace_memory_snapshots). The memory content is the learning material;
  origin-evolve distills it. Pure code sessions produce no trace entry.

Zero external dependencies. Python 3.6+.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)
from _castflow_paths import evolution_enabled, runtime_dir  # noqa: E402

TRACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "traces")
TRACE_FILE = os.path.join(TRACE_DIR, "trace.md")
LIMITS_FILE = os.path.join(TRACE_DIR, "config", "limits.json")
PENDING_VALIDATED_FILE = os.path.join(TRACE_DIR, ".pending_validated.json")
NOTIFY_STATE_FILE = os.path.join(TRACE_DIR, ".notify_state.json")
TRACE_LOCK_FILE = os.path.join(TRACE_DIR, ".trace_lock")
# Memory snapshots captured by trace-collector; flushed into trace.md here.
MEMORY_SNAPSHOTS_FILE = os.path.join(TRACE_DIR, ".trace_memory_snapshots")
UNFLUSHED_FILE = os.path.join(TRACE_DIR, ".unflushed")
EVOLVE_NUDGE_FILE = os.path.join(TRACE_DIR, ".evolve_nudge")

TRACE_SCHEMA_VERSION = 4

DEFAULT_LIMITS = {
    "compact_max_entries": 80,
    "compact_max_size_kb": 100,
    "level2_age_days": 14,
    "level3_age_days": 7,
    "keep_recent_n": 20,
    "passive_trigger_threshold": 10,
    "passive_trigger_min_new": 5,
    "validated_uncertain_expire_days": 14,
    "processed_expire_days": 30,
    "waiting_expire_days": 21,
}

# Memory snapshot type precedence when an entry carries multiple snapshots:
# feedback (explicit user rule) > project (context) > reference (pointer).
_TYPE_PRECEDENCE = ("feedback", "project", "reference")


def load_limits():
    """Load compaction limits from limits.json, fallback to defaults."""
    limits = dict(DEFAULT_LIMITS)

    if not os.path.isfile(LIMITS_FILE):
        return limits

    try:
        with open(LIMITS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key in DEFAULT_LIMITS:
            if key in data:
                val = data[key]
                if isinstance(val, (int, float)) and val > 0:
                    limits[key] = val
    except (json.JSONDecodeError, OSError):
        pass

    return limits


# ============================================================
# Memory snapshots (the only learning source)
# ============================================================

def read_memory_snapshots():
    """Read pending memory snapshots into a list of snapshot dicts.

    Returns [] when the store is absent or malformed. Ordering is by the
    store's insertion order (dict preserves it), which reflects capture order.
    """
    if not os.path.isfile(MEMORY_SNAPSHOTS_FILE):
        return []
    try:
        with open(MEMORY_SNAPSHOTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        snapshots = data.get("snapshots", {}) if isinstance(data, dict) else {}
        return [snapshots[k] for k in snapshots if isinstance(snapshots[k], dict)]
    except (json.JSONDecodeError, OSError, AttributeError):
        return []


def clear_memory_snapshots():
    """Remove the memory snapshots store after flushing."""
    try:
        if os.path.isfile(MEMORY_SNAPSHOTS_FILE):
            os.remove(MEMORY_SNAPSHOTS_FILE)
    except OSError:
        pass


def _dominant_type(memory_snapshots):
    """Pick the entry type from captured snapshots by precedence.

    feedback (explicit user rule) > project > reference > whatever's present.
    """
    types = {str(s.get("type") or "").strip() for s in memory_snapshots
             if isinstance(s, dict)}
    for t in _TYPE_PRECEDENCE:
        if t in types:
            return t
    for t in types:
        if t and t != "_":
            return t
    return "_"


def _signal_char_count(text):
    n = 0
    for ch in text or "":
        if ch.isalnum():
            n += 1
    return n


def _compute_quality(description, body):
    desc = (description or "").strip()
    if len(desc) >= 8 and _signal_char_count(body) >= 20:
        return "ok"
    return "thin"


def _snapshot_quality(snap):
    q = str((snap or {}).get("quality") or "").strip()
    if q in ("ok", "thin"):
        return q
    body = snap.get("body") if snap else None
    if body is None:
        body = (snap or {}).get("content") or ""
    return _compute_quality((snap or {}).get("description"), body)


def _trace_quality_and_gate(memory_snapshots):
    """TRACE.quality = best feedback quality; gate_hint = any feedback+ok."""
    snaps = [s for s in (memory_snapshots or []) if isinstance(s, dict)]
    has_ok_feedback = False
    has_feedback = False
    any_thin = False
    for snap in snaps:
        quality = _snapshot_quality(snap)
        if quality == "thin":
            any_thin = True
        if str(snap.get("type") or "").strip() == "feedback":
            has_feedback = True
            if quality == "ok":
                has_ok_feedback = True
    gate_hint = "promotable" if has_ok_feedback else "waiting"
    if has_feedback:
        quality = "ok" if has_ok_feedback else "thin"
    elif not snaps:
        quality = "thin"
    else:
        quality = "thin" if any_thin else "ok"
    return quality, gate_hint


def _format_anchors(anchors):
    if not anchors:
        return "[]"
    if isinstance(anchors, str):
        return anchors
    return "[{}]".format(", ".join(str(a) for a in anchors))


# ============================================================
# Validated update (most-recent pending entry)
# ============================================================

def apply_validated_update():
    """Read .pending_validated.json and update the most recent validated:_ trace entry."""
    if not os.path.isfile(PENDING_VALIDATED_FILE):
        return

    validated_value = None
    try:
        with open(PENDING_VALIDATED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = data.get("result", "")
        if result == "accepted":
            validated_value = "true"
        elif result == "rejected":
            validated_value = "false"
    except (json.JSONDecodeError, OSError):
        pass
    finally:
        try:
            os.remove(PENDING_VALIDATED_FILE)
        except OSError:
            pass

    if validated_value is None or not os.path.isfile(TRACE_FILE):
        return

    try:
        with open(TRACE_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        trace_block_pattern = re.compile(
            r"(<!-- TRACE[^>]*-->.*?<!-- /TRACE -->)",
            re.DOTALL
        )
        blocks = list(trace_block_pattern.finditer(content))

        target_match = None
        for m in reversed(blocks):
            block_text = m.group(1)
            if re.search(r"^validated:\s*_\s*$", block_text, re.MULTILINE):
                target_match = m
                break

        if target_match is None:
            return

        old_block = target_match.group(1)
        new_block = re.sub(
            r"^(validated:\s*)_\s*$",
            r"\g<1>" + validated_value,
            old_block,
            count=1,
            flags=re.MULTILINE,
        )

        new_content = (
            content[:target_match.start()]
            + new_block
            + content[target_match.end():]
        )

        tmp_file = TRACE_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_content)
        os.replace(tmp_file, TRACE_FILE)

    except OSError:
        pass


# ============================================================
# Trace lifecycle updates
# ============================================================

def _block_status(block):
    status_match = re.search(r"<!-- TRACE status:(\S+)", block)
    return status_match.group(1) if status_match else "pending"


def _block_gate_hint(block):
    """Infer gate_hint for old blocks: feedback + MEMORY => promotable."""
    explicit = _get_block_field(block, "gate_hint")
    if explicit in ("promotable", "waiting"):
        return explicit
    entry_type = _get_block_field(block, "type")
    if entry_type == "feedback" and "<!-- MEMORY " in block:
        return "promotable"
    return "waiting"


def apply_trace_expiration():
    """Expire waiting pending rows past waiting_expire_days. Not validated:_."""
    if not os.path.isfile(TRACE_FILE):
        return

    limits = load_limits()
    now = datetime.now(timezone.utc)
    waiting_expire = int(limits.get("waiting_expire_days", 21))

    try:
        with open(TRACE_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return

    trace_block_pattern = re.compile(
        r"(<!-- TRACE[^>]*-->.*?<!-- /TRACE -->)",
        re.DOTALL,
    )

    changed = False

    def update_block(m):
        nonlocal changed
        block = m.group(1)
        age = _get_block_age_days(block, now)
        validated = _get_block_field(block, "validated")
        status = _block_status(block)
        new_block = block

        if validated == "pending-pipeline":
            new_block = re.sub(
                r"^(validated:\s*)pending-pipeline\s*$",
                r"\g<1>invalid",
                new_block,
                count=1,
                flags=re.MULTILINE,
            )
            new_block = re.sub(
                r"^(<!-- TRACE status:)(\S+)",
                r"\g<1>invalid",
                new_block,
                count=1,
                flags=re.MULTILINE,
            )
        elif status == "pending" and _block_gate_hint(block) == "waiting" and age > waiting_expire:
            new_block = re.sub(
                r"^(<!-- TRACE status:)(\S+)",
                r"\g<1>expired",
                new_block,
                count=1,
                flags=re.MULTILINE,
            )

        if new_block != block:
            changed = True
        return new_block

    new_content = trace_block_pattern.sub(update_block, content)

    if not changed:
        return

    try:
        tmp_file = TRACE_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_content)
        os.replace(tmp_file, TRACE_FILE)
    except OSError:
        pass


# ============================================================
# Trace formatting and appending
# ============================================================

def _sanitize_snapshot_content(text):
    """Neutralize HTML-comment tokens so snapshot content cannot break the
    outer TRACE/MEMORY block regexes (which match `<!-- ... -->` spans).

    Memory markdown may legitimately contain `<!--`/`-->` (e.g. a doc about
    the trace format itself); we defang the tokens rather than drop content.
    """
    return text.replace("<!--", "<! --").replace("-->", "-- >")


def _format_memory_blocks(memory_snapshots):
    """Render captured memory snapshots as MEMORY subblocks (raw material)."""
    if not memory_snapshots:
        return ""
    blocks = []
    for snap in memory_snapshots:
        if not isinstance(snap, dict):
            continue
        slug = str(snap.get("name") or snap.get("slug") or "_")
        mtype = str(snap.get("type") or "_")
        quality = _snapshot_quality(snap)
        description = str(snap.get("description") or "")
        skill = str(snap.get("skill") or "")
        anchors = _format_anchors(snap.get("anchors"))
        content = _sanitize_snapshot_content(str(snap.get("content") or ""))
        trunc = " truncated:1" if snap.get("truncated") else ""
        blocks.append(
            "<!-- MEMORY slug:{} type:{} quality:{}{} -->\n"
            "skill: {}\n"
            "anchors: {}\n"
            "description: {}\n"
            "---\n"
            "{}\n"
            "<!-- /MEMORY -->\n".format(
                slug, mtype, quality, trunc, skill, anchors,
                description, content.rstrip("\n")
            )
        )
    return "".join(blocks)


def format_trace(entry_type, memory_snapshots):
    """Format a schema:4 trace entry — a memory-snapshot ledger record."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    memory_blocks = _format_memory_blocks(memory_snapshots)
    memory_count = len(memory_snapshots) if memory_snapshots else 0
    quality, gate_hint = _trace_quality_and_gate(memory_snapshots)

    return (
        "<!-- TRACE status:pending schema:{} -->\n"
        "timestamp: {}\n"
        "type: {}\n"
        "validated: _\n"
        "quality: {}\n"
        "gate_hint: {}\n"
        "memory_snapshots: {}\n"
        "{}"
        "<!-- /TRACE -->\n"
    ).format(
        TRACE_SCHEMA_VERSION,
        timestamp, entry_type or "_",
        quality, gate_hint,
        memory_count, memory_blocks,
    )


def append_trace(entry):
    """Append a trace entry to trace.md."""
    os.makedirs(os.path.dirname(TRACE_FILE), exist_ok=True)

    header_needed = not os.path.isfile(TRACE_FILE)
    with open(TRACE_FILE, "a", encoding="utf-8") as f:
        if header_needed:
            f.write("# Execution Traces\n\n")
            f.write("Auto-generated by CastFlow trace hooks. Consumed by origin-evolve.\n\n")
            f.write("---\n\n")
        f.write(entry)
        f.write("\n")


# ============================================================
# New trace flush
# ============================================================

def _clear_unflushed():
    try:
        if os.path.isfile(UNFLUSHED_FILE):
            os.remove(UNFLUSHED_FILE)
    except OSError:
        pass


def flush_new_trace():
    """Write a trace entry IF the model captured memory this session.

    Memory snapshots are the only learning source now — a pure code session
    (no auto-memory written) produces no trace entry.
    """
    memory_snapshots = read_memory_snapshots()
    if not memory_snapshots:
        clear_memory_snapshots()
        _clear_unflushed()
        return

    entry_type = _dominant_type(memory_snapshots)
    entry = format_trace(entry_type, memory_snapshots)
    append_trace(entry)

    clear_memory_snapshots()
    _clear_unflushed()


# ============================================================
# Compaction
# ============================================================

def count_trace_entries(content):
    """Count total TRACE blocks in trace.md content."""
    return len(re.findall(r"<!-- TRACE\b", content))


def count_pending_entries(content):
    """Count pending TRACE blocks eligible for origin-evolve analysis.

    """
    return len(re.findall(r"<!-- TRACE status:pending\b", content))


def check_and_compact():
    """Compact trace.md if over threshold, unless .trace_lock exists."""
    if os.path.isfile(TRACE_LOCK_FILE):
        return

    if not os.path.isfile(TRACE_FILE):
        return

    limits = load_limits()

    try:
        file_size_kb = os.path.getsize(TRACE_FILE) / 1024.0
        with open(TRACE_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        entry_count = count_trace_entries(content)
    except OSError:
        return

    max_entries = int(limits["compact_max_entries"])
    max_size_kb = float(limits["compact_max_size_kb"])

    if entry_count <= max_entries and file_size_kb <= max_size_kb:
        return

    compact_trace(content, limits)


def _get_block_field(block, field):
    m = re.search(r"^" + re.escape(field) + r":\s*(.+)$", block, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _get_block_age_days(block, now):
    ts_str = _get_block_field(block, "timestamp")
    if not ts_str:
        return 0
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return (now - ts).days
    except (ValueError, OverflowError):
        return 0


def _is_experience_asset(block):
    """Promotable pending rows are never age-deleted or cap-deleted."""
    if _block_status(block) != "pending":
        return False
    return _block_gate_hint(block) == "promotable"


def _compact_level0_audit(content, limits, now):
    """Level 0: Remove expired PROCESSED/COMPACTED audit lines."""
    processed_expire = int(limits.get("processed_expire_days", 30))
    audit_pattern = re.compile(
        r"<!-- (?:PROCESSED|COMPACTED) ts:(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)[^>]*-->\n?",
    )

    def remove_expired(m):
        ts_str = m.group(1)
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if (now - ts).days > processed_expire:
                return ""
        except (ValueError, OverflowError):
            pass
        return m.group(0)

    return audit_pattern.sub(remove_expired, content)


def _compact_level1_invalid(blocks):
    """Level 1: Unconditionally remove invalid and expired entries."""
    to_remove = set()
    for i, m in enumerate(blocks):
        block = m.group(0)
        validated = _get_block_field(block, "validated")
        status_match = re.search(r"<!-- TRACE status:(\S+)", block)
        status = status_match.group(1) if status_match else "pending"
        if status in ("expired", "invalid") or validated == "invalid":
            to_remove.add(i)
    return to_remove


def _compact_level2_old_age(blocks, already_removed, limits, now):
    """Level 2: never age-delete status:pending (waiting or promotable)."""
    to_remove = set()
    level2_age = int(limits["level2_age_days"])
    for i, m in enumerate(blocks):
        if i in already_removed:
            continue
        block = m.group(0)
        if _block_status(block) == "pending":
            continue
        if _get_block_age_days(block, now) > level2_age:
            to_remove.add(i)
    return to_remove


def _compact_level3_overflow(blocks, already_removed, limits, now):
    """Level 3: skip all pending. Overflow of pending is waiting-only (below)."""
    remaining = len(blocks) - len(already_removed)
    max_entries = int(limits["compact_max_entries"])
    if remaining <= max_entries:
        return set()

    level3_age = int(limits["level3_age_days"])
    keep_recent_n = int(limits.get("keep_recent_n", 20))
    protected = set(range(max(0, len(blocks) - keep_recent_n), len(blocks)))

    candidates = []
    for i, m in enumerate(blocks):
        if i in already_removed or i in protected:
            continue
        block = m.group(0)
        if _block_status(block) == "pending":
            continue
        age = _get_block_age_days(block, now)
        if age > level3_age:
            candidates.append((age, i))

    candidates.sort(key=lambda x: -x[0])
    overflow = remaining - max_entries
    to_remove = set()
    for _, idx in candidates[:overflow]:
        to_remove.add(idx)
    return to_remove


def _compact_waiting_overflow(blocks, already_removed, limits):
    """If pending count > compact_max_entries, drop oldest waiting only."""
    pending_idx = []
    waiting_idx = []
    for i, m in enumerate(blocks):
        if i in already_removed:
            continue
        block = m.group(0)
        if _block_status(block) != "pending":
            continue
        pending_idx.append(i)
        if _block_gate_hint(block) == "waiting":
            ts = _get_block_field(block, "timestamp")
            waiting_idx.append((ts, i))
    max_entries = int(limits["compact_max_entries"])
    if len(pending_idx) <= max_entries:
        return set()
    overflow = len(pending_idx) - max_entries
    waiting_idx.sort(key=lambda x: x[0])
    to_remove = set()
    for _, idx in waiting_idx[:overflow]:
        to_remove.add(idx)
    return to_remove


def _rebuild_after_compact(content, blocks, blocks_to_remove, now):
    """Rebuild content excluding removed blocks, clean whitespace, add audit."""
    removed = len(blocks_to_remove)
    kept_count = len(blocks) - removed

    parts = []
    prev = 0
    for i, m in enumerate(blocks):
        if i in blocks_to_remove:
            parts.append(content[prev:m.start()])
            prev = m.end()
    parts.append(content[prev:])
    final = "".join(parts)
    final = re.sub(r"\n{3,}", "\n\n", final)

    compact_ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    audit_line = "\n<!-- COMPACTED ts:{} removed:{} kept:{} -->\n".format(
        compact_ts, removed, kept_count,
    )
    return final.rstrip("\n") + "\n" + audit_line


def compact_trace(content, limits):
    """Execute three-level compaction on trace.md content."""
    now = datetime.now(timezone.utc)
    original = content

    trace_block_pattern = re.compile(
        r"<!-- TRACE[^>]*-->.*?<!-- /TRACE -->",
        re.DOTALL,
    )

    content = _compact_level0_audit(content, limits, now)
    blocks = list(trace_block_pattern.finditer(content))

    blocks_to_remove = _compact_level1_invalid(blocks)
    blocks_to_remove |= _compact_waiting_overflow(blocks, blocks_to_remove, limits)
    blocks_to_remove |= _compact_level2_old_age(blocks, blocks_to_remove, limits, now)
    blocks_to_remove |= _compact_level3_overflow(blocks, blocks_to_remove, limits, now)

    if blocks_to_remove:
        final_content = _rebuild_after_compact(content, blocks, blocks_to_remove, now)
    elif content != original:
        final_content = content
    else:
        return

    try:
        tmp_file = TRACE_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(final_content)
        os.replace(tmp_file, TRACE_FILE)
    except OSError:
        pass


# ============================================================
# Passive trigger notification
# ============================================================

def count_notify_entries(content):
    """Pending TRACE rows that are promotable or validated:false."""
    pattern = re.compile(
        r"(<!-- TRACE[^>]*-->.*?<!-- /TRACE -->)",
        re.DOTALL,
    )
    n = 0
    for m in pattern.finditer(content or ""):
        block = m.group(1)
        if _block_status(block) != "pending":
            continue
        if _block_gate_hint(block) == "promotable":
            n += 1
        elif _get_block_field(block, "validated") == "false":
            n += 1
    return n


def _write_evolve_nudge(pending_count):
    try:
        os.makedirs(os.path.dirname(EVOLVE_NUDGE_FILE), exist_ok=True)
        with open(EVOLVE_NUDGE_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write("pending_promotable: {}\n".format(pending_count))
    except OSError:
        pass


def check_notify():
    """Notify on promotable / validated:false pending, not all waiting."""
    if not os.path.isfile(TRACE_FILE):
        return

    limits = load_limits()
    threshold = int(limits["passive_trigger_threshold"])
    min_new = int(limits["passive_trigger_min_new"])

    try:
        with open(TRACE_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        pending_count = count_notify_entries(content)
    except OSError:
        return

    if pending_count < threshold:
        return

    last_notified = 0
    try:
        if os.path.isfile(NOTIFY_STATE_FILE):
            with open(NOTIFY_STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
            last_notified = int(state.get("last_pending_count", 0))
    except (json.JSONDecodeError, OSError, ValueError):
        pass

    new_since_last = pending_count - last_notified
    if new_since_last < min_new:
        return

    notify_block = (
        "\n<!-- NOTIFY type:passive_trigger -->\n"
        "pending_count: {}\n"
        "new_since_last: {}\n"
        "message: CastFlow: {} promotable pending traces. "
        "Run 'origin evolve' to analyze and generate improvement proposals.\n"
        "<!-- /NOTIFY -->\n"
    ).format(pending_count, new_since_last, pending_count)

    try:
        with open(TRACE_FILE, "a", encoding="utf-8") as f:
            f.write(notify_block)
    except OSError:
        return

    _write_evolve_nudge(pending_count)

    try:
        os.makedirs(os.path.dirname(NOTIFY_STATE_FILE), exist_ok=True)
        with open(NOTIFY_STATE_FILE, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"last_pending_count": pending_count}, f)
    except OSError:
        pass


# ============================================================
# Error logging
# ============================================================

TRACE_ERROR_LOG = os.path.join(TRACE_DIR, ".trace_error.log")
_ERROR_LOG_MAX_BYTES = 64 * 1024


def _log_error(exc):
    """Append error to .trace_error.log (capped at 64 KB, rotates on overflow)."""
    import traceback
    try:
        entry = "[{}] {}\n{}\n".format(
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            exc,
            traceback.format_exc(),
        )
        if os.path.isfile(TRACE_ERROR_LOG):
            try:
                size = os.path.getsize(TRACE_ERROR_LOG)
            except OSError:
                size = 0
            if size > _ERROR_LOG_MAX_BYTES:
                rotated = TRACE_ERROR_LOG + ".prev"
                try:
                    if os.path.exists(rotated):
                        os.remove(rotated)
                    os.rename(TRACE_ERROR_LOG, rotated)
                except OSError:
                    pass
        os.makedirs(os.path.dirname(TRACE_ERROR_LOG), exist_ok=True)
        with open(TRACE_ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
    except OSError:
        pass


# ============================================================
# Self-test
# ============================================================

def selftest():
    """Verify the trace-flush pipeline (schema:4, memory-only) end-to-end.

    Checks: limits loading, dominant-type, format_trace schema:4 shape,
    snapshot defang, experience-asset detection, config, error log.
    Prints results to stdout. Returns True on success.
    """
    print("trace-flush self-test")
    print("=" * 40)
    ok = True

    print("[1] Load limits... ", end="")
    try:
        limits = load_limits()
        assert "keep_recent_n" in limits
        assert "waiting_expire_days" in limits
        assert "level2_score_threshold" not in limits, "score keys must be gone"
        print("OK (keep_recent_n={})".format(limits["keep_recent_n"]))
    except Exception as e:
        print("FAIL: {}".format(e))
        ok = False

    print("[2] Dominant type precedence... ", end="")
    try:
        t = _dominant_type([{"type": "project"}, {"type": "feedback"}])
        assert t == "feedback", "feedback must win over project"
        assert _dominant_type([{"type": "reference"}]) == "reference"
        assert _dominant_type([{"type": "_"}]) == "_"
        print("OK")
    except Exception as e:
        print("FAIL: {}".format(e))
        ok = False

    print("[3] Format trace schema:4... ", end="")
    try:
        snaps = [{
            "type": "feedback", "name": "use-x-not-y",
            "description": "prefer X over Y",
            "content": "---\nname: use-x-not-y\n---\n\nAlways use X not Y because Y leaks extra state.",
            "path": ".claude/projects/p/memory/use-x-not-y.md", "truncated": False,
        }]
        entry = format_trace("feedback", snaps)
        assert "schema:4" in entry, "schema must be 4"
        assert "type: feedback" in entry
        assert "memory_snapshots: 1" in entry
        assert "gate_hint:" in entry
        assert "<!-- MEMORY slug:use-x-not-y type:feedback quality:" in entry
        assert "Always use X" in entry
        # retired fields must be gone
        for gone in ("score:", "score_breakdown:", "modules:", "mode:", "lesson:"):
            assert gone not in entry, "retired field {} must be absent".format(gone)
        assert _get_block_field(entry, "validated") == "_"
        print("OK ({} chars)".format(len(entry)))
    except Exception as e:
        print("FAIL: {}".format(e))
        ok = False

    print("[4] Snapshot comment-token defang... ", end="")
    try:
        evil = [{
            "type": "project", "name": "doc", "description": "d",
            "content": "explains <!-- TRACE --> and closing --> markers",
            "path": "x", "truncated": False,
        }]
        entry = format_trace("project", evil)
        assert entry.count("<!-- /TRACE -->") == 1, "content must not inject a TRACE close"
        assert "<! --" in entry, "content <!-- should be defanged"
        print("OK")
    except Exception as e:
        print("FAIL: {}".format(e))
        ok = False

    print("[5] Experience-asset detection... ", end="")
    try:
        asset = format_trace("feedback", [{
            "type": "feedback", "name": "r",
            "description": "use this rule when inserting",
            "content": "abcdefghijklmnopqrstuvwxyz", "path": "p",
            "truncated": False, "quality": "ok"}])
        assert _is_experience_asset(asset), "ok-feedback block is an asset"
        skeleton = (
            "<!-- TRACE status:pending schema:4 -->\n"
            "timestamp: 2020-01-01T00:00:00Z\ntype: _\nvalidated: _\n"
            "gate_hint: waiting\nmemory_snapshots: 0\n<!-- /TRACE -->\n"
        )
        assert not _is_experience_asset(skeleton), "waiting skeleton is not an asset"
        print("OK")
    except Exception as e:
        print("FAIL: {}".format(e))
        ok = False

    print("[6] Config loading... ", end="")
    try:
        lim = load_limits()
        print("OK ({} keys)".format(len(lim)))
    except Exception as e:
        print("FAIL: {}".format(e))
        ok = False

    print("[7] Error log writable... ", end="")
    try:
        os.makedirs(os.path.dirname(TRACE_ERROR_LOG), exist_ok=True)
        print("OK ({})".format(TRACE_ERROR_LOG))
    except Exception as e:
        print("FAIL: {}".format(e))
        ok = False

    print("=" * 40)
    print("Result: {}".format("ALL PASS" if ok else "SOME FAILED"))
    return ok


# ============================================================
# Main
# ============================================================

def run_flush_pipeline():
    """Shipped flush door after paths are bound. Lock => no-op, keep snapshots."""
    if os.path.isfile(TRACE_LOCK_FILE):
        return "locked"
    apply_validated_update()
    flush_new_trace()
    apply_trace_expiration()
    check_and_compact()
    check_notify()
    return "ok"


def _bind_runtime_trace_dir():
    """Point flush I/O at `.castflow-runtime/traces/` when present."""
    global TRACE_DIR, TRACE_FILE, LIMITS_FILE, PENDING_VALIDATED_FILE
    global NOTIFY_STATE_FILE, TRACE_LOCK_FILE, MEMORY_SNAPSHOTS_FILE
    global UNFLUSHED_FILE, EVOLVE_NUDGE_FILE
    rt = runtime_dir()
    traces = os.path.join(rt, "traces")
    if not os.path.isdir(rt):
        return
    TRACE_DIR = traces
    TRACE_FILE = os.path.join(TRACE_DIR, "trace.md")
    LIMITS_FILE = os.path.join(TRACE_DIR, "config", "limits.json")
    PENDING_VALIDATED_FILE = os.path.join(TRACE_DIR, ".pending_validated.json")
    NOTIFY_STATE_FILE = os.path.join(TRACE_DIR, ".notify_state.json")
    TRACE_LOCK_FILE = os.path.join(TRACE_DIR, ".trace_lock")
    MEMORY_SNAPSHOTS_FILE = os.path.join(TRACE_DIR, ".trace_memory_snapshots")
    UNFLUSHED_FILE = os.path.join(TRACE_DIR, ".unflushed")
    EVOLVE_NUDGE_FILE = os.path.join(TRACE_DIR, ".evolve_nudge")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        success = selftest()
        sys.exit(0 if success else 1)

    try:
        if not evolution_enabled():
            return
        _bind_runtime_trace_dir()

        try:
            sys.stdin.read()
        except Exception:
            pass

        run_flush_pipeline()

    except Exception as exc:
        _log_error(exc)


if __name__ == "__main__":
    main()
