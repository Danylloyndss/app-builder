"""Testing component for App Builder V1."""

from pathlib import Path

from .executor import Executor


class Tester:
    def __init__(self) -> None:
        self.executor = Executor()

    def test(self, workspace: Path) -> tuple[bool, str]:
        marker = workspace / "hello_app.txt"
        if not (marker.exists() and marker.read_text(encoding="utf-8").strip()):
            return False, "Expected output file was not created"

        code, output = self.executor.run_command(
            ["python", "-m", "unittest", "discover", "-s", "tests", "-v"],
            workspace.parent,
        )
        if code != 0:
            return False, f"Automated tests failed: {output[-2000:]}"
        return True, "Hello App and automated test suite passed"
