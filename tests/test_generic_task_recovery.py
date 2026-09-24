import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from app.manager import Manager
from app.tasks import BuildTask


class GenericTaskRecoveryTests(unittest.TestCase):
    def test_build_task_failure_is_repaired_and_retried(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = Manager(workspace=temp_dir, max_retries=1)
            manager.memory.mission = "Build a simple app"
            task = BuildTask("implement", "Implement requested functionality", "build")
            tasks = [task]
            manager.memory.task_statuses = {"implement": "pending"}

            calls = []

            def execute(task_text, workspace, mission):
                calls.append(task_text)
                if task_text == task.title and calls.count(task.title) == 1:
                    raise RuntimeError("temporary build failure")
                return "repaired"

            manager.executor.execute = execute
            result = manager._execute_task(task, tasks)

            self.assertTrue(result)
            self.assertEqual(manager.memory.task_statuses["implement"], "completed")
            self.assertEqual(manager.memory.diagnostics["task_retry_counts"]["implement"], 1)
            self.assertTrue(any(event.get("event") == "task_failure_diagnosed" for event in manager.memory.events))
            self.assertGreaterEqual(calls.count(task.title), 2)


if __name__ == "__main__":
    unittest.main()
