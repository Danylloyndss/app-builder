import tempfile
import unittest
from pathlib import Path
from app.manager import Manager

class ManagerDiagnosticsTests(unittest.TestCase):
    def test_manager_debug(self):
        for mission in ["Create a mobile timesheet app with forms, data storage and manager dashboard", "Construa o TimePro"]:
            with self.subTest(mission=mission), tempfile.TemporaryDirectory() as temp_dir:
                root=Path(temp_dir)
                memory=Manager(str(root)).run(mission)
                report=root/".app-builder"/"quality_report.json"
                self.assertEqual(memory.status,"completed", f"status={memory.status} errors={memory.errors} diagnostics={memory.diagnostics} report={(report.read_text() if report.exists() else 'MISSING')}")

if __name__ == "__main__": unittest.main()
