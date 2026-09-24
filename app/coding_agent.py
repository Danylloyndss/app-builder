"""Bounded coding specialist for App Builder V1.

The execution loop is deterministic and sandboxed. An optional
OpenAI-compatible model endpoint can provide structured write/run actions;
without configuration the builder keeps its deterministic BuildEngine path.
"""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen

from .workspace import Workspace


@dataclass
class AgentAction:
    kind: str
    target: str = ""
    content: str = ""
    command: list[str] = field(default_factory=list)


@dataclass
class AgentResult:
    success: bool
    iterations: int
    actions: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class CodingAgent:
    """Observe -> plan -> act -> validate, with a strict iteration budget."""

    def __init__(self, workspace: str | Path, max_iterations: int = 5):
        self.project = Workspace(workspace)
        self.max_iterations = max(1, max_iterations)

    @property
    def model_configured(self) -> bool:
        return bool(os.environ.get("APP_BUILDER_LLM_URL"))

    def inspect(self) -> list[str]:
        return self.project.list_files(".")

    def apply(self, action: AgentAction) -> str:
        if action.kind == "write":
            if len(action.content.encode("utf-8")) > 2_000_000:
                raise ValueError("Agent file write is too large")
            self.project.write_file(action.target, action.content)
            return f"wrote {action.target}"
        if action.kind == "run":
            code, output = self.project.run(action.command)
            if code:
                raise RuntimeError(output or f"command exited with {code}")
            return f"ran {' '.join(action.command)}"
        raise ValueError(f"Unsupported agent action: {action.kind}")

    def model_planner(self, goal: str, files: list[str], observations: list[str]) -> list[AgentAction]:
        if not self.model_configured:
            return []
        payload = {
            "model": os.environ.get("APP_BUILDER_LLM_MODEL", "gpt-5"),
            "messages": [
                {"role": "system", "content": (
                    "You are a coding specialist. Return ONLY JSON with "
                    "{actions:[{kind:'write',target,content}|{kind:'run',command}],summary}. "
                    "Paths are relative to the workspace. Never use ../, absolute paths, "
                    "shell operators, secrets, credentials, or binary data. Prefer write "
                    "actions and the smallest safe change."
                )},
                {"role": "user", "content": json.dumps({
                    "goal": goal, "files": files[-200:], "observations": observations[-10:]
                }, ensure_ascii=False)},
            ],
            "temperature": 0,
        }
        raw = self._request(payload)
        outer = json.loads(raw)
        content = outer.get("choices", [{}])[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise ValueError("LLM response did not contain message content")
        data = json.loads(content)
        actions = []
        for item in data.get("actions", []):
            if not isinstance(item, dict):
                raise ValueError("Invalid model action")
            kind = item.get("kind")
            if kind == "write":
                target, content = item.get("target"), item.get("content")
                if not isinstance(target, str) or not isinstance(content, str):
                    raise ValueError("Invalid write action")
                if target.startswith("/") or ".." in Path(target).parts:
                    raise ValueError("Model attempted workspace escape")
                if any(x in content.lower() for x in (
                    "-----begin private key-----", "api_key=", "secret_key="
                )):
                    raise ValueError("Model proposed a possible secret")
                actions.append(AgentAction("write", target, content))
            elif kind == "run":
                command = item.get("command")
                if not isinstance(command, list) or not all(isinstance(x, str) and x for x in command):
                    raise ValueError("Invalid run action")
                self._validate_command(command)
                actions.append(AgentAction("run", command=command))
            else:
                raise ValueError("Unsupported model action")
        return actions

    @staticmethod
    def _validate_command(command: list[str]) -> None:
        """Allow only narrowly-scoped validation/build commands."""
        program = command[0]
        if program in {"python", "python3"}:
            if len(command) < 3 or command[1] != "-m" or command[2] not in {"py_compile", "unittest", "pytest"}:
                raise ValueError("Python command is restricted to test/compile modules")
            return
        if program == "pytest":
            return
        if program == "node":
            if len(command) >= 2 and command[1] in {"--check", "--test"}:
                return
            raise ValueError("Node command is restricted to syntax/test checks")
        if program == "npm":
            if command[1:] in (["test"], ["run", "test"], ["run", "build"]):
                return
            raise ValueError("npm command is restricted to test/build scripts")
        raise ValueError("Command is not allowlisted")

    def _request(self, payload: dict) -> str:
        url = os.environ["APP_BUILDER_LLM_URL"]
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        token = os.environ.get("APP_BUILDER_LLM_API_KEY")
        if token:
            headers["Authorization"] = "Bearer " + token
        with urlopen(
            Request(url, data=body, method="POST", headers=headers),
            timeout=int(os.environ.get("APP_BUILDER_LLM_TIMEOUT", "60")),
        ) as response:
            return response.read().decode("utf-8")

    def run(
        self,
        goal: str,
        planner: Callable[[str, list[str], list[str]], list[AgentAction]] | None = None,
        validator: Callable[[Workspace], tuple[bool, str]] | None = None,
    ) -> AgentResult:
        planner = planner or self.model_planner
        if validator is None:
            validator = lambda workspace: (True, "no validator configured")

        actions, errors, observations = [], [], []
        for iteration in range(1, self.max_iterations + 1):
            try:
                proposed = planner(goal, self.inspect(), observations)
                if not proposed:
                    ok, message = validator(self.project)
                    observations.append(message)
                    if ok:
                        return AgentResult(True, iteration, actions, errors)
                    errors.append(message)
                    continue
                for action in proposed:
                    actions.append(self.apply(action))
                ok, message = validator(self.project)
                observations.append(message)
                if ok:
                    return AgentResult(True, iteration, actions, errors)
                errors.append(message)
            except Exception as exc:
                errors.append(str(exc))
                observations.append(f"error: {exc}")
        return AgentResult(False, self.max_iterations, actions, errors)
