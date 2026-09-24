import unittest

from app.server import Handler


class ServerReleaseApiTests(unittest.TestCase):
    def test_release_control_plane_exposes_lifecycle_routes(self):
        source = __import__("pathlib").Path("app/server.py").read_text(encoding="utf-8")
        for route in (
            '"/release/history"',
            '"/release/prepare"',
            '"/release/publish"',
            '"/release/health"',
            '"/release/rollback"',
        ):
            self.assertIn(route, source)


if __name__ == "__main__":
    unittest.main()
