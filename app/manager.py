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

    def run(self, mission: str, resume: bool = False) -> ProjectMemory:
        if resume and self.memory.mission == mission and self.memory.plan:
            start_index = len(self.memory.completed)
        else:
            self.memory = ProjectMemory(mission=mission, status="planning")
            self.memory.plan = self.planner.create_plan(mission)
            self.memory.record("plan_created", tasks=self.memory.plan)
            self.memory.save(self.memory_path)
            start_index = 0

        self.memory.status = "running"
        self.memory.save(self.memory_path)

        for index, task in enumerate(self.memory.plan[start_index:], start=start_index):
            self.memory.current_task = task
            self.memory.record("task_started", index=index, task=task)
            self.memory.save(self.memory_path)

            if task != "Run tests":
                result = self.executor.execute(task, self.workspace)
                self.memory.completed.append(result)
                self.memory.record("task_completed", index=index, task=task, result=result)
                self.memory.save(self.memory_path)
                continue

            ok, message = self.tester.test(self.workspace)
            attempts = 0
            while not ok and attempts < self.max_retries:
                attempts += 1
                self.memory.errors.append(f"Attempt {attempts}: {message}")
                self.memory.record("repair", attempt=attempts, error=message)
                self.executor.execute("Repair after test failure", self.workspace)
                ok, message = self.tester.test(self.workspace)

            if ok:
                self.memory.completed.append(message)
                self.memory.record("tests_passed", message=message)
            else:
                self.memory.errors.append(message)
                self.memory.record("tests_failed", message=message)
            self.memory.save(self.memory_path)

        self.memory.current_task = ""
        self.memory.status = "completed" if not self.memory.errors else "completed_with_errors"
        self.memory.record("mission_finished", status=self.memory.status)
        self.memory.save(self.memory_path)
        return self.memory
