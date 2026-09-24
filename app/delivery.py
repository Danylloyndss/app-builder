"""End-to-end release delivery coordinator.

This module owns the deterministic hand-off from a verified bundle to an
external deployment provider. It never claims publication without provider
confirmation and a successful health check.
"""

from __future__ import annotations

from pathlib import Path

from .deployment_history import DeploymentHistory
from .deployment_runtime import DeploymentRuntime, DeploymentResult, HealthResult
from .release_controller import ReleaseController
from .release_fingerprint import bundle_fingerprint
from .release_verifier import ReleaseVerifier


class DeliveryCoordinator:
    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace)
        self.verifier = ReleaseVerifier()
        self.runtime = DeploymentRuntime()
        self.controller = ReleaseController(self.workspace)
        self.history = DeploymentHistory(self.workspace)

    def verify_bundle(self, bundle: str | Path) -> dict:
        result = self.verifier.verify(bundle)
        self.history.append(
            "bundle_verified" if result.get("ok") else "bundle_rejected",
            "control-plane",
            result.get("sha256"),
            result.get("error", ""),
        )
        return result

    def prepare(self, bundle: str | Path, require_approval: bool = True) -> dict:
        verification = self.verify_bundle(bundle)
        if not verification.get("ok"):
            self.controller.fail(verification.get("sha256"), verification.get("error", "bundle verification failed"))
            return {"ready": False, "verification": verification}
        release_hash = verification["sha256"]
        if require_approval:
            state = self.controller.request_approval(release_hash)
        else:
            state = self.controller.approve(release_hash)
        return {"ready": True, "release_hash": release_hash, "state": state, "verification": verification}

    def publish(self, provider: str, bundle: str | Path) -> DeploymentResult:
        verification = self.verify_bundle(bundle)
        if not verification.get("ok"):
            return DeploymentResult("bundle_rejected", provider, verification.get("sha256"), False, None, verification.get("error"))
        release_hash = verification["sha256"]
        current = self.controller.state.read()
        if current.get("release_hash") != release_hash:
            self.controller.state.set("ready", release_hash, reason="verified release selected")
        if self.controller.state.read().get("state") != "deploy_pending":
            self.controller.approve(release_hash)
        return self.controller.publish(provider, release_hash)

    def confirm_health(self, release_hash: str, health_url: str, timeout: float = 5.0) -> HealthResult:
        health = self.runtime.health_check(health_url, timeout)
        if health.ok:
            self.controller.state.set("published", release_hash, reason="deployment health check passed")
            self.history.append("published", "health-check", release_hash, f"{health_url} {health.status_code}")
        else:
            self.controller.fail(release_hash, health.error or "deployment health check failed")
        return health

    def bundle_hash(self, bundle: str | Path) -> str:
        return bundle_fingerprint(bundle)
