"""Manager that coordinates the App Builder V1 components."""

from pathlib import Path

from .executor import Executor
from .memory import ProjectMemory
from .planner import Planner
from .tester import Tester


class Manager:
    def __init__(self, workspace: str = "workspace"):
        self.workspace = Path(workspace)
        self.memory_path = self.workspace / "state.json"
        self.memory = ProjectMemory.load(self.memory_path)
        self.planner = Planner()
        self.executor = Executor()
        self.tester = Tester()

    def run(self, mission: str) -> ProjectMemory:
        self.memory = ProjectMemory(mission=mission)
        self.memory.plan = self.planner.create_plan(mission)
        self.memory.save(self.memory_path)

        for task in self.memory.plan:
            if task == "Run tests":
                ok, message = self.tester.test(self.workspace)
                if not ok:
                    self.memory.errors.append(message)
                    self.memory.save(self.memory_path)
                    break
                self.memory.completed.append(message)
                self.memory.save(self.memory_path)
                continue

            result = self.executor.execute(task, self.workspace)
            self.memory.completed.append(result)
            self.memory.save(self.memory_path)

        return self.memory
