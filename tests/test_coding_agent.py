import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.coding_agent import AgentAction, CodingAgent


class CodingAgentTests(unittest.TestCase):
    def test_agent_can_write_and_validate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = CodingAgent(temp_dir, max_iterations=3)

            def planner(goal, files, observations):
                if "app.txt" not in files:
                    return [AgentAction("write", "app.txt", "hello")]
                return []

            def validator(workspace):
                path = workspace.root / "app.txt"
                return path.exists() and path.read_text(encoding="utf-8") == "hello", "app.txt is ready"

            result = agent.run("create hello app", planner, validator)
            self.assertTrue(result.success)
            self.assertEqual(result.iterations, 1)
            self.assertIn("wrote app.txt", result.actions)

    def test_agent_is_bounded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = CodingAgent(temp_dir, max_iterations=2)
            result = agent.run("never finish", lambda *_: [AgentAction("write", "attempt.txt", "x")],
                               lambda _: (False, "still failing"))
            self.assertFalse(result.success)
            self.assertEqual(result.iterations, 2)

    def test_model_planner_applies_structured_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = CodingAgent(temp_dir)
            response = {"choices": [{"message": {"content": json.dumps({
                "actions": [{"kind": "write", "target": "generated.py", "content": "print('ok')\n"}]
            })}}]}
            fake = type("Response", (), {
                "__enter__": lambda self: self,
                "__exit__": lambda self, *args: None,
                "read": lambda self: json.dumps(response).encode(),
            })()
            with patch.dict(os.environ, {"APP_BUILDER_LLM_URL": "https://example.invalid"}):
                with patch("app.coding_agent.urlopen", return_value=fake):
                    result = agent.run("implement feature")
            self.assertTrue(result.success)
            self.assertEqual((Path(temp_dir) / "generated.py").read_text(), "print('ok')\n")

    def test_run_command_allowlist_blocks_arbitrary_execution(self):
        with self.assertRaises(ValueError):
            CodingAgent._validate_command(["python", "-c", "print('bad')"])
        with self.assertRaises(ValueError):
            CodingAgent._validate_command(["node", "-e", "console.log('bad')"])
        with self.assertRaises(ValueError):
            CodingAgent._validate_command(["npm", "install", "package"])

    def test_run_command_allowlist_accepts_validation_commands(self):
        for command in (
            ["python", "-m", "py_compile", "backend.py"],
            ["python", "-m", "unittest", "discover"],
            ["node", "--check", "app.js"],
            ["npm", "test"],
        ):
            CodingAgent._validate_command(command)

    def test_model_cannot_escape_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = CodingAgent(temp_dir)
            response = {"choices": [{"message": {"content": json.dumps({
                "actions": [{"kind": "write", "target": "../outside.txt", "content": "bad"}]
            })}}]}
            fake = type("Response", (), {
                "__enter__": lambda self: self,
                "__exit__": lambda self, *args: None,
                "read": lambda self: json.dumps(response).encode(),
            })()
            with patch.dict(os.environ, {"APP_BUILDER_LLM_URL": "https://example.invalid"}):
                with patch("app.coding_agent.urlopen", return_value=fake):
                    with self.assertRaises(ValueError):
                        agent.model_planner("goal", [], [])


if __name__ == "__main__":
    unittest.main()
