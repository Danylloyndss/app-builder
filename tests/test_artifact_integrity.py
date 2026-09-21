import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app.manager import Manager
from app.tasks import BuildTask


class ArtifactIntegrityTests(unittest.TestCase):
    def test_resume_detects_changed_artifact_and_requeues_build_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "index.html"
            artifact.write_text("original", encoding="utf-8")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            report_dir = root / ".app-builder"
            report_dir.mkdir()
            (report_dir / "build_report.json").write_text(
                json.dumps({"artifacts": {"index.html": digest}}),
                encoding="utf-8",
            )
            artifact.write_text("changed", encoding="utf-8")
            manager = Manager(workspace=str(root))
            tasks = [
                BuildTask("structure", "Create project structure", "build", status="completed"),
                BuildTask("implement", "Implement requested functionality", "build", status="completed"),
                BuildTask("test", "Run tests", "test", status="completed"),
                BuildTask("security", "Run security review", "security", status="completed"),
            ]
            manager.memory.task_statuses = {task.id: task.status for task in tasks}

            self.assertFalse(manager._validate_build_integrity(tasks))
            self.assertEqual(
                [manager.memory.task_statuses[t.id] for t in tasks],
                ["pending", "pending", "pending", "pending"],
            )
            self.assertEqual(manager.memory.diagnostics["artifact_integrity"], "changed")
            self.assertEqual(manager.memory.diagnostics["artifact_integrity_mismatches"], ["index.html"])

    def test_resume_accepts_unchanged_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "index.html"
            artifact.write_text("stable", encoding="utf-8")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            report_dir = root / ".app-builder"
            report_dir.mkdir()
            (report_dir / "build_report.json").write_text(
                json.dumps({"artifacts": {"index.html": digest}}),
                encoding="utf-8",
            )
            manager = Manager(workspace=str(root))
            tasks = [BuildTask("implement", "Implement requested functionality", "build", status="completed")]

            self.assertTrue(manager._validate_build_integrity(tasks))
            self.assertEqual(tasks[0].status, "completed")


if __name__ == "__main__":
    unittest.main()
