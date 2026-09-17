"""TimePro application service backed by the database adapter."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import base64
import binascii
import mimetypes
import secrets
from .database import create_timepro_database

class TimeProValidationError(ValueError): pass

def _minutes(value: str) -> int:
    try:
        hour, minute = (int(part) for part in value.split(":", 1))
        if not (0 <= hour <= 23 and 0 <= minute <= 59): raise ValueError
        return hour * 60 + minute
    except (ValueError, TypeError): raise TimeProValidationError("time must use HH:MM format")

def calculate_total(start_time: str, end_time: str, pause_minutes: int = 0) -> int:
    start, end = _minutes(start_time), _minutes(end_time)
    try: pause = int(pause_minutes)
    except (TypeError, ValueError): raise TimeProValidationError("pause_minutes must be an integer")
    if pause < 0: raise TimeProValidationError("pause_minutes cannot be negative")
    total = end - start - pause
    if total <= 0: raise TimeProValidationError("end time must be after start time and pause")
    return total

class TimeProService:
    def __init__(self, path: str | Path = "data/timepro.db") -> None:
        self.db = create_timepro_database(path)
        self.root = Path(path).parent / "timepro_uploads"
        self.root.mkdir(parents=True, exist_ok=True)

    def _validate_payload(self, payload: dict):
        employee, work_date = str(payload.get("employee", "")).strip(), str(payload.get("work_date", "")).strip()
        location, start_time = str(payload.get("location", "")).strip(), str(payload.get("start_time", "")).strip()
        end_time, note = str(payload.get("end_time", "")).strip(), str(payload.get("note", "")).strip()
        if not employee or not work_date or not start_time or not end_time: raise TimeProValidationError("employee, work_date, start_time and end_time are required")
        try: datetime.strptime(work_date, "%Y-%m-%d")
        except ValueError: raise TimeProValidationError("work_date must use YYYY-MM-DD format")
        try: pause = int(payload.get("pause_minutes", 0))
        except (TypeError, ValueError): raise TimeProValidationError("pause_minutes must be an integer")
        calculate_total(start_time, end_time, pause)
        return employee, work_date, location, start_time, pause, end_time, note

    def create_timesheet(self, payload: dict) -> dict:
        employee, work_date, location, start_time, pause, end_time, note = self._validate_payload(payload)
        total = calculate_total(start_time, end_time, pause)
        self.db.execute("INSERT INTO timesheets (employee, work_date, location, start_time, pause_minutes, end_time, total_minutes, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",(employee,work_date,location,start_time,pause,end_time,total,note))
        return self.db.fetch_one("SELECT * FROM timesheets WHERE id = last_insert_rowid()") or {}

    def update_timesheet(self, timesheet_id: int, payload: dict) -> dict:
        try: record_id = int(timesheet_id)
        except (TypeError, ValueError): raise TimeProValidationError("timesheet id must be an integer")
        employee, work_date, location, start_time, pause, end_time, note = self._validate_payload(payload)
        total = calculate_total(start_time, end_time, pause)
        if self.db.execute("UPDATE timesheets SET employee=?, work_date=?, location=?, start_time=?, pause_minutes=?, end_time=?, total_minutes=?, note=? WHERE id=?",(employee,work_date,location,start_time,pause,end_time,total,note,record_id)) == 0: return {}
        return self.db.fetch_one("SELECT * FROM timesheets WHERE id=?",(record_id,)) or {}

    def delete_timesheet(self, timesheet_id: int) -> bool:
        try: record_id = int(timesheet_id)
        except (TypeError, ValueError): raise TimeProValidationError("timesheet id must be an integer")
        self.db.execute("DELETE FROM timesheet_attachments WHERE timesheet_id=?",(record_id,))
        self.db.execute("DELETE FROM timesheet_signatures WHERE timesheet_id=?",(record_id,))
        return self.db.execute("DELETE FROM timesheets WHERE id=?",(record_id,)) > 0

    def history(self, employee: str | None = None) -> list[dict]:
        rows = self.db.fetch_all("SELECT * FROM timesheets WHERE employee=? ORDER BY work_date DESC,id DESC",(employee,)) if employee else self.db.fetch_all("SELECT * FROM timesheets ORDER BY work_date DESC,id DESC")
        for row in rows:
            row["attachments"] = self.db.fetch_all("SELECT id,filename,mime_type,created_at FROM timesheet_attachments WHERE timesheet_id=? ORDER BY id DESC",(row["id"],))
            row["has_signature"] = bool(self.db.fetch_one("SELECT timesheet_id FROM timesheet_signatures WHERE timesheet_id=?",(row["id"],)))
        return rows

    def dashboard(self) -> dict:
        rows = self.history()
        return {"count":len(rows),"total_minutes":sum(int(r["total_minutes"]) for r in rows),"employees":sorted({r["employee"] for r in rows}),"timesheets":rows}

    def add_attachment(self, timesheet_id: int, filename: str, mime_type: str, content_b64: str) -> dict:
        try: record_id=int(timesheet_id); raw=base64.b64decode(content_b64, validate=True)
        except (TypeError, ValueError, binascii.Error): raise TimeProValidationError("invalid attachment")
        if not self.db.fetch_one("SELECT id FROM timesheets WHERE id=?",(record_id,)): raise TimeProValidationError("timesheet not found")
        if len(raw)>5_000_000: raise TimeProValidationError("attachment exceeds 5 MB")
        safe=Path(filename or "attachment").name.replace(" ","_")
        ext=Path(safe).suffix.lower()
        allowed={".jpg",".jpeg",".png",".webp",".pdf"}
        if ext not in allowed: raise TimeProValidationError("only JPG, PNG, WEBP or PDF files are allowed")
        token=secrets.token_hex(8); stored=self.root/f"{record_id}_{token}{ext}"; stored.write_bytes(raw)
        self.db.execute("INSERT INTO timesheet_attachments(timesheet_id,filename,stored_path,mime_type) VALUES(?,?,?,?)",(record_id,safe,str(stored),mime_type or mimetypes.guess_type(safe)[0] or "application/octet-stream"))
        return self.db.fetch_one("SELECT id,filename,mime_type,created_at FROM timesheet_attachments WHERE id=last_insert_rowid()") or {}

    def save_signature(self, timesheet_id: int, content_b64: str) -> bool:
        try: record_id=int(timesheet_id); raw=base64.b64decode(content_b64, validate=True)
        except (TypeError, ValueError, binascii.Error): raise TimeProValidationError("invalid signature")
        if not self.db.fetch_one("SELECT id FROM timesheets WHERE id=?",(record_id,)): raise TimeProValidationError("timesheet not found")
        if len(raw)>1_000_000: raise TimeProValidationError("signature exceeds 1 MB")
        stored=self.root/f"signature_{record_id}_{secrets.token_hex(8)}.png"; stored.write_bytes(raw)
        self.db.execute("DELETE FROM timesheet_signatures WHERE timesheet_id=?",(record_id,))
        self.db.execute("INSERT INTO timesheet_signatures(timesheet_id,stored_path) VALUES(?,?)",(record_id,str(stored)))
        return True
