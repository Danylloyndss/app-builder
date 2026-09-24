import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from app.server import _release_bundle


class ReleaseBundleTests(unittest.TestCase):
    def test_release_bundle_is_complete_and_hash_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<html></html>", encoding="utf-8")
            (root / "app.js").write_text("console.log('ok')", encoding="utf-8")
            out, report = _release_bundle(root)
            self.assertTrue(report.ready)
            self.assertTrue(out.is_file())
            with ZipFile(out) as bundle:
                self.assertEqual(
                    set(bundle.namelist()),
                    set(report.artifacts) | {"release_report.json"},
                )
                self.assertEqual(
                    bundle.read("index.html"),
                    b"<html></html>",
                )
                self.assertIn(b'"ready": true', bundle.read("release_report.json"))


if __name__ == "__main__":
    unittest.main()
