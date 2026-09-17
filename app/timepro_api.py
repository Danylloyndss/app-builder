"""TimePro application service backed by the database adapter."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import base64, binascii, mimetypes, secrets
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
        self._ensure_company_column()

    def _ensure_company_column(self):
        columns = self.db.fetch_all("PRAGMA table_info(timesheets)")
        if not any(c["name"] == "company" for c in columns):
            self.db.execute("ALTER TABLE timesheets ADD COLUMN company TEXT NOT NULL DEFAULT ''")

    def _validate_payload(self, payload: dict):
        employee, company = str(payload.get("employee", "")).strip(), str(payload.get("company", "")).strip()
        work_date = str(payload.get("work_date", "")).strip()
        location, start_time = str(payload.get("location", "")).strip(), str(payload.get("start_time", "")).strip()
        end_time, note = str(payload.get("end_time", "")).strip(), str(payload.get("note", "")).strip()
        if not employee or not work_date or not start_time or not end_time: raise TimeProValidationError("employee, work_date, start_time and end_time are required")
        if len(employee)>120 or len(company)>160 or len(location)>200 or len(note)>1000: raise TimeProValidationError("text field is too long")
        try: datetime.strptime(work_date, "%Y-%m-%d")
        except ValueError: raise TimeProValidationError("work_date must use YYYY-MM-DD format")
        try: pause = int(payload.get("pause_minutes", 0))
        except (TypeError, ValueError): raise TimeProValidationError("pause_minutes must be an integer")
        calculate_total(start_time, end_time, pause)
        return employee, company, work_date, location, start_time, pause, end_time, note

    def create_timesheet(self, payload: dict) -> dict:
        employee, company, work_date, location, start_time, pause, end_time, note = self._validate_payload(payload)
        total = calculate_total(start_time, end_time, pause)
        self.db.execute("INSERT INTO timesheets (employee, company, work_date, location, start_time, pause_minutes, end_time, total_minutes, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",(employee,company,work_date,location,start_time,pause,end_time,total,note))
        return self.db.fetch_one("SELECT * FROM timesheets WHERE id = last_insert_rowid()") or {}

    def update_timesheet(self, timesheet_id: int, payload: dict) -> dict:
        try: record_id = int(timesheet_id)
        except (TypeError, ValueError): raise TimeProValidationError("timesheet id must be an integer")
        employee, company, work_date, location, start_time, pause, end_time, note = self._validate_payload(payload)
        total = calculate_total(start_time, end_time, pause)
        if self.db.execute("UPDATE timesheets SET employee=?, company=?, work_date=?, location=?, start_time=?, pause_minutes=?, end_time=?, total_minutes=?, note=? WHERE id=?",(employee,company,work_date,location,start_time,pause,end_time,total,note,record_id)) == 0: return {}
        return self.db.fetch_one("SELECT * FROM timesheets WHERE id=?",(record_id,)) or {}

    def delete_timesheet(self, timesheet_id: int) -> bool:
        try: record_id = int(timesheet_id)
        except (TypeError, ValueError): raise TimeProValidationError("timesheet id must be an integer")
        files = self.db.fetch_all("SELECT stored_path FROM timesheet_attachments WHERE timesheet_id=? UNION ALL SELECT stored_path FROM timesheet_signatures WHERE timesheet_id=?",(record_id,record_id))
        self.db.execute("DELETE FROM timesheet_attachments WHERE timesheet_id=?",(record_id,))
        self.db.execute("DELETE FROM timesheet_signatures WHERE timesheet_id=?",(record_id,))
        deleted = self.db.execute("DELETE FROM timesheets WHERE id=?",(record_id,)) > 0
        if deleted:
            for row in files:
                try: Path(row["stored_path"]).unlink(missing_ok=True)
                except OSError: pass
        return deleted

    def history(self, employee: str | None = None, company: str | None = None, date_from: str | None = None, date_to: str | None = None) -> list[dict]:
        clauses, params = [], []
        if employee: clauses.append("employee LIKE ?"); params.append(f"%{employee}%")
        if company: clauses.append("company LIKE ?"); params.append(f"%{company}%")
        if date_from: clauses.append("work_date >= ?"); params.append(date_from)
        if date_to: clauses.append("work_date <= ?"); params.append(date_to)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.db.fetch_all(f"SELECT * FROM timesheets{where} ORDER BY work_date DESC,id DESC",params)
        for row in rows:
            row["attachments"] = self.db.fetch_all("SELECT id,filename,mime_type,created_at FROM timesheet_attachments WHERE timesheet_id=? ORDER BY id DESC",(row["id"],))
            row["has_signature"] = bool(self.db.fetch_one("SELECT timesheet_id FROM timesheet_signatures WHERE timesheet_id=?",(row["id"],)))
        return rows

    def dashboard(self, employee: str | None = None, company: str | None = None, date_from: str | None = None, date_to: str | None = None) -> dict:
        rows = self.history(employee, company, date_from, date_to)
        return {"count":len(rows),"total_minutes":sum(int(r["total_minutes"]) for r in rows),"employees":sorted({r["employee"] for r in rows}),"companies":sorted({r["company"] for r in rows if r.get("company")}),"timesheets":rows}

    def add_attachment(self, timesheet_id: int, filename: str, mime_type: str, content_b64: str) -> dict:
        try: record_id=int(timesheet_id); raw=base64.b64decode(content_b64, validate=True)
        except (TypeError, ValueError, binascii.Error): raise TimeProValidationError("invalid attachment")
        if not self.db.fetch_one("SELECT id FROM timesheets WHERE id=?",(record_id,)): raise TimeProValidationError("timesheet not found")
        if len(raw)>5_000_000: raise TimeProValidationError("attachment exceeds 5 MB")
        safe=Path(filename or "attachment").name.replace(" ","_"); ext=Path(safe).suffix.lower()
        allowed={".jpg",".jpeg",".png",".webp",".pdf"}
        if ext not in allowed: raise TimeProValidationError("only JPG, PNG, WEBP or PDF files are allowed")
        token=secrets.token_hex(8); stored=self.root/f"{record_id}_{token}{ext}"; stored.write_bytes(raw)
        self.db.execute("INSERT INTO timesheet_attachments(timesheet_id,filename,stored_path,mime_type) VALUES(?,?,?,?)",(record_id,safe,mime_type or mimetypes.guess_type(safe)[0] or "application/octet-stream",str(stored)))
        return self.db.fetch_one("SELECT id,filename,mime_type,created_at FROM timesheet_attachments WHERE id=last_insert_rowid()") or {}

    def save_signature(self, timesheet_id: int, content_b64: str) -> bool:
        try: record_id=int(timesheet_id); raw=base64.b64decode(content_b64, validate=True)
        except (TypeError, ValueError, binascii.Error): raise TimeProValidationError("invalid signature")
        if not self.db.fetch_one("SELECT id FROM timesheets WHERE id=?",(record_id,)): raise TimeProValidationError("timesheet not found")
        if len(raw)>1_000_000 or not raw.startswith(b"\x89PNG\r\n\x1a\n"): raise TimeProValidationError("invalid PNG signature")
        old=self.db.fetch_one("SELECT stored_path FROM timesheet_signatures WHERE timesheet_id=?",(record_id,)); stored=self.root/f"signature_{record_id}_{secrets.token_hex(8)}.png"; stored.write_bytes(raw)
        self.db.execute("DELETE FROM timesheet_signatures WHERE timesheet_id=?",(record_id,)); self.db.execute("INSERT INTO timesheet_signatures(timesheet_id,stored_path) VALUES(?,?)",(record_id,str(stored)))
        if old:
            try: Path(old["stored_path"]).unlink(missing_ok=True)
            except OSError: pass
        return True
