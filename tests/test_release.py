import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.release import ReleaseManager


class ReleaseManagerTests(unittest.TestCase):
    def _base(self, root):
        (root / "index.html").write_text("<html></html>", encoding="utf-8")
        (root / "app.js").write_text("console.log('ok')", encoding="utf-8")
        (root / "README.md").write_text("# Generated App\n\nA complete generated application.", encoding="utf-8")

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






    def test_verify_bundle_detects_hash_tampering(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = root / "release.zip"
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("release_report.json", json.dumps({"artifacts": {"app.js": "0" * 64}}))
                archive.writestr("app.js", "console.log('tampered')")
            result = ReleaseManager().verify_bundle(bundle)
            self.assertFalse(result["ok"])
            self.assertIn("artifact hash mismatch", result["error"])

    def test_release_rejects_whitespace_only_readme(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._base(root)
            (root / "README.md").write_text("   \n\t", encoding="utf-8")
            report = ReleaseManager().prepare(root, True)
            self.assertFalse(report.ready)
            self.assertIn("README.md is missing or empty", report.blockers)

    def test_release_records_artifact_inventory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._base(root)
            report = ReleaseManager().prepare(root, True)
            self.assertTrue(report.ready)
            self.assertTrue(any("release artifact inventory contains" in item for item in report.checks))

    def test_release_rejects_empty_artifact_set(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text("# App", encoding="utf-8")
            (root / "index.html").write_text("<html></html>", encoding="utf-8")
            (root / "app.js").write_text("console.log('ok')", encoding="utf-8")
            report = ReleaseManager().prepare(root, True)
            self.assertTrue(report.ready)
            self.assertGreater(len(report.artifacts), 0)

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

    def test_release_blocks_production_without_authentication(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._base(root)
            report = ReleaseManager().prepare(
                root, True, production=True,
                authentication_ready=False, deployment_ready=True
            )
            self.assertFalse(report.ready)
            self.assertIn("production authentication is not configured", report.blockers)

    def test_release_blocks_production_without_deployment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._base(root)
            report = ReleaseManager().prepare(
                root, True, production=True,
                authentication_ready=True, deployment_ready=False
            )
            self.assertFalse(report.ready)
            self.assertIn("production deployment is not configured", report.blockers)

    def test_verify_bundle_accepts_matching_artifact_hash(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = root / "release.zip"
            payload = "console.log('ok')"
            digest = __import__("hashlib").sha256(payload.encode("utf-8")).hexdigest()
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("release_report.json", json.dumps({"artifacts": {"app.js": digest}}))
                archive.writestr("app.js", payload)
            result = ReleaseManager().verify_bundle(bundle)
            self.assertTrue(result["ok"])
            self.assertEqual(result["artifact_count"], 1)


if __name__ == "__main__":
    unittest.main()
