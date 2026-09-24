import tempfile
import unittest
from pathlib import Path
import zipfile

from app.release_fingerprint import bundle_fingerprint, is_same_release
from app.release_verifier import ReleaseVerifier


class ReleaseVerifierTests(unittest.TestCase):
    def test_verifier_accepts_valid_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "release.zip"
            payload = b"hello"
            digest = __import__("hashlib").sha256(payload).hexdigest()
            with zipfile.ZipFile(bundle, "w") as z:
                z.writestr("app.js", payload)
                z.writestr("release_report.json", __import__("json").dumps({"artifacts": {"app.js": digest}}))
            result = ReleaseVerifier().verify(bundle)
            self.assertTrue(result["ok"])
            self.assertEqual(result["artifact_count"], 1)

    def test_fingerprint_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "release.zip"
            bundle.write_bytes(b"release")
            manifest = root / ".app-builder" / "bundle_manifest.json"
            manifest.parent.mkdir()
            manifest.write_text(__import__("json").dumps({"bundle_sha256": bundle_fingerprint(bundle)}))
            self.assertTrue(is_same_release(root, bundle))


if __name__ == "__main__":
    unittest.main()
