import tempfile
import unittest

from app.release_controller import ReleaseController
from app.release_state import ReleaseState


class ReleaseControllerTests(unittest.TestCase):
    def test_approval_and_publish_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = ReleaseController(tmp)
            controller.state.set("ready", "abc")
            controller.request_approval("abc")
            self.assertEqual(ReleaseState(tmp).read()["state"], "awaiting_approval")
            controller.approve("abc")
            result = controller.publish("railway", "abc")
            self.assertTrue(result.external_action_required)
            self.assertEqual(ReleaseState(tmp).read()["state"], "deploy_pending")
            self.assertEqual(len(controller.history.list()), 3)

    def test_failed_release_can_be_recovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = ReleaseController(tmp)
            controller.state.set("ready", "abc")
            controller.fail("abc", "health check failed")
            self.assertEqual(ReleaseState(tmp).read()["state"], "failed")
            controller.state.set("ready", "abc", reason="fixed")
            self.assertEqual(ReleaseState(tmp).read()["state"], "ready")


if __name__ == "__main__":
    unittest.main()
