#!/usr/bin/env python3
"""
CastFlow Self-Evolution - 365-Day Production Simulation.

Simulates a full year of real development with realistic team rhythms:
  - Weekday / weekend activity variance
  - Seasonal module focus shifts (quarterly)
  - Mixed session types: normal chat, code_pipeline, pure Q&A
  - Scoring filter rejects trivial edits
  - Validated signals (user accept/reject) at realistic rates
  - Pipeline result signals (GO/NO-GO)
  - Periodic origin-evolve runs (every ~10 days when enough material)
  - Compaction under continuous growth (trace.md stays bounded)
  - Knowledge base lifecycle: rule extract, merge, retire
  - Rejection memory prevents re-proposal
  - Step 0 lifecycle transitions (pending-pipeline expiry, stale expiry)

Run:
    py test_365day_simulation.py               # run and discard test data
    py test_365day_simulation.py --keep-data   # preserve output in test-output/365day/
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
from collections import Counter, defaultdict

import importlib.util

_script_dir = os.path.dirname(os.path.abspath(__file__))
_HOOKS_DIR = os.path.normpath(os.path.join(
    _script_dir, "..", "..", ".castflow", "core", "hooks"
))

# --keep-data: preserve each test case's trace files for inspection
KEEP_DATA = "--keep-data" in sys.argv
if KEEP_DATA:
    sys.argv.remove("--keep-data")

_OUTPUT_BASE = os.path.join(_script_dir, "test-output", "365day")

if KEEP_DATA:
    if os.path.isdir(_OUTPUT_BASE):
        shutil.rmtree(_OUTPUT_BASE)
    os.makedirs(_OUTPUT_BASE, exist_ok=True)
    print("[keep-data] Output directory: {}".format(_OUTPUT_BASE))


def _import_hyphen_module(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(_HOOKS_DIR, filename)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


collector = _import_hyphen_module("collector", "trace-collector.py")
flush = _import_hyphen_module("flush", "trace-flush.py")

random.seed(2026)

# ============================================================
# Simulation constants
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
    "Analytics": [
        "src/analytics/EventTracker.py",
        "src/analytics/MetricsService.py",
        "src/analytics/IAnalyticsService.py",
    ],
    "Notification": [
        "src/notification/NotificationService.ts",
        "src/notification/INotificationService.ts",
        "src/notification/EmailSender.ts",
    ],
}

# Quarterly focus: which modules are hot in each quarter
QUARTERLY_FOCUS = {
    0: {"Auth": 3.0, "Database": 2.5, "Config": 2.0},               # Q1: infrastructure
    1: {"API": 3.0, "Worker": 2.5, "Analytics": 2.0},               # Q2: features
    2: {"UI": 3.0, "Cache": 2.5, "API": 2.0},                       # Q3: frontend/perf
    3: {"Auth": 2.0, "Notification": 2.5, "Database": 1.5, "Config": 2.0},  # Q4: hardening
}

SESSION_TEMPLATES = [
    {"name": "feature", "type": "feature", "mode": "standard",
     "file_count": (2, 4), "lines": (30, 150), "edits": (5, 18), "reverts": (0, 2)},
    {"name": "bugfix", "type": "bugfix", "mode": "standard",
     "file_count": (1, 3), "lines": (8, 50), "edits": (3, 10), "reverts": (0, 3)},
    {"name": "refactor", "type": "refactor", "mode": "standard",
     "file_count": (3, 6), "lines": (40, 200), "edits": (8, 25), "reverts": (1, 4)},
    {"name": "pipeline_feature", "type": "feature", "mode": "pipeline",
     "file_count": (3, 6), "lines": (60, 250), "edits": (10, 30), "reverts": (0, 4)},
    {"name": "pipeline_refactor", "type": "refactor", "mode": "pipeline",
     "file_count": (4, 8), "lines": (80, 300), "edits": (12, 35), "reverts": (1, 5)},
    {"name": "tiny_fix", "type": "bugfix", "mode": "standard",
     "file_count": (1, 1), "lines": (1, 5), "edits": (1, 2), "reverts": (0, 0)},
    {"name": "trivial_chat", "type": "question", "mode": "standard",
     "file_count": (0, 0), "lines": (0, 0), "edits": (0, 0), "reverts": (0, 0)},
]

# Probability of each session type (sums to 1.0)
SESSION_WEIGHTS = {
    "feature": 0.18,
    "bugfix": 0.16,
    "refactor": 0.06,
    "pipeline_feature": 0.10,
    "pipeline_refactor": 0.05,
    "tiny_fix": 0.20,
    "trivial_chat": 0.25,
}


def pick_session_template():
    r = random.random()
    cumul = 0.0
    for t in SESSION_TEMPLATES:
        cumul += SESSION_WEIGHTS.get(t["name"], 0)
        if r <= cumul:
            return t
    return SESSION_TEMPLATES[-1]


def pick_modules_for_quarter(quarter):
    focus = QUARTERLY_FOCUS.get(quarter, {})
    all_mods = list(MODULE_FILE_MAP.keys())
    weights = []
    for m in all_mods:
        weights.append(focus.get(m, 1.0))
    total = sum(weights)
    probs = [w / total for w in weights]
    count = random.choices([1, 2, 3], weights=[0.55, 0.35, 0.10])[0]
    chosen = []
    for _ in range(count):
        r = random.random()
        cumul = 0.0
        for i, p in enumerate(probs):
            cumul += p
            if r <= cumul:
                if all_mods[i] not in chosen:
                    chosen.append(all_mods[i])
                break
    return chosen if chosen else [random.choice(all_mods)]


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


# ============================================================
# Simulated Knowledge Base
# ============================================================

class SimulatedKnowledgeBase:
    """In-memory model of the Skill knowledge base for lifecycle testing."""

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.rules = {}        # key -> {anchors, content, retired, rule_id, file}
        self.rejections = []   # list of pattern names
        self.next_id = 1
        self.merge_count = 0
        self.retire_count = 0
        self.extract_count = 0

    def _skill_dir(self, skill_name):
        d = os.path.join(self.base_dir, "skills", skill_name)
        os.makedirs(d, exist_ok=True)
        return d

    def extract_rule(self, skill_name, anchors, content):
        key = frozenset(anchors)
        existing = self._find_overlapping(key)
        if existing:
            self._merge_rule(existing, anchors, content)
            return "merge"
        rule_id = self.next_id
        self.next_id += 1
        self.rules[key] = {
            "anchors": set(anchors), "content": content,
            "retired": False, "rule_id": rule_id,
            "skill": skill_name, "file": "SKILL_MEMORY.md",
        }
        self.extract_count += 1
        self._write_skill_file(skill_name)
        return "append"

    def _find_overlapping(self, key):
        for existing_key, rule in self.rules.items():
            if rule["retired"]:
                continue
            overlap = key & existing_key
            union = key | existing_key
            if len(overlap) / len(union) >= 0.5:
                return existing_key
        return None

    def _merge_rule(self, existing_key, new_anchors, new_content):
        rule = self.rules[existing_key]
        combined_anchors = rule["anchors"] | set(new_anchors)
        combined_key = frozenset(combined_anchors)
        rule["anchors"] = combined_anchors
        rule["content"] = rule["content"] + " " + new_content
        if combined_key != existing_key:
            self.rules[combined_key] = rule
            del self.rules[existing_key]
        self.merge_count += 1
        self._write_skill_file(rule["skill"])

    def retire_rule(self, key):
        if key in self.rules and not self.rules[key]["retired"]:
            self.rules[key]["retired"] = True
            self.retire_count += 1
            self._write_skill_file(self.rules[key]["skill"])
            return True
        return False

    def check_capacity(self, skill_name, threshold=2000):
        total_words = 0
        for rule in self.rules.values():
            if rule["skill"] == skill_name and not rule["retired"]:
                total_words += len(rule["content"].split())
        return total_words > threshold

    def add_rejection(self, pattern_name):
        self.rejections.append(pattern_name)

    def is_rejected(self, pattern_name):
        return pattern_name in self.rejections

    def active_rule_count(self):
        return sum(1 for r in self.rules.values() if not r["retired"])

    def _write_skill_file(self, skill_name):
        d = self._skill_dir(skill_name)
        path = os.path.join(d, "SKILL_MEMORY.md")
        lines = ["# {} - Hard Rules\n\n".format(skill_name)]
        for rule in sorted(self.rules.values(), key=lambda r: r["rule_id"]):
            if rule["skill"] != skill_name:
                continue
            prefix = "[RETIRED] " if rule["retired"] else ""
            lines.append("### Rule {}: {}{}\n\n".format(
                rule["rule_id"], prefix, "auto-extracted rule"
            ))
            lines.append("Anchors: [{}]\n".format(", ".join(sorted(rule["anchors"]))))
            lines.append("Related: none\n\n")
            lines.append(rule["content"] + "\n\n---\n\n")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(lines))


# ============================================================
# Test base
# ============================================================

class SimulationTestBase(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="castflow_365_")
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

    # ---- Simulation helpers ----

    def simulate_session(self, day, template, modules, pipeline_run_id=None):
        base_time = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=day)
        fc_lo, fc_hi = template["file_count"]
        file_count = random.randint(fc_lo, fc_hi) if fc_hi > 0 else 0
        if file_count == 0:
            return False, {}

        files = pick_files_for_modules(modules, file_count)
        if not files:
            return False, {}

        lines = random.randint(*template["lines"])
        edits = random.randint(*template["edits"])
        reverts = random.randint(*template["reverts"])

        weights, threshold = flush.load_weights()
        inferred_modules = flush.infer_modules(files)
        score, _ = flush.compute_score(files, inferred_modules, lines, edits, weights)
        if score < threshold:
            return False, {"reason": "below_threshold", "score": score}

        correction = flush.infer_correction(reverts)
        entry = make_trace_block(
            timestamp=base_time + timedelta(hours=random.randint(8, 20)),
            modules=inferred_modules, score=score, correction=correction,
            mode=template["mode"], entry_type=template["type"],
            request="sim:{} day{}".format(template["name"], day),
            intent="simulated {}".format(template["type"]),
            edit_count=edits, file_count=file_count, lines_changed=lines,
            files=files,
            pipeline_run_id=pipeline_run_id or "_",
            validated="pending-pipeline" if pipeline_run_id else "_",
        )
        flush.append_trace(entry)
        return True, {
            "modules": inferred_modules, "score": score,
            "correction": correction, "mode": template["mode"],
        }

    def simulate_evolve(self, content):
        """Simplified evolve: sort, detect patterns, mark processed.
        Returns (new_content, patterns_list, processed_count).
        """
        blocks = self.get_all_blocks(content)
        pending = [b for b in blocks if "status:pending" in b]
        if not pending:
            return content, [], 0

        module_counter = Counter()
        correction_by_mod = defaultdict(list)
        val_false_by_mod = Counter()
        high_edit_blocks = []

        for b in pending:
            mods = re.findall(r"[A-Za-z_]\w*", self.get_field(b, "modules"))
            corr = self.get_field(b, "correction")
            val = self.get_field(b, "validated")
            try:
                ec = int(self.get_field(b, "edit_count"))
            except ValueError:
                ec = 0
            try:
                fc = int(self.get_field(b, "file_count"))
            except ValueError:
                fc = 0
            for m in mods:
                module_counter[m] += 1
                if corr not in ("_", ""):
                    correction_by_mod[m].append(corr)
                if val == "false":
                    val_false_by_mod[m] += 1
            if ec >= 8 and fc <= 2:
                high_edit_blocks.append(mods)

        patterns = []
        for m, cs in correction_by_mod.items():
            if len(cs) >= 3:
                patterns.append({"type": "correction", "module": m, "count": len(cs)})
        for m, c in module_counter.items():
            if c >= 5:
                patterns.append({"type": "hotspot", "module": m, "count": c})
        for m, c in val_false_by_mod.items():
            if c >= 3:
                patterns.append({"type": "semantic_drift", "module": m, "count": c})
        seen = set()
        for mods in high_edit_blocks:
            key = tuple(sorted(mods))
            if key not in seen and len(high_edit_blocks) >= 2:
                seen.add(key)
                patterns.append({"type": "complexity", "modules": list(key)})

        new_content = content
        for b in pending:
            new_content = new_content.replace(b, b.replace("status:pending", "status:processed"))

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        new_content += "\n<!-- PROCESSED ts:{} entries:{} proposals:{} -->\n".format(
            ts, len(pending), len(patterns)
        )
        return new_content, patterns, len(pending)

    def apply_lifecycle_transitions(self, content, sim_now):
        """Simulate Step 0: pending-pipeline expiry and stale pending expiry."""
        limits = flush.load_limits()
        pipe_expire = int(limits.get("pipeline_pending_expire_days", 7))
        unc_expire = int(limits.get("validated_uncertain_expire_days", 14))

        blocks = self.get_all_blocks(content)
        for b in blocks:
            if "status:pending" not in b:
                continue
            validated = self.get_field(b, "validated")
            ts_str = self.get_field(b, "timestamp")
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except ValueError:
                continue
            age = (sim_now - ts).days

            if validated == "pending-pipeline" and age > pipe_expire:
                content = content.replace(b, b.replace(
                    "validated: pending-pipeline", "validated: invalid"
                ).replace("status:pending", "status:invalid"))
            elif validated in ("_",) and age > unc_expire:
                content = content.replace(b, b.replace("status:pending", "status:expired"))

        return content


# ============================================================
# TEST 1: Full 365-Day Lifecycle Simulation
# ============================================================

class Test365DayLifecycle(SimulationTestBase):

    def test_full_year_simulation(self):
        """Run 365 days of simulated sessions and verify the full lifecycle."""

        self.write_limits({
            "compact_max_entries": 60,
            "compact_max_size_kb": 150,
            "level2_age_days": 14, "level2_score_threshold": 2.5,
            "level3_age_days": 7, "level3_score_threshold": 3.5,
            "keep_top_n_per_module": 3,
            "passive_trigger_threshold": 10,
            "passive_trigger_min_new": 5,
            "processed_expire_days": 30,
            "pipeline_pending_expire_days": 5,
            "validated_uncertain_expire_days": 8,
        })
        kb = SimulatedKnowledgeBase(self.test_dir)

        stats = {
            "total_sessions": 0, "traces_written": 0,
            "trivial_chats": 0, "below_threshold": 0,
            "pipeline_sessions": 0, "normal_sessions": 0,
            "evolve_runs": 0, "total_proposals": 0,
            "total_processed": 0, "compaction_runs": 0,
            "validated_accept": 0, "validated_reject": 0,
            "pipeline_go": 0, "pipeline_nogo": 0,
            "lifecycle_transitions": 0,
            "rules_extracted": 0, "rules_merged": 0, "rules_retired": 0,
        }

        pending_pipeline_ids = []
        quarterly_modules_touched = [Counter() for _ in range(4)]

        for day in range(365):
            quarter = day // 91
            is_weekend = (day % 7) >= 5
            sessions_today = random.randint(0, 2) if is_weekend else random.randint(1, 6)

            for _ in range(sessions_today):
                template = pick_session_template()
                stats["total_sessions"] += 1

                if template["name"] == "trivial_chat":
                    stats["trivial_chats"] += 1
                    continue

                modules = pick_modules_for_quarter(quarter)
                pipeline_id = None
                if template["mode"] == "pipeline":
                    pipeline_id = "pipe-d{}-{}".format(day, random.randint(100, 999))
                    stats["pipeline_sessions"] += 1
                    pending_pipeline_ids.append((pipeline_id, day))
                else:
                    stats["normal_sessions"] += 1

                written, info = self.simulate_session(day, template, modules, pipeline_id)
                if written:
                    stats["traces_written"] += 1
                    for m in info.get("modules", []):
                        quarterly_modules_touched[min(quarter, 3)][m] += 1
                else:
                    stats["below_threshold"] += 1

            # Validated signals: 40% chance on weekdays
            if not is_weekend and random.random() < 0.4 and os.path.isfile(flush.TRACE_FILE):
                content = self.read_trace()
                eligible = [b for b in self.get_all_blocks(content)
                            if self.get_field(b, "validated") == "_" and "status:pending" in b]
                if eligible:
                    accepted = random.random() < 0.72
                    with open(flush.PENDING_VALIDATED_FILE, "w", encoding="utf-8") as f:
                        json.dump({"result": "accepted" if accepted else "rejected"}, f)
                    flush.apply_validated_update()
                    if accepted:
                        stats["validated_accept"] += 1
                    else:
                        stats["validated_reject"] += 1

            # Pipeline results: 60% chance per day when pending
            if random.random() < 0.6 and pending_pipeline_ids and os.path.isfile(flush.TRACE_FILE):
                pid, pday = pending_pipeline_ids.pop(0)
                go = random.random() < 0.65
                with open(flush.PENDING_PIPELINE_FILE, "w", encoding="utf-8") as f:
                    json.dump({"pipeline_run_id": pid, "result": "GO" if go else "NO-GO"}, f)
                flush.apply_pipeline_result()
                if go:
                    stats["pipeline_go"] += 1
                else:
                    stats["pipeline_nogo"] += 1

            # Lifecycle transitions every 7 days
            if day % 7 == 6 and os.path.isfile(flush.TRACE_FILE):
                sim_now = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=day + 1)
                content = self.read_trace()
                before_pending = len(re.findall(r"status:pending", content))
                content = self.apply_lifecycle_transitions(content, sim_now)
                after_pending = len(re.findall(r"status:pending", content))
                transitions = before_pending - after_pending
                if transitions > 0:
                    stats["lifecycle_transitions"] += transitions
                    self.write_trace(content)

            # Evolve every ~10 days
            if day > 0 and day % 10 == 0 and os.path.isfile(flush.TRACE_FILE):
                content = self.read_trace()
                pending_count = self.count_pending(content)
                if pending_count >= 5:
                    new_content, patterns, processed = self.simulate_evolve(content)
                    self.write_trace(new_content)
                    stats["evolve_runs"] += 1
                    stats["total_proposals"] += len(patterns)
                    stats["total_processed"] += processed

                    for p in patterns:
                        mod = p.get("module", "Unknown")
                        ptype = p["type"]
                        pattern_key = "{}-{}".format(ptype, mod)

                        if kb.is_rejected(pattern_key):
                            continue

                        if random.random() < 0.15:
                            kb.add_rejection(pattern_key)
                            continue

                        skill_name = "programmer-{}-skill".format(mod.lower())
                        anchors = ["Auto{}".format(mod), "{}Manager".format(mod), "OnDestroy"]
                        rule_text = (
                            "Auto-rule from {ptype} pattern in {mod} with {cnt} occurrences. "
                            "When working with {mod} module ensure all resource references "
                            "are properly cleaned up in OnDestroy. This includes subscriptions "
                            "timers asset handles and coroutines. "
                        ).format(ptype=ptype, mod=mod, cnt=p.get("count", "?"))
                        result = kb.extract_rule(skill_name, anchors, rule_text)
                        if result == "merge":
                            stats["rules_merged"] += 1
                        else:
                            stats["rules_extracted"] += 1

                        if kb.check_capacity(skill_name, threshold=100):
                            for key, rule in list(kb.rules.items()):
                                if rule["skill"] == skill_name and not rule["retired"]:
                                    kb.retire_rule(key)
                                    stats["rules_retired"] += 1
                                    break

            # Compaction
            if os.path.isfile(flush.TRACE_FILE):
                flush.check_and_compact()
                flush.check_notify()

        # ====== ASSERTIONS ======

        print("\n" + "=" * 70)
        print("365-Day Simulation Stats")
        print("=" * 70)
        for k, v in stats.items():
            print("  {:30s}: {}".format(k, v))
        print("\n  Knowledge Base:")
        print("    Active rules: {}".format(kb.active_rule_count()))
        print("    Total extracts: {}".format(kb.extract_count))
        print("    Total merges: {}".format(kb.merge_count))
        print("    Total retires: {}".format(kb.retire_count))
        print("    Rejections: {}".format(len(kb.rejections)))
        print("\n  Quarterly module distribution:")
        for q in range(4):
            top3 = quarterly_modules_touched[q].most_common(3)
            print("    Q{}: {}".format(q + 1, top3))

        # --- Core flow assertions ---
        self.assertGreater(stats["total_sessions"], 600,
                           "Full year should have many sessions")
        self.assertGreater(stats["traces_written"], 100,
                           "Should write a meaningful number of traces")
        self.assertGreater(stats["trivial_chats"], 50,
                           "Pure Q&A sessions should be common")
        self.assertGreater(stats["below_threshold"], 20,
                           "Scoring filter should reject trivial edits")

        # --- Pipeline vs normal monitoring ---
        self.assertGreater(stats["pipeline_sessions"], 30,
                           "Should have sufficient pipeline sessions")
        self.assertGreater(stats["normal_sessions"], 200,
                           "Should have many normal sessions")

        # --- Evolve correctness ---
        self.assertGreater(stats["evolve_runs"], 15,
                           "Should run evolve frequently over a year")
        self.assertGreater(stats["total_proposals"], 20,
                           "Should generate many proposals over a year")
        self.assertGreater(stats["total_processed"], 50,
                           "Should process many entries over a year")

        # --- Validated and pipeline signals ---
        self.assertGreater(stats["validated_accept"], 10,
                           "Should have accepted signals")
        self.assertGreater(stats["validated_reject"], 3,
                           "Should have rejected signals")
        self.assertGreater(stats["pipeline_go"], 10,
                           "Should have GO results")
        self.assertGreater(stats["pipeline_nogo"], 3,
                           "Should have NO-GO results")

        # --- Lifecycle transitions ---
        self.assertGreater(stats["lifecycle_transitions"], 0,
                           "Should have lifecycle state transitions")

        # --- Knowledge base lifecycle ---
        self.assertGreater(stats["rules_extracted"], 5,
                           "Should extract rules from patterns")
        self.assertGreater(stats["rules_merged"], 0,
                           "Duplicate rules should be merged")
        self.assertGreater(stats["rules_retired"], 0,
                           "Over-capacity should trigger retires")
        self.assertGreater(len(kb.rejections), 0,
                           "Some patterns should be rejected")

        # --- Trace file integrity ---
        if os.path.isfile(flush.TRACE_FILE):
            content = self.read_trace()

            # Inject an expired block so compact_trace always writes and cleans up
            expired_block = make_trace_block(
                datetime(2025, 1, 1, tzinfo=timezone.utc), ["_Cleanup_"], 0.1, status="expired",
            )
            content += "\n" + expired_block + "\n"
            self.write_trace(content)

            limits = flush.load_limits()
            flush.compact_trace(content, limits)
            content = self.read_trace()

            self.assertNotIn("\n\n\n", content,
                             "No triple blank lines after final compaction")

            blocks = self.get_all_blocks(content)
            open_tags = len(re.findall(r"<!-- TRACE ", content))
            close_tags = len(re.findall(r"<!-- /TRACE -->", content))
            self.assertEqual(open_tags, close_tags,
                             "Mismatched TRACE tags")

            for b in blocks:
                ts = self.get_field(b, "timestamp")
                self.assertRegex(ts, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
                score_val = float(self.get_field(b, "score"))
                self.assertGreaterEqual(score_val, 0)


# ============================================================
# TEST 2: Pipeline vs Normal always correctly monitored
# ============================================================

class Test365PipelineNormalSeparation(SimulationTestBase):

    def test_pipeline_always_gets_pending_pipeline(self):
        """Every pipeline session must write validated:pending-pipeline."""
        written_count = 0
        for day in range(30):
            tpl = SESSION_TEMPLATES[3]  # pipeline_feature
            modules = pick_modules_for_quarter(0)
            pid = "verify-pipe-{}".format(day)
            ok, _ = self.simulate_session(day, tpl, modules, pipeline_run_id=pid)
            if ok:
                written_count += 1

        self.assertGreater(written_count, 0)
        content = self.read_trace()
        blocks = self.get_all_blocks(content)
        for b in blocks:
            self.assertEqual(self.get_field(b, "validated"), "pending-pipeline")
            self.assertIn("verify-pipe-", b)

    def test_normal_never_gets_pending_pipeline(self):
        """Normal sessions must never have pending-pipeline."""
        for day in range(30):
            tpl = SESSION_TEMPLATES[0]  # feature
            modules = pick_modules_for_quarter(0)
            self.simulate_session(day, tpl, modules)

        content = self.read_trace()
        self.assertNotIn("pending-pipeline", content)

    def test_trivial_chat_never_writes_trace(self):
        """Pure Q&A sessions must never produce a trace."""
        for _ in range(100):
            tpl = SESSION_TEMPLATES[6]  # trivial_chat
            ok, _ = self.simulate_session(0, tpl, [])
            self.assertFalse(ok)
        self.assertFalse(os.path.isfile(flush.TRACE_FILE))


# ============================================================
# TEST 3: Rule extraction when enough material
# ============================================================

class Test365RuleExtraction(SimulationTestBase):

    def test_correction_pattern_triggers_extraction(self):
        """3+ correction traces in same module -> pattern -> rule extraction."""
        kb = SimulatedKnowledgeBase(self.test_dir)
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)

        blocks = []
        for i in range(5):
            blocks.append(make_trace_block(
                base + timedelta(days=i), ["Building"], 2.5,
                correction="auto:minor", edit_count=8,
            ))
        content = "# Traces\n\n---\n\n" + "\n".join(blocks) + "\n"
        self.write_trace(content)

        _, patterns, _ = self.simulate_evolve(content)
        corr_patterns = [p for p in patterns if p["type"] == "correction"]
        self.assertGreater(len(corr_patterns), 0)

        for p in corr_patterns:
            kb.extract_rule(
                "programmer-building-skill",
                ["BuildingManager", "OnDestroy", "Unsubscribe"],
                "Auto: correction pattern with {} occurrences.".format(p["count"]),
            )
        self.assertGreater(kb.active_rule_count(), 0)

    def test_insufficient_material_no_extraction(self):
        """< 3 correction traces should NOT trigger correction pattern."""
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        blocks = [
            make_trace_block(base, ["Building"], 2.0, correction="auto:minor"),
            make_trace_block(base + timedelta(days=1), ["Building"], 2.0, correction="auto:minor"),
        ]
        content = "# Traces\n\n" + "\n".join(blocks) + "\n"
        self.write_trace(content)

        _, patterns, _ = self.simulate_evolve(content)
        corr = [p for p in patterns if p["type"] == "correction"]
        self.assertEqual(len(corr), 0, "2 corrections should not trigger pattern")

    def test_hotspot_triggers_extraction(self):
        """5+ traces in same module -> hotspot pattern."""
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        blocks = [make_trace_block(base + timedelta(days=i), ["NPC"], 2.0)
                  for i in range(7)]
        content = "# Traces\n\n" + "\n".join(blocks) + "\n"
        self.write_trace(content)

        _, patterns, _ = self.simulate_evolve(content)
        hotspots = [p for p in patterns if p["type"] == "hotspot"]
        self.assertGreater(len(hotspots), 0)


# ============================================================
# TEST 4: Duplicate rule merging
# ============================================================

class Test365RuleMerging(SimulationTestBase):

    def test_overlapping_anchors_merge(self):
        """Two rules with >50% anchor overlap should be merged."""
        kb = SimulatedKnowledgeBase(self.test_dir)

        result1 = kb.extract_rule(
            "test-skill",
            ["OnDestroy", "Unsubscribe", "RemoveTimer"],
            "Clean up subscriptions and timers.",
        )
        self.assertEqual(result1, "append")
        self.assertEqual(kb.active_rule_count(), 1)

        result2 = kb.extract_rule(
            "test-skill",
            ["OnDestroy", "Unsubscribe", "Release"],
            "Clean up subscriptions and asset handles.",
        )
        self.assertEqual(result2, "merge")
        self.assertEqual(kb.active_rule_count(), 1, "Should merge, not create second rule")
        self.assertEqual(kb.merge_count, 1)

        merged_anchors = None
        for rule in kb.rules.values():
            merged_anchors = rule["anchors"]
        self.assertIn("RemoveTimer", merged_anchors)
        self.assertIn("Release", merged_anchors)
        self.assertIn("OnDestroy", merged_anchors)

    def test_disjoint_anchors_no_merge(self):
        """Two rules with <50% anchor overlap should remain separate."""
        kb = SimulatedKnowledgeBase(self.test_dir)

        kb.extract_rule("test-skill", ["ClassA", "MethodA"], "Rule about A.")
        kb.extract_rule("test-skill", ["ClassB", "MethodB"], "Rule about B.")

        self.assertEqual(kb.active_rule_count(), 2)
        self.assertEqual(kb.merge_count, 0)

    def test_repeated_merges_accumulate(self):
        """Multiple merges into the same rule should keep expanding it."""
        kb = SimulatedKnowledgeBase(self.test_dir)

        kb.extract_rule("s", ["A", "B", "C"], "Base rule.")
        kb.extract_rule("s", ["A", "B", "D"], "Extension 1.")
        kb.extract_rule("s", ["A", "B", "C", "E"], "Extension 2.")
        kb.extract_rule("s", ["A", "B", "D", "F"], "Extension 3.")

        self.assertEqual(kb.active_rule_count(), 1)
        self.assertEqual(kb.merge_count, 3)
        merged = list(kb.rules.values())[0]
        for anchor in ["A", "B", "C", "D", "E", "F"]:
            self.assertIn(anchor, merged["anchors"])


# ============================================================
# TEST 5: Old rule retirement
# ============================================================

class Test365RuleRetirement(SimulationTestBase):

    def test_capacity_triggers_retire(self):
        """When a skill file exceeds capacity, oldest rule should be retired."""
        kb = SimulatedKnowledgeBase(self.test_dir)

        for i in range(20):
            kb.extract_rule(
                "heavy-skill",
                ["Anchor{}".format(i), "Base{}".format(i)],
                "A rule with plenty of words. " * 20,
            )

        self.assertTrue(kb.check_capacity("heavy-skill", threshold=500))

        retired_any = False
        for key, rule in list(kb.rules.items()):
            if rule["skill"] == "heavy-skill" and not rule["retired"]:
                kb.retire_rule(key)
                retired_any = True
                break

        self.assertTrue(retired_any)
        self.assertGreater(kb.retire_count, 0)

        all_retired = [r for r in kb.rules.values() if r["retired"]]
        for r in all_retired:
            d = kb._skill_dir(r["skill"])
            path = os.path.join(d, "SKILL_MEMORY.md")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("[RETIRED]", content, "Retired rule must be marked, not deleted")

    def test_retired_rule_not_merged_into(self):
        """A retired rule should not be a merge target."""
        kb = SimulatedKnowledgeBase(self.test_dir)

        kb.extract_rule("s", ["X", "Y", "Z"], "Old rule.")
        for key in list(kb.rules.keys()):
            kb.retire_rule(key)

        result = kb.extract_rule("s", ["X", "Y", "Z2"], "New rule.")
        self.assertEqual(result, "append", "Should append, not merge into retired")
        self.assertEqual(kb.active_rule_count(), 1)


# ============================================================
# TEST 6: Rejection memory across evolve cycles
# ============================================================

class Test365RejectionMemory(SimulationTestBase):

    def test_rejected_pattern_skipped_in_future(self):
        """Once a pattern is rejected, future evolve should skip it."""
        kb = SimulatedKnowledgeBase(self.test_dir)

        kb.add_rejection("correction-Building")
        self.assertTrue(kb.is_rejected("correction-Building"))
        self.assertFalse(kb.is_rejected("correction-NPC"))

    def test_rejection_persists_across_multiple_evolve_runs(self):
        """Rejections must persist across simulated evolve runs."""
        kb = SimulatedKnowledgeBase(self.test_dir)
        kb.add_rejection("hotspot-Combat")

        for evolve_run in range(5):
            patterns = [
                {"type": "hotspot", "module": "Combat", "count": 6},
                {"type": "correction", "module": "NPC", "count": 3},
            ]
            for p in patterns:
                key = "{}-{}".format(p["type"], p["module"])
                if kb.is_rejected(key):
                    continue
                kb.extract_rule("s", ["Dummy"], "Rule from {}.".format(key))

        combat_rules = [r for r in kb.rules.values()
                        if "Combat" in str(r["anchors"]) or "hotspot" in r["content"]]
        self.assertEqual(len(combat_rules), 0,
                         "Rejected pattern should never produce a rule")
        self.assertGreater(kb.active_rule_count(), 0,
                           "Other patterns should still produce rules")


# ============================================================
# TEST 7: Compaction keeps trace bounded over a full year
# ============================================================

class Test365CompactionBounded(SimulationTestBase):

    def test_500_entries_stay_bounded(self):
        """Write 500 entries with periodic compaction -> stays bounded."""
        self.write_limits({
            "compact_max_entries": 60,
            "level2_age_days": 14, "level2_score_threshold": 3.0,
            "level3_age_days": 7, "level3_score_threshold": 5.0,
            "keep_top_n_per_module": 3,
        })

        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        mods = list(MODULE_FILE_MAP.keys())

        for i in range(500):
            ts = base + timedelta(days=i // 3, hours=(i * 3) % 24)
            mod = mods[i % len(mods)]
            score = 0.3 + random.random() * 3.0
            entry = make_trace_block(
                ts, [mod], round(score, 2),
                edit_count=random.randint(2, 15),
                lines_changed=random.randint(5, 100),
            )
            flush.append_trace(entry)

            if i > 0 and i % 30 == 0:
                flush.check_and_compact()

        flush.check_and_compact()

        content = self.read_trace()
        block_count = self.count_blocks(content)
        self.assertLessEqual(block_count, 250,
                             "500 entries should compact significantly (got {})".format(block_count))
        self.assertGreater(block_count, 0)

    def test_all_modules_survive_heavy_compaction(self):
        """After compaction, every module retains >= keep_top_n entries."""
        self.write_limits({
            "compact_max_entries": 25,
            "level2_age_days": 100, "level2_score_threshold": 0.1,
            "level3_age_days": 3, "level3_score_threshold": 3.0,
            "keep_top_n_per_module": 2,
        })

        now = datetime.now(timezone.utc)
        test_mods = ["ModA", "ModB", "ModC", "ModD", "ModE"]

        for i in range(100):
            ts = now - timedelta(days=5 + i // 3)
            mod = test_mods[i % len(test_mods)]
            score = 0.3 + random.random() * 0.4
            entry = make_trace_block(ts, [mod], round(score, 2),
                                     edit_count=3, lines_changed=10)
            flush.append_trace(entry)

        flush.check_and_compact()

        content = self.read_trace()
        blocks = self.get_all_blocks(content)
        mod_counts = Counter()
        for b in blocks:
            for m in re.findall(r"[A-Za-z_]\w*", self.get_field(b, "modules")):
                mod_counts[m] += 1

        for mod in test_mods:
            self.assertGreaterEqual(
                mod_counts.get(mod, 0), 2,
                "{} should keep >= 2 entries (got {})".format(mod, mod_counts.get(mod, 0))
            )

    def test_validated_false_never_deleted(self):
        """validated:false entries must survive any compaction level."""
        self.write_limits({
            "compact_max_entries": 5,
            "level2_age_days": 1, "level2_score_threshold": 10.0,
            "level3_age_days": 1, "level3_score_threshold": 10.0,
        })

        now = datetime.now(timezone.utc)
        old = now - timedelta(days=60)
        blocks = []
        for i in range(15):
            val = "false" if i < 5 else "_"
            blocks.append(make_trace_block(
                old, ["M{}".format(i)], 0.1, validated=val,
            ))

        content = "# Traces\n\n" + "\n".join(blocks) + "\n"
        self.write_trace(content)
        flush.check_and_compact()

        content = self.read_trace()
        false_count = content.count("validated: false")
        self.assertEqual(false_count, 5, "All 5 validated:false entries must survive")


# ============================================================
# TEST 8: Quarterly module focus drift
# ============================================================

class Test365QuarterlyDrift(SimulationTestBase):

    def test_module_focus_shifts_across_quarters(self):
        """Different quarters should have different dominant modules."""
        quarterly_counters = [Counter() for _ in range(4)]

        for q in range(4):
            for _ in range(200):
                modules = pick_modules_for_quarter(q)
                for m in modules:
                    quarterly_counters[q][m] += 1

        q1_top = quarterly_counters[0].most_common(1)[0][0]
        q2_top = quarterly_counters[1].most_common(1)[0][0]

        self.assertIn(q1_top, QUARTERLY_FOCUS[0],
                      "Q1 top module should be in Q1 focus")
        self.assertIn(q2_top, QUARTERLY_FOCUS[1],
                      "Q2 top module should be in Q2 focus")

        all_q1_mods = set(quarterly_counters[0].keys())
        all_q2_mods = set(quarterly_counters[1].keys())
        self.assertGreater(len(all_q1_mods), 2, "Q1 should touch multiple modules")
        self.assertGreater(len(all_q2_mods), 2, "Q2 should touch multiple modules")


# ============================================================
# TEST 9: End-to-end collector -> flush -> evolve -> knowledge base
# ============================================================

class Test365EndToEnd(SimulationTestBase):

    def test_full_pipeline_collector_to_knowledge_base(self):
        """
        1. Collector writes buffer
        2. Flush scores and writes trace
        3. Validated signal injected
        4. Evolve detects patterns
        5. Rules extracted into knowledge base
        """
        kb = SimulatedKnowledgeBase(self.test_dir)

        entries = {
            "Assets/Scripts/Modules/Building/BuildingManager.cs": (60, 10, {"R"}),
            "Assets/Scripts/Modules/Building/BuildingFunc.cs": (25, 4, set()),
        }
        collector.write_buffer(entries)
        flush.flush_new_trace(idp={
            "mode": "standard", "type": "feature",
            "request": "add batch upgrade", "intent": "implement batch upgrade",
            "skills": ["programmer-building-skill"],
        })

        self.assertTrue(os.path.isfile(flush.TRACE_FILE))
        self.assertFalse(os.path.isfile(collector.BUFFER_FILE))

        with open(flush.PENDING_VALIDATED_FILE, "w", encoding="utf-8") as f:
            json.dump({"result": "accepted"}, f)
        flush.apply_validated_update()

        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(6):
            entry = make_trace_block(
                base + timedelta(days=i), ["Building"], 2.0 + i * 0.1,
                correction="auto:minor" if i < 4 else "_", edit_count=9 + i,
            )
            flush.append_trace(entry)

        content = self.read_trace()
        new_content, patterns, processed = self.simulate_evolve(content)
        self.write_trace(new_content)

        self.assertGreater(processed, 0)
        self.assertGreater(len(patterns), 0)

        for p in patterns:
            mod = p.get("module", "Unknown")
            kb.extract_rule(
                "programmer-{}-skill".format(mod.lower()),
                ["{}Manager".format(mod), "OnDestroy"],
                "Rule from pattern {} with {} occurrences.".format(p["type"], p.get("count", "?")),
            )

        self.assertGreater(kb.active_rule_count(), 0)

        result = self.read_trace()
        self.assertIn("status:processed", result)
        self.assertIn("<!-- PROCESSED", result)

    def test_pipeline_session_full_lifecycle(self):
        """Pipeline: write -> pending-pipeline -> GO -> validated:true -> evolve."""
        now = datetime(2026, 5, 10, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(8):
            entry = make_trace_block(
                now + timedelta(hours=i), ["Combat"], 2.5,
                validated="pending-pipeline", pipeline_run_id="lifecycle-pipe-001",
                correction="auto:minor" if i < 4 else "_",
                edit_count=12, mode="pipeline", entry_type="feature",
            )
            flush.append_trace(entry)

        content = self.read_trace()
        self.assertEqual(content.count("pending-pipeline"), 8)

        with open(flush.PENDING_PIPELINE_FILE, "w", encoding="utf-8") as f:
            json.dump({"pipeline_run_id": "lifecycle-pipe-001", "result": "GO"}, f)
        flush.apply_pipeline_result()

        content = self.read_trace()
        self.assertNotIn("pending-pipeline", content)
        self.assertEqual(content.count("validated: true"), 8)

        new_content, patterns, processed = self.simulate_evolve(content)
        self.assertGreater(processed, 0)


# ============================================================
# TEST 10: Audit line and data integrity over full year
# ============================================================

class Test365DataIntegrity(SimulationTestBase):

    def test_no_phantom_blocks_after_year(self):
        """After many operations, all TRACE blocks must be well-formed."""
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(150):
            ts = base + timedelta(days=i)
            entry = make_trace_block(
                ts, ["Mod{}".format(i % 6)], 1.5 + random.random(),
                edit_count=random.randint(3, 15),
            )
            flush.append_trace(entry)

            if i % 25 == 0 and i > 0:
                flush.check_and_compact()

        flush.check_and_compact()

        content = self.read_trace()
        opens = len(re.findall(r"<!-- TRACE ", content))
        closes = len(re.findall(r"<!-- /TRACE -->", content))
        self.assertEqual(opens, closes, "Tag mismatch: {} opens, {} closes".format(opens, closes))

        for b in self.get_all_blocks(content):
            for field in ["timestamp", "modules", "score", "validated", "correction"]:
                self.assertTrue(
                    self.get_field(b, field) != "",
                    "Block missing field: {}".format(field),
                )

    def test_old_audit_lines_cleaned(self):
        """PROCESSED/COMPACTED lines older than expire threshold should be removed."""
        now = datetime.now(timezone.utc)
        old_ts = (now - timedelta(days=45)).strftime("%Y-%m-%dT%H:%M:%SZ")
        recent_ts = (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

        content = "# Traces\n\n"
        content += "<!-- PROCESSED ts:{} entries:10 proposals:2 -->\n".format(old_ts)
        content += "<!-- COMPACTED ts:{} removed:5 kept:20 -->\n".format(old_ts)
        content += "<!-- PROCESSED ts:{} entries:3 proposals:1 -->\n".format(recent_ts)

        for i in range(5):
            content += make_trace_block(
                now - timedelta(days=30), ["Old"], 0.3, status="expired") + "\n"
        content += make_trace_block(now, ["Keep"], 2.0) + "\n"

        self.write_trace(content)
        self.write_limits({"compact_max_entries": 1, "processed_expire_days": 30})
        flush.check_and_compact()

        result = self.read_trace()
        self.assertNotIn(old_ts, result, "45-day-old audit lines should be gone")
        self.assertIn(recent_ts, result, "5-day-old audit lines should survive")

    def test_lock_blocks_compaction(self):
        """Compaction must be skipped when .trace_lock exists."""
        with open(flush.TRACE_LOCK_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write("locked")

        now = datetime.now(timezone.utc)
        old = now - timedelta(days=30)
        for i in range(100):
            entry = make_trace_block(old, ["M{}".format(i % 5)], 0.5,
                                     status="expired" if i < 50 else "pending")
            flush.append_trace(entry)

        self.write_limits({"compact_max_entries": 10})
        flush.check_and_compact()

        self.assertEqual(self.count_blocks(), 100, "No compaction when locked")

        os.remove(flush.TRACE_LOCK_FILE)
        flush.check_and_compact()

        self.assertLess(self.count_blocks(), 100, "Compaction should run after unlock")


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("CastFlow Self-Evolution - 365-Day Production Simulation")
    if KEEP_DATA:
        print("Mode: --keep-data  (output -> test-output/365day/)")
    print("=" * 70)
    unittest.main(verbosity=2)
