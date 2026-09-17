"""Structured application specification for App Builder V1."""

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path

from .timepro_blueprint import TIMEPRO


@dataclass
class AppSpecification:
    mission: str
    app_name: str = "Generated App"
    app_type: str = "web"
    platforms: list[str] = field(default_factory=lambda: ["web"])
    users: list[str] = field(default_factory=list)
    screens: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    data_entities: list[str] = field(default_factory=list)
    business_rules: list[str] = field(default_factory=list)
    integrations: list[str] = field(default_factory=list)
    security_requirements: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")


class SpecificationBuilder:
    """Build a deterministic V1 specification from a natural-language mission."""

    def build(self, mission: str) -> AppSpecification:
        text = mission.strip()
        lower = text.lower()

        # TimePro is the first production target of the autonomous builder.
        # Keep its contract deterministic so later planning/build/test stages
        # operate from one canonical product definition.
        if "timepro" in lower or "folha de horas" in lower or "timesheet" in lower:
            features = list(TIMEPRO.features) + [
                "forms",
                "data storage",
                "calculation",
                "history",
                "dashboard",
                "mobile",
            ]
            return AppSpecification(
                mission=text,
                app_name=TIMEPRO.name,
                app_type="web",
                platforms=["web", "mobile-web"],
                users=list(TIMEPRO.roles),
                screens=list(TIMEPRO.screens),
                features=list(dict.fromkeys(features)),
                data_entities=list(TIMEPRO.entities),
                business_rules=[
                    "Total = end - start - break",
                    "End time must be greater than or equal to start time",
                    "Break must be zero or positive",
                    "Optional fields must never block submission",
                ],
                security_requirements=[
                    "Never expose secrets in generated source code",
                    "Validate user-controlled input",
                    "Keep employee and manager permissions distinct",
                    "Require human approval before external authentication, payment, messaging or production release",
                ],
                acceptance_criteria=list(TIMEPRO.acceptance_criteria),
            )

        features: list[str] = []
        screens = ["Main"]
        users = ["User"]
        entities: list[str] = []

        rules = {
            "authentication": ("login", "sign in", "account", "senha", "connexion"),
            "data storage": ("database", "data", "dados", "save", "store", "persist"),
            "forms": ("form", "field", "formulário", "cadastro"),
            "dashboard": ("dashboard", "admin", "manager", "gestor", "painel"),
            "mobile": ("mobile", "phone", "celular", "smartphone", "responsive"),
            "calculation": ("calculator", "calculate", "total", "calcular", "hours", "horas"),
            "history": ("list", "history", "lista", "histórico", "records", "registros"),
        }
        for feature, keywords in rules.items():
            if any(keyword in lower for keyword in keywords):
                features.append(feature)

        if "dashboard" in features:
            users.append("Manager")
            screens.append("Dashboard")
        if "forms" in features:
            screens.append("Form")
        if "history" in features:
            screens.append("History")
        if "authentication" in features:
            screens.append("Login")
        if "data storage" in features:
            entities.append("ApplicationRecord")

        security = ["Never expose secrets in generated source code", "Validate user-controlled input"]
        if "authentication" in features:
            security.append("Require explicit human approval before external account/login actions")

        acceptance = [
            "Generated project files exist and are non-empty",
            "Automated structural tests pass",
            "Detected requested features are represented in the generated project",
        ]
        if "mobile" in features:
            acceptance.append("Core interface is usable on a mobile viewport")

        return AppSpecification(
            mission=text,
            app_name=self._app_name(text),
            app_type="web",
            platforms=["web", "mobile-web"] if "mobile" in features else ["web"],
            users=users,
            screens=screens,
            features=features,
            data_entities=entities,
            security_requirements=security,
            acceptance_criteria=acceptance,
        )

    @staticmethod
    def _app_name(mission: str) -> str:
        words = mission.strip().split()
        if not words:
            return "Generated App"
        return " ".join(words[:6]).removesuffix(".")
