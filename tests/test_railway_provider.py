import os
import tempfile
import unittest
from unittest import mock

from app.railway_provider import RailwayProvider


class RailwayProviderTests(unittest.TestCase):
    def test_without_credentials_it_requests_external_action(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {}, clear=True):
            result = RailwayProvider(tmp).publish()
        self.assertEqual(result.status, "external_action_required")
        self.assertTrue(result.external_action_required)

    def test_status_maps_success(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"RAILWAY_API_TOKEN": "test-token"}, clear=True):
            completed = mock.Mock(returncode=0, stdout='{"status":"success","url":"https://example.test"}\n', stderr="")
            with mock.patch("subprocess.run", return_value=completed):
                result = RailwayProvider(tmp).status("dep-123")
        self.assertEqual(result.status, "published")
        self.assertEqual(result.url, "https://example.test")

    def test_authenticated_publish_queues_deployment(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"RAILWAY_API_TOKEN": "test-token"}, clear=True):
            completed = mock.Mock(returncode=0, stdout='{"deploymentId":"dep-123"}\n', stderr="")
            with mock.patch("subprocess.run", return_value=completed) as run:
                result = RailwayProvider(tmp).publish()
        self.assertEqual(result.status, "queued")
        self.assertEqual(result.deployment_id, "dep-123")
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
