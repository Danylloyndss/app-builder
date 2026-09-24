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
            attempts.finish(first["attempt_id"], "failed")
            second = attempts.begin("railway", "abc")
            self.assertTrue(second["allowed"])
            attempts.finish(second["attempt_id"], "failed")
            self.assertFalse(attempts.begin("railway", "abc")["allowed"])


if __name__ == "__main__":
    unittest.main()
