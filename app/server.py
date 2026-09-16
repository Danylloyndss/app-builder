"""HTTP control plane for the App Builder V1."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json

from .manager import Manager

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "static" / "index.html"


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
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/run":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length) or b"{}")
            mission = str(data.get("mission", "")).strip()
            if not mission:
                self._send(400, {"error": "mission is required"})
                return
            memory = Manager().run(mission)
            self._send(200, {
                "mission": memory.mission,
                "plan": memory.plan,
                "completed": memory.completed,
                "errors": memory.errors,
            })
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
