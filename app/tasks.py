"""Dependency-aware task generation for App Builder V1."""

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path

from .architecture import Architecture
from .specification import AppSpecification


@dataclass
class BuildTask:
    id: str
    title: str
    kind: str
    dependencies: list[str] = field(default_factory=list)
    risk: str = "low"
    requires_approval: bool = False
    acceptance: list[str] = field(default_factory=list)
    status: str = "pending"


class TaskBuilder:
    """Turn specification + architecture into an executable task graph."""

    def build(self, spec: AppSpecification, architecture: Architecture) -> list[BuildTask]:
        tasks = [
            BuildTask("spec", "Validate application specification", "planning", acceptance=["specification exists"]),
            BuildTask("structure", "Create project structure", "build", ["spec"]),
        ]

        previous = "structure"
        features = set(spec.features)
        feature_map = [
            ("auth", "Implement user access flow", "authentication", "medium"),
            ("storage", "Implement data storage layer", "storage", "medium"),
            ("forms", "Implement input forms", "ui", "low"),
            ("dashboard", "Implement dashboard", "ui", "low"),
            ("mobile", "Optimize mobile experience", "ui", "low"),
            ("calculator", "Implement calculator", "logic", "low"),
            ("history", "Implement history and lists", "ui", "low"),
        ]
        feature_to_spec = {
            "auth": "authentication", "storage": "data storage", "forms": "forms",
            "dashboard": "dashboard", "mobile": "mobile", "calculator": "calculation", "history": "history",
        }
        for task_id, title, kind, risk in feature_map:
            if feature_to_spec[task_id] in features:
                requires_approval = task_id == "auth" and not any(token in spec.mission.lower() for token in ("timepro", "timesheet", "folha de horas"))
                tasks.append(BuildTask(task_id, title, kind, [previous], risk, requires_approval,
                    [f"{title} is represented in the generated project"]))
                previous = task_id

        tasks.append(BuildTask("implement", "Implement requested functionality", "build", [previous], "medium"))
        if "data storage" in features or "storage" in features:
            tasks.append(BuildTask("backend", "Generate backend and persistence layer", "storage", ["implement"], "medium", ["Persistence boundary is explicitly defined"]))
            backend_previous = "backend"
        else:
            backend_previous = "implement"
        tasks.append(BuildTask("test", "Run tests", "test", [backend_previous], "medium",
                               acceptance=list(spec.acceptance_criteria)))
        tasks.append(BuildTask("repair", "Fix errors and retest", "repair", ["test"], "medium"))
        tasks.append(BuildTask("security", "Run security review", "security", ["repair"], "high",
                               acceptance=list(spec.security_requirements)))
        tasks.append(BuildTask("acceptance", "Run acceptance checks", "acceptance", ["security"], "medium",
                               acceptance=list(spec.acceptance_criteria)))
        return tasks

    @staticmethod
    def save(tasks: list[BuildTask], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([asdict(task) for task in tasks], indent=2, ensure_ascii=False), encoding="utf-8")
