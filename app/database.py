"""Small database adapter layer used by generated applications.

The adapter is intentionally dependency-free so the builder can generate a
real persistence boundary without forcing a hosted database vendor. SQLite is
the default local/early-production implementation; the interface can later be
backed by Postgres or another provider without changing application services.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator, Sequence


class DatabaseError(RuntimeError):
    """Raised when the database adapter cannot complete an operation."""


class Database:
    """Minimal transactional database interface for generated apps."""

    def __init__(self, path: str | Path = "data/app.db") -> None:
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path.as_posix())
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            raise DatabaseError(str(exc)) from exc
        finally:
            conn.close()

    def execute(self, sql: str, params: Sequence[object] = ()) -> int:
        with self.connection() as conn:
            cursor = conn.execute(sql, tuple(params))
            return int(cursor.rowcount)

    def fetch_one(self, sql: str, params: Sequence[object] = ()) -> dict | None:
        with self.connection() as conn:
            row = conn.execute(sql, tuple(params)).fetchone()
            return dict(row) if row else None

    def fetch_all(self, sql: str, params: Sequence[object] = ()) -> list[dict]:
        with self.connection() as conn:
            return [dict(row) for row in conn.execute(sql, tuple(params)).fetchall()]

    def initialize(self, schema: str) -> None:
        with self.connection() as conn:
            conn.executescript(schema)


TIMEPRO_SCHEMA = """
CREATE TABLE IF NOT EXISTS timesheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee TEXT NOT NULL,
    work_date TEXT NOT NULL,
    location TEXT NOT NULL DEFAULT '',
    start_time TEXT NOT NULL,
    pause_minutes INTEGER NOT NULL DEFAULT 0 CHECK (pause_minutes >= 0),
    end_time TEXT NOT NULL,
    total_minutes INTEGER NOT NULL CHECK (total_minutes >= 0),
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_timesheets_work_date ON timesheets(work_date);
CREATE INDEX IF NOT EXISTS idx_timesheets_employee ON timesheets(employee);

CREATE TABLE IF NOT EXISTS timesheet_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timesheet_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    mime_type TEXT NOT NULL DEFAULT 'application/octet-stream',
    client_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(timesheet_id) REFERENCES timesheets(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_timesheet_attachments_timesheet ON timesheet_attachments(timesheet_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_timesheet_attachment_client ON timesheet_attachments(client_id) WHERE client_id <> '';

CREATE TABLE IF NOT EXISTS timesheet_signatures (
    timesheet_id INTEGER PRIMARY KEY,
    stored_path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(timesheet_id) REFERENCES timesheets(id) ON DELETE CASCADE
);
"""


def migrate_timepro_database(db: Database) -> None:
    """Upgrade older TimePro databases without destroying existing data."""
    columns = {row["name"] for row in db.fetch_all("PRAGMA table_info(timesheets)")}
    if "company" not in columns:
        db.execute("ALTER TABLE timesheets ADD COLUMN company TEXT NOT NULL DEFAULT ''")
    if "idempotency_key" not in columns:
        db.execute("ALTER TABLE timesheets ADD COLUMN idempotency_key TEXT NOT NULL DEFAULT ''")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_timesheets_idempotency ON timesheets(idempotency_key) WHERE idempotency_key <> ''")


def create_timepro_database(path: str | Path = "data/timepro.db") -> Database:
    """Create/initialize the persistence store used by TimePro."""
    db = Database(path)
    db.initialize(TIMEPRO_SCHEMA)
    migrate_timepro_database(db)
    return db
