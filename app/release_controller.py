"""Release orchestration between readiness, approval, and deployment."""

from __future__ import annotations

from pathlib import Path

from .deployment_history import DeploymentHistory
from .deployment_runtime import DeploymentRuntime, DeploymentResult
from .release_state import ReleaseState


class ReleaseController:
    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace)
        self.state = ReleaseState(self.workspace)
        self.history = DeploymentHistory(self.workspace)
        self.runtime = DeploymentRuntime()

    def request_approval(self, release_hash: str | None) -> dict:
        value = self.state.set("awaiting_approval", release_hash, reason="release requires human approval")
        self.history.append("awaiting_approval", "control-plane", release_hash, "human approval required")
        return value

    def approve(self, release_hash: str | None) -> dict:
        value = self.state.set("deploy_pending", release_hash, reason="human approval granted")
        self.history.append("deploy_pending", "control-plane", release_hash, "approval granted")
        return value

    def publish(self, provider: str, release_hash: str | None) -> DeploymentResult:
        result = self.runtime.publish(provider, release_hash)
        if result.external_action_required:
            self.state.set("deploy_pending", release_hash, reason="provider authentication/action required")
        else:
            self.state.set("published", release_hash, reason="deployment completed")
        self.history.append(result.status, provider, release_hash, result.error or "")
        self.runtime.save_result(self.workspace, result)
        return result

    def fail(self, release_hash: str | None, reason: str) -> dict:
        value = self.state.set("failed", release_hash, reason=reason)
        self.history.append("failed", "control-plane", release_hash, reason)
        return value

    def rollback(self, release_hash: str | None, reason: str = "rollback requested") -> dict:
        value = self.state.set("rolled_back", release_hash, reason=reason)
        self.history.append("rolled_back", "control-plane", release_hash, reason)
        return value
