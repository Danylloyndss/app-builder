"""Architecture planning for App Builder V1."""

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path

from .specification import AppSpecification


@dataclass
class Architecture:
    app_type: str = "web"
    frontend: str = "static web frontend"
    backend: str = "none (prototype)"
    database: str = "local storage (prototype)"
    authentication: str = "none"
    storage: str = "browser local storage"
    integrations: list[str] = field(default_factory=list)
    deployment: str = "Railway"
    components: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")


class ArchitectureBuilder:
    """Convert a structured specification into a deterministic V1 architecture."""

    def build(self, spec: AppSpecification) -> Architecture:
        features = set(spec.features)
        authentication = "demo authentication" if "authentication" in features else "none"
        database = "browser local storage" if "data storage" in features else "none"
        components = ["frontend"]
        constraints = [
            "Prototype credentials must never be treated as production security",
            "Secrets must not be written into source files",
            "Human approval is required for external authentication, payment, communication, or production release",
        ]

        if "dashboard" in features:
            components.append("manager dashboard")
        if "forms" in features:
            components.append("input forms")
        if "history" in features:
            components.append("history/list view")
        if "calculation" in features:
            components.append("calculation engine")
        if "authentication" in features:
            components.append("authentication boundary")
        if "data storage" in features:
            components.append("persistence layer")

        return Architecture(
            app_type=spec.app_type,
            frontend="responsive HTML/CSS/JavaScript",
            backend="none (prototype)" if "data storage" not in features else "prototype browser-only backend boundary",
            database=database,
            authentication=authentication,
            storage=database,
            integrations=list(spec.integrations),
            components=components,
            constraints=constraints,
        )
