"""Independent verification of deterministic release bundles."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import zipfile


class ReleaseVerifier:
    def verify(self, bundle: str | Path, expected_hash: str | None = None) -> dict:
        path = Path(bundle)
        if not path.is_file():
            return {"ok": False, "error": "release bundle is missing"}
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected_hash and digest != expected_hash:
            return {"ok": False, "error": "bundle sha256 mismatch", "sha256": digest}
        try:
            with zipfile.ZipFile(path) as archive:
                if archive.testzip() is not None:
                    return {"ok": False, "error": "zip integrity check failed", "sha256": digest}
                if "release_report.json" not in archive.namelist():
                    return {"ok": False, "error": "release report is missing", "sha256": digest}
                report = json.loads(archive.read("release_report.json"))
                artifacts = report.get("artifacts", {})
                missing = [name for name in artifacts if name not in archive.namelist()]
                mismatched = []
                for name, expected in artifacts.items():
                    if name in archive.namelist():
                        actual = hashlib.sha256(archive.read(name)).hexdigest()
                        if actual != expected:
                            mismatched.append(name)
                if missing or mismatched:
                    return {"ok": False, "error": "artifact integrity mismatch", "missing": missing, "mismatched": mismatched, "sha256": digest}
                return {
                    "ok": True,
                    "sha256": digest,
                    "artifact_count": len(artifacts),
                    "production": bool(report.get("production", False)),
                }
        except (OSError, ValueError, zipfile.BadZipFile, KeyError) as exc:
            return {"ok": False, "error": str(exc), "sha256": digest}
