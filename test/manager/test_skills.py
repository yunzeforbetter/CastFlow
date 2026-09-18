#!/usr/bin/env python3
"""Skill inventory, retire, update, sync, CLI, and console handlers."""

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

_CASTFLOW = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", ".castflow"
))
sys.path.insert(0, _CASTFLOW)

from manager import adapters, config, skills
from manager.paths import runtime_dir, bootstrap_skill_src
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


def _enabled_discovery_dirs(project_root):
    cfg = config.load_config(project_root)
    wanted = cfg.get("adapters") or {}
    out = []
    for key in adapters.SKILL_DISCOVERY_ADAPTERS:
        rel = adapters.ADAPTER_SKILL_DIRS[key]
        if wanted.get(key):
            out.append((key, os.path.join(project_root, rel)))
    return out


def _compat_skill_path(project_root, host, name):
    rel = adapters.COMPAT_SKILL_DIRS[host]
    return os.path.join(project_root, rel, name)


def _assert_skill_md_layout(test, skill_dir):
    skill_md = os.path.join(skill_dir, "SKILL.md")
    test.assertTrue(os.path.isdir(skill_dir), "missing skill dir {}".format(skill_dir))
    test.assertTrue(os.path.isfile(skill_md), "missing SKILL.md in {}".format(skill_dir))
    text = _read(skill_md)
    test.assertTrue(text.lstrip().startswith("---"), "SKILL.md needs YAML frontmatter")
    parts = text.split("---", 2)
    test.assertGreaterEqual(len(parts), 3, "SKILL.md frontmatter not closed")
    test.assertIn("name:", parts[1])
    test.assertTrue(parts[2].strip(), "SKILL.md body is empty")


class TmpProject(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cf_skills_")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)


class TestInventoryAfterSeed(TmpProject):
    def test_seed_creates_runtime_store_and_inventory(self):
        rc = manager_main(["--project-root", self.root, "seed"])
        self.assertEqual(rc, 0)
        runtime_skills = os.path.join(runtime_dir(self.root), "skills")
        self.assertTrue(os.path.isdir(runtime_skills))
        items = skills.inventory(self.root)
        names = set(i["name"] for i in items)
        self.assertIn("bootstrap-skill", names)
        self.assertIn("skill-creator", names)
        self.assertIn("origin-evolve-skill", names)
        self.assertNotIn("skill-forge", names)
        by_name = dict((i["name"], i) for i in items)
        self.assertEqual(by_name["bootstrap-skill"]["kind"], "bootstrap")
        self.assertEqual(by_name["skill-creator"]["kind"], "core")
        self.assertFalse(by_name["skill-creator"]["retired"])
        self.assertTrue(os.path.isdir(os.path.join(runtime_skills, "bootstrap-skill")))
        self.assertTrue(os.path.isdir(os.path.join(runtime_skills, "skill-creator")))
        self.assertTrue(os.path.isfile(os.path.join(
            runtime_skills, "MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md")))
        self.assertTrue(os.path.isfile(os.path.join(self.root, "castflow.bat")))
        self.assertTrue(os.path.isfile(os.path.join(
            self.root, ".castflow", "manager.py")))
        self.assertTrue(os.path.isfile(os.path.join(
            self.root, ".castflow", "manager", "ui", "static", "index.html")))
        bat = _read(os.path.join(self.root, "castflow.bat"))
        self.assertIn(".castflow\\manager.py", bat)
        self.assertIn(" ui", bat)


class TestRetireSync(TmpProject):
    def test_retire_then_sync_removes_from_all_enabled_trees(self):
        self.assertEqual(manager_main(["--project-root", self.root, "seed"]), 0)
        name = "skill-creator"
        for key, dest in _enabled_discovery_dirs(self.root):
            _assert_skill_md_layout(self, os.path.join(dest, name))

        result = skills.retire(self.root, name)
        self.assertTrue(result.get("ok"))
        self.assertTrue(skills.is_retired(self.root, name))
        # Retire does not delete the runtime copy.
        self.assertTrue(os.path.isdir(os.path.join(
            runtime_dir(self.root), "skills", name)))
        # Adapter copies remain until sync.
        self.assertTrue(os.path.isdir(os.path.join(
            self.root, ".claude", "skills", name)))

        report = adapters.sync(self.root)
        self.assertIn(name, report.get("retired") or [])
        for key, dest in _enabled_discovery_dirs(self.root):
            self.assertFalse(
                os.path.isdir(os.path.join(dest, name)),
                "{} still has retired {}".format(key, name),
            )
            # Other skills still projected.
            self.assertTrue(os.path.isdir(os.path.join(dest, "bootstrap-skill")))

        adapters.sync(self.root)
        for key, dest in _enabled_discovery_dirs(self.root):
            self.assertFalse(
                os.path.isdir(os.path.join(dest, name)),
                "second sync resurrected {} on {}".format(name, key),
            )
        self.assertTrue(os.path.isdir(os.path.join(
            runtime_dir(self.root), "skills", name)))

        restored = skills.restore(self.root, name)
        self.assertTrue(restored.get("ok"))
        self.assertFalse(skills.is_retired(self.root, name))
        adapters.sync(self.root)
        for key, dest in _enabled_discovery_dirs(self.root):
            _assert_skill_md_layout(self, os.path.join(dest, name))

    def test_retire_unknown_skill_fails(self):
        manager_main(["--project-root", self.root, "seed"])
        result = skills.retire(self.root, "no-such-skill")
        self.assertFalse(result.get("ok"))
        self.assertEqual(manager_main(
            ["--project-root", self.root, "retire", "no-such-skill"]), 2)


class TestUpdateSync(TmpProject):
    def test_update_core_skill_refreshes_from_harness_then_sync(self):
        self.assertEqual(manager_main(["--project-root", self.root, "seed"]), 0)
        name = "skill-creator"
        harness_md = os.path.join(
            _CASTFLOW, "core", "skills", name, "SKILL.md")
        runtime_md = os.path.join(
            runtime_dir(self.root), "skills", name, "SKILL.md")
        source = _read(harness_md)
        with open(runtime_md, "a", encoding="utf-8", newline="\n") as f:
            f.write("\n<!-- mutated-by-test -->\n")
        self.assertIn("mutated-by-test", _read(runtime_md))

        result = skills.update_skill(self.root, name)
        self.assertTrue(result.get("ok"))
        self.assertFalse(result.get("noop"))
        refreshed = _read(runtime_md)
        self.assertEqual(refreshed, source)
        self.assertNotIn("mutated-by-test", refreshed)

        adapters.sync(self.root)
        for key, dest in _enabled_discovery_dirs(self.root):
            projected = os.path.join(dest, name, "SKILL.md")
            self.assertTrue(os.path.isfile(projected), key)
            self.assertEqual(_read(projected), source)

    def test_update_project_skill_uses_runtime_copy(self):
        manager_main(["--project-root", self.root, "seed"])
        body = (
            "---\nname: programmer-billing-skill\ndescription: billing\n"
            "---\n\n# billing\n\nOwns invoices.\n"
        )
        dest = os.path.join(
            runtime_dir(self.root), "skills", "programmer-billing-skill")
        _write(os.path.join(dest, "SKILL.md"), body)
        result = skills.update_skill(self.root, "programmer-billing-skill")
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("kind"), "project")
        self.assertTrue(result.get("noop"))
        self.assertEqual(_read(os.path.join(dest, "SKILL.md")), body)
        adapters.sync(self.root)
        claude = os.path.join(
            self.root, ".claude", "skills", "programmer-billing-skill")
        _assert_skill_md_layout(self, claude)
        self.assertEqual(_read(os.path.join(claude, "SKILL.md")), body)


class TestCursorAdapter(TmpProject):
    def test_cursor_and_grok_do_not_get_skill_trees(self):
        manager_main(["--project-root", self.root, "seed"])
        self.assertFalse(os.path.isdir(_compat_skill_path(
            self.root, "cursor", "bootstrap-skill")))
        self.assertFalse(os.path.isdir(_compat_skill_path(
            self.root, "grok", "bootstrap-skill")))
        for key in adapters.SKILL_DISCOVERY_ADAPTERS:
            rel = adapters.ADAPTER_SKILL_DIRS[key]
            _assert_skill_md_layout(
                self, os.path.join(self.root, rel, "skill-creator"))
        self.assertTrue(os.path.isfile(os.path.join(
            self.root, ".grok", "hooks", "castflow.json")))
        self.assertTrue(os.path.isfile(os.path.join(
            self.root, ".cursor", "hooks.json")))

        other = tempfile.mkdtemp(prefix="cf_skills_nocursor_")
        self.addCleanup(lambda: shutil.rmtree(other, ignore_errors=True))
        cfg = config.load_config(other)
        cfg.setdefault("adapters", {})["cursor"] = False
        config.save_config(other, cfg)
        adapters.seed(other)
        self.assertFalse(os.path.isdir(os.path.join(other, ".cursor", "skills")))
        for key in adapters.SKILL_DISCOVERY_ADAPTERS:
            rel = adapters.ADAPTER_SKILL_DIRS[key]
            _assert_skill_md_layout(
                self, os.path.join(other, rel, "bootstrap-skill"))

    def test_disabled_adapter_not_written(self):
        cfg = config.load_config(self.root)
        cfg["adapters"]["codex"] = False
        config.save_config(self.root, cfg)
        adapters.seed(self.root)
        self.assertFalse(os.path.isdir(os.path.join(self.root, ".agents", "skills")))
        self.assertTrue(os.path.isdir(os.path.join(
            self.root, ".claude", "skills", "skill-creator")))


class TestCliLaunch(TmpProject):
    def test_manager_seed_retire_update_sync(self):
        rc = manager_main(["--project-root", self.root, "seed"])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(os.path.join(
            self.root, ".claude", "skills", "skill-creator", "SKILL.md")))
        self.assertTrue(os.path.isfile(os.path.join(
            self.root, ".agents", "skills", "skill-creator", "SKILL.md")))
        self.assertFalse(os.path.isdir(os.path.join(
            self.root, ".cursor", "skills", "skill-creator")))

        rc = manager_main(["--project-root", self.root, "skills"])
        self.assertEqual(rc, 0)

        rc = manager_main(["--project-root", self.root, "retire", "bootstrap-skill"])
        self.assertEqual(rc, 0)
        rc = manager_main(["--project-root", self.root, "sync"])
        self.assertEqual(rc, 0)
        for key, dest in _enabled_discovery_dirs(self.root):
            self.assertFalse(os.path.isdir(os.path.join(dest, "bootstrap-skill")))
        self.assertTrue(os.path.isdir(os.path.join(
            runtime_dir(self.root), "skills", "bootstrap-skill")))

        rc = manager_main(["--project-root", self.root, "update", "skill-creator"])
        self.assertEqual(rc, 0)
        rc = manager_main(["--project-root", self.root, "sync"])
        self.assertEqual(rc, 0)
        harness = _read(os.path.join(_CASTFLOW, "core", "skills", "skill-creator", "SKILL.md"))
        self.assertEqual(
            _read(os.path.join(self.root, ".claude", "skills", "skill-creator", "SKILL.md")),
            harness,
        )
        self.assertEqual(
            _read(os.path.join(self.root, ".agents", "skills", "skill-creator", "SKILL.md")),
            harness,
        )


class TestConsoleSurface(TmpProject):
    def test_index_html_has_retire_update_sync_controls(self):
        html_path = os.path.join(STATIC_DIR, "index.html")
        self.assertTrue(os.path.isfile(html_path))
        html = _read(html_path)
        self.assertIn("tab-skills", html)
        self.assertIn("retire", html)
        self.assertIn("update", html)
        self.assertIn("sync", html)
        self.assertIn("/api/skills/retire", html)
        self.assertIn("/api/skills/activate", html)
        self.assertIn("/api/skills/update", html)
        self.assertIn("/api/sync", html)
        self.assertIn("doRetire", html)
        self.assertIn("doActivate", html)
        self.assertIn("doUpdate", html)
        self.assertIn("doSync", html)
        self.assertIn("castflow.bat", html)

    def test_state_includes_inventory(self):
        manager_main(["--project-root", self.root, "seed"])
        state = _state(self.root)
        names = [i["name"] for i in state["skills"]]
        self.assertIn("skill-creator", names)
        self.assertIn("bootstrap-skill", names)
        skills.retire(self.root, "skill-creator")
        state = _state(self.root)
        by_name = dict((i["name"], i) for i in state["skills"])
        self.assertTrue(by_name["skill-creator"]["retired"])
        self.assertIn("skill-creator", state["retired"])


class TestConsoleHttp(TmpProject):
    def setUp(self):
        super(TestConsoleHttp, self).setUp()
        manager_main(["--project-root", self.root, "seed"])
        handler = make_handler(self.root)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        super(TestConsoleHttp, self).tearDown()

    def _json(self, method, path, body=None):
        data = None
        headers = {}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = Request(
            "http://127.0.0.1:{}{}".format(self.port, path),
            data=data,
            headers=headers,
            method=method,
        )
        resp = urlopen(req, timeout=10)
        raw = resp.read().decode("utf-8")
        return resp.status, json.loads(raw)

    def test_http_inventory_retire_update_sync(self):
        req = Request("http://127.0.0.1:{}/".format(self.port))
        page = urlopen(req, timeout=10).read().decode("utf-8")
        self.assertIn("retire", page)
        self.assertIn("update", page)
        self.assertIn("sync", page)
        self.assertIn("tab-skills", page)

        status, state = self._json("GET", "/api/state")
        self.assertEqual(status, 200)
        names = [i["name"] for i in state["skills"]]
        self.assertIn("skill-creator", names)

        status, state = self._json(
            "POST", "/api/skills/retire", {"name": "skill-creator"})
        self.assertEqual(status, 200)
        by_name = dict((i["name"], i) for i in state["skills"])
        self.assertTrue(by_name["skill-creator"]["retired"])

        status, state = self._json("POST", "/api/sync", {})
        self.assertEqual(status, 200)
        self.assertFalse(os.path.isdir(os.path.join(
            self.root, ".claude", "skills", "skill-creator")))
        self.assertFalse(os.path.isdir(os.path.join(
            self.root, ".agents", "skills", "skill-creator")))
        self.assertFalse(os.path.isdir(os.path.join(
            self.root, ".cursor", "skills", "skill-creator")))

        status, state = self._json(
            "POST", "/api/skills/update", {"name": "bootstrap-skill"})
        self.assertEqual(status, 200)
        src = os.path.join(bootstrap_skill_src(), "SKILL.md")
        dst = os.path.join(
            runtime_dir(self.root), "skills", "bootstrap-skill", "SKILL.md")
        self.assertEqual(_read(dst), _read(src))


class TestOption4Projection(TmpProject):
    def test_sync_strips_leftover_grok_and_cursor_copies(self):
        manager_main(["--project-root", self.root, "seed"])
        leftover = (
            "---\nname: leftover\ndescription: leftover copy\n---\n\n# leftover\n"
        )
        for host in ("grok", "cursor"):
            path = os.path.join(
                _compat_skill_path(self.root, host, "bootstrap-skill"), "SKILL.md")
            _write(path, leftover)
            self.assertTrue(os.path.isfile(path))
        adapters.sync(self.root)
        self.assertFalse(os.path.isdir(_compat_skill_path(
            self.root, "grok", "bootstrap-skill")))
        self.assertFalse(os.path.isdir(_compat_skill_path(
            self.root, "cursor", "bootstrap-skill")))
        _assert_skill_md_layout(self, os.path.join(
            self.root, ".claude", "skills", "bootstrap-skill"))

    def test_new_runtime_skill_reaches_claude_and_agents_only(self):
        manager_main(["--project-root", self.root, "seed"])
        name = "programmer-u3d-probe-skill"
        body = (
            "---\nname: programmer-u3d-probe-skill\n"
            "description: probe skill for discovery\n---\n\n# probe\n"
        )
        dest = os.path.join(runtime_dir(self.root), "skills", name)
        _write(os.path.join(dest, "SKILL.md"), body)
        adapters.sync(self.root)
        for key, rel in (
            ("claude", os.path.join(".claude", "skills")),
            ("codex", os.path.join(".agents", "skills")),
        ):
            projected = os.path.join(self.root, rel, name)
            _assert_skill_md_layout(self, projected)
            self.assertEqual(_read(os.path.join(projected, "SKILL.md")), body)
        self.assertFalse(os.path.isdir(_compat_skill_path(self.root, "grok", name)))
        self.assertFalse(os.path.isdir(_compat_skill_path(self.root, "cursor", name)))


if __name__ == "__main__":
    unittest.main()
