"""HTTP control plane for App Builder V1 and TimePro."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import io
import json
import os
from pathlib import Path
import threading
import zipfile
from urllib.parse import parse_qs, urlparse

from .approvals import ApprovalStore
from .manager import Manager
from .timepro_api import TimeProService, TimeProValidationError

WORKSPACE = "workspace"
ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "static" / "index.html"
TIMEPRO_INDEX = ROOT / "static" / "timepro.html"
APPROVALS = ApprovalStore(f"{WORKSPACE}/approvals.json")
RUN_LOCK = threading.Lock()
TIMEPRO = TimeProService()


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, path: Path) -> None:
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        configured = os.environ.get("APP_BUILDER_API_KEY", "").strip()
        if not configured:
            return True
        supplied = self.headers.get("X-App-Builder-Key", "")
        return bool(supplied) and hmac.compare_digest(supplied, configured)

    def _status_payload(self, memory) -> dict:
        return {"mission": memory.mission, "status": memory.status, "current_task": memory.current_task, "plan": memory.plan, "completed": memory.completed, "errors": memory.errors, "task_statuses": memory.task_statuses, "history": memory.history[-20:], "approvals": APPROVALS.list_pending()}

    def _artifact_files(self) -> list[str]:
        root = Path(WORKSPACE)
        if not root.exists(): return []
        return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and ".git" not in path.parts)

    def _artifact_zip(self) -> bytes:
        root = Path(WORKSPACE); buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for relative in self._artifact_files(): archive.write(root / relative, arcname=relative)
        return buffer.getvalue()

    def _timepro_id(self) -> int | None:
        try:
            value = parse_qs(urlparse(self.path).query).get("id", [None])[0]
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("request too large")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:
        if self.path == "/health": self._send(200, {"status": "ok", "service": "app-builder-agent"}); return
        if self.path in ("/", "/index.html"):
            self._send_html(INDEX); return
        if self.path in ("/timepro", "/timepro/"):
            self._send_html(TIMEPRO_INDEX); return
        if self.path == "/status": self._send(200, self._status_payload(Manager(workspace=WORKSPACE).memory)); return
        if self.path == "/approvals": self._send(200, {"approvals": APPROVALS.list_pending()}); return
        if self.path == "/artifacts": self._send(200, {"files": self._artifact_files()}); return
        if self.path == "/artifacts.zip":
            body = self._artifact_zip(); self.send_response(200); self.send_header("Content-Type", "application/zip"); self.send_header("Content-Disposition", "attachment; filename=app-builder-artifacts.zip"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/timepro/history"):
            employee = parse_qs(urlparse(self.path).query).get("employee", [None])[0]
            self._send(200, {"timesheets": TIMEPRO.history(employee)}); return
        if self.path == "/api/timepro/dashboard": self._send(200, TIMEPRO.dashboard()); return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        try:
            if not self._authorized(): self._send(401, {"error": "authentication required"}); return
            data = self._read_json()
            if self.path == "/api/timepro/timesheets":
                record = TIMEPRO.create_timesheet(data)
                self._send(201, {"timesheet": record}); return
            if self.path in ("/run", "/resume"):
                mission = str(data.get("mission", "")).strip()
                if not mission or len(mission) > 20_000: self._send(400, {"error": "mission is required and must be <= 20000 characters"}); return
                if not RUN_LOCK.acquire(blocking=False): self._send(409, {"error": "another build is already running"}); return
                try: memory = Manager(workspace=WORKSPACE).run(mission, resume=self.path == "/resume")
                finally: RUN_LOCK.release()
                self._send(200, self._status_payload(memory)); return
            if self.path == "/approval":
                action = str(data.get("action", "")).strip(); reason = str(data.get("reason", "")).strip()
                if not action or not reason: self._send(400, {"error": "action and reason are required"}); return
                request = APPROVALS.create(action, reason); self._send(201, {"approval": request.__dict__}); return
            if self.path == "/approval/decision":
                result = APPROVALS.decide(str(data.get("id", "")), bool(data.get("approved", False)))
                if result is None: self._send(404, {"error": "approval not found"}); return
                self._send(200, {"approval": result}); return
            self._send(404, {"error": "not found"})
        except json.JSONDecodeError: self._send(400, {"error": "invalid JSON"})
        except TimeProValidationError as exc: self._send(422, {"error": str(exc)})
        except ValueError as exc: self._send(413 if str(exc) == "request too large" else 400, {"error": str(exc)})
        except (TypeError, KeyError): self._send(400, {"error": "invalid request"})
        except Exception as exc: self._send(500, {"error": str(exc)})

    def do_PUT(self) -> None:
        if not self._authorized(): self._send(401, {"error": "authentication required"}); return
        if not self.path.startswith("/api/timepro/timesheets"):
            self._send(404, {"error": "not found"}); return
        try:
            record_id = self._timepro_id()
            if record_id is None: self._send(400, {"error": "timesheet id is required"}); return
            record = TIMEPRO.update_timesheet(record_id, self._read_json())
            if not record: self._send(404, {"error": "timesheet not found"}); return
            self._send(200, {"timesheet": record})
        except json.JSONDecodeError: self._send(400, {"error": "invalid JSON"})
        except TimeProValidationError as exc: self._send(422, {"error": str(exc)})
        except ValueError as exc: self._send(413 if str(exc) == "request too large" else 400, {"error": str(exc)})

    def do_DELETE(self) -> None:
        if not self._authorized(): self._send(401, {"error": "authentication required"}); return
        if not self.path.startswith("/api/timepro/timesheets"):
            self._send(404, {"error": "not found"}); return
        try:
            record_id = self._timepro_id()
            if record_id is None: self._send(400, {"error": "timesheet id is required"}); return
            if not TIMEPRO.delete_timesheet(record_id): self._send(404, {"error": "timesheet not found"}); return
            self._send(200, {"deleted": True, "id": record_id})
        except TimeProValidationError as exc: self._send(422, {"error": str(exc)})

    def log_message(self, format: str, *args) -> None: return


def serve() -> None:
    port = int(os.environ.get("PORT", "8080")); server = ThreadingHTTPServer(("0.0.0.0", port), Handler); print(f"App Builder V1 listening on {port}"); server.serve_forever()


if __name__ == "__main__": serve()
