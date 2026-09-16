"""Execution component for App Builder V1."""

from pathlib import Path
import subprocess


class Executor:
    def execute(self, task: str, workspace: Path) -> str:
        workspace.mkdir(parents=True, exist_ok=True)
        marker = workspace / "hello_app.txt"
        marker.write_text(
            f"Hello App - V1 task completed: {task}.\n",
            encoding="utf-8",
        )
        return f"Executed: {task}"

    def run_command(self, command: list[str], workspace: Path) -> tuple[int, str]:
        """Run a project command and return its exit code plus combined output."""
        workspace.mkdir(parents=True, exist_ok=True)
        process = subprocess.run(
            command,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (process.stdout + process.stderr).strip()
        return process.returncode, output
