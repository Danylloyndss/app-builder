"""Release readiness and artifact manifest for App Builder."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json


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
        deployment_manifest = root / ".app-builder" / "deployment.json"
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
            artifacts[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        checks.extend(["quality gate passed", "required web artifacts present", "artifact hashes generated"])
        if production:
            checks.extend(["production Dockerfile present", "production deployment manifest present", "production readiness checks passed"])
        return ReleaseReport(True, checks, [], artifacts)
