import tempfile
import unittest
from pathlib import Path

from app.project_validator import ProjectValidator


class ProjectValidatorTests(unittest.TestCase):
    def test_rejects_missing_script_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text(
                '<html><head><meta name="viewport" content="width=device-width"></head>'
                '<body><script src="missing.js"></script></body></html>',
                encoding="utf-8",
            )
            (root / "app.js").write_text("document.body;", encoding="utf-8")
            (root / "README.md").write_text("# App", encoding="utf-8")
            ok, errors = ProjectValidator().validate(root)
            self.assertFalse(ok)
            self.assertIn("HTML references missing script: missing.js", errors)

    def test_accepts_valid_generated_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text(
                '<html><head><meta name="viewport" content="width=device-width"></head>'
                '<body><script src="app.js"></script></body></html>',
                encoding="utf-8",
            )
            (root / "app.js").write_text("document.body;", encoding="utf-8")
            (root / "README.md").write_text("# App", encoding="utf-8")
            ok, errors = ProjectValidator().validate(root)
            self.assertTrue(ok)
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
