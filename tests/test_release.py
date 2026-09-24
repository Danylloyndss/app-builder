import json
import tempfile
import unittest
from pathlib import Path

from app.release import ReleaseManager


class ReleaseManagerTests(unittest.TestCase):
    def _base(self, root):
        (root / "index.html").write_text("<html></html>", encoding="utf-8")
        (root / "app.js").write_text("console.log('ok')", encoding="utf-8")
        (root / "README.md").write_text("# App", encoding="utf-8")

    def test_release_requires_readme(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "index.html").write_text("<html></html>", encoding="utf-8")
            (root / "app.js").write_text("console.log('ok')", encoding="utf-8")
            report = ReleaseManager().prepare(root, True)
            self.assertFalse(report.ready)
            self.assertIn("README.md is missing or empty", report.blockers)

    def test_release_accepts_valid_mobile_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._base(root)
            (root / "manifest.webmanifest").write_text(json.dumps({
                "name": "Test App", "short_name": "Test", "start_url": "/", "display": "standalone",
                "icons": [{"src": "icon-192.png"}]
            }), encoding="utf-8")
            report = ReleaseManager().prepare(root, True)
            self.assertTrue(report.ready)
            self.assertIn("mobile install manifest validated", report.checks)


    def test_release_rejects_incomplete_icon_entry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._base(root)
            (root / "manifest.webmanifest").write_text(json.dumps({
                "name": "Test App", "short_name": "Test", "start_url": "/", "display": "standalone",
                "icons": [{"sizes": "192x192"}]
            }), encoding="utf-8")
            report = ReleaseManager().prepare(root, True)
            self.assertFalse(report.ready)
            self.assertIn("mobile install manifest contains incomplete icons", report.blockers)

    def test_release_rejects_incomplete_mobile_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._base(root)
            (root / "manifest.webmanifest").write_text(json.dumps({
                "name": "Test App", "short_name": "Test", "start_url": "/", "display": "browser"
            }), encoding="utf-8")
            report = ReleaseManager().prepare(root, True)
            self.assertFalse(report.ready)
            self.assertIn("mobile install manifest is incomplete", report.blockers)


if __name__ == "__main__":
    unittest.main()
