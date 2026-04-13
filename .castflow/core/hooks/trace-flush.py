#!/usr/bin/env python3
"""
CastFlow Trace Flush - Cross-platform hook script.

Triggered when the agent stops (Cursor: stop, Claude Code: Stop).
Reads the trace buffer, computes a multi-dimensional significance score,
and appends a trace entry to trace.md if the score meets the threshold.

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

DEFAULT_WEIGHTS = {
    "F": 1.0,
    "D": 0.5,
    "K": 1.5,
    "S": 0.5,
    "E": 0.8,
}
DEFAULT_THRESHOLD = 1.5

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

GENERIC_DIR_SEGMENTS = frozenset([
    "Scripts", "Assets", "GameLogic", "Logic", "Render",
    "Common", "Core", "UI", "src", "lib", "utils", "helpers",
])

MODULE_DIR_PATTERN = re.compile(r"[Mm]odules/([^/]+)")


# ============================================================
# Weights loading
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
    """Infer correction level from revert count.

    Returns a string for the correction field in the trace entry.
    """
    if revert_count >= 3:
        return "auto:major"
    if revert_count >= 1:
        return "auto:minor"
    return "_"


# ============================================================
# Trace formatting
# ============================================================

def format_trace(file_paths, modules, score, total_lines, total_edits,
                 correction):
    """Format a trace entry with v2 metadata."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    files_str = ", ".join(file_paths[:20])
    if len(file_paths) > 20:
        files_str += ", ... +{} more".format(len(file_paths) - 20)
    modules_str = ", ".join(modules)

    return (
        "<!-- TRACE status:pending -->\n"
        "timestamp: {}\n"
        "type: _\n"
        "correction: {}\n"
        "modules: [{}]\n"
        "skills: []\n"
        "files_modified: [{}]\n"
        "file_count: {}\n"
        "lines_changed: {}\n"
        "edit_count: {}\n"
        "score: {}\n"
        "<!-- /TRACE -->\n"
    ).format(timestamp, correction, modules_str, files_str,
             len(file_paths), total_lines, total_edits, score)


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
# Main
# ============================================================

def main():
    try:
        try:
            sys.stdin.read()
        except Exception:
            pass

        file_paths, total_lines, total_edits, revert_count = read_buffer()
        if not file_paths:
            clear_buffer()
            return

        weights, threshold = load_weights()
        modules = infer_modules(file_paths)
        score, _ = compute_score(file_paths, modules, total_lines,
                                 total_edits, weights)

        if score >= threshold:
            correction = infer_correction(revert_count)
            entry = format_trace(file_paths, modules, score, total_lines,
                                 total_edits, correction)
            append_trace(entry)

        clear_buffer()

    except Exception:
        clear_buffer()


if __name__ == "__main__":
    main()
