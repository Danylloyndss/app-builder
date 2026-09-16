"""Mission planner for App Builder V1."""


class Planner:
    """Convert a natural-language mission into deterministic build stages."""

    FEATURE_RULES = {
        "Implement user access flow": ("login", "sign in", "account", "senha", "connexion", "connect"),
        "Implement data storage layer": ("database", "data", "dados", "save", "store", "enregistrer", "persist"),
        "Implement input forms": ("form", "field", "formulário", "cadastro", "register", "timesheet", "folha de horas"),
        "Implement dashboard": ("dashboard", "admin", "manager", "gestor", "painel"),
        "Optimize mobile experience": ("mobile", "phone", "celular", "smartphone", "responsive"),
        "Implement calculator": ("calculator", "calculate", "total", "calcular", "hours", "horas", "timesheet", "folha de horas"),
        "Implement history and lists": ("list", "history", "lista", "histórico", "records", "registros", "timesheet", "folha de horas"),
    }

    def create_plan(self, mission: str) -> list[str]:
        mission = mission.strip()
        lower = mission.lower()
        plan = ["Understand the mission", "Create the project structure"]
        for task, keywords in self.FEATURE_RULES.items():
            if any(keyword in lower for keyword in keywords):
                plan.append(task)
        plan.extend([
            "Implement the requested functionality",
            "Run tests",
            "Fix errors and retest",
            "Save progress",
        ])
        return plan
