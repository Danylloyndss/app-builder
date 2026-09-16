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

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "ProjectMemory":
        if not path.exists():
            return cls()
        return cls(**json.loads(path.read_text(encoding="utf-8")))
