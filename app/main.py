"""App Builder V1 - minimal autonomous build loop."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProjectMemory:
    mission: str = ""
    plan: list[str] = field(default_factory=list)
    completed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Planner:
    def create_plan(self, mission: str) -> list[str]:
        return [
            "Understand the mission",
            "Create the project structure",
            "Implement the requested functionality",
            "Run tests",
            "Fix errors and retest",
            "Save progress",
        ]


class Executor:
    def execute(self, task: str, workspace: Path) -> str:
        workspace.mkdir(parents=True, exist_ok=True)
        marker = workspace / "hello_app.txt"
        marker.write_text("Hello App - first App Builder V1 task completed.\n", encoding="utf-8")
        return f"Executed: {task}"


class Tester:
    def test(self, workspace: Path) -> tuple[bool, str]:
        marker = workspace / "hello_app.txt"
        if marker.exists() and marker.read_text(encoding="utf-8").strip():
            return True, "Hello App test passed"
        return False, "Expected output file was not created"


class Manager:
    def __init__(self, workspace: str = "workspace"):
        self.workspace = Path(workspace)
        self.memory = ProjectMemory()
        self.planner = Planner()
        self.executor = Executor()
        self.tester = Tester()

    def run(self, mission: str) -> ProjectMemory:
        self.memory.mission = mission
        self.memory.plan = self.planner.create_plan(mission)
        for task in self.memory.plan:
            if task == "Run tests":
                ok, message = self.tester.test(self.workspace)
                if not ok:
                    self.memory.errors.append(message)
                    break
                self.memory.completed.append(message)
                continue
            result = self.executor.execute(task, self.workspace)
            self.memory.completed.append(result)
        return self.memory


if __name__ == "__main__":
    memory = Manager().run("Create a simple Hello App")
    print("Mission:", memory.mission)
    print("Plan:")
    for item in memory.plan:
        print("-", item)
    print("Completed:")
    for item in memory.completed:
        print("-", item)
    if memory.errors:
        print("Errors:")
        for error in memory.errors:
            print("-", error)
