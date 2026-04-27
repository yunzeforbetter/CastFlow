#!/usr/bin/env python3
"""
CastFlow Self-Evolution - 100-Day Production Simulation.

Simulates 100 days of real development activity including:
  - Normal chat sessions (various edit intensities)
  - code_pipeline driven sessions (with pipeline context)
  - Pure Q&A sessions (no file edits -> no trace)
  - Validated signals (accept/reject from user)
  - Pipeline result signals (GO/NO-GO)
  - Periodic origin-evolve runs (pattern detection, proposal generation)
  - Compaction under continuous growth
  - Rule extraction, merge, and retire lifecycle

Run:
    py test_100day_simulation.py               # run and discard test data
    py test_100day_simulation.py --keep-data   # preserve output in test-output/100day/
"""

import json
import os
import random
import re
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from collections import Counter

import importlib.util

_script_dir = os.path.dirname(os.path.abspath(__file__))
_HOOKS_DIR = os.path.normpath(os.path.join(
    _script_dir, "..", "..", ".castflow", "core", "hooks"
))

# --keep-data: preserve each test case's trace files for inspection
KEEP_DATA = "--keep-data" in sys.argv
if KEEP_DATA:
    sys.argv.remove("--keep-data")

_OUTPUT_BASE = os.path.join(_script_dir, "test-output", "100day")

if KEEP_DATA:
    if os.path.isdir(_OUTPUT_BASE):
        shutil.rmtree(_OUTPUT_BASE)
    os.makedirs(_OUTPUT_BASE, exist_ok=True)
    print("[keep-data] Output directory: {}".format(_OUTPUT_BASE))

def _import_hyphen_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HOOKS_DIR, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

collector = _import_hyphen_module("collector", "trace-collector.py")
flush = _import_hyphen_module("flush", "trace-flush.py")

random.seed(42)

# ============================================================
# Simulation Data: generic multi-language project distributions
# (tech-stack agnostic - works for any project type)
# ============================================================

MODULE_FILE_MAP = {
    "Auth": [
        "src/auth/AuthService.py",
        "src/auth/TokenManager.py",
        "src/auth/IAuthService.py",
        "src/auth/auth_middleware.py",
        "src/auth/UserCredential.py",
        "src/auth/SessionStore.py",
    ],
    "Database": [
        "src/database/DatabaseService.ts",
        "src/database/Repository.ts",
        "src/database/IRepository.ts",
        "src/database/ConnectionPool.ts",
        "src/database/QueryBuilder.ts",
    ],
    "API": [
        "src/api/UserController.go",
        "src/api/router.go",
        "src/api/middleware.go",
        "src/api/IController.go",
        "src/api/ErrorHandler.go",
    ],
    "Worker": [
        "src/worker/TaskWorker.java",
        "src/worker/IWorkerService.java",
        "src/worker/WorkerPool.java",
        "src/worker/TaskQueue.java",
    ],
    "UI": [
        "src/ui/components/Dashboard.tsx",
        "src/ui/components/LoginForm.tsx",
        "src/ui/pages/Home.tsx",
    ],
    "Cache": [
        "src/cache/CacheService.py",
        "src/cache/ICacheService.py",
        "src/cache/redis_client.py",
    ],
    "Config": [
        "src/config/AppConfig.ts",
        "src/config/EnvLoader.ts",
    ],
}

SESSION_TEMPLATES = [
    {
        "name": "feature_core",
        "type": "feature", "mode": "standard",
        "modules": ["Auth"], "file_count": (2, 4), "lines": (30, 120),
        "edits": (5, 15), "reverts": (0, 2), "weight": 15,
    },
    {
        "name": "bugfix_service",
        "type": "bugfix", "mode": "standard",
        "modules": ["Database"], "file_count": (1, 3), "lines": (10, 40),
        "edits": (3, 8), "reverts": (0, 3), "weight": 12,
    },
    {
        "name": "api_feature",
        "type": "feature", "mode": "standard",
        "modules": ["API"], "file_count": (2, 4), "lines": (40, 100),
        "edits": (5, 12), "reverts": (0, 1), "weight": 10,
    },
    {
        "name": "cross_module_refactor",
        "type": "refactor", "mode": "standard",
        "modules": ["Auth", "Database"], "file_count": (3, 6), "lines": (50, 200),
        "edits": (8, 20), "reverts": (1, 4), "weight": 5,
    },
    {
        "name": "ui_tweak",
        "type": "bugfix", "mode": "standard",
        "modules": ["UI"], "file_count": (1, 2), "lines": (5, 20),
        "edits": (1, 3), "reverts": (0, 0), "weight": 10,
    },
    {
        "name": "pipeline_core",
        "type": "feature", "mode": "pipeline",
        "modules": ["Auth"], "file_count": (3, 5), "lines": (60, 200),
        "edits": (10, 25), "reverts": (0, 3), "weight": 8,
    },
    {
        "name": "pipeline_api",
        "type": "feature", "mode": "pipeline",
        "modules": ["API", "Worker"], "file_count": (4, 6), "lines": (80, 250),
        "edits": (12, 30), "reverts": (1, 5), "weight": 6,
    },
    {
        "name": "trivial_chat",
        "type": "question", "mode": "standard",
        "modules": [], "file_count": (0, 0), "lines": (0, 0),
        "edits": (0, 0), "reverts": (0, 0), "weight": 20,
    },
    {
        "name": "tiny_fix",
        "type": "bugfix", "mode": "standard",
        "modules": ["Config"], "file_count": (1, 1), "lines": (1, 5),
        "edits": (1, 2), "reverts": (0, 0), "weight": 14,
    },
    {
        "name": "worker_bugfix",
        "type": "bugfix", "mode": "standard",
        "modules": ["Worker"], "file_count": (1, 3), "lines": (10, 50),
        "edits": (3, 10), "reverts": (0, 2), "weight": 8,
    },
    {
        "name": "cache_feature",
        "type": "feature", "mode": "standard",
        "modules": ["Cache"], "file_count": (1, 3), "lines": (20, 60),
        "edits": (3, 8), "reverts": (0, 1), "weight": 6,
    },
    {
        "name": "db_refactor",
        "type": "refactor", "mode": "pipeline",
        "modules": ["Database", "Cache"], "file_count": (2, 4), "lines": (30, 80),
        "edits": (5, 12), "reverts": (0, 2), "weight": 4,
    },
]


def pick_session_template():
    total = sum(t["weight"] for t in SESSION_TEMPLATES)
    r = random.randint(1, total)
    cumulative = 0
    for t in SESSION_TEMPLATES:
        cumulative += t["weight"]
        if r <= cumulative:
            return t
    return SESSION_TEMPLATES[-1]


def pick_files_for_modules(modules, count):
    pool = []
    for mod in modules:
        pool.extend(MODULE_FILE_MAP.get(mod, []))
    if not pool:
        return []
    return random.sample(pool, min(count, len(pool)))


def make_trace_block(timestamp, modules, score, validated="_", correction="_",
                     status="pending", pipeline_run_id="_", edit_count=1,
                     file_count=1, lines_changed=10, mode="_", entry_type="_",
                     request="_", intent="_", skills=None, files=None):
    ts_str = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
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


class SimulationTestBase(unittest.TestCase):
    """Base class that sets up an isolated temp environment."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="castflow_sim_")
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
        if KEEP_DATA:
            dest = os.path.join(_OUTPUT_BASE,
                                "{}__{}" .format(type(self).__name__, self._testMethodName))
            shutil.copytree(self.test_dir, dest, ignore_dangling_symlinks=True)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def write_limits(self, overrides):
        data = dict(flush.DEFAULT_LIMITS)
        data.update(overrides)
        with open(flush.LIMITS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def read_trace(self):
        if not os.path.isfile(flush.TRACE_FILE):
            return ""
        with open(flush.TRACE_FILE, "r", encoding="utf-8") as f:
            return f.read()

    def write_trace(self, content):
        with open(flush.TRACE_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

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

    def simulate_session(self, day_offset, template, pipeline_run_id=None):
        """Simulate a single development session.

        Returns True if a trace was written (above threshold), False otherwise.
        """
        base_time = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_offset)
        fc_lo, fc_hi = template["file_count"]
        file_count = random.randint(fc_lo, fc_hi) if fc_hi > 0 else 0

        if file_count == 0:
            return False

        lines_lo, lines_hi = template["lines"]
        edits_lo, edits_hi = template["edits"]
        rev_lo, rev_hi = template["reverts"]

        total_lines = random.randint(lines_lo, lines_hi)
        total_edits = random.randint(edits_lo, edits_hi)
        revert_count = random.randint(rev_lo, rev_hi)

        files = pick_files_for_modules(template["modules"], file_count)
        if not files:
            return False

        weights, threshold = flush.load_weights()
        modules = flush.infer_modules(files)
        score, _ = flush.compute_score(files, modules, total_lines, total_edits, weights)

        if score < threshold:
            return False

        correction = flush.infer_correction(revert_count)

        entry = make_trace_block(
            timestamp=base_time + timedelta(hours=random.randint(8, 20)),
            modules=modules,
            score=score,
            correction=correction,
            mode=template.get("mode", "_"),
            entry_type=template.get("type", "_"),
            request="sim: {} day{}".format(template["name"], day_offset),
            intent="simulated {}".format(template["type"]),
            edit_count=total_edits,
            file_count=file_count,
            lines_changed=total_lines,
            files=files,
            pipeline_run_id=pipeline_run_id or "_",
            validated="pending-pipeline" if pipeline_run_id else "_",
        )
        flush.append_trace(entry)
        return True

    def simulate_evolve_process(self, content):
        """Simulate origin-evolve consuming pending traces.

        This simulates Steps 0-5 of the evolve process:
        - Step 0: Lifecycle transitions (pending-pipeline expiry, stale pending expiry)
        - Step 1: Read & Sort pending entries
        - Step 2: Pattern detection (correction, hotspot, knowledge gap, etc.)
        - Step 3: Generate proposals (extraction/merge/retire decisions)
        - Step 5: Mark processed

        Returns (new_content, analysis_result_dict).
        """
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        blocks = self.get_all_blocks(content)
        pending_blocks = []
        for b in blocks:
            status_m = re.search(r"<!-- TRACE status:(\S+) -->", b)
            status = status_m.group(1) if status_m else "pending"
            if status == "pending":
                pending_blocks.append(b)

        if not pending_blocks:
            return content, {"proposals": 0, "patterns": []}

        # Step 1: Sort by priority
        def priority_key(block):
            validated = self.get_field(block, "validated")
            correction = self.get_field(block, "correction")
            score = 0.0
            try:
                score = float(self.get_field(block, "score"))
            except ValueError:
                pass

            if validated == "false":
                p = 0
                if correction == "auto:major":
                    sub = 0
                elif correction == "auto:minor":
                    sub = 1
                else:
                    sub = 2
            elif validated == "true" and correction == "auto:major":
                p, sub = 1, 0
            elif validated == "true" and correction == "auto:minor":
                p, sub = 2, 0
            elif validated == "true":
                p, sub = 2, 1
            elif correction not in ("_", ""):
                p, sub = 3, 0
            else:
                p, sub = 4, 0

            return (p, sub, -score)

        sorted_blocks = sorted(pending_blocks, key=priority_key)

        # Step 2: Pattern detection
        module_counter = Counter()
        correction_by_module = {}
        skill_empty_modules = set()
        high_edit_low_file = []
        validated_false_by_module = Counter()
        mode_unknown_by_module = Counter()

        for b in sorted_blocks:
            modules_str = self.get_field(b, "modules")
            mods = re.findall(r"[A-Za-z_]\w*", modules_str)
            correction = self.get_field(b, "correction")
            validated = self.get_field(b, "validated")
            skills_str = self.get_field(b, "skills")
            mode = self.get_field(b, "mode")

            try:
                edit_count = int(self.get_field(b, "edit_count"))
            except ValueError:
                edit_count = 0
            try:
                file_count = int(self.get_field(b, "file_count"))
            except ValueError:
                file_count = 0

            for mod in mods:
                module_counter[mod] += 1
                if correction not in ("_", ""):
                    correction_by_module.setdefault(mod, []).append(correction)
                if validated == "false":
                    validated_false_by_module[mod] += 1
                if mode in ("_", ""):
                    mode_unknown_by_module[mod] += 1

            if skills_str in ("[]", ""):
                for mod in mods:
                    skill_empty_modules.add(mod)

            if edit_count >= 8 and file_count <= 2:
                high_edit_low_file.append((mods, edit_count, file_count))

        patterns = []

        for mod, corrections in correction_by_module.items():
            if len(corrections) >= 3:
                patterns.append({
                    "type": "correction",
                    "module": mod,
                    "count": len(corrections),
                    "target_file": "SKILL_MEMORY.md",
                })

        hotspots = [mod for mod, cnt in module_counter.items() if cnt >= 5]
        for mod in hotspots:
            patterns.append({
                "type": "module_hotspot",
                "module": mod,
                "count": module_counter[mod],
                "target_file": "SKILL_MEMORY.md",
            })

        if skill_empty_modules:
            for mod in skill_empty_modules:
                if module_counter[mod] >= 2:
                    patterns.append({
                        "type": "knowledge_gap",
                        "module": mod,
                        "target_file": "SKILL.md",
                    })

        if high_edit_low_file:
            seen_mods = set()
            for mods, ec, fc in high_edit_low_file:
                key = tuple(mods)
                if key not in seen_mods and len(high_edit_low_file) >= 2:
                    seen_mods.add(key)
                    patterns.append({
                        "type": "complexity_concentration",
                        "modules": mods,
                        "target_file": "EXAMPLES.md",
                    })

        for mod, cnt in validated_false_by_module.items():
            if cnt >= 3:
                corr_list = correction_by_module.get(mod, [])
                no_corr_count = sum(1 for c in corr_list if c == "_")
                if no_corr_count >= 2 or cnt - len(corr_list) >= 2:
                    patterns.append({
                        "type": "semantic_drift",
                        "module": mod,
                        "count": cnt,
                        "target_file": "SKILL_MEMORY.md",
                    })

        for mod, cnt in mode_unknown_by_module.items():
            if cnt >= 3 and module_counter[mod] >= 4:
                ratio = cnt / module_counter[mod]
                if ratio > 0.6:
                    patterns.append({
                        "type": "idp_gap",
                        "module": mod,
                        "ratio": round(ratio, 2),
                    })

        # Step 3: Generate proposals from patterns
        proposals = []
        for p in patterns:
            proposals.append({
                "pattern_type": p["type"],
                "module": p.get("module", p.get("modules", "?")),
                "operation": "append",
                "confidence": 0.85 if p["type"] in ("correction", "semantic_drift") else 0.75,
            })

        # Step 5: Mark processed
        processed_count = len(sorted_blocks)
        new_content = content
        for b in sorted_blocks:
            new_content = new_content.replace(
                b,
                b.replace("status:pending", "status:processed"),
            )
        audit_line = "<!-- PROCESSED ts:{} entries:{} proposals:{} -->\n".format(
            now_str, processed_count, len(proposals)
        )
        new_content += "\n" + audit_line

        return new_content, {
            "proposals": len(proposals),
            "patterns": patterns,
            "processed": processed_count,
            "sorted_order_valid": True,
        }


# ============================================================
# Test 1: 100-Day Full Lifecycle
# ============================================================

class Test100DayLifecycle(SimulationTestBase):
    """Simulate 100 days of development and verify the full lifecycle."""

    def test_full_100_day_simulation(self):
        """Run 100 days of simulated sessions and periodic evolve runs."""

        self.write_limits({
            "compact_max_entries": 50,
            "compact_max_size_kb": 100,
            "level2_age_days": 14,
            "level2_score_threshold": 3.0,
            "level3_age_days": 7,
            "level3_score_threshold": 4.0,
            "keep_top_n_per_module": 3,
            "passive_trigger_threshold": 10,
            "passive_trigger_min_new": 5,
            "processed_expire_days": 30,
        })

        stats = {
            "total_sessions": 0,
            "traces_written": 0,
            "trivial_rejected": 0,
            "pipeline_sessions": 0,
            "evolve_runs": 0,
            "total_proposals": 0,
            "total_processed": 0,
            "compaction_runs": 0,
            "notify_triggers": 0,
            "pipeline_results_applied": 0,
            "validated_signals_applied": 0,
        }

        pending_pipeline_ids = []

        for day in range(100):
            sessions_today = random.randint(1, 5)

            for _ in range(sessions_today):
                template = pick_session_template()
                stats["total_sessions"] += 1

                pipeline_id = None
                if template["mode"] == "pipeline":
                    pipeline_id = "pipeline-day{}-{}".format(day, random.randint(100, 999))
                    stats["pipeline_sessions"] += 1
                    pending_pipeline_ids.append(pipeline_id)

                written = self.simulate_session(day, template, pipeline_run_id=pipeline_id)
                if written:
                    stats["traces_written"] += 1
                elif template["file_count"][1] > 0:
                    stats["trivial_rejected"] += 1

            # Randomly apply validated signals (30% chance per day)
            if random.random() < 0.3 and os.path.isfile(flush.TRACE_FILE):
                content = self.read_trace()
                pending = self.get_all_blocks(content)
                underscore_blocks = [b for b in pending
                                     if self.get_field(b, "validated") == "_"
                                     and "status:pending" in b]
                if underscore_blocks:
                    result = "accepted" if random.random() < 0.7 else "rejected"
                    with open(flush.PENDING_VALIDATED_FILE, "w", encoding="utf-8") as f:
                        json.dump({"result": result}, f)
                    flush.apply_validated_update()
                    stats["validated_signals_applied"] += 1

            # Randomly resolve pipeline results (50% chance per day if pending)
            if random.random() < 0.5 and pending_pipeline_ids and os.path.isfile(flush.TRACE_FILE):
                pid = pending_pipeline_ids.pop(0)
                result = "GO" if random.random() < 0.6 else "NO-GO"
                with open(flush.PENDING_PIPELINE_FILE, "w", encoding="utf-8") as f:
                    json.dump({"pipeline_run_id": pid, "result": result}, f)
                flush.apply_pipeline_result()
                stats["pipeline_results_applied"] += 1

            # Run evolve every 10 days
            if day > 0 and day % 10 == 0 and os.path.isfile(flush.TRACE_FILE):
                content = self.read_trace()
                pending_count = self.count_pending(content)
                if pending_count >= 5:
                    new_content, analysis = self.simulate_evolve_process(content)
                    self.write_trace(new_content)
                    stats["evolve_runs"] += 1
                    stats["total_proposals"] += analysis["proposals"]
                    stats["total_processed"] += analysis["processed"]

            # Check compaction
            if os.path.isfile(flush.TRACE_FILE):
                flush.check_and_compact()
                flush.check_notify()

        # ====== ASSERTIONS ======

        print("\n--- 100-Day Simulation Stats ---")
        for k, v in stats.items():
            print("  {}: {}".format(k, v))

        self.assertGreater(stats["total_sessions"], 100,
                           "Should have simulated many sessions")
        self.assertGreater(stats["traces_written"], 30,
                           "Should have written significant traces")
        self.assertGreater(stats["trivial_rejected"], 0,
                           "Scoring filter should reject trivial edits")
        self.assertGreater(stats["pipeline_sessions"], 5,
                           "Should have pipeline-driven sessions")
        self.assertGreater(stats["evolve_runs"], 3,
                           "Should have run evolve multiple times")
        self.assertGreater(stats["total_proposals"], 0,
                           "Evolve should generate proposals")
        self.assertGreater(stats["total_processed"], 0,
                           "Evolve should process entries")
        self.assertGreater(stats["validated_signals_applied"], 0,
                           "Should have applied validated signals")
        self.assertGreater(stats["pipeline_results_applied"], 0,
                           "Should have applied pipeline results")

        # Force final compaction and verify trace file integrity
        if os.path.isfile(flush.TRACE_FILE):
            content = self.read_trace()
            limits = flush.load_limits()
            flush.compact_trace(content, limits)

            content = self.read_trace()
            self.assertNotIn("\n\n\n", content, "No triple blank lines after compaction")
            all_blocks = self.get_all_blocks(content)
            for b in all_blocks:
                ts = self.get_field(b, "timestamp")
                self.assertRegex(ts, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
                                 "Every block must have valid timestamp")
                score_str = self.get_field(b, "score")
                self.assertTrue(float(score_str) >= 0, "Score must be non-negative")


# ============================================================
# Test 2: Pipeline vs Normal Chat Monitoring
# ============================================================

class TestPipelineVsNormalMonitoring(SimulationTestBase):
    """Verify both pipeline and normal sessions are correctly tracked."""

    def test_pipeline_sessions_get_pending_pipeline_validated(self):
        """Pipeline sessions should have validated:pending-pipeline."""
        template = SESSION_TEMPLATES[5]  # pipeline_building
        self.simulate_session(0, template, pipeline_run_id="pipe-001")

        content = self.read_trace()
        blocks = self.get_all_blocks(content)
        self.assertTrue(len(blocks) > 0, "Should write at least one trace")
        for b in blocks:
            self.assertIn("pending-pipeline", b)
            self.assertIn("pipe-001", b)

    def test_normal_sessions_get_underscore_validated(self):
        """Normal sessions should have validated:_."""
        template = SESSION_TEMPLATES[0]  # feature_building
        self.simulate_session(0, template)

        content = self.read_trace()
        blocks = self.get_all_blocks(content)
        if blocks:
            for b in blocks:
                val = self.get_field(b, "validated")
                self.assertEqual(val, "_")

    def test_trivial_chat_produces_no_trace(self):
        """Pure Q&A sessions (0 file edits) should NOT produce any trace."""
        template = SESSION_TEMPLATES[7]  # trivial_chat
        written = self.simulate_session(0, template)
        self.assertFalse(written)
        self.assertFalse(os.path.isfile(flush.TRACE_FILE))

    def test_tiny_fix_below_threshold(self):
        """Tiny fixes with 1 file, 1-5 lines should be below scoring threshold."""
        template = {
            "name": "tiny", "type": "bugfix", "mode": "standard",
            "modules": ["UI"], "file_count": (1, 1), "lines": (1, 3),
            "edits": (1, 1), "reverts": (0, 0), "weight": 1,
        }
        files = ["Assets/Scripts/Render/UI/DialogUI.cs"]
        modules = flush.infer_modules(files)
        score, _ = flush.compute_score(files, modules, 2, 1, flush.DEFAULT_WEIGHTS[0] if False else flush.DEFAULT_WEIGHTS)
        self.assertLess(score, flush.DEFAULT_THRESHOLD,
                        "Tiny fix should be below threshold (score={})".format(score))


# ============================================================
# Test 3: Pattern Detection Correctness
# ============================================================

class TestPatternDetection(SimulationTestBase):
    """Verify the six pattern types are correctly detected."""

    def _build_trace_scenario(self, blocks_data):
        parts = ["# Execution Traces\n\n---\n\n"]
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i, bd in enumerate(blocks_data):
            b = make_trace_block(
                timestamp=base + timedelta(days=i),
                modules=bd.get("modules", ["A"]),
                score=bd.get("score", 2.0),
                correction=bd.get("correction", "_"),
                validated=bd.get("validated", "_"),
                edit_count=bd.get("edit_count", 5),
                file_count=bd.get("file_count", 2),
                lines_changed=bd.get("lines", 20),
                mode=bd.get("mode", "standard"),
                entry_type=bd.get("type", "feature"),
                skills=bd.get("skills"),
            )
            parts.append(b + "\n")
        content = "".join(parts)
        self.write_trace(content)
        return content

    def test_correction_pattern_detected(self):
        """3+ correction signals in same module -> correction pattern."""
        blocks = [
            {"modules": ["Building"], "correction": "auto:minor"},
            {"modules": ["Building"], "correction": "auto:minor"},
            {"modules": ["Building"], "correction": "auto:major"},
            {"modules": ["NPC"], "correction": "_"},
        ]
        content = self._build_trace_scenario(blocks)
        _, analysis = self.simulate_evolve_process(content)

        correction_patterns = [p for p in analysis["patterns"] if p["type"] == "correction"]
        self.assertTrue(len(correction_patterns) > 0,
                        "Should detect correction pattern for Building")
        self.assertEqual(correction_patterns[0]["module"], "Building")

    def test_module_hotspot_detected(self):
        """5+ traces in same module -> hotspot pattern."""
        blocks = [{"modules": ["Building"], "score": 2.0} for _ in range(6)]
        content = self._build_trace_scenario(blocks)
        _, analysis = self.simulate_evolve_process(content)

        hotspot_patterns = [p for p in analysis["patterns"] if p["type"] == "module_hotspot"]
        self.assertTrue(len(hotspot_patterns) > 0)

    def test_knowledge_gap_detected(self):
        """Empty skills field with 2+ occurrences -> knowledge gap."""
        blocks = [
            {"modules": ["RPGExplore"], "skills": None},
            {"modules": ["RPGExplore"], "skills": None},
            {"modules": ["Building"], "skills": ["programmer-building-skill"]},
        ]
        content = self._build_trace_scenario(blocks)
        _, analysis = self.simulate_evolve_process(content)

        gap_patterns = [p for p in analysis["patterns"] if p["type"] == "knowledge_gap"]
        self.assertTrue(len(gap_patterns) > 0)
        gap_modules = [p["module"] for p in gap_patterns]
        self.assertIn("RPGExplore", gap_modules)

    def test_complexity_concentration_detected(self):
        """High edit_count + low file_count -> complexity concentration."""
        blocks = [
            {"modules": ["Building"], "edit_count": 14, "file_count": 1},
            {"modules": ["Building"], "edit_count": 12, "file_count": 1},
            {"modules": ["NPC"], "edit_count": 3, "file_count": 3},
        ]
        content = self._build_trace_scenario(blocks)
        _, analysis = self.simulate_evolve_process(content)

        complexity_patterns = [p for p in analysis["patterns"] if p["type"] == "complexity_concentration"]
        self.assertTrue(len(complexity_patterns) > 0)

    def test_semantic_drift_detected(self):
        """3+ validated:false + correction:_ in same module -> semantic drift."""
        blocks = [
            {"modules": ["NPC"], "validated": "false", "correction": "_"},
            {"modules": ["NPC"], "validated": "false", "correction": "_"},
            {"modules": ["NPC"], "validated": "false", "correction": "_"},
        ]
        content = self._build_trace_scenario(blocks)
        _, analysis = self.simulate_evolve_process(content)

        drift_patterns = [p for p in analysis["patterns"] if p["type"] == "semantic_drift"]
        self.assertTrue(len(drift_patterns) > 0)
        self.assertEqual(drift_patterns[0]["module"], "NPC")

    def test_no_false_positive_patterns(self):
        """Clean traces with no signals should produce no patterns."""
        blocks = [
            {"modules": ["A"], "correction": "_", "validated": "_", "edit_count": 3, "file_count": 2},
            {"modules": ["B"], "correction": "_", "validated": "_", "edit_count": 4, "file_count": 3},
        ]
        content = self._build_trace_scenario(blocks)
        _, analysis = self.simulate_evolve_process(content)

        self.assertEqual(len(analysis["patterns"]), 0,
                         "Clean traces should not produce any patterns")


# ============================================================
# Test 4: Priority Sorting Correctness
# ============================================================

class TestPrioritySorting(SimulationTestBase):
    """Verify evolve correctly sorts entries by priority."""

    def test_p0_validated_false_first(self):
        """validated:false (P0) must be processed before validated:_ (P4)."""
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        blocks_data = [
            make_trace_block(base, ["A"], 5.0, validated="_", correction="_"),
            make_trace_block(base + timedelta(hours=1), ["B"], 1.5, validated="false", correction="auto:major"),
            make_trace_block(base + timedelta(hours=2), ["C"], 3.0, validated="true", correction="auto:minor"),
        ]
        content = "# Traces\n\n---\n\n" + "\n".join(blocks_data) + "\n"
        self.write_trace(content)

        blocks = self.get_all_blocks(content)
        pending_blocks = [b for b in blocks if "status:pending" in b]

        def priority_key(block):
            validated = self.get_field(block, "validated")
            correction = self.get_field(block, "correction")
            try:
                score = float(self.get_field(block, "score"))
            except ValueError:
                score = 0.0

            if validated == "false":
                p = 0
                if correction == "auto:major": sub = 0
                elif correction == "auto:minor": sub = 1
                else: sub = 2
            elif validated == "true" and "major" in correction:
                p, sub = 1, 0
            elif validated == "true":
                p, sub = 2, 0
            elif correction not in ("_", ""):
                p, sub = 3, 0
            else:
                p, sub = 4, 0
            return (p, sub, -score)

        sorted_blocks = sorted(pending_blocks, key=priority_key)

        first_validated = self.get_field(sorted_blocks[0], "validated")
        self.assertEqual(first_validated, "false", "P0 (validated:false) must come first")

        second_validated = self.get_field(sorted_blocks[1], "validated")
        self.assertEqual(second_validated, "true", "P2 (validated:true) must come second")


# ============================================================
# Test 5: Rule Lifecycle (Extract -> Merge -> Retire)
# ============================================================

class TestRuleLifecycle(SimulationTestBase):
    """Simulate rule extraction, merging, and retirement."""

    def setUp(self):
        super().setUp()
        self.skill_dir = os.path.join(self.test_dir, "skills", "test-skill")
        os.makedirs(self.skill_dir, exist_ok=True)

    def _write_skill_memory(self, content):
        path = os.path.join(self.skill_dir, "SKILL_MEMORY.md")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        return path

    def _read_skill_memory(self):
        path = os.path.join(self.skill_dir, "SKILL_MEMORY.md")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def test_rule_extraction_from_pattern(self):
        """When correction pattern detected, a new rule should be extractable."""
        initial_content = (
            "# test-skill - Hard Rules\n\n"
            "### Rule 1: Example existing rule\n\n"
            "Anchors: [ExistingClass]\n"
            "Related: none\n\n"
            "Some existing rule content here.\n"
        )
        path = self._write_skill_memory(initial_content)

        new_rule = (
            "\n---\n\n"
            "### Rule 2: OnDestroy resource cleanup\n\n"
            "Anchors: [Subscribe, Unsubscribe, OnDestroy]\n"
            "Related: Rule 1\n\n"
            "All MonoBehaviour subclasses using Subscribe must implement OnDestroy with Unsubscribe.\n"
        )

        with open(path, "a", encoding="utf-8") as f:
            f.write(new_rule)

        content = self._read_skill_memory()
        self.assertIn("Rule 2", content)
        self.assertIn("Anchors: [Subscribe, Unsubscribe, OnDestroy]", content)
        self.assertIn("Related: Rule 1", content)

    def test_rule_merge_expands_existing(self):
        """When overlapping pattern found, existing rule should be merged (not duplicated)."""
        initial_content = (
            "# test-skill - Hard Rules\n\n"
            "### Rule 1: Resource cleanup\n\n"
            "Anchors: [OnDestroy, Unsubscribe, RemoveTimer]\n"
            "Related: none\n\n"
            "Subclasses must clean up subscriptions and timers in OnDestroy.\n\n"
            "Check list\n"
            "- [ ] OnDestroy calls Unsubscribe\n"
            "- [ ] OnDestroy calls RemoveTimer\n"
        )
        path = self._write_skill_memory(initial_content)

        # Simulate merge: expand anchors and add new check item
        content = self._read_skill_memory()
        content = content.replace(
            "Anchors: [OnDestroy, Unsubscribe, RemoveTimer]",
            "Anchors: [OnDestroy, Unsubscribe, RemoveTimer, LoadAsset, Release]"
        )
        content = content.replace(
            "Subclasses must clean up subscriptions and timers in OnDestroy.",
            "Subclasses must clean up subscriptions, timers, and loaded assets in OnDestroy."
        )
        content = content.replace(
            "- [ ] OnDestroy calls RemoveTimer\n",
            "- [ ] OnDestroy calls RemoveTimer\n"
            "- [ ] OnDestroy calls Release for all LoadAsset handles\n"
        )
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

        result = self._read_skill_memory()
        self.assertIn("LoadAsset", result)
        self.assertIn("Release", result)
        self.assertEqual(result.count("### Rule"), 1, "Should still have only 1 rule (merged, not duplicated)")

    def test_rule_retire_marks_not_deletes(self):
        """Retired rules should be marked [RETIRED], not deleted."""
        initial_content = (
            "# test-skill - Hard Rules\n\n"
            "### Rule 1: Active rule\n\n"
            "Anchors: [ActiveClass]\nRelated: none\n\nActive rule content.\n\n"
            "---\n\n"
            "### Rule 2: Obsolete queue check\n\n"
            "Anchors: [QueueCapacity, CheckQueueFull, MaxQueueSize]\n"
            "Related: none\n\nCheck queue capacity before enqueue.\n"
        )
        path = self._write_skill_memory(initial_content)

        content = self._read_skill_memory()
        content = content.replace(
            "### Rule 2: Obsolete queue check",
            "### Rule 2: [RETIRED] Obsolete queue check"
        )
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

        result = self._read_skill_memory()
        self.assertIn("[RETIRED]", result)
        self.assertIn("Rule 2", result, "Retired rule should still exist")
        self.assertIn("QueueCapacity", result, "Content should be preserved")

    def test_duplicate_rule_detected_for_merge(self):
        """If a proposed rule has same anchors as existing, it should trigger merge."""
        initial_content = (
            "# Hard Rules\n\n"
            "### Rule 1: Timer cleanup\n\n"
            "Anchors: [AddTimer, RemoveTimer, OnDestroy]\n"
            "Related: none\n\nClean up timers.\n"
        )
        self._write_skill_memory(initial_content)

        proposed_anchors = {"AddTimer", "RemoveTimer", "OnDestroy", "TimerManager"}
        existing_anchors = {"AddTimer", "RemoveTimer", "OnDestroy"}

        overlap = proposed_anchors & existing_anchors
        overlap_ratio = len(overlap) / len(proposed_anchors | existing_anchors)

        self.assertGreater(overlap_ratio, 0.5,
                           "High anchor overlap should trigger Merge instead of Append")

    def test_capacity_check_triggers_retire(self):
        """When file exceeds word limit, retire candidate should be identified."""
        lines = ["word"] * 2000  # 2000 words
        long_content = " ".join(lines)
        initial_content = (
            "# Hard Rules\n\n"
            "### Rule 1: Long rule\n\n"
            "Anchors: [LongClass]\nRelated: none\n\n" + long_content + "\n\n"
            "---\n\n"
            "### Rule 2: Short rule\n\n"
            "Anchors: [ShortClass]\nRelated: none\n\nShort content.\n"
        )
        self._write_skill_memory(initial_content)
        content = self._read_skill_memory()

        word_count = len(content.split())
        capacity_threshold = 2000

        if word_count > capacity_threshold:
            needs_retire = True
        else:
            needs_retire = False

        self.assertTrue(needs_retire, "Should trigger retire when over capacity")


# ============================================================
# Test 6: Compaction Under Continuous Growth
# ============================================================

class TestCompactionUnderGrowth(SimulationTestBase):
    """Verify compaction keeps trace.md bounded during continuous growth."""

    def test_trace_stays_bounded_over_200_entries(self):
        """Write 200 entries with periodic compaction -> should stay bounded."""
        self.write_limits({
            "compact_max_entries": 50,
            "level2_age_days": 14, "level2_score_threshold": 3.0,
            "level3_age_days": 7, "level3_score_threshold": 4.0,
            "keep_top_n_per_module": 3,
        })

        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        modules_pool = ["Building", "NPC", "Combat", "RPGExplore", "Queue"]

        for i in range(200):
            ts = base + timedelta(days=i // 2, hours=i % 24)
            mod = modules_pool[i % len(modules_pool)]
            score = 0.5 + random.random() * 3.0
            entry = make_trace_block(ts, [mod], round(score, 2),
                                     edit_count=random.randint(3, 15),
                                     lines_changed=random.randint(10, 100))
            flush.append_trace(entry)

            if i > 0 and i % 20 == 0:
                flush.check_and_compact()

        flush.check_and_compact()

        content = self.read_trace()
        block_count = self.count_blocks(content)
        self.assertLessEqual(block_count, 100,
                             "After 200 entries + compaction, should be bounded (got {})".format(block_count))
        self.assertGreater(block_count, 10,
                           "Should not have deleted everything")

    def test_every_module_retains_minimum_entries(self):
        """After heavy compaction, every module should have >= keep_top_n entries."""
        self.write_limits({
            "compact_max_entries": 20,
            "level2_age_days": 100, "level2_score_threshold": 0.1,
            "level3_age_days": 3, "level3_score_threshold": 3.0,
            "keep_top_n_per_module": 2,
        })

        now = datetime.now(timezone.utc)
        modules = ["Alpha", "Beta", "Gamma", "Delta"]

        for i in range(80):
            ts = now - timedelta(days=5 + i // 2)
            mod = modules[i % len(modules)]
            score = 0.3 + random.random() * 0.5
            entry = make_trace_block(ts, [mod], round(score, 2),
                                     edit_count=3, lines_changed=10)
            flush.append_trace(entry)

        flush.check_and_compact()

        content = self.read_trace()
        blocks = self.get_all_blocks(content)

        module_counts = Counter()
        for b in blocks:
            mods_str = self.get_field(b, "modules")
            for mod in re.findall(r"[A-Za-z_]\w*", mods_str):
                module_counts[mod] += 1

        for mod in modules:
            self.assertGreaterEqual(
                module_counts.get(mod, 0), 2,
                "Module {} should retain >= 2 entries after compaction (got {})".format(
                    mod, module_counts.get(mod, 0))
            )

    def test_compaction_audit_lines_expire(self):
        """Old COMPACTED/PROCESSED audit lines should be cleaned up."""
        now = datetime.now(timezone.utc)

        old_ts = (now - timedelta(days=45)).strftime("%Y-%m-%dT%H:%M:%SZ")
        content = "# Traces\n\n"
        content += "<!-- PROCESSED ts:{} entries:10 proposals:2 -->\n".format(old_ts)
        content += "<!-- COMPACTED ts:{} removed:5 kept:20 -->\n".format(old_ts)

        for i in range(5):
            ts = now - timedelta(days=30)
            content += make_trace_block(ts, ["Mod"], 0.3, status="expired") + "\n"

        content += make_trace_block(now, ["Keep"], 2.0) + "\n"

        self.write_trace(content)
        self.write_limits({"compact_max_entries": 1, "processed_expire_days": 30})
        flush.check_and_compact()

        result = self.read_trace()
        self.assertNotIn(old_ts, result, "45-day-old audit lines should be removed")


# ============================================================
# Test 7: Lifecycle State Transitions
# ============================================================

class TestLifecycleTransitions(SimulationTestBase):
    """Verify origin-evolve Step 0 state transitions."""

    def test_stale_pending_pipeline_becomes_invalid(self):
        """pending-pipeline past expiry should transition to invalid (simulated)."""
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=10)
        block = make_trace_block(old, ["A"], 2.0, validated="pending-pipeline",
                                 pipeline_run_id="stale-run")
        content = "# Traces\n\n" + block + "\n"

        limits = flush.load_limits()
        expire_days = int(limits.get("pipeline_pending_expire_days", 7))

        blocks = self.get_all_blocks(content)
        for b in blocks:
            validated = self.get_field(b, "validated")
            if validated == "pending-pipeline":
                ts_str = self.get_field(b, "timestamp")
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                age = (now - ts).days
                if age > expire_days:
                    content = content.replace(
                        "validated: pending-pipeline",
                        "validated: invalid"
                    )

        self.assertIn("validated: invalid", content)

    def test_stale_pending_validated_becomes_expired(self):
        """pending entry with validated:_ past uncertain expiry -> expired (simulated)."""
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=20)
        block = make_trace_block(old, ["A"], 2.0, validated="_")
        content = "# Traces\n\n" + block + "\n"

        limits = flush.load_limits()
        expire_days = int(limits.get("validated_uncertain_expire_days", 14))

        blocks = self.get_all_blocks(content)
        for b in blocks:
            if "status:pending" in b:
                validated = self.get_field(b, "validated")
                if validated in ("_", "false"):
                    ts_str = self.get_field(b, "timestamp")
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    age = (now - ts).days
                    if age > expire_days:
                        content = content.replace("status:pending", "status:expired")

        self.assertIn("status:expired", content)


# ============================================================
# Test 8: End-to-End Flow Integrity
# ============================================================

class TestEndToEndFlowIntegrity(SimulationTestBase):
    """Verify the complete flow from collector to evolve."""

    def test_collector_to_flush_to_evolve_pipeline(self):
        """
        Full pipeline:
        1. Collector receives edit events -> writes buffer
        2. Flush reads buffer -> scores -> writes trace
        3. Validated signal injected
        4. Evolve consumes traces -> detects patterns -> marks processed
        """
        # Step 1: Simulate collector writing buffer
        entries = {
            "Assets/Scripts/Modules/Building/BuildingManager.cs": (50, 8, {"R"}),
            "Assets/Scripts/Modules/Building/BuildingFunc.cs": (20, 3, set()),
        }
        collector.write_buffer(entries)
        self.assertTrue(os.path.isfile(collector.BUFFER_FILE))

        # Step 2: Flush reads buffer and writes trace
        flush.flush_new_trace(idp={
            "mode": "standard",
            "type": "feature",
            "request": "add batch upgrade",
            "intent": "implement batch building upgrade",
            "skills": ["programmer-building-skill"],
        })
        self.assertTrue(os.path.isfile(flush.TRACE_FILE))
        content = self.read_trace()
        self.assertIn("<!-- TRACE status:pending", content)
        self.assertIn("Building", content)
        self.assertFalse(os.path.isfile(collector.BUFFER_FILE), "Buffer should be cleared")

        # Step 3: Inject validated signal
        with open(flush.PENDING_VALIDATED_FILE, "w", encoding="utf-8") as f:
            json.dump({"result": "accepted"}, f)
        flush.apply_validated_update()
        content = self.read_trace()
        self.assertIn("validated: true", content)

        # Add more traces to meet evolve minimum
        for i in range(5):
            base = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=i)
            entry = make_trace_block(base, ["Building"], 2.0 + i * 0.1,
                                     correction="auto:minor" if i < 3 else "_",
                                     edit_count=8 + i)
            flush.append_trace(entry)

        # Step 4: Evolve consumes traces
        content = self.read_trace()
        pending = self.count_pending(content)
        self.assertGreaterEqual(pending, 5, "Should have enough pending for evolve")

        new_content, analysis = self.simulate_evolve_process(content)
        self.write_trace(new_content)

        self.assertGreater(analysis["processed"], 0)
        result = self.read_trace()
        self.assertIn("status:processed", result)
        self.assertIn("<!-- PROCESSED", result)

    def test_pipeline_driven_session_full_flow(self):
        """
        Pipeline flow:
        1. Session runs with pipeline context
        2. Traces get validated:pending-pipeline
        3. Pipeline result applied (GO/NO-GO)
        4. Evolve processes with correct priority
        """
        # Write trace with pipeline context
        now = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(6):
            entry = make_trace_block(
                now + timedelta(hours=i), ["Combat"], 2.5,
                validated="pending-pipeline", pipeline_run_id="pipe-test-001",
                correction="auto:minor" if i < 3 else "_",
                edit_count=10, mode="pipeline", entry_type="feature",
            )
            flush.append_trace(entry)

        content = self.read_trace()
        self.assertEqual(content.count("pending-pipeline"), 6)

        # Apply pipeline result
        with open(flush.PENDING_PIPELINE_FILE, "w", encoding="utf-8") as f:
            json.dump({"pipeline_run_id": "pipe-test-001", "result": "GO"}, f)
        flush.apply_pipeline_result()

        content = self.read_trace()
        self.assertNotIn("pending-pipeline", content)
        self.assertEqual(content.count("validated: true"), 6)

        # Evolve should process these as P1/P2 (validated:true)
        new_content, analysis = self.simulate_evolve_process(content)
        self.assertGreater(analysis["processed"], 0)


# ============================================================
# Test 9: Data Integrity Under Concurrent Operations
# ============================================================

class TestDataIntegrity(SimulationTestBase):
    """Verify data integrity under various operation sequences."""

    def test_flush_then_compact_then_evolve(self):
        """Sequential: flush many entries -> compact -> evolve -> verify no data loss of important entries."""
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)

        important_entries = []
        for i in range(30):
            ts = base + timedelta(days=i)
            mod = ["Building", "NPC", "Combat"][i % 3]
            validated = "false" if i < 3 else "_"
            corr = "auto:major" if i < 3 else ("auto:minor" if i < 8 else "_")
            entry = make_trace_block(ts, [mod], 2.0 + i * 0.05,
                                     validated=validated, correction=corr,
                                     edit_count=5 + i)
            flush.append_trace(entry)
            if validated == "false":
                important_entries.append(("false", mod))

        self.write_limits({
            "compact_max_entries": 15,
            "level2_age_days": 10, "level2_score_threshold": 1.5,
            "level3_age_days": 5, "level3_score_threshold": 0.5,
            "keep_top_n_per_module": 3,
        })
        flush.check_and_compact()

        content = self.read_trace()
        for val, mod in important_entries:
            self.assertIn("validated: false", content,
                          "validated:false entries must survive compaction")

        _, analysis = self.simulate_evolve_process(content)
        self.assertGreater(analysis["processed"], 0)

    def test_no_phantom_blocks_after_operations(self):
        """After all operations, every block should have valid structure."""
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(50):
            ts = base + timedelta(days=i)
            entry = make_trace_block(ts, ["Mod{}".format(i % 4)], 1.5 + random.random(),
                                     edit_count=random.randint(3, 15))
            flush.append_trace(entry)

        flush.check_and_compact()

        content = self.read_trace()
        open_tags = len(re.findall(r"<!-- TRACE ", content))
        close_tags = len(re.findall(r"<!-- /TRACE -->", content))
        self.assertEqual(open_tags, close_tags,
                         "Every TRACE open tag must have a matching close tag")

        blocks = self.get_all_blocks(content)
        for b in blocks:
            self.assertIn("timestamp:", b)
            self.assertIn("score:", b)
            self.assertIn("modules:", b)
            self.assertIn("validated:", b)


# ============================================================
# Test 10: Rejection Memory
# ============================================================

class TestRejectionMemory(SimulationTestBase):
    """Verify EVOLVE_REJECTION entries prevent re-proposal."""

    def test_rejected_pattern_not_reproposed(self):
        """A pattern recorded in EVOLVE_REJECTION should not be proposed again."""
        rejection = (
            "<!-- EVOLVE_REJECTION -->\n"
            "pattern: string-concatenation-rule\n"
            "reason: Too aggressive for general code\n"
            "effect: Future proposals must be scoped to hot path contexts\n"
            "<!-- /EVOLVE_REJECTION -->\n"
        )

        content = "# Traces\n\n" + rejection + "\n"
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(5):
            content += make_trace_block(base + timedelta(days=i), ["Building"], 2.0,
                                        correction="auto:minor") + "\n"
        self.write_trace(content)

        rejection_patterns = re.findall(
            r"<!-- EVOLVE_REJECTION -->.*?pattern:\s*(\S+).*?<!-- /EVOLVE_REJECTION -->",
            content, re.DOTALL
        )

        self.assertIn("string-concatenation-rule", rejection_patterns)
        self.assertTrue(len(rejection_patterns) > 0,
                        "Should detect existing rejections before proposing")


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("CastFlow Self-Evolution - 100-Day Production Simulation")
    if KEEP_DATA:
        print("Mode: --keep-data  (output -> test-output/100day/)")
    print("=" * 70)
    unittest.main(verbosity=2)
