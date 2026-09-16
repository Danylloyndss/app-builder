import tempfile
import unittest
from pathlib import Path

from app.manager import Manager


class BuildEngineTests(unittest.TestCase):
    def test_generates_real_web_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = Manager(temp_dir).run("Create a simple expense tracker")
            self.assertEqual(memory.status, "completed")
            self.assertFalse(memory.errors)
            self.assertTrue((Path(temp_dir) / "index.html").exists())
            self.assertTrue((Path(temp_dir) / "app.js").exists())
            self.assertTrue((Path(temp_dir) / "README.md").exists())


if __name__ == "__main__":
    unittest.main()
