#!/usr/bin/env python3
"""Unit tests for the bootstrap package.

Covers: templates, claude_merge, hook_config, validate, backup, io_ops.
Each test creates an isolated tmp directory. Zero external dependencies.
"""

import json
import os
import shutil
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

# Add .castflow to path so we can import the bootstrap package
_CASTFLOW_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".castflow",
)
sys.path.insert(0, _CASTFLOW_DIR)

from bootstrap.templates import replace_placeholders, process_conditionals
from bootstrap.claude_merge import (
    merge_claude_md, _split_at_boundary, _deduplicate_sections,
    _extract_user_additions, CLAUDE_BOUNDARY,
)
from bootstrap.hook_config import merge_cursor_hooks, merge_claude_settings
from bootstrap.validate import validate_skill_dir, _count_size_units
from bootstrap.backup import BackupSession, rotate_backups
from bootstrap.io_ops import safe_write, safe_copy_file, read_file


class TestReplacePlaceholders(unittest.TestCase):

    def test_basic_replacement(self):
        content = "Hello {{NAME}}, welcome to {{PROJECT}}."
        result, warnings = replace_placeholders(content, {
            "NAME": "Alice",
            "PROJECT": "CastFlow",
        })
        self.assertEqual(result, "Hello Alice, welcome to CastFlow.")
        self.assertEqual(warnings, [])

    def test_none_value_warns(self):
        content = "Value is {{MISSING}}."
        result, warnings = replace_placeholders(content, {"MISSING": None})
        self.assertEqual(result, "Value is {{MISSING}}.")
        self.assertEqual(warnings, ["MISSING"])

    def test_no_matching_token(self):
        content = "No placeholders here."
        result, warnings = replace_placeholders(content, {"KEY": "val"})
        self.assertEqual(result, "No placeholders here.")
        self.assertEqual(warnings, [])

    def test_multiple_same_token(self):
        content = "{{A}} and {{A}} again."
        result, _ = replace_placeholders(content, {"A": "X"})
        self.assertEqual(result, "X and X again.")

    def test_strict_mode_unknown_raises(self):
        content = "Hello {{NAME}} and {{UNKNOWN}}."
        with self.assertRaises(ValueError) as ctx:
            replace_placeholders(content, {"NAME": "Alice"}, strict=True)
        self.assertIn("UNKNOWN", str(ctx.exception))

    def test_strict_mode_all_known_passes(self):
        content = "Hello {{NAME}}."
        result, warnings = replace_placeholders(
            content, {"NAME": "Bob"}, strict=True)
        self.assertEqual(result, "Hello Bob.")
        self.assertEqual(warnings, [])


class TestProcessConditionals(unittest.TestCase):

    def test_matching_tech_stack(self):
        content = "before\n<!-- if:unity -->\nunity content\n<!-- endif -->\nafter"
        result = process_conditionals(content, "unity")
        self.assertIn("unity content", result)
        self.assertIn("before", result)
        self.assertIn("after", result)

    def test_non_matching_tech_stack(self):
        content = "before\n<!-- if:unity -->\nunity only\n<!-- endif -->\nafter"
        result = process_conditionals(content, "react")
        self.assertNotIn("unity only", result)
        self.assertIn("before", result)
        self.assertIn("after", result)

    def test_multiple_conditionals(self):
        content = (
            "<!-- if:unity -->\nA\n<!-- endif -->\n"
            "<!-- if:react -->\nB\n<!-- endif -->\n"
            "C"
        )
        result = process_conditionals(content, "react")
        self.assertNotIn("A", result)
        self.assertIn("B", result)
        self.assertIn("C", result)


class TestClaudeMerge(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_new_file_written(self):
        dest = os.path.join(self.tmpdir, "CLAUDE.md")
        merge_claude_md(dest, "# New Content\n", dry_run=False)
        self.assertTrue(os.path.isfile(dest))
        self.assertEqual(read_file(dest), "# New Content\n")

    def test_boundary_merge_preserves_project_section(self):
        dest = os.path.join(self.tmpdir, "CLAUDE.md")
        boundary = CLAUDE_BOUNDARY
        existing = "# Harness v1\n\n{} PROJECT =====>\n\n## My Rules\n\nKeep this.\n".format(boundary)
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write(existing)
        new_content = "# Harness v2\n\n{} PROJECT =====>\n\n## Template Rules\n".format(boundary)
        merge_claude_md(dest, new_content, dry_run=False,
                        choice_callback=lambda _: "1")
        result = read_file(dest)
        self.assertIn("Harness v2", result)
        self.assertIn("My Rules", result)
        self.assertIn("Keep this.", result)

    def test_harness_match_preserves(self):
        dest = os.path.join(self.tmpdir, "CLAUDE.md")
        boundary = CLAUDE_BOUNDARY
        harness = "# Same Harness\n\n"
        project = "{} PROJECT =====>\n\n## User Rules\n".format(boundary)
        existing = harness + project
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write(existing)
        merge_claude_md(dest, existing, dry_run=False)
        result = read_file(dest)
        self.assertIn("User Rules", result)

    def test_diff_with_choice_1(self):
        dest = os.path.join(self.tmpdir, "CLAUDE.md")
        boundary = CLAUDE_BOUNDARY
        old = "# Old Harness\n\n{} PROJECT =====>\n\n## Project\n".format(boundary)
        new = "# New Harness\n\n{} PROJECT =====>\n\n## Template\n".format(boundary)
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write(old)
        merge_claude_md(dest, new, dry_run=False,
                        choice_callback=lambda _: "1")
        result = read_file(dest)
        self.assertIn("New Harness", result)
        self.assertIn("Project", result)
        backup_path = dest + ".castflow-backup"
        self.assertTrue(os.path.isfile(backup_path))

    def test_diff_with_choice_2_skips(self):
        dest = os.path.join(self.tmpdir, "CLAUDE.md")
        boundary = CLAUDE_BOUNDARY
        old = "# Old\n\n{} PROJECT =====>\n\n## P\n".format(boundary)
        new = "# New\n\n{} PROJECT =====>\n\n## T\n".format(boundary)
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write(old)
        merge_claude_md(dest, new, dry_run=False,
                        choice_callback=lambda _: "2")
        result = read_file(dest)
        self.assertIn("Old", result)

    def test_diff_with_harness_merge_preset_skips(self):
        dest = os.path.join(self.tmpdir, "CLAUDE.md")
        boundary = CLAUDE_BOUNDARY
        old = "# Old\n\n{} PROJECT =====>\n\n## P\n".format(boundary)
        new = "# New\n\n{} PROJECT =====>\n\n## T\n".format(boundary)
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write(old)
        merge_claude_md(
            dest, new, dry_run=False, harness_merge_choice="2")
        result = read_file(dest)
        self.assertIn("Old", result)

    def test_diff_noninteractive_aborts_without_preset(self):
        dest = os.path.join(self.tmpdir, "CLAUDE.md")
        boundary = CLAUDE_BOUNDARY
        old = "# Old Harness\n\n{} PROJECT =====>\n\n## Project\n".format(boundary)
        new = "# New Harness\n\n{} PROJECT =====>\n\n## Template\n".format(boundary)
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write(old)
        with patch("bootstrap.claude_merge.sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            with self.assertRaises(SystemExit) as ctx:
                merge_claude_md(dest, new, dry_run=False)
        self.assertEqual(ctx.exception.code, 1)

    def test_no_boundary_dedup(self):
        dest = os.path.join(self.tmpdir, "CLAUDE.md")
        existing = (
            "## Section A\n\nContent A with some shared text here.\n\n"
            "## My Custom Project Rules\n\n"
            "This is a completely unique section about project-specific conventions "
            "that has no counterpart in the template whatsoever. It describes rules "
            "about naming, file organization, and deployment procedures.\n"
        )
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write(existing)
        new_content = (
            "## Section A\n\nContent A with some shared text here.\n\n"
            "## Template Generated Rules\n\nTemplate-specific content.\n"
        )
        merge_claude_md(dest, new_content, dry_run=False)
        result = read_file(dest)
        self.assertIn("My Custom Project Rules", result)
        self.assertIn("Template Generated Rules", result)

    def test_split_at_boundary(self):
        content = "before\n{} MARKER =====>\nafter\n".format(CLAUDE_BOUNDARY)
        harness, project = _split_at_boundary(content)
        self.assertEqual(harness, "before\n")
        self.assertIn("MARKER", project)

    def test_split_no_boundary(self):
        content = "no boundary here"
        harness, project = _split_at_boundary(content)
        self.assertEqual(harness, content)
        self.assertEqual(project, "")


class TestHookConfig(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_cursor_hooks_create(self):
        path = os.path.join(self.tmpdir, "hooks.json")
        merge_cursor_hooks(path, dry_run=False)
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("hooks", data)
        self.assertIn("afterFileEdit", data["hooks"])
        self.assertIn("stop", data["hooks"])

    def test_cursor_hooks_idempotent(self):
        path = os.path.join(self.tmpdir, "hooks.json")
        merge_cursor_hooks(path, dry_run=False)
        with open(path, "r", encoding="utf-8") as f:
            data1 = json.load(f)
        merge_cursor_hooks(path, dry_run=False)
        with open(path, "r", encoding="utf-8") as f:
            data2 = json.load(f)
        self.assertEqual(len(data1["hooks"]["afterFileEdit"]),
                         len(data2["hooks"]["afterFileEdit"]))

    def test_cursor_hooks_preserve_existing(self):
        path = os.path.join(self.tmpdir, "hooks.json")
        existing = {
            "version": 1,
            "hooks": {
                "afterFileEdit": [{"command": "python my_hook.py"}],
            },
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f)
        merge_cursor_hooks(path, dry_run=False)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        commands = [e.get("command", "") for e in data["hooks"]["afterFileEdit"]]
        self.assertIn("python my_hook.py", commands)
        self.assertTrue(any("trace-collector" in c for c in commands))

    def test_claude_settings_create(self):
        path = os.path.join(self.tmpdir, "settings.json")
        merge_claude_settings(path, dry_run=False)
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("PostToolUse", data["hooks"])
        self.assertIn("Stop", data["hooks"])

    def test_claude_settings_idempotent(self):
        path = os.path.join(self.tmpdir, "settings.json")
        merge_claude_settings(path, dry_run=False)
        merge_claude_settings(path, dry_run=False)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["hooks"]["Stop"]), 1)

    def test_corrupt_file_recreated(self):
        path = os.path.join(self.tmpdir, "hooks.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("NOT JSON")
        merge_cursor_hooks(path, dry_run=False)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("hooks", data)


class TestValidate(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_skill(self, name="test-skill", **overrides):
        skill_dir = os.path.join(self.tmpdir, name)
        os.makedirs(skill_dir, exist_ok=True)
        defaults = {
            "SKILL.md": "---\nname: test\ndescription: test skill\n---\n\n# Test\n",
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
        big_content = "---\nname: t\ndescription: t\n---\n\n" + "x " * 5000
        skill_dir = self._create_skill(**{"SKILL.md": big_content})
        errors, warnings, _ = validate_skill_dir(skill_dir)
        self.assertTrue(any("size" in w.lower() for w in warnings))

    def test_non_standard_structure_skipped(self):
        skill_dir = os.path.join(self.tmpdir, "odd-skill")
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "README.md"), "w") as f:
            f.write("# Not a standard skill\n")
        _, _, skipped = validate_skill_dir(skill_dir)
        self.assertTrue(skipped)

    def test_count_size_units_excludes_code(self):
        content = "Hello world\n```python\nlong code here\n```\nEnd.\n"
        size = _count_size_units(content)
        self.assertLess(size, 15)


class TestBackupSession(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.project_root = self.tmpdir

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_backup_creates_session_dir(self):
        session = BackupSession(self.project_root, enabled=True)
        src_file = os.path.join(self.project_root, "test.txt")
        with open(src_file, "w") as f:
            f.write("original")
        session.backup_original(src_file, dry_run=False)
        self.assertIsNotNone(session.session_dir)
        self.assertTrue(os.path.isdir(session.session_dir))

    def test_backup_disabled_returns_none(self):
        session = BackupSession(self.project_root, enabled=False)
        src_file = os.path.join(self.project_root, "test.txt")
        with open(src_file, "w") as f:
            f.write("original")
        result = session.backup_original(src_file, dry_run=False)
        self.assertIsNone(result)

    def test_backup_dry_run_returns_none(self):
        session = BackupSession(self.project_root, enabled=True)
        src_file = os.path.join(self.project_root, "test.txt")
        with open(src_file, "w") as f:
            f.write("original")
        result = session.backup_original(src_file, dry_run=True)
        self.assertIsNone(result)

    def test_backup_preserves_content(self):
        session = BackupSession(self.project_root, enabled=True)
        sub = os.path.join(self.project_root, "sub")
        os.makedirs(sub)
        src_file = os.path.join(sub, "data.txt")
        with open(src_file, "w") as f:
            f.write("important data")
        dest = session.backup_original(src_file, dry_run=False)
        self.assertIsNotNone(dest)
        with open(dest, "r") as f:
            self.assertEqual(f.read(), "important data")

    def test_rotate_keeps_n(self):
        backups_root = os.path.join(self.project_root, ".claude", ".backups")
        for i in range(5):
            d = os.path.join(backups_root, "2026-01-0{}_00-00-00".format(i + 1))
            os.makedirs(d)
            with open(os.path.join(d, "marker.txt"), "w") as f:
                f.write(str(i))
        rotate_backups(self.project_root, keep=2)
        remaining = os.listdir(backups_root)
        self.assertEqual(len(remaining), 2)
        self.assertIn("2026-01-05_00-00-00", remaining)
        self.assertIn("2026-01-04_00-00-00", remaining)


class TestIOOps(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_safe_write_creates_parents(self):
        path = os.path.join(self.tmpdir, "a", "b", "c.txt")
        safe_write(path, "content", "full", dry_run=False)
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(read_file(path), "content")

    def test_safe_write_skip_existing(self):
        path = os.path.join(self.tmpdir, "existing.txt")
        with open(path, "w") as f:
            f.write("old")
        result = safe_write(path, "new", "skip", dry_run=False)
        self.assertFalse(result)
        self.assertEqual(read_file(path), "old")

    def test_safe_write_full_overwrites(self):
        path = os.path.join(self.tmpdir, "existing.txt")
        with open(path, "w") as f:
            f.write("old")
        result = safe_write(path, "new", "full", dry_run=False)
        self.assertTrue(result)
        self.assertEqual(read_file(path), "new")

    def test_safe_write_dry_run(self):
        path = os.path.join(self.tmpdir, "new.txt")
        result = safe_write(path, "content", "full", dry_run=True)
        self.assertTrue(result)
        self.assertFalse(os.path.isfile(path))

    def test_safe_write_with_backup(self):
        session = BackupSession(self.tmpdir, enabled=True)
        path = os.path.join(self.tmpdir, "file.txt")
        with open(path, "w") as f:
            f.write("original")
        safe_write(path, "replaced", "full", dry_run=False, backup_session=session)
        self.assertEqual(read_file(path), "replaced")
        self.assertIsNotNone(session.session_dir)


if __name__ == "__main__":
    unittest.main()
