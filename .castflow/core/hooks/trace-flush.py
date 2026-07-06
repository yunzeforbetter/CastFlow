#!/usr/bin/env python3
"""
CastFlow Trace Flush - Cross-platform hook script.

Triggered when the agent stops (Claude Code: Stop).
Responsibilities (in order):
  1. apply_validated_update  - update validated field for most-recent pending entry
  2. apply_pipeline_result   - consume code-pipeline's component-owned result signal
  3. flush_new_trace         - write a new trace entry IF memory snapshots were captured
  4. apply_trace_expiration  - expire stale pending-pipeline / uncertain trace entries
  5. check_and_compact       - compress trace.md if over threshold (skipped when locked)
  6. check_notify            - passive trigger notification via NOTIFY block in trace.md

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

TRACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "traces")
TRACE_FILE = os.path.join(TRACE_DIR, "trace.md")
LIMITS_FILE = os.path.join(TRACE_DIR, "config", "limits.json")
PENDING_VALIDATED_FILE = os.path.join(TRACE_DIR, ".pending_validated.json")
# code-pipeline own runtime signal; consumed by the shared trace hook.
PENDING_PIPELINE_FILE = os.path.join(TRACE_DIR, ".pending_pipeline_result.json")
NOTIFY_STATE_FILE = os.path.join(TRACE_DIR, ".notify_state.json")
TRACE_LOCK_FILE = os.path.join(TRACE_DIR, ".trace_lock")
# Memory snapshots captured by trace-collector; flushed into trace.md here.
MEMORY_SNAPSHOTS_FILE = os.path.join(TRACE_DIR, ".trace_memory_snapshots")

TRACE_SCHEMA_VERSION = 4

DEFAULT_LIMITS = {
    "compact_max_entries": 80,
    "compact_max_size_kb": 100,
    "level2_age_days": 14,
    "level3_age_days": 7,
    "keep_recent_n": 20,
    "passive_trigger_threshold": 10,
    "passive_trigger_min_new": 5,
    "pipeline_pending_expire_days": 7,
    "validated_uncertain_expire_days": 14,
    "processed_expire_days": 30,
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
# Pipeline result batch update
# ============================================================

def _detect_project_root_from_trace_dir():
    """Resolve the project root for an installed `.claude/traces` layout.

    Runtime hooks are copied to `.claude/hooks/` and use `TRACE_DIR = .claude/traces`.
    The project root is therefore the parent directory of `.claude/`.
    If the expected layout is unavailable, fall back to walking upward looking
    for a directory that contains `.claude/`.
    """
    trace_dir = os.path.abspath(TRACE_DIR)
    claude_dir = os.path.dirname(trace_dir)
    if os.path.basename(claude_dir) == ".claude":
        return os.path.dirname(claude_dir)

    candidate = trace_dir
    for _ in range(6):
        if os.path.isdir(os.path.join(candidate, ".claude")):
            return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent

    return None


def detect_pipeline_context():
    """Detect active code-pipeline run_id from PIPELINE_CONTEXT.md.

    Searches for PIPELINE_CONTEXT.md from the installed `.claude/traces`
    runtime layout. Falls back to an upward search for a directory containing
    `.claude/` if the expected layout is unavailable.
    Returns run_id string if file exists and contains pipeline_run_id field,
    otherwise returns None.
    """
    search_dir = _detect_project_root_from_trace_dir()
    if not search_dir:
        return None
    candidate = os.path.join(search_dir, "PIPELINE_CONTEXT.md")

    if not os.path.isfile(candidate):
        return None

    try:
        with open(candidate, "r", encoding="utf-8") as f:
            for line in f:
                m = re.match(r"pipeline_run_id:\s*(\S+)", line.strip())
                if m:
                    return m.group(1)
    except OSError:
        pass

    return None


def apply_pipeline_result():
    """Read code-pipeline's result signal and batch-update matching trace entries."""
    if not os.path.isfile(PENDING_PIPELINE_FILE):
        return

    try:
        with open(PENDING_PIPELINE_FILE, "r", encoding="utf-8") as f:
            content_str = f.read()
    except OSError:
        return

    try:
        target_run_id, target_validated = parse_pipeline_result_signal(content_str)
    except ValueError as exc:
        _log_error(exc)
        return

    if not os.path.isfile(TRACE_FILE):
        return

    try:
        with open(TRACE_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return

    trace_block_pattern = re.compile(
        r"(<!-- TRACE[^>]*-->.*?<!-- /TRACE -->)",
        re.DOTALL
    )
    matched_any = 0
    consumed_any = False

    def replace_pipeline_validated(m):
        nonlocal matched_any, consumed_any
        block = m.group(1)
        if ("pipeline_run_id: " + target_run_id) not in block:
            return block
        matched_any += 1
        if target_validated == "pending-pipeline":
            if re.search(r"^validated:\s*pending-pipeline\s*$", block, re.MULTILINE):
                consumed_any = True
            return block
        if not re.search(r"^validated:\s*pending-pipeline\s*$", block, re.MULTILINE):
            return block
        consumed_any = True
        return re.sub(
            r"^(validated:\s*)pending-pipeline\s*$",
            r"\g<1>" + target_validated,
            block,
            count=1,
            flags=re.MULTILINE,
        )

    new_content = trace_block_pattern.sub(replace_pipeline_validated, content)

    if matched_any == 0 or not consumed_any:
        return

    if new_content != content:
        try:
            tmp_file = TRACE_FILE + ".tmp"
            with open(tmp_file, "w", encoding="utf-8", newline="\n") as f:
                f.write(new_content)
            os.replace(tmp_file, TRACE_FILE)
        except OSError:
            return

    try:
        os.remove(PENDING_PIPELINE_FILE)
    except OSError:
        pass


def _parse_bool_token(value, field_name):
    if isinstance(value, bool):
        return value
    token = str(value).strip().lower()
    if token in ("true", "1", "yes"):
        return True
    if token in ("false", "0", "no"):
        return False
    raise ValueError("Invalid {} value in pipeline result signal: {!r}".format(
        field_name, value))


def parse_pipeline_result_signal(content_str):
    """Parse and validate code-pipeline's result signal."""
    run_id = ""
    result_str = ""
    finalized = None

    try:
        data = json.loads(content_str)
        run_id = data.get("pipeline_run_id", "")
        result_str = data.get("result", "")
        finalized = data.get("finalized")
    except json.JSONDecodeError:
        for line in content_str.splitlines():
            m = re.match(r"pipeline_run_id:\s*(\S+)", line)
            if m:
                run_id = m.group(1)
            m2 = re.match(r"result:\s*(\S+)", line)
            if m2:
                result_str = m2.group(1)
            m3 = re.match(r"finalized:\s*(\S+)", line)
            if m3:
                finalized = m3.group(1)

    if not run_id:
        raise ValueError("Pipeline result signal missing pipeline_run_id")
    if not re.match(r"^pipeline_\d{8}_\d{6}$", run_id):
        raise ValueError("Invalid pipeline_run_id in pipeline result signal: {}".format(run_id))
    if not result_str:
        raise ValueError("Pipeline result signal missing result")

    result_upper = str(result_str).strip().upper()
    if result_upper not in ("GO", "GO-WITH-CAUTION", "NO-GO"):
        raise ValueError("Invalid result in pipeline result signal: {}".format(result_str))
    if finalized is None:
        raise ValueError("Pipeline result signal missing finalized")

    finalized_bool = _parse_bool_token(finalized, "finalized")
    if result_upper in ("GO", "NO-GO") and not finalized_bool:
        raise ValueError("{} requires finalized=true in pipeline result signal".format(
            result_upper))

    if result_upper == "GO-WITH-CAUTION":
        validated_value = "true" if finalized_bool else "pending-pipeline"
    elif result_upper == "GO":
        validated_value = "true"
    else:
        validated_value = "false"

    return run_id, validated_value


# ============================================================
# Trace lifecycle updates
# ============================================================

def apply_trace_expiration():
    """Expire stale pending-pipeline and uncertain pending trace entries."""
    if not os.path.isfile(TRACE_FILE):
        return

    limits = load_limits()
    now = datetime.now(timezone.utc)
    pipeline_pending_expire = int(limits.get("pipeline_pending_expire_days", 7))
    validated_uncertain_expire = int(limits.get("validated_uncertain_expire_days", 14))

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
        status_match = re.search(r"<!-- TRACE status:(\S+)", block)
        status = status_match.group(1) if status_match else "pending"
        new_block = block

        if validated == "pending-pipeline" and age > pipeline_pending_expire:
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
        elif validated == "_" and status == "pending" and age > validated_uncertain_expire:
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
        slug = str(snap.get("name") or "_")
        mtype = str(snap.get("type") or "_")
        description = str(snap.get("description") or "")
        content = _sanitize_snapshot_content(str(snap.get("content") or ""))
        trunc = " truncated:1" if snap.get("truncated") else ""
        blocks.append(
            "<!-- MEMORY slug:{} type:{}{} -->\n"
            "description: {}\n"
            "---\n"
            "{}\n"
            "<!-- /MEMORY -->\n".format(
                slug, mtype, trunc, description, content.rstrip("\n")
            )
        )
    return "".join(blocks)


def format_trace(entry_type, pipeline_run_id, memory_snapshots):
    """Format a schema:4 trace entry — a memory-snapshot ledger record.

    Only lifecycle + snapshot fields remain; the memory content itself is the
    learning material for origin-evolve to distill.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    validated = "pending-pipeline" if pipeline_run_id else "_"
    run_id_value = pipeline_run_id if pipeline_run_id else "_"

    memory_blocks = _format_memory_blocks(memory_snapshots)
    memory_count = len(memory_snapshots) if memory_snapshots else 0

    return (
        "<!-- TRACE status:pending schema:{} -->\n"
        "timestamp: {}\n"
        "type: {}\n"
        "validated: {}\n"
        "pipeline_run_id: {}\n"
        "memory_snapshots: {}\n"
        "{}"
        "<!-- /TRACE -->\n"
    ).format(
        TRACE_SCHEMA_VERSION,
        timestamp, entry_type or "_",
        validated, run_id_value,
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

def flush_new_trace():
    """Write a trace entry IF the model captured memory this session.

    Memory snapshots are the only learning source now — a pure code session
    (no auto-memory written) produces no trace entry.
    """
    memory_snapshots = read_memory_snapshots()
    if not memory_snapshots:
        clear_memory_snapshots()
        return

    entry_type = _dominant_type(memory_snapshots)
    pipeline_run_id = detect_pipeline_context()
    entry = format_trace(entry_type, pipeline_run_id, memory_snapshots)
    append_trace(entry)

    clear_memory_snapshots()


# ============================================================
# Compaction
# ============================================================

def count_trace_entries(content):
    """Count total TRACE blocks in trace.md content."""
    return len(re.findall(r"<!-- TRACE\b", content))


def count_pending_entries(content):
    """Count pending TRACE blocks eligible for origin-evolve analysis.

    Entries still waiting for pipeline finalization (`validated:pending-pipeline`)
    remain pending in lifecycle terms, but they should not trigger passive
    origin-evolve notifications until the pipeline reaches a final verdict or
    expires to invalid.
    """
    trace_block_pattern = re.compile(
        r"<!-- TRACE status:pending\b[^>]*-->.*?<!-- /TRACE -->",
        re.DOTALL,
    )
    count = 0
    for m in trace_block_pattern.finditer(content):
        block = m.group(0)
        if _get_block_field(block, "validated") == "pending-pipeline":
            continue
        count += 1
    return count


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
    """True if the block carries durable learning value and must not be
    auto-removed by age-based compaction: a validated:true entry, or one
    carrying at least one embedded memory snapshot.
    """
    if _get_block_field(block, "validated") == "true":
        return True
    count_str = _get_block_field(block, "memory_snapshots")
    try:
        if int(count_str) > 0:
            return True
    except (TypeError, ValueError):
        pass
    return "<!-- MEMORY " in block


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
        if validated == "pending-pipeline":
            continue
        status_match = re.search(r"<!-- TRACE status:(\S+)", block)
        status = status_match.group(1) if status_match else "pending"
        if status in ("expired", "invalid") or validated == "invalid":
            to_remove.add(i)
    return to_remove


def _compact_level2_old_age(blocks, already_removed, limits, now):
    """Level 2: Remove old non-asset skeleton entries past the age threshold.

    Experience assets (validated:true or carrying memory snapshots) and
    in-flight pipeline entries are never age-removed.
    """
    to_remove = set()
    level2_age = int(limits["level2_age_days"])
    for i, m in enumerate(blocks):
        if i in already_removed:
            continue
        block = m.group(0)
        validated = _get_block_field(block, "validated")
        if validated in ("pending-pipeline", "false"):
            continue
        if _is_experience_asset(block):
            continue
        if _get_block_age_days(block, now) > level2_age:
            to_remove.add(i)
    return to_remove


def _compact_level3_overflow(blocks, already_removed, limits, now):
    """Level 3: If still over the entry cap, drop the oldest non-asset entries,
    always keeping the most recent keep_recent_n entries as a floor."""
    remaining = len(blocks) - len(already_removed)
    max_entries = int(limits["compact_max_entries"])
    if remaining <= max_entries:
        return set()

    level3_age = int(limits["level3_age_days"])
    keep_recent_n = int(limits.get("keep_recent_n", 20))

    # Protect the newest keep_recent_n block indices from overflow removal.
    protected = set(range(max(0, len(blocks) - keep_recent_n), len(blocks)))

    candidates = []
    for i, m in enumerate(blocks):
        if i in already_removed or i in protected:
            continue
        block = m.group(0)
        validated = _get_block_field(block, "validated")
        if validated in ("pending-pipeline", "false"):
            continue
        if _is_experience_asset(block):
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

    trace_block_pattern = re.compile(
        r"<!-- TRACE[^>]*-->.*?<!-- /TRACE -->",
        re.DOTALL,
    )

    content = _compact_level0_audit(content, limits, now)
    blocks = list(trace_block_pattern.finditer(content))

    blocks_to_remove = _compact_level1_invalid(blocks)
    blocks_to_remove |= _compact_level2_old_age(blocks, blocks_to_remove, limits, now)
    blocks_to_remove |= _compact_level3_overflow(blocks, blocks_to_remove, limits, now)

    if not blocks_to_remove:
        return

    final_content = _rebuild_after_compact(content, blocks, blocks_to_remove, now)

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

def check_notify():
    """Check if analyzable pending count crosses threshold and notify."""
    if not os.path.isfile(TRACE_FILE):
        return

    limits = load_limits()
    threshold = int(limits["passive_trigger_threshold"])
    min_new = int(limits["passive_trigger_min_new"])

    try:
        with open(TRACE_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        pending_count = count_pending_entries(content)
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

    # Write NOTIFY block to trace.md so AI sees it on next read
    notify_block = (
        "\n<!-- NOTIFY type:passive_trigger -->\n"
        "pending_count: {}\n"
        "new_since_last: {}\n"
        "message: CastFlow: {} pending trace entries accumulated. "
        "Run 'origin evolve' to analyze and generate improvement proposals.\n"
        "<!-- /NOTIFY -->\n"
    ).format(pending_count, new_since_last, pending_count)

    try:
        with open(TRACE_FILE, "a", encoding="utf-8") as f:
            f.write(notify_block)
    except OSError:
        return

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
            "content": "---\nname: use-x-not-y\n---\n\nAlways use X. Reason: Y leaks.",
            "path": ".claude/projects/p/memory/use-x-not-y.md", "truncated": False,
        }]
        entry = format_trace("feedback", None, snaps)
        assert "schema:4" in entry, "schema must be 4"
        assert "type: feedback" in entry
        assert "memory_snapshots: 1" in entry
        assert "<!-- MEMORY slug:use-x-not-y type:feedback -->" in entry
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
        entry = format_trace("project", None, evil)
        assert entry.count("<!-- /TRACE -->") == 1, "content must not inject a TRACE close"
        assert "<! --" in entry, "content <!-- should be defanged"
        print("OK")
    except Exception as e:
        print("FAIL: {}".format(e))
        ok = False

    print("[5] Experience-asset detection... ", end="")
    try:
        asset = format_trace("feedback", None, [{
            "type": "feedback", "name": "r", "description": "",
            "content": "x", "path": "p", "truncated": False}])
        assert _is_experience_asset(asset), "memory-carrying block is an asset"
        skeleton = (
            "<!-- TRACE status:pending schema:4 -->\n"
            "timestamp: 2020-01-01T00:00:00Z\ntype: _\nvalidated: _\n"
            "pipeline_run_id: _\nmemory_snapshots: 0\n<!-- /TRACE -->\n"
        )
        assert not _is_experience_asset(skeleton), "empty skeleton is not an asset"
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

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        success = selftest()
        sys.exit(0 if success else 1)

    try:
        try:
            sys.stdin.read()
        except Exception:
            pass

        apply_validated_update()
        apply_pipeline_result()
        flush_new_trace()
        apply_trace_expiration()
        check_and_compact()
        check_notify()

    except Exception as exc:
        _log_error(exc)


if __name__ == "__main__":
    main()
