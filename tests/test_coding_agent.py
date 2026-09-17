import tempfile
import unittest
from pathlib import Path

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
            self.assertEqual(result.iterations, 2)
            self.assertIn("wrote app.txt", result.actions)

    def test_agent_is_bounded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = CodingAgent(temp_dir, max_iterations=2)

            def planner(goal, files, observations):
                return [AgentAction("write", "attempt.txt", "x")]

            def validator(workspace):
                return False, "still failing"

            result = agent.run("never finish", planner, validator)
            self.assertFalse(result.success)
            self.assertEqual(result.iterations, 2)
            self.assertEqual(len(result.errors), 2)


if __name__ == "__main__":
    unittest.main()
