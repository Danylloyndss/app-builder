"""Specialist execution behind the same bounded task contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .coding_agent import AgentAction, CodingAgent


@dataclass(frozen=True)
class Specialist:
    name: str
    system_prompt: str


class SpecialistRunner:
    """Runs bounded specialist passes without creating a second orchestration system."""

    def __init__(self, workspace, max_iterations: int = 3):
        self.workspace = workspace
        self.max_iterations = max_iterations
        self.specialists = {
            "frontend": Specialist("frontend", "Implement and verify UI behavior."),
            "backend": Specialist("backend", "Implement and verify persistence/API behavior."),
            "qa": Specialist("qa", "Inspect failures and produce the smallest safe fixes."),
            "security": Specialist("security", "Remove obvious unsafe patterns and secrets."),
        }

    def run(
        self,
        name: str,
        goal: str,
        planner: Callable[[str, list[str], list[str]], list[AgentAction]] | None = None,
        validator: Callable | None = None,
    ):
        specialist = self.specialists.get(name)
        if specialist is None:
            raise ValueError(f"unknown specialist: {name}")
        agent = CodingAgent(self.workspace, max_iterations=self.max_iterations)
        return agent.run(f"{specialist.system_prompt}\n{goal}", planner=planner, validator=validator)
