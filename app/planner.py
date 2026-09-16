"""Planning component for App Builder V1."""


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
