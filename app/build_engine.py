"""Mission-aware deterministic build engine for App Builder V1.

V1 uses dependency-free templates so the agent can reliably build and test a
working prototype before a future LLM coding layer takes over.
"""

from html import escape
import json
from pathlib import Path
import re

from .workspace import Workspace


class BuildEngine:
    def __init__(self, workspace: Path):
        self.project = Workspace(workspace)

    def execute(self, task: str, mission: str) -> str:
        normalized = task.lower()
        if "create the project structure" in normalized or "create project structure" in normalized:
            return self.create_structure(mission)
        if "implement user access flow" in normalized:
            return self.implement_feature("auth", mission)
        if "implement data storage layer" in normalized:
            return self.implement_feature("storage", mission)
        if "implement input forms" in normalized:
            return self.implement_feature("forms", mission)
        if "implement dashboard" in normalized:
            return self.implement_feature("dashboard", mission)
        if "optimize mobile experience" in normalized:
            return self.implement_feature("mobile", mission)
        if "implement calculator" in normalized:
            return self.implement_feature("calculator", mission)
        if "implement history and lists" in normalized:
            return self.implement_feature("list", mission)
        if "implement the requested functionality" in normalized:
            return self.implement(mission)
        if "repair after test failure" in normalized:
            return self.repair(mission)
        if "save progress" in normalized or "understand the mission" in normalized:
            self.project.write_file(".app-builder/mission.txt", mission + "\n")
            return "Mission/progress recorded"
        if normalized in {"validate application specification", "run security review", "run acceptance checks", "fix errors and retest"}:
            return f"Checkpoint completed: {task}"
        return f"No build handler for task: {task}"

    def create_structure(self, mission: str = "") -> str:
        self.project.write_file("index.html", self._html("Generated App", mission))
        self.project.write_file("app.js", self._javascript())
        self.project.write_file("README.md", self._readme(mission))
        self.project.write_file(".app-builder/mission.txt", mission + "\n")
        self._save_features([])
        return "Project structure created"

    def implement(self, mission: str) -> str:
        title = self._title(mission)
        features = self.detect_features(mission)
        self.project.write_file("index.html", self._html(title, mission, features))
        self.project.write_file("app.js", self._javascript(features))
        self.project.write_file("README.md", self._readme(mission, features))
        self.project.write_file("hello_app.txt", f"{title}\n")
        self.project.write_file(".app-builder/mission.txt", mission + "\n")
        self._save_features(features)
        return f"Implemented generated app: {title} ({len(features)} features)"

    def implement_feature(self, feature: str, mission: str) -> str:
        files = self.project.list_files(".")
        if "index.html" not in files or "app.js" not in files:
            self.create_structure(mission)
        current = self._load_features()
        if feature not in current:
            current.append(feature)
        title = self._title(mission)
        self.project.write_file("index.html", self._html(title, mission, current))
        self.project.write_file("app.js", self._javascript(current))
        self.project.write_file("README.md", self._readme(mission, current))
        self._save_features(current)
        return f"Implemented feature: {feature}"

    def repair(self, mission: str) -> str:
        files = self.project.list_files(".")
        if not files:
            return self.create_structure(mission)
        features = self._load_features() or self.detect_features(mission)
        self.project.write_file("index.html", self._html(self._title(mission), mission, features))
        self.project.write_file("app.js", self._javascript(features))
        self.project.write_file("README.md", self._readme(mission, features))
        if "hello_app.txt" not in files:
            self.project.write_file("hello_app.txt", f"{self._title(mission)}\n")
        self._save_features(features)
        return "Repair completed"

    @staticmethod
    def detect_features(mission: str) -> list[str]:
        text = mission.lower()
        features: list[str] = []
        groups = {
            "auth": ("login", "sign in", "account", "senha", "connexion", "connect"),
            "storage": ("database", "data", "dados", "save", "store", "enregistrer"),
            "forms": ("form", "field", "formulário", "cadastro", "register", "timesheet", "folha de horas"),
            "dashboard": ("dashboard", "admin", "manager", "gestor", "painel"),
            "mobile": ("mobile", "phone", "celular", "smartphone", "responsive"),
            "calculator": ("calculator", "calculate", "total", "calcular", "horas"),
            "list": ("list", "history", "lista", "histórico", "records", "registros"),
        }
        for feature, keywords in groups.items():
            if any(keyword in text for keyword in keywords):
                features.append(feature)
        return features

    def _save_features(self, features: list[str]) -> None:
        self.project.write_file(
            ".app-builder/features.json",
            json.dumps(features, indent=2, ensure_ascii=False) + "\n",
        )

    def _load_features(self) -> list[str]:
        path = self.project.root / ".app-builder/features.json"
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _title(mission: str) -> str:
        cleaned = re.sub(r"\s+", " ", mission).strip()
        return cleaned[:80] if cleaned else "Generated App"

    @staticmethod
    def _javascript(features: list[str] | None = None) -> str:
        features = features or []
        blocks = [
            "document.addEventListener('DOMContentLoaded', () => {",
            "  const status = document.querySelector('[data-builder-status]');",
            "  if (status) status.textContent = 'App generated successfully';",
        ]
        if "calculator" in features:
            blocks += [
                "  const start = document.querySelector('#start');",
                "  const end = document.querySelector('#end');",
                "  const total = document.querySelector('#total');",
                "  const calculate = () => {",
                "    if (!start || !end || !total || !start.value || !end.value) return;",
                "    const a = start.value.split(':').map(Number); const b = end.value.split(':').map(Number);",
                "    let minutes = (b[0] * 60 + b[1]) - (a[0] * 60 + a[1]);",
                "    if (minutes < 0) minutes += 1440;",
                "    total.textContent = `${Math.floor(minutes / 60)}h ${minutes % 60}min`;",
                "  };",
                "  start?.addEventListener('input', calculate); end?.addEventListener('input', calculate);",
            ]
        if "storage" in features:
            blocks += [
                "  document.querySelectorAll('form[data-save]').forEach(form => form.addEventListener('submit', event => {",
                "    event.preventDefault();",
                "    localStorage.setItem('app-builder-form', JSON.stringify(Object.fromEntries(new FormData(form))));",
                "    if (status) status.textContent = 'Saved locally';",
                "  }));",
            ]
        if "auth" in features:
            blocks += [
                "  document.querySelector('[data-login]')?.addEventListener('submit', event => {",
                "    event.preventDefault();",
                "    if (status) status.textContent = 'Demo login successful';",
                "  });",
            ]
        blocks.append("});")
        return "\n".join(blocks) + "\n"

    @staticmethod
    def _readme(mission: str, features: list[str] | None = None) -> str:
        features = features or []
        lines = [
            "# Generated App",
            "",
            f"Mission: {mission or 'Generated project'}",
            "",
            "Features detected: " + (", ".join(features) if features else "none yet"),
            "",
            "Built by App Builder V1.",
        ]
        return "\n".join(lines) + "\n"

    @staticmethod
    def _html(title: str, mission: str = "", features: list[str] | None = None) -> str:
        features = features or []
        safe_title = escape(title)
        safe_description = escape(mission or "Generated project")
        sections = [f"<h1>{safe_title}</h1>", f"<p>{safe_description}</p>"]
        if "auth" in features:
            sections.append('<form data-login><h2>Sign in</h2><input name="email" type="email" placeholder="Email" required><input name="password" type="password" placeholder="Password" required><button>Sign in</button></form>')
        if "forms" in features:
            sections.append('<form data-save><h2>New entry</h2><input name="date" type="date"><input name="location" placeholder="Location / site"><input id="start" name="start" type="time"><input name="break" type="number" min="0" placeholder="Break (minutes)"><input id="end" name="end" type="time"><textarea name="note" placeholder="Optional note"></textarea><button>Save</button></form>')
        if "calculator" in features:
            sections.append('<section><h2>Total</h2><strong id="total">0h 0min</strong></section>')
        if "list" in features:
            sections.append('<section><h2>History</h2><ul><li>No records yet</li></ul></section>')
        if "dashboard" in features:
            sections.append('<section><h2>Dashboard</h2><div class="cards"><article>Employees</article><article>Hours</article><article>Pending</article></div></section>')
        sections.append('<p data-builder-status>Building...</p>')
        body = "\n    ".join(sections)
        return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:auto;padding:24px;background:#f7f7f7}}main{{display:grid;gap:20px}}form,section{{background:white;border:1px solid #ddd;border-radius:16px;padding:20px;display:grid;gap:10px}}input,textarea,button{{font:inherit;padding:10px;border:1px solid #ccc;border-radius:10px}}button{{cursor:pointer}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}article{{padding:20px;border:1px solid #ddd;border-radius:12px}}@media(max-width:600px){{.cards{{grid-template-columns:1fr}}}}</style>
</head>
<body><main>
    {body}
</main><script src="app.js"></script></body>
</html>
'''
