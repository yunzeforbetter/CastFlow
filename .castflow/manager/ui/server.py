"""127.0.0.1 visual console. No third-party deps."""

from __future__ import print_function

import json
import os
import sys
import webbrowser

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
except ImportError:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer  # type: ignore
    try:
        from SocketServer import ThreadingMixIn
    except ImportError:
        from socketserver import ThreadingMixIn

    class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True

from .. import adapters, catalog, config, evolution, queue, setup, skills
from ..paths import find_harness_dir, runtime_dir

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class BoundRoot(object):
    """Mutable project root so the folder picker can retarget a running console."""

    def __init__(self, root):
        self.root = os.path.abspath(root)


def _state(project_root):
    if setup.is_seeded(project_root):
        adapters.refresh_projections(project_root)
    harness = find_harness_dir()
    return {
        "project_root": project_root.replace("\\", "/"),
        "castflow_home": os.path.dirname(harness).replace("\\", "/"),
        "runtime": runtime_dir(project_root).replace("\\", "/"),
        "seeded": setup.is_seeded(project_root),
        "config": config.load_config(project_root),
        "catalog": catalog.load_catalog(project_root),
        "queue": queue.load_queue(project_root),
        "adapters": adapters.adapter_status(project_root),
        "handoff": queue.build_handoff(project_root),
        "default_prompt": queue.default_scan_generate_prompt(project_root),
        "skills": skills.inventory(project_root),
        "retired": sorted(skills.retired_names(project_root)),
    }


def _read_json(handler):
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError:
        return {}


def make_handler(project_root):
    bound = project_root if isinstance(project_root, BoundRoot) else BoundRoot(project_root)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

        def _send(self, code, body, content_type="application/json"):
            if not isinstance(body, bytes):
                body = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, code, data):
            self._send(code, json.dumps(data, ensure_ascii=False, indent=2))

        def do_GET(self):
            project_root = bound.root
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                index = os.path.join(STATIC_DIR, "index.html")
                with open(index, "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            if path == "/api/state":
                return self._send_json(200, _state(project_root))
            if path == "/api/handoff":
                generate = None
                raw_path = self.path or ""
                if "generate=1" in raw_path or "generate=true" in raw_path:
                    generate = True
                elif "generate=0" in raw_path or "generate=false" in raw_path:
                    generate = False
                return self._send_json(200, {
                    "text": queue.build_handoff(project_root, generate=generate),
                })
            if path == "/api/skills":
                return self._send_json(200, {
                    "skills": skills.inventory(project_root),
                    "retired": sorted(skills.retired_names(project_root)),
                })
            return self._send_json(404, {"error": "not found"})

        def do_POST(self):
            project_root = bound.root
            path = self.path.split("?", 1)[0]
            body = _read_json(self)
            try:
                if path == "/api/pick-root":
                    picked = setup.pick_project_directory(
                        project_root, "Select the project folder")
                    if not picked:
                        data = _state(bound.root)
                        data["cancelled"] = True
                        return self._send_json(200, data)
                    bound.root = os.path.abspath(picked)
                    data = _state(bound.root)
                    data["cancelled"] = False
                    return self._send_json(200, data)
                if path == "/api/sync":
                    adapters.sync(project_root)
                    return self._send_json(200, _state(project_root))
                if path == "/api/setup":
                    report = setup.cold_start(project_root, body)
                    data = _state(project_root)
                    data["handoff"] = report.get("handoff") or ""
                    data["generate_skills"] = bool(report.get("generate_skills"))
                    return self._send_json(200, data)
                if path == "/api/unseed":
                    setup.unseed(project_root)
                    data = _state(project_root)
                    data["reset"] = True
                    return self._send_json(200, data)
                if path == "/api/framework/update":
                    setup.update_framework(project_root)
                    return self._send_json(200, _state(project_root))
                if path == "/api/skills/retire":
                    result = skills.retire(project_root, body.get("name"))
                    if not result.get("ok"):
                        return self._send_json(400, result)
                    adapters.refresh_projections(project_root)
                    return self._send_json(200, _state(project_root))
                if path == "/api/skills/activate":
                    result = skills.restore(project_root, body.get("name"))
                    if not result.get("ok"):
                        return self._send_json(400, result)
                    adapters.refresh_projections(project_root)
                    return self._send_json(200, _state(project_root))
                if path == "/api/skills/update":
                    result = skills.update_skill(project_root, body.get("name"))
                    if not result.get("ok"):
                        return self._send_json(400, result)
                    return self._send_json(200, _state(project_root))
                if path == "/api/evolve":
                    enabled = bool(body.get("enabled"))
                    evolution.set_enabled(project_root, enabled, sync_fn=adapters.sync)
                    return self._send_json(200, _state(project_root))
                if path == "/api/queue":
                    queue.enqueue_accepted(project_root)
                    return self._send_json(200, _state(project_root))
                if path == "/api/config":
                    current = config.load_config(project_root)
                    if "language" in body:
                        current["language"] = body["language"]
                    if "adapters" in body and isinstance(body["adapters"], dict):
                        current.setdefault("adapters", {}).update(body["adapters"])
                    if "optional_skills" in body and isinstance(body["optional_skills"], dict):
                        current.setdefault("optional_skills", {}).update(
                            body["optional_skills"])
                    config.save_config(project_root, current)
                    cat = catalog.load_catalog(project_root)
                    for name, enabled in (current.get("optional_skills") or {}).items():
                        if name in cat["core_skills"]:
                            cat["core_skills"][name]["enabled"] = bool(enabled)
                    catalog.save_catalog(project_root, cat)
                    if body.get("sync", True):
                        adapters.sync(project_root)
                    return self._send_json(200, _state(project_root))
                if path.startswith("/api/catalog/modules/"):
                    module_id = path.rsplit("/", 1)[-1]
                    cat = catalog.load_catalog(project_root)
                    cat, mod = catalog.patch_module(cat, module_id, body)
                    if mod is None:
                        return self._send_json(404, {"error": "unknown module"})
                    catalog.save_catalog(project_root, cat)
                    return self._send_json(200, _state(project_root))
            except Exception as exc:
                return self._send_json(500, {"error": str(exc)})
            return self._send_json(404, {"error": "not found"})

        def do_PUT(self):
            self.do_POST()

        def do_PATCH(self):
            self.do_POST()

    return Handler


def serve(project_root, port=8765, no_browser=False):
    bound = project_root if isinstance(project_root, BoundRoot) else BoundRoot(project_root)
    handler = make_handler(bound)
    server = None
    last_err = None
    start = int(port or 8765)
    for candidate in range(start, start + 12):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), handler)
            port = candidate
            break
        except OSError as exc:
            last_err = exc
            server = None
    if server is None:
        print("Could not bind 127.0.0.1:{}-{}: {}".format(
            start, start + 11, last_err))
        return 1
    url = "http://127.0.0.1:{}".format(port)
    print("CastFlow console: {}".format(url))
    print("Project: {}".format(bound.root))
    if not no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0
