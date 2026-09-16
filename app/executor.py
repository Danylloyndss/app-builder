"""Execution component for App Builder V1."""

from pathlib import Path


class Executor:
    def execute(self, task: str, workspace: Path) -> str:
        workspace.mkdir(parents=True, exist_ok=True)
        marker = workspace / "hello_app.txt"
        marker.write_text(
            "Hello App - first App Builder V1 task completed.\n",
            encoding="utf-8",
        )
        return f"Executed: {task}"
