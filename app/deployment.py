"""Deployment planning and readiness adapters for App Builder V1."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json


@dataclass(frozen=True)
class DeploymentPlan:
    platform: str
    runtime: str
    command: str
    healthcheck: str
    port: int
    configured: bool
    blockers: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


class DeploymentAdapter:
    """Provider-neutral deployment readiness; never publishes without an external adapter."""

    platform = "generic"

    def plan(self, workspace: str | Path) -> DeploymentPlan:
        root = Path(workspace)
        blockers: list[str] = []
        runtime, command, health, port = "python", "python -m app.server", "/health", 8080
        railway = root / "railway.toml"
        if railway.exists():
            text = railway.read_text(encoding="utf-8")
            if "startCommand" not in text:
                blockers.append("railway start command is missing")
            if "healthcheckPath" not in text:
                blockers.append("railway healthcheck is missing")
        else:
            blockers.append("deployment manifest is missing")
        return DeploymentPlan("railway" if railway.exists() else self.platform, runtime, command, health, port, not blockers, blockers)

    def save(self, workspace: str | Path) -> Path:
        root = Path(workspace)
        path = root / ".app-builder" / "deployment.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.plan(root).to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path
