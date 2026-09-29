#!/usr/bin/env python3

import os
import shutil
import sys
import tempfile
import unittest

_CASTFLOW = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", ".castflow"
))
sys.path.insert(0, _CASTFLOW)

from manager import coldstart


class ColdStartExtensionTests(unittest.TestCase):

    def test_function_declarations_and_lowercase_references_are_indexed(self):
        sources = {
            "src/payments/charge.py": (
                "def charge_card():\n"
                "    return True\n"
            ),
            "src/ui/view.py": (
                "from payments.charge import charge_card\n"
                "def click():\n"
                "    charge_card()\n"
            ),
            "src/auth/login.ts": (
                "export function loginUser() { return true; }\n"
            ),
            "src/app/home.ts": (
                "import { loginUser } from '../auth/login';\n"
                "export function render() { loginUser(); }\n"
            ),
        }
        cards = {card["id"]: card for card in coldstart.analyze_sources(sources)}
        self.assertIn("charge_card", cards["payments"]["core_symbols"])
        self.assertIn("loginUser", cards["auth"]["core_symbols"])
        self.assertEqual(cards["payments"]["frequency"], 1)
        self.assertEqual(cards["auth"]["frequency"], 1)

    def test_module_marks_are_loaded_and_applied_before_cut(self):
        root = tempfile.mkdtemp(prefix="castflow-marks-")
        self.addCleanup(shutil.rmtree, root, True)
        runtime = os.path.join(root, ".castflow-runtime")
        os.makedirs(runtime)
        with open(os.path.join(runtime, "module-marks.txt"), "w", encoding="utf-8") as handle:
            handle.write("# accepted user decision\nattach a b feature\n")
        self.assertEqual(
            coldstart.load_module_marks(root),
            [{"id": "a", "action": "attach", "target_id": "b", "role": "feature"}],
        )
        sources = {
            "src/a/A.py": "class A:\n    pass\n",
            "src/b/B.py": "class B:\n    pass\n",
        }
        cards = coldstart.analyze_sources(
            sources, module_marks=coldstart.load_module_marks(root),
        )
        self.assertEqual(len(cards), 1)
        self.assertEqual([atom["id"] for atom in cards[0]["atoms"]], ["a", "b"])

    def test_keep_mark_is_a_hard_boundary_for_fallback_merges(self):
        def atom(name, keep=False):
            return {
                "id": name, "kind": "file", "role": "feature",
                "paths": [name + ".py"], "decls": [], "owners": {},
                "empty_enums": set(), "entries": 0, "members": [name],
                "file_count": 1, "symbol_fanin": {}, "frequency": 0,
                "mark_keep": keep, "mark_role": "",
            }
        merges = coldstart.build_merges([atom("a", keep=True), atom("b")], {})
        self.assertEqual(merges, [])


if __name__ == "__main__":
    unittest.main()
