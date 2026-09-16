"""Testing component for App Builder V1."""

from pathlib import Path

from .executor import Executor


class Tester:
    def __init__(self) -> None:
        self.executor = Executor()

    def test(self, workspace: Path) -> tuple[bool, str]:
        required = ("index.html", "app.js", "README.md")
        missing = [name for name in required if not (workspace / name).exists()]
        if missing:
            return False, f"Generated project is missing: {', '.join(missing)}"

        index = (workspace / "index.html").read_text(encoding="utf-8")
        script = (workspace / "app.js").read_text(encoding="utf-8")
        if "<html" not in index.lower() or not script.strip():
            return False, "Generated web app files are invalid or empty"

        tests_dir = workspace / "tests"
        if tests_dir.exists():
            code, output = self.executor.run_command(
                ["python", "-m", "unittest", "discover", "-s", "tests", "-v"],
                workspace,
            )
            if code != 0:
                return False, f"Project tests failed: {output[-2000:]}"

        return True, "Generated project passed structural tests"
