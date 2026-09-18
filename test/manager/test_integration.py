#!/usr/bin/env python3
"""End-to-end: seed → queue → sync → evolve off."""

import json
import os
import shutil
import sys
import tempfile
import unittest

_CASTFLOW = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", ".castflow"
))
sys.path.insert(0, _CASTFLOW)

from manager import evolution, queue
from manager.paths import ensure_runtime_layout, runtime_dir, runtime_path
from manager.cli import main as manager_main


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cf_e2e_")
        _write(os.path.join(self.root, "pyproject.toml"), "[project]\nname='demo'\n")
        for name in ("billing", "inventory"):
            for i in range(4):
                _write(
                    os.path.join(self.root, "src", name, "m{}.py".format(i)),
                    "class {}{}:\n    pass\n".format(name.title(), i),
                )
            _write(
                os.path.join(self.root, "src", name, "README.md"),
                "# {}\n\nOwns {} in this app.\n".format(name, name),
            )

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_seed_queue_sync_evolve_off(self):
        rc = manager_main(["--project-root", self.root, "seed"])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(runtime_path(self.root, "config")))
        self.assertTrue(os.path.isdir(os.path.join(
            self.root, ".agents", "skills", "skill-creator")))
        self.assertTrue(os.path.isdir(os.path.join(
            self.root, ".claude", "skills", "skill-creator")))
        self.assertTrue(os.path.isfile(os.path.join(
            self.root, ".claude", "skills", "skill-creator", "SKILL.md")))
        self.assertFalse(os.path.isdir(os.path.join(
            self.root, ".cursor", "skills", "skill-creator")))
        self.assertFalse(os.path.isdir(os.path.join(
            self.root, ".grok", "skills", "skill-creator")))
        self.assertFalse(os.path.isdir(os.path.join(
            self.root, ".cursor", "skills", "skill-creator")))
        self.assertTrue(os.path.isfile(os.path.join(self.root, "AGENTS.md")))
        self.assertTrue(os.path.isfile(os.path.join(
            self.root, ".grok", "hooks", "castflow.json")))

        rc = manager_main(["--project-root", self.root, "queue"])
        self.assertEqual(rc, 0)
        q = queue.load_queue(self.root)
        self.assertEqual(q.get("items") or [], [])
        text = queue.build_handoff(self.root)
        self.assertEqual(text, "")

        rc = manager_main(["--project-root", self.root, "sync"])
        self.assertEqual(rc, 0)

        rc = manager_main(["--project-root", self.root, "evolve", "off"])
        self.assertEqual(rc, 0)
        self.assertFalse(evolution.is_enabled(self.root))
        self.assertFalse(os.path.isfile(os.path.join(
            self.root, ".grok", "hooks", "castflow.json")))
        self.assertFalse(os.path.isdir(os.path.join(
            runtime_dir(self.root), "skills", "origin-evolve-skill")))
        self.assertFalse(os.path.isdir(os.path.join(
            self.root, ".claude", "skills", "origin-evolve-skill")))
        with open(os.path.join(self.root, "AGENTS.md"), encoding="utf-8") as f:
            agents = f.read()
        self.assertIn("evolution plugin OFF", agents)

        rc = manager_main(["--project-root", self.root, "evolve", "on"])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(os.path.join(
            self.root, ".grok", "hooks", "castflow.json")))
        self.assertTrue(os.path.isdir(os.path.join(
            runtime_dir(self.root), "skills", "origin-evolve-skill")))


class TestCliNoArgs(unittest.TestCase):
    def test_no_args_prints_usage(self):
        rc = manager_main([])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
