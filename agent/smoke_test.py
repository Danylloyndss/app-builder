from pathlib import Path

from .core import Manager


def run_smoke_test() -> None:
    state = Manager().run("Construa o TimePro", Path.cwd())
    assert state.mission == "Construa o TimePro"
    assert [task.status.value for task in state.tasks] == ["done", "done"]
    assert state.tasks[-1].result == "HELLO_APP_OK"
    print("APP_BUILDER_V1_SMOKE_TEST_OK")


if __name__ == "__main__":
    run_smoke_test()
