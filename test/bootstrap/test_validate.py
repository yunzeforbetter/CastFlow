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
    validate_all,
    check_programmer_skill,
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

    def _write_only(self, name, files):
        skill_dir = os.path.join(self.tmpdir, name)
        os.makedirs(skill_dir, exist_ok=True)
        for fname, content in files.items():
            path = os.path.join(skill_dir, fname.replace("/", os.sep))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
        return skill_dir

    def _recall_skill(self, body="Change the fixture when asked.\n"):
        return (
            "---\nname: test\ndescription: {}\n---\n\n{}".format(
                VALID_DESCRIPTION, body
            )
        )

    def test_one_file_catalog_case_passing(self):
        skill_dir = self._write_only("one-file-skill", {
            "SKILL.md": self._recall_skill(),
        })
        errors, _, skipped = validate_skill_dir(skill_dir)
        print("one-file catalog case passing: skipped={} errors={}".format(
            skipped, errors))
        self.assertFalse(skipped)
        self.assertEqual(errors, [])

    def test_extra_markdown_case_failing_validation(self):
        skill_dir = self._write_only("notes-skill", {
            "SKILL.md": self._recall_skill(),
            "NOTES.md": "# another case library\n\nDo not put cases here.\n",
        })
        errors, _, skipped = validate_skill_dir(skill_dir)
        print("extra-markdown case failing validation: skipped={} errors={}".format(
            skipped, errors))
        self.assertFalse(skipped)
        self.assertTrue(any("extra markdown" in e.lower() for e in errors))

    def test_stub_case_failing_validation(self):
        empty_dir = self._write_only("empty-role-skill", {
            "SKILL.md": self._recall_skill(),
            "EXAMPLES.md": "",
        })
        errors, _, skipped = validate_skill_dir(empty_dir)
        print("stub case failing validation: skipped={} errors={}".format(
            skipped, errors))
        self.assertFalse(skipped)
        self.assertTrue(any("heading-only" in e.lower() or "empty" in e.lower()
                            for e in errors))
        heading_dir = self._write_only("heading-role-skill", {
            "SKILL.md": self._recall_skill(),
            "SKILL_MEMORY.md": "# Rules\n\n## Still only a heading\n",
        })
        errors, _, skipped = validate_skill_dir(heading_dir)
        self.assertFalse(skipped)
        self.assertTrue(any("heading-only" in e.lower() for e in errors))

    def test_unpointed_attachment_fails_and_pointer_passes(self):
        missing = self._write_only("attach-skill", {
            "SKILL.md": self._recall_skill(),
            "scripts/lookup.json": "{}\n",
        })
        errors, _, skipped = validate_skill_dir(missing)
        self.assertFalse(skipped)
        self.assertTrue(any("no pointer" in e.lower() for e in errors))
        pointed = self._write_only("attach-ok-skill", {
            "SKILL.md": self._recall_skill(
                "Run scripts/lookup.json when resolving a name.\n"
            ),
            "scripts/lookup.json": "{}\n",
        })
        errors, _, skipped = validate_skill_dir(pointed)
        self.assertFalse(skipped)
        self.assertEqual(errors, [])

    def test_freeform_nested_markdown_stays_skipped(self):
        skill_dir = self._write_only("skill-creator", {
            "SKILL.md": self._recall_skill(),
            "agents/grader.md": "# grader\n",
            "references/schemas.md": "# schema\n",
        })
        _, _, skipped = validate_skill_dir(skill_dir)
        self.assertTrue(skipped)
        shipped = os.path.join(
            _CASTFLOW_DIR, "core", "skills", "skill-creator")
        _, _, skipped = validate_skill_dir(shipped)
        self.assertTrue(skipped)

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


_PROGRAMMER_DESC = (
    "Change mail in this repo. Use when the user names mail. NOT battle."
)

_LIVE_SERVICE = (
    "public class MailService\n"
    "{\n"
    "    public int Send(int id)\n"
    "    {\n"
    "        return id;\n"
    "    }\n"
    "}\n"
)

_LIVE_FLOW = (
    "public class MailFlow\n"
    "{\n"
    "    public void Run(MailService mail, int id)\n"
    "    {\n"
    "        var n = mail.Send(id);\n"
    "    }\n"
    "}\n"
)

_GAP_SERVICE = (
    "public class MailService\n"
    "{\n"
    "    public void Send(int id)\n"
    "    {\n"
    "        if (session == null) return;\n"
    "        session.Transmit(id);\n"
    "    }\n"
    "}\n"
)

_GAP_FLOW = (
    "public class MailFlow\n"
    "{\n"
    "    public void Run(MailService mail, int id)\n"
    "    {\n"
    "        mail.Send(id);\n"
    "    }\n"
    "}\n"
)

_EMPTY_WIDGET = (
    "public class Widget\n"
    "{\n"
    "    public void Open()\n"
    "    {\n"
    "    }\n"
    "}\n"
)

_PUBLISH_BUS = (
    "public class Bus\n"
    "{\n"
    "    public void Run()\n"
    "    {\n"
    "        Ready.Publish();\n"
    "    }\n"
    "}\n"
)


def _line_of(text, snippet):
    for number, line in enumerate(text.splitlines(), 1):
        if snippet in line:
            return number
    raise AssertionError(snippet)


def _examples(scene, code, ref):
    return (
        "## Example 1: send\n\n"
        "Scene\n"
        "{scene}\n\n"
        "Code\n"
        "```\n"
        "{code}\n"
        "```\n\n"
        "Project reference\n"
        "{ref}\n"
    ).format(scene=scene, code=code, ref=ref)


class TestProgrammerSkillGate(unittest.TestCase):
    """Drive check_programmer_skill, the function validate_all calls."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="castflow-gate-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write(self, rel, text):
        path = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        return path

    def _skill(self, examples, memory=None):
        skill = os.path.join(
            self.root, ".castflow-runtime", "skills", "programmer-mail-skill",
        )
        os.makedirs(skill, exist_ok=True)
        skill_md = (
            "---\nname: programmer-mail-skill\n"
            "description: {}\n---\n\n# Mail\n\nYield to battle.\n"
        ).format(_PROGRAMMER_DESC)
        self._write(
            ".castflow-runtime/skills/programmer-mail-skill/SKILL.md",
            skill_md,
        )
        self._write(
            ".castflow-runtime/skills/programmer-mail-skill/EXAMPLES.md",
            examples,
        )
        if memory is not None:
            self._write(
                ".castflow-runtime/skills/programmer-mail-skill/SKILL_MEMORY.md",
                memory,
            )
        return skill

    def _check(self, skill):
        first = check_programmer_skill(skill, self.root)
        second = check_programmer_skill(skill, self.root)
        self.assertEqual(first, second)
        return first

    def test_live_call_without_memory_passes(self):
        self._write("Assets/Mail/MailService.cs", _LIVE_SERVICE)
        self._write("Assets/Flow/MailFlow.cs", _LIVE_FLOW)
        line_no = _line_of(_LIVE_FLOW, "mail.Send(id)")
        skill = self._skill(_examples(
            "Send the id.",
            "var n = mail.Send(id);",
            "Assets/Flow/MailFlow.cs:{}".format(line_no),
        ))
        errors = self._check(skill)
        self.assertEqual(errors, [])
        self.assertTrue(validate_all(self.root))

    def test_signature_gap_without_memory_fails(self):
        self._write("Assets/Mail/MailService.cs", _GAP_SERVICE)
        self._write("Assets/Flow/MailFlow.cs", _GAP_FLOW)
        line_no = _line_of(_GAP_FLOW, "mail.Send(id)")
        skill = self._skill(_examples(
            "Send the id.",
            "mail.Send(id);",
            "Assets/Flow/MailFlow.cs:{}".format(line_no),
        ))
        errors = self._check(skill)
        self.assertIn("signature gap missing from memory", errors)
        self.assertFalse(validate_all(self.root))

    def test_signature_gap_that_only_repeats_the_signature_fails(self):
        self._write("Assets/Mail/MailService.cs", _GAP_SERVICE)
        self._write("Assets/Flow/MailFlow.cs", _GAP_FLOW)
        line_no = _line_of(_GAP_FLOW, "mail.Send(id)")
        memory = (
            "### Rule 1: send\n\n"
            "Anchors: [method:Mail/MailService:Send]\n\n"
            "Definition\n"
            "Send takes id.\n"
        )
        skill = self._skill(_examples(
            "Send the id.",
            "mail.Send(id);",
            "Assets/Flow/MailFlow.cs:{}".format(line_no),
        ), memory)
        errors = self._check(skill)
        self.assertIn("signature gap repeats the signature", errors)

    def test_signature_gap_with_body_requirement_passes(self):
        self._write("Assets/Mail/MailService.cs", _GAP_SERVICE)
        self._write("Assets/Flow/MailFlow.cs", _GAP_FLOW)
        line_no = _line_of(_GAP_FLOW, "mail.Send(id)")
        memory = (
            "### Rule 1: session first\n\n"
            "Anchors: [method:Mail/MailService:Send]\n\n"
            "Definition\n"
            "Call Send only after session exists.\n"
        )
        skill = self._skill(_examples(
            "Send the id.",
            "mail.Send(id);",
            "Assets/Flow/MailFlow.cs:{}".format(line_no),
        ), memory)
        self.assertEqual(self._check(skill), [])

    def test_declaration_cite_fails(self):
        self._write("Assets/Mail/MailService.cs", _GAP_SERVICE)
        line_no = _line_of(_GAP_SERVICE, "public void Send(int id)")
        skill = self._skill(_examples(
            "Send the id.",
            "public void Send(int id)",
            "Assets/Mail/MailService.cs:{}".format(line_no),
        ))
        self.assertIn("call site is a declaration", self._check(skill))

    def test_empty_body_cite_fails(self):
        self._write("Assets/Widget/Widget.cs", _EMPTY_WIDGET)
        line_no = _line_of(_EMPTY_WIDGET, "public void Open()")
        skill = self._skill(_examples(
            "Open it.",
            "public void Open()",
            "Assets/Widget/Widget.cs:{}".format(line_no),
        ))
        self.assertIn("call site is an empty body", self._check(skill))

    def test_publish_without_subscriber_fails(self):
        self._write("Assets/Bus/Bus.cs", _PUBLISH_BUS)
        line_no = _line_of(_PUBLISH_BUS, "Ready.Publish()")
        skill = self._skill(_examples(
            "Publish ready.",
            "Ready.Publish();",
            "Assets/Bus/Bus.cs:{}".format(line_no),
        ))
        self.assertIn(
            "call site is a publish with no subscriber", self._check(skill),
        )

    def test_anchor_that_does_not_grep_fails(self):
        self._write("Assets/Mail/MailService.cs", _LIVE_SERVICE)
        self._write("Assets/Flow/MailFlow.cs", _LIVE_FLOW)
        line_no = _line_of(_LIVE_FLOW, "mail.Send(id)")
        memory = (
            "### Rule 1: note\n\n"
            "Anchors: [method:Nope/MissingSymbol]\n\n"
            "Definition\n"
            "Leave the return value as the caller wrote it.\n"
        )
        skill = self._skill(_examples(
            "Send the id.",
            "var n = mail.Send(id);",
            "Assets/Flow/MailFlow.cs:{}".format(line_no),
        ), memory)
        self.assertIn("memory anchor does not grep", self._check(skill))

    def test_live_call_written_up_as_a_registry_fails(self):
        self._write("Assets/Mail/MailService.cs", _LIVE_SERVICE)
        self._write("Assets/Flow/MailFlow.cs", _LIVE_FLOW)
        line_no = _line_of(_LIVE_FLOW, "mail.Send(id)")
        skill = self._skill(_examples(
            "Write this call site up as a registry.",
            "var n = mail.Send(id);",
            "Assets/Flow/MailFlow.cs:{}".format(line_no),
        ))
        self.assertIn(
            "call site is written up as a registry", self._check(skill),
        )

    def test_flow_defers_writing_rules_to_one_pass(self):
        skills = os.path.join(_CASTFLOW_DIR, "core", "skills")
        with open(os.path.join(skills, "SKILL_ITERATION.md"), encoding="utf-8") as handle:
            contract = handle.read()
        with open(os.path.join(skills, "MODULE_MARK_SYSTEM_PROMPT.md"), encoding="utf-8") as handle:
            flow = handle.read()
        keep = (
            "Keep a line only when omitting it would make the next generated "
            "call use the wrong symbol or the wrong argument."
        )
        fact = "A fact the signature already states stays an example, not a rule."
        self.assertEqual(contract.count(keep), 1)
        self.assertEqual(contract.count(fact), 1)
        self.assertNotIn(keep, flow)
        self.assertNotIn("Hot-path evidence", flow)
        self.assertNotIn("three gates", flow)
        self.assertNotIn("1-9", flow)
        for term in ("call site", "signature gap", "yield"):
            self.assertIn(term, contract)
            self.assertIn(term, flow)
        self.assertIn("Use when the user names <id>", contract)
        self.assertIn("only when validate passed", flow)
        self.assertIn("do not delete the queue", flow)
        self.assertIn("does not write a skill body", contract)
        self.assertIn("does not write a body", flow)
        self.assertIn("does not require", flow)
        self.assertIn("Checker, Collector, or Maker", flow)
        self.assertIn("run_loop.py", flow)
        self.assertIn("eval-viewer", flow)


if __name__ == "__main__":
    unittest.main()
