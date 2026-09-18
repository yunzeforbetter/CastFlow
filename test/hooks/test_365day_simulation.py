#!/usr/bin/env python3
"""365-day schema:4 simulation: memory snapshots + compaction stay bounded."""

import os
import random
import unittest
from datetime import datetime, timezone, timedelta

try:
    from ._trace_harness import (
        KEEP_DATA, flush, make_trace_block, build_trace_file,
        make_output_base, TraceTestBase,
    )
except ImportError:
    from _trace_harness import (
        KEEP_DATA, flush, make_trace_block, build_trace_file,
        make_output_base, TraceTestBase,
    )

_OUTPUT_BASE = make_output_base("365day")
random.seed(2026)


class Test365DayMemoryLedger(TraceTestBase):
    TMP_PREFIX = "cf365_"
    OUTPUT_BASE = _OUTPUT_BASE

    def test_year_of_snapshots_stays_bounded_and_keeps_assets(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        blocks = []
        for day in range(365):
            ts = start + timedelta(days=day)
            weekday = ts.weekday() < 5
            n = random.randint(0, 2) if weekday else random.randint(0, 1)
            for i in range(n):
                blocks.append(make_trace_block(
                    ts + timedelta(hours=i),
                    entry_type="feedback",
                    memory_snapshots=[{
                        "slug": "d{}-{}".format(day, i),
                        "type": "feedback",
                        "content": "rule day {} item {}".format(day, i),
                    }],
                ))
            if day % 14 == 0:
                blocks.append(make_trace_block(
                    ts, entry_type="_", memory_snapshots=[],
                ))
        self.write_trace(build_trace_file(blocks))
        self.write_limits({
            "compact_max_entries": 80,
            "compact_max_size_kb": 100,
            "level2_age_days": 14,
            "level3_age_days": 7,
            "keep_recent_n": 20,
        })
        before = self.count_blocks()
        self.assertGreater(before, 80)
        flush.compact_trace(self.read_trace(), flush.load_limits())
        after = self.count_blocks()
        text = self.read_trace()
        self.assertLessEqual(after, before)
        self.assertIn("rule day", text)
        self.assertIn("<!-- MEMORY ", text)
        size_kb = os.path.getsize(flush.TRACE_FILE) / 1024.0
        self.assertLess(size_kb, 400)


if __name__ == "__main__":
    unittest.main()
