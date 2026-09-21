import tempfile
import unittest
from pathlib import Path

from app.tester import Tester


class TesterFallbackTests(unittest.TestCase):
    def test_executable_integration_script_is_run_when_discovery_finds_no_tests(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "index.html").write_text('<html><head><meta name="viewport" content="width=device-width"></head><body><script src="app.js"></script></body></html>', encoding="utf-8")
            (root / "app.js").write_text("console.log('ok')", encoding="utf-8")
            (root / "README.md").write_text("# Test", encoding="utf-8")
            tests = root / "tests"
            tests.mkdir()
            (tests / "test_integration.py").write_text("assert 2 + 2 == 4\n", encoding="utf-8")
            ok, message = Tester().test(root)
            self.assertTrue(ok, message)
            self.assertIn("integration", message.lower())


if __name__ == "__main__":
    unittest.main()
