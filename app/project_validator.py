"""Generic generated-project validation for App Builder.

This validator checks contracts that apply to every generated web project,
without depending on a specific product such as TimePro.
"""

from __future__ import annotations

import json
from pathlib import Path
import re


class ProjectValidator:
    REQUIRED = ("index.html", "app.js", "README.md")

    def validate(self, workspace: Path, mission: str = "") -> tuple[bool, list[str]]:
        errors: list[str] = []
        for name in self.REQUIRED:
            path = workspace / name
            if not path.is_file():
                errors.append(f"Missing required artifact: {name}")
            elif not path.read_text(encoding="utf-8").strip():
                errors.append(f"Empty required artifact: {name}")

        index_path = workspace / "index.html"
        script_path = workspace / "app.js"
        if index_path.is_file():
            html = index_path.read_text(encoding="utf-8")
            lowered = html.lower()
            if "<html" not in lowered or "</html>" not in lowered:
                errors.append("index.html is not a complete HTML document")
            if "<head" in lowered and '<meta name="viewport"' not in lowered:
                errors.append("index.html is missing a mobile viewport")
            scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.I)
            for source in scripts:
                if not (workspace / source).is_file():
                    errors.append(f"HTML references missing script: {source}")

        if script_path.is_file() and not script_path.read_text(encoding="utf-8").strip():
            errors.append("app.js is empty")

        features_path = workspace / ".app-builder" / "features.json"
        if features_path.exists():
            try:
                features = json.loads(features_path.read_text(encoding="utf-8"))
                if not isinstance(features, list) or any(not isinstance(x, str) for x in features):
                    errors.append("features.json must contain a list of strings")
            except (OSError, ValueError):
                errors.append("features.json is invalid JSON")

        integrations_path = workspace / ".app-builder" / "integrations.json"
        if integrations_path.exists():
            try:
                integrations = json.loads(integrations_path.read_text(encoding="utf-8"))
                if not isinstance(integrations.get("integrations", {}), dict):
                    errors.append("integrations.json must contain an integrations object")
                else:
                    for name, config in integrations["integrations"].items():
                        if not isinstance(config, dict) or config.get("approval_required") is not True:
                            errors.append(f"Integration {name} must require explicit approval")
            except (OSError, ValueError, TypeError):
                errors.append("integrations.json is invalid JSON")

        adapters_dir = workspace / ".app-builder" / "integrations"
        if adapters_dir.exists():
            for adapter in adapters_dir.glob("*.json"):
                try:
                    data = json.loads(adapter.read_text(encoding="utf-8"))
                    if data.get("external_call") is not False or data.get("approval_required") is not True:
                        errors.append(f"Unsafe integration adapter: {adapter.name}")
                except (OSError, ValueError, TypeError):
                    errors.append(f"Invalid integration adapter: {adapter.name}")

        return not errors, errors
