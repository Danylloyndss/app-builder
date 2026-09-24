"""Durable release state machine with guarded transitions."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json


class ReleaseState:
    STATES = {
        "not_ready",
        "ready",
        "awaiting_approval",
        "deploy_pending",
        "published",
        "failed",
        "rolled_back",
    }

    TRANSITIONS = {
        "not_ready": {"ready", "awaiting_approval", "deploy_pending", "failed"},
        "ready": {"awaiting_approval", "deploy_pending", "failed"},
        "awaiting_approval": {"deploy_pending", "failed", "ready"},
        "deploy_pending": {"published", "failed", "rolled_back"},
        "published": {"rolled_back", "failed"},
        "failed": {"ready", "awaiting_approval", "deploy_pending", "rolled_back"},
        "rolled_back": {"ready", "awaiting_approval", "deploy_pending"},
    }

    def __init__(self, workspace: str | Path):
        self.path = Path(workspace) / ".app-builder" / "release_state.json"

    def read(self) -> dict:
        if not self.path.exists():
            return {"state": "not_ready", "release_hash": None, "updated_at": None, "history": []}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            value.setdefault("history", [])
            return value
        except (OSError, ValueError):
            return {"state": "not_ready", "release_hash": None, "updated_at": None, "history": []}

    def set(self, state: str, release_hash: str | None = None, *, force: bool = False, reason: str = "") -> dict:
        if state not in self.STATES:
            raise ValueError("invalid release state")
        current = self.read()
        previous = current.get("state", "not_ready")
        if not force and state != previous and state not in self.TRANSITIONS.get(previous, set()):
            raise ValueError(f"invalid release transition: {previous} -> {state}")
        now = datetime.now(timezone.utc).isoformat()
        value = {
            "state": state,
            "release_hash": release_hash if release_hash is not None else current.get("release_hash"),
            "updated_at": now,
            "history": list(current.get("history") or [])[-49:],
        }
        if state != previous or reason:
            value["history"].append({
                "from": previous,
                "to": state,
                "reason": reason[:500],
                "updated_at": now,
            })
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return value

    def mark_ready(self, release_hash: str, reason: str = "new verified release selected") -> dict:
        """Select a newly verified release without weakening normal transitions."""
        current = self.read()
        if current.get("state") in {"published", "failed", "rolled_back", "awaiting_approval"}:
            return self.set("ready", release_hash, force=True, reason=reason)
        return self.set("ready", release_hash, reason=reason)

    def can_transition(self, state: str) -> bool:
        current = self.read().get("state", "not_ready")
        return state == current or state in self.TRANSITIONS.get(current, set())
