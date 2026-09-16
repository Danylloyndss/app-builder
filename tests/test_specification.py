import json
import tempfile
import unittest
from pathlib import Path

from app.manager import Manager
from app.specification import SpecificationBuilder


class SpecificationTests(unittest.TestCase):
    def test_timesheet_spec_is_structured(self):
        spec = SpecificationBuilder().build(
            "Create a mobile timesheet app with login, forms, data storage and manager dashboard"
        )
        self.assertEqual(spec.app_type, "web")
        self.assertIn("mobile", spec.features)
        self.assertIn("authentication", spec.features)
        self.assertIn("dashboard", spec.features)
        self.assertIn("Manager", spec.users)
        self.assertIn("Dashboard", spec.screens)
        self.assertTrue(spec.acceptance_criteria)

    def test_manager_persists_specification(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            Manager(temp_dir).run("Create a mobile timesheet with forms and data storage")
            path = Path(temp_dir) / ".app-builder" / "spec.json"
            self.assertTrue(path.exists())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["app_type"], "web")
            self.assertIn("forms", data["features"])


if __name__ == "__main__":
    unittest.main()
