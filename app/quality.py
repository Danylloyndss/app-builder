"""Quality and security gates for generated App Builder projects."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re

from .project_validator import ProjectValidator


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
        validator = ProjectValidator()
        valid, contract_errors = validator.validate(workspace)
        if valid:
            structural.append("Generated project contract passed")
        else:
            errors.extend(contract_errors)
        security: list[str] = []
        acceptance: list[str] = []

        required = ("index.html", "app.js", "README.md")
        for filename in required:
            path = workspace / filename
            if path.exists() and path.read_text(encoding="utf-8").strip():
                structural.append(f"{filename} exists and is non-empty")
            else:
                errors.append(f"Missing or empty required artifact: {filename}")

        skip_dirs = {".git", ".app-builder", "__pycache__", "node_modules"}
        for path in workspace.rglob("*"):
            if not path.is_file() or any(part in skip_dirs for part in path.parts):
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

        # Reject common executable payloads disguised as ordinary project files.
        dangerous = re.compile(r"(?:^|\n)\s*(?:curl|wget)\s+[^\n]*(?:\||;)\s*(?:sh|bash)|(?:eval\s*\(|os\.system\s*\()", re.I)
        for path in workspace.rglob("*"):
            if not path.is_file() or any(part in skip_dirs for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if dangerous.search(text):
                errors.append(f"Potentially unsafe executable payload found in {path.relative_to(workspace)}")
        if not any("unsafe executable" in error.lower() for error in errors):
            security.append("No obvious shell-download/eval payloads detected")

        # The saved specification is the source of truth. Fall back to the
        # mission file for older workspaces that predate spec.json.
        mission = ""
        spec_path = workspace / ".app-builder" / "spec.json"
        if spec_path.exists():
            try:
                spec = json.loads(spec_path.read_text(encoding="utf-8"))
                mission = str(spec.get("app_name", "")) + " " + str(spec.get("mission", ""))
            except (json.JSONDecodeError, OSError):
                mission = ""
        if not mission:
            mission_path = workspace / ".app-builder" / "mission.txt"
            if mission_path.exists():
                mission = mission_path.read_text(encoding="utf-8")
        mission = mission.lower()

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
            requested = acceptance_criteria or ["Generated project has required artifacts"]
            artifact_map = {
                "form": "form-schema.json",
                "dashboard": "dashboard.json",
                "mobile": "mobile.json",
                "calculator": "calculator.json",
                "history": "list.json",
            }
            spec_features = []
            try:
                spec_data = json.loads((workspace / ".app-builder" / "spec.json").read_text(encoding="utf-8"))
                spec_features = [str(x).lower() for x in spec_data.get("features", [])]
            except (OSError, ValueError, TypeError):
                pass
            for criterion in requested:
                matched = next((feature for feature, artifact in artifact_map.items()
                                 if feature in criterion.lower() and feature in spec_features), None)
                if matched:
                    artifact = workspace / artifact_map[matched]
                    if artifact.exists() and artifact.read_text(encoding="utf-8").strip():
                        acceptance.append(criterion)
                    else:
                        errors.append(f"Feature artifact missing: {artifact_map[matched]}")
                else:
                    acceptance.append(criterion)

        # Generic feature behavior must exist in executable UI code, not only metadata.
        if "timepro" not in mission:
            script = (workspace / "app.js").read_text(encoding="utf-8") if (workspace / "app.js").exists() else ""
            if "forms" in spec_features and "data-save" not in ((workspace / "index.html").read_text(encoding="utf-8") if (workspace / "index.html").exists() else ""):
                errors.append("Generic forms feature has no save form")
            if "storage" in spec_features and "fetch" not in script and "localStorage" not in script:
                errors.append("Generic storage feature has no persistence client")
            if "dashboard" in spec_features and "metric-records" not in ((workspace / "index.html").read_text(encoding="utf-8") if (workspace / "index.html").exists() else ""):
                errors.append("Generic dashboard has no metric output")
            if "list" in spec_features and "history-list" not in ((workspace / "index.html").read_text(encoding="utf-8") if (workspace / "index.html").exists() else ""):
                errors.append("Generic list feature has no history output")

        return QualityReport(not errors, structural, security, acceptance, errors)
