"""Idempotency helpers for release bundles."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json


def bundle_fingerprint(bundle: str | Path) -> str:
    return hashlib.sha256(Path(bundle).read_bytes()).hexdigest()


def load_manifest(workspace: str | Path) -> dict:
    path = Path(workspace) / ".app-builder" / "bundle_manifest.json"
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def is_same_release(workspace: str | Path, bundle: str | Path) -> bool:
    manifest = load_manifest(workspace)
    expected = manifest.get("bundle_sha256")
    return bool(expected) and expected == bundle_fingerprint(bundle)
