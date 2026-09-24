"""Release orchestration between readiness, approval, and deployment."""

from __future__ import annotations

from pathlib import Path

from .deployment_history import DeploymentHistory
from .deployment_attempts import DeploymentAttempts
from .deployment_runtime import DeploymentRuntime, DeploymentResult
from .release_state import ReleaseState


class ReleaseController:
    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace)
        self.state = ReleaseState(self.workspace)
        self.history = DeploymentHistory(self.workspace)
        self.runtime = DeploymentRuntime()
        self.attempts = DeploymentAttempts(self.workspace)

    def request_approval(self, release_hash: str | None) -> dict:
        value = self.state.set("awaiting_approval", release_hash, reason="release requires human approval")
        self.history.append("awaiting_approval", "control-plane", release_hash, "human approval required")
        return value

    def approve(self, release_hash: str | None) -> dict:
        value = self.state.set("deploy_pending", release_hash, reason="human approval granted")
        self.history.append("deploy_pending", "control-plane", release_hash, "approval granted")
        return value

    def publish(self, provider: str, release_hash: str | None) -> DeploymentResult:
        current = self.state.read()
        if release_hash and current.get("release_hash") not in {None, release_hash}:
            raise ValueError("release hash does not match selected release")
        attempt = self.attempts.begin(provider, release_hash or "")
        if not attempt.get("allowed"):
            result = DeploymentResult("deployment_blocked", provider, release_hash, False, None, attempt.get("reason"))
            self.history.append(result.status, provider, release_hash, result.error or "")
            self.runtime.save_result(self.workspace, result)
            return result
        result = self.runtime.publish(provider, release_hash, self.workspace)
        if result.external_action_required:
            self.state.set("deploy_pending", release_hash, reason="provider authentication/action required")
            self.attempts.finish(attempt["attempt_id"], "waiting_external_action", error=result.error)
        elif result.status in {"queued", "running"}:
            self.state.set("deploy_pending", release_hash, reason="deployment queued")
            self.attempts.finish(attempt["attempt_id"], result.status, deployment_id=getattr(result, "deployment_id", None), url=getattr(result, "url", None))
        elif result.status == "failed":
            self.state.set("failed", release_hash, reason=result.error or "deployment failed")
            self.attempts.finish(attempt["attempt_id"], "failed", error=result.error)
        else:
            self.state.set("published", release_hash, reason="deployment completed")
            self.attempts.finish(attempt["attempt_id"], "published", deployment_id=getattr(result, "deployment_id", None), url=getattr(result, "url", None))
        self.history.append(result.status, provider, release_hash, result.error or "")
        self.runtime.save_result(self.workspace, result)
        return result

    def check_deployment(self, provider: str, release_hash: str | None, deployment_id: str) -> DeploymentResult:
        result = self.runtime.deployment_status(provider, deployment_id, self.workspace)
        if result.status == "published":
            self.state.set("published", release_hash, reason="provider reports deployment successful")
        elif result.status == "failed":
            self.state.set("failed", release_hash, reason=result.error or "provider reports deployment failure")
        else:
            self.state.set("deploy_pending", release_hash, reason="provider deployment still in progress")
        self.history.append("deployment_status", provider, release_hash, result.status)
        self.runtime.save_result(self.workspace, result)
        return result

    def recover_deployment(self, provider: str, release_hash: str) -> DeploymentResult | None:
        items = self.attempts._load()
        candidates = [x for x in items if x.get("provider") == provider and x.get("release_hash") == release_hash and x.get("deployment_id")]
        if not candidates:
            return None
        latest = candidates[-1]
        if latest.get("status") not in {"queued", "running", "waiting_external_action"}:
            return None
        return self.check_deployment(provider, release_hash, str(latest["deployment_id"]))

    def fail(self, release_hash: str | None, reason: str) -> dict:
        value = self.state.set("failed", release_hash, reason=reason)
        self.history.append("failed", "control-plane", release_hash, reason)
        return value

    def rollback(self, release_hash: str | None, reason: str = "rollback requested") -> dict:
        value = self.state.set("rolled_back", release_hash, reason=reason)
        self.history.append("rolled_back", "control-plane", release_hash, reason)
        return value
