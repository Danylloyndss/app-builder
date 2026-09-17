from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, List


class TaskStatus(str, Enum):
    TODO = "todo"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Task:
    id: str
    title: str
    action: Callable[[], str]
    status: TaskStatus = TaskStatus.TODO
    result: str = ""
    error: str = ""


@dataclass
class AgentState:
    mission: str
    tasks: List[Task] = field(default_factory=list)
    history: List[str] = field(default_factory=list)


class Planner:
    """Turns a mission into an explicit, inspectable task list."""

    def plan(self, mission: str, workspace: Path) -> AgentState:
        state = AgentState(mission=mission)
        state.tasks.append(Task("inspect", "Inspect workspace", lambda: str(workspace.resolve())))
        state.tasks.append(Task("hello", "Run the first smoke test", lambda: "HELLO_APP_OK"))
        return state


class Executor:
    def run(self, state: AgentState) -> AgentState:
        for task in state.tasks:
            if task.status != TaskStatus.TODO:
                continue
            task.status = TaskStatus.RUNNING
            try:
                task.result = task.action()
                task.status = TaskStatus.DONE
                state.history.append(f"DONE:{task.id}:{task.result}")
            except Exception as exc:
                task.status = TaskStatus.FAILED
                task.error = str(exc)
                state.history.append(f"FAILED:{task.id}:{task.error}")
                break
        return state


class Tester:
    def verify(self, state: AgentState) -> bool:
        return all(task.status == TaskStatus.DONE for task in state.tasks)


class Manager:
    def run(self, mission: str, workspace: Path) -> AgentState:
        state = Planner().plan(mission, workspace)
        state = Executor().run(state)
        if not Tester().verify(state):
            raise RuntimeError("Agent V1 verification failed")
        return state
