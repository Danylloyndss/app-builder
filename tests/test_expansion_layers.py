import tempfile
import unittest
from pathlib import Path

from app.integrations import EnvironmentSecretProvider, IntegrationConfig, IntegrationRegistry
from app.release import ReleaseManager
from app.runtime import RuntimeSmokeTest
from app.specialists import SpecialistRunner
from app.coding_agent import AgentAction


class ExpansionLayerTests(unittest.TestCase):
    def test_integration_requires_runtime_secret(self):
        registry = IntegrationRegistry(EnvironmentSecretProvider())
        registry.register(IntegrationConfig("payments", enabled=True, secret_names=("PAYMENTS_KEY",)))
        ok, message = registry.ready("payments")
        self.assertFalse(ok)
        self.assertIn("missing", message)

        approved_registry = IntegrationRegistry(EnvironmentSecretProvider())
        approved_registry.register(IntegrationConfig("analytics", enabled=True, requires_approval=True))
        ok, message = approved_registry.ready("analytics")
        self.assertFalse(ok)
        self.assertIn("approval", message)
        ok, _ = approved_registry.ready("analytics", approved=True)
        self.assertTrue(ok)

    def test_release_report_hashes_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<html></html>")
            (root / "app.js").write_text("console.log('ok')")
            (root / "README.md").write_text("# Generated App\n\nA complete generated application.")
            (root / "Dockerfile").write_text("FROM python:3.12-slim")
            (root / "railway.toml").write_text("[deploy]\nstartCommand = \"python -m app.server\"")
            report = ReleaseManager().prepare(root, True)
            self.assertTrue(report.ready)
            self.assertIn("index.html", report.artifacts)

            deployment_blocked = ReleaseManager().prepare(root, True, production=True)
            self.assertFalse(deployment_blocked.ready)
            self.assertIn("deployment readiness manifest", " ".join(deployment_blocked.blockers))

            (root / "railway.toml").unlink()
            blocked = ReleaseManager().prepare(root, True, production=True, authentication_ready=False)
            self.assertFalse(blocked.ready)
            self.assertIn("authentication", " ".join(blocked.blockers))
            self.assertIn("deployment manifest", " ".join(blocked.blockers))

            (root / "railway.toml").write_text("[deploy]\nstartCommand = \"python -m app.server\"")
            (root / ".app-builder").mkdir(exist_ok=True)
            (root / ".app-builder" / "deployment.json").write_text('{"configured":true}')
            (root / "backend.py").write_text("print('ok')\n")
            (root / ".app-builder" / "backend.json").write_text('{"entrypoint":"backend.py","health":"/health"}')
            ready = ReleaseManager().prepare(root, True, production=True)
            self.assertTrue(ready.ready)

            (root / ".app-builder").mkdir(exist_ok=True)
            (root / ".app-builder" / "backend.json").write_text('{"entrypoint":"backend.py","health":"/health"}')
            manifest_ready = ReleaseManager().prepare(root, True, production=True)
            self.assertTrue(manifest_ready.ready)

            (root / ".app-builder" / "backend.json").write_text('{"entrypoint":"backend.py"}')
            manifest_blocked = ReleaseManager().prepare(root, True, production=True)
            self.assertFalse(manifest_blocked.ready)
            self.assertIn("backend manifest", " ".join(manifest_blocked.blockers))

    def test_runtime_smoke_passes_backend_compile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "backend.py").write_text("print('ok')\n")
            ok, _ = RuntimeSmokeTest().run(root)
            self.assertTrue(ok)

    def test_specialist_uses_same_bounded_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = SpecialistRunner(tmp, max_iterations=1)
            def planner(goal, files, observations):
                return [AgentAction("write", "specialist.txt", "done")]
            result = runner.run("qa", "fix test", planner, lambda _: (True, "passed"))
            self.assertTrue(result.success)
            self.assertTrue((Path(tmp) / "specialist.txt").exists())


if __name__ == "__main__":
    unittest.main()
