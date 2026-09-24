import tempfile
import unittest
from pathlib import Path

from app.deployment import DeploymentAdapter
from app.release_state import ReleaseState


class ReleaseStateTests(unittest.TestCase):
    def test_deployment_plan_and_state_are_durable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "railway.toml").write_text(
                '[deploy]\nstartCommand = "python -m app.server"\nhealthcheckPath = "/health"\n',
                encoding="utf-8",
            )
            path = DeploymentAdapter().save(root)
            self.assertTrue(path.is_file())
            self.assertTrue(DeploymentAdapter().plan(root).configured)
            state = ReleaseState(root).set("ready", "abc123")
            self.assertEqual(state["state"], "ready")
            self.assertEqual(ReleaseState(root).read()["release_hash"], "abc123")

    def test_invalid_release_state_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                ReleaseState(tmp).set("unknown")


if __name__ == "__main__":
    unittest.main()
