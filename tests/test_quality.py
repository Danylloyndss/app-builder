import tempfile
import unittest
from pathlib import Path

from app.quality import QualityGate


class QualityGateTests(unittest.TestCase):
    def test_valid_generated_shape_passes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "index.html").write_text("<html></html>", encoding="utf-8")
            (root / "app.js").write_text("console.log('ok')", encoding="utf-8")
            (root / "README.md").write_text("# App", encoding="utf-8")
            report = QualityGate().evaluate(root, ["required artifacts exist"])
            self.assertTrue(report.passed)
            self.assertFalse(report.errors)

    def test_secret_marker_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "index.html").write_text("<html></html>", encoding="utf-8")
            (root / "app.js").write_text("const api_key='secret';", encoding="utf-8")
            (root / "README.md").write_text("# App", encoding="utf-8")
            report = QualityGate().evaluate(root)
            self.assertFalse(report.passed)
            self.assertTrue(report.errors)


if __name__ == "__main__":
    unittest.main()
