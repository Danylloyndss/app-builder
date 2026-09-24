"""Dependency-light runtime smoke checks for generated applications."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


class RuntimeSmokeTest:
    """Validate generated Python backends without requiring browser dependencies."""

    def run(self, workspace: str | Path) -> tuple[bool, str]:
        root = Path(workspace)
        backend = root / "backend.py"
        if not backend.exists():
            return True, "No backend runtime to smoke-test"
        proc = subprocess.run(
            [sys.executable, "-m", "py_compile", str(backend)],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode:
            return False, (proc.stdout + proc.stderr)[-2000:]
        return True, "Backend runtime compilation passed"
