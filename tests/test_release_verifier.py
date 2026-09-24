import tempfile
import unittest
from pathlib import Path
import hashlib
import json
import zipfile

from app.release_fingerprint import bundle_fingerprint, is_same_release
from app.release_verifier import ReleaseVerifier
from app.delivery import DeliveryCoordinator


class ReleaseVerifierTests(unittest.TestCase):
    def test_verifier_accepts_valid_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "release.zip"
            payload = b"hello"
            digest = hashlib.sha256(payload).hexdigest()
            with zipfile.ZipFile(bundle, "w") as z:
                z.writestr("app.js", payload)
                z.writestr("release_report.json", json.dumps({"artifacts": {"app.js": digest}}))
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
            manifest.write_text(json.dumps({"bundle_sha256": bundle_fingerprint(bundle)}))
            self.assertTrue(is_same_release(root, bundle))

    def _bundle(self, root: Path) -> Path:
        bundle = root / "release.zip"
        payload = b"TimePro"
        digest = hashlib.sha256(payload).hexdigest()
        with zipfile.ZipFile(bundle, "w") as z:
            z.writestr("app.js", payload)
            z.writestr("release_report.json", json.dumps({"artifacts": {"app.js": digest}}))
        return bundle

    def test_delivery_requires_approval_after_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = DeliveryCoordinator(tmp).prepare(self._bundle(Path(tmp)))
            self.assertTrue(result["ready"])
            self.assertEqual(result["state"]["state"], "awaiting_approval")

    def test_invalid_bundle_cannot_enter_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.zip"
            bad.write_bytes(b"not zip")
            result = DeliveryCoordinator(tmp).prepare(bad)
            self.assertFalse(result["ready"])

    def test_provider_publish_remains_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._bundle(Path(tmp))
            coordinator = DeliveryCoordinator(tmp)
            coordinator.prepare(bundle, require_approval=False)
            result = coordinator.publish("railway", bundle)
            self.assertTrue(result.external_action_required)


if __name__ == "__main__":
    unittest.main()
