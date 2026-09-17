"""TimePro application service backed by the database adapter."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .database import create_timepro_database


class TimeProValidationError(ValueError):
    """Raised when a TimePro timesheet is invalid."""


def _minutes(value: str) -> int:
    try:
        hour, minute = (int(part) for part in value.split(":", 1))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        return hour * 60 + minute
    except (ValueError, TypeError):
        raise TimeProValidationError("time must use HH:MM format")


def calculate_total(start_time: str, end_time: str, pause_minutes: int = 0) -> int:
    start = _minutes(start_time)
    end = _minutes(end_time)
    try:
        pause = int(pause_minutes)
    except (TypeError, ValueError):
        raise TimeProValidationError("pause_minutes must be an integer")
    if pause < 0:
        raise TimeProValidationError("pause_minutes cannot be negative")
    total = end - start - pause
    if total <= 0:
        raise TimeProValidationError("end time must be after start time and pause")
    return total


class TimeProService:
    def __init__(self, path: str | Path = "data/timepro.db") -> None:
        self.db = create_timepro_database(path)

    def create_timesheet(self, payload: dict) -> dict:
        employee = str(payload.get("employee", "")).strip()
        work_date = str(payload.get("work_date", "")).strip()
        location = str(payload.get("location", "")).strip()
        start_time = str(payload.get("start_time", "")).strip()
        end_time = str(payload.get("end_time", "")).strip()
        note = str(payload.get("note", "")).strip()
        if not employee or not work_date or not start_time or not end_time:
            raise TimeProValidationError("employee, work_date, start_time and end_time are required")
        try:
            datetime.strptime(work_date, "%Y-%m-%d")
        except ValueError:
            raise TimeProValidationError("work_date must use YYYY-MM-DD format")
        total_minutes = calculate_total(start_time, end_time, payload.get("pause_minutes", 0))
        self.db.execute(
            "INSERT INTO timesheets (employee, work_date, location, start_time, pause_minutes, end_time, total_minutes, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (employee, work_date, location, start_time, int(payload.get("pause_minutes", 0)), end_time, total_minutes, note),
        )
        return self.db.fetch_one("SELECT * FROM timesheets WHERE id = last_insert_rowid()") or {}

    def history(self, employee: str | None = None) -> list[dict]:
        if employee:
            return self.db.fetch_all("SELECT * FROM timesheets WHERE employee = ? ORDER BY work_date DESC, id DESC", (employee,))
        return self.db.fetch_all("SELECT * FROM timesheets ORDER BY work_date DESC, id DESC")

    def dashboard(self) -> dict:
        rows = self.history()
        return {
            "count": len(rows),
            "total_minutes": sum(int(row["total_minutes"]) for row in rows),
            "employees": sorted({row["employee"] for row in rows}),
            "timesheets": rows,
        }
