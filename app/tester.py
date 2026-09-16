"""Testing component for App Builder V1."""

from pathlib import Path


class Tester:
    def test(self, workspace: Path) -> tuple[bool, str]:
        marker = workspace / "hello_app.txt"
        if marker.exists() and marker.read_text(encoding="utf-8").strip():
            return True, "Hello App test passed"
        return False, "Expected output file was not created"
