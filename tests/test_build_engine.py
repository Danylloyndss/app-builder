import json
import tempfile
import unittest
from pathlib import Path

from app.build_engine import BuildEngine
from app.manager import Manager


class BuildEngineTests(unittest.TestCase):
    def test_generates_real_web_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = Manager(temp_dir).run("Create a simple expense tracker")
            self.assertEqual(memory.status, "completed")
            self.assertFalse(memory.errors)
            self.assertTrue((Path(temp_dir) / "index.html").exists())
            self.assertTrue((Path(temp_dir) / "app.js").exists())
            self.assertTrue((Path(temp_dir) / "README.md").exists())

    def test_timesheet_features_generate_real_ui(self) -> None:
        mission = "Create a mobile timesheet with forms, data storage and manager dashboard"
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = BuildEngine(Path(temp_dir))
            engine.create_structure(mission)
            engine.implement_feature("forms", mission)
            engine.implement_feature("storage", mission)
            engine.implement_feature("dashboard", mission)
            engine.implement_feature("mobile", mission)
            engine.implement_feature("calculator", mission)

            html = (Path(temp_dir) / "index.html").read_text(encoding="utf-8")
            js = (Path(temp_dir) / "app.js").read_text(encoding="utf-8")
            features = json.loads((Path(temp_dir) / ".app-builder" / "features.json").read_text(encoding="utf-8"))

            self.assertIn('name="location"', html)
            self.assertIn('id="total"', html)
            self.assertIn("localStorage", js)
            self.assertIn("dashboard", features)
            self.assertIn("mobile", features)

    def test_html_escapes_mission(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = BuildEngine(Path(temp_dir))
            engine.implement("<script>alert('x')</script>")
            html = (Path(temp_dir) / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("<script>alert('x')</script>", html)


if __name__ == "__main__":
    unittest.main()
