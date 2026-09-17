"""Dependency-aware task engine for App Builder V1."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class BuildTask:
    id: str
    title: str
    kind: str
    risk: str = "low"
    depends_on: tuple[str, ...] = ()
    acceptance: tuple[str, ...] = ()


class TaskEngine:
    """Convert an architecture/specification into deterministic executable tasks."""

    def create_tasks(self, specification: dict, architecture: dict) -> list[BuildTask]:
        tasks = [
            BuildTask("workspace", "Prepare project workspace", "workspace", acceptance=("workspace ready",)),
            BuildTask("scaffold", "Create project structure", "build", ("low"), ("workspace",), ("index.html exists", "app.js exists")),
        ]
        previous = "scaffold"
        components = architecture.get("components", {})
        for name, kind in (("frontend", "frontend"), ("backend", "backend"), ("database", "database"), ("auth", "auth")):
            if components.get(name):
                risk = "high" if kind in {"auth", "database"} else "medium"
                tasks.append(BuildTask(kind, f"Implement {name}", kind, risk, (previous,), (f"{name} implemented",)))
                previous = kind
        tasks.append(BuildTask("features", "Implement requested functionality", "feature", "medium", (previous,), ("requested features implemented",)))
        tasks.append(BuildTask("test", "Run tests", "test", "low", ("features",), ("tests pass",)))
        tasks.append(BuildTask("quality", "Run quality and security gates", "quality", "medium", ("test",), ("quality gates pass",)))
        return tasks

    def save(self, tasks: list[BuildTask], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([asdict(t) for t in tasks], indent=2), encoding="utf-8")

    def load(self, path: Path) -> list[BuildTask]:
        if not path.exists():
            return []
        return [BuildTask(**item) for item in json.loads(path.read_text(encoding="utf-8"))]

    def ready(self, tasks: list[BuildTask], completed: set[str]) -> list[BuildTask]:
        return [task for task in tasks if task.id not in completed and all(dep in completed for dep in task.depends_on)]
