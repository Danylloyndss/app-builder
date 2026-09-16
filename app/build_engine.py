"""Deterministic build engine for App Builder V1.

This is the first real project builder: it turns high-level tasks into files
inside an isolated Workspace. A later agent can replace/extend these handlers
with LLM-driven code generation without changing the Workspace contract.
"""

from pathlib import Path
import re

from .workspace import Workspace


class BuildEngine:
    def __init__(self, workspace: Path):
        self.project = Workspace(workspace)

    def execute(self, task: str, mission: str) -> str:
        normalized = task.lower()
        if "create the project structure" in normalized:
            return self.create_structure()
        if "implement the requested functionality" in normalized:
            return self.implement(mission)
        if "repair after test failure" in normalized:
            return self.repair()
        if "save progress" in normalized:
            self.project.write_file(".app-builder/mission.txt", mission + "\n")
            return "Progress saved"
        if "understand the mission" in normalized:
            self.project.write_file(".app-builder/mission.txt", mission + "\n")
            return "Mission recorded"
        return f"No build handler for task: {task}"

    def create_structure(self) -> str:
        self.project.write_file("index.html", self._html("App Builder project"))
        self.project.write_file("app.js", "console.log('App Builder project ready');\n")
        self.project.write_file("README.md", "# Generated App\n\nBuilt by App Builder V1.\n")
        return "Project structure created"

    def implement(self, mission: str) -> str:
        title = self._title(mission)
        html = self._html(title, mission)
        self.project.write_file("index.html", html)
        self.project.write_file(
            "app.js",
            "document.addEventListener('DOMContentLoaded', () => {\n"
            "  const status = document.querySelector('[data-builder-status]');\n"
            "  if (status) status.textContent = 'App generated successfully';\n"
            "});\n",
        )
        # Keep the original smoke-test artifact for backwards compatibility.
        self.project.write_file("hello_app.txt", f"{title}\n")
        self.project.write_file(".app-builder/mission.txt", mission + "\n")
        return f"Implemented generated app: {title}"

    def repair(self) -> str:
        if not self.project.list_files("."):
            return self.create_structure()
        if "index.html" not in self.project.list_files("."):
            self.project.write_file("index.html", self._html("Recovered App"))
        return "Repair completed"

    @staticmethod
    def _title(mission: str) -> str:
        cleaned = re.sub(r"\s+", " ", mission).strip()
        if not cleaned:
            return "Generated App"
        return cleaned[:80]

    @staticmethod
    def _html(title: str, mission: str = "") -> str:
        description = mission or "Generated project"
        return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{title}</title>
  <style>body{{font-family:system-ui,sans-serif;max-width:760px;margin:60px auto;padding:24px}}main{{border:1px solid #ddd;border-radius:16px;padding:24px}}</style>
</head>
<body>
  <main>
    <h1>{title}</h1>
    <p>{description}</p>
    <p data-builder-status>Building...</p>
  </main>
  <script src=\"app.js\"></script>
</body>
</html>
"""
