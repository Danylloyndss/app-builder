import tempfile
import unittest
from pathlib import Path

from app.manager import Manager


class ApprovalFlowTests(unittest.TestCase):
    def test_sensitive_task_pauses_then_resumes_after_approval(self):
        mission = "Create a web app with login"
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = Manager(temp_dir)
            waiting = manager.run(mission)
            self.assertEqual(waiting.status, "waiting_for_approval")
            self.assertEqual(waiting.current_task, "Implement user access flow")

            pending = manager.approvals.list_pending()
            self.assertEqual(len(pending), 1)
            request_id = pending[0]["id"]
            manager.approvals.decide(request_id, True)

            resumed = Manager(temp_dir).run(mission, resume=True)
            self.assertTrue(any("auth" in item.lower() for item in resumed.completed))
            self.assertNotEqual(resumed.status, "waiting_for_approval")
            self.assertEqual(Manager(temp_dir).approvals.get(request_id)["status"], "consumed")
            self.assertTrue((Path(temp_dir) / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
