"""HTTP control plane for App Builder V1."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path

from .approvals import ApprovalStore
from .manager import Manager

WORKSPACE = "workspace"
ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "static" / "index.html"
APPROVALS = ApprovalStore(f"{WORKSPACE}/approvals.json")


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send(200, {"status": "ok", "service": "app-builder-agent"})
            return
        if self.path in ("/", "/index.html"):
            body = INDEX.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/status":
            memory = Manager(workspace=WORKSPACE).memory
            self._send(200, {"mission": memory.mission, "status": memory.status,
                "current_task": memory.current_task, "plan": memory.plan,
                "completed": memory.completed, "errors": memory.errors,
                "history": memory.history[-20:], "approvals": APPROVALS.list_pending()})
            return
        if self.path == "/approvals":
            self._send(200, {"approvals": APPROVALS.list_pending()})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length) or b"{}")
            if self.path in ("/run", "/resume"):
                mission = str(data.get("mission", "")).strip()
                if not mission:
                    self._send(400, {"error": "mission is required"})
                    return
                memory = Manager(workspace=WORKSPACE).run(mission, resume=self.path == "/resume")
                self._send(200, {"mission": memory.mission, "status": memory.status,
                    "current_task": memory.current_task, "plan": memory.plan,
                    "completed": memory.completed, "errors": memory.errors})
                return
            if self.path == "/approval":
                action = str(data.get("action", "")).strip()
                reason = str(data.get("reason", "")).strip()
                if not action or not reason:
                    self._send(400, {"error": "action and reason are required"})
                    return
                request = APPROVALS.create(action, reason)
                self._send(201, {"approval": request.__dict__})
                return
            if self.path == "/approval/decision":
                result = APPROVALS.decide(str(data.get("id", "")), bool(data.get("approved", False)))
                if result is None:
                    self._send(404, {"error": "approval not found"})
                    return
                self._send(200, {"approval": result})
                return
            self._send(404, {"error": "not found"})
        except Exception as exc:
            self._send(500, {"error": str(exc)})

    def log_message(self, format: str, *args) -> None:
        return


def serve() -> None:
    import os
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"App Builder V1 listening on {port}")
    server.serve_forever()


if __name__ == "__main__":
    serve()
