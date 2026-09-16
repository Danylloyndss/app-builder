"""Manager that coordinates the App Builder V1 components."""

from pathlib import Path

from .executor import Executor
from .memory import ProjectMemory
from .planner import Planner
from .tester import Tester


class Manager:
    def __init__(self, workspace: str = "workspace", max_retries: int = 2):
        self.workspace = Path(workspace)
        self.memory_path = self.workspace / "state.json"
        self.memory = ProjectMemory.load(self.memory_path)
        self.planner = Planner()
        self.executor = Executor()
        self.tester = Tester()
        self.max_retries = max_retries

    def run(self, mission: str) -> ProjectMemory:
        self.memory = ProjectMemory(mission=mission)
        self.memory.plan = self.planner.create_plan(mission)
        self.memory.save(self.memory_path)

        for task in self.memory.plan:
            if task != "Run tests":
                result = self.executor.execute(task, self.workspace)
                self.memory.completed.append(result)
                self.memory.save(self.memory_path)
                continue

            ok, message = self.tester.test(self.workspace)
            attempts = 0
            while not ok and attempts < self.max_retries:
                attempts += 1
                self.memory.errors.append(f"Attempt {attempts}: {message}")
                self.executor.execute("Repair after test failure", self.workspace)
                ok, message = self.tester.test(self.workspace)

            if ok:
                self.memory.completed.append(message)
            else:
                self.memory.errors.append(message)
            self.memory.save(self.memory_path)

        return self.memory
