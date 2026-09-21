"""Persistent project memory for App Builder V1."""

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path


@dataclass
class ProjectMemory:
    mission: str = ""
    plan: list[str] = field(default_factory=list)
    completed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    status: str = "idle"
    current_task: str = ""
    task_statuses: dict[str, str] = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "ProjectMemory":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        # Keep backward compatibility with V1 memory files.
        data.setdefault("status", "idle")
        data.setdefault("current_task", "")
        data.setdefault("task_statuses", {})
        data.setdefault("history", [])
        data.setdefault("diagnostics", {})
        return cls(**data)

    def record(self, event: str, **details) -> None:
        self.history.append({"event": event, **details})
        if event in {"tests_failed", "acceptance_failed", "quality_gate", "quality_repair", "task_failed", "task_cancelled"}:
            self.diagnostics.update({
                "last_event": event,
                "last_task": details.get("task_id", self.current_task),
                "last_error": details.get("message") or details.get("error") or details.get("report", ""),
            })
        elif event in {"tests_passed", "mission_finished"}:
            self.diagnostics["last_success"] = event
        elif event == "task_started":
            self.diagnostics["active_task_id"] = details.get("task_id", "")
            self.diagnostics["active_task"] = details.get("title", self.current_task)
