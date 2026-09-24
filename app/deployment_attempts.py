"""Durable, bounded deployment attempt tracking."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
import secrets


class DeploymentAttempts:
    def __init__(self, workspace: str | Path, max_attempts: int = 3):
        self.path = Path(workspace) / ".app-builder" / "deployment_attempts.json"
        self.max_attempts = max(1, int(max_attempts))

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, list) else []
        except (OSError, ValueError):
            return []

    def _save(self, items: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(items[-100:], indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def begin(self, provider: str, release_hash: str) -> dict:
        items = self._load()
        existing = [x for x in items if x.get("provider") == provider and x.get("release_hash") == release_hash]
        if any(x.get("status") in {"queued", "running"} for x in existing):
            return {"allowed": False, "reason": "deployment already in progress", "attempt_id": existing[-1]["attempt_id"]}
        count = len(existing)
        if count >= self.max_attempts:
            return {"allowed": False, "reason": "deployment retry limit reached", "attempt_id": existing[-1]["attempt_id"] if existing else None}
        attempt = {
            "attempt_id": secrets.token_hex(8),
            "provider": provider,
            "release_hash": release_hash,
            "attempt": count + 1,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        items.append(attempt)
        self._save(items)
        return {"allowed": True, **attempt}

    def find_active(self, provider: str, release_hash: str) -> dict | None:
        items = self._load()
        for item in reversed(items):
            if item.get("provider") == provider and item.get("release_hash") == release_hash and item.get("status") in {"queued", "running", "waiting_external_action"}:
                return item
        return None

    def finish(self, attempt_id: str, status: str, **details) -> dict | None:
        items = self._load()
        for item in reversed(items):
            if item.get("attempt_id") == attempt_id:
                item["status"] = status
                item["finished_at"] = datetime.now(timezone.utc).isoformat()
                item.update({k: v for k, v in details.items() if v is not None})
                self._save(items)
                return item
        return None
