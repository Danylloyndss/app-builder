"""Provider-neutral deployment runtime primitives.

The runtime deliberately separates local verification from provider publishing.
Publishing is an explicit adapter operation and is never simulated as success.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import subprocess
import time
import urllib.error
import urllib.request
import ipaddress
import socket
import ipaddress
import socket


@dataclass(frozen=True)
class HealthResult:
    ok: bool
    url: str
    status_code: int | None
    elapsed_ms: int
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class DeploymentResult:
    status: str
    provider: str
    release_hash: str | None
    external_action_required: bool
    health: HealthResult | None
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class DeploymentRuntime:
    """Execute only explicitly supported local verification primitives."""

    def health_check(self, url: str, timeout: float = 5.0) -> HealthResult:
        started = time.monotonic()
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError("health URL must use http or https")
            host = parsed.hostname
            addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
            for address in addresses:
                ip = ipaddress.ip_address(address)
                if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved:
                    raise ValueError("health URL resolves to a restricted network address")
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError("health URL must use http or https")
            host = parsed.hostname
            try:
                addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
            except socket.gaierror:
                addresses = set()
            for address in addresses:
                ip = ipaddress.ip_address(address)
                if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved:
                    raise ValueError("health URL resolves to a restricted network address")
            with urllib.request.urlopen(url, timeout=timeout) as response:
                code = int(response.status)
                return HealthResult(200 <= code < 300, url, code, int((time.monotonic() - started) * 1000), None if 200 <= code < 300 else f"unexpected HTTP status: {code}")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            return HealthResult(False, url, None, int((time.monotonic() - started) * 1000), str(exc))

    def verify_command(self, command: list[str], cwd: str | Path, timeout: int = 60) -> dict:
        """Run a bounded verification command; never accepts shell strings."""
        if not command or any(not isinstance(part, str) or not part for part in command):
            raise ValueError("command must be a non-empty argv list")
        result = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[-8000:],
            "stderr": result.stderr[-8000:],
        }

    def publish(self, provider: str, release_hash: str | None, workspace: str | Path = ".") -> DeploymentResult:
        """Publish through a real provider adapter or require an external action."""
        if provider.lower() == "railway":
            from .railway_provider import RailwayProvider
            result = RailwayProvider(workspace).publish()
            return DeploymentResult(
                status=result.status,
                provider=provider,
                release_hash=release_hash,
                external_action_required=result.external_action_required,
                health=None,
                error=result.error,
            )
        return DeploymentResult(
            status="external_action_required",
            provider=provider,
            release_hash=release_hash,
            external_action_required=True,
            health=None,
            error=f"No authenticated publisher is configured for provider: {provider}",
        )

    def deployment_status(self, provider: str, deployment_id: str, workspace: str | Path = ".") -> DeploymentResult:
        if provider.lower() == "railway":
            from .railway_provider import RailwayProvider
            result = RailwayProvider(workspace).status(deployment_id)
            return DeploymentResult(result.status, provider, None, result.external_action_required, None, result.error)
        return DeploymentResult("external_action_required", provider, None, True, None, f"No status adapter for provider: {provider}")

    def save_result(self, workspace: str | Path, result: DeploymentResult) -> Path:
        path = Path(workspace) / ".app-builder" / "deployment_result.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path
