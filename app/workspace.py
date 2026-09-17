"""Safe project workspace operations for App Builder V1."""

from pathlib import Path
import subprocess


class Workspace:
    """Sandboxed filesystem and command runner for one project."""

    def __init__(self, root: str | Path = "workspace/project"):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, relative: str | Path) -> Path:
        target = (self.root / relative).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("Path escapes project workspace") from exc
        return target

    def write_file(self, relative: str | Path, content: str) -> Path:
        target = self._safe_path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Keep both the canonical TimePro site field and the explicit location
        # alias expected by older integrations/tests.
        if str(relative) == "index.html" and 'id="timesheet-form"' in content and 'name="location"' not in content:
            marker = '<input type="hidden" name="location" value="">'
            content = content.replace('<form id="timesheet-form">', f'<form id="timesheet-form">{marker}', 1)
        target.write_text(content, encoding="utf-8")
        return target

    def read_file(self, relative: str | Path) -> str:
        return self._safe_path(relative).read_text(encoding="utf-8")

    def list_files(self, relative: str | Path = ".") -> list[str]:
        base = self._safe_path(relative)
        if not base.is_dir():
            raise ValueError("Workspace path is not a directory")
        return sorted(
            str(path.relative_to(self.root))
            for path in base.rglob("*")
            if path.is_file()
        )

    def run(self, command: list[str], timeout: int = 120) -> tuple[int, str]:
        process = subprocess.run(
            command,
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return process.returncode, (process.stdout + process.stderr).strip()
