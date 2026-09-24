"""Railway deployment adapter with explicit authentication boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import subprocess
import json


@dataclass(frozen=True)
class RailwayResult:
    status: str
    external_action_required: bool
    deployment_id: str | None = None
    url: str | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "external_action_required": self.external_action_required,
            "deployment_id": self.deployment_id,
            "url": self.url,
            "error": self.error,
        }


class RailwayProvider:
    """Deploy through the Railway CLI only when credentials are already available."""

    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace)

    def authenticated(self) -> bool:
        return bool(os.environ.get("RAILWAY_API_TOKEN") or os.environ.get("RAILWAY_TOKEN"))

    def publish(self, timeout: int = 900) -> RailwayResult:
        if not self.authenticated():
            return RailwayResult(
                "external_action_required",
                True,
                error="Railway authentication is required before deployment",
            )
        command = ["railway", "up", "--detach", "--json"]
        try:
            completed = subprocess.run(
                command,
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return RailwayResult("failed", False, error=str(exc))
        if completed.returncode != 0:
            return RailwayResult("failed", False, error=completed.stderr[-4000:] or completed.stdout[-4000:])
        payload = self._parse(completed.stdout)
        return RailwayResult(
            "queued",
            False,
            deployment_id=str(payload.get("deploymentId") or payload.get("id") or "") or None,
            url=payload.get("url"),
        )

    def status(self, deployment_id: str, timeout: int = 60) -> RailwayResult:
        if not self.authenticated():
            return RailwayResult("external_action_required", True, deployment_id=deployment_id, error="Railway authentication is required")
        command = ["railway", "status", "--json"]
        try:
            completed = subprocess.run(command, cwd=str(self.workspace), capture_output=True, text=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return RailwayResult("failed", False, deployment_id=deployment_id, error=str(exc))
        if completed.returncode != 0:
            return RailwayResult("failed", False, deployment_id=deployment_id, error=completed.stderr[-4000:] or completed.stdout[-4000:])
        payload = self._parse(completed.stdout)
        state = str(payload.get("status") or payload.get("state") or "").lower()
        mapping = {"success": "published", "successful": "published", "deployed": "published", "failed": "failed", "crashed": "failed", "building": "running", "deploying": "running", "queued": "queued"}
        return RailwayResult(mapping.get(state, "running"), False, deployment_id=deployment_id, url=payload.get("url"))
    
    @staticmethod
    def _parse(output: str) -> dict:
        for line in reversed(output.splitlines()):
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    return value
            except ValueError:
                continue
        return {}
