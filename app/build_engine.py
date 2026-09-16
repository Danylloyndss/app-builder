"""Mission-aware deterministic build engine for App Builder V1."""

from html import escape
from pathlib import Path
import re

from .workspace import Workspace


class BuildEngine:
    def __init__(self, workspace: Path):
        self.project = Workspace(workspace)

    def execute(self, task: str, mission: str) -> str:
        normalized = task.lower()
        if "create the project structure" in normalized:
            return self.create_structure(mission)
        if "implement the requested functionality" in normalized:
            return self.implement(mission)
        if "repair after test failure" in normalized:
            return self.repair(mission)
        if "save progress" in normalized or "understand the mission" in normalized:
            self.project.write_file(".app-builder/mission.txt", mission + "\n")
            return "Mission/progress recorded"
        return f"No build handler for task: {task}"

    def create_structure(self, mission: str = "") -> str:
        self.project.write_file("index.html", self._html("Generated App", mission))
        self.project.write_file("app.js", self._javascript())
        self.project.write_file("README.md", self._readme(mission))
        self.project.write_file(".app-builder/mission.txt", mission + "\n")
        return "Project structure created"

    def implement(self, mission: str) -> str:
        title = self._title(mission)
        self.project.write_file("index.html", self._html(title, mission))
        self.project.write_file("app.js", self._javascript())
        self.project.write_file("README.md", self._readme(mission))
        self.project.write_file("hello_app.txt", f"{title}\n")
        self.project.write_file(".app-builder/mission.txt", mission + "\n")
        return f"Implemented generated app: {title}"

    def repair(self, mission: str) -> str:
        files = self.project.list_files(".")
        if not files:
            return self.create_structure(mission)
        if "index.html" not in files:
            self.project.write_file("index.html", self._html("Recovered App", mission))
        if "app.js" not in files:
            self.project.write_file("app.js", self._javascript())
        if "hello_app.txt" not in files:
            self.project.write_file("hello_app.txt", f"{self._title(mission)}\n")
        return "Repair completed"

    @staticmethod
    def _title(mission: str) -> str:
        cleaned = re.sub(r"\s+", " ", mission).strip()
        return cleaned[:80] if cleaned else "Generated App"

    @staticmethod
    def _javascript() -> str:
        return """document.addEventListener('DOMContentLoaded', () => {
  const status = document.querySelector('[data-builder-status]');
  if (status) status.textContent = 'App generated successfully';
});
"""

    @staticmethod
    def _readme(mission: str) -> str:
        return f"# Generated App\n\nMission: {mission or 'Generated project'}\n\nBuilt by App Builder V1.\n"

    @staticmethod
    def _html(title: str, mission: str = "") -> str:
        safe_title = escape(title)
        safe_description = escape(mission or "Generated project")
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>body{{font-family:system-ui,sans-serif;max-width:760px;margin:60px auto;padding:24px}}main{{border:1px solid #ddd;border-radius:16px;padding:24px}}</style>
</head>
<body>
  <main>
    <h1>{safe_title}</h1>
    <p>{safe_description}</p>
    <p data-builder-status>Building...</p>
  </main>
  <script src="app.js"></script>
</body>
</html>
"""
