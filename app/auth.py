"""Provider-neutral authentication boundary for generated applications.

The builder can reason about authentication without receiving passwords or
provider secrets. Concrete providers are adapters; runtime credentials stay
outside source files, and enabling an external provider requires approval.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .integrations import SecretProvider, EnvironmentSecretProvider


class AuthenticationError(RuntimeError):
    pass


@dataclass(frozen=True)
class AuthProviderConfig:
    name: str
    enabled: bool = False
    requires_approval: bool = True
    secret_names: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ("login",)


class AuthenticationRegistry:
    """Registry and readiness gate for authentication provider adapters."""

    def __init__(self, secret_provider: SecretProvider | None = None):
        self.secret_provider = secret_provider or EnvironmentSecretProvider()
        self._providers: dict[str, AuthProviderConfig] = {}

    def register(self, config: AuthProviderConfig) -> None:
        if not config.name.strip():
            raise ValueError("authentication provider name is required")
        self._providers[config.name] = config

    def get(self, name: str) -> AuthProviderConfig | None:
        return self._providers.get(name)

    def ready(self, name: str, approved: bool = False) -> tuple[bool, str]:
        config = self.get(name)
        if config is None:
            return False, "authentication provider is not registered"
        if not config.enabled:
            return False, "authentication provider is disabled"
        missing = [key for key in config.secret_names if not self.secret_provider.get(key)]
        if missing:
            return False, "missing runtime secret(s): " + ", ".join(missing)
        if config.requires_approval and not approved:
            return False, "human approval required"
        return True, "authentication provider is configured"

    def all_ready(self, approved: bool = False) -> tuple[bool, dict[str, str]]:
        messages: dict[str, str] = {}
        ready = True
        for name in self._providers:
            ok, message = self.ready(name, approved=approved)
            messages[name] = message
            ready = ready and ok
        return ready, messages

    def snapshot(self) -> Mapping[str, dict]:
        return {
            name: {
                "enabled": cfg.enabled,
                "requires_approval": cfg.requires_approval,
                "secret_names": list(cfg.secret_names),
                "capabilities": list(cfg.capabilities),
            }
            for name, cfg in self._providers.items()
        }
