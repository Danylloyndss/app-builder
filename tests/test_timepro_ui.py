import unittest
from pathlib import Path


class TimeProUiTests(unittest.TestCase):
    def test_timepro_ui_uses_persistent_api(self):
        html = (Path(__file__).parents[1] / "app" / "static" / "timepro.html").read_text(encoding="utf-8")
        self.assertIn("/api/timepro/timesheets", html)
        self.assertIn("/api/timepro/history", html)
        self.assertIn("/api/timepro/dashboard", html)
        self.assertNotIn("localStorage", html)

    def test_server_exposes_timepro_ui(self):
        server = (Path(__file__).parents[1] / "app" / "server.py").read_text(encoding="utf-8")
        self.assertIn("TIMEPRO_INDEX", server)
        self.assertIn("/timepro", server)


if __name__ == "__main__":
    unittest.main()
