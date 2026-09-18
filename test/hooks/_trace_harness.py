#!/usr/bin/env python3
"""Shared test harness for schema:4 memory-snapshot hook tests."""

import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone

_HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
HOOKS_DIR = os.path.normpath(os.path.join(
    _HARNESS_DIR, "..", "..", ".castflow", "core", "hooks"
))

KEEP_DATA = "--keep-data" in sys.argv
if KEEP_DATA:
    sys.argv.remove("--keep-data")


def import_hyphen_module(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(HOOKS_DIR, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


collector = import_hyphen_module("collector", "trace-collector.py")
flush = import_hyphen_module("flush", "trace-flush.py")


def make_trace_block(timestamp, entry_type="feedback", validated="_",
                     status="pending", memory_snapshots=None, schema=4,
                     gate_hint=None, quality=None):
    ts_str = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") if isinstance(
        timestamp, datetime) else timestamp
    snaps = memory_snapshots or []
    mem_blocks = ""
    for snap in snaps:
        q = snap.get("quality", "ok")
        mem_blocks += (
            "<!-- MEMORY slug:{slug} type:{typ} quality:{q} -->\n"
            "skill: {skill}\n"
            "anchors: {anchors}\n"
            "description: {desc}\n"
            "---\n{content}\n"
            "<!-- /MEMORY -->\n"
        ).format(
            slug=snap.get("slug", "s"),
            typ=snap.get("type", "feedback"),
            q=q,
            skill=snap.get("skill", ""),
            anchors=snap.get("anchors", "[]"),
            desc=snap.get("description", ""),
            content=snap.get("content", "rule"),
        )
    extra = ""
    if quality:
        extra += "quality: {}\n".format(quality)
    if gate_hint:
        extra += "gate_hint: {}\n".format(gate_hint)
    return (
        "<!-- TRACE status:{status} schema:{schema} -->\n"
        "timestamp: {ts}\n"
        "type: {typ}\n"
        "validated: {validated}\n"
        "{extra}"
        "memory_snapshots: {n}\n"
        "{mem}"
        "<!-- /TRACE -->\n"
    ).format(
        status=status, schema=schema, ts=ts_str, typ=entry_type,
        validated=validated, extra=extra, n=len(snaps),
        mem=mem_blocks,
    )


def build_trace_file(blocks, header=True):
    parts = []
    if header:
        parts.append("# Execution Traces\n\n---\n\n")
    for b in blocks:
        parts.append(b)
        parts.append("\n")
    return "".join(parts)


FLUSH_PATH_ATTRS = (
    "TRACE_DIR", "TRACE_FILE", "LIMITS_FILE", "PENDING_VALIDATED_FILE",
    "NOTIFY_STATE_FILE", "TRACE_LOCK_FILE",
    "MEMORY_SNAPSHOTS_FILE", "TRACE_ERROR_LOG",
    "UNFLUSHED_FILE", "EVOLVE_NUDGE_FILE",
)

COLLECTOR_PATH_ATTRS = (
    "TRACE_DIR", "MEMORY_SNAPSHOTS_FILE", "UNFLUSHED_FILE",
)


class TraceTestBase(unittest.TestCase):
    TMP_PREFIX = "castflow_"
    OUTPUT_BASE = None

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix=self.TMP_PREFIX)
        self.traces_dir = os.path.join(self.test_dir, "traces")
        os.makedirs(self.traces_dir, exist_ok=True)
        self.config_dir = os.path.join(self.traces_dir, "config")
        os.makedirs(self.config_dir, exist_ok=True)
        self.memory_dir = os.path.join(self.test_dir, ".castflow-runtime", "memory")
        os.makedirs(self.memory_dir, exist_ok=True)

        self._saved_flush = {}
        for attr in FLUSH_PATH_ATTRS:
            if hasattr(flush, attr):
                self._saved_flush[attr] = getattr(flush, attr)

        flush.TRACE_DIR = self.traces_dir
        flush.TRACE_FILE = os.path.join(self.traces_dir, "trace.md")
        flush.LIMITS_FILE = os.path.join(self.config_dir, "limits.json")
        flush.PENDING_VALIDATED_FILE = os.path.join(
            self.traces_dir, ".pending_validated.json")
        flush.NOTIFY_STATE_FILE = os.path.join(
            self.traces_dir, ".notify_state.json")
        flush.TRACE_LOCK_FILE = os.path.join(self.traces_dir, ".trace_lock")
        flush.MEMORY_SNAPSHOTS_FILE = os.path.join(
            self.traces_dir, ".trace_memory_snapshots")
        flush.TRACE_ERROR_LOG = os.path.join(self.traces_dir, ".trace_error.log")
        if hasattr(flush, "UNFLUSHED_FILE"):
            flush.UNFLUSHED_FILE = os.path.join(self.traces_dir, ".unflushed")
        if hasattr(flush, "EVOLVE_NUDGE_FILE"):
            flush.EVOLVE_NUDGE_FILE = os.path.join(
                self.traces_dir, ".evolve_nudge")

        self._saved_coll = {}
        for attr in COLLECTOR_PATH_ATTRS:
            if hasattr(collector, attr):
                self._saved_coll[attr] = getattr(collector, attr)
        collector.TRACE_DIR = self.traces_dir
        collector.MEMORY_SNAPSHOTS_FILE = os.path.join(
            self.traces_dir, ".trace_memory_snapshots")
        if hasattr(collector, "UNFLUSHED_FILE"):
            collector.UNFLUSHED_FILE = os.path.join(
                self.traces_dir, ".unflushed")

    def tearDown(self):
        for attr, val in self._saved_flush.items():
            setattr(flush, attr, val)
        for attr, val in self._saved_coll.items():
            setattr(collector, attr, val)
        if KEEP_DATA and self.OUTPUT_BASE:
            dest = os.path.join(
                self.OUTPUT_BASE,
                "{}__{}".format(type(self).__name__, self._testMethodName),
            )
            shutil.copytree(self.test_dir, dest, ignore_dangling_symlinks=True)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def write_trace(self, content):
        with open(flush.TRACE_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    def read_trace(self):
        if not os.path.isfile(flush.TRACE_FILE):
            return ""
        with open(flush.TRACE_FILE, "r", encoding="utf-8") as f:
            return f.read()

    def write_limits(self, overrides):
        data = dict(flush.DEFAULT_LIMITS)
        data.update(overrides)
        with open(flush.LIMITS_FILE, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f)

    def write_memory_file(self, slug, mem_type, body, extra_dir=None,
                          name=None, description=None, extra_front=None,
                          omit_name=False, raw=None):
        folder = extra_dir or self.memory_dir
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, slug + ".md")
        if raw is not None:
            text = raw
        else:
            lines = ["---"]
            if not omit_name:
                lines.append("name: {}".format(name if name is not None else slug))
            if mem_type is not None:
                lines.append("type: {}".format(mem_type))
            desc = description if description is not None else slug
            lines.append("description: {}".format(desc))
            if extra_front:
                lines.extend(extra_front)
            lines.append("---")
            lines.append("")
            lines.append(body)
            lines.append("")
            text = "\n".join(lines)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return path

    def write_snapshots_store(self, snapshots):
        store = {"snapshots": snapshots, "dropped": 0}
        with open(flush.MEMORY_SNAPSHOTS_FILE, "w", encoding="utf-8", newline="\n") as f:
            json.dump(store, f)
        return store

    def count_blocks(self, content=None):
        if content is None:
            content = self.read_trace()
        return len(re.findall(r"<!-- TRACE ", content))

    def count_pending(self, content=None):
        if content is None:
            content = self.read_trace()
        return flush.count_pending_entries(content)


def make_output_base(subdir):
    base = os.path.join(_HARNESS_DIR, "test-output", subdir)
    if KEEP_DATA:
        if os.path.isdir(base):
            shutil.rmtree(base)
        os.makedirs(base, exist_ok=True)
        print("[keep-data] Output directory: {}".format(base))
    return base
