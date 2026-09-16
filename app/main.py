"""App Builder V1 entry point."""

from .manager import Manager


def main() -> None:
    memory = Manager().run("Create a simple Hello App")
    print("Mission:", memory.mission)
    print("Plan:")
    for item in memory.plan:
        print("-", item)
    print("Completed:")
    for item in memory.completed:
        print("-", item)
    if memory.errors:
        print("Errors:")
        for error in memory.errors:
            print("-", error)


if __name__ == "__main__":
    main()
