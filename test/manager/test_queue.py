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

from manager import catalog, queue
from manager.skills import project_skill_dir


class QueueStateTests(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="castflow-queue-")
        data = catalog.empty_catalog()
        data["modules"] = [{"id": "battle", "status": "accepted"}]
        catalog.save_catalog(self.root, data)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_enqueue_is_idempotent_and_preserves_running_item(self):
        first = queue.enqueue_accepted(self.root)
        self.assertEqual(len(first["items"]), 1)
        self.assertEqual(first["items"][0]["state"], "queued")
        queue._save_item_state(self.root, "battle", "running")
        second = queue.enqueue_accepted(self.root)
        self.assertEqual(second["items"][0]["state"], "running")

    def test_complete_requires_validation_and_marks_catalog_ready(self):
        queue.enqueue_accepted(self.root)
        skill_dir = project_skill_dir(self.root, "programmer-battle-skill")
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as handle:
            handle.write(
                "---\n"
                "name: programmer-battle-skill\n"
                "description: Change battle in this repo. Use when the user names battle. NOT work outside battle.\n"
                "---\n\n"
                "Change battle.\n"
            )
        with open(os.path.join(skill_dir, "ITERATION_GUIDE.md"), "w", encoding="utf-8") as handle:
            handle.write("# Iteration\n\nUpdate when the cited script file moves.\n")
        result = queue.complete_item(self.root, "battle")
        self.assertTrue(result["ok"], result)
        self.assertEqual(queue.load_queue(self.root)["items"][0]["state"], "done")
        self.assertEqual(catalog.load_catalog(self.root)["modules"][0]["skill_state"], "ready")

    def test_failed_item_can_be_retried(self):
        queue.enqueue_accepted(self.root)
        self.assertTrue(queue.fail_item(self.root, "battle", "model output invalid")["ok"])
        self.assertEqual(queue.load_queue(self.root)["items"][0]["state"], "failed")
        self.assertTrue(queue.retry_item(self.root, "battle")["ok"])
        self.assertEqual(queue.next_item(self.root)["id"], "battle")


if __name__ == "__main__":
    unittest.main()
