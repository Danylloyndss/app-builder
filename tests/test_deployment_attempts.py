import tempfile
import unittest

from app.deployment_attempts import DeploymentAttempts


class DeploymentAttemptsTests(unittest.TestCase):
    def test_retry_limit_and_inflight_protection(self):
        with tempfile.TemporaryDirectory() as tmp:
            attempts = DeploymentAttempts(tmp, max_attempts=2)
            first = attempts.begin("railway", "abc")
            self.assertTrue(first["allowed"])
            self.assertFalse(attempts.begin("railway", "abc")["allowed"])
            attempts.finish(first["attempt_id"], "queued", deployment_id="dep-1", url="https://example.test")
            stored = attempts._load()[-1]
            self.assertEqual(stored["deployment_id"], "dep-1")
            self.assertEqual(stored["url"], "https://example.test")
            attempts.finish(first["attempt_id"], "failed")
            second = attempts.begin("railway", "abc")
            self.assertTrue(second["allowed"])
            attempts.finish(second["attempt_id"], "failed")
            self.assertFalse(attempts.begin("railway", "abc")["allowed"])


if __name__ == "__main__":
    unittest.main()
