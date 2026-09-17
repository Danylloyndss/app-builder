import json
import tempfile
import unittest
from pathlib import Path

from app.architecture import ArchitectureBuilder
from app.specification import SpecificationBuilder
from app.tasks import TaskBuilder


class TaskBuilderTests(unittest.TestCase):
    def test_timesheet_graph_has_dependencies_and_acceptance(self):
        spec = SpecificationBuilder().build(
            "Create a mobile timesheet app with login, forms, data storage and manager dashboard"
        )
        architecture = ArchitectureBuilder().build(spec)
        tasks = TaskBuilder().build(spec, architecture)
        ids = [task.id for task in tasks]
        self.assertEqual(ids[0], "spec")
        self.assertIn("auth", ids)
        self.assertIn("storage", ids)
        self.assertIn("dashboard", ids)
        self.assertEqual(tasks[-1].id, "acceptance")
        self.assertTrue(all(task.dependencies or task.id == "spec" for task in tasks))
        self.assertTrue(any(task.requires_approval for task in tasks))

    def test_graph_is_serializable(self):
        spec = SpecificationBuilder().build("Create an expense tracker")
        architecture = ArchitectureBuilder().build(spec)
        tasks = TaskBuilder().build(spec, architecture)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tasks.json"
            TaskBuilder.save(tasks, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data[0]["id"], "spec")
            self.assertIn("acceptance", data[-1])


if __name__ == "__main__":
    unittest.main()
