import json
import tempfile
import unittest
from pathlib import Path

from app.architecture import ArchitectureBuilder
from app.specification import SpecificationBuilder
from app.tasks import TaskBuilder


class ArchitectureTests(unittest.TestCase):
    def test_timesheet_architecture_and_task_graph(self):
        mission = "Create a mobile timesheet app with login, forms, data storage and manager dashboard"
        spec = SpecificationBuilder().build(mission)
        architecture = ArchitectureBuilder().build(spec)
        tasks = TaskBuilder().build(spec, architecture)

        self.assertEqual(architecture.frontend, "responsive HTML/CSS/JavaScript")
        self.assertIn("manager dashboard", architecture.components)
        self.assertIn("persistence layer", architecture.components)
        self.assertIn("auth", [task.id for task in tasks])
        self.assertIn("test", [task.id for task in tasks])
        self.assertEqual(tasks[-1].id, "acceptance")

    def test_manager_writes_architecture_artifacts(self):
        from app.manager import Manager

        with tempfile.TemporaryDirectory() as temp_dir:
            Manager(temp_dir).run("Create a simple expense tracker")
            artifact_dir = Path(temp_dir) / ".app-builder"
            for filename in ("spec.json", "architecture.json", "tasks.json"):
                self.assertTrue((artifact_dir / filename).exists())
            tasks = json.loads((artifact_dir / "tasks.json").read_text(encoding="utf-8"))
            self.assertEqual(tasks[0]["id"], "spec")
            self.assertEqual(tasks[-1]["id"], "acceptance")


if __name__ == "__main__":
    unittest.main()
