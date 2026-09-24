import tempfile
import unittest
from pathlib import Path

import app.server as server


class ServerControlTests(unittest.TestCase):
    def test_enqueue_job_persists_production_flag(self):
        old = server.WORKSPACE
        try:
            with tempfile.TemporaryDirectory() as tmp:
                server.WORKSPACE = tmp
                job = server._enqueue_job("build TimePro", production=True)
                self.assertTrue(job["production"])
                stored = server._load_jobs()[0]
                self.assertTrue(stored["production"])
        finally:
            server.WORKSPACE = old

    def test_stale_job_becomes_resumable(self):
        job = {"status": "running", "cancel_requested": False, "diagnostics": {}}
        self.assertTrue(server._recover_stale_job(job, "2026-09-24T00:00:00+00:00"))
        self.assertEqual(job["status"], "pending")
        self.assertTrue(job["diagnostics"]["resume_eligible"])


if __name__ == "__main__":
    unittest.main()
