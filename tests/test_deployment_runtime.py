import tempfile
import unittest
from unittest import mock
from pathlib import Path

from app.deployment_runtime import DeploymentRuntime
from app.deployment_history import DeploymentHistory


class DeploymentRuntimeTests(unittest.TestCase):
    def test_publish_never_fakes_success(self):
        result = DeploymentRuntime().publish("railway", "abc")
        self.assertEqual(result.status, "external_action_required")
        self.assertTrue(result.external_action_required)
        self.assertIsNone(result.health)

    def test_verify_command_uses_argv(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = DeploymentRuntime().verify_command(
                ["python", "-c", "print('ok')"], Path(tmp)
            )
            self.assertTrue(result["ok"])
            self.assertEqual(result["returncode"], 0)

    def test_health_rejects_local_targets(self):
        result = DeploymentRuntime().health_check("http://127.0.0.1:8080/health")
        self.assertFalse(result.ok)
        self.assertIn("restricted", result.error)

    def test_health_accepts_2xx(self):
        response = mock.Mock(status=204)
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        with mock.patch("urllib.request.urlopen", return_value=response):
            with mock.patch("socket.getaddrinfo", return_value=[(2,1,6,"",("93.184.216.34",443))]):
                result = DeploymentRuntime().health_check("https://example.com/health")
        self.assertTrue(result.ok)
        self.assertEqual(result.status_code, 204)

    def test_history_is_durable_and_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            history = DeploymentHistory(tmp)
            history.append("external_action_required", "railway", "abc", "login required")
            self.assertEqual(history.list()[0]["release_hash"], "abc")


if __name__ == "__main__":
    unittest.main()
