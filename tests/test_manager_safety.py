import json
import tempfile
import unittest
from pathlib import Path

from app.manager import Manager


class ManagerSafetyTests(unittest.TestCase):
    def test_resume_rejects_corrupted_task_graph(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            manager = Manager(workspace=str(workspace))
            tasks_dir = workspace / ".app-builder"
            tasks_dir.mkdir(parents=True)
            (tasks_dir / "tasks.json").write_text(json.dumps([
                {"id": "a", "title": "A", "kind": "build", "dependencies": ["missing"]},
            ]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unknown dependencies"):
                manager._load_tasks()


if __name__ == "__main__":
    unittest.main()
