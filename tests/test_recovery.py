import tempfile
import unittest
from pathlib import Path

from app.release_state import ReleaseState
from app.server import _recover_stale_job


class RecoveryTests(unittest.TestCase):
    def test_stale_job_becomes_resumable(self):
        job = {"status": "running", "cancel_requested": False, "diagnostics": {}}
        self.assertTrue(_recover_stale_job(job, "2026-09-24T12:00:00+00:00"))
        self.assertEqual(job["status"], "pending")
        self.assertTrue(job["diagnostics"]["resume_eligible"])
        self.assertEqual(job["diagnostics"]["recovery_count"], 1)

    def test_cancelled_running_job_is_not_recovered(self):
        job = {"status": "running", "cancel_requested": True, "diagnostics": {}}
        self.assertFalse(_recover_stale_job(job, "2026-09-24T12:00:00+00:00"))
        self.assertEqual(job["status"], "running")

    def test_release_can_roll_forward_after_previous_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = ReleaseState(tmp)
            state.set("ready", "old")
            state.set("awaiting_approval", "old")
            state.set("deploy_pending", "old")
            state.set("published", "old")
            next_release = state.mark_ready("new")
            self.assertEqual(next_release["state"], "ready")
            self.assertEqual(next_release["release_hash"], "new")


if __name__ == "__main__":
    unittest.main()
