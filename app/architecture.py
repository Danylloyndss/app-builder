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
    """Convert a structured specification into a deterministic architecture."""

    def build(self, spec: AppSpecification) -> Architecture:
        features = set(spec.features)
        authentication = "demo authentication" if "authentication" in features else "none"
        persistent_data = "data storage" in features
        database = "SQLite adapter" if persistent_data else "none"
        storage = "database persistence" if persistent_data else "none"
        backend = "Python service boundary" if persistent_data else "none (prototype)"
        components = ["frontend"]
        constraints = [
            "Prototype credentials must never be treated as production security",
            "Secrets must not be written into source files",
            "Human approval is required for external authentication, payment, communication, or production release",
            "Database access must go through the adapter boundary",
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
        if persistent_data:
            components.extend(["backend service", "persistence adapter", "persistence layer"])

        return Architecture(
            app_type=spec.app_type,
            frontend="responsive HTML/CSS/JavaScript",
            backend=backend,
            database=database,
            authentication=authentication,
            storage=storage,
            integrations=list(spec.integrations),
            components=components,
            constraints=constraints,
        )
