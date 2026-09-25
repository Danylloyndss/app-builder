"""Release readiness and artifact manifest for App Builder."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json
import zipfile


@dataclass(frozen=True)
class ReleaseReport:
    ready: bool
    checks: list[str]
    blockers: list[str]
    artifacts: dict[str, str]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")


class ReleaseManager:
    """Prepare a deterministic release report; publishing remains approval-gated."""

    def prepare(self, workspace: str | Path, quality_passed: bool, production: bool = False,
                authentication_ready: bool = True, deployment_ready: bool = True) -> ReleaseReport:
        root = Path(workspace)
        blockers = []
        checks = []
        if not quality_passed:
            blockers.append("quality gate has not passed")
        if production and not authentication_ready:
            blockers.append("production authentication is not configured")
        if production and not deployment_ready:
            blockers.append("production deployment is not configured")
        if production and not (root / "Dockerfile").is_file():
            blockers.append("production Dockerfile is missing")
        if production and not (root / "railway.toml").is_file():
            blockers.append("production deployment manifest is missing")
        if not (root / "index.html").is_file():
            blockers.append("index.html is missing")
        if not (root / "app.js").is_file():
            blockers.append("app.js is missing")
        readme = root / "README.md"
        if not readme.is_file() or not readme.read_text(encoding="utf-8").strip():
            blockers.append("README.md is missing or empty")
        else:
            checks.append("README documentation present")
            try:
                readme_text = readme.read_text(encoding="utf-8").strip()
                if len(readme_text) < 20:
                    blockers.append("README.md is too short")
                elif not any(line.strip().startswith("#") for line in readme_text.splitlines()):
                    blockers.append("README.md has no heading")
            except OSError:
                blockers.append("README.md cannot be read")
        mobile_manifest = root / "manifest.webmanifest"
        if mobile_manifest.is_file():
            try:
                mobile = json.loads(mobile_manifest.read_text(encoding="utf-8"))
                if mobile.get("display") != "standalone" or not mobile.get("start_url"):
                    blockers.append("mobile install manifest is incomplete")
                elif not mobile.get("name") or not mobile.get("short_name"):
                    blockers.append("mobile install manifest has no app name")
                elif not isinstance(mobile.get("icons", []), list):
                    blockers.append("mobile install manifest icons are invalid")
                elif mobile.get("icons") and any(not isinstance(icon, dict) or not icon.get("src") for icon in mobile["icons"]):
                    blockers.append("mobile install manifest contains incomplete icons")
                else:
                    checks.append("mobile install manifest validated")
            except (OSError, ValueError):
                blockers.append("mobile install manifest is invalid JSON")
        if not mobile_manifest.is_file():
            checks.append("mobile install manifest not present; desktop release remains supported")
        deployment_manifest = root / ".app-builder" / "deployment.json"
        if production and not deployment_manifest.is_file():
            blockers.append("deployment readiness manifest is missing")
        if production and deployment_manifest.is_file():
            try:
                deployment = json.loads(deployment_manifest.read_text(encoding="utf-8"))
                if not deployment.get("configured"):
                    blockers.extend(str(x) for x in deployment.get("blockers", ["deployment adapter is not configured"]))
                else:
                    checks.append("deployment readiness manifest validated")
            except (OSError, ValueError):
                blockers.append("deployment manifest is invalid JSON")
        backend_manifest = root / ".app-builder" / "backend.json"
        if production and not backend_manifest.is_file():
            blockers.append("backend manifest is missing")
        if production and backend_manifest.is_file():
            try:
                manifest = json.loads(backend_manifest.read_text(encoding="utf-8"))
                if not manifest.get("entrypoint") or not manifest.get("health"):
                    blockers.append("backend manifest is incomplete")
                else:
                    checks.append("backend runtime manifest validated")
            except (OSError, ValueError):
                blockers.append("backend manifest is invalid JSON")
        if blockers:
            return ReleaseReport(False, checks, blockers, {})

        artifacts = {}
        for path in sorted(root.rglob("*")):
            if not path.is_file() or ".app-builder" in path.parts or ".git" in path.parts:
                continue
            relative = str(path.relative_to(root))
            if relative in {"state.json", "release.zip"}:
                continue
            artifacts[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        if not artifacts:
            return ReleaseReport(False, checks, ["no release artifacts were generated"], {})
        checks.append(f"release artifact inventory contains {len(artifacts)} file(s)")
        checks.extend(["quality gate passed", "required web artifacts present", "artifact hashes generated"])
        if production:
            checks.extend(["production Dockerfile present", "production deployment manifest present", "production readiness checks passed"])
        return ReleaseReport(True, checks, [], artifacts)

    def build_verified_bundle(self, workspace: str | Path, quality_passed: bool, production: bool = False) -> tuple[Path, ReleaseReport]:
        """Create a deterministic, hash-verified release bundle after quality passes.

        This is intentionally provider-neutral: creating the bundle is autonomous;
        publishing it remains a separate approval-gated action.
        """
        root = Path(workspace)
        report = self.prepare(root, quality_passed, production=production)
        if not report.ready:
            raise RuntimeError("; ".join(report.blockers))

        output = root / ".app-builder" / "release_bundle.zip"
        output.parent.mkdir(parents=True, exist_ok=True)
        manifest = {
            "format_version": 1,
            "production": bool(production),
            "ready": report.ready,
            "checks": report.checks,
            "blockers": report.blockers,
            "artifacts": report.artifacts,
        }
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for relative in sorted(report.artifacts):
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, (root / relative).read_bytes())
            info = zipfile.ZipInfo("release_report.json", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True))

        verification = self.verify_bundle(output, report)
        if not verification.get("ok"):
            raise RuntimeError(verification.get("error", "release bundle verification failed"))
        return output, report

    def verify_bundle(self, bundle: str | Path, report: ReleaseReport | None = None) -> dict:
        """Verify ZIP safety and every artifact hash before delivery."""
        path = Path(bundle)
        if not path.is_file():
            return {"ok": False, "error": "release bundle is missing"}
        try:
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                if len(names) != len(set(names)):
                    return {"ok": False, "error": "release bundle contains duplicate entries"}
                for name in names:
                    candidate = Path(name)
                    if candidate.is_absolute() or ".." in candidate.parts:
                        return {"ok": False, "error": "release bundle contains unsafe path"}
                if "release_report.json" not in names:
                    return {"ok": False, "error": "release report is missing"}
                release_report = json.loads(archive.read("release_report.json"))
                artifacts = release_report.get("artifacts", {})
                if not isinstance(artifacts, dict):
                    return {"ok": False, "error": "release report artifacts are invalid"}
                expected = set(artifacts) | {"release_report.json"}
                if set(names) != expected:
                    return {"ok": False, "error": "release bundle contents do not match release report"}
                for name, digest in artifacts.items():
                    if not isinstance(name, str) or not isinstance(digest, str) or len(digest) != 64:
                        return {"ok": False, "error": f"invalid artifact digest: {name}"}
                for name, digest in artifacts.items():
                    actual = hashlib.sha256(archive.read(name)).hexdigest()
                    if actual != digest:
                        return {"ok": False, "error": f"artifact hash mismatch: {name}"}
                return {"ok": True, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "artifact_count": len(artifacts)}
        except (OSError, ValueError, zipfile.BadZipFile, KeyError) as exc:
            return {"ok": False, "error": str(exc)}
