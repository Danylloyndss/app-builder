"""Lightweight project checkpoints for safe autonomous changes."""

from pathlib import Path
import shutil
from datetime import datetime, timezone

from .workspace import Workspace


class CheckpointStore:
    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace).resolve()
        self.root = self.workspace / ".app-builder" / "checkpoints"

    def create(self, label: str = "checkpoint") -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in label.lower()).strip("-") or "checkpoint"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        target = self.root / f"{stamp}-{safe}"
        suffix = 1
        while target.exists():
            target = self.root / f"{stamp}-{safe}-{suffix}"
            suffix += 1
        target.mkdir(parents=True, exist_ok=False)
        for source in self.workspace.iterdir():
            if source.name in {".app-builder", "__pycache__"}:
                continue
            destination = target / source.name
            if source.is_dir():
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
        return target

    def latest(self) -> Path | None:
        if not self.root.exists():
            return None
        items = sorted(path for path in self.root.iterdir() if path.is_dir())
        return items[-1] if items else None

    def restore(self, checkpoint: str | Path | None = None) -> Path:
        source = Path(checkpoint).resolve() if checkpoint else self.latest()
        if source is None or not source.is_dir() or source.parent != self.root:
            raise ValueError("Invalid checkpoint")
        for target in list(self.workspace.iterdir()):
            if target.name in {".app-builder", "__pycache__"}:
                continue
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        for item in source.iterdir():
            destination = self.workspace / item.name
            if item.is_dir():
                shutil.copytree(item, destination)
            else:
                shutil.copy2(item, destination)
        return source
