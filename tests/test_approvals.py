import tempfile
import unittest
from pathlib import Path

from app.approvals import ApprovalStore


class ApprovalStoreTests(unittest.TestCase):
    def test_rejection_is_persisted_and_not_reported_as_approval(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ApprovalStore(Path(temp_dir) / "approvals.json")
            request = store.create("Publish app", "Human approval required")
            decided = store.decide(request.id, False)
            self.assertEqual(decided["status"], "rejected")
            self.assertIsNone(store.approved_for("Publish app", request.id))
            self.assertEqual(store.get(request.id)["status"], "rejected")

    def test_approval_is_single_use(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ApprovalStore(Path(temp_dir) / "approvals.json")
            request = store.create("Deploy", "Human approval required")
            store.decide(request.id, True)
            self.assertIsNotNone(store.approved_for("Deploy", request.id))
            self.assertIsNotNone(store.consume(request.id))
            self.assertIsNone(store.approved_for("Deploy", request.id))


if __name__ == "__main__":
    unittest.main()
