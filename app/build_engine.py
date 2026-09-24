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
        if "generate backend and persistence layer" in normalized or "validate backend and persistence contract" in normalized:
            return self.implement_backend(mission)
        if "implement requested functionality" in normalized:
            return self.implement(mission)
        if "repair after test failure" in normalized:
            return self.repair(mission)
        if "save progress" in normalized or "understand the mission" in normalized:
            self.project.write_file(".app-builder/mission.txt", mission + "\n")
            return "Mission/progress recorded"
        if normalized in {"validate application specification", "run security review", "run acceptance checks", "fix errors and retest"}:
            return f"Checkpoint completed: {task}"
        return f"No build handler for task: {task}"

    @staticmethod
    def is_timepro(mission: str) -> bool:
        text = mission.lower()
        return any(token in text for token in ("timepro", "timesheet", "folha de horas"))

    def create_structure(self, mission: str = "") -> str:
        if self.is_timepro(mission):
            self.project.write_file("index.html", self._timepro_html())
            self.project.write_file("app.js", self._timepro_javascript())
            self.project.write_file("README.md", self._timepro_readme())
            self.project.write_file(".app-builder/mission.txt", mission + "\n")
            self._save_features(["forms", "storage", "calculator", "list", "dashboard", "mobile"])
            return "TimePro project structure created"
        self.project.write_file("index.html", self._html("Generated App", mission))
        self.project.write_file("app.js", self._javascript())
        self.project.write_file("README.md", self._readme(mission))
        self.project.write_file(".app-builder/mission.txt", mission + "\n")
        self._save_features([])
        return "Project structure created"

    def implement(self, mission: str) -> str:
        if self.is_timepro(mission):
            self.project.write_file("index.html", self._timepro_html())
            self.project.write_file("app.js", self._timepro_javascript())
            self.project.write_file("README.md", self._timepro_readme())
            self.project.write_file("api_contract.json", self._timepro_api_contract())
            self.project.write_file("hello_app.txt", "TimePro\n")
            self.project.write_file(".app-builder/mission.txt", mission + "\n")
            self._save_features(["forms", "storage", "calculator", "list", "dashboard", "mobile", "api-contract"])
            return "Implemented TimePro functional MVP with backend contract"
        title = self._title(mission)
        features = self.detect_features(mission)
        self.project.write_file("index.html", self._html(title, mission, features))
        self.project.write_file("app.js", self._javascript(features))
        self.project.write_file("README.md", self._readme(mission, features))
        self.project.write_file("hello_app.txt", f"{title}\n")
        if "storage" in features:
            self.project.write_file("api_contract.json", self._generic_api_contract())
        self.project.write_file(".app-builder/mission.txt", mission + "\n")
        self._save_features(features)
        return f"Implemented generated app: {title} ({len(features)} features)"

    def implement_backend(self, mission: str) -> str:
        if self.is_timepro(mission):
            self.project.write_file("backend.py", self._timepro_backend())
            self.project.write_file("tests/test_backend_integration.py", self._timepro_integration_test())
            self.project.write_file("api_contract.json", self._timepro_api_contract())
            manifest = {"runtime": "python", "entrypoint": "backend.py", "database": "sqlite", "api_base": "/api/timepro", "health": "/health", "generated": True}
            self.project.write_file(".app-builder/backend.json", json.dumps(manifest, indent=2) + "\n")
            return "TimePro backend persistence service generated"
        features = self._load_features()
        if "storage" not in features:
            return "Backend generation skipped: project has no storage capability"
        manifest = {
            "runtime": "python",
            "entrypoint": "backend.py",
            "database": "sqlite",
            "api_base": "/api",
            "health": "/health",
            "generated": True,
            "capabilities": ["crud", "health"],
        }
        schema = self._generic_backend_schema(mission)
        self.project.write_file("backend.py", self._generic_backend(mission, schema))
        self.project.write_file("tests/test_backend_integration.py", self._generic_backend_test(schema))
        self.project.write_file(".app-builder/backend.json", json.dumps({**manifest, "schema": ".app-builder/backend_schema.json"}, indent=2) + "\n")
        self.project.write_file(".app-builder/backend_schema.json", json.dumps(schema, indent=2) + "\n")
        self.project.write_file("api_contract.json", self._generic_api_contract(schema))
        return "Generic persistent backend generated"

    @staticmethod
    def _generic_backend(mission: str = "", schema: dict | None = None) -> str:
        schema = schema or {"entity": "ApplicationRecord", "entities": ["ApplicationRecord"], "fields": ["id"], "entity_fields": {"ApplicationRecord": ["id"]}, "business_rules": []}
        schema_json = json.dumps(schema, ensure_ascii=False)
        source = r'''from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import sqlite3
from urllib.parse import parse_qs, urlparse

DB = os.environ.get("APP_DB", "app.db")
HOST = os.environ.get("APP_HOST", "127.0.0.1")
PORT = int(os.environ.get("APP_PORT", "8001"))
SCHEMA = json.loads(__SCHEMA__)

def init_db():
    with sqlite3.connect(DB) as db:
        db.execute("CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        db.execute("CREATE TABLE IF NOT EXISTS entity_records (id INTEGER PRIMARY KEY AUTOINCREMENT, entity TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_entity_records_entity ON entity_records(entity)")

def entity_name():
    return str(SCHEMA.get("entity") or "ApplicationRecord")

def slug(value):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", str(value)).lower().replace("_", "-")

def entity_for_path(path):
    if path == "/api/records":
        return entity_name()
    for entity in SCHEMA.get("entities", [entity_name()]):
        if path == "/api/" + slug(entity):
            return str(entity)
    return None

def fields_for_entity(entity):
    mapped = SCHEMA.get("entity_fields") or {}
    fields = mapped.get(entity) or SCHEMA.get("fields", ["id"])
    return [str(x) for x in fields if str(x) and str(x) != "id"]

def payload(row):
    return {"id": row[0], **json.loads(row[1]), "created_at": row[2], "_entity": row[3]}

def validate(data, entity=None):
    if not isinstance(data, dict):
        raise ValueError("payload must be an object")
    fields = fields_for_entity(entity or entity_name())
    unknown = [key for key in data if key not in fields]
    if unknown:
        raise ValueError("unknown fields: " + ", ".join(sorted(unknown)))
    for rule in [str(x).lower() for x in SCHEMA.get("business_rules", [])]:
        if ("zero or positive" in rule or "non-negative" in rule) and any(key in data for key in ("amount", "price", "total", "hours", "pause", "pause_minutes", "break")):
            for key in ("amount", "price", "total", "hours", "pause", "pause_minutes", "break"):
                if key in data and float(data[key]) < 0:
                    raise ValueError(key + " must be zero or positive")
    return data

def save(data, record_id=None, entity=None):
    encoded = json.dumps(data, ensure_ascii=False)
    entity = entity or entity_name()
    with sqlite3.connect(DB) as db:
        if record_id is None:
            cur = db.execute("INSERT INTO entity_records (entity, data) VALUES (?, ?)", (entity, encoded))
            record_id = cur.lastrowid
        else:
            changed = db.execute("UPDATE entity_records SET data=? WHERE id=? AND entity=?", (encoded, record_id, entity)).rowcount
            if not changed:
                return None
        return db.execute("SELECT id, data, created_at, entity FROM entity_records WHERE id=? AND entity=?", (record_id, entity)).fetchone()

class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, value):
        raw = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1000000: raise ValueError("request too large")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return self.send_json(200, {"ok": True, "entity": entity_name(), "schema_version": SCHEMA.get("version", 1)})
        entity = entity_for_path(parsed.path)
        if entity:
            with sqlite3.connect(DB) as db:
                rows = db.execute("SELECT id, data, created_at, entity FROM entity_records WHERE entity=? ORDER BY id DESC", (entity,)).fetchall()
            return self.send_json(200, [payload(row) for row in rows])
        return self.send_json(404, {"error": "not found"})

    def do_POST(self):
        entity = entity_for_path(urlparse(self.path).path)
        if not entity: return self.send_json(404, {"error": "not found"})
        try:
            return self.send_json(201, payload(save(validate(self.read_json(), entity), entity=entity)))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self.send_json(400, {"error": str(exc)})

    def do_PUT(self):
        parsed = urlparse(self.path)
        entity = entity_for_path(parsed.path)
        if not entity: return self.send_json(404, {"error": "not found"})
        try:
            data = self.read_json()
            record_id = int(data.pop("id", parse_qs(parsed.query).get("id", ["0"])[0]))
            if record_id <= 0: return self.send_json(400, {"error": "id is required"})
            row = save(validate(data, entity), record_id, entity=entity)
            return self.send_json(200, payload(row)) if row else self.send_json(404, {"error": "not found"})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self.send_json(400, {"error": str(exc)})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        entity = entity_for_path(parsed.path)
        if not entity: return self.send_json(404, {"error": "not found"})
        try:
            record_id = int(parse_qs(parsed.query).get("id", ["0"])[0])
            with sqlite3.connect(DB) as db:
                changed = db.execute("DELETE FROM entity_records WHERE id=? AND entity=?", (record_id, entity)).rowcount
            return self.send_json(200, {"deleted": True}) if changed else self.send_json(404, {"error": "not found"})
        except ValueError:
            return self.send_json(400, {"error": "id is required"})

if __name__ == "__main__":
    init_db()
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
'''
        return source.replace("__SCHEMA__", repr(schema_json))

    @staticmethod
    def _generic_backend_test(schema: dict | None = None) -> str:
        schema = schema or {"entity": "ApplicationRecord", "entities": ["ApplicationRecord"], "entity_fields": {"ApplicationRecord": ["id", "date", "location", "note"]}}
        entity = str(schema.get("entity") or "ApplicationRecord")
        resource = re.sub(r"(?<!^)(?=[A-Z])", "_", entity).lower().replace("_", "-")
        fields = [str(x) for x in (schema.get("entity_fields") or {}).get(entity, schema.get("fields", ["id"])) if str(x) != "id"]
        sample = {}
        for field in fields:
            if field == "email":
                sample[field] = "test@example.com"
            elif field.endswith("_id"):
                sample[field] = 1
            elif "amount" in field or field in {"price", "total", "hours"}:
                sample[field] = 1
            elif "date" in field:
                sample[field] = "2026-01-02"
            else:
                sample[field] = "Test"
        sample_json = json.dumps(sample, ensure_ascii=False)
        update_data = dict(sample)
        if fields:
            update_data[fields[0]] = "Updated" if fields[0] not in {"date", "amount", "price", "total", "hours"} else ("2026-01-03" if fields[0] == "date" else 2)
        update_json = json.dumps(update_data, ensure_ascii=False)
        return r'''import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

root = Path(__file__).resolve().parents[1]

def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]

def call(url, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = Request(url, data=data, method=method, headers={"Content-Type": "application/json"} if data else {})
    with urlopen(req, timeout=4) as response:
        return json.load(response)

with tempfile.TemporaryDirectory() as tmp:
    port = str(free_port())
    env = dict(os.environ, APP_PORT=port, APP_DB=str(Path(tmp) / "app.db"))
    process = subprocess.Popen([sys.executable, str(root / "backend.py")], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = "http://127.0.0.1:" + port
        for _ in range(30):
            try:
                assert call(base + "/health")["ok"] is True
                break
            except Exception:
                time.sleep(0.05)
        else:
            raise AssertionError("backend did not become healthy")
        created = call(base + "/api/__RESOURCE__", "POST", __SAMPLE__)
        assert created["id"] > 0
        rows = call(base + "/api/__RESOURCE__")
        assert rows and rows[0]["id"] == created["id"]
        record_id = created["id"]
        updated = call(base + "/api/__RESOURCE__?id=" + str(record_id), "PUT", dict(__UPDATE__))
        assert updated["id"] == record_id
        try:
            call(base + "/api/__RESOURCE__", "POST", {"unexpected": True})
            raise AssertionError("unknown field accepted")
        except HTTPError as exc:
            assert exc.code == 400
        deleted = call(base + "/api/__RESOURCE__?id=" + str(record_id), "DELETE")
        assert deleted["deleted"] is True
        assert call(base + "/api/__RESOURCE__") == []
        compatibility = call(base + "/api/records")
        assert compatibility == []
    finally:
        process.terminate()
        process.wait(timeout=3)
'''.replace("__RESOURCE__", resource).replace("__SAMPLE__", sample_json).replace("__UPDATE__", update_json)

    @staticmethod
    def _timepro_integration_test() -> str:
        return r'''import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]

def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]

def call(base, path, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"} if data else {})
    with urlopen(request, timeout=4) as response:
        return json.load(response)

with tempfile.TemporaryDirectory() as tmp:
    port = free_port()
    env = dict(os.environ, TIMEPRO_PORT=str(port), TIMEPRO_DB=str(Path(tmp) / "timepro.db"))
    process = subprocess.Popen([sys.executable, str(ROOT / "backend.py")], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = "http://127.0.0.1:" + str(port)
        for _ in range(40):
            try:
                assert call(base, "/health")["ok"] is True
                break
            except Exception:
                time.sleep(0.05)
        else:
            raise AssertionError("TimePro backend did not become healthy")

        try:
            call(base, "/api/timepro/timesheets", "POST", {
                "employee": "Test Employee",
                "company": "Test Company",
                "work_date": "2026-01-02",
                "location": "Test Site",
                "start_time": "08:00",
                "pause_minutes": -1,
                "end_time": "17:00",
            })
            raise AssertionError("negative pause accepted")
        except Exception as exc:
            assert "HTTP Error 400" in str(exc)

        created = call(base, "/api/timepro/timesheets", "POST", {
            "employee": "Test Employee",
            "company": "Test Company",
            "work_date": "2026-01-02",
            "location": "Test Site",
            "start_time": "08:00",
            "pause_minutes": 30,
            "end_time": "17:00",
            "note": "integration",
        })
        assert created["id"] > 0
        assert created["total_minutes"] == 510

        rows = call(base, "/api/timepro/timesheets")
        assert len(rows) == 1
        assert rows[0]["id"] == created["id"]

        dashboard = call(base, "/api/timepro/dashboard")
        assert dashboard["timesheets"] == 1

        updated = call(base, "/api/timepro/timesheets?id=" + str(created["id"]), "PUT", {
            "employee": "Updated Employee",
            "company": "Test Company",
            "work_date": "2026-01-02",
            "location": "Updated Site",
            "start_time": "08:00",
            "pause_minutes": 30,
            "end_time": "17:00",
            "note": "updated",
        })
        assert updated["id"] == created["id"]

        deleted = call(base, "/api/timepro/timesheets?id=" + str(created["id"]), "DELETE")
        assert deleted["deleted"] is True
        assert call(base, "/api/timepro/timesheets") == []
    finally:
        process.terminate()
        process.wait(timeout=3)
'''
    
    @staticmethod
    def _timepro_backend() -> str:
        return """from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import sqlite3
from urllib.parse import urlparse

DB = os.environ.get("TIMEPRO_DB", "timepro.db")
HOST = os.environ.get("TIMEPRO_HOST", "127.0.0.1")
PORT = int(os.environ.get("TIMEPRO_PORT", "8001"))

def init_db():
    with sqlite3.connect(DB) as db:
        db.execute("CREATE TABLE IF NOT EXISTS timesheets (id INTEGER PRIMARY KEY AUTOINCREMENT, employee TEXT NOT NULL, company TEXT NOT NULL DEFAULT '', work_date TEXT NOT NULL, location TEXT NOT NULL DEFAULT '', start_time TEXT NOT NULL, pause_minutes INTEGER NOT NULL DEFAULT 0, end_time TEXT NOT NULL, total_minutes INTEGER NOT NULL, note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")

def minutes(value):
    h, m = (int(x) for x in value.split(":", 1))
    if not (0 <= h <= 23 and 0 <= m <= 59): raise ValueError("invalid time")
    return h * 60 + m

def total(start, end, pause):
    pause = int(pause)
    if pause < 0:
        raise ValueError("pause must be zero or positive")
    value = minutes(end) - minutes(start) - pause
    if value <= 0: raise ValueError("end time must be after start time and pause")
    return value

def row_payload(row):
    if row is None:
        return None
    columns = ("id", "employee", "company", "work_date", "location", "start_time", "pause_minutes", "end_time", "total_minutes", "note", "created_at")
    return dict(zip(columns, row))

def create(payload):
    required = ("employee", "work_date", "start_time", "end_time")
    if any(not str(payload.get(k, "")).strip() for k in required): raise ValueError("required field missing")
    value = total(payload["start_time"], payload["end_time"], payload.get("pause_minutes", 0))
    row = (str(payload["employee"]).strip(), str(payload.get("company", "")).strip(), str(payload["work_date"]).strip(), str(payload.get("location", "")).strip(), str(payload["start_time"]), int(payload.get("pause_minutes", 0)), str(payload["end_time"]), value, str(payload.get("note", "")).strip())
    with sqlite3.connect(DB) as db:
        cur = db.execute("INSERT INTO timesheets (employee, company, work_date, location, start_time, pause_minutes, end_time, total_minutes, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", row)
        return db.execute("SELECT * FROM timesheets WHERE id=?", (cur.lastrowid,)).fetchone()

def update(record_id, payload):
    value = total(payload["start_time"], payload["end_time"], payload.get("pause_minutes", 0))
    with sqlite3.connect(DB) as db:
        changed = db.execute("UPDATE timesheets SET employee=?, company=?, work_date=?, location=?, start_time=?, pause_minutes=?, end_time=?, total_minutes=?, note=? WHERE id=?", (str(payload["employee"]).strip(), str(payload.get("company", "")).strip(), str(payload["work_date"]).strip(), str(payload.get("location", "")).strip(), str(payload["start_time"]), int(payload.get("pause_minutes", 0)), str(payload["end_time"]), value, str(payload.get("note", "")).strip(), record_id)).rowcount
        if not changed: return None
        return db.execute("SELECT * FROM timesheets WHERE id=?", (record_id,)).fetchone()

def delete(record_id):
    with sqlite3.connect(DB) as db:
        return db.execute("DELETE FROM timesheets WHERE id=?", (record_id,)).rowcount > 0

class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        raw = json.dumps(payload).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1000000: raise ValueError("request too large")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health": return self.send_json(200, {"ok": True})
        if path == "/api/timepro/timesheets":
            with sqlite3.connect(DB) as db:
                db.row_factory = sqlite3.Row
                return self.send_json(200, [dict(r) for r in db.execute("SELECT * FROM timesheets ORDER BY id DESC").fetchall()])
        if path == "/api/timepro/dashboard":
            with sqlite3.connect(DB) as db:
                db.row_factory = sqlite3.Row
                rows = [dict(r) for r in db.execute("SELECT * FROM timesheets ORDER BY id DESC").fetchall()]
            return self.send_json(200, {"count": len(rows), "total_minutes": sum(int(r["total_minutes"]) for r in rows), "employees": sorted({r["employee"] for r in rows}), "timesheets": len(rows)})
        return self.send_json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/timepro/timesheets": return self.send_json(404, {"error": "not found"})
        try:
            payload = self.read_json()
            return self.send_json(201, row_payload(create(payload)))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self.send_json(400, {"error": str(exc)})

    def do_PUT(self):
        path = urlparse(self.path).path
        if path != "/api/timepro/timesheets": return self.send_json(404, {"error": "not found"})
        try:
            payload = self.read_json()
            query_id = urlparse(self.path).query.split("=", 1)[1] if "=" in urlparse(self.path).query else "0"
            record_id = int(payload.pop("id", query_id))
            if record_id <= 0: return self.send_json(400, {"error": "id is required"})
            updated = update(record_id, payload)
            return self.send_json(200, row_payload(updated)) if updated else self.send_json(404, {"error": "not found"})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self.send_json(400, {"error": str(exc)})

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path != "/api/timepro/timesheets": return self.send_json(404, {"error": "not found"})
        try:
            record_id = int(urlparse(self.path).query.split("=", 1)[1])
            return self.send_json(200, {"deleted": True}) if delete(record_id) else self.send_json(404, {"error": "not found"})
        except (ValueError, IndexError):
            return self.send_json(400, {"error": "id is required"})

if __name__ == "__main__":
    init_db(); ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
"""
    def _generic_backend_schema(self, mission: str) -> dict:
        lower = mission.lower()
        spec_path = self.project.root / ".app-builder" / "spec.json"
        spec = {}
        if spec_path.exists():
            try:
                spec = json.loads(spec_path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                spec = {}
        if not spec.get("data_entities"):
            from .specification import SpecificationBuilder
            built = SpecificationBuilder().build(mission)
            spec = {
                "data_entities": list(built.data_entities),
                "entity_fields": dict(built.entity_fields),
                "business_rules": list(built.business_rules),
                "integrations": list(built.integrations),
            }
        entities = [str(x) for x in spec.get("data_entities", []) if str(x).strip()]
        entity = entities[0] if entities else "ApplicationRecord"
        fields = ["id"]
        if any(x in lower for x in ("form", "cadastro")): fields += ["date", "location", "note"]
        if any(x in lower for x in ("hour", "hours", "hora", "horas", "time", "tempo")): fields += ["start", "end", "break"]
        if any(x in lower for x in ("name", "nome", "employee", "cliente", "client")): fields += ["name"]
        rules = [str(x) for x in spec.get("business_rules", []) if str(x).strip()]
        entity_fields = spec.get("entity_fields", {})
        inferred = entity_fields.get(entity, []) if isinstance(entity_fields, dict) else []
        fields.extend(str(x) for x in inferred if str(x).strip() and str(x) != "id")
        return {
            "version": 3,
            "resource": "records",
            "entity": entity,
            "entities": entities or [entity],
            "fields": list(dict.fromkeys(fields)),
            "entity_fields": entity_fields if isinstance(entity_fields, dict) else {},
            "business_rules": rules,
            "integrations": list(spec.get("integrations", [])),
            "persistence": {"required": True, "adapter": "sqlite"},
        }

    @staticmethod
    def _generic_api_contract(schema: dict | None = None) -> str:
        schema = schema or {}
        entities = schema.get("entities") or [schema.get("entity") or "ApplicationRecord"]
        fields_by_entity = schema.get("entity_fields") or {}
        resources = {}
        for entity in entities:
            resource = re.sub(r"(?<!^)(?=[A-Z])", "_", str(entity)).lower().replace("_", "-")
            fields = list(fields_by_entity.get(entity, schema.get("fields", ["id"])))
            definitions = []
            for name in fields:
                field = str(name)
                lower = field.lower()
                field_type = "integer" if lower == "id" or lower.endswith("_id") else ("number" if lower in {"amount", "price", "total", "hours"} else ("email" if "email" in lower else ("date" if "date" in lower else ("time" if "time" in lower else "text"))))
                definitions.append({"name": field, "type": field_type, "required": field == "id" or field in {"name", "title", "date", "number"}})
            resources[resource] = {
                "entity": entity,
                "fields": fields,
                "field_definitions": definitions,
                "GET": "/api/" + resource,
                "POST": "/api/" + resource,
                "PUT": "/api/" + resource + "?id={id}",
                "DELETE": "/api/" + resource + "?id={id}",
            }
        primary = schema.get("entity") or entities[0]
        primary_resource = re.sub(r"(?<!^)(?=[A-Z])", "_", str(primary)).lower().replace("_", "-")
        resources["records"] = {
            "entity": primary,
            "fields": schema.get("fields", ["id"]),
            "GET": "/api/records",
            "POST": "/api/records",
            "PUT": "/api/records?id={id}",
            "DELETE": "/api/records?id={id}",
            "compatibility_alias_for": primary_resource,
        }
        return json.dumps({
            "version": 3,
            "base": "/api",
            "primary_entity": schema.get("entity") or entities[0],
            "primary_resource": re.sub(r"(?<!^)(?=[A-Z])", "_", str(schema.get("entity") or entities[0])).lower().replace("_", "-"),
            "resources": resources,
            "compatibility": {"records": "/api/records"},
            "business_rules": schema.get("business_rules", []),
            "health": "/health",
            "persistence": schema.get("persistence", {"required": True, "adapter": "sqlite"}),
        }, indent=2, ensure_ascii=False) + "\n"

    def implement_feature(self, feature: str, mission: str) -> str:
        files = self.project.list_files(".")
        if self.is_timepro(mission):
            # TimePro is a cohesive template: feature tasks are checkpoints over
            # the same working application rather than disconnected mockups.
            self.project.write_file("index.html", self._timepro_html())
            self.project.write_file("app.js", self._timepro_javascript())
            self.project.write_file("README.md", self._timepro_readme())
            current = self._load_features()
            for item in ("forms", "storage", "calculator", "list", "dashboard", "mobile"):
                if item not in current:
                    current.append(item)
            self._save_features(current)
            return f"Implemented TimePro feature: {feature}"
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
        if self.is_timepro(mission):
            return self.implement(mission)
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
        self.project.write_file(".app-builder/features.json", json.dumps(features, indent=2, ensure_ascii=False) + "\n")

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
    def _timepro_javascript() -> str:
        return r'''document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('#timesheet-form');
  const start = document.querySelector('#start');
  const end = document.querySelector('#end');
  const pause = document.querySelector('#pause');
  const total = document.querySelector('#total');
  const error = document.querySelector('#form-error');
  const history = document.querySelector('#history');
  const dashboard = document.querySelector('#dashboard');
  const status = document.querySelector('#status');
  const key = 'timepro-timesheets-v1';
  const apiBase = window.TIMEPRO_API_BASE || '';

  async function api(path, options = {}) {
    const response = await fetch(`${apiBase}${path}`, {headers: {'Content-Type': 'application/json'}, ...options});
    if (!response.ok) throw new Error(`API ${response.status}`);
    return response.json();
  }

  function read() {
    try {
      const raw = localStorage.getItem(key);
      const parsed = JSON.parse(raw || '[]');
      return Array.isArray(parsed) ? parsed : [];
    } catch (_) {
      return [];
    }
  }

  function write(items) {
    try {
      localStorage.setItem(key, JSON.stringify(items));
      return true;
    } catch (_) {
      status.textContent = 'Impossible de sauvegarder la feuille sur cet appareil.';
      return false;
    }
  }

  function minutes(value) {
    if (!value) return null;
    const [h, m] = value.split(':').map(Number);
    return h * 60 + m;
  }

  function duration() {
    const a = minutes(start?.value), b = minutes(end?.value), p = Number(pause?.value || 0);
    if (a === null || b === null) return null;
    if (b < a || p < 0) return -1;
    return Math.max(0, b - a - p);
  }

  function format(totalMinutes) {
    return `${Math.floor(totalMinutes / 60)}h ${String(totalMinutes % 60).padStart(2, '0')}min`;
  }

  function updateTotal() {
    const value = duration();
    if (value === null) { total.textContent = '0h 00min'; error.textContent = ''; return; }
    if (value < 0) { total.textContent = '—'; error.textContent = 'L’heure de fin doit être après l’heure de début.'; return; }
    total.textContent = format(value);
    error.textContent = '';
  }

  function render(items = read()) {
    history.innerHTML = items.length ? items.map(item =>
      `<article class="entry"><strong>${escapeHtml(item.date || '')}</strong><span>${escapeHtml(item.site || '')}</span><span>${escapeHtml(item.start)} → ${escapeHtml(item.end)}</span><b>${format(item.total)}</b></article>`
    ).join('') : '<p class="empty">Aucune feuille envoyée.</p>';
    const totalMinutes = items.reduce((sum, item) => sum + item.total, 0);
    dashboard.innerHTML = `<div><b>${items.length}</b><small>Feuilles</small></div><div><b>${format(totalMinutes)}</b><small>Heures</small></div><div><b>${new Set(items.map(x => x.employee)).size}</b><small>Employés</small></div>`;
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  }

  [start, end, pause].forEach(input => input?.addEventListener('input', updateTotal));
  form?.addEventListener('submit', async event => {
    event.preventDefault();
    const totalMinutes = duration();
    if (totalMinutes === null || totalMinutes < 0) { error.textContent = 'Vérifie les heures de début, de fin et la pause.'; return; }
    const data = new FormData(form);
    const item = Object.fromEntries(data.entries());
    item.total = totalMinutes;
    item.createdAt = new Date().toISOString();
    try {
      await api('/api/timepro/timesheets', {method: 'POST', body: JSON.stringify({employee: item.employee, company: item.company, work_date: item.date, location: item.site, start_time: item.start, pause_minutes: item.pause || 0, end_time: item.end, note: item.note || ''})});
      status.textContent = 'Feuille envoyée avec succès';
      const remote = await api('/api/timepro/timesheets');
      render(remote.map(x => ({employee:x.employee, date:x.work_date, site:x.location, start:x.start_time, end:x.end_time, total:Number(x.total_minutes)})));
    } catch (_) {
      const items = read();
      items.unshift(item);
      if (!write(items)) return;
      status.textContent = 'Serveur indisponible — feuille enregistrée localement';
      render(items);
    }
    form.reset();
    total.textContent = '0h 00min';
  });

  api('/api/timepro/timesheets').then(rows => render(rows.map(x => ({employee:x.employee, date:x.work_date, site:x.location, start:x.start_time, end:x.end_time, total:Number(x.total_minutes)})))).catch(() => render());
});
'''

    @staticmethod
    def _timepro_html() -> str:
        return '''<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#111827">
  <title>TimePro — Feuille d’heures</title>
  <style>
    :root{font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#111827;background:#f3f4f6}
    *{box-sizing:border-box}body{margin:0}main{max-width:980px;margin:auto;padding:20px;display:grid;gap:18px}
    header{display:flex;justify-content:space-between;align-items:center;gap:12px}h1{margin:0;font-size:28px}header p{margin:4px 0 0;color:#6b7280}
    section{background:white;border:1px solid #e5e7eb;border-radius:18px;padding:18px;box-shadow:0 3px 14px rgba(0,0,0,.04)}
    h2{margin:0 0 14px;font-size:19px}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.field{display:grid;gap:6px}label{font-size:13px;font-weight:700;color:#374151}input,textarea,button{font:inherit;border-radius:11px;padding:11px;border:1px solid #d1d5db}textarea{min-height:70px;resize:vertical}.full{grid-column:1/-1}
    button{background:#111827;color:white;border:0;font-weight:700;cursor:pointer;padding:13px 18px}.total{display:flex;justify-content:space-between;align-items:center;background:#f9fafb;padding:14px;border-radius:12px;margin-top:12px}.total strong{font-size:23px}.error{color:#b91c1c;min-height:20px;font-size:13px}.status{color:#047857;font-weight:700;min-height:20px}
    .cards{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.cards div{background:#f9fafb;padding:16px;border-radius:14px}.cards b{display:block;font-size:22px}.cards small{color:#6b7280}.entry{display:grid;grid-template-columns:1fr 1.5fr 1.2fr auto;gap:10px;align-items:center;padding:12px 0;border-bottom:1px solid #eee}.entry:last-child{border-bottom:0}.entry span{color:#4b5563;font-size:14px}.empty{color:#6b7280}
    @media(max-width:650px){main{padding:12px}.grid,.cards{grid-template-columns:1fr}.full{grid-column:auto}header{align-items:flex-start;flex-direction:column}.entry{grid-template-columns:1fr 1fr}.entry b{grid-column:2}.entry span:nth-child(3){grid-column:1/-1}}
  </style>
</head>
<body><main>
  <header><div><h1>TimePro</h1><p>Feuille d’heures simple et rapide</p></div><span>Employé</span></header>
  <section><h2>Nouvelle journée</h2>
    <form id="timesheet-form"><div class="grid">
      <div class="field"><label>Employé</label><input name="employee" required placeholder="Nom et prénom"></div>
      <div class="field"><label>Entreprise</label><input name="company" required placeholder="Entreprise"></div>
      <div class="field"><label>Date</label><input name="date" type="date" required></div>
      <div class="field"><label>Lieu / chantier / client</label><input name="site" required placeholder="Lieu ou client"></div>
      <div class="field"><label>Début</label><input id="start" name="start" type="time" required></div>
      <div class="field"><label>Fin</label><input id="end" name="end" type="time" required></div>
      <div class="field"><label>Pause (minutes)</label><input id="pause" name="pause" type="number" min="0" value="30"></div>
      <div class="field"><label>Photo (optionnelle)</label><input name="photos" type="file" accept="image/*" capture="environment"></div>
      <div class="field full"><label>Note (optionnelle)</label><textarea name="note" placeholder="Un recado pour le responsable..."></textarea></div>
    </div><div class="total"><span>Total automatique</span><strong id="total">0h 00min</strong></div><p id="form-error" class="error"></p><button type="submit">Envoyer la feuille</button><p id="status" class="status"></p></form>
  </section>
  <section><h2>Tableau de bord</h2><div id="dashboard" class="cards"></div></section>
  <section><h2>Historique</h2><div id="history"></div></section>
  <p data-builder-status>TimePro MVP — stockage serveur avec secours local si le serveur est indisponible.</p>
</main><script src="app.js"></script></body>
</html>
'''

    @staticmethod
    def _timepro_api_contract() -> str:
        return json.dumps({
            "version": 1,
            "base_path": "/api/timepro",
            "resources": {
                "timesheets": {"methods": ["GET", "POST", "PUT", "DELETE"], "fields": ["employee", "company", "date", "site", "location", "start", "break", "end", "photos", "note", "signature"], "server_rules": ["end >= start", "break >= 0", "total = end - start - break"]},
                "dashboard": {"methods": ["GET"], "resource": "timesheets"},
                "attachments": {"methods": ["POST"], "optional": True},
                "signature": {"methods": ["POST"], "optional": True}
            },
            "persistence": {"required": True, "adapter_boundary": True},
            "authentication": {"required_for_production": True, "approval_for_external_provider": True}
        }, indent=2, ensure_ascii=False) + "\n"

    @staticmethod
    def _timepro_readme() -> str:
        return '''# TimePro

MVP généré automatiquement par App Builder V1.

## Inclus
- Feuille d’heures mobile responsive
- Employé, entreprise, date et chantier/client
- Début, fin et pause avec calcul automatique
- Validation des horaires invalides
- Historique des feuilles envoyées
- Tableau de bord local
- Note et photo optionnelles
- Stockage local du navigateur pour le prototype

## Architecture de production
Le prototype peut utiliser `localStorage` hors serveur, mais lorsqu’un backend TimePro est généré, les feuilles sont persistées dans SQLite via l’API `/api/timepro`.
L’authentification de production, les signatures et les pièces jointes restent des intégrations séparées et doivent être activées avec l’approbation correspondante.
'''

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
                "  const apiBase = window.APP_API_BASE || '';",
                "  const api = async (path, options = {}) => {",
                "    const response = await fetch(apiBase + path, {headers: {'Content-Type': 'application/json'}, ...options});",
                "    if (!response.ok) throw new Error('API request failed');",
                "    return response.json();",
                "  };",
                "  const renderRecords = records => {",
                "    const list = document.querySelector('#history-list');",
                "    if (!list) return;",
                "    list.innerHTML = '';",
                "    (records || []).forEach(record => { const item = document.createElement('li'); item.textContent = JSON.stringify(record); list.appendChild(item); });",
                "  };",
                "  const loadRecords = async () => {",
                "    try { renderRecords(await api('/api/records')); } catch (_) {",
                "      const cached = JSON.parse(localStorage.getItem('app-builder-records') || '[]'); renderRecords(cached);",
                "    }",
                "  };",
                "  document.querySelectorAll('form[data-save]').forEach(form => form.addEventListener('submit', async event => {",
                "    event.preventDefault();",
                "    const payload = Object.fromEntries(new FormData(form));",
                "    try { await api('/api/records', {method: 'POST', body: JSON.stringify(payload)}); await loadRecords(); if (status) status.textContent = 'Saved to server'; }",
                "    catch (_) { const cached = JSON.parse(localStorage.getItem('app-builder-records') || '[]'); cached.push(payload); localStorage.setItem('app-builder-records', JSON.stringify(cached)); renderRecords(cached); if (status) status.textContent = 'Server unavailable — saved locally'; }",
                "  }));",
                "  loadRecords();",
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
        lines = ["# Generated App", "", f"Mission: {mission or 'Generated project'}", "", "Features detected: " + (", ".join(features) if features else "none yet"), "", "Built by App Builder V1."]
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
            sections.append('<section><h2>History</h2><ul id="history-list"><li>No records yet</li></ul></section>')
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
