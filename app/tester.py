"""Testing component for App Builder V1."""

from pathlib import Path
import json

from .executor import Executor


class Tester:
    def __init__(self) -> None:
        self.executor = Executor()

    @staticmethod
    def _is_timepro(workspace: Path) -> bool:
        spec = workspace / ".app-builder" / "spec.json"
        if spec.exists():
            try:
                data = json.loads(spec.read_text(encoding="utf-8"))
                if str(data.get("app_name", "")).lower() == "timepro":
                    return True
                mission = str(data.get("mission", "")).lower()
                if any(token in mission for token in ("timepro", "timesheet", "folha de horas")):
                    return True
            except (OSError, ValueError, TypeError):
                pass
        mission = workspace / ".app-builder" / "mission.txt"
        if mission.exists():
            text = mission.read_text(encoding="utf-8").lower()
            return any(token in text for token in ("timepro", "timesheet", "folha de horas"))
        return False

    def _test_timepro(self, workspace: Path) -> tuple[bool, str]:
        index = (workspace / "index.html").read_text(encoding="utf-8")
        script = (workspace / "app.js").read_text(encoding="utf-8")
        required_html = (
            'id="timesheet-form"', 'name="employee"', 'name="company"',
            'name="date"', 'name="site"', 'id="start"', 'id="end"',
            'id="pause"', 'id="total"', 'id="history"', 'id="dashboard"',
        )
        missing_html = [marker for marker in required_html if marker not in index]
        if missing_html:
            return False, f"TimePro HTML missing required elements: {', '.join(missing_html)}"
        required_js = (
            "localStorage", "b < a", "Feuille envoyée avec succès", "function duration",
        )
        missing_js = [marker for marker in required_js if marker not in script]
        if missing_js:
            return False, f"TimePro logic missing required behavior: {', '.join(missing_js)}"
        return True, "TimePro functional MVP passed structural and behavior checks"

    def test(self, workspace: Path) -> tuple[bool, str]:
        required = ("index.html", "app.js", "README.md")
        missing = [name for name in required if not (workspace / name).exists()]
        if missing:
            return False, f"Generated project is missing: {', '.join(missing)}"

        index = (workspace / "index.html").read_text(encoding="utf-8")
        script = (workspace / "app.js").read_text(encoding="utf-8")
        if "<html" not in index.lower() or not script.strip():
            return False, "Generated web app files are invalid or empty"

        # Catch JavaScript syntax errors before calling the build successful.
        # Node is optional; when unavailable, keep the deterministic checks below.
        node = self.executor.run_command(["node", "--check", "app.js"], workspace)
        if node[0] == 0:
            syntax_ok = True
        elif "not found" in node[1].lower() or "no such file" in node[1].lower():
            syntax_ok = True
        else:
            return False, f"JavaScript syntax check failed: {node[1][-1500:]}"

        if self._is_timepro(workspace):
            ok, message = self._test_timepro(workspace)
            if not ok:
                return False, message

        tests_dir = workspace / "tests"
        if tests_dir.exists():
            code, output = self.executor.run_command(
                ["python", "-m", "unittest", "discover", "-s", "tests", "-v"],
                workspace,
            )
            if code != 0:
                return False, f"Project tests failed: {output[-2000:]}"

        return True, "Generated project passed structural and functional tests"
