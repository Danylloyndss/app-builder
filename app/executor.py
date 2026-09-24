"""Execution component for App Builder V1."""

from pathlib import Path
from typing import Callable

from .build_engine import BuildEngine
from .coding_agent import CodingAgent
from .workspace import Workspace


class Executor:
    def execute(
        self,
        task: str,
        workspace: Path,
        mission: str = "",
        validator: Callable[[Workspace], tuple[bool, str]] | None = None,
    ) -> str:
        """Execute deterministic handlers, then delegate unknown work to the coding agent."""
        project = Workspace(workspace)
        project.write_file(".app-builder/last_task.txt", task + "\n")
        engine = BuildEngine(workspace)
        result = engine.execute(task, mission)
        if not result.startswith("No build handler"):
            return result

        agent = CodingAgent(workspace, max_iterations=3)
        if not agent.model_configured:
            return result

        outcome = agent.run(task, validator=validator)
        if not outcome.success:
            raise RuntimeError("; ".join(outcome.errors[-3:]) or "Coding agent failed")
        return "Coding agent completed: " + "; ".join(outcome.actions)

    def run_command(self, command: list[str], workspace: Path, timeout: int = 120, cancel_check=None) -> tuple[int, str]:
        return Workspace(workspace).run(command, timeout=timeout, cancel_check=cancel_check)
