import unittest

from datetime import datetime, timezone

from app.server import _recover_stale_job


class WorkerRecoveryTests(unittest.TestCase):
    def test_running_job_becomes_resumable_after_restart(self):
        job = {
            "status": "running",
            "cancel_requested": False,
            "diagnostics": {"worker_attempt": 3},
        }
        now = datetime.now(timezone.utc).isoformat()

        self.assertTrue(_recover_stale_job(job, now))
        self.assertEqual(job["status"], "pending")
        self.assertEqual(job["started_at"], None)
        self.assertTrue(job["diagnostics"]["resume_eligible"])
        self.assertEqual(job["diagnostics"]["recovery_reason"], "worker_restart")
        self.assertEqual(job["diagnostics"]["recovery_count"], 1)
        self.assertEqual(job["diagnostics"]["recovered_at"], now)

    def test_cancelled_job_is_not_requeued(self):
        job = {"status": "running", "cancel_requested": True, "diagnostics": {}}

        self.assertFalse(_recover_stale_job(job, "now"))
        self.assertEqual(job["status"], "running")


if __name__ == "__main__":
    unittest.main()
