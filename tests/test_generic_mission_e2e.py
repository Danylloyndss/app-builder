import json
import tempfile
import unittest
from pathlib import Path

from app.manager import Manager


class GenericMissionEndToEndTests(unittest.TestCase):
    def test_expense_tracker_builds_to_completed_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            manager = Manager(workspace=str(workspace), max_retries=1)
            memory = manager.run(
                "Create an expense tracker with forms, data storage, history, dashboard and mobile support"
            )

            self.assertEqual(memory.status, "completed")
            self.assertFalse(memory.errors)
            self.assertTrue((workspace / "index.html").exists())
            self.assertTrue((workspace / "app.js").exists())
            self.assertTrue((workspace / "backend.py").exists())

            capabilities = json.loads(
                (workspace / ".app-builder" / "capabilities.json").read_text(encoding="utf-8")
            )
            self.assertTrue({"forms", "storage", "list", "dashboard", "mobile"}.issubset(
                set(capabilities["features"])
            ))

            report = json.loads(
                (workspace / ".app-builder" / "build_report.json").read_text(encoding="utf-8")
            )
            self.assertTrue(report["quality_passed"])
            self.assertGreaterEqual(report["artifact_count"], 5)

            release = json.loads(
                (workspace / ".app-builder" / "release_report.json").read_text(encoding="utf-8")
            )
            self.assertTrue(release["ready"])


if __name__ == "__main__":
    unittest.main()
