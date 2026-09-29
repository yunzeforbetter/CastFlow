#!/usr/bin/env python3
"""Cold-start GUI/setup: config + seed without a Python module scanner."""

from __future__ import print_function

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

try:
    from http.server import ThreadingHTTPServer
except ImportError:  # pragma: no cover
    from http.server import HTTPServer
    from socketserver import ThreadingMixIn

    class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True

try:
    from urllib.request import Request, urlopen
except ImportError:  # pragma: no cover
    from urllib2 import Request, urlopen  # type: ignore

_REPO = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".."))
_CASTFLOW = os.path.join(_REPO, ".castflow")
sys.path.insert(0, _CASTFLOW)

from manager import adapters, config, queue, setup, skills
from manager.paths import FactoryRuntimeError, factory_root, runtime_dir
from manager.cli import main as manager_main
from manager.ui.server import STATIC_DIR, _state, make_handler


def _write(path, content):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _mini_project(root):
    _write(os.path.join(root, "pyproject.toml"), "[project]\nname='demo'\n")
    for name in ("billing", "inventory"):
        for i in range(4):
            _write(
                os.path.join(root, "src", name, "m{}.py".format(i)),
                "class {}{}:\n    pass\n".format(name.title(), i),
            )
        _write(
            os.path.join(root, "src", name, "README.md"),
            "# {}\n\nOwns {} in this app.\n".format(name, name),
        )


class TmpProject(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cf_setup_")
        _mini_project(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)


class TestColdStart(TmpProject):
    def test_unseeded_then_setup_applies_gui_choices(self):
        self.assertFalse(setup.is_seeded(self.root))
        report = setup.cold_start(self.root, {
            "language": "en",
            "adapters": {
                "claude": True,
                "grok": True,
                "codex": True,
                "cursor": False,
            },
            "evolution": {"enabled": False},
            "optional_skills": {
                "architect": True,
                "debug": True,
                "profiler": False,
            },
        })
        self.assertTrue(report.get("ok"))
        self.assertTrue(setup.is_seeded(self.root))
        cfg = config.load_config(self.root)
        self.assertEqual(cfg["language"], "en")
        self.assertFalse(cfg["adapters"]["cursor"])
        self.assertFalse(cfg["evolution"]["enabled"])
        self.assertTrue(cfg["optional_skills"]["debug"])
        self.assertTrue(os.path.isdir(os.path.join(
            runtime_dir(self.root), "skills", "skill-creator")))
        self.assertTrue(os.path.isfile(os.path.join(
            self.root, ".claude", "skills", "skill-creator", "SKILL.md")))
        self.assertFalse(os.path.isdir(os.path.join(self.root, ".cursor", "skills")))
        self.assertFalse(os.path.isdir(os.path.join(
            self.root, ".claude", "skills", "origin-evolve-skill")))
        self.assertFalse(report.get("generate_skills"))
        self.assertEqual(report.get("handoff") or "", "")

    def test_handoff_install_only_unless_generate_requested(self):
        report = setup.cold_start(self.root, {"language": "zh"})
        self.assertFalse(report.get("generate_skills"))
        self.assertEqual(report.get("queued"), 0)
        text = report.get("handoff") or ""
        self.assertEqual(text, "")
        q = queue.load_queue(self.root)
        self.assertEqual(q.get("items") or [], [])

        report2 = setup.cold_start(self.root, {
            "language": "zh",
            "generate_skills": True,
            "optional_skills": {
                "architect": False, "debug": False, "profiler": False,
            },
        })
        self.assertTrue(report2.get("generate_skills"))
        scan_text = report2.get("handoff") or ""
        self.assertEqual(
            scan_text,
            "/goal 读取并按照 .castflow-runtime/skills/"
            "MODULE_MARK_SYSTEM_PROMPT.md 执行。"
            "跟用户说话用 zh：多选的问题和每项说明用中文。"
            "模块 id 保持原样。技能正文仍按卡上的 language。",
        )
        self.assertNotIn("\n", scan_text)
        copied = os.path.join(
            runtime_dir(self.root), "skills",
            "MODULE_MARK_SYSTEM_PROMPT.md")
        self.assertTrue(os.path.isfile(copied))
        copied_text = _read(copied)
        self.assertIn(".castflow-runtime/", copied_text)
        self.assertIn("never in the multi-select", copied_text)
        self.assertIn("CastFlow/", copied_text)
        self.assertIn("_skill-gen-queue", copied_text)
        self.assertIn("only 1 skill at a time", copied_text)

        custom = "只扫 src/billing，生成 programmer-billing-skill"
        report3 = setup.cold_start(self.root, {
            "language": "zh",
            "generate_skills": True,
            "generate_prompt": custom,
            "optional_skills": {
                "architect": False, "debug": False, "profiler": False,
            },
        })
        self.assertEqual(report3.get("handoff"), custom)

    def test_unseed_keeps_agents_project_section_and_import_notes(self):
        setup.cold_start(self.root, {"language": "en"})
        agents_path = os.path.join(self.root, "AGENTS.md")
        claude_path = os.path.join(self.root, "CLAUDE.md")
        with open(agents_path, encoding="utf-8") as f:
            agents = f.read()
        agents = agents.replace(
            "Add team conventions below.",
            "Add team conventions below.\n\nKeep this note.",
            1,
        )
        _write(agents_path, agents)
        _write(claude_path, "@AGENTS.md\n\nPlan mode for billing.\n")
        report = setup.unseed(self.root)
        self.assertTrue(report.get("ok"))
        with open(agents_path, encoding="utf-8") as f:
            kept = f.read()
        self.assertIn("Keep this note.", kept)
        self.assertNotIn("ROOT_RULES.template.md", kept)
        self.assertNotIn("This file is generated from CastFlow", kept)
        with open(claude_path, encoding="utf-8") as f:
            claude = f.read()
        self.assertNotIn("@AGENTS.md", claude)
        self.assertIn("Plan mode for billing.", claude)

    def test_unseed_allows_cold_start_again(self):
        setup.cold_start(self.root, {"language": "zh"})
        self.assertTrue(setup.is_seeded(self.root))
        self.assertTrue(os.path.isfile(os.path.join(self.root, "CLAUDE.md")))
        self.assertTrue(os.path.isdir(os.path.join(
            self.root, ".claude", "skills", "skill-creator")))
        with open(os.path.join(self.root, "CLAUDE.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "@AGENTS.md\n")
        report = setup.unseed(self.root)
        self.assertFalse(os.path.isfile(os.path.join(self.root, "CLAUDE.md")))
        self.assertFalse(os.path.isfile(os.path.join(self.root, "AGENTS.md")))
        self.assertTrue(report.get("ok"))
        self.assertFalse(setup.is_seeded(self.root))
        self.assertFalse(os.path.isdir(runtime_dir(self.root)))
        for name in ("castflow.bat", "castflow.sh", "castflow.command"):
            self.assertFalse(os.path.isfile(os.path.join(self.root, name)))
        self.assertFalse(os.path.isdir(os.path.join(
            self.root, ".claude", "skills", "skill-creator")))

    def test_unseed_via_runtime_manager_removes_launchers(self):
        """Project castflow.bat runs the copy under .castflow-runtime."""
        setup.cold_start(self.root, {"language": "en"})
        runtime_py = os.path.join(runtime_dir(self.root), "manager.py")
        self.assertTrue(os.path.isfile(runtime_py))
        self.assertTrue(os.path.isfile(os.path.join(self.root, "castflow.bat")))
        proc = subprocess.run(
            [sys.executable, runtime_py, "--project-root", self.root, "unseed"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("manager.bundle", proc.stderr)
        self.assertFalse(os.path.isdir(runtime_dir(self.root)))
        for name in ("castflow.bat", "castflow.sh", "castflow.command"):
            self.assertFalse(
                os.path.isfile(os.path.join(self.root, name)), name)
        again = setup.cold_start(self.root, {
            "language": "en",
            "generate_skills": True,
        })
        self.assertTrue(setup.is_seeded(self.root))
        self.assertTrue(again.get("generate_skills"))
        again_text = again.get("handoff") or ""
        self.assertTrue(again_text.startswith("/goal "))
        self.assertIn(
            ".castflow-runtime/skills/MODULE_MARK_SYSTEM_PROMPT.md",
            again_text,
        )
        self.assertNotIn("\n", again_text)

    def test_unseed_cold_start_keeps_project_skill_and_refreshes_factory(self):
        """Winner C: project bytes sit outside the wipe; factory files are replaced."""
        from installer.validate import validate_all, validate_skill_dir

        setup.cold_start(self.root, {"language": "en"})
        name = "programmer-billing-skill"
        body = (
            "---\nname: programmer-billing-skill\n"
            "description: Change billing in this repo. "
            "Use when the user names billing. NOT work outside billing.\n"
            "---\n\n# billing\n"
        )
        memory = "### Rule 1: keep\n\nDefinition\nDo not drop the id.\n"
        first = skills.write_project_skill(self.root, name, {"SKILL.md": body})
        self.assertTrue(first.get("ok"), first)
        second = skills.write_project_skill(
            self.root, name, {"SKILL_MEMORY.md": memory})
        self.assertTrue(second.get("ok"), second)
        skill_dir = skills.project_skill_dir(self.root, name)
        skill_md = os.path.join(skill_dir, "SKILL.md")
        memory_md = os.path.join(skill_dir, "SKILL_MEMORY.md")
        self.assertEqual(_read(skill_md), body)
        self.assertEqual(_read(memory_md), memory)

        notes_name = "notes-skill"
        notes = (
            "---\nname: notes-skill\n"
            "description: Project notes. Use when the user asks for notes. "
            "NOT module API how-to.\n"
            "---\n\nKeep a short project note.\n"
        )
        noted = skills.write_project_skill(
            self.root, notes_name, {"SKILL.md": notes})
        self.assertTrue(noted.get("ok"), noted)
        rejected = skills.write_project_skill(
            self.root, "skill-creator", {"SKILL.md": "nope\n"})
        self.assertFalse(rejected.get("ok"))
        self.assertEqual(rejected.get("error"), "factory-owned")

        factory_skill = os.path.join(
            _CASTFLOW, "core", "skills", "skill-creator", "SKILL.md")
        factory_loose = os.path.join(
            _CASTFLOW, "core", "skills", "SKILL_ITERATION.md")
        runtime_skill = os.path.join(
            runtime_dir(self.root), "skills", "skill-creator", "SKILL.md")
        runtime_loose = os.path.join(
            runtime_dir(self.root), "skills", "SKILL_ITERATION.md")
        with open(runtime_skill, "a", encoding="utf-8", newline="\n") as handle:
            handle.write("\n<!-- mutated-by-test -->\n")
        with open(runtime_loose, "a", encoding="utf-8", newline="\n") as handle:
            handle.write("\n<!-- mutated-loose -->\n")
        shadow = os.path.join(self.root, "castflow-skills", "skill-creator")
        _write(os.path.join(shadow, "SKILL.md"), "shadow skill\n")
        _write(os.path.join(shadow, "EXTRA.txt"), "extra\n")

        setup.cold_start(self.root, {"language": "en"})
        self.assertEqual(_read(skill_md), body)
        self.assertEqual(_read(memory_md), memory)
        self.assertEqual(_read(runtime_skill), _read(factory_skill))
        self.assertEqual(_read(runtime_loose), _read(factory_loose))

        setup.unseed(self.root)
        self.assertFalse(os.path.isdir(runtime_dir(self.root)))
        self.assertEqual(_read(skill_md), body)
        self.assertEqual(_read(memory_md), memory)
        self.assertEqual(_read(os.path.join(shadow, "EXTRA.txt")), "extra\n")

        setup.cold_start(self.root, {"language": "en"})
        self.assertEqual(_read(skill_md), body)
        self.assertEqual(_read(memory_md), memory)
        self.assertEqual(_read(runtime_skill), _read(factory_skill))
        self.assertEqual(_read(runtime_loose), _read(factory_loose))
        self.assertFalse(os.path.isdir(os.path.join(
            runtime_dir(self.root), "skills", name)))

        rows = skills.inventory(self.root)
        names = [row["name"] for row in rows]
        self.assertEqual(names.count(name), 1)
        self.assertEqual(names.count("skill-creator"), 1)
        self.assertEqual(names.count(notes_name), 1)
        by_name = dict((row["name"], row) for row in rows)
        self.assertEqual(
            by_name["skill-creator"].get("collision"),
            "ignored-project-shadow",
        )
        self.assertTrue(by_name["skill-creator"]["body_path"].replace(
            "\\", "/").endswith(".castflow-runtime/skills/skill-creator"))
        self.assertTrue(by_name[name]["body_path"].replace(
            "\\", "/").endswith("castflow-skills/" + name))

        adapters.sync(self.root)
        factory_text = _read(factory_skill)
        for rel in (
            os.path.join(".claude", "skills"),
            os.path.join(".agents", "skills"),
        ):
            projected = os.path.join(self.root, rel, "skill-creator")
            self.assertFalse(os.path.isfile(os.path.join(projected, "EXTRA.txt")))
            self.assertEqual(_read(os.path.join(projected, "SKILL.md")), factory_text)
            self.assertEqual(
                _read(os.path.join(self.root, rel, name, "SKILL.md")), body)
            self.assertEqual(os.listdir(os.path.join(self.root, rel)).count(name), 1)
            self.assertEqual(
                os.listdir(os.path.join(self.root, rel)).count("skill-creator"), 1)
        for host in ("grok", "cursor"):
            base = os.path.join(self.root, "." + host, "skills")
            self.assertFalse(os.path.lexists(os.path.join(base, name)))
            self.assertFalse(os.path.lexists(os.path.join(base, "skill-creator")))

        errors, _warnings, skipped = validate_skill_dir(
            skills.resolve_skill_dir(self.root, notes_name))
        self.assertFalse(skipped)
        self.assertEqual(errors, [])
        self.assertTrue(skills.retire(self.root, notes_name).get("ok"))
        adapters.sync(self.root)
        self.assertFalse(os.path.isdir(os.path.join(
            self.root, ".claude", "skills", notes_name)))
        self.assertFalse(os.path.isdir(os.path.join(
            self.root, ".agents", "skills", notes_name)))
        self.assertEqual(_read(os.path.join(
            skills.project_skill_dir(self.root, notes_name), "SKILL.md")), notes)
        self.assertTrue(skills.restore(self.root, notes_name).get("ok"))
        adapters.sync(self.root)
        self.assertTrue(os.path.isfile(os.path.join(
            self.root, ".claude", "skills", notes_name, "SKILL.md")))
        self.assertIn(notes_name, [
            row["name"] for row in skills.inventory(self.root)])
        import io
        from contextlib import redirect_stdout
        captured = io.StringIO()
        with redirect_stdout(captured):
            validate_all(self.root)
        self.assertIn("[PASS]   notes-skill", captured.getvalue())

    def test_update_framework_refreshes_core_skill(self):
        setup.cold_start(self.root, {"optional_skills": {"architect": False}})
        runtime_md = os.path.join(
            runtime_dir(self.root), "skills", "skill-creator", "SKILL.md")
        with open(runtime_md, "a", encoding="utf-8", newline="\n") as f:
            f.write("\n<!-- mutated-by-test -->\n")
        report = setup.update_framework(self.root)
        self.assertTrue(report.get("ok"))
        self.assertIn("skill-creator", report.get("updated") or [])
        text = _read(runtime_md)
        self.assertNotIn("mutated-by-test", text)
        self.assertTrue(os.path.isfile(os.path.join(
            self.root, ".claude", "skills", "skill-creator", "SKILL.md")))
        runtime_setup = os.path.join(
            runtime_dir(self.root), "manager", "setup.py")
        with open(runtime_setup, "a", encoding="utf-8", newline="\n") as f:
            f.write("\n# mutated-manager\n")
        setup.update_framework(self.root)
        self.assertNotIn("mutated-manager", _read(runtime_setup))
        self.assertIn("remove_project_launchers", _read(runtime_setup))

    def test_cli_setup_seeds_without_scan(self):
        rc = manager_main(["--project-root", self.root, "setup", "--language", "ja"])
        self.assertEqual(rc, 0)
        self.assertTrue(setup.is_seeded(self.root))
        self.assertEqual(config.load_config(self.root)["language"], "ja")
        self.assertTrue(os.path.isfile(os.path.join(
            runtime_dir(self.root), "skills", "skill-creator", "SKILL.md")))

    def _assert_factory_clean(self, factory):
        for name in (
            ".castflow-runtime", ".claude", ".agents", ".cursor", ".grok",
        ):
            self.assertFalse(
                os.path.isdir(os.path.join(factory, name)),
                "factory still has {}".format(name),
            )
        for name in ("CLAUDE.md", "AGENTS.md"):
            self.assertFalse(
                os.path.isfile(os.path.join(factory, name)),
                "factory still has {}".format(name),
            )

    def test_seed_refuses_factory_and_scrubs_leftover_runtime(self):
        factory = factory_root()
        leftover = os.path.join(factory, ".castflow-runtime", "stale")
        os.makedirs(leftover, exist_ok=True)
        _write(os.path.join(leftover, "marker.txt"), "stale\n")
        os.makedirs(os.path.join(factory, ".claude", "skills"), exist_ok=True)
        os.makedirs(os.path.join(factory, ".agents", "skills"), exist_ok=True)
        with self.assertRaises(FactoryRuntimeError):
            adapters.seed(factory)
        self._assert_factory_clean(factory)
        rc = manager_main(["--project-root", factory, "seed"])
        self.assertEqual(rc, 2)
        self._assert_factory_clean(factory)

    def test_seed_target_scrubs_factory_runtime(self):
        factory = factory_root()
        leftover = os.path.join(factory, ".castflow-runtime", "stale")
        os.makedirs(leftover, exist_ok=True)
        _write(os.path.join(leftover, "marker.txt"), "stale\n")
        os.makedirs(os.path.join(factory, ".claude", "skills"), exist_ok=True)
        os.makedirs(os.path.join(factory, ".cursor", "skills"), exist_ok=True)
        _write(os.path.join(factory, ".grok", "hooks", "x.json"), "{}\n")
        adapters.seed(self.root)
        self._assert_factory_clean(factory)
        self.assertTrue(os.path.isfile(os.path.join(
            runtime_dir(self.root), "skills", "skill-creator", "SKILL.md")))
        self.assertTrue(os.path.isdir(os.path.join(
            self.root, ".claude", "skills", "skill-creator")))
        self.assertFalse(os.path.isdir(os.path.join(factory, ".claude")))


class TestLaunchRoot(unittest.TestCase):
    def test_submodule_uses_parent_project(self):
        parent = tempfile.mkdtemp(prefix="cf_host_")
        self.addCleanup(lambda: shutil.rmtree(parent, ignore_errors=True))
        checkout = os.path.join(parent, "CastFlow")
        os.makedirs(os.path.join(checkout, ".castflow"))
        _write(os.path.join(checkout, ".castflow", "manager.py"), "")
        _write(os.path.join(checkout, ".git"), "gitdir: ../.git/modules/CastFlow\n")
        root = setup.resolve_launch_root(harness_checkout=checkout)
        self.assertEqual(os.path.normpath(root), os.path.normpath(parent))

    def test_full_clone_stays_in_checkout(self):
        checkout = tempfile.mkdtemp(prefix="cf_clone_")
        self.addCleanup(lambda: shutil.rmtree(checkout, ignore_errors=True))
        os.makedirs(os.path.join(checkout, ".castflow"))
        _write(os.path.join(checkout, ".castflow", "manager.py"), "")
        os.makedirs(os.path.join(checkout, ".git"))
        root = setup.resolve_launch_root(
            harness_checkout=checkout, start=checkout)
        self.assertEqual(os.path.normpath(root), os.path.normpath(checkout))

    def test_nested_clone_uses_host_game(self):
        parent = tempfile.mkdtemp(prefix="cf_game_")
        self.addCleanup(lambda: shutil.rmtree(parent, ignore_errors=True))
        os.makedirs(os.path.join(parent, "Assets", "Scripts"))
        checkout = os.path.join(parent, "CastFlow")
        os.makedirs(os.path.join(checkout, ".castflow"))
        _write(os.path.join(checkout, ".castflow", "manager.py"), "")
        os.makedirs(os.path.join(checkout, ".git"))
        root = setup.resolve_launch_root(harness_checkout=checkout)
        self.assertEqual(os.path.normpath(root), os.path.normpath(parent))

    def test_explicit_root_wins(self):
        chosen = tempfile.mkdtemp(prefix="cf_explicit_")
        self.addCleanup(lambda: shutil.rmtree(chosen, ignore_errors=True))
        root = setup.resolve_launch_root(
            explicit=chosen, harness_checkout=r"C:\not-used")
        self.assertEqual(os.path.normpath(root), os.path.normpath(chosen))


class TestBatLauncher(unittest.TestCase):
    def test_bat_invokes_manager_launch(self):
        bat = os.path.join(_REPO, "castflow.bat")
        self.assertTrue(os.path.isfile(bat))
        text = _read(bat)
        self.assertIn(".castflow\\manager.py", text)
        self.assertIn("launch", text)
        self.assertIn("--from-harness", text)
        self.assertIn("py -3", text)
        self.assertIn("%MANAGER%", text)
        # cmd.exe parses .bat as the OEM code page; keep the file ASCII.
        try:
            text.encode("ascii")
        except UnicodeEncodeError:
            self.fail("castflow.bat must be ASCII-only so cmd.exe does not split lines")
        self.assertIn("开启冷启动", setup.LAUNCH_GUIDE)
        self.assertIn("optional", setup.LAUNCH_GUIDE.lower())
        self.assertIn("[1]", setup.LAUNCH_GUIDE)
        self.assertIn("[4]", setup.LAUNCH_GUIDE)

    def test_posix_launchers_invoke_manager_launch(self):
        sh = os.path.join(_REPO, "castflow.sh")
        command = os.path.join(_REPO, "castflow.command")
        self.assertTrue(os.path.isfile(sh))
        self.assertTrue(os.path.isfile(command))
        text = _read(sh)
        wrapper = _read(command)
        self.assertTrue(text.startswith("#!/usr/bin/env bash"))
        with open(sh, "rb") as f:
            self.assertNotIn(b"\r", f.read())
        with open(command, "rb") as f:
            self.assertNotIn(b"\r", f.read())
        try:
            text.encode("ascii")
            wrapper.encode("ascii")
        except UnicodeEncodeError:
            self.fail("POSIX launchers must stay ASCII")
        self.assertIn(".castflow/manager.py", text)
        self.assertIn("launch", text)
        self.assertIn("--from-harness", text)
        self.assertIn("python3", text)
        self.assertIn("castflow.sh", wrapper)
        from manager.pick_dir import darwin_choose_folder_script
        script = darwin_choose_folder_script("/tmp", 'Select "folder"')
        self.assertIn("choose folder", script)
        self.assertIn('Select \\"folder\\"', script)


class TestJevModuleInstall(TmpProject):
    def test_checkbox_syncs_module_and_keeps_key_out_of_git_config(self):
        secret = "project-local-key-abc"
        off = setup.cold_start(self.root, {"language": "zh", "jev_enabled": False})
        self.assertFalse(off.get("jev_enabled"))
        self.assertFalse(os.path.isdir(os.path.join(runtime_dir(self.root), "jev")))
        report = setup.cold_start(self.root, {
            "language": "zh",
            "jev_enabled": True,
            "jev_key": secret,
        })
        self.assertTrue(report.get("jev_enabled"))
        module = os.path.join(runtime_dir(self.root), "jev")
        self.assertTrue(os.path.isfile(os.path.join(module, "mark.py")))
        self.assertTrue(os.path.isfile(os.path.join(module, "__init__.py")))
        env_file = os.path.join(runtime_dir(self.root), "secrets.env")
        from manager.envfile import get, set_key
        self.assertEqual(get(self.root, "TYPESAFE_API_KEY"), secret)
        self.assertTrue(set_key(self.root, "OTHER_API_KEY", "second-key-value"))
        self.assertEqual(get(self.root, "TYPESAFE_API_KEY"), secret)
        self.assertEqual(get(self.root, "OTHER_API_KEY"), "second-key-value")
        with open(env_file, encoding="utf-8") as handle:
            env_body = handle.read()
        self.assertIn("TYPESAFE_API_KEY=" + secret, env_body)
        self.assertIn("OTHER_API_KEY=second-key-value", env_body)
        with open(os.path.join(runtime_dir(self.root), "config.json"), encoding="utf-8") as handle:
            raw = handle.read()
        self.assertNotIn(secret, raw)
        self.assertNotIn("TYPESAFE_API_KEY", raw)
        self.assertIn('"jev_enabled": true', raw)
        gitignore = open(os.path.join(self.root, ".gitignore"), encoding="utf-8").read()
        self.assertIn(".castflow-runtime/secrets.env", gitignore)
        from manager import jevmark
        cfg = jevmark.official_config({}, project_root=self.root)
        self.assertIsNotNone(cfg)
        self.assertNotIn(secret, repr(cfg))
        self.assertNotIn(secret, json.dumps(cfg.public()))
        gone = setup.cold_start(self.root, {"language": "zh", "jev_enabled": False})
        self.assertFalse(gone.get("jev_enabled"))
        self.assertFalse(os.path.isfile(os.path.join(module, "mark.py")))
        self.assertEqual(get(self.root, "TYPESAFE_API_KEY"), secret)


class TestSetupConsole(TmpProject):
    def test_page_has_setup_wizard(self):
        html = _read(os.path.join(STATIC_DIR, "index.html"))
        self.assertIn("setup-overlay", html)
        self.assertIn("/api/setup", html)
        self.assertIn("doSetup", html)
        self.assertIn("开启冷启动", html)
        self.assertIn("seed", html)
        self.assertIn("data-setup-ad=\"claude\"", html)
        self.assertIn("data-setup-ad=\"cursor\"", html)
        self.assertIn("setup-lang", html)
        self.assertIn("setup-evo", html)
        self.assertIn("setup-scan-gen", html)
        self.assertIn("setup-jev", html)
        self.assertIn(".castflow-runtime/secrets.env", html)
        self.assertIn("扫描模块并生成 skill", html)
        self.assertIn("goal-loop-creator", html)
        self.assertIn("long-task converter", html)
        self.assertIn("loop-engine", html)
        self.assertIn("setup-prompt", html)
        self.assertIn("留空", html)
        self.assertIn("MODULE_MARK_SYSTEM_PROMPT.md", html)
        self.assertIn(".castflow-runtime/skills/", html)
        self.assertIn("写入", html)
        self.assertIn("不会再拷一份", html)
        self.assertNotIn("也不删项目里的", html)
        self.assertNotIn("bootstrap-assets", html)
        self.assertNotIn("*.template.md", html)
        self.assertNotIn("setup-architect", html)
        self.assertNotIn("opt-architect", html)
        self.assertNotIn("id=\"setup-debug\"", html)
        self.assertNotIn("id=\"opt-profiler\"", html)
        self.assertIn("/goal", html)
        self.assertIn("label class=\"choice\"", html)
        self.assertIn("btn-copy-scan-gen", html)
        self.assertIn("/api/unseed", html)
        self.assertIn("回退并重新冷启动", html)
        self.assertNotIn("/api/scan", html)
        self.assertNotIn("/api/preview-scan", html)
        self.assertIn("选择项目文件夹", html)
        self.assertIn("/api/pick-root", html)
        self.assertIn("tab-framework", html)
        self.assertIn("fw-scan-gen", html)
        self.assertIn("scanHelpLater", html)
        self.assertIn("/api/framework/update", html)
        self.assertNotIn("data-tab=\"queue\"", html)
        self.assertNotIn("id=\"tab-queue\"", html)
        self.assertNotIn("data-tab=\"overview\"", html)
        self.assertNotIn("data-tab=\"evolution\"", html)

    def test_state_unseeded_then_http_setup(self):
        state = _state(self.root)
        self.assertFalse(state["seeded"])
        handler = make_handler(self.root)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever)
        thread.daemon = True
        thread.start()
        try:
            page = urlopen(
                Request("http://127.0.0.1:{}/".format(port)), timeout=10
            ).read().decode("utf-8")
            self.assertIn("setup-overlay", page)
            self.assertIn("开启冷启动", page)
            body = json.dumps({
                "language": "en",
                "adapters": {
                    "claude": True, "grok": True, "codex": False, "cursor": True,
                },
                "evolution": {"enabled": True},
                "optional_skills": {
                    "architect": True, "debug": False, "profiler": False,
                },
            }).encode("utf-8")
            req = Request(
                "http://127.0.0.1:{}/api/setup".format(port),
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urlopen(req, timeout=30)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("seeded"))
            self.assertEqual(data["config"]["language"], "en")
            self.assertFalse(data["config"]["adapters"]["codex"])
            self.assertTrue(os.path.isdir(os.path.join(
                self.root, ".claude", "skills", "skill-creator")))
            self.assertFalse(os.path.isdir(os.path.join(
                self.root, ".cursor", "skills", "skill-creator")))
            self.assertFalse(os.path.isdir(os.path.join(
                self.root, ".agents", "skills")))
            self.assertFalse(data.get("generate_skills"))

            req = Request(
                "http://127.0.0.1:{}/api/evolve".format(port),
                data=json.dumps({"enabled": False}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            evo = json.loads(urlopen(req, timeout=30).read().decode("utf-8"))
            self.assertFalse(evo["config"]["evolution"]["enabled"])

            req = Request(
                "http://127.0.0.1:{}/api/config".format(port),
                data=json.dumps({
                    "language": "ko",
                    "sync": True,
                    "adapters": evo["config"]["adapters"],
                    "optional_skills": evo["config"]["optional_skills"],
                }).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            cfg = json.loads(urlopen(req, timeout=30).read().decode("utf-8"))
            self.assertEqual(cfg["config"]["language"], "ko")
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_pick_root_retargets_bound_project(self):
        other = tempfile.mkdtemp(prefix="cf_other_")
        self.addCleanup(lambda: shutil.rmtree(other, ignore_errors=True))
        orig = setup.pick_project_directory
        setup.pick_project_directory = lambda initial=None, title=None: other
        handler = make_handler(self.root)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever)
        thread.daemon = True
        thread.start()
        try:
            req = Request(
                "http://127.0.0.1:{}/api/pick-root".format(port),
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            data = json.loads(urlopen(req, timeout=10).read().decode("utf-8"))
            self.assertFalse(data.get("cancelled"))
            self.assertEqual(
                os.path.normcase(os.path.abspath(data["project_root"])),
                os.path.normcase(os.path.abspath(other)),
            )
        finally:
            setup.pick_project_directory = orig
            httpd.shutdown()
            httpd.server_close()

    def test_generate_handoff_is_goal_loop_engine(self):
        empty = tempfile.mkdtemp(prefix="cf_empty_scan_")
        self.addCleanup(lambda: shutil.rmtree(empty, ignore_errors=True))
        text = queue.build_handoff(empty, generate=True)
        self.assertEqual(
            text,
            "/goal Read and follow .castflow-runtime/skills/"
            "MODULE_MARK_SYSTEM_PROMPT.md. "
            "Speak to the user in en: the multi-select question and each "
            "option sentence use that language. "
            "Keep module ids as printed. Skill prose still follows the card language.",
        )
        self.assertNotIn("\n", text)


class TestLoopEnginePrompt(unittest.TestCase):
    def test_prompt_and_catalog_exclude_ai_framework(self):
        prompt = _read(os.path.join(
            _CASTFLOW, "core", "skills",
            "MODULE_MARK_SYSTEM_PROMPT.md"))
        for needle in (
            "CastFlow/",
            ".castflow/",
            ".castflow-runtime/",
            ".claude/",
            ".agents/",
            ".cursor/",
            ".grok/",
            "never in the multi-select",
            "castflow.bat",
            "castflow.sh",
            "castflow.command",
            "ignore the whole tree",
            "Do not list by skill name",
            "_skill-gen-queue",
            "only 1 skill at a time",
            "No parallel",
            "status: pending",
            "status: done",
            "config.json` key `language`",
            "哪些模块要生成 programmer skill",
        ):
            self.assertIn(needle, prompt)
        catalog = _read(os.path.join(
            _CASTFLOW, "core", "rules", "module-catalog.md"))
        self.assertIn("Never a module", catalog)
        self.assertIn("CastFlow/", catalog)
        self.assertIn(".castflow-runtime/", catalog)
        self.assertIn("Do not keep a roster of framework skill names", catalog)
        self.assertNotIn("existing framework skills", catalog)
        self.assertNotIn("goal-loop-creator", prompt)

    def test_catalog_generation_forbids_pushy_description(self):
        prompt = _read(os.path.join(
            _CASTFLOW, "core", "skills",
            "MODULE_MARK_SYSTEM_PROMPT.md"))
        self.assertIn("Description Optimization", prompt)
        self.assertIn("manager.py validate", prompt)
        creator = _read(os.path.join(
            _CASTFLOW, "core", "skills", "skill-creator", "SKILL.md"))
        self.assertIn("false recall against sibling modules", creator)
        self.assertIn("**ignore** this bullet", creator)
        self.assertIn("then **stop**", creator)
        self.assertIn("## Freeform skills (not CastFlow catalog)", creator)
        iteration = _read(os.path.join(
            _CASTFLOW, "core", "skills", "SKILL_ITERATION.md"))
        self.assertNotIn("add a feature / fix a bug", iteration)
        self.assertIn("Use when the user names", iteration)
        self.assertIn("Pushy expansion is an error", iteration)
        self.assertIn("A missed recall beats a false one", iteration)
        self.assertIn("NOT other programmer-*-skill", iteration)
        self.assertNotIn("programmer.template", iteration)


if __name__ == "__main__":
    unittest.main()
