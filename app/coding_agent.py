"""Autonomous coding loop for App Builder V1.

The V1 agent exposes a small tool-driven loop. A future model adapter can supply
plans and edits; the execution loop itself stays deterministic, observable and
safe inside Workspace.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .workspace import Workspace


@dataclass
class AgentAction:
    kind: str
    target: str = ""
    content: str = ""
    command: list[str] = field(default_factory=list)


@dataclass
class AgentResult:
    success: bool
    iterations: int
    actions: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class CodingAgent:
    """Execute a bounded observe -> act -> test loop in a project workspace."""

    def __init__(self, workspace: str | Path, max_iterations: int = 5):
        self.project = Workspace(workspace)
        self.max_iterations = max(1, max_iterations)

    def inspect(self) -> list[str]:
        """Return the project's files without leaving the sandbox."""
        return self.project.list_files(".")

    def apply(self, action: AgentAction) -> str:
        if action.kind == "write":
            self.project.write_file(action.target, action.content)
            return f"wrote {action.target}"
        if action.kind == "run":
            code, output = self.project.run(action.command)
            if code:
                raise RuntimeError(output or f"command exited with {code}")
            return f"ran {' '.join(action.command)}"
        raise ValueError(f"Unsupported agent action: {action.kind}")

    def run(
        self,
        goal: str,
        planner: Callable[[str, list[str], list[str]], list[AgentAction]],
        validator: Callable[[Workspace], tuple[bool, str]],
    ) -> AgentResult:
        actions: list[str] = []
        errors: list[str] = []
        observations: list[str] = []

        for iteration in range(1, self.max_iterations + 1):
            files = self.inspect()
            try:
                proposed = planner(goal, files, observations)
                if not proposed:
                    ok, message = validator(self.project)
                    if ok:
                        return AgentResult(True, iteration, actions, errors)
                    errors.append(message)
                    observations.append(message)
                    continue
                for action in proposed:
                    result = self.apply(action)
                    actions.append(result)
                ok, message = validator(self.project)
                observations.append(message)
                if ok:
                    # A successful write is confirmed by a clean observe/validate
                    # pass on the next iteration, making the loop auditable.
                    continue
                errors.append(message)
            except Exception as exc:
                errors.append(str(exc))
                observations.append(f"error: {exc}")

        return AgentResult(False, self.max_iterations, actions, errors)
