#!/usr/bin/env python3
"""validate.py: four-file skill shape (used by manager.py validate)."""

import os
import shutil
import sys
import tempfile
import unittest

_CASTFLOW_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".castflow",
)
sys.path.insert(0, _CASTFLOW_DIR)

from installer.validate import (
    validate_skill_dir,
    _count_size_units,
    extract_yaml_description,
    description_shape_errors,
    frontmatter_key_errors,
)


VALID_DESCRIPTION = (
    "Use when checking a compact four-file skill fixture. "
    "NOT for production feature work."
)


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_skill(self, name="test-skill", **overrides):
        skill_dir = os.path.join(self.tmpdir, name)
        os.makedirs(skill_dir, exist_ok=True)
        defaults = {
            "SKILL.md": (
                "---\nname: test\ndescription: {}\n---\n\n# Test\n".format(
                    VALID_DESCRIPTION
                )
            ),
            "EXAMPLES.md": "# Examples\n\n## Example 1\n\nSample.\n",
            "SKILL_MEMORY.md": "# Rules\n\n### Rule 1\n\nDon't break.\n",
            "ITERATION_GUIDE.md": "# Guide\n\n### Rule 1\n\nUpdate when needed.\n",
        }
        defaults.update(overrides)
        for fname, content in defaults.items():
            with open(os.path.join(skill_dir, fname), "w",
                       encoding="utf-8", newline="\n") as f:
                f.write(content)
        return skill_dir

    def test_valid_skill_passes(self):
        skill_dir = self._create_skill()
        errors, warnings, skipped = validate_skill_dir(skill_dir)
        self.assertFalse(skipped)
        self.assertEqual(errors, [])

    def test_missing_metadata_fails(self):
        skill_dir = self._create_skill(**{
            "SKILL.md": "# No metadata\n\nJust text.\n"
        })
        errors, _, _ = validate_skill_dir(skill_dir)
        self.assertTrue(any("metadata" in e.lower() for e in errors))

    def test_residual_placeholder_fails(self):
        skill_dir = self._create_skill(**{
            "EXAMPLES.md": "# Examples\n\n{{UNFILLED}}\n"
        })
        errors, _, _ = validate_skill_dir(skill_dir)
        self.assertTrue(any("placeholder" in e.lower() for e in errors))

    def test_emoji_detected(self):
        skill_dir = self._create_skill(**{
            "SKILL.md": "---\nname: t\ndescription: t\n---\n\n# Test \u2705\n"
        })
        errors, _, _ = validate_skill_dir(skill_dir)
        self.assertTrue(any("emoji" in e.lower() for e in errors))

    def test_date_in_skill_memory_fails(self):
        skill_dir = self._create_skill(**{
            "SKILL_MEMORY.md": "# Rules\n\nUpdated 2025-03-15.\n"
        })
        errors, _, _ = validate_skill_dir(skill_dir)
        self.assertTrue(any("date" in e.lower() for e in errors))

    def test_date_in_iteration_guide_fails(self):
        skill_dir = self._create_skill(**{
            "ITERATION_GUIDE.md": "# Guide\n\nLast check 2026-01-01.\n"
        })
        errors, _, _ = validate_skill_dir(skill_dir)
        self.assertTrue(any("date" in e.lower() for e in errors))

    def test_oversized_file_warns(self):
        big_content = (
            "---\nname: t\ndescription: {}\n---\n\n".format(VALID_DESCRIPTION)
            + "x " * 5000
        )
        skill_dir = self._create_skill(**{"SKILL.md": big_content})
        errors, warnings, _ = validate_skill_dir(skill_dir)
        self.assertEqual(errors, [])
        self.assertTrue(any("size" in w.lower() for w in warnings))

    def test_oversized_examples_prose_warns(self):
        bloated = "# Examples\n\n" + ("unused prose padding. " * 2000)
        skill_dir = self._create_skill(**{"EXAMPLES.md": bloated})
        errors, warnings, skipped = validate_skill_dir(skill_dir)
        self.assertFalse(skipped)
        self.assertEqual(errors, [])
        self.assertTrue(
            any("EXAMPLES.md" in w and "size" in w.lower() for w in warnings)
        )
        self.assertTrue(any("delete or merge" in w.lower() for w in warnings))

    def test_non_standard_structure_skipped(self):
        skill_dir = os.path.join(self.tmpdir, "odd-skill")
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "README.md"), "w") as f:
            f.write("# Not a standard skill\n")
        _, _, skipped = validate_skill_dir(skill_dir)
        self.assertTrue(skipped)

    def test_extra_markdown_is_invalid(self):
        skill_dir = self._create_skill()
        with open(os.path.join(skill_dir, "ANALYSIS.md"), "w", encoding="utf-8") as f:
            f.write("# leftover notes\n")
        errors, _, skipped = validate_skill_dir(skill_dir)
        self.assertFalse(skipped)
        self.assertTrue(any("extra markdown" in e.lower() for e in errors))

    def test_nested_extra_markdown_is_invalid(self):
        skill_dir = self._create_skill()
        ref = os.path.join(skill_dir, "references")
        os.makedirs(ref)
        with open(os.path.join(ref, "more-examples.md"), "w", encoding="utf-8") as f:
            f.write("# annex\n")
        errors, _, skipped = validate_skill_dir(skill_dir)
        self.assertFalse(skipped)
        self.assertTrue(any("extra markdown" in e.lower() for e in errors))

    def test_keyword_dump_description_fails(self):
        skill_dir = self._create_skill(**{
            "SKILL.md": (
                "---\nname: t\n"
                "description: architect architecture layers manager service\n"
                "---\n\n# Test\n"
            )
        })
        errors, _, skipped = validate_skill_dir(skill_dir)
        self.assertFalse(skipped)
        self.assertTrue(any("keyword dump" in e.lower() for e in errors))

    def test_description_missing_yield_fails(self):
        skill_dir = self._create_skill(**{
            "SKILL.md": (
                "---\nname: t\n"
                "description: Use when the user asks about billing totals.\n"
                "---\n\n# Test\n"
            )
        })
        errors, _, skipped = validate_skill_dir(skill_dir)
        self.assertFalse(skipped)
        self.assertTrue(any("not/yield" in e.lower() for e in errors))

    def test_count_size_units_excludes_code(self):
        content = "Hello world\n```python\nlong code here\n```\nEnd.\n"
        size = _count_size_units(content)
        self.assertLess(size, 15)

    def test_extract_folded_yaml_description(self):
        text = (
            "---\nname: x\ndescription: >\n"
            "  Use when the user says scan.\n"
            "  NOT bootstrap.\n"
            "when-to-use: scan\n---\n\n# X\n"
        )
        desc = extract_yaml_description(text)
        self.assertIn("Use when", desc)
        self.assertIn("NOT bootstrap", desc)
        self.assertTrue(
            any("extra key" in e.lower() for e in frontmatter_key_errors(text))
        )

    def test_description_shape_accepts_spoken_yield(self):
        self.assertEqual(
            description_shape_errors(VALID_DESCRIPTION),
            [],
        )

    def test_description_shape_rejects_dump(self):
        errs = description_shape_errors(
            "architect architecture layers dependency manager"
        )
        self.assertTrue(any("keyword dump" in e.lower() for e in errs))

    def test_description_shape_rejects_pushy(self):
        errs = description_shape_errors(
            "Use when the user asks about billing. "
            "Make sure to use this skill whenever the user mentions "
            "invoices, money, or any company data, even if they don't "
            "ask for billing. NOT other programmer-*-skill."
        )
        self.assertTrue(any("pushy" in e.lower() or "over-recall" in e.lower()
                            for e in errs))

    def test_programmer_description_too_long_fails(self):
        long_desc = (
            "Use when the user mentions billing, invoices, charges, "
            "payments, refunds, ledgers, tax, receipts, dunning, "
            "or asks how to add a feature or fix a bug here, and also "
            "when they talk about money, checkout, or this module's files. "
            "Read SKILL_MEMORY then EXAMPLES before editing. "
            "NOT other programmer-*-skill."
        )
        errs = description_shape_errors(
            long_desc, skill_name="programmer-billing-skill")
        self.assertTrue(any("too long" in e.lower() for e in errs))
        self.assertEqual(
            description_shape_errors(
                "Use when the user names Billing or billing. "
                "NOT other programmer-*-skill.",
                skill_name="programmer-billing-skill",
            ),
            [],
        )

    def test_description_shape_rejects_not_catalog(self):
        errs = description_shape_errors(
            "Use when the user asks about billing. "
            "NOT sibling-a-skill, NOT sibling-b-skill."
        )
        self.assertTrue(any("too many not" in e.lower() for e in errs))

    def test_description_shape_rejects_long_framework(self):
        long_desc = (
            "Use when the user asks about architecture, layering, "
            "dependency direction, cyclic imports, manager creation, "
            "service placement, ADR writing, naming conventions, "
            "physical folders, and whether a change violates the "
            "project's layers. Load SKILL_MEMORY then EXAMPLES then "
            "recon the repo, grep Manager names, and cite budgets "
            "before answering any design question in this repository. "
            "NOT module API how-to."
        )
        self.assertGreater(len(" ".join(long_desc.split())), 240)
        errs = description_shape_errors(long_desc, skill_name="skill-creator")
        self.assertTrue(any("too long" in e.lower() for e in errs))

    def test_validate_skill_dir_limit_uses_directory_name(self):
        desc = (
            "Change Billing (billing) in this repo. "
            "Use when the user names Billing or billing. "
            "NOT other programmer-*-skill. "
            + ("padding " * 18)
        )
        compact = " ".join(desc.split())
        self.assertGreater(len(compact), 240)
        self.assertLessEqual(len(compact), 280)
        skill_md = "---\nname: t\ndescription: {}\n---\n\n# Test\n".format(desc)
        prog = self._create_skill(
            name="programmer-billing-skill", **{"SKILL.md": skill_md})
        errors, _, skipped = validate_skill_dir(prog)
        self.assertFalse(skipped)
        self.assertEqual(errors, [])
        other = self._create_skill(
            name="goal-loop-creator", **{"SKILL.md": skill_md})
        errors, _, skipped = validate_skill_dir(other)
        self.assertFalse(skipped)
        self.assertTrue(any("too long" in e.lower() for e in errors))

    def test_extra_yaml_key_fails_validate_skill_dir(self):
        skill_dir = self._create_skill(**{
            "SKILL.md": (
                "---\nname: t\n"
                "description: {}\n"
                "when-to-use: scan\n"
                "---\n\n# Test\n".format(VALID_DESCRIPTION)
            )
        })
        errors, _, skipped = validate_skill_dir(skill_dir)
        self.assertFalse(skipped)
        self.assertTrue(any("extra key" in e.lower() for e in errors))


if __name__ == "__main__":
    unittest.main()
