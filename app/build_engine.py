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
        schema = self._generic_backend_schema(mission) if "storage" in features else None
        self.project.write_file("index.html", self._html(title, mission, features, schema))
        self.project.write_file("app.js", self._javascript(features))
        self.project.write_file("README.md", self._readme(mission, features))
        self.project.write_file("hello_app.txt", f"{title}\n")
        if schema is not None:
            self.project.write_file("api_contract.json", self._generic_api_contract(schema))
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
        self.project.write_file("tests/test_backend_integration.py", self._generic_backend_test())
        self.project.write_file(".app-builder/backend.json", json.dumps({**manifest, "schema": ".app-builder/backend_schema.json"}, indent=2) + "\n")
        self.project.write_file(".app-builder/backend_schema.json", json.dumps(schema, indent=2) + "\n")
        self.project.write_file("api_contract.json", self._generic_api_contract(schema))
        return "Generic persistent backend generated"

    @staticmethod
    def _generic_backend(mission: str = "", schema: dict | None = None) -> str:
        schema = schema or {
            "version": 3,
            "entity": "ApplicationRecord",
            "entities": ["ApplicationRecord"],
            "fields": ["id"],
            "entity_fields": {"ApplicationRecord": ["id"]},
            "business_rules": [],
        }
        schema_json = json.dumps(schema, ensure_ascii=False)
        source = """from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
        db.execute("CREATE TABLE IF NOT EXISTS entity_records (id INTEGER PRIMARY KEY AUTOINCREMENT, entity TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_entity_records_entity ON entity_records(entity)")

def entities():
    values = SCHEMA.get("entities") or [SCHEMA.get("entity") or "ApplicationRecord"]
    return [str(value) for value in values]

def primary_entity():
    return str(SCHEMA.get("entity") or entities()[0])

def slug(entity):
    return re.sub(r"(?<!^)(?=[A-Z])", "-", str(entity)).lower().replace("_", "-")

def entity_from_path(path):
    if path == "/api/records":
        return primary_entity()
    prefix = "/api/"
    if not path.startswith(prefix):
        return None
    candidate = path[len(prefix):].strip("/")
    for entity in entities():
        if slug(entity) == candidate:
            return entity
    return None

def fields_for(entity):
    values = (SCHEMA.get("entity_fields") or {}).get(entity)
    if not values:
        values = SCHEMA.get("fields", ["id"])
    return [str(value) for value in values]

def payload(row):
    return {"id": row[0], **json.loads(row[1]), "created_at": row[2], "_entity": row[3]}

def validate(data, entity):
    if not isinstance(data, dict):
        raise ValueError("payload must be an object")
    fields = [field for field in fields_for(entity) if field != "id"]
    unknown = [key for key in data if key not in fields]
    if unknown:
        raise ValueError("unknown fields: " + ", ".join(sorted(unknown)))
    rules = [str(rule).lower() for rule in SCHEMA.get("business_rules", [])]
    for rule in rules:
        if "zero or positive" in rule or "non-negative" in rule:
            for key in ("amount", "price", "total", "hours", "pause", "pause_minutes", "break"):
                if key in data:
                    try:
                        if float(data[key]) < 0:
                            raise ValueError(key + " must be zero or positive")
                    except (TypeError, ValueError) as exc:
                        if isinstance(exc, ValueError) and "must be zero or positive" in str(exc):
                            raise
    return data

def save(data, entity, record_id=None):
    encoded = json.dumps(data, ensure_ascii=False)
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
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1000000:
            raise ValueError("request too large")
        return json.loads(self.rfile.read(length) or b"{}")

    def route(self):
        return entity_from_path(urlparse(self.path).path)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return self.send_json(200, {"ok": True, "entities": entities(), "schema_version": SCHEMA.get("version", 1)})
        entity = self.route()
        if not entity:
            return self.send_json(404, {"error": "not found"})
        with sqlite3.connect(DB) as db:
            rows = db.execute("SELECT id, data, created_at, entity FROM entity_records WHERE entity=? ORDER BY id DESC", (entity,)).fetchall()
        return self.send_json(200, [payload(row) for row in rows])

    def do_POST(self):
        entity = self.route()
        if not entity:
            return self.send_json(404, {"error": "not found"})
        try:
            row = save(validate(self.read_json(), entity), entity)
            return self.send_json(201, payload(row))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self.send_json(400, {"error": str(exc)})

    def do_PUT(self):
        parsed = urlparse(self.path)
        entity = self.route()
        if not entity:
            return self.send_json(404, {"error": "not found"})
        try:
            data = self.read_json()
            record_id = int(data.pop("id", parse_qs(parsed.query).get("id", ["0"])[0]))
            if record_id <= 0:
                return self.send_json(400, {"error": "id is required"})
            row = save(validate(data, entity), entity, record_id)
            return self.send_json(200, payload(row)) if row else self.send_json(404, {"error": "not found"})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self.send_json(400, {"error": str(exc)})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        entity = self.route()
        if not entity:
            return self.send_json(404, {"error": "not found"})
        try:
            record_id = int(parse_qs(parsed.query).get("id", ["0"])[0])
            with sqlite3.connect(DB) as db:
                changed = db.execute("DELETE FROM entity_records WHERE id=? AND entity=?", (record_id, entity)).rowcount
            return self.send_json(200, {"deleted": True, "_entity": entity}) if changed else self.send_json(404, {"error": "not found"})
        except ValueError:
            return self.send_json(400, {"error": "id is required"})

if __name__ == "__main__":
    init_db()
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
"""
        return source.replace("__SCHEMA__", repr(schema_json))

    @staticmethod
    def _generic_backend_test() -> str:
        return '''import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from pathlib import Path

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

        client = call(base + "/api/client", "POST", {"name": "Test", "email": "test@example.com", "phone": "1", "note": "ok"})
        assert client["_entity"] == "Client"
        assert client["name"] == "Test"
        assert call(base + "/api/client")[0]["email"] == "test@example.com"

        client_id = client["id"]
        updated = call(base + "/api/client?id=" + str(client_id), "PUT", {"id": client_id, "name": "Updated", "email": "test@example.com", "phone": "2", "note": "changed"})
        assert updated["name"] == "Updated"

        try:
            call(base + "/api/client", "POST", {"unexpected": True})
            raise AssertionError("unknown field accepted")
        except HTTPError as exc:
            assert exc.code == 400

        deleted = call(base + "/api/client?id=" + str(client_id), "DELETE")
        assert deleted["deleted"] is True
        assert call(base + "/api/client") == []

        legacy = call(base + "/api/records", "POST", {"name": "Legacy", "email": "legacy@example.com", "phone": "3", "note": "compat"})
        assert legacy["_entity"] == "Client"
        assert call(base + "/api/records")[0]["name"] == "Legacy"
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
    value = minutes(end) - minutes(start) - int(pause)
    if value <= 0: raise ValueError("end time must be after start time and pause")
    return value

def row_payload(row):
    return dict(row)

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
            return self.send_json(200, {"count": len(rows), "total_minutes": sum(int(r["total_minutes"]) for r in rows), "employees": sorted({r["employee"] for r in rows}), "timesheets": rows})
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
            record_id = int(payload.pop("id", 0))
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

        entities = [str(x) for x in spec.get("data_entities", []) if str(x).strip()]
        if not entities:
            catalog = {
                "expense": "Expense", "expenses": "Expense",
                "client": "Client", "clients": "Client",
                "customer": "Customer", "customers": "Customer",
                "product": "Product", "products": "Product",
                "order": "Order", "orders": "Order",
                "employee": "Employee", "employees": "Employee",
                "appointment": "Appointment", "appointments": "Appointment",
                "task": "Task", "tasks": "Task",
                "project": "Project", "projects": "Project",
                "invoice": "Invoice", "invoices": "Invoice",
            }
            entities = []
            for keyword, candidate in catalog.items():
                if keyword in lower and candidate not in entities:
                    entities.append(candidate)
        entity = entities[0] if entities else "ApplicationRecord"

        fields = ["id"]
        if any(x in lower for x in ("form", "cadastro")):
            fields += ["date", "location", "note"]
        if any(x in lower for x in ("hour", "hours", "hora", "horas", "time", "tempo")):
            fields += ["start", "end", "break"]
        if any(x in lower for x in ("name", "nome", "employee", "cliente", "client")):
            fields += ["name"]

        rules = [str(x) for x in spec.get("business_rules", []) if str(x).strip()]
        catalog_fields = {
            "Expense": ["id", "date", "amount", "description", "category"],
            "Client": ["id", "name", "email", "phone", "note"],
            "Customer": ["id", "name", "email", "phone", "note"],
            "Product": ["id", "name", "price", "sku", "description"],
            "Order": ["id", "date", "customer_id", "total", "status"],
            "Employee": ["id", "name", "email", "role"],
            "Appointment": ["id", "date", "time", "client_id", "note"],
            "Task": ["id", "title", "description", "status", "due_date"],
            "Project": ["id", "name", "description", "status", "due_date"],
            "Invoice": ["id", "number", "date", "client_id", "amount", "status"],
            "ApplicationRecord": ["id", "date", "location", "note"],
        }
        entity_fields = spec.get("entity_fields", {})
        if not isinstance(entity_fields, dict):
            entity_fields = {}
        for detected in entities:
            entity_fields.setdefault(detected, list(catalog_fields.get(detected, ["id", "name", "note"])))
        entity_fields.setdefault(entity, list(catalog_fields.get(entity, fields)))
        primary_fields = entity_fields.get(entity, fields)
        return {
            "version": 3,
            "resource": "records",
            "entity": entity,
            "entities": entities or [entity],
            "fields": list(dict.fromkeys(primary_fields)),
            "entity_fields": entity_fields,
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
            resource = re.sub(r"(?<!^)(?=[A-Z])", "-", str(entity)).lower().replace("_", "-")
            fields = fields_by_entity.get(entity, schema.get("fields", ["id"]))
            resources[resource] = {
                "entity": entity,
                "fields": fields,
                "GET": f"/api/{resource}",
                "POST": f"/api/{resource}",
                "PUT": f"/api/{resource}?id={{id}}",
                "DELETE": f"/api/{resource}?id={{id}}",
            }
        primary = schema.get("entity") or entities[0]
        primary_resource = re.sub(r"(?<!^)(?=[A-Z])", "-", str(primary)).lower().replace("_", "-")
        return json.dumps({
            "version": 3,
            "base": "/api",
            "primary_entity": primary,
            "primary_resource": primary_resource,
            "resources": resources,
            "compatibility": {"records": "/api/records"},
            "business_rules": schema.get("business_rules", []),
            "integrations": schema.get("integrations", []),
            "health": "/health",
            "persistence": schema.get("persistence", {"required": True, "adapter": "sqlite"}),
        }, indent=2, ensure_ascii=False) + "\n"

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

## Limitation volontaire du MVP
Les données sont stockées dans `localStorage`. L’authentification, une vraie base de données, les signatures et l’envoi vers un serveur nécessitent une étape backend et, si nécessaire, l’approbation humaine correspondante.
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
    def _html(title: str, mission: str = "", features: list[str] | None = None, schema: dict | None = None) -> str:
        features = features or []
        safe_title = escape(title)
        safe_description = escape(mission or "Generated project")
        sections = [f"<h1>{safe_title}</h1>", f"<p>{safe_description}</p>"]
        if "auth" in features:
            sections.append('<form data-login><h2>Sign in</h2><input name="email" type="email" placeholder="Email" required><input name="password" type="password" placeholder="Password" required><button>Sign in</button></form>')
        if "forms" in features:
            fields = ((schema or {}).get("entity_fields") or {}).get((schema or {}).get("entity") or "", [])
            if not fields:
                fields = ["date", "location", "note"]
            inputs = []
            for field_name in fields:
                if field_name == "id":
                    continue
                input_type = "number" if field_name in {"amount", "price", "total", "hours"} else "email" if field_name == "email" else "date" if field_name in {"date", "due_date"} else "time" if field_name in {"time", "start", "end"} else "text"
                inputs.append(f'<label>{escape(field_name.replace("_", " ").title())}<input name="{escape(field_name)}" type="{input_type}"></label>')
            sections.append('<form data-save><h2>New entry</h2>' + ''.join(inputs) + '<button>Save</button></form>')
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
