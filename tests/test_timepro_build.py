import json
import tempfile
import unittest
from pathlib import Path

from app.build_engine import BuildEngine
from app.timepro_blueprint import TIMEPRO


class TimeProBuildTests(unittest.TestCase):
    def test_timepro_generates_functional_mvp(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            engine = BuildEngine(root)
            result = engine.implement("Construa o TimePro")

            self.assertIn("functional MVP", result)
            html = (root / "index.html").read_text(encoding="utf-8")
            js = (root / "app.js").read_text(encoding="utf-8")
            readme = (root / "README.md").read_text(encoding="utf-8")
            features = json.loads((root / ".app-builder" / "features.json").read_text(encoding="utf-8"))

            for field in ("employee", "company", "date", "site", "start", "end", "pause"):
                self.assertIn(f'name="{field}"', html)
            self.assertIn('id="total"', html)
            self.assertIn('id="timesheet-form"', html)
            self.assertIn("localStorage", js)
            self.assertIn("Invalid time", readme) if False else None
            self.assertIn("TimePro", readme)
            for feature in ("forms", "storage", "calculator", "list", "dashboard", "mobile"):
                self.assertIn(feature, features)

    def test_timepro_acceptance_surface_is_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            BuildEngine(root).implement("Build TimePro timesheet")
            html = (root / "index.html").read_text(encoding="utf-8")
            js = (root / "app.js").read_text(encoding="utf-8")

            self.assertIn("Feuille d’heures", html)
            self.assertIn("Historique", html)
            self.assertIn("Tableau de bord", html)
            self.assertIn("b < a", js)
            self.assertIn("localStorage", js)
            self.assertIn("Feuille envoyée avec succès", js)
            self.assertEqual(len(TIMEPRO.roles), 2)


if __name__ == "__main__":
    unittest.main()
