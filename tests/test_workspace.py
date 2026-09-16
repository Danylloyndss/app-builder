import pytest

from app.workspace import Workspace


def test_workspace_write_read_and_list(tmp_path):
    workspace = Workspace(tmp_path / "project")
    workspace.write_file("src/app.txt", "hello")

    assert workspace.read_file("src/app.txt") == "hello"
    assert workspace.list_files() == ["src/app.txt"]


def test_workspace_blocks_path_traversal(tmp_path):
    workspace = Workspace(tmp_path / "project")

    with pytest.raises(ValueError):
        workspace.write_file("../outside.txt", "blocked")


def test_workspace_runs_commands(tmp_path):
    workspace = Workspace(tmp_path / "project")
    code, output = workspace.run(["python", "-c", "print('workspace-ok')"])

    assert code == 0
    assert output == "workspace-ok"
