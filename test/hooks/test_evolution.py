#!/usr/bin/env python3
"""schema:4 memory-snapshot hook tests (collector + flush + compaction)."""

import json
import os
import unittest
from datetime import datetime, timezone, timedelta

try:
    from ._trace_harness import (
        KEEP_DATA, collector, flush, make_trace_block, build_trace_file,
        make_output_base, TraceTestBase,
    )
except ImportError:
    from _trace_harness import (
        KEEP_DATA, collector, flush, make_trace_block, build_trace_file,
        make_output_base, TraceTestBase,
    )

_OUTPUT_BASE = make_output_base("evolution")


class TestSetup(TraceTestBase):
    TMP_PREFIX = "castflow_"
    OUTPUT_BASE = _OUTPUT_BASE


class TestCollectorMemoryPaths(unittest.TestCase):
    def test_runtime_memory_is_captured(self):
        self.assertTrue(collector._is_memory_file(
            "C:/p/.castflow-runtime/memory/foo.md"))
        self.assertTrue(collector._is_memory_file(
            r"C:\p\.castflow-runtime\memory\bar.md"))

    def test_index_and_non_md_skipped(self):
        self.assertFalse(collector._is_memory_file(
            "C:/p/.castflow-runtime/memory/MEMORY.md"))
        self.assertFalse(collector._is_memory_file(
            "C:/p/.castflow-runtime/memory/note.txt"))
        self.assertFalse(collector._is_memory_file("C:/p/src/app.py"))

    def test_claude_auto_memory_still_matches(self):
        self.assertTrue(collector._is_memory_file(
            "C:/Users/x/.claude/projects/my-slug/memory/topic.md"))


class TestCollectorSnapshot(TestSetup):
    def test_captures_feedback_and_filters_user(self):
        path = self.write_memory_file("insert-rule", "feedback", "use Insert not Add")
        collector._capture_memory_snapshot(path)
        with open(collector.MEMORY_SNAPSHOTS_FILE, encoding="utf-8") as f:
            store = json.load(f)
        self.assertIn("insert-rule", store["snapshots"])
        self.assertEqual(store["snapshots"]["insert-rule"]["type"], "feedback")

        user_path = self.write_memory_file("profile", "user", "I like vim")
        collector._capture_memory_snapshot(user_path)
        with open(collector.MEMORY_SNAPSHOTS_FILE, encoding="utf-8") as f:
            store = json.load(f)
        self.assertNotIn("profile", store["snapshots"])

    def test_last_write_wins_same_slug(self):
        p1 = self.write_memory_file("dup", "project", "first")
        collector._capture_memory_snapshot(p1)
        p2 = self.write_memory_file("dup", "feedback", "second")
        collector._capture_memory_snapshot(p2)
        with open(collector.MEMORY_SNAPSHOTS_FILE, encoding="utf-8") as f:
            store = json.load(f)
        self.assertEqual(store["snapshots"]["dup"]["type"], "feedback")
        self.assertIn("second", store["snapshots"]["dup"]["content"])


_CJK_OK = "必须使用Insert插入有序列表不能使用Add追加否则顺序会错"
_OK_DESC = "use when inserting by index not append"


class TestCollectorFrontmatterGate(TestSetup):
    def _store(self):
        if not os.path.isfile(collector.MEMORY_SNAPSHOTS_FILE):
            return {}
        with open(collector.MEMORY_SNAPSHOTS_FILE, encoding="utf-8") as f:
            return json.load(f)

    def test_missing_name_not_captured(self):
        path = self.write_memory_file(
            "no-name", "feedback", _CJK_OK, omit_name=True,
            description=_OK_DESC)
        collector._capture_memory_snapshot(path)
        self.assertEqual(self._store().get("snapshots", {}), {})

    def test_unknown_type_not_captured(self):
        path = self.write_memory_file(
            "weird", "mystery", _CJK_OK, description=_OK_DESC)
        collector._capture_memory_snapshot(path)
        self.assertEqual(self._store().get("snapshots", {}), {})

    def test_type_only_in_body_not_captured(self):
        raw = (
            "---\nname: spoof\ndescription: {}\n---\n\n"
            "type: feedback\n{}\n"
        ).format(_OK_DESC, _CJK_OK)
        path = self.write_memory_file("spoof", None, "", raw=raw)
        collector._capture_memory_snapshot(path)
        self.assertEqual(self._store().get("snapshots", {}), {})

    def test_cjk_body_is_ok(self):
        path = self.write_memory_file(
            "cjk-rule", "feedback", _CJK_OK, description=_OK_DESC)
        collector._capture_memory_snapshot(path)
        snap = self._store()["snapshots"]["cjk-rule"]
        self.assertEqual(snap["quality"], "ok")
        self.assertEqual(snap["type"], "feedback")

    def test_punctuation_only_body_is_thin(self):
        path = self.write_memory_file(
            "dots", "feedback", "....................", description=_OK_DESC)
        collector._capture_memory_snapshot(path)
        snap = self._store()["snapshots"]["dots"]
        self.assertEqual(snap["quality"], "thin")

    def test_runtime_wins_inbound_same_slug(self):
        inbound_dir = os.path.join(
            self.test_dir, ".claude", "projects", "slug", "memory")
        inbound = self.write_memory_file(
            "dup", "project", "inbound body text goes here xx",
            extra_dir=inbound_dir, description=_OK_DESC)
        runtime = self.write_memory_file(
            "dup", "feedback", _CJK_OK, description=_OK_DESC)
        collector._capture_memory_snapshot(runtime)
        collector._capture_memory_snapshot(inbound)
        snap = self._store()["snapshots"]["dup"]
        self.assertEqual(snap["type"], "feedback")
        self.assertIn(".castflow-runtime/memory", snap["path"].replace("\\", "/"))


class TestFlushQualityGate(TestSetup):
    def test_ok_feedback_plus_thin_project_is_promotable(self):
        self.write_snapshots_store({
            "okfb": {
                "type": "feedback",
                "name": "okfb",
                "description": _OK_DESC,
                "content": _CJK_OK,
                "quality": "ok",
                "skill": "programmer-building-skill",
                "anchors": ["method:Foo:Insert"],
                "path": ".castflow-runtime/memory/okfb.md",
                "truncated": False,
            },
            "thinp": {
                "type": "project",
                "name": "thinp",
                "description": _OK_DESC,
                "content": "....",
                "quality": "thin",
                "skill": "",
                "anchors": [],
                "path": ".castflow-runtime/memory/thinp.md",
                "truncated": False,
            },
        })
        flush.flush_new_trace()
        text = self.read_trace()
        self.assertIn("gate_hint: promotable", text)
        self.assertIn("quality: ok", text)
        self.assertIn("skill: programmer-building-skill", text)
        self.assertIn("anchors: [method:Foo:Insert]", text)
        self.assertIn("<!-- MEMORY slug:okfb type:feedback quality:ok", text)

    def test_waiting_expire_days_loaded(self):
        limits = flush.load_limits()
        self.assertEqual(int(limits["waiting_expire_days"]), 21)

    def test_lock_keeps_snapshots_and_skips_trace(self):
        self.write_snapshots_store({
            "x": {
                "type": "feedback", "name": "x",
                "description": _OK_DESC, "content": _CJK_OK,
                "quality": "ok", "path": "p", "truncated": False,
            }
        })
        with open(flush.TRACE_LOCK_FILE, "w", encoding="utf-8") as f:
            f.write("1")
        result = flush.run_flush_pipeline()
        self.assertEqual(result, "locked")
        self.assertTrue(os.path.isfile(flush.MEMORY_SNAPSHOTS_FILE))
        self.assertEqual(self.read_trace(), "")

    def test_waiting_expires_after_21_days(self):
        old = datetime.now(timezone.utc) - timedelta(days=22)
        block = make_trace_block(
            old, entry_type="project", gate_hint="waiting",
            memory_snapshots=[{"slug": "w", "type": "project",
                               "content": "ctx", "quality": "thin"}])
        self.write_trace(build_trace_file([block]))
        flush.apply_trace_expiration()
        self.assertIn("status:expired", self.read_trace())

    def test_promotable_not_age_expired(self):
        old = datetime.now(timezone.utc) - timedelta(days=30)
        block = make_trace_block(
            old, entry_type="feedback", validated="_", gate_hint="promotable",
            memory_snapshots=[{"slug": "p", "type": "feedback",
                               "content": _CJK_OK, "quality": "ok"}])
        self.write_trace(build_trace_file([block]))
        flush.apply_trace_expiration()
        self.assertIn("status:pending", self.read_trace())
        self.assertNotIn("status:expired", self.read_trace())

    def test_pending_not_deleted_by_level2_age(self):
        old = datetime.now(timezone.utc) - timedelta(days=30)
        waiting = make_trace_block(
            old, entry_type="project", gate_hint="waiting",
            memory_snapshots=[{"slug": "wait", "type": "project",
                               "content": "context note here", "quality": "thin"}])
        promo = make_trace_block(
            old, entry_type="feedback", gate_hint="promotable",
            memory_snapshots=[{"slug": "keep", "type": "feedback",
                               "content": _CJK_OK, "quality": "ok"}])
        self.write_trace(build_trace_file([waiting, promo]))
        self.write_limits({
            "compact_max_entries": 80,
            "level2_age_days": 7,
            "level3_age_days": 1,
            "keep_recent_n": 0,
        })
        flush.compact_trace(self.read_trace(), flush.load_limits())
        text = self.read_trace()
        self.assertIn("slug:wait", text)
        self.assertIn("slug:keep", text)

    def test_overflow_drops_oldest_waiting_never_promotable(self):
        now = datetime.now(timezone.utc)
        blocks = []
        for i in range(5):
            ts = now - timedelta(days=5 - i)
            blocks.append(make_trace_block(
                ts, entry_type="project", gate_hint="waiting",
                memory_snapshots=[{"slug": "w{}".format(i), "type": "project",
                                   "content": "w", "quality": "thin"}]))
        blocks.append(make_trace_block(
            now, entry_type="feedback", gate_hint="promotable",
            memory_snapshots=[{"slug": "keep-promo", "type": "feedback",
                               "content": _CJK_OK, "quality": "ok"}]))
        self.write_trace(build_trace_file(blocks))
        self.write_limits({"compact_max_entries": 3, "keep_recent_n": 0})
        flush.compact_trace(self.read_trace(), flush.load_limits())
        text = self.read_trace()
        self.assertIn("keep-promo", text)
        self.assertNotIn("slug:w0", text)


class TestFlushSchema4(TestSetup):
    def test_empty_snapshots_write_nothing(self):
        flush.flush_new_trace()
        self.assertEqual(self.read_trace(), "")

    def test_flush_embeds_memory_block(self):
        self.write_snapshots_store({
            "use-x": {
                "type": "feedback",
                "name": "use-x",
                "description": "use X",
                "content": "Always use X not Y",
                "path": ".castflow-runtime/memory/use-x.md",
                "truncated": False,
            }
        })
        flush.flush_new_trace()
        text = self.read_trace()
        self.assertIn("schema:4", text)
        self.assertIn("type: feedback", text)
        self.assertIn("memory_snapshots: 1", text)
        self.assertIn("<!-- MEMORY slug:use-x type:feedback quality:", text)
        self.assertIn("Always use X not Y", text)
        self.assertNotIn("score:", text)
        self.assertFalse(os.path.isfile(flush.MEMORY_SNAPSHOTS_FILE))

    def test_legacy_pending_pipeline_marked_invalid(self):
        block = make_trace_block(
            datetime.now(timezone.utc), validated="pending-pipeline")
        self.write_trace(build_trace_file([block]))
        flush.apply_trace_expiration()
        text = self.read_trace()
        self.assertIn("validated: invalid", text)
        self.assertIn("status:invalid", text)


class TestCompaction(TestSetup):
    def _old(self, days, **kwargs):
        ts = datetime.now(timezone.utc) - timedelta(days=days)
        return make_trace_block(ts, **kwargs)

    def test_experience_assets_survive_level2(self):
        skeleton = self._old(30, entry_type="_", memory_snapshots=[])
        asset = self._old(30, entry_type="feedback", memory_snapshots=[{
            "slug": "keep-me", "type": "feedback", "content": "must keep",
        }])
        self.write_trace(build_trace_file([skeleton, asset]))
        self.write_limits({
            "compact_max_entries": 1,
            "level2_age_days": 7,
            "level3_age_days": 1,
            "keep_recent_n": 0,
        })
        content = self.read_trace()
        flush.compact_trace(content, flush.load_limits())
        text = self.read_trace()
        self.assertIn("keep-me", text)
        self.assertIn("must keep", text)

    def test_invalid_removed_level1(self):
        bad = make_trace_block(
            datetime.now(timezone.utc), status="invalid", entry_type="_")
        good = make_trace_block(
            datetime.now(timezone.utc), entry_type="feedback",
            memory_snapshots=[{"slug": "g", "type": "feedback", "content": "ok"}],
        )
        self.write_trace(build_trace_file([bad, good]))
        flush.compact_trace(self.read_trace(), dict(flush.DEFAULT_LIMITS))
        text = self.read_trace()
        self.assertNotIn("status:invalid", text)
        self.assertIn("slug:g", text)

    def test_processed_audit_expires(self):
        old_ts = (datetime.now(timezone.utc) - timedelta(days=40)).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        content = (
            "# Execution Traces\n\n"
            "<!-- PROCESSED ts:{} entries:2 proposals:1 -->\n\n"
            "{}"
        ).format(old_ts, make_trace_block(datetime.now(timezone.utc)))
        self.write_trace(content)
        self.write_limits({"processed_expire_days": 30})
        flush.compact_trace(self.read_trace(), flush.load_limits())
        self.assertNotIn("PROCESSED ts:{}".format(old_ts), self.read_trace())


class TestNotify(TestSetup):
    def test_notify_after_threshold(self):
        blocks = [
            make_trace_block(
                datetime.now(timezone.utc),
                memory_snapshots=[{"slug": "s{}".format(i), "type": "feedback",
                                   "content": "r{}".format(i)}],
            )
            for i in range(12)
        ]
        self.write_trace(build_trace_file(blocks))
        self.write_limits({
            "passive_trigger_threshold": 10,
            "passive_trigger_min_new": 5,
        })
        flush.check_notify()
        self.assertIn("NOTIFY type:passive_trigger", self.read_trace())

    def test_no_notify_below_threshold(self):
        blocks = [
            make_trace_block(
                datetime.now(timezone.utc),
                memory_snapshots=[{"slug": "s", "type": "feedback", "content": "r"}],
            )
            for _ in range(3)
        ]
        self.write_trace(build_trace_file(blocks))
        self.write_limits({
            "passive_trigger_threshold": 10,
            "passive_trigger_min_new": 5,
        })
        flush.check_notify()
        self.assertNotIn("NOTIFY type:passive_trigger", self.read_trace())


class TestSelftest(unittest.TestCase):
    def test_flush_selftest_passes(self):
        self.assertTrue(flush.selftest())


if __name__ == "__main__":
    unittest.main()
