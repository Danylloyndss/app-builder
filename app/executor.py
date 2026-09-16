"""Execution component for App Builder V1."""

from pathlib import Path

from .build_engine import BuildEngine
from .workspace import Workspace


class Executor:
    def execute(self, task: str, workspace: Path, mission: str = "") -> str:
        """Execute a build task inside the project's sandbox workspace."""
        project = Workspace(workspace)
        project.write_file(".app-builder/last_task.txt", task + "\n")
        return BuildEngine(workspace).execute(task, mission)

    def run_command(self, command: list[str], workspace: Path, timeout: int = 120) -> tuple[int, str]:
        """Run a project command through the sandbox workspace."""
        return Workspace(workspace).run(command, timeout=timeout)
