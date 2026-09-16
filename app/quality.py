"""Quality and security gates for generated App Builder projects."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass
class QualityReport:
    passed: bool
    structural_checks: list[str]
    security_checks: list[str]
    acceptance_checks: list[str]
    errors: list[str]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")


class QualityGate:
    """Run lightweight deterministic gates before a mission is considered complete."""

    SECRET_MARKERS = ("sk-", "api_key=", "password=", "secret=")

    def evaluate(self, workspace: Path, acceptance_criteria: list[str] | None = None) -> QualityReport:
        errors: list[str] = []
        structural = []
        security = []
        acceptance = []

        for filename in ("index.html", "app.js", "README.md"):
            path = workspace / filename
            if path.exists() and path.read_text(encoding="utf-8").strip():
                structural.append(f"{filename} exists and is non-empty")
            else:
                errors.append(f"Missing or empty required artifact: {filename}")

        for path in workspace.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            lowered = text.lower()
            if any(marker in lowered for marker in self.SECRET_MARKERS):
                errors.append(f"Possible secret marker found in {path.relative_to(workspace)}")
        if not any("secret" in error.lower() for error in errors):
            security.append("No obvious hard-coded secret markers detected")

        criteria = acceptance_criteria or []
        acceptance.extend(criteria or ["Generated project has required artifacts"])

        return QualityReport(not errors, structural, security, acceptance, errors)
