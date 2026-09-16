"""Mission planner for App Builder V1.

The planner turns a natural-language mission into concrete, deterministic
build stages. It deliberately stays dependency-free so it can run in the
same sandbox as the rest of V1.
"""


class Planner:
    def create_plan(self, mission: str) -> list[str]:
        mission = mission.strip()
        plan = [
            "Understand the mission",
            "Create the project structure",
        ]

        # Add focused implementation stages from common app requirements.
        lower = mission.lower()
        if any(word in lower for word in ("login", "account", "user", "senha")):
            plan.append("Implement user access flow")
        if any(word in lower for word in ("database", "data", "dados", "save", "store")):
            plan.append("Implement data storage layer")
        if any(word in lower for word in ("form", "field", "formulário", "cadastro")):
            plan.append("Implement input forms")
        if any(word in lower for word in ("dashboard", "admin", "manager", "gestor")):
            plan.append("Implement dashboard")
        if any(word in lower for word in ("mobile", "phone", "celular", "responsive")):
            plan.append("Optimize mobile experience")

        plan.extend([
            "Implement the requested functionality",
            "Run tests",
            "Fix errors and retest",
            "Save progress",
        ])
        return plan
