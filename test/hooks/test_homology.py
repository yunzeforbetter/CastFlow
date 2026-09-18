#!/usr/bin/env python3
"""Homology helper: connected components via the shipped module."""

import json
import os
import sys
import unittest

_HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
HOOKS_DIR = os.path.normpath(os.path.join(
    _HARNESS_DIR, "..", "..", ".castflow", "core", "hooks"
))
if HOOKS_DIR not in sys.path:
    sys.path.insert(0, HOOKS_DIR)

import _homology  # noqa: E402


class TestHomology(unittest.TestCase):
    def test_insert_tokens_pair(self):
        a = {"id": "a", "slug": "one", "skill": "",
             "anchors": ["method:Foo:Insert"]}
        b = {"id": "b", "slug": "two", "skill": "",
             "anchors": ["Insert"]}
        self.assertTrue(_homology.homologous(a, b))

    def test_empty_anchors_do_not_pair(self):
        a = {"id": "a", "slug": "one", "skill": "", "anchors": []}
        b = {"id": "b", "slug": "two", "skill": "", "anchors": []}
        self.assertFalse(_homology.homologous(a, b))
        result = _homology.cluster_items([a, b])
        self.assertEqual(len(result["clusters"]), 2)

    def test_connected_components_and_singleton(self):
        items = [
            {"id": "p1", "slug": "same", "skill": "", "anchors": []},
            {"id": "p2", "slug": "same", "skill": "", "anchors": []},
            {"id": "s", "slug": "solo", "skill": "", "anchors": []},
            {"id": "e", "slug": "empty-a", "skill": "", "anchors": []},
        ]
        result = _homology.cluster_items(items)
        clusters = result["clusters"]
        sizes = sorted(len(c) for c in clusters)
        self.assertEqual(sizes, [1, 1, 2])
        paired = [c for c in clusters if len(c) == 2][0]
        self.assertEqual(set(paired), {"p1", "p2"})
        singles = [c for c in clusters if len(c) == 1]
        self.assertEqual(len(singles), 2)

    def test_cli_main_roundtrip(self):
        payload = {
            "items": [
                {"id": "a", "slug": "x", "skill": "",
                 "anchors": ["method:Foo:Insert"]},
                {"id": "b", "slug": "y", "skill": "", "anchors": ["Insert"]},
                {"id": "c", "slug": "z", "skill": "", "anchors": []},
            ]
        }
        import io
        old_in, old_out = sys.stdin, sys.stdout
        sys.stdin = io.StringIO(json.dumps(payload))
        buf = io.StringIO()
        sys.stdout = buf
        try:
            rc = _homology.main()
        finally:
            sys.stdin, sys.stdout = old_in, old_out
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        sizes = sorted(len(c) for c in data["clusters"])
        self.assertEqual(sizes, [1, 2])


if __name__ == "__main__":
    unittest.main()
