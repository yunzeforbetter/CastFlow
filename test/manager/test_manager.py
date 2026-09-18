#!/usr/bin/env python3
"""Config, evolution switch, seed/sync adapter projection."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

_CASTFLOW = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", ".castflow"
))
sys.path.insert(0, _CASTFLOW)

from manager import adapters, config, evolution, catalog
from manager.cli import USAGE
from manager.paths import runtime_dir, ensure_runtime_layout, find_harness_dir
from installer.validate import (
    description_shape_errors,
    extract_yaml_description,
    frontmatter_key_errors,
)


class TmpProject(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cf_mgr_")
        ensure_runtime_layout(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)


class TestEvolutionSwitch(TmpProject):
    def test_default_on(self):
        self.assertTrue(evolution.is_enabled(self.root))

    def test_toggle_persists(self):
        evolution.set_enabled(self.root, False)
        self.assertFalse(evolution.is_enabled(self.root))
        cfg = config.load_config(self.root)
        self.assertFalse(cfg["evolution"]["enabled"])
        evolution.set_enabled(self.root, True)
        self.assertTrue(evolution.is_enabled(self.root))


class TestSeedSync(TmpProject):
    def test_seed_writes_runtime_and_rules(self):
        adapters.seed(self.root)
        self.assertTrue(os.path.isfile(os.path.join(runtime_dir(self.root), "config.json")))
        self.assertTrue(os.path.isfile(os.path.join(self.root, "AGENTS.md")))
        self.assertTrue(os.path.isfile(os.path.join(self.root, "CLAUDE.md")))
        self.assertTrue(os.path.isdir(os.path.join(self.root, ".claude", "skills", "skill-creator")))
        self.assertTrue(os.path.isdir(os.path.join(self.root, ".agents", "skills", "skill-creator")))
        self.assertTrue(os.path.isfile(os.path.join(
            self.root, ".claude", "skills", "skill-creator", "SKILL.md")))
        self.assertTrue(os.path.isfile(os.path.join(
            self.root, ".agents", "skills", "skill-creator", "SKILL.md")))
        self.assertFalse(os.path.isdir(os.path.join(
            self.root, ".grok", "skills", "skill-creator")))
        self.assertFalse(os.path.isdir(os.path.join(
            self.root, ".cursor", "skills", "skill-creator")))
        self.assertTrue(os.path.isdir(os.path.join(
            runtime_dir(self.root), "skills", "skill-creator")))
        self.assertTrue(os.path.isdir(os.path.join(
            runtime_dir(self.root), "skills", "goal-loop-creator")))
        self.assertTrue(os.path.isfile(os.path.join(
            self.root, ".claude", "skills", "goal-loop-creator", "SKILL.md")))
        self.assertFalse(os.path.isdir(os.path.join(
            runtime_dir(self.root), "skills", "skill-forge")))
        self.assertTrue(os.path.isdir(os.path.join(
            runtime_dir(self.root), "skills", "skill-creator")))
        self.assertFalse(os.path.isdir(os.path.join(
            runtime_dir(self.root), "skills", "code-pipeline-skill")))
        self.assertFalse(os.path.isdir(os.path.join(
            self.root, ".claude", "skills", "code-pipeline-skill")))
        self.assertTrue(os.path.isfile(os.path.join(
            runtime_dir(self.root), "rules", "cross-cutting.md")))
        with open(os.path.join(self.root, "CLAUDE.md"), encoding="utf-8") as f:
            claude = f.read()
        self.assertNotIn("<!-- if:evolution -->", claude)
        self.assertNotIn("<!-- if:no-evolution -->", claude)
        self.assertIn(".castflow-runtime/memory/", claude)
        self.assertIn("must not Read `.castflow-runtime/traces/trace.md`", claude)
        self.assertIn("ROOT_RULES.template.md", claude)
        self.assertNotIn("CLAUDE.template.md", claude)
        mdc = os.path.join(self.root, ".cursor", "rules", "evolve-reminder.mdc")
        self.assertTrue(os.path.isfile(mdc))
        with open(mdc, encoding="utf-8") as f:
            mdc_text = f.read()
        self.assertIn("alwaysApply: true", mdc_text)
        gitignore = os.path.join(self.root, ".gitignore")
        self.assertTrue(os.path.isfile(gitignore))
        with open(gitignore, encoding="utf-8") as f:
            ignore_text = f.read()
        self.assertIn("# BEGIN CASTFLOW GITIGNORE", ignore_text)
        self.assertIn(".claude/skills/", ignore_text)
        self.assertIn(".agents/skills/", ignore_text)
        self.assertIn(".castflow-runtime/skills-disabled.json", ignore_text)
        rules = [
            ln.strip() for ln in ignore_text.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        self.assertIn(".castflow-runtime/skills-disabled.json", rules)
        self.assertNotIn(".castflow-runtime/skills/", rules)
        self.assertNotIn(".castflow-runtime/", rules)

    def test_evolve_off_removes_hooks_and_origin_evolve(self):
        adapters.seed(self.root)
        grok_hook = os.path.join(self.root, ".grok", "hooks", "castflow.json")
        self.assertTrue(os.path.isfile(grok_hook))
        self.assertTrue(os.path.isdir(os.path.join(
            runtime_dir(self.root), "skills", "origin-evolve-skill")))
        evolution.set_enabled(self.root, False, sync_fn=adapters.sync)
        self.assertFalse(os.path.isfile(grok_hook))
        self.assertFalse(os.path.isdir(os.path.join(
            runtime_dir(self.root), "skills", "origin-evolve-skill")))
        with open(os.path.join(self.root, "AGENTS.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("evolution plugin OFF", text)
        self.assertNotIn("evolution plugin ON", text)
        self.assertFalse(os.path.isdir(os.path.join(
            self.root, ".claude", "skills", "origin-evolve-skill")))

    def test_claude_settings_has_hooks_when_on(self):
        adapters.seed(self.root)
        path = os.path.join(self.root, ".claude", "settings.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("PostToolUse", data.get("hooks") or {})
        self.assertIn("trace-collector.py", json.dumps(data))
        blob = json.dumps(data)
        self.assertIn(".castflow-runtime/hooks/trace-collector.py", blob.replace("\\\\", "/"))

    def test_hook_scripts_absolute_when_castflow_outside_project(self):
        cmds = adapters.hook_commands(self.root)
        collector = cmds["collector_rel"].replace("/", os.sep)
        self.assertFalse(cmds["collector_rel"].startswith(".."))
        self.assertTrue(os.path.isfile(collector), collector)
        harness_script = os.path.join(
            find_harness_dir(), "core", "hooks", "trace-collector.py")
        self.assertEqual(
            os.path.normcase(os.path.abspath(collector)),
            os.path.normcase(os.path.abspath(harness_script)),
        )


class TestProjectionGitignore(TmpProject):
    def test_upsert_appends_and_preserves_user_rules(self):
        existing = "node_modules/\n*.log\n"
        updated = adapters.upsert_gitignore_block(existing)
        self.assertIn("node_modules/", updated)
        self.assertIn("*.log", updated)
        self.assertIn(".claude/skills/", updated)
        self.assertIn(".agents/skills/", updated)
        self.assertIn(".grok/skills/", updated)
        self.assertIn(".cursor/skills/", updated)
        self.assertEqual(updated.count(adapters.GITIGNORE_BEGIN), 1)
        self.assertTrue(updated.endswith("\n"))

    def test_upsert_replaces_managed_block_only(self):
        existing = (
            "node_modules/\n\n"
            "# BEGIN CASTFLOW GITIGNORE (managed - do not edit)\n"
            ".old-skill-path/\n"
            "# END CASTFLOW GITIGNORE\n"
            "*.log\n"
        )
        updated = adapters.upsert_gitignore_block(existing)
        self.assertIn("node_modules/", updated)
        self.assertIn("*.log", updated)
        self.assertIn(".claude/skills/", updated)
        self.assertNotIn(".old-skill-path/", updated)
        self.assertEqual(updated.count(adapters.GITIGNORE_BEGIN), 1)

    def test_upsert_idempotent(self):
        once = adapters.upsert_gitignore_block("")
        twice = adapters.upsert_gitignore_block(once)
        self.assertEqual(once, twice)

    def test_upsert_preserves_crlf(self):
        existing = "foo\r\n"
        updated = adapters.upsert_gitignore_block(existing)
        self.assertTrue(updated.startswith("foo\r\n"))
        self.assertIn(".claude/skills/\r\n", updated)
        self.assertEqual(updated.count("\n"), updated.count("\r\n"))

    def test_sync_writes_gitignore_idempotent(self):
        adapters.sync(self.root)
        path = os.path.join(self.root, ".gitignore")
        with open(path, encoding="utf-8") as f:
            first = f.read()
        report = adapters.sync(self.root)
        with open(path, encoding="utf-8") as f:
            second = f.read()
        self.assertEqual(first, second)
        self.assertFalse(report.get("gitignore", {}).get("changed"))

    def test_dry_run_does_not_write_gitignore(self):
        adapters.sync(self.root, dry_run=True)
        self.assertFalse(os.path.isfile(os.path.join(self.root, ".gitignore")))

    def test_sync_untracks_indexed_projection_paths(self):
        git = shutil.which("git")
        if not git:
            self.skipTest("git not available")
        tracked = os.path.join(self.root, ".claude", "skills", "already-tracked", "SKILL.md")
        os.makedirs(os.path.dirname(tracked))
        with open(tracked, "w", encoding="utf-8") as f:
            f.write("tracked-by-mistake\n")
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = "CastFlow Test"
        env["GIT_AUTHOR_EMAIL"] = "castflow@test"
        env["GIT_COMMITTER_NAME"] = "CastFlow Test"
        env["GIT_COMMITTER_EMAIL"] = "castflow@test"
        env["GIT_TERMINAL_PROMPT"] = "0"
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        def run(args):
            subprocess.check_call(
                [git, "-C", self.root] + args,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags if os.name == "nt" else 0,
            )

        run(["init"])
        run(["add", "-f", ".claude/skills/already-tracked/SKILL.md"])
        run(["-c", "commit.gpgsign=false", "commit", "-m", "track projection"])
        listed = subprocess.check_output(
            [git, "-C", self.root, "ls-files", "--", ".claude/skills"],
            env=env,
            creationflags=flags if os.name == "nt" else 0,
        )
        self.assertIn(b"already-tracked", listed)
        report = adapters.sync(self.root)
        listed_after = subprocess.check_output(
            [git, "-C", self.root, "ls-files", "--", ".claude/skills", ".agents/skills"],
            env=env,
            creationflags=flags if os.name == "nt" else 0,
        )
        self.assertEqual(listed_after.strip(), b"")
        self.assertTrue(os.path.isdir(os.path.join(
            self.root, ".claude", "skills", "skill-creator")))
        self.assertFalse(os.path.isfile(tracked))
        removed = report.get("untracked", {}).get("removed") or []
        self.assertTrue(any("already-tracked" in p.replace("\\", "/") for p in removed))


class TestCollectorRuntimeMemory(unittest.TestCase):
    def test_runtime_memory_path_is_captured(self):
        hooks = os.path.join(_CASTFLOW, "core", "hooks")
        sys.path.insert(0, hooks)
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "collector_mod", os.path.join(hooks, "trace-collector.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue(mod._is_memory_file(
            r"C:\proj\.castflow-runtime\memory\ordered-insert.md"))
        self.assertFalse(mod._is_memory_file(
            r"C:\proj\.castflow-runtime\memory\MEMORY.md"))
        self.assertFalse(mod._is_memory_file(r"C:\proj\src\app.py"))


class TestHarnessDropsProvenDeadFiles(unittest.TestCase):
    """Seeded projects must not depend on files that have no loader."""

    def test_orphans_absent_and_root_rules_still_render(self):
        harness = find_harness_dir()
        self.assertTrue(os.path.isfile(os.path.join(
            harness, "core", "templates", "root", "ROOT_RULES.template.md")))
        self.assertFalse(os.path.isfile(os.path.join(
            harness, "core", "CLAUDE.template.md")))
        self.assertFalse(os.path.isfile(os.path.join(
            harness, "installer", "placeholders.py")))
        text = adapters._render_root_rules(True)
        self.assertIn("ROOT_RULES.template.md", text)
        self.assertIn(".castflow-runtime/skills/", text)
        self.assertNotIn("CLAUDE.template.md", text)

    def test_manager_usage_lists_live_commands_not_scan(self):
        for cmd in ("launch", "seed", "sync", "validate", "ui"):
            self.assertIn("manager.py " + cmd, USAGE)
        self.assertNotIn("manager.py scan", USAGE)

    def test_bootstrap_wrapper_does_not_advertise_scan(self):
        path = os.path.join(find_harness_dir(), "bootstrap.py")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("manager.py scan", text)
        self.assertIn("manager.py launch", text)


class TestSkillRecallDescriptions(unittest.TestCase):
    """Live YAML must pass shipped installer.validate description checks."""

    ROOT = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", ".."))

    def _read(self, *parts):
        path = os.path.join(self.ROOT, *parts)
        with open(path, encoding="utf-8") as f:
            return f.read()

    def _assert_recall(self, skill_name, *parts):
        text = self._read(*parts)
        self.assertTrue(text.lstrip().startswith("---"), parts)
        self.assertEqual(frontmatter_key_errors(text), [], parts)
        desc = extract_yaml_description(text)
        self.assertEqual(
            description_shape_errors(desc, skill_name=skill_name),
            [],
            parts,
        )

    def test_live_skills(self):
        self._assert_recall(
            "origin-evolve-skill",
            ".castflow", "core", "skills", "origin-evolve-skill", "SKILL.md")
        self._assert_recall(
            "skill-creator",
            ".castflow", "core", "skills", "skill-creator", "SKILL.md")
        self._assert_recall(
            "goal-loop-creator",
            ".castflow", "core", "skills", "goal-loop-creator", "SKILL.md")
        self._assert_recall(
            "skill-iteration",
            ".castflow", "core", "skills", "SKILL_ITERATION.md")
        creator = self._read(
            ".castflow", "core", "skills", "skill-creator", "SKILL.md")
        self.assertNotIn("skill-forge", creator)
        self.assertIn("castflow generate skills", creator.lower())

    def test_templates(self):
        iteration = self._read(
            ".castflow", "core", "skills", "SKILL_ITERATION.md")
        self.assertIn("Use when the user names", iteration)
        self.assertIn("NOT other programmer-*-skill", iteration)
        self.assertNotIn("programmer.template", iteration)
        self.assertNotIn("bootstrap-assets", iteration)
        self.assertIn("architect-skill", iteration)
        self.assertIn("which layer a change belongs in", iteration)
        self.assertIn("null, race, or crash", iteration)
        self.assertIn("hot path is slow", iteration)
        assets = os.path.join(
            self.ROOT, ".castflow", "bootstrap-assets")
        self.assertFalse(os.path.isdir(assets), assets)


class TestSkillIterationMetaSpec(unittest.TestCase):
    """Shipped SKILL_ITERATION.md must keep T4 contracts and drop theater."""

    ROOT = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", ".."))

    def _text(self):
        path = os.path.join(
            self.ROOT, ".castflow", "core", "skills", "SKILL_ITERATION.md")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_required_contracts_present(self):
        text = self._text()
        self.assertIn("SKILL.md", text)
        self.assertIn("EXAMPLES.md", text)
        self.assertIn("SKILL_MEMORY.md", text)
        self.assertIn("ITERATION_GUIDE.md", text)
        self.assertIn(".castflow-runtime/skills/", text)
        self.assertIn("python .castflow-runtime/manager.py validate", text)
        self.assertIn("Anchors", text)
        self.assertIn("Merge", text)
        self.assertIn("Retire", text)
        self.assertRegex(text, r"Use when|当用户")
        self.assertIn("NOT", text)

    def test_theater_strings_absent(self):
        text = self._text()
        for banned in (
            "工作无效",
            "wc -w",
            "300-500",
            "规范检查命令集",
        ):
            self.assertNotIn(banned, text, banned)


if __name__ == "__main__":
    unittest.main()
