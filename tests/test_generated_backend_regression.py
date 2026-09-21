import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from app.build_engine import BuildEngine


class GeneratedTimeProBackendRegressionTests(unittest.TestCase):
    def test_generated_timepro_backend_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            BuildEngine(root).implement_backend("Construa o TimePro")
            result = subprocess.run([sys.executable, str(root / "tests" / "test_backend_integration.py")], cwd=root, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
