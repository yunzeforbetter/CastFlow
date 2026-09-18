#!/usr/bin/env python3
"""Cold-start GUI/setup: config + seed without a Python module scanner."""

from __future__ import print_function

import json
import os
import shutil
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

from manager import adapters, config, queue, setup
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
            "MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md 执行",
        )
        self.assertNotIn("\n", scan_text)
        copied = os.path.join(
            runtime_dir(self.root), "skills",
            "MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md")
        self.assertTrue(os.path.isfile(copied))
        copied_text = _read(copied)
        self.assertIn(".castflow-runtime/", copied_text)
        self.assertIn("禁止出现在多选", copied_text)
        self.assertIn("CastFlow/", copied_text)
        self.assertIn("_skill-gen-queue", copied_text)
        self.assertIn("同一时刻只允许 1 个", copied_text)

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

    def test_unseed_allows_cold_start_again(self):
        setup.cold_start(self.root, {"language": "zh"})
        self.assertTrue(setup.is_seeded(self.root))
        self.assertTrue(os.path.isfile(os.path.join(self.root, "CLAUDE.md")))
        self.assertTrue(os.path.isdir(os.path.join(
            self.root, ".claude", "skills", "skill-creator")))
        report = setup.unseed(self.root)
        self.assertTrue(report.get("ok"))
        self.assertFalse(setup.is_seeded(self.root))
        self.assertFalse(os.path.isdir(runtime_dir(self.root)))
        self.assertFalse(os.path.isdir(os.path.join(
            self.root, ".claude", "skills", "skill-creator")))
        again = setup.cold_start(self.root, {
            "language": "en",
            "generate_skills": True,
        })
        self.assertTrue(setup.is_seeded(self.root))
        self.assertTrue(again.get("generate_skills"))
        again_text = again.get("handoff") or ""
        self.assertTrue(again_text.startswith("/goal "))
        self.assertIn(
            ".castflow-runtime/skills/MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md",
            again_text,
        )
        self.assertNotIn("\n", again_text)

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
        self.assertIn("扫描模块并生成 skill", html)
        self.assertIn("goal-loop-creator", html)
        self.assertIn("长任务转换系统", html)
        self.assertIn("loop-engine", html)
        self.assertIn("setup-prompt", html)
        self.assertIn("留空", html)
        self.assertIn("MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md", html)
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
        self.assertIn("/api/framework/update", html)
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
            "/goal 读取并按照 .castflow-runtime/skills/"
            "MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md 执行",
        )
        self.assertNotIn("\n", text)


class TestLoopEnginePrompt(unittest.TestCase):
    def test_prompt_and_catalog_exclude_ai_framework(self):
        prompt = _read(os.path.join(
            _CASTFLOW, "core", "skills",
            "MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md"))
        for needle in (
            "CastFlow/",
            ".castflow/",
            ".castflow-runtime/",
            ".claude/",
            ".agents/",
            ".cursor/",
            ".grok/",
            "禁止出现在多选",
            "castflow.bat",
            "整棵忽略",
            "不要按 skill 名列举",
            "_skill-gen-queue",
            "同一时刻只允许 1 个",
            "禁止并行",
            "status: pending",
            "status: done",
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
            "MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md"))
        self.assertIn("误召回比漏召回更差", prompt)
        self.assertIn("pushy", prompt)
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
        self.assertIn("NOT other programmer-*-skill", iteration)
        self.assertNotIn("programmer.template", iteration)


if __name__ == "__main__":
    unittest.main()
