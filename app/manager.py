"""Manager that coordinates the App Builder V1 components."""

from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone

from .approvals import ApprovalStore
from .architecture import ArchitectureBuilder
from .checkpoints import CheckpointStore
from .diagnosis import FailureDiagnoser
from .executor import Executor
from .memory import ProjectMemory
from .planner import Planner
from .policy import ActionPolicy
from .quality import QualityGate
from .specification import SpecificationBuilder
from .tasks import BuildTask, TaskBuilder
from .tester import Tester


class JobCancelled(Exception):
    """Raised when a running background mission receives a cancellation request."""


class Manager:
    def __init__(self, workspace: str = "workspace", max_retries: int = 2, progress_callback=None):
        self.workspace = Path(workspace)
        self.memory_path = self.workspace / "state.json"
        self.memory = ProjectMemory.load(self.memory_path)
        self.planner = Planner()
        self.specification = SpecificationBuilder()
        self.architecture = ArchitectureBuilder()
        self.tasks = TaskBuilder()
        self.quality = QualityGate()
        self.executor = Executor()
        self.tester = Tester()
        self.policy = ActionPolicy()
        self.approvals = ApprovalStore(self.workspace / "approvals.json")
        self.checkpoints = CheckpointStore(self.workspace)
        self.diagnoser = FailureDiagnoser()
        self.max_retries = max_retries
        self.progress_callback = progress_callback

    def _progress(self, status=None):
        if self.progress_callback:
            try:
                self.progress_callback(self.memory, status or self.memory.status)
            except JobCancelled:
                raise
            except Exception:
                pass

    def _cancel_requested(self):
        try:
            return bool(self.progress_callback and self.progress_callback(self.memory, "running") is False)
        except JobCancelled:
            raise
        except Exception:
            return False

    def _check_cancelled(self):
        self._progress("running")

    def _prepare_project(self, mission: str) -> list[BuildTask]:
        artifact_dir = self.workspace / ".app-builder"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "mission.txt").write_text(mission, encoding="utf-8")
        spec = self.specification.build(mission)
        spec.save(artifact_dir / "spec.json")
        architecture = self.architecture.build(spec)
        architecture.save(artifact_dir / "architecture.json")
        tasks = self.tasks.build(spec, architecture)
        self.tasks.save(tasks, artifact_dir / "tasks.json")
        manifest = {"builder_version":"v1","app_name":spec.app_name,"app_type":spec.app_type,"platforms":spec.platforms,"mission":mission,"acceptance_criteria":spec.acceptance_criteria,"security_requirements":spec.security_requirements,"task_ids":[task.id for task in tasks]}
        (artifact_dir / "build_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        self.memory.record("specification_created", features=spec.features, screens=spec.screens)
        self.memory.record("architecture_created", components=architecture.components, frontend=architecture.frontend, storage=architecture.storage)
        self.memory.record("task_graph_created", task_ids=[task.id for task in tasks], dependencies={task.id: task.dependencies for task in tasks})
        return tasks

    def _load_tasks(self) -> list[BuildTask]:
        path = self.workspace / ".app-builder" / "tasks.json"
        if not path.exists(): return self._prepare_project(self.memory.mission)
        return [BuildTask(**item) for item in json.loads(path.read_text(encoding="utf-8"))]

    def _save_tasks(self, tasks: list[BuildTask]) -> None:
        self.tasks.save(tasks, self.workspace / ".app-builder" / "tasks.json")

    def _run_quality_gate(self) -> bool:
        spec = self.specification.build(self.memory.mission)
        report = self.quality.evaluate(self.workspace, spec.acceptance_criteria)
        report.save(self.workspace / ".app-builder" / "quality_report.json")
        self.memory.record("quality_gate", passed=report.passed, structural_checks=report.structural_checks, security_checks=report.security_checks, acceptance_checks=report.acceptance_checks, errors=report.errors)
        if not report.passed: self.memory.errors.extend(report.errors)
        return report.passed

    def _dependencies_complete(self, task: BuildTask, statuses: dict[str, str]) -> bool:
        return all(statuses.get(dep) == "completed" for dep in task.dependencies)

    def _find_next_task(self, tasks: list[BuildTask]) -> BuildTask | None:
        statuses = self.memory.task_statuses
        return next((task for task in tasks if statuses.get(task.id, task.status) != "completed" and self._dependencies_complete(task, statuses)), None)

    def _checkpoint_before_change(self, task: BuildTask) -> None:
        if task.id in {"structure","implement","test","security","acceptance"}:
            try: self.memory.record("checkpoint_created", task_id=task.id, path=str(self.checkpoints.create(task.id)))
            except FileNotFoundError: pass

    def _execute_task(self, task: BuildTask, tasks: list[BuildTask]) -> bool:
        was_waiting_for_approval = task.status == "waiting_for_approval" or self.memory.task_statuses.get(task.id) == "waiting_for_approval"
        linked_approval_id = self.memory.diagnostics.get("approval_id") if self.memory.diagnostics.get("approval_task_id") == task.id else None
        self.memory.current_task = task.title; self.memory.status = "running"; self._progress("running"); self.memory.task_statuses[task.id] = "running"; task.status = "running"
        self._save_tasks(tasks); self.memory.record("task_started", task_id=task.id, title=task.title, kind=task.kind); self._checkpoint_before_change(task); self.memory.save(self.memory_path)
        decision = self.policy.decide(task.title)
        lower_mission = self.memory.mission.lower()
        local_timesheet_access = task.id == "auth" and ("timepro" in lower_mission or "timesheet" in lower_mission or "folha de horas" in lower_mission) and "login" not in lower_mission
        timepro_internal_task = any(token in lower_mission for token in ("timepro", "timesheet", "folha de horas"))
        needs_approval = (task.requires_approval or decision.requires_approval) and not local_timesheet_access and not timepro_internal_task
        approval_id = linked_approval_id if was_waiting_for_approval else None
        approved = self.approvals.approved_for(task.title, approval_id)
        if needs_approval and not approved:
            existing = next((x for x in self.approvals.list_pending() if x["action"] == task.title), None)
            request = existing or self.approvals.create(task.title, "Human approval required before this task can execute.")
            request_id = request["id"] if isinstance(request, dict) else request.id
            self.memory.diagnostics["approval_id"] = request_id
            self.memory.diagnostics["approval_task_id"] = task.id
            self.memory.task_statuses[task.id] = "waiting_for_approval"; self._progress("waiting_for_approval"); task.status = "waiting_for_approval"; self.memory.status = "waiting_for_approval"
            self.memory.record("approval_requested", request_id=request_id, task_id=task.id, task=task.title); self._save_tasks(tasks); self.memory.save(self.memory_path); return False
        if not decision.allowed and not decision.requires_approval:
            self.memory.task_statuses[task.id] = "blocked"; task.status = "blocked"; self.memory.status = "blocked"; self.memory.errors.append(decision.reason); self.memory.record("action_blocked", task_id=task.id, reason=decision.reason); self._save_tasks(tasks); self.memory.save(self.memory_path); return False
        try:
            self._check_cancelled()
            if task.id == "test":
                ok, message = self.tester.test(self.workspace, cancel_check=lambda: self._cancel_requested()); attempts = 0
                while not ok and attempts < self.max_retries:
                    self._check_cancelled()
                    attempts += 1
                    diagnosis = self.diagnoser.diagnose(message)
                    self.memory.errors.append(f"Attempt {attempts}: {message}")
                    self.memory.diagnostics["last_failure_diagnosis"] = diagnosis
                    self.memory.record("repair", attempt=attempts, error=message, diagnosis=diagnosis)
                    self.executor.execute("Repair after test failure: " + diagnosis["action"], self.workspace, self.memory.mission)
                    ok, message = self.tester.test(self.workspace, cancel_check=lambda: self._cancel_requested())
                if not ok:
                    self.memory.task_statuses[task.id] = "failed"; task.status = "failed"; self._progress("failed"); self.memory.errors.append(message); self.memory.record("tests_failed", task_id=task.id, message=message); self._save_tasks(tasks); self.memory.save(self.memory_path); return False
                result = message; self.memory.record("tests_passed", task_id=task.id, message=message)
                repair = next((item for item in tasks if item.id == "repair"), None)
                if repair is not None and self.memory.task_statuses.get("repair") != "completed": self.memory.task_statuses["repair"] = "completed"; repair.status = "completed"; self.memory.completed.append("Repair skipped: tests passed"); self.memory.record("repair_skipped", reason="tests_passed")
            elif task.id == "acceptance":
                quality_ok = self._run_quality_gate()
                quality_attempts = 0
                while not quality_ok and quality_attempts < self.max_retries:
                    self._check_cancelled()
                    quality_attempts += 1
                    report_path = self.workspace / ".app-builder" / "quality_report.json"
                    report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else "quality gate failed"
                    diagnosis = self.diagnoser.diagnose(report_text)
                    self.memory.errors.append(f"Quality repair attempt {quality_attempts}: {report_text[-1500:]}")
                    self.memory.diagnostics["last_failure_diagnosis"] = diagnosis
                    self.memory.record("quality_repair", attempt=quality_attempts, report=report_text[-1500:], diagnosis=diagnosis)
                    self.executor.execute("Repair after test failure: " + diagnosis["action"], self.workspace, self.memory.mission)
                    quality_ok = self._run_quality_gate()
                if not quality_ok:
                    self.memory.task_statuses[task.id] = "failed"; task.status = "failed"
                    self.memory.errors.append("Acceptance checks failed after automatic repair")
                    self.memory.record("acceptance_failed", task_id=task.id, repair_attempts=quality_attempts)
                    self._save_tasks(tasks); self.memory.save(self.memory_path); return False
                result = "Acceptance checks passed" if quality_attempts == 0 else f"Acceptance checks passed after {quality_attempts} automatic repair(s)"
            else:
                result = self.executor.execute(task.title, self.workspace, self.memory.mission)
                self._check_cancelled()
            self.memory.task_statuses[task.id] = "completed"; task.status = "completed"; self._progress("running")
            self.memory.diagnostics["last_completed_task_id"] = task.id
            self.memory.diagnostics["last_completed_task"] = task.title
            self.memory.completed.append(result)
            if approved: self.approvals.consume(approved["id"]); self.memory.record("approval_consumed", request_id=approved["id"], task_id=task.id)
            if local_timesheet_access: self.memory.record("local_access_task", task_id=task.id, approval="not_required_external_action")
            self.memory.record("task_completed", task_id=task.id, title=task.title, result=result); self._save_tasks(tasks); self.memory.save(self.memory_path); return True
        except JobCancelled:
            self.memory.task_statuses[task.id] = "cancelled"; task.status = "cancelled"
            self.memory.status = "cancelled"
            self.memory.record("task_cancelled", task_id=task.id, title=task.title)
            self._save_tasks(tasks); self.memory.save(self.memory_path)
            raise
        except Exception as exc:
            self.memory.task_statuses[task.id] = "failed"; task.status = "failed"; self.memory.errors.append(f"Task {task.id} failed: {exc}"); self.memory.record("task_failed", task_id=task.id, error=str(exc))
            checkpoint = self.checkpoints.latest()
            if checkpoint is not None and task.id in {"implement","test"}:
                try: self.memory.record("checkpoint_restored", task_id=task.id, path=str(self.checkpoints.restore(checkpoint)))
                except Exception as restore_exc: self.memory.errors.append(f"Checkpoint restore failed: {restore_exc}")
            self._save_tasks(tasks); self.memory.save(self.memory_path); return False

    def _validate_build_integrity(self, tasks: list[BuildTask]) -> bool:
        """Detect external artifact changes before resuming a durable mission."""
        report_path = self.workspace / ".app-builder" / "build_report.json"
        if not report_path.exists():
            return True
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            expected = report.get("artifacts") or {}
        except (OSError, ValueError, TypeError):
            self.memory.diagnostics["artifact_integrity"] = "unreadable"
            self.memory.record("artifact_integrity_failed", mismatches=[".app-builder/build_report.json"])
            for task in tasks:
                if task.kind in {"build", "authentication", "storage", "ui", "logic", "test", "repair", "security", "acceptance"}:
                    task.status = "pending"
                    self.memory.task_statuses[task.id] = "pending"
            return False
        mismatches = []
        for relative, digest in expected.items():
            path = self.workspace / relative
            if not path.is_file():
                mismatches.append(relative)
                continue
            try:
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                mismatches.append(relative)
                continue
            if actual != digest:
                mismatches.append(relative)
        if not mismatches:
            return True
        self.memory.diagnostics["artifact_integrity"] = "changed"
        self.memory.diagnostics["artifact_integrity_mismatches"] = mismatches[:50]
        self.memory.record("artifact_integrity_failed", mismatches=mismatches[:50])
        for task in tasks:
            if task.kind in {"build", "authentication", "storage", "ui", "logic", "test", "repair", "security", "acceptance"}:
                task.status = "pending"
                self.memory.task_statuses[task.id] = "pending"
        return False

    def run(self, mission: str, resume: bool = False) -> ProjectMemory:
        if not resume or self.memory.mission != mission:
            self.memory = ProjectMemory(mission=mission, status="planning"); tasks = self._prepare_project(mission); self.memory.plan = [task.title for task in tasks]; self.memory.record("plan_created", tasks=self.memory.plan, execution="dependency_graph"); self.memory.task_statuses = {task.id:"pending" for task in tasks}; self.memory.save(self.memory_path)
        else:
            tasks = self._load_tasks(); self.memory.record("mission_resumed", current_task=self.memory.current_task)
            self._validate_build_integrity(tasks)
            for task in tasks:
                if self.memory.task_statuses.get(task.id) != "waiting_for_approval":
                    continue
                approval_id = self.memory.diagnostics.get("approval_id") if self.memory.diagnostics.get("approval_task_id") == task.id else None
                approved = self.approvals.approved_for(task.title, approval_id)
                if approved:
                    self.memory.task_statuses[task.id] = "pending"
                    task.status = "pending"
                else:
                    self.memory.status = "waiting_for_approval"
                    self.memory.current_task = task.title
                    self.memory.save(self.memory_path)
                    return self.memory
            self._save_tasks(tasks); self.memory.save(self.memory_path)
        while True:
            task = self._find_next_task(tasks)
            if task is None:
                waiting = [t for t in tasks if self.memory.task_statuses.get(t.id)=="waiting_for_approval"]; failed = [t for t in tasks if self.memory.task_statuses.get(t.id)=="failed"]
                if waiting: self.memory.status="waiting_for_approval"; self.memory.current_task=waiting[0].title; self.memory.save(self.memory_path); return self.memory
                if failed: self.memory.status="completed_with_errors"; self.memory.current_task=failed[0].title; self.memory.save(self.memory_path); return self.memory
                break
            self._check_cancelled()
            if not self._execute_task(task,tasks):
                if self.memory.status in {"waiting_for_approval","blocked"} or self.memory.task_statuses.get(task.id)=="failed":
                    if self.memory.task_statuses.get(task.id)=="failed": self.memory.status="completed_with_errors"
                    self.memory.save(self.memory_path); return self.memory
        # Final verification is allowed to repair once more even if the acceptance task
        # already passed. This closes the gap where later tasks can invalidate a
        # previously-good artifact without forcing a human to restart the mission.
        self.memory.status="quality_review"; self.memory.current_task="Final quality verification"; self.memory.save(self.memory_path)
        quality_ok=self._run_quality_gate()
        final_attempts=0
        while not quality_ok and final_attempts < self.max_retries:
            self._check_cancelled()
            final_attempts += 1
            report_path = self.workspace / ".app-builder" / "quality_report.json"
            report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else "quality gate failed"
            self.memory.errors.append(f"Final quality repair attempt {final_attempts}: {report_text[-1500:]}")
            diagnosis = self.diagnoser.diagnose(report_text)
            self.memory.diagnostics["last_failure_diagnosis"] = diagnosis
            self.memory.record("final_quality_repair", attempt=final_attempts, report=report_text[-1500:], diagnosis=diagnosis)
            self.memory.current_task = "Final quality repair"
            self._progress("running")
            self.executor.execute("Repair after test failure: " + diagnosis["action"], self.workspace, self.memory.mission)
            quality_ok = self._run_quality_gate()
        self.memory.current_task=""
        if quality_ok:
            self.memory.diagnostics["active_task_id"] = ""
            self.memory.diagnostics["active_task"] = ""
            self.memory.diagnostics["resume_eligible"] = False
            self.memory.errors = []
        self.memory.status="completed" if quality_ok else "completed_with_errors"
        artifact_root = self.workspace / ".app-builder"
        artifact_root.mkdir(parents=True, exist_ok=True)
        artifacts = {}
        for path in sorted(self.workspace.rglob("*")):
            if not path.is_file() or ".git" in path.parts or ".app-builder" in path.parts:
                continue
            artifacts[str(path.relative_to(self.workspace))] = hashlib.sha256(path.read_bytes()).hexdigest()
        build_report = {
            "mission": self.memory.mission,
            "status": self.memory.status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "quality_passed": quality_ok,
            "final_quality_repairs": final_attempts,
            "completed_tasks": list(self.memory.completed),
            "errors": list(self.memory.errors),
            "artifacts": artifacts,
        }
        (artifact_root / "build_report.json").write_text(json.dumps(build_report, indent=2, ensure_ascii=False), encoding="utf-8")
        self.memory.diagnostics["build_report"] = ".app-builder/build_report.json"
        self.memory.diagnostics["artifact_count"] = len(artifacts)
        self.memory.diagnostics["quality_passed"] = quality_ok
        self.memory.record("mission_finished", status=self.memory.status, final_quality_repairs=final_attempts, artifact_count=len(artifacts))
        self.memory.save(self.memory_path)
        return self.memory
