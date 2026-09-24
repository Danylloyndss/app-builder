"""Durable deployment attempt history without secrets."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json


class DeploymentHistory:
    def __init__(self, workspace: str | Path):
        self.path = Path(workspace) / ".app-builder" / "deployment_history.json"

    def list(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, list) else []
        except (OSError, ValueError):
            return []

    def append(self, status: str, provider: str, release_hash: str | None, detail: str = "") -> dict:
        if not status or not provider:
            raise ValueError("status and provider are required")
        item = {
            "id": f"{int(datetime.now(timezone.utc).timestamp() * 1000):x}",
            "status": status,
            "provider": provider,
            "release_hash": release_hash,
            "detail": detail[:1000],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        items = self.list()
        items.append(item)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(items[-100:], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return item
