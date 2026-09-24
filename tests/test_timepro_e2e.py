import tempfile
import unittest
from pathlib import Path

from app.manager import Manager


class TimeProE2ETests(unittest.TestCase):
    def test_agent_builds_timepro_through_quality_and_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = Manager(workspace=tmp).run(
                "Build TimePro, a timesheet application with employee entry, automatic hour calculation, history and manager dashboard."
            )
            root = Path(tmp)
            self.assertEqual(memory.status, "completed")
            self.assertTrue(memory.diagnostics.get("quality_passed"))
            self.assertTrue(memory.diagnostics.get("release_ready"))
            for required in ("index.html", "app.js", "README.md", "backend.py", "api_contract.json"):
                self.assertTrue((root / required).is_file(), required)
            self.assertTrue((root / ".app-builder" / "quality_report.json").is_file())
            self.assertTrue((root / ".app-builder" / "release_report.json").is_file())


if __name__ == "__main__":
    unittest.main()
