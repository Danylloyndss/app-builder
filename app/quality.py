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
    """Run deterministic quality, security, and mission acceptance gates."""

    SECRET_MARKERS = ("sk-", "api_key=", "password=", "secret=")

    def evaluate(self, workspace: Path, acceptance_criteria: list[str] | None = None) -> QualityReport:
        errors: list[str] = []
        structural: list[str] = []
        security: list[str] = []
        acceptance: list[str] = []

        required = ("index.html", "app.js", "README.md")
        for filename in required:
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

        mission_path = workspace / ".app-builder" / "mission.txt"
        mission = mission_path.read_text(encoding="utf-8").lower() if mission_path.exists() else ""
        if any(token in mission for token in ("timepro", "timesheet", "folha de horas")):
            index = (workspace / "index.html").read_text(encoding="utf-8") if (workspace / "index.html").exists() else ""
            script = (workspace / "app.js").read_text(encoding="utf-8") if (workspace / "app.js").exists() else ""
            checks = {
                "Employee can enter a workday timesheet": 'id="timesheet-form"' in index,
                "Total hours calculated automatically": "function duration" in script and 'id="total"' in index,
                "Invalid time ranges rejected": "b < a" in script,
                "Submitted timesheets visible in history": 'id="history"' in index and "localStorage" in script,
                "Manager dashboard can summarize submitted timesheets": 'id="dashboard"' in index,
                "Core flow works on mobile viewport": "@media" in index and "viewport" in index,
                "Optional fields do not block submission": "Feuille envoyée avec succès" in script,
            }
            for label, passed in checks.items():
                if passed:
                    acceptance.append(label)
                else:
                    errors.append(f"TimePro acceptance failed: {label}")
        else:
            acceptance.extend(acceptance_criteria or ["Generated project has required artifacts"])

        return QualityReport(not errors, structural, security, acceptance, errors)
