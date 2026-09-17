import tempfile
import unittest
from pathlib import Path

from app.checkpoints import CheckpointStore


class CheckpointTests(unittest.TestCase):
    def test_create_and_restore(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            root.joinpath("app.txt").write_text("before", encoding="utf-8")
            store = CheckpointStore(root)
            checkpoint = store.create("before-change")
            root.joinpath("app.txt").write_text("after", encoding="utf-8")
            root.joinpath("new.txt").write_text("new", encoding="utf-8")
            restored = store.restore(checkpoint)
            self.assertEqual(restored, checkpoint)
            self.assertEqual(root.joinpath("app.txt").read_text(encoding="utf-8"), "before")
            self.assertFalse(root.joinpath("new.txt").exists())


if __name__ == "__main__":
    unittest.main()
