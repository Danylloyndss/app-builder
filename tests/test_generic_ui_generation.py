import json
import tempfile
import unittest
from pathlib import Path

from app.build_engine import BuildEngine


class GenericUiGenerationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_form_matches_mission_schema(self):
        engine = BuildEngine(self.workspace)
        engine.implement("Create an expense tracker with a form and data storage")
        html = (self.workspace / "index.html").read_text(encoding="utf-8")
        self.assertIn('name="amount"', html)
        self.assertIn('name="note"', html)
        self.assertNotIn('name="start"', html)

    def test_mobile_generates_install_manifest(self):
        engine = BuildEngine(self.workspace)
        engine.implement("Create a mobile client manager with forms and responsive support")
        manifest = json.loads((self.workspace / "manifest.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual(manifest["display"], "standalone")
        mobile = json.loads((self.workspace / "mobile.json").read_text(encoding="utf-8"))
        self.assertEqual(mobile["display_mode"], "standalone")
        self.assertTrue(mobile["install_prompt_ready"])

    def test_history_is_readable(self):
        engine = BuildEngine(self.workspace)
        engine.implement("Create a client history list with data storage")
        script = (self.workspace / "app.js").read_text(encoding="utf-8")
        self.assertIn("Object.entries(record", script)


if __name__ == "__main__":
    unittest.main()
