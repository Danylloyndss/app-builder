"""Safe integration boundaries for generated applications.

External providers are deliberately adapters: credentials never live in source
files and production actions can be placed behind the existing approval store.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping


class IntegrationError(RuntimeError):
    pass


class SecretProvider:
    """Read runtime secrets without exposing values to the builder state."""

    def get(self, name: str) -> str | None:
        raise NotImplementedError


class EnvironmentSecretProvider(SecretProvider):
    def get(self, name: str) -> str | None:
        value = os.environ.get(name)
        return value if value else None


@dataclass(frozen=True)
class IntegrationConfig:
    name: str
    enabled: bool = False
    requires_approval: bool = True
    secret_names: tuple[str, ...] = ()


class IntegrationRegistry:
    def __init__(self, secret_provider: SecretProvider | None = None):
        self.secret_provider = secret_provider or EnvironmentSecretProvider()
        self._configs: dict[str, IntegrationConfig] = {}

    def register(self, config: IntegrationConfig) -> None:
        if not config.name.strip():
            raise ValueError("integration name is required")
        self._configs[config.name] = config

    def get(self, name: str) -> IntegrationConfig | None:
        return self._configs.get(name)

    def ready(self, name: str) -> tuple[bool, str]:
        config = self.get(name)
        if config is None:
            return False, "integration is not registered"
        if not config.enabled:
            return False, "integration is disabled"
        missing = [key for key in config.secret_names if not self.secret_provider.get(key)]
        if missing:
            return False, "missing runtime secret(s): " + ", ".join(missing)
        return True, "integration is configured"

    def snapshot(self) -> Mapping[str, dict]:
        return {
            name: {
                "enabled": cfg.enabled,
                "requires_approval": cfg.requires_approval,
                "secret_names": list(cfg.secret_names),
            }
            for name, cfg in self._configs.items()
        }
