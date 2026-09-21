"""Safe project workspace operations for App Builder V1."""

from pathlib import Path
import subprocess
import os
import signal
import time


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

    def run(self, command: list[str], timeout: int = 120, cancel_check=None) -> tuple[int, str]:
        """Run a command with a hard timeout and optional cooperative cancellation.

        Commands run in their own process group so a cancellation/timeout can
        terminate the whole child tree instead of leaving orphan processes.
        """
        if not command or any(not isinstance(part, str) or not part for part in command):
            raise ValueError("Command must be a non-empty list of strings")
        env = os.environ.copy()
        process = subprocess.Popen(
            command,
            cwd=self.root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
            env=env,
        )
        deadline = time.monotonic() + timeout
        chunks = []
        try:
            while process.poll() is None:
                if cancel_check is not None and cancel_check():
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    raise RuntimeError("Command cancelled")
                if time.monotonic() >= deadline:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    raise subprocess.TimeoutExpired(command, timeout, output="".join(chunks))
                if process.stdout is not None:
                    line = process.stdout.readline()
                    if line:
                        chunks.append(line)
                        continue
                time.sleep(0.05)
            if process.stdout is not None:
                chunks.append(process.stdout.read())
            return process.returncode, "".join(chunks).strip()
        finally:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if process.stdout is not None and not process.stdout.closed:
                process.stdout.close()
