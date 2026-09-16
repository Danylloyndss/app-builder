import tempfile
import unittest
from pathlib import Path

from app.manager import Manager


class AppBuilderV1Tests(unittest.TestCase):
    def test_hello_app_mission(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = Manager(temp_dir).run("Create a simple Hello App")
            output = Path(temp_dir) / "hello_app.txt"
            state = Path(temp_dir) / "state.json"

            self.assertTrue(output.exists())
            self.assertTrue(output.read_text(encoding="utf-8").strip())
            self.assertTrue(state.exists())
            self.assertEqual(memory.mission, "Create a simple Hello App")
            self.assertFalse(memory.errors)
            self.assertTrue(memory.completed)


if __name__ == "__main__":
    unittest.main()
