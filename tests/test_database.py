from pathlib import Path

from app.database import Database, create_timepro_database


def test_database_crud_and_transaction(tmp_path: Path):
    db = Database(tmp_path / "app.db")
    db.initialize("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")

    assert db.execute("INSERT INTO items (name) VALUES (?)", ("first",)) == 1
    assert db.fetch_one("SELECT name FROM items WHERE id = ?", (1,))["name"] == "first"
    assert db.fetch_all("SELECT name FROM items") == [{"name": "first"}]


def test_timepro_schema_is_ready(tmp_path: Path):
    db = create_timepro_database(tmp_path / "timepro.db")
    db.execute(
        "INSERT INTO timesheets "
        "(employee, work_date, location, start_time, pause_minutes, end_time, total_minutes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("Danyllo", "2026-09-17", "Neuchatel", "08:00", 30, "17:00", 510),
    )

    row = db.fetch_one("SELECT employee, total_minutes FROM timesheets WHERE employee = ?", ("Danyllo",))
    assert row == {"employee": "Danyllo", "total_minutes": 510}
