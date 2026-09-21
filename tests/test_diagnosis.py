import unittest

from app.diagnosis import FailureDiagnoser


class FailureDiagnosisTests(unittest.TestCase):
    def test_maps_javascript_failure_to_specific_repair(self):
        result = FailureDiagnoser().diagnose("JavaScript syntax check failed: Unexpected token")
        self.assertEqual(result["category"], "javascript syntax")
        self.assertEqual(result["confidence"], "deterministic")
        self.assertIn("app.js", result["action"])

    def test_preserves_unknown_failure_evidence(self):
        result = FailureDiagnoser().diagnose("Something unexpected happened")
        self.assertEqual(result["category"], "unknown")
        self.assertIn("Something unexpected happened", result["evidence"])


if __name__ == "__main__":
    unittest.main()
