"""Human approval gates for autonomous App Builder actions."""

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import uuid


@dataclass
class ApprovalRequest:
    id: str
    action: str
    reason: str
    status: str = "pending"


class ApprovalStore:
    def __init__(self, path: str = "workspace/approvals.json"):
        self.path = Path(path)

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, items: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(items, indent=2), encoding="utf-8")

    def create(self, action: str, reason: str) -> ApprovalRequest:
        request = ApprovalRequest(str(uuid.uuid4()), action, reason)
        items = self._load()
        items.append(asdict(request))
        self._save(items)
        return request

    def list_pending(self) -> list[dict]:
        return [item for item in self._load() if item["status"] == "pending"]

    def get(self, request_id: str) -> dict | None:
        return next((item for item in self._load() if item["id"] == request_id), None)

    def approved_for(self, action: str, request_id: str | None = None) -> dict | None:
        items = self._load()
        if request_id:
            return next((item for item in items if item["id"] == request_id and item["status"] == "approved"), None)
        return next((item for item in items if item["action"] == action and item["status"] == "approved"), None)

    def consume(self, request_id: str) -> dict | None:
        items = self._load()
        for item in items:
            if item["id"] == request_id and item["status"] == "approved":
                item["status"] = "consumed"
                self._save(items)
                return item
        return None

    def decide(self, request_id: str, approved: bool) -> dict | None:
        items = self._load()
        for item in items:
            if item["id"] == request_id:
                if item["status"] != "pending":
                    return item
                item["status"] = "approved" if approved else "rejected"
                self._save(items)
                return item
        return None
