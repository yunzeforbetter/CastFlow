#!/usr/bin/env python3
"""
CastFlow Trace Flush - Cross-platform hook script.

Triggered when the agent stops (Claude Code: Stop).
Responsibilities (in order):
  1. apply_validated_update  - update validated field for most-recent pending entry
  2. apply_pipeline_result   - consume code-pipeline's component-owned result signal
  3. flush_new_trace         - read buffer, score, write new trace entry (with IDP)
  4. apply_trace_expiration  - expire stale pending-pipeline / uncertain trace entries
  5. check_and_compact       - compress trace.md if over threshold (skipped when locked)
  6. check_notify            - passive trigger notification via NOTIFY block in trace.md

Scoring model (v2):
  F (file count)        min(file_count / 3, 1.0)
  D (module spread)     min(module_count / 2, 1.0)
  K (critical path)     tiered: Interface=1.0, Impl=0.6, Base=0.3, other=0.0
  S (change scale)      min(total_lines / 50, 1.0)
  E (edit intensity)    min(total_edits / 5, 1.0)

  score = F*w_F + D*w_D + K*w_K + S*w_S + E*w_E
  Weights and threshold loaded from weights.json (fallback to defaults).

Zero external dependencies. Python 3.6+.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

TRACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "traces")
BUFFER_FILE = os.path.join(TRACE_DIR, ".trace_buffer")
TRACE_FILE = os.path.join(TRACE_DIR, "trace.md")
WEIGHTS_FILE = os.path.join(TRACE_DIR, "weights.json")
LIMITS_FILE = os.path.join(TRACE_DIR, "config", "limits.json")
PENDING_IDP_FILE = os.path.join(TRACE_DIR, ".pending_idp.json")
PENDING_VALIDATED_FILE = os.path.join(TRACE_DIR, ".pending_validated.json")
# code-pipeline own runtime signal; consumed by the shared trace hook.
PENDING_PIPELINE_FILE = os.path.join(TRACE_DIR, ".pending_pipeline_result.json")
NOTIFY_STATE_FILE = os.path.join(TRACE_DIR, ".notify_state.json")
TRACE_LOCK_FILE = os.path.join(TRACE_DIR, ".trace_lock")

TRACE_SCHEMA_VERSION = 1

DEFAULT_WEIGHTS = {
    "F": 1.0,
    "D": 0.5,
    "K": 1.5,
    "S": 0.5,
    "E": 0.8,
}
DEFAULT_THRESHOLD = 1.5

DEFAULT_LIMITS = {
    "compact_max_entries": 80,
    "compact_max_size_kb": 100,
    "level2_age_days": 14,
    "level2_score_threshold": 1.0,
    "level3_age_days": 7,
    "level3_score_threshold": 0.5,
    "keep_top_n_per_module": 3,
    "passive_trigger_threshold": 10,
    "passive_trigger_min_new": 5,
    "pipeline_pending_expire_days": 7,
    "validated_uncertain_expire_days": 14,
    "processed_expire_days": 30,
}

CRITICAL_TIERS = [
    (re.compile(r"^I[A-Z]\w+Manager\.cs$"), 1.0),
    (re.compile(r"^I[A-Z]\w+Service\.cs$"), 1.0),
    (re.compile(r"^I[A-Z]\w+System\.cs$"), 1.0),
    (re.compile(r"Manager\.cs$", re.IGNORECASE), 0.6),
    (re.compile(r"Handler\.cs$", re.IGNORECASE), 0.6),
    (re.compile(r"Controller\.cs$", re.IGNORECASE), 0.6),
    (re.compile(r"System\.cs$", re.IGNORECASE), 0.6),
    (re.compile(r"Service\.cs$", re.IGNORECASE), 0.6),
    (re.compile(r"Factory\.cs$", re.IGNORECASE), 0.6),
    (re.compile(r"Base\.cs$", re.IGNORECASE), 0.3),
]

_HOOKS_CONFIG_PATH = os.path.join(TRACE_DIR, "config", "hooks.config.json")

_DEFAULT_GENERIC_SEGMENTS = frozenset([
    "Scripts", "Assets", "GameLogic", "Logic", "Render",
    "Common", "Core", "UI", "src", "lib", "utils", "helpers",
])
_DEFAULT_MODULE_PATTERN = r"[Mm]odules/([^/]+)"


def _load_module_config():
    """Load module inference config from hooks.config.json, fall back to defaults."""
    segments = _DEFAULT_GENERIC_SEGMENTS
    pattern = _DEFAULT_MODULE_PATTERN
    if os.path.isfile(_HOOKS_CONFIG_PATH):
        try:
            with open(_HOOKS_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data.get("generic_dir_segments"), list):
                segments = frozenset(data["generic_dir_segments"])
            if isinstance(data.get("module_dir_pattern"), str):
                pattern = data["module_dir_pattern"]
        except (json.JSONDecodeError, OSError):
            pass
    return segments, re.compile(pattern)


GENERIC_DIR_SEGMENTS, MODULE_DIR_PATTERN = _load_module_config()


# ============================================================
# Config loading
# ============================================================

def load_weights():
    """Load weights and threshold from weights.json, fallback to defaults."""
    weights = dict(DEFAULT_WEIGHTS)
    threshold = DEFAULT_THRESHOLD

    if not os.path.isfile(WEIGHTS_FILE):
        return weights, threshold

    try:
        with open(WEIGHTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data.get("weights"), dict):
            for key in DEFAULT_WEIGHTS:
                if key in data["weights"]:
                    val = data["weights"][key]
                    if isinstance(val, (int, float)) and 0 <= val <= 10:
                        weights[key] = float(val)

        if isinstance(data.get("threshold"), (int, float)):
            val = data["threshold"]
            if 0.5 <= val <= 5.0:
                threshold = float(val)

    except (json.JSONDecodeError, OSError, KeyError):
        pass

    return weights, threshold


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
# Buffer reading
# ============================================================

def read_buffer():
    """Read buffer entries into (file_paths, total_lines, total_edits, revert_count).

    Supports v2 (path|lines|edits|flags), v1 (path|lines), and legacy (path) formats.
    """
    if not os.path.isfile(BUFFER_FILE):
        return [], 0, 0, 0

    seen = {}
    total_lines = 0
    total_edits = 0
    revert_count = 0

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
                    edits = 1
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

            if path not in seen:
                seen[path] = True
                total_lines += lines
                total_edits += edits
                if "R" in flags:
                    revert_count += 1

    file_paths = list(seen.keys())
    return file_paths, total_lines, total_edits, revert_count


def clear_buffer():
    """Remove the trace buffer file and prev-edits store."""
    for f in (BUFFER_FILE, os.path.join(TRACE_DIR, ".trace_prev_edits")):
        try:
            if os.path.isfile(f):
                os.remove(f)
        except OSError:
            pass


# ============================================================
# Module inference
# ============================================================

def infer_modules(file_paths):
    """Infer module names from file paths."""
    modules = set()

    for p in file_paths:
        normalized = p.replace("\\", "/")
        match = MODULE_DIR_PATTERN.search(normalized)
        if match:
            modules.add(match.group(1))
        else:
            parts = normalized.split("/")
            for segment in reversed(parts[:-1]):
                if segment and segment not in GENERIC_DIR_SEGMENTS:
                    modules.add(segment)
                    break

    return sorted(modules) if modules else ["Unknown"]


# ============================================================
# Critical path (tiered)
# ============================================================

def compute_critical_tier(file_paths):
    """Compute the highest critical tier value across all files.

    Returns a float: 1.0 (interface), 0.6 (implementation), 0.3 (base), 0.0 (none).
    """
    max_tier = 0.0
    for p in file_paths:
        filename = p.replace("\\", "/").split("/")[-1] if "/" in p or "\\" in p else p
        for pattern, tier_value in CRITICAL_TIERS:
            if pattern.search(filename):
                if tier_value > max_tier:
                    max_tier = tier_value
                break
        if max_tier >= 1.0:
            break
    return max_tier


# ============================================================
# Scoring
# ============================================================

def compute_score(file_paths, modules, total_lines, total_edits, weights):
    """Compute multi-dimensional significance score (v2).

    Returns (score, breakdown_dict).
    """
    file_count = len(file_paths)
    module_count = len(modules) if modules and modules != ["Unknown"] else 0

    f_raw = min(file_count / 3.0, 1.0)
    d_raw = min(module_count / 2.0, 1.0)
    k_raw = compute_critical_tier(file_paths)
    s_raw = min(total_lines / 50.0, 1.0)
    e_raw = min(total_edits / 5.0, 1.0)

    score = (
        f_raw * weights["F"]
        + d_raw * weights["D"]
        + k_raw * weights["K"]
        + s_raw * weights["S"]
        + e_raw * weights["E"]
    )

    breakdown = {
        "F": round(f_raw * weights["F"], 2),
        "D": round(d_raw * weights["D"], 2),
        "K": round(k_raw * weights["K"], 2),
        "S": round(s_raw * weights["S"], 2),
        "E": round(e_raw * weights["E"], 2),
    }

    return round(score, 2), breakdown


# ============================================================
# Correction inference
# ============================================================

def infer_correction(revert_count):
    """Infer correction level from revert count."""
    if revert_count >= 3:
        return "auto:major"
    if revert_count >= 1:
        return "auto:minor"
    return "_"


# ============================================================
# Pending file readers
# ============================================================

def read_pending_idp():
    """Read .pending_idp.json and return its data dict or None.

    The file is deleted unconditionally in cleanup_pending_files() (finally block).
    """
    if not os.path.isfile(PENDING_IDP_FILE):
        return None

    try:
        with open(PENDING_IDP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass

    return None


def cleanup_pending_files():
    """Unconditionally delete .pending_idp.json.

    Called in the finally block of main() to prevent stale IDP from
    contaminating the next Stop Hook invocation.
    """
    try:
        if os.path.isfile(PENDING_IDP_FILE):
            os.remove(PENDING_IDP_FILE)
    except OSError:
        pass


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

def format_trace(file_paths, modules, score, total_lines, total_edits,
                 correction, idp=None, pipeline_run_id=None):
    """Format a trace entry with v3 metadata (IDP + validated fields)."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    files_str = ", ".join(file_paths[:20])
    if len(file_paths) > 20:
        files_str += ", ... +{} more".format(len(file_paths) - 20)
    modules_str = ", ".join(modules)

    mode = "_"
    request = "_"
    intent = "_"
    entry_type = "_"
    skills = "[]"

    if idp and isinstance(idp, dict):
        mode = str(idp.get("mode") or "_")
        request = str(idp.get("request") or "_")
        intent = str(idp.get("intent") or "_")
        entry_type = str(idp.get("type") or "_")
        raw_skills = idp.get("skills", [])
        if isinstance(raw_skills, list) and raw_skills:
            skills = "[{}]".format(", ".join(str(s) for s in raw_skills))

    validated = "pending-pipeline" if pipeline_run_id else "_"
    run_id_value = pipeline_run_id if pipeline_run_id else "_"

    return (
        "<!-- TRACE status:pending schema:{} -->\n"
        "timestamp: {}\n"
        "mode: {}\n"
        "type: {}\n"
        "request: {}\n"
        "intent: {}\n"
        "correction: {}\n"
        "validated: {}\n"
        "pipeline_run_id: {}\n"
        "modules: [{}]\n"
        "skills: {}\n"
        "files_modified: [{}]\n"
        "file_count: {}\n"
        "lines_changed: {}\n"
        "edit_count: {}\n"
        "score: {}\n"
        "<!-- /TRACE -->\n"
    ).format(
        TRACE_SCHEMA_VERSION,
        timestamp, mode, entry_type, request, intent,
        correction, validated, run_id_value,
        modules_str, skills, files_str,
        len(file_paths), total_lines, total_edits, score,
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

def flush_new_trace(idp):
    """Read buffer, score, and write a new trace entry if score meets threshold."""
    file_paths, total_lines, total_edits, revert_count = read_buffer()
    if not file_paths:
        clear_buffer()
        return

    weights, threshold = load_weights()
    modules = infer_modules(file_paths)
    score, _ = compute_score(file_paths, modules, total_lines, total_edits, weights)

    if score >= threshold:
        correction = infer_correction(revert_count)
        pipeline_run_id = detect_pipeline_context()
        entry = format_trace(
            file_paths, modules, score, total_lines, total_edits,
            correction, idp=idp, pipeline_run_id=pipeline_run_id,
        )
        append_trace(entry)

    clear_buffer()


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


def _get_block_score(block):
    s = _get_block_field(block, "score")
    try:
        return float(s)
    except ValueError:
        return 0.0


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


def _compact_level2_old_low(blocks, already_removed, limits, now):
    """Level 2: Remove old low-score entries past age threshold."""
    to_remove = set()
    level2_age = int(limits["level2_age_days"])
    level2_score = float(limits["level2_score_threshold"])
    for i, m in enumerate(blocks):
        if i in already_removed:
            continue
        block = m.group(0)
        validated = _get_block_field(block, "validated")
        if validated in ("pending-pipeline", "true", "false"):
            continue
        age = _get_block_age_days(block, now)
        score = _get_block_score(block)
        if age > level2_age and score < level2_score:
            to_remove.add(i)
    return to_remove


def _compact_level3_overflow(blocks, already_removed, limits, now):
    """Level 3: If still over limit, remove oldest low-score entries
    while preserving keep_top_n_per_module coverage."""
    remaining = len(blocks) - len(already_removed)
    max_entries = int(limits["compact_max_entries"])
    if remaining <= max_entries:
        return set()

    level3_age = int(limits["level3_age_days"])
    level3_score = float(limits["level3_score_threshold"])
    keep_top_n = int(limits.get("keep_top_n_per_module", 3))

    candidates = []
    module_keep_count = {}

    for i, m in enumerate(blocks):
        if i in already_removed:
            continue
        block = m.group(0)
        validated = _get_block_field(block, "validated")
        modules_str = _get_block_field(block, "modules")

        for mod in re.findall(r"[A-Za-z_]\w*", modules_str):
            module_keep_count[mod] = module_keep_count.get(mod, 0) + 1

        if validated in ("pending-pipeline", "false"):
            continue
        age = _get_block_age_days(block, now)
        score = _get_block_score(block)
        if age > level3_age and score < level3_score:
            candidates.append((age, score, i))

    candidates.sort(key=lambda x: (-x[0], x[1]))
    overflow = remaining - max_entries
    to_remove = set()

    for _, _, idx in candidates[:overflow]:
        block = blocks[idx].group(0)
        modules_str = _get_block_field(block, "modules")
        mods = re.findall(r"[A-Za-z_]\w*", modules_str)
        if any(module_keep_count.get(mod, 0) <= keep_top_n for mod in mods):
            continue
        to_remove.add(idx)
        for mod in mods:
            if mod in module_keep_count:
                module_keep_count[mod] -= 1

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
    blocks_to_remove |= _compact_level2_old_low(blocks, blocks_to_remove, limits, now)
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
    """Verify the trace-flush pipeline can execute end-to-end.

    Checks: weights loading, buffer parsing, module inference, scoring,
    formatting. Prints results to stdout. Returns True on success.
    """
    print("trace-flush self-test")
    print("=" * 40)
    ok = True

    print("[1] Load weights... ", end="")
    try:
        weights, threshold = load_weights()
        print("OK (threshold={})".format(threshold))
    except Exception as e:
        print("FAIL: {}".format(e))
        ok = False

    print("[2] Parse buffer line... ", end="")
    try:
        parts = "Assets/Scripts/Modules/Building/Test.cs|10|3|".split("|")
        assert len(parts) >= 2
        print("OK")
    except Exception as e:
        print("FAIL: {}".format(e))
        ok = False

    print("[3] Infer module... ", end="")
    try:
        modules = infer_modules(["Assets/Scripts/Modules/Building/Test.cs"])
        print("OK -> {}".format(modules))
    except Exception as e:
        print("FAIL: {}".format(e))
        ok = False

    print("[4] Compute score... ", end="")
    try:
        score, breakdown = compute_score(
            ["test.cs"], ["TestModule"], 10, 3, weights,
        )
        print("OK -> {:.2f}".format(score))
    except Exception as e:
        print("FAIL: {}".format(e))
        ok = False

    print("[5] Format trace... ", end="")
    try:
        entry = format_trace(
            ["test.cs"], ["TestModule"], 5.0, 10, 3, "_",
        )
        assert "<!-- TRACE" in entry
        assert "<!-- /TRACE -->" in entry
        print("OK ({} chars)".format(len(entry)))
    except Exception as e:
        print("FAIL: {}".format(e))
        ok = False

    print("[6] Config loading... ", end="")
    try:
        segs, pat = _load_module_config()
        print("OK ({} segments, pattern={})".format(len(segs), pat.pattern))
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

    idp = None
    try:
        try:
            sys.stdin.read()
        except Exception:
            pass

        apply_validated_update()
        apply_pipeline_result()
        idp = read_pending_idp()
        flush_new_trace(idp)
        apply_trace_expiration()
        check_and_compact()
        check_notify()

    except Exception as exc:
        _log_error(exc)
    finally:
        cleanup_pending_files()


if __name__ == "__main__":
    main()
