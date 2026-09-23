#!/usr/bin/env python3
"""Official TypeSafe Jev when configured; structural prior otherwise."""

from __future__ import print_function

import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

_CASTFLOW = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", ".castflow"
))
sys.path.insert(0, _CASTFLOW)

from manager import jevmark


def _atom(atom_id, kind, role, path, decls, inbound, entries):
    return {
        "id": atom_id,
        "kind": kind,
        "role": role,
        "paths": [path],
        "decls": list(decls),
        "inbound": set(inbound),
        "outbound": set(),
        "entries": entries,
    }


def _sample_atoms():
    return [
        _atom(
            "mail", "feature-dir", "feature",
            "Assets/Scripts/GameLogic/Logic/Modules/Mail/MailBox.cs",
            ["MailBox"], [], 2,
        ),
        _atom(
            "protocol", "adapter-path", "adapter",
            "tools/Tuyoo.Protocol/TType.cs",
            ["TType"], ["mail"], 0,
        ),
        _atom(
            "mystery", "residue", "engine",
            "Assets/Scripts/GameLogic/Renderer/UI/Mixed/MixedView.cs",
            ["MixedView"], ["mail"], 4,
        ),
    ]


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        self.server.captured = {
            "path": self.path,
            "authorization_present": bool(self.headers.get("Authorization")),
            "body": json.loads(raw.decode("utf-8")),
        }
        stance = "stance__mystery"
        answers = {
            stance: {
                "type": "choice",
                "choice": "framework_mechanism",
                "confidence": 0.91,
                "probabilities": {
                    "framework_mechanism": 0.91,
                    "feature": 0.04,
                    "shared_method": 0.02,
                    "independent_system": 0.02,
                    "other": 0.01,
                },
            },
            "serves_one__mystery": {"type": "noul", "noul": 0.12},
            "mechanism__mystery": {
                "type": "score",
                "score": 2.0,
                "confidence": 0.8,
                "legend": {
                    "0": "No shared contract or host",
                    "1": "Mixed",
                    "2": "Only a mechanism; surfaces live elsewhere",
                },
                "probabilities": {"0": 0.05, "1": 0.15, "2": 0.8},
            },
        }
        payload = json.dumps({
            "model": "jev-latest",
            "answers": answers,
            "usage": {"input_tokens": 20, "output_tokens": 6},
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        return


class JevMarkTests(unittest.TestCase):
    def test_config_detection_never_prints_the_key(self):
        secret = "super-secret-key-xyz"
        self.assertIsNone(jevmark.official_config({}))
        self.assertIsNone(jevmark.official_config({"TYPESAFE_API_KEY": "   "}))
        self.assertIsNone(jevmark.official_config({"TYPESAFE_API_KEY": "has space"}))
        self.assertIsNone(jevmark.official_config({"TYPESAFE_API_KEY": "bad\nkey"}))
        self.assertIsNone(jevmark.official_config({"TYPESAFE_API_KEY": "密钥"}))
        config = jevmark.official_config({
            "TYPESAFE_API_KEY": "  {0}  ".format(secret),
            "TYPESAFE_DEFAULT_MODEL": "jev-1.13.0",
            "TYPESAFE_BASE_URL": "http://127.0.0.1:9",
        })
        self.assertEqual(config.model, "jev-1.13.0")
        self.assertEqual(config.base_url, "http://127.0.0.1:9")
        self.assertNotIn(secret, repr(config))
        self.assertNotIn(secret, json.dumps(config.public()))
        marks, notice = jevmark.mark_atoms(_sample_atoms(), {}, environ={})
        text = jevmark.format_marks(marks) + (notice or "")
        self.assertIn("not configured", notice)
        self.assertNotIn(secret, text)
        self.assertNotIn(jevmark.OFFICIAL_SOURCE, text)
        for mark in marks:
            self.assertNotEqual(mark["source"], jevmark.OFFICIAL_SOURCE)
            self.assertNotIn("probability", mark)
            self.assertNotIn("noul", mark)
            self.assertNotIn("confidence", mark)

    def test_missing_config_uses_prior_without_fake_jev(self):
        marks, notice = jevmark.mark_atoms(_sample_atoms(), {}, environ={})
        by_id = {mark["id"]: mark for mark in marks}
        self.assertEqual(notice, jevmark.NOTICE_NOT_CONFIGURED)
        self.assertEqual(by_id["mail"]["source"], "prior")
        self.assertEqual(by_id["mail"]["role"], "feature")
        self.assertEqual(by_id["protocol"]["source"], "prior")
        self.assertEqual(by_id["protocol"]["role"], "adapter")
        self.assertEqual(by_id["mystery"]["source"], "review")
        self.assertEqual(by_id["mystery"]["action"], "review")
        self.assertNotIn("choice", by_id["mystery"])
        rendered = jevmark.format_marks(marks)
        self.assertNotIn("official-jev", rendered)

    def test_official_client_wins_and_applies_only_response_fields(self):
        server = HTTPServer(("127.0.0.1", 0), _Handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        self.addCleanup(server.shutdown)
        secret = "local-official-key"
        environ = {
            "TYPESAFE_API_KEY": secret,
            "TYPESAFE_BASE_URL": "http://127.0.0.1:{0}".format(port),
        }
        marks, notice = jevmark.mark_atoms(_sample_atoms(), {}, environ=environ)
        self.assertIsNone(notice)
        captured = server.captured
        self.assertEqual(captured["path"], "/v1/systemone")
        self.assertTrue(captured["authorization_present"])
        body = captured["body"]
        self.assertEqual(body["model"], "jev-latest")
        self.assertIn("cards", body["state"])
        sent_ids = [card["id"] for card in body["state"]["cards"]]
        self.assertEqual(sent_ids, ["mystery"])
        self.assertIn("stance__mystery", body["questions"])
        self.assertEqual(body["questions"]["serves_one__mystery"]["type"], "noul")
        self.assertEqual(body["questions"]["mechanism__mystery"]["type"], "score")
        by_id = {mark["id"]: mark for mark in marks}
        mystery = by_id["mystery"]
        self.assertEqual(mystery["source"], jevmark.OFFICIAL_SOURCE)
        self.assertEqual(mystery["choice"], "framework_mechanism")
        self.assertEqual(mystery["action"], "split")
        self.assertEqual(mystery["noul"], 0.12)
        self.assertEqual(mystery["score"], 2.0)
        self.assertEqual(mystery["weights"]["framework_mechanism"], 0.91)
        self.assertEqual(by_id["mail"]["source"], "prior")
        self.assertEqual(by_id["protocol"]["source"], "prior")
        self.assertNotIn(secret, jevmark.format_marks(marks))
        # Persist the request without the key for the goal evidence folder.
        scratch = os.environ.get("JEV_MARK_SCRATCH")
        if scratch:
            safe = {
                "path": captured["path"],
                "model": body["model"],
                "state": body["state"],
                "questions": body["questions"],
                "mark": {
                    "id": mystery["id"],
                    "action": mystery["action"],
                    "source": mystery["source"],
                    "choice": mystery["choice"],
                    "noul": mystery["noul"],
                    "score": mystery["score"],
                },
            }
            with open(os.path.join(scratch, "official-systemone.json"), "w", encoding="utf-8") as handle:
                json.dump(safe, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    unittest.main()
