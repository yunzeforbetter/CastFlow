#!/usr/bin/env python3
"""
CastFlow Self-Evolution System - Comprehensive Test Suite.

Tests the full pipeline: collector -> buffer -> flush -> scoring -> compaction -> notify.
Covers all P0-P2 fixes and edge cases.

Run:
    py test_evolution.py               # run and discard test data
    py test_evolution.py --keep-data   # preserve output in test-output/evolution/
"""

import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta

# --keep-data: preserve each test case's trace files for inspection
KEEP_DATA = "--keep-data" in sys.argv
if KEEP_DATA:
    sys.argv.remove("--keep-data")

_script_dir_top = os.path.dirname(os.path.abspath(__file__))
_HOOKS_DIR = os.path.normpath(os.path.join(
    _script_dir_top, "..", "..", ".castflow", "core", "hooks"
))
_OUTPUT_BASE = os.path.join(_script_dir_top, "test-output", "evolution")

if KEEP_DATA:
    if os.path.isdir(_OUTPUT_BASE):
        shutil.rmtree(_OUTPUT_BASE)
    os.makedirs(_OUTPUT_BASE, exist_ok=True)
    print("[keep-data] Output directory: {}".format(_OUTPUT_BASE))

# Import modules with hyphens in filenames via importlib
import importlib.util

def _import_hyphen_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HOOKS_DIR, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

collector = _import_hyphen_module("collector", "trace-collector.py")
flush = _import_hyphen_module("flush", "trace-flush.py")


def make_trace_block(timestamp, modules, score, validated="_", correction="_",
                     status="pending", pipeline_run_id="_", edit_count=1,
                     file_count=1, lines_changed=10):
    """Helper to generate a trace block string."""
    ts_str = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") if isinstance(timestamp, datetime) else timestamp
    mods = ", ".join(modules) if isinstance(modules, list) else modules
    return (
        "<!-- TRACE status:{status} -->\n"
        "timestamp: {ts}\n"
        "mode: _\n"
        "type: _\n"
        "request: _\n"
        "intent: _\n"
        "correction: {correction}\n"
        "validated: {validated}\n"
        "pipeline_run_id: {run_id}\n"
        "modules: [{modules}]\n"
        "skills: []\n"
        "files_modified: [test.cs]\n"
        "file_count: {fc}\n"
        "lines_changed: {lc}\n"
        "edit_count: {ec}\n"
        "score: {score}\n"
        "<!-- /TRACE -->\n"
    ).format(
        status=status, ts=ts_str, correction=correction,
        validated=validated, run_id=pipeline_run_id,
        modules=mods, fc=file_count, lc=lines_changed,
        ec=edit_count, score=score,
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


class TestSetup(unittest.TestCase):
    """Base class that redirects all file paths to a temp directory."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="castflow_")
        self.traces_dir = os.path.join(self.test_dir, "traces")
        os.makedirs(self.traces_dir, exist_ok=True)

        self._orig_trace_dir = flush.TRACE_DIR
        self._orig_buffer = flush.BUFFER_FILE
        self._orig_trace = flush.TRACE_FILE
        self._orig_weights = flush.WEIGHTS_FILE
        self._orig_limits = flush.LIMITS_FILE
        self._orig_idp = flush.PENDING_IDP_FILE
        self._orig_validated = flush.PENDING_VALIDATED_FILE
        self._orig_pipeline = flush.PENDING_PIPELINE_FILE
        self._orig_notify = flush.NOTIFY_STATE_FILE
        self._orig_lock = flush.TRACE_LOCK_FILE

        flush.TRACE_DIR = self.traces_dir
        flush.BUFFER_FILE = os.path.join(self.traces_dir, ".trace_buffer")
        flush.TRACE_FILE = os.path.join(self.traces_dir, "trace.md")
        flush.WEIGHTS_FILE = os.path.join(self.traces_dir, "weights.json")
        flush.LIMITS_FILE = os.path.join(self.traces_dir, "limits.json")
        flush.PENDING_IDP_FILE = os.path.join(self.traces_dir, ".pending_idp.json")
        flush.PENDING_VALIDATED_FILE = os.path.join(self.traces_dir, ".pending_validated.json")
        flush.PENDING_PIPELINE_FILE = os.path.join(self.traces_dir, ".pending_pipeline_result.json")
        flush.NOTIFY_STATE_FILE = os.path.join(self.traces_dir, ".notify_state.json")
        flush.TRACE_LOCK_FILE = os.path.join(self.traces_dir, ".trace_lock")

        self._orig_coll_buffer = collector.BUFFER_FILE
        self._orig_coll_prev = collector.PREV_EDITS_FILE
        collector.BUFFER_FILE = os.path.join(self.traces_dir, ".trace_buffer")
        collector.PREV_EDITS_FILE = os.path.join(self.traces_dir, ".trace_prev_edits")

    def tearDown(self):
        flush.TRACE_DIR = self._orig_trace_dir
        flush.BUFFER_FILE = self._orig_buffer
        flush.TRACE_FILE = self._orig_trace
        flush.WEIGHTS_FILE = self._orig_weights
        flush.LIMITS_FILE = self._orig_limits
        flush.PENDING_IDP_FILE = self._orig_idp
        flush.PENDING_VALIDATED_FILE = self._orig_validated
        flush.PENDING_PIPELINE_FILE = self._orig_pipeline
        flush.NOTIFY_STATE_FILE = self._orig_notify
        flush.TRACE_LOCK_FILE = self._orig_lock

        collector.BUFFER_FILE = self._orig_coll_buffer
        collector.PREV_EDITS_FILE = self._orig_coll_prev

        if KEEP_DATA:
            dest = os.path.join(_OUTPUT_BASE,
                                "{}__{}" .format(type(self).__name__, self._testMethodName))
            shutil.copytree(self.test_dir, dest, ignore_dangling_symlinks=True)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def write_trace(self, content):
        with open(flush.TRACE_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    def read_trace(self):
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


# ============================================================
# 1. Collector Tests
# ============================================================

class TestCollectorExtensions(unittest.TestCase):
    """Verify TRACKED_EXTENSIONS covers all major languages."""

    def test_csharp_tracked(self):
        self.assertTrue(collector.should_track("Assets/Scripts/Foo.cs"))

    def test_typescript_tracked(self):
        self.assertTrue(collector.should_track("src/app.ts"))
        self.assertTrue(collector.should_track("src/app.tsx"))

    def test_python_tracked(self):
        self.assertTrue(collector.should_track("main.py"))

    def test_go_tracked(self):
        self.assertTrue(collector.should_track("cmd/server.go"))

    def test_java_tracked(self):
        self.assertTrue(collector.should_track("com/app/Main.java"))

    def test_rust_tracked(self):
        self.assertTrue(collector.should_track("src/lib.rs"))

    def test_cpp_tracked(self):
        self.assertTrue(collector.should_track("engine/render.cpp"))
        self.assertTrue(collector.should_track("engine/render.h"))
        self.assertTrue(collector.should_track("engine/render.hpp"))

    def test_swift_tracked(self):
        self.assertTrue(collector.should_track("App/ViewController.swift"))

    def test_kotlin_tracked(self):
        self.assertTrue(collector.should_track("app/MainActivity.kt"))

    def test_lua_tracked(self):
        self.assertTrue(collector.should_track("scripts/init.lua"))

    def test_dart_tracked(self):
        self.assertTrue(collector.should_track("lib/main.dart"))

    def test_meta_excluded(self):
        self.assertFalse(collector.should_track("Foo.cs.meta"))

    def test_asset_excluded(self):
        self.assertFalse(collector.should_track("scene.asset"))

    def test_prefab_excluded(self):
        self.assertFalse(collector.should_track("obj.prefab"))

    def test_unknown_not_tracked(self):
        self.assertFalse(collector.should_track("readme.md"))
        self.assertFalse(collector.should_track("data.json"))
        self.assertFalse(collector.should_track("image.png"))


class TestCollectorRevertDetection(TestSetup):
    """Test the revert/correction detection logic."""

    def test_exact_revert_detected(self):
        collector._save_prev_edit("test.cs", "public void Foo() { return 1; }")
        result = collector.detect_revert("test.cs", "public void Foo() { return 1; }", "something new")
        self.assertTrue(result)

    def test_similar_revert_detected(self):
        original = "public void Foo() { int x = 0; int y = 1; return x + y; }"
        collector._save_prev_edit("test.cs", original)
        slightly_different = "public void Foo() { int x = 0; int y = 1; return x + y + 1; }"
        result = collector.detect_revert("test.cs", slightly_different, "new code")
        self.assertTrue(result)

    def test_different_code_not_revert(self):
        collector._save_prev_edit("test.cs", "completely different code here with lots of text")
        result = collector.detect_revert("test.cs", "another totally unrelated block of source code here", "new")
        self.assertFalse(result)

    def test_short_string_not_revert(self):
        collector._save_prev_edit("test.cs", "short")
        result = collector.detect_revert("test.cs", "short", "new")
        self.assertFalse(result)

    def test_no_previous_edit(self):
        result = collector.detect_revert("nonexistent.cs", "some old code that is long enough", "new")
        self.assertFalse(result)


class TestCollectorBufferFormats(TestSetup):
    """Test buffer read/write with v1, v2, and legacy formats."""

    def test_v2_format_roundtrip(self):
        entries = {"a.cs": (10, 3, {"R"}), "b.cs": (5, 1, set())}
        collector.write_buffer(entries)
        read_back = collector.read_existing_buffer()
        self.assertEqual(read_back["a.cs"], (10, 3, {"R"}))
        self.assertEqual(read_back["b.cs"], (5, 1, set()))

    def test_v1_backward_compat(self):
        self.write_buffer(["a.cs|15"])
        read_back = collector.read_existing_buffer()
        self.assertEqual(read_back["a.cs"], (15, 1, set()))

    def test_legacy_backward_compat(self):
        self.write_buffer(["a.cs"])
        read_back = collector.read_existing_buffer()
        self.assertEqual(read_back["a.cs"], (0, 1, set()))

    def test_accumulation_same_file(self):
        self.write_buffer(["a.cs|10|2|", "a.cs|5|1|R"])
        read_back = collector.read_existing_buffer()
        self.assertEqual(read_back["a.cs"], (15, 3, {"R"}))


# ============================================================
# 2. Scoring Tests
# ============================================================

class TestScoring(unittest.TestCase):
    """Test the five-dimensional scoring model."""

    def test_typo_fix_rejected(self):
        """Single config file, 1 line, 1 edit -> should be below threshold."""
        paths = ["Assets/Scripts/data.cs"]
        modules = ["Unknown"]
        score, _ = flush.compute_score(paths, modules, 1, 1, flush.DEFAULT_WEIGHTS)
        self.assertLess(score, flush.DEFAULT_THRESHOLD)

    def test_manager_edit_accepted(self):
        """1 Manager file, 8 edits, 5 lines -> should pass threshold."""
        paths = ["Assets/Scripts/Modules/Building/BuildingManager.cs"]
        modules = ["Building"]
        score, _ = flush.compute_score(paths, modules, 5, 8, flush.DEFAULT_WEIGHTS)
        self.assertGreaterEqual(score, flush.DEFAULT_THRESHOLD)

    def test_interface_refactor_high_score(self):
        """Interface file refactoring -> K=1.0, high score."""
        paths = ["Assets/Scripts/Modules/Building/IBuildingManager.cs"]
        modules = ["Building"]
        score, _ = flush.compute_score(paths, modules, 50, 5, flush.DEFAULT_WEIGHTS)
        self.assertGreater(score, 2.5)

    def test_multi_module_high_score(self):
        """4 files across 2 modules -> high F and D."""
        paths = [
            "Assets/Scripts/Modules/Building/BuildingManager.cs",
            "Assets/Scripts/Modules/Building/BuildingFunc.cs",
            "Assets/Scripts/Modules/NPC/NpcController.cs",
            "Assets/Scripts/Modules/NPC/NpcData.cs",
        ]
        modules = ["Building", "NPC"]
        score, _ = flush.compute_score(paths, modules, 100, 10, flush.DEFAULT_WEIGHTS)
        self.assertGreater(score, 3.0)

    def test_each_dimension_independent(self):
        """Each dimension should saturate at 1.0 independently."""
        paths = ["a.cs"] * 10
        modules = ["A", "B", "C"]
        score_saturated, breakdown = flush.compute_score(paths, modules, 200, 20, flush.DEFAULT_WEIGHTS)
        self.assertAlmostEqual(breakdown["F"], 1.0 * flush.DEFAULT_WEIGHTS["F"], places=2)
        self.assertAlmostEqual(breakdown["D"], 1.0 * flush.DEFAULT_WEIGHTS["D"], places=2)
        self.assertAlmostEqual(breakdown["E"], 1.0 * flush.DEFAULT_WEIGHTS["E"], places=2)


class TestCriticalTiers(unittest.TestCase):
    """Test K dimension tier classification."""

    def test_interface_tier(self):
        self.assertAlmostEqual(flush.compute_critical_tier(["IBuildingManager.cs"]), 1.0)
        self.assertAlmostEqual(flush.compute_critical_tier(["IQueueService.cs"]), 1.0)
        self.assertAlmostEqual(flush.compute_critical_tier(["ICombatSystem.cs"]), 1.0)

    def test_implementation_tier(self):
        self.assertAlmostEqual(flush.compute_critical_tier(["BuildingManager.cs"]), 0.6)
        self.assertAlmostEqual(flush.compute_critical_tier(["NpcHandler.cs"]), 0.6)
        self.assertAlmostEqual(flush.compute_critical_tier(["PlayerController.cs"]), 0.6)

    def test_base_tier(self):
        self.assertAlmostEqual(flush.compute_critical_tier(["ManagerBase.cs"]), 0.3)

    def test_no_tier(self):
        self.assertAlmostEqual(flush.compute_critical_tier(["PlayerData.cs"]), 0.0)
        self.assertAlmostEqual(flush.compute_critical_tier(["utils.cs"]), 0.0)

    def test_highest_tier_wins(self):
        paths = ["PlayerData.cs", "ManagerBase.cs", "IBuildingManager.cs"]
        self.assertAlmostEqual(flush.compute_critical_tier(paths), 1.0)


class TestCorrectionInference(unittest.TestCase):
    """Test correction field inference from revert counts."""

    def test_no_reverts(self):
        self.assertEqual(flush.infer_correction(0), "_")

    def test_minor_correction(self):
        self.assertEqual(flush.infer_correction(1), "auto:minor")
        self.assertEqual(flush.infer_correction(2), "auto:minor")

    def test_major_correction(self):
        self.assertEqual(flush.infer_correction(3), "auto:major")
        self.assertEqual(flush.infer_correction(10), "auto:major")


class TestModuleInference(unittest.TestCase):
    """Test module name inference from file paths."""

    def test_modules_dir_pattern(self):
        paths = ["Assets/Scripts/Modules/Building/BuildingManager.cs"]
        self.assertEqual(flush.infer_modules(paths), ["Building"])

    def test_multiple_modules(self):
        paths = [
            "Assets/Scripts/Modules/Building/Foo.cs",
            "Assets/Scripts/Modules/NPC/Bar.cs",
        ]
        self.assertEqual(flush.infer_modules(paths), ["Building", "NPC"])

    def test_fallback_non_generic_segment(self):
        paths = ["Assets/Scripts/GameLogic/Logic/Combat/CombatLogic.cs"]
        modules = flush.infer_modules(paths)
        self.assertIn("Combat", modules)

    def test_unknown_fallback(self):
        paths = ["Scripts/Assets/GameLogic/Logic/Render/UI/Core/Common/foo.cs"]
        modules = flush.infer_modules(paths)
        self.assertEqual(modules, ["Unknown"])


# ============================================================
# 3. Pipeline Result Bug Fix (P0)
# ============================================================

class TestPipelineResultFix(TestSetup):
    """P0: Verify apply_pipeline_result handles missing result field gracefully."""

    def test_json_format_go(self):
        """JSON with result=GO -> validated becomes true."""
        now = datetime.now(timezone.utc)
        block = make_trace_block(now, ["Building"], 2.0, validated="pending-pipeline", pipeline_run_id="run-001")
        self.write_trace(build_trace_file([block]))

        with open(flush.PENDING_PIPELINE_FILE, "w", encoding="utf-8") as f:
            json.dump({"pipeline_run_id": "run-001", "result": "GO"}, f)

        flush.apply_pipeline_result()
        content = self.read_trace()
        self.assertIn("validated: true", content)
        self.assertNotIn("pending-pipeline", content)

    def test_json_format_nogo(self):
        """JSON with result=NO-GO -> validated becomes false."""
        now = datetime.now(timezone.utc)
        block = make_trace_block(now, ["Building"], 2.0, validated="pending-pipeline", pipeline_run_id="run-002")
        self.write_trace(build_trace_file([block]))

        with open(flush.PENDING_PIPELINE_FILE, "w", encoding="utf-8") as f:
            json.dump({"pipeline_run_id": "run-002", "result": "NO-GO"}, f)

        flush.apply_pipeline_result()
        content = self.read_trace()
        self.assertIn("validated: false", content)

    def test_plaintext_fallback(self):
        """Plain text key:value format (non-JSON) should work."""
        now = datetime.now(timezone.utc)
        block = make_trace_block(now, ["NPC"], 2.0, validated="pending-pipeline", pipeline_run_id="run-003")
        self.write_trace(build_trace_file([block]))

        with open(flush.PENDING_PIPELINE_FILE, "w", encoding="utf-8") as f:
            f.write("pipeline_run_id: run-003\nresult: GO\n")

        flush.apply_pipeline_result()
        content = self.read_trace()
        self.assertIn("validated: true", content)

    def test_missing_result_field_no_crash(self):
        """P0 fix: missing result field should not crash (result_str initialized to '')."""
        now = datetime.now(timezone.utc)
        block = make_trace_block(now, ["Building"], 2.0, validated="pending-pipeline", pipeline_run_id="run-004")
        self.write_trace(build_trace_file([block]))

        with open(flush.PENDING_PIPELINE_FILE, "w", encoding="utf-8") as f:
            json.dump({"pipeline_run_id": "run-004"}, f)

        flush.apply_pipeline_result()
        content = self.read_trace()
        self.assertIn("pending-pipeline", content)

    def test_malformed_plaintext_no_crash(self):
        """Plaintext without result: line should not crash."""
        now = datetime.now(timezone.utc)
        block = make_trace_block(now, ["Building"], 2.0, validated="pending-pipeline", pipeline_run_id="run-005")
        self.write_trace(build_trace_file([block]))

        with open(flush.PENDING_PIPELINE_FILE, "w", encoding="utf-8") as f:
            f.write("pipeline_run_id: run-005\nsome_garbage: value\n")

        flush.apply_pipeline_result()
        content = self.read_trace()
        self.assertIn("pending-pipeline", content)

    def test_pipeline_file_cleaned_up(self):
        """Pipeline file should always be deleted after processing."""
        with open(flush.PENDING_PIPELINE_FILE, "w", encoding="utf-8") as f:
            f.write("{}")
        flush.apply_pipeline_result()
        self.assertFalse(os.path.isfile(flush.PENDING_PIPELINE_FILE))


# ============================================================
# 4. Validated Update Tests
# ============================================================

class TestValidatedUpdate(TestSetup):
    """Test the validated signal injection into trace entries."""

    def test_accept_updates_most_recent(self):
        now = datetime.now(timezone.utc)
        b1 = make_trace_block(now - timedelta(hours=2), ["A"], 2.0)
        b2 = make_trace_block(now - timedelta(hours=1), ["B"], 2.0)
        self.write_trace(build_trace_file([b1, b2]))

        with open(flush.PENDING_VALIDATED_FILE, "w", encoding="utf-8") as f:
            json.dump({"result": "accepted"}, f)

        flush.apply_validated_update()
        content = self.read_trace()
        blocks = re.findall(r"<!-- TRACE.*?<!-- /TRACE -->", content, re.DOTALL)
        self.assertIn("validated: _", blocks[0])
        self.assertIn("validated: true", blocks[1])

    def test_reject_signal(self):
        now = datetime.now(timezone.utc)
        block = make_trace_block(now, ["A"], 2.0)
        self.write_trace(build_trace_file([block]))

        with open(flush.PENDING_VALIDATED_FILE, "w", encoding="utf-8") as f:
            json.dump({"result": "rejected"}, f)

        flush.apply_validated_update()
        content = self.read_trace()
        self.assertIn("validated: false", content)

    def test_validated_file_always_cleaned(self):
        with open(flush.PENDING_VALIDATED_FILE, "w", encoding="utf-8") as f:
            f.write("invalid json {{{")
        flush.apply_validated_update()
        self.assertFalse(os.path.isfile(flush.PENDING_VALIDATED_FILE))


# ============================================================
# 5. Compaction Tests
# ============================================================

class TestCompactionValidatedProtection(TestSetup):
    """P1: validated:true/false entries must survive compaction."""

    def test_validated_false_survives_all_levels(self):
        """validated:false (P0 signal) must never be deleted by any compaction level."""
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=30)
        blocks = [
            make_trace_block(old, ["A"], 0.3, validated="false"),
            make_trace_block(old, ["B"], 0.3, validated="_"),
        ]
        self.write_limits({"compact_max_entries": 1, "level2_age_days": 1, "level2_score_threshold": 5.0,
                           "level3_age_days": 1, "level3_score_threshold": 5.0})
        content = build_trace_file(blocks)
        limits = flush.load_limits()
        flush.compact_trace(content, limits)

        result = self.read_trace()
        self.assertIn("validated: false", result)

    def test_validated_true_survives_level2(self):
        """validated:true entries should survive Level 2 compaction."""
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=30)
        blocks = [
            make_trace_block(old, ["A"], 0.3, validated="true"),
            make_trace_block(old, ["B"], 0.3, validated="_"),
        ]
        self.write_limits({"compact_max_entries": 100, "level2_age_days": 1, "level2_score_threshold": 5.0})
        content = build_trace_file(blocks)
        limits = flush.load_limits()
        flush.compact_trace(content, limits)

        result = self.read_trace()
        self.assertIn("validated: true", result)
        self.assertNotIn("validated: _", result)

    def test_pending_pipeline_never_deleted(self):
        """pending-pipeline entries must survive all levels."""
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=60)
        blocks = [make_trace_block(old, ["A"], 0.1, validated="pending-pipeline")]
        self.write_limits({"compact_max_entries": 0, "level2_age_days": 1, "level2_score_threshold": 10.0,
                           "level3_age_days": 1, "level3_score_threshold": 10.0})
        content = build_trace_file(blocks)
        limits = flush.load_limits()
        flush.compact_trace(content, limits)

        if os.path.isfile(flush.TRACE_FILE):
            result = self.read_trace()
        else:
            result = content
        self.assertIn("pending-pipeline", result)


class TestCompactionExpiredInvalid(TestSetup):
    """Level 1: expired and invalid entries should be removed."""

    def test_expired_entries_removed(self):
        now = datetime.now(timezone.utc)
        blocks = [
            make_trace_block(now, ["A"], 2.0, status="expired"),
            make_trace_block(now, ["B"], 2.0, status="pending"),
        ]
        self.write_limits({"compact_max_entries": 0})
        content = build_trace_file(blocks)
        limits = flush.load_limits()
        flush.compact_trace(content, limits)

        result = self.read_trace()
        self.assertNotIn("status:expired", result)
        self.assertIn("status:pending", result)

    def test_invalid_validated_removed(self):
        now = datetime.now(timezone.utc)
        blocks = [
            make_trace_block(now, ["A"], 2.0, validated="invalid"),
            make_trace_block(now, ["B"], 2.0),
        ]
        self.write_limits({"compact_max_entries": 0})
        content = build_trace_file(blocks)
        limits = flush.load_limits()
        flush.compact_trace(content, limits)

        result = self.read_trace()
        self.assertNotIn("validated: invalid", result)


class TestCompactionLevel2(TestSetup):
    """Level 2: old + low-score entries removed (respecting validated)."""

    def test_old_low_score_removed(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=20)
        blocks = [
            make_trace_block(old, ["A"], 0.5),
            make_trace_block(now, ["B"], 3.0),
        ]
        self.write_limits({"compact_max_entries": 0, "level2_age_days": 14, "level2_score_threshold": 1.0})
        content = build_trace_file(blocks)
        limits = flush.load_limits()
        flush.compact_trace(content, limits)

        result = self.read_trace()
        blocks_found = re.findall(r"<!-- TRACE.*?<!-- /TRACE -->", result, re.DOTALL)
        self.assertEqual(len(blocks_found), 1)
        self.assertIn("modules: [B]", blocks_found[0])

    def test_young_low_score_survives(self):
        """Entries younger than level2_age_days survive even with low score."""
        now = datetime.now(timezone.utc)
        young = now - timedelta(days=5)
        blocks = [make_trace_block(young, ["A"], 0.5)]
        self.write_limits({"compact_max_entries": 0, "level2_age_days": 14, "level2_score_threshold": 1.0})
        content = build_trace_file(blocks)
        limits = flush.load_limits()
        flush.compact_trace(content, limits)

        if os.path.isfile(flush.TRACE_FILE):
            result = self.read_trace()
        else:
            result = content
        self.assertIn("modules: [A]", result)


class TestCompactionLevel3KeepTopN(TestSetup):
    """P2: Level 3 must respect keep_top_n_per_module."""

    def test_module_minimum_preserved(self):
        """Even under extreme pressure, each module keeps at least N entries."""
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=10)
        blocks = []
        for i in range(5):
            blocks.append(make_trace_block(old, ["RareModule"], 0.3))
        for i in range(10):
            blocks.append(make_trace_block(old, ["CommonModule"], 0.3))

        self.write_limits({
            "compact_max_entries": 5,
            "level2_age_days": 100, "level2_score_threshold": 0.0,
            "level3_age_days": 1, "level3_score_threshold": 5.0,
            "keep_top_n_per_module": 3,
        })
        content = build_trace_file(blocks)
        limits = flush.load_limits()
        flush.compact_trace(content, limits)

        result = self.read_trace()
        rare_count = result.count("RareModule")
        common_count = result.count("CommonModule")
        self.assertGreaterEqual(rare_count, 3, "RareModule should keep at least 3 entries")
        self.assertGreaterEqual(common_count, 3, "CommonModule should keep at least 3 entries")


class TestCompactionAuditLineCleanup(TestSetup):
    """P1: PROCESSED and COMPACTED audit lines should be cleaned after expiry."""

    def test_old_processed_lines_removed(self):
        now = datetime.now(timezone.utc)
        old_ts = (now - timedelta(days=45)).strftime("%Y-%m-%dT%H:%M:%SZ")
        recent_ts = (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        old_expired = now - timedelta(days=30)

        content = (
            "# Execution Traces\n\n---\n\n"
            "<!-- PROCESSED ts:{old} entries:5 proposals:2 -->\n"
            "<!-- COMPACTED ts:{old} removed:3 kept:10 -->\n"
            "<!-- PROCESSED ts:{recent} entries:3 proposals:1 -->\n"
        ).format(old=old_ts, recent=recent_ts)

        # Add an expired block so compaction actually writes the file
        content += make_trace_block(old_expired, ["Expired"], 0.3, status="expired") + "\n"
        content += make_trace_block(now, ["Keep"], 2.0) + "\n"

        self.write_limits({"compact_max_entries": 0, "processed_expire_days": 30})
        limits = flush.load_limits()
        flush.compact_trace(content, limits)

        result = self.read_trace()
        self.assertNotIn(old_ts, result, "Old audit lines should be removed")
        self.assertIn(recent_ts, result, "Recent audit lines should survive")

    def test_recent_audit_lines_preserved(self):
        now = datetime.now(timezone.utc)
        recent_ts = (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        old_expired = now - timedelta(days=30)

        content = (
            "# Traces\n\n"
            "<!-- PROCESSED ts:{} entries:5 proposals:2 -->\n"
        ).format(recent_ts)
        content += make_trace_block(old_expired, ["Expired"], 0.3, status="expired") + "\n"
        content += make_trace_block(now, ["Keep"], 2.0) + "\n"

        self.write_limits({"compact_max_entries": 0, "processed_expire_days": 30})
        limits = flush.load_limits()
        flush.compact_trace(content, limits)

        result = self.read_trace()
        self.assertIn(recent_ts, result)


class TestCompactionBlankLineCleanup(TestSetup):
    """P2: consecutive blank lines should be collapsed after compaction."""

    def test_no_triple_newlines_after_compact(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=30)
        blocks = []
        for i in range(5):
            blocks.append(make_trace_block(old, ["Mod{}".format(i)], 0.3))

        content = build_trace_file(blocks)
        content = content.replace("\n\n", "\n\n\n\n\n")

        self.write_limits({"compact_max_entries": 0, "level2_age_days": 1, "level2_score_threshold": 5.0})
        limits = flush.load_limits()
        flush.compact_trace(content, limits)

        result = self.read_trace()
        self.assertNotIn("\n\n\n", result, "Should not have 3+ consecutive newlines")


# ============================================================
# 6. Lock Management Tests
# ============================================================

class TestLockManagement(TestSetup):
    """Verify compaction respects .trace_lock."""

    def test_compaction_skipped_when_locked(self):
        with open(flush.TRACE_LOCK_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write("locked")

        now = datetime.now(timezone.utc)
        blocks = [make_trace_block(now, ["A"], 2.0) for _ in range(100)]
        self.write_trace(build_trace_file(blocks))

        self.write_limits({"compact_max_entries": 10})
        flush.check_and_compact()

        content = self.read_trace()
        block_count = len(re.findall(r"<!-- TRACE ", content))
        self.assertEqual(block_count, 100, "Compaction should be skipped when locked")


# ============================================================
# 7. Passive Trigger Tests
# ============================================================

class TestPassiveTrigger(TestSetup):
    """Test passive trigger notification logic."""

    def test_notify_at_threshold(self):
        now = datetime.now(timezone.utc)
        blocks = [make_trace_block(now - timedelta(hours=i), ["Mod"], 2.0) for i in range(12)]
        self.write_trace(build_trace_file(blocks))
        self.write_limits({"passive_trigger_threshold": 10, "passive_trigger_min_new": 5})

        flush.check_notify()
        content = self.read_trace()
        self.assertIn("<!-- NOTIFY type:passive_trigger -->", content)

    def test_no_notify_below_threshold(self):
        now = datetime.now(timezone.utc)
        blocks = [make_trace_block(now, ["Mod"], 2.0) for _ in range(5)]
        self.write_trace(build_trace_file(blocks))
        self.write_limits({"passive_trigger_threshold": 10, "passive_trigger_min_new": 5})

        flush.check_notify()
        content = self.read_trace()
        self.assertNotIn("NOTIFY", content)

    def test_no_repeat_notify(self):
        """Should not re-notify if not enough new entries since last notification."""
        now = datetime.now(timezone.utc)
        blocks = [make_trace_block(now - timedelta(hours=i), ["Mod"], 2.0) for i in range(12)]
        self.write_trace(build_trace_file(blocks))
        self.write_limits({"passive_trigger_threshold": 10, "passive_trigger_min_new": 5})

        with open(flush.NOTIFY_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_pending_count": 10}, f)

        flush.check_notify()
        content = self.read_trace()
        self.assertNotIn("NOTIFY", content)


# ============================================================
# 8. Flush Integration Tests
# ============================================================

class TestFlushIntegration(TestSetup):
    """End-to-end flush: buffer -> score -> trace.md."""

    def test_high_score_trace_written(self):
        self.write_buffer([
            "Assets/Scripts/Modules/Building/BuildingManager.cs|50|8|R",
            "Assets/Scripts/Modules/Building/BuildingFunc.cs|20|3|",
        ])
        flush.flush_new_trace(idp=None)

        self.assertTrue(os.path.isfile(flush.TRACE_FILE))
        content = self.read_trace()
        self.assertIn("<!-- TRACE status:pending -->", content)
        self.assertIn("Building", content)
        self.assertIn("auto:minor", content)

    def test_low_score_trace_not_written(self):
        self.write_buffer(["Assets/Scripts/data.cs|1|1|"])
        flush.flush_new_trace(idp=None)

        if os.path.isfile(flush.TRACE_FILE):
            content = self.read_trace()
            self.assertNotIn("<!-- TRACE", content)

    def test_buffer_cleared_after_flush(self):
        self.write_buffer(["Assets/Scripts/Modules/Building/BuildingManager.cs|50|8|"])
        flush.flush_new_trace(idp=None)
        self.assertFalse(os.path.isfile(flush.BUFFER_FILE))

    def test_idp_fields_injected(self):
        self.write_buffer([
            "Assets/Scripts/Modules/Building/IBuildingManager.cs|50|8|",
        ])
        idp = {
            "mode": "standard",
            "request": "add batch upgrade",
            "intent": "implement batch upgrade feature",
            "type": "feature",
            "skills": ["programmer-building-skill"],
        }
        flush.flush_new_trace(idp=idp)

        content = self.read_trace()
        self.assertIn("mode: standard", content)
        self.assertIn("type: feature", content)
        self.assertIn("request: add batch upgrade", content)

    def test_pipeline_context_detected(self):
        """When PIPELINE_CONTEXT.md exists, validated should be pending-pipeline."""
        context_dir = os.path.abspath(os.path.join(self.traces_dir, "..", "..", ".."))
        os.makedirs(context_dir, exist_ok=True)
        context_file = os.path.join(context_dir, "PIPELINE_CONTEXT.md")
        with open(context_file, "w", encoding="utf-8") as f:
            f.write("pipeline_run_id: test-run-99\n")

        self.write_buffer([
            "Assets/Scripts/Modules/Building/IBuildingManager.cs|50|8|",
        ])
        flush.flush_new_trace(idp=None)

        if os.path.isfile(flush.TRACE_FILE):
            content = self.read_trace()
            if "<!-- TRACE" in content:
                self.assertIn("pending-pipeline", content)
                self.assertIn("test-run-99", content)

        try:
            os.remove(context_file)
        except OSError:
            pass


# ============================================================
# 9. Stress / Edge Case Tests
# ============================================================

class TestStressCompaction(TestSetup):
    """Stress test compaction with large trace files."""

    def test_100_entries_compacted(self):
        now = datetime.now(timezone.utc)
        blocks = []
        for i in range(100):
            age = timedelta(days=i)
            blocks.append(make_trace_block(now - age, ["Mod{}".format(i % 5)], 0.3 + (i % 10) * 0.1))

        self.write_limits({
            "compact_max_entries": 30,
            "level2_age_days": 14, "level2_score_threshold": 1.0,
            "level3_age_days": 7, "level3_score_threshold": 0.5,
            "keep_top_n_per_module": 3,
        })
        content = build_trace_file(blocks)
        limits = flush.load_limits()
        flush.compact_trace(content, limits)

        result = self.read_trace()
        remaining = len(re.findall(r"<!-- TRACE ", result))
        self.assertLessEqual(remaining, 50, "Should have compacted significantly")
        self.assertGreater(remaining, 0, "Should not have deleted everything")

    def test_all_validated_false_no_deletion(self):
        """If all entries are validated:false, compaction should not delete any."""
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=60)
        blocks = [make_trace_block(old, ["A"], 0.1, validated="false") for _ in range(20)]

        self.write_limits({"compact_max_entries": 5, "level2_age_days": 1, "level2_score_threshold": 10.0,
                           "level3_age_days": 1, "level3_score_threshold": 10.0})
        content = build_trace_file(blocks)
        limits = flush.load_limits()
        flush.compact_trace(content, limits)

        if os.path.isfile(flush.TRACE_FILE):
            result = self.read_trace()
        else:
            result = content
        count = len(re.findall(r"<!-- TRACE ", result))
        self.assertEqual(count, 20, "All validated:false entries must survive")

    def test_mixed_validated_compaction(self):
        """Mix of validated values: false protected, true protected in L2, _ eligible."""
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=30)
        blocks = [
            make_trace_block(old, ["A"], 0.3, validated="false"),
            make_trace_block(old, ["B"], 0.3, validated="true"),
            make_trace_block(old, ["C"], 0.3, validated="_"),
            make_trace_block(old, ["D"], 0.3, validated="_"),
            make_trace_block(old, ["E"], 0.3, validated="pending-pipeline"),
        ]
        self.write_limits({"compact_max_entries": 0, "level2_age_days": 1, "level2_score_threshold": 5.0})
        content = build_trace_file(blocks)
        limits = flush.load_limits()
        flush.compact_trace(content, limits)

        result = self.read_trace()
        self.assertIn("validated: false", result)
        self.assertIn("validated: true", result)
        self.assertIn("pending-pipeline", result)
        self.assertNotIn("modules: [C]", result)
        self.assertNotIn("modules: [D]", result)


class TestEdgeCases(TestSetup):
    """Miscellaneous edge cases."""

    def test_empty_buffer_no_crash(self):
        flush.flush_new_trace(idp=None)

    def test_empty_trace_no_crash(self):
        flush.check_and_compact()
        flush.check_notify()

    def test_corrupt_weights_uses_defaults(self):
        with open(flush.WEIGHTS_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write("{invalid json")
        weights, threshold = flush.load_weights()
        self.assertEqual(weights, flush.DEFAULT_WEIGHTS)
        self.assertEqual(threshold, flush.DEFAULT_THRESHOLD)

    def test_corrupt_limits_uses_defaults(self):
        with open(flush.LIMITS_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write("not json at all")
        limits = flush.load_limits()
        self.assertEqual(limits, flush.DEFAULT_LIMITS)

    def test_trace_format_has_all_fields(self):
        """Verify format_trace produces all expected fields."""
        entry = flush.format_trace(
            ["a.cs", "b.cs"], ["Building"], 2.5, 50, 8, "auto:minor",
            idp={"mode": "standard", "request": "test", "intent": "test intent",
                 "type": "feature", "skills": ["skill-a"]},
            pipeline_run_id="run-X"
        )
        for field in ["timestamp", "mode", "type", "request", "intent", "correction",
                       "validated", "pipeline_run_id", "modules", "skills",
                       "files_modified", "file_count", "lines_changed", "edit_count", "score"]:
            self.assertIn(field + ":", entry, "Missing field: {}".format(field))

    def test_idp_cleanup_always_runs(self):
        """IDP file should be cleaned up even if flush crashes."""
        with open(flush.PENDING_IDP_FILE, "w", encoding="utf-8") as f:
            json.dump({"mode": "test"}, f)
        flush.cleanup_pending_files()
        self.assertFalse(os.path.isfile(flush.PENDING_IDP_FILE))

    def test_normalize_path_backslash(self):
        self.assertEqual(collector.normalize_path("C:\\Users\\test\\foo.cs"), "C:/Users/test/foo.cs")

    def test_extract_file_path_cursor_format(self):
        event = {"input": {"filePath": "Assets/Scripts/Foo.cs"}}
        self.assertEqual(collector.extract_file_path(event), "Assets/Scripts/Foo.cs")

    def test_extract_file_path_claude_format(self):
        event = {"tool_input": {"file_path": "src/main.py"}}
        self.assertEqual(collector.extract_file_path(event), "src/main.py")

    def test_extract_file_path_none_on_empty(self):
        self.assertIsNone(collector.extract_file_path({}))
        self.assertIsNone(collector.extract_file_path(None))

    def test_estimate_lines_old_new_string(self):
        event = {"input": {"oldString": "line1\nline2", "newString": "line1\nline2\nline3"}}
        lines = collector.estimate_lines_changed(event)
        self.assertGreater(lines, 0)


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("CastFlow Self-Evolution System - Comprehensive Test Suite")
    if KEEP_DATA:
        print("Mode: --keep-data  (output -> test-output/evolution/)")
    print("=" * 70)
    unittest.main(verbosity=2)
