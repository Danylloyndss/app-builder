import json
import tempfile
import unittest
from pathlib import Path

from app.manager import Manager


class TimeProManagerFlowTests(unittest.TestCase):
    def test_manager_completes_timepro_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory = Manager(workspace=str(root)).run("Construa o TimePro")

            self.assertEqual(memory.status, "completed")
            self.assertEqual(memory.errors, [])
            self.assertEqual(memory.task_statuses.get("test"), "completed")
            self.assertEqual(memory.task_statuses.get("repair"), "completed")
            self.assertEqual(memory.task_statuses.get("acceptance"), "completed")

            quality_path = root / ".app-builder" / "quality_report.json"
            self.assertTrue(quality_path.exists())
            report = json.loads(quality_path.read_text(encoding="utf-8"))
            self.assertTrue(report["passed"], report["errors"])
            self.assertEqual(len(report["acceptance_checks"]), 7)


if __name__ == "__main__":
    unittest.main()
