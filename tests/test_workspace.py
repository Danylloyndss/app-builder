import tempfile
import unittest
from pathlib import Path

from app.workspace import Workspace


class WorkspaceTests(unittest.TestCase):
    def test_workspace_write_read_and_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Workspace(Path(temp_dir) / "project")
            workspace.write_file("src/app.txt", "hello")
            self.assertEqual(workspace.read_file("src/app.txt"), "hello")
            self.assertEqual(workspace.list_files(), ["src/app.txt"])

    def test_workspace_blocks_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Workspace(Path(temp_dir) / "project")
            with self.assertRaises(ValueError):
                workspace.write_file("../outside.txt", "blocked")

    def test_workspace_runs_commands(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Workspace(Path(temp_dir) / "project")
            code, output = workspace.run(["python", "-c", "print('workspace-ok')"])
            self.assertEqual(code, 0)
            self.assertEqual(output, "workspace-ok")


if __name__ == "__main__":
    unittest.main()
