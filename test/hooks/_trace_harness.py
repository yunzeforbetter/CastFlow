#!/usr/bin/env python3
"""Shared test harness for the CastFlow hook test suite.

Centralizes the pieces that were copy-pasted across test_evolution.py and the
production simulations: hyphen-module import, trace-block construction, and the
temp-dir base class that redirects trace-collector / trace-flush file paths.

Consumers:
    from _trace_harness import (
        collector, flush, make_trace_block, build_trace_file, TraceTestBase,
    )
"""

import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from datetime import datetime

_HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
HOOKS_DIR = os.path.normpath(os.path.join(
    _HARNESS_DIR, "..", "..", ".castflow", "core", "hooks"
))

# --keep-data: preserve each test case's trace files for inspection.
# Parsed once here so every consumer shares one flag.
KEEP_DATA = "--keep-data" in sys.argv
if KEEP_DATA:
    sys.argv.remove("--keep-data")


def import_hyphen_module(name, filename):
    """Import a module whose filename contains hyphens (not importable normally)."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(HOOKS_DIR, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


collector = import_hyphen_module("collector", "trace-collector.py")
flush = import_hyphen_module("flush", "trace-flush.py")


def make_trace_block(timestamp, modules, score, validated="_", correction="_",
                     status="pending", pipeline_run_id="_", edit_count=1,
                     file_count=1, lines_changed=10, mode="_", entry_type="_",
                     request="_", intent="_", skills=None, files=None):
    """Build a single trace block string.

    Accepts either a datetime or a pre-formatted timestamp string.
    """
    ts_str = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") if isinstance(timestamp, datetime) else timestamp
    mods = ", ".join(modules) if isinstance(modules, list) else modules
    skills_str = "[{}]".format(", ".join(skills)) if skills else "[]"
    files_str = ", ".join(files[:20]) if files else "test.cs"
    return (
        "<!-- TRACE status:{status} -->\n"
        "timestamp: {ts}\n"
        "mode: {mode}\n"
        "type: {type}\n"
        "request: {request}\n"
        "intent: {intent}\n"
        "correction: {correction}\n"
        "validated: {validated}\n"
        "pipeline_run_id: {run_id}\n"
        "modules: [{modules}]\n"
        "skills: {skills}\n"
        "files_modified: [{files}]\n"
        "file_count: {fc}\n"
        "lines_changed: {lc}\n"
        "edit_count: {ec}\n"
        "score: {score}\n"
        "<!-- /TRACE -->\n"
    ).format(
        status=status, ts=ts_str, mode=mode, type=entry_type,
        request=request, intent=intent,
        correction=correction, validated=validated, run_id=pipeline_run_id,
        modules=mods, skills=skills_str, files=files_str,
        fc=file_count, lc=lines_changed, ec=edit_count, score=score,
    )


def build_trace_file(blocks, header=True):
    """Build a full trace.md content string from a list of block strings."""
    parts = []
    if header:
        parts.append("# Execution Traces\n\n---\n\n")
    for b in blocks:
        parts.append(b)
        parts.append("\n")
    return "".join(parts)


class TraceTestBase(unittest.TestCase):
    """Base class that redirects all collector/flush file paths to a temp dir.

    Subclasses may set class attributes to control temp-dir naming and
    --keep-data snapshots:
        TMP_PREFIX   -- mkdtemp prefix
        OUTPUT_BASE  -- directory to copy test data into when --keep-data is set
                        (None disables snapshotting even under --keep-data)
    """

    TMP_PREFIX = "castflow_"
    OUTPUT_BASE = None

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix=self.TMP_PREFIX)
        self.traces_dir = os.path.join(self.test_dir, "traces")
        os.makedirs(self.traces_dir, exist_ok=True)
        self.config_dir = os.path.join(self.traces_dir, "config")
        os.makedirs(self.config_dir, exist_ok=True)

        self._saved = {}
        for attr in ["TRACE_DIR", "BUFFER_FILE", "TRACE_FILE", "WEIGHTS_FILE",
                     "LIMITS_FILE", "PENDING_IDP_FILE", "PENDING_VALIDATED_FILE",
                     "PENDING_PIPELINE_FILE", "NOTIFY_STATE_FILE", "TRACE_LOCK_FILE"]:
            self._saved[attr] = getattr(flush, attr)

        flush.TRACE_DIR = self.traces_dir
        flush.BUFFER_FILE = os.path.join(self.traces_dir, ".trace_buffer")
        flush.TRACE_FILE = os.path.join(self.traces_dir, "trace.md")
        flush.WEIGHTS_FILE = os.path.join(self.traces_dir, "weights.json")
        flush.LIMITS_FILE = os.path.join(self.config_dir, "limits.json")
        flush.PENDING_IDP_FILE = os.path.join(self.traces_dir, ".pending_idp.json")
        flush.PENDING_VALIDATED_FILE = os.path.join(self.traces_dir, ".pending_validated.json")
        flush.PENDING_PIPELINE_FILE = os.path.join(self.traces_dir, ".pending_pipeline_result.json")
        flush.NOTIFY_STATE_FILE = os.path.join(self.traces_dir, ".notify_state.json")
        flush.TRACE_LOCK_FILE = os.path.join(self.traces_dir, ".trace_lock")

        self._saved_coll = {
            "BUFFER_FILE": collector.BUFFER_FILE,
            "PREV_EDITS_FILE": collector.PREV_EDITS_FILE,
        }
        collector.BUFFER_FILE = os.path.join(self.traces_dir, ".trace_buffer")
        collector.PREV_EDITS_FILE = os.path.join(self.traces_dir, ".trace_prev_edits")

    def tearDown(self):
        for attr, val in self._saved.items():
            setattr(flush, attr, val)
        for attr, val in self._saved_coll.items():
            setattr(collector, attr, val)

        if KEEP_DATA and self.OUTPUT_BASE:
            dest = os.path.join(self.OUTPUT_BASE,
                                "{}__{}".format(type(self).__name__, self._testMethodName))
            shutil.copytree(self.test_dir, dest, ignore_dangling_symlinks=True)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # ---- file helpers ----

    def write_trace(self, content):
        with open(flush.TRACE_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    def read_trace(self):
        if not os.path.isfile(flush.TRACE_FILE):
            return ""
        with open(flush.TRACE_FILE, "r", encoding="utf-8") as f:
            return f.read()

    def write_buffer(self, lines):
        with open(flush.BUFFER_FILE, "w", encoding="utf-8", newline="\n") as f:
            for line in lines:
                f.write(line + "\n")

    def write_limits(self, overrides):
        data = dict(flush.DEFAULT_LIMITS)
        data.update(overrides)
        with open(flush.LIMITS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)

    # ---- trace-block parsing helpers ----

    def count_blocks(self, content=None):
        if content is None:
            content = self.read_trace()
        return len(re.findall(r"<!-- TRACE ", content))

    def count_pending(self, content=None):
        if content is None:
            content = self.read_trace()
        return len(re.findall(r"<!-- TRACE status:pending\b", content))

    def get_all_blocks(self, content=None):
        if content is None:
            content = self.read_trace()
        return re.findall(r"<!-- TRACE[^>]*-->.*?<!-- /TRACE -->", content, re.DOTALL)

    def get_field(self, block, field):
        m = re.search(r"^" + re.escape(field) + r":\s*(.+)$", block, re.MULTILINE)
        return m.group(1).strip() if m else ""


def make_output_base(subdir):
    """Resolve and reset a test-output directory under this folder, if --keep-data."""
    base = os.path.join(_HARNESS_DIR, "test-output", subdir)
    if KEEP_DATA:
        if os.path.isdir(base):
            shutil.rmtree(base)
        os.makedirs(base, exist_ok=True)
        print("[keep-data] Output directory: {}".format(base))
    return base
