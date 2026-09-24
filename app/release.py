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

    def prepare(self, workspace: str | Path, quality_passed: bool) -> ReleaseReport:
        root = Path(workspace)
        blockers = []
        checks = []
        if not quality_passed:
            blockers.append("quality gate has not passed")
        if not (root / "index.html").is_file():
            blockers.append("index.html is missing")
        if not (root / "app.js").is_file():
            blockers.append("app.js is missing")
        if blockers:
            return ReleaseReport(False, checks, blockers, {})

        artifacts = {}
        for path in sorted(root.rglob("*")):
            if not path.is_file() or ".app-builder" in path.parts or ".git" in path.parts:
                continue
            artifacts[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        checks.extend(["quality gate passed", "required web artifacts present", "artifact hashes generated"])
        return ReleaseReport(True, checks, [], artifacts)
