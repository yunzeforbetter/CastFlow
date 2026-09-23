#!/usr/bin/env python3
"""Structural checks on the shipped GLOBAL_SKILL_MEMORY + ROOT_RULES texts."""

from __future__ import print_function

import os
import unittest

_CORE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", ".castflow", "core"
))
_GLOBAL = os.path.join(_CORE, "skills", "GLOBAL_SKILL_MEMORY.md")
_ROOT_RULES = os.path.join(_CORE, "templates", "root", "ROOT_RULES.template.md")

_CEREMONY = (
    "检查清单",
    "P0",
    "底层法律",
    "缺一不可",
    "执行模式检测",
    ".pending_idp",
    "mLevel",
)

_PROTOCOLS = (
    "## Protocol 1: Prove a project API before use",
    "## Protocol 2: Constraints beat copied code",
    "## Protocol 3: If the scope is unclear, ask first",
)


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class GlobalSkillMemoryShippedText(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.global_text = _read(_GLOBAL)
        cls.root_text = _read(_ROOT_RULES)

    def test_shipped_files_exist(self):
        self.assertTrue(os.path.isfile(_GLOBAL), _GLOBAL)
        self.assertTrue(os.path.isfile(_ROOT_RULES), _ROOT_RULES)

    def test_three_protocols_present(self):
        for heading in _PROTOCOLS:
            self.assertIn(heading, self.global_text)

    def test_three_jobs_still_present(self):
        g = self.global_text
        self.assertIn("EXAMPLES.md", g)
        self.assertIn("opened source definition", g)
        self.assertIn("A location the user pointed at", g)
        self.assertIn("Copied code yields to constraints", g)
        self.assertIn("collect first; do not write code", g)
        self.assertIn("Irreversible", g)

    def test_removed_rituals_absent(self):
        g = self.global_text
        for token in _CEREMONY:
            self.assertNotIn(token, g, token)

    def test_root_rules_t1_t2_api_agree(self):
        r = self.root_text
        self.assertIn("whole `GLOBAL_SKILL_MEMORY.md`", r)
        self.assertIn("no extra file; apply protocol 3 from the T1 load", r)
        self.assertIn(
            "Evidence is EXAMPLES, an opened definition, or a user pointer.",
            r,
        )
        self.assertIn("Unverified calls get TODO; do not guess signatures.", r)


if __name__ == "__main__":
    unittest.main()
