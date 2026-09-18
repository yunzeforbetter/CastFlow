#!/usr/bin/env python3
"""catalog.json merge and patch (no Python project scanner)."""

import os
import sys
import unittest

_CASTFLOW = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", ".castflow"
))
sys.path.insert(0, _CASTFLOW)

from manager.catalog import merge_scan, empty_catalog, patch_module


class TestCatalogMerge(unittest.TestCase):

    def test_refresh_keeps_user_edits(self):
        existing = empty_catalog()
        existing["modules"] = [{
            "id": "billing",
            "name": "Billing (custom)",
            "role": "user role",
            "paths": ["old"],
            "notes": "do not charge twice",
            "status": "accepted",
            "skill_state": "none",
            "file_count": 1,
        }]
        incoming = empty_catalog()
        incoming["modules"] = [{
            "id": "billing",
            "name": "billing",
            "role": "incoming role",
            "paths": ["src/billing"],
            "notes": "",
            "status": "candidate",
            "file_count": 9,
        }, {
            "id": "newmod",
            "name": "newmod",
            "role": "",
            "paths": ["src/newmod"],
            "status": "candidate",
            "file_count": 3,
        }]
        merged = merge_scan(existing, incoming)
        billing = [m for m in merged["modules"] if m["id"] == "billing"][0]
        self.assertEqual(billing["name"], "Billing (custom)")
        self.assertEqual(billing["role"], "user role")
        self.assertEqual(billing["notes"], "do not charge twice")
        self.assertEqual(billing["status"], "accepted")
        self.assertEqual(billing["paths"], ["src/billing"])
        self.assertEqual(billing["file_count"], 9)
        self.assertFalse(billing["stale"])
        ids = [m["id"] for m in merged["modules"]]
        self.assertIn("newmod", ids)

    def test_patch_module(self):
        cat = empty_catalog()
        cat["modules"] = [{"id": "a", "name": "A", "status": "candidate"}]
        cat, mod = patch_module(cat, "a", {"status": "accepted", "notes": "x"})
        self.assertEqual(mod["status"], "accepted")
        self.assertEqual(mod["notes"], "x")


if __name__ == "__main__":
    unittest.main()
