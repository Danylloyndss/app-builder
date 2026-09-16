"""Execution component for App Builder V1."""

from pathlib import Path

from .workspace import Workspace


class Executor:
    def execute(self, task: str, workspace: Path) -> str:
        """Execute a task inside the project's sandbox workspace."""
        project = Workspace(workspace)
        project.write_file(".app-builder/last_task.txt", task + "\n")
        return f"Executed: {task}"

    def run_command(self, command: list[str], workspace: Path, timeout: int = 120) -> tuple[int, str]:
        """Run a project command through the sandbox workspace."""
        return Workspace(workspace).run(command, timeout=timeout)
