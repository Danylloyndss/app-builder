"""Canonical TimePro product blueprint used as the first real App Builder target."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TimeProBlueprint:
    name: str = "TimePro"
    roles: tuple[str, ...] = ("Employee", "Manager")
    screens: tuple[str, ...] = (
        "Daily Timesheet",
        "History",
        "Manager Dashboard",
    )
    required_fields: tuple[str, ...] = (
        "employee",
        "company",
        "date",
        "site/client",
        "start",
        "break",
        "end",
    )
    optional_fields: tuple[str, ...] = ("photos", "note", "signature")
    features: tuple[str, ...] = (
        "digital timesheet",
        "automatic hour total",
        "input validation",
        "history",
        "manager dashboard",
        "mobile responsive interface",
        "optional photos",
        "optional note",
        "signature and submission",
    )
    entities: tuple[str, ...] = ("Timesheet", "Employee", "Company")
    acceptance_criteria: tuple[str, ...] = (
        "Employee can enter a workday timesheet",
        "Total hours are calculated automatically from start, end and break",
        "Invalid time ranges are rejected",
        "Submitted timesheets are visible in history",
        "Manager dashboard can summarize submitted timesheets",
        "Core flow works on a mobile viewport",
        "Optional photos, note and signature do not block submission",
    )

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "roles": list(self.roles),
            "screens": list(self.screens),
            "required_fields": list(self.required_fields),
            "optional_fields": list(self.optional_fields),
            "features": list(self.features),
            "entities": list(self.entities),
            "acceptance_criteria": list(self.acceptance_criteria),
        }


TIMEPRO = TimeProBlueprint()
