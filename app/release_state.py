"""Durable release state machine."""

from __future__ import annotations

from pathlib import Path
import json


class ReleaseState:
    STATES = {"not_ready", "ready", "awaiting_approval", "deploy_pending", "published"}

    def __init__(self, workspace: str | Path):
        self.path = Path(workspace) / ".app-builder" / "release_state.json"

    def read(self) -> dict:
        if not self.path.exists():
            return {"state": "not_ready", "release_hash": None, "updated_at": None}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"state": "not_ready", "release_hash": None, "updated_at": None}

    def set(self, state: str, release_hash: str | None = None) -> dict:
        if state not in self.STATES:
            raise ValueError("invalid release state")
        from datetime import datetime, timezone
        value = {"state": state, "release_hash": release_hash, "updated_at": datetime.now(timezone.utc).isoformat()}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return value
