import tempfile
import unittest
from pathlib import Path

from app.approvals import ApprovalStore
from app.manager import Manager
from app.memory import ProjectMemory
from app.tasks import BuildTask


class ApprovalResumeTests(unittest.TestCase):
    def _seed(self, root: Path, approval_id: str):
        task = BuildTask("deploy", "Deploy application", "build", status="waiting_for_approval")
        builder = Manager(workspace=str(root))
        builder.memory = ProjectMemory(
            mission="build a demo app",
            status="waiting_for_approval",
            current_task=task.title,
            task_statuses={task.id: "waiting_for_approval"},
            diagnostics={"approval_id": approval_id, "approval_task_id": task.id},
        )
        builder._save_tasks([task])
        builder.memory.save(builder.memory_path)

    def test_resume_requires_the_linked_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ApprovalStore(root / "approvals.json")
            linked = store.create("Deploy application", "linked")
            other = store.create("Deploy application", "other")
            store.decide(other.id, True)
            self._seed(root, linked.id)

            manager = Manager(workspace=str(root))
            resumed = manager.run("build a demo app", resume=True)

            self.assertEqual(resumed.status, "waiting_for_approval")
            self.assertEqual(resumed.task_statuses["deploy"], "waiting_for_approval")

    def test_resume_releases_task_when_linked_approval_is_approved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ApprovalStore(root / "approvals.json")
            linked = store.create("Deploy application", "linked")
            store.decide(linked.id, True)
            self._seed(root, linked.id)

            manager = Manager(workspace=str(root))
            manager._execute_task = lambda task, tasks: False
            resumed = manager.run("build a demo app", resume=True)

            self.assertEqual(resumed.task_statuses["deploy"], "pending")


if __name__ == "__main__":
    unittest.main()
