#!/usr/bin/env python3
"""catalog.json patch (queue uses accepted modules)."""

import os
import sys
import unittest

_CASTFLOW = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", ".castflow"
))
sys.path.insert(0, _CASTFLOW)

from manager.catalog import empty_catalog, patch_module


class TestCatalogPatch(unittest.TestCase):

    def test_patch_module(self):
        cat = empty_catalog()
        cat["modules"] = [{"id": "a", "name": "A", "status": "candidate"}]
        cat, mod = patch_module(cat, "a", {"status": "accepted", "notes": "x"})
        self.assertEqual(mod["status"], "accepted")
        self.assertEqual(mod["notes"], "x")

    def test_patch_unknown_returns_none(self):
        cat = empty_catalog()
        cat, mod = patch_module(cat, "missing", {"status": "accepted"})
        self.assertIsNone(mod)


if __name__ == "__main__":
    unittest.main()
