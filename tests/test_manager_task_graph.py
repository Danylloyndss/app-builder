import tempfile
import unittest
from pathlib import Path

from app.manager import Manager


class ManagerTaskGraphTests(unittest.TestCase):
    def test_graph_executes_in_dependency_order(self):
        mission = "Create a mobile timesheet app with forms, data storage and manager dashboard"
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = Manager(temp_dir).run(mission)
            print("DEBUG_MANAGER_STATUS", memory.status, memory.errors, memory.task_statuses, memory.diagnostics)\n            self.assertEqual(memory.status, "completed")
            self.assertEqual(memory.task_statuses.get("spec"), "completed")
            self.assertEqual(memory.task_statuses.get("structure"), "completed")
            self.assertEqual(memory.task_statuses.get("forms"), "completed")
            self.assertEqual(memory.task_statuses.get("storage"), "completed")
            self.assertEqual(memory.task_statuses.get("dashboard"), "completed")
            self.assertEqual(memory.task_statuses.get("test"), "completed")
            self.assertEqual(memory.task_statuses.get("security"), "completed")
            self.assertEqual(memory.task_statuses.get("acceptance"), "completed")
            self.assertTrue((Path(temp_dir) / ".app-builder" / "tasks.json").exists())

    def test_graph_pauses_at_sensitive_task_and_resumes(self):
        mission = "Create a web app with login"
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = Manager(temp_dir)
            waiting = manager.run(mission)
            self.assertEqual(waiting.status, "waiting_for_approval")
            self.assertEqual(waiting.task_statuses.get("auth"), "waiting_for_approval")

            pending = manager.approvals.list_pending()
            self.assertEqual(len(pending), 1)
            request_id = pending[0]["id"]
            manager.approvals.decide(request_id, True)

            resumed = Manager(temp_dir).run(mission, resume=True)
            self.assertEqual(resumed.task_statuses.get("auth"), "completed")
            self.assertNotEqual(resumed.status, "waiting_for_approval")
            self.assertEqual(Manager(temp_dir).approvals.get(request_id)["status"], "consumed")

    def test_resume_does_not_repeat_completed_tasks(self):
        mission = "Create a simple Hello App"
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Manager(temp_dir).run(mission)
            completed_before = dict(first.task_statuses)
            history_before = len(first.history)

            resumed = Manager(temp_dir).run(mission, resume=True)
            self.assertEqual(resumed.status, "completed")
            self.assertEqual(resumed.task_statuses, completed_before)
            self.assertGreater(len(resumed.history), history_before)


if __name__ == "__main__":
    unittest.main()
