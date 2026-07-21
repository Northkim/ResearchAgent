"""Deterministic Agent Runtime coordinated through persistence ports."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from backend.agent_runtime._immutability import thaw_json
from backend.agent_runtime.context import ExecutionContextBuilder
from backend.domain.enums import StepRunStatus, WorkflowRunStatus
from backend.domain.exceptions import ExecutionNotResumableError
from backend.domain.models import ApprovalRequest, Checkpoint
from backend.domain.models._utils import utc_now
from backend.domain.services import ExecutionState
from backend.execution_events import (
    EventPayload,
    EventSeverity,
    ExecutionEvent,
    ExecutionEventType,
)
from backend.persistence.models import CheckpointBoundary
from backend.persistence.ports import (
    CheckpointRepository,
    MemoryRepository,
    StaleStateError,
    UnitOfWork,
)
from backend.skill_system.models import SkillReference
from backend.skill_system.runtime import SkillExecutor
from backend.workflow_engine.models import (
    ApprovalCompleted,
    ApprovalOutcome,
    NoAction,
    RetryScheduled,
    StepReady,
    WaitingApproval,
    WorkflowCancelled,
    WorkflowCompleted,
    WorkflowFailed,
)
from backend.workflow_engine.services import WorkflowExecutionCoordinator

from .runtime_result import RuntimeResult


class AgentRuntimeError(RuntimeError):
    """Raised when orchestration cannot safely continue."""


Clock = Callable[[], datetime]
IdFactory = Callable[[str], str]


def _default_id_factory(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class AgentRuntime:
    """Invoke components in order and persist each recovery boundary atomically."""

    def __init__(
        self,
        *,
        workflow_coordinator: WorkflowExecutionCoordinator,
        skill_executor: SkillExecutor,
        unit_of_work: UnitOfWork,
        context_builder: ExecutionContextBuilder | None = None,
        max_decisions: int = 100,
        clock: Clock = utc_now,
        id_factory: IdFactory = _default_id_factory,
        approval_ttl: timedelta = timedelta(hours=24),
    ) -> None:
        if max_decisions <= 0:
            raise ValueError("max_decisions must be positive")
        if approval_ttl <= timedelta(0):
            raise ValueError("approval_ttl must be positive")
        self.workflow = workflow_coordinator
        self.skills = skill_executor
        self.uow = unit_of_work
        self.context_builder = context_builder or ExecutionContextBuilder()
        self.max_decisions = max_decisions
        self._clock = clock
        self._id_factory = id_factory
        self._approval_ttl = approval_ttl
        self._persistence_versions: dict[str, int | None] = {}

    @property
    def memory(self) -> MemoryRepository:
        return self.uow.memory

    @property
    def checkpoints(self) -> CheckpointRepository:
        return self.uow.checkpoints

    async def run(
        self,
        execution_or_id: ExecutionState | str,
        *,
        approval_outcome: ApprovalOutcome | None = None,
    ) -> RuntimeResult:
        """Run from a new aggregate or restore one by WorkflowRun ID."""

        execution, is_new = self._resolve_execution(execution_or_id)
        memory_was_empty = (
            self.memory.latest_revision_number(
                execution.workflow_run.project_id,
                execution.workflow_run.id,
            )
            == 0
        )
        checkpoints_were_empty = not self.checkpoints.list_records(
            execution.workflow_run.id
        )
        self._initialize_memory(execution)
        self._record_baseline(execution)
        if is_new or memory_was_empty or checkpoints_were_empty:
            self._commit(execution)

        if execution.workflow_run.status.is_terminal:
            return self._result(execution)

        if execution.workflow_run.status is WorkflowRunStatus.CREATED:
            checkpoint = self.workflow.domain.start_execution(execution)
            self._emit_event(
                execution,
                ExecutionEventType.WORKFLOW_STARTED,
                {
                    "status": execution.workflow_run.status.value,
                    "workflow_id": execution.workflow.id,
                    "workflow_version": execution.workflow.version,
                },
            )
            self._record(
                execution,
                CheckpointBoundary.INITIALIZED,
                checkpoint,
            )
            self._commit(execution)

        preparation_result = self._prepare_resume(
            execution,
            approval_outcome=approval_outcome,
        )
        if preparation_result is not None:
            return preparation_result

        for _ in range(self.max_decisions):
            decision = self.workflow.decide(execution)

            if isinstance(decision, StepReady):
                yielded = await self._execute_step(execution, decision)
                if yielded is not None:
                    return yielded
                continue

            if isinstance(decision, WaitingApproval):
                checkpoint = self.workflow.apply_decision(execution, decision)
                if checkpoint is None:
                    raise AgentRuntimeError("WaitingApproval did not create a checkpoint")
                approval = self._create_approval_request(
                    execution,
                    step_id=decision.step_id,
                    step_run_id=decision.step_run_id,
                    attempt=decision.attempt,
                    policy_key=decision.approval_policy,
                )
                self._emit_event(
                    execution,
                    ExecutionEventType.APPROVAL_REQUESTED,
                    {
                        "approval_request_id": approval.id,
                        "step_id": decision.step_id,
                        "attempt": decision.attempt,
                        "policy_key": decision.approval_policy,
                        "expires_at": approval.expires_at.isoformat()
                        if approval.expires_at is not None
                        else None,
                    },
                    step_run_id=decision.step_run_id,
                )
                self._record(
                    execution,
                    CheckpointBoundary.WAITING_APPROVAL,
                    checkpoint,
                    step_id=decision.step_id,
                    attempt=decision.attempt,
                )
                self._commit(execution)
                return self._result(execution)

            if isinstance(decision, RetryScheduled):
                checkpoint = self.workflow.apply_decision(execution, decision)
                if checkpoint is None:
                    raise AgentRuntimeError("RetryScheduled did not create a checkpoint")
                self._record(
                    execution,
                    CheckpointBoundary.RETRY_SCHEDULED,
                    checkpoint,
                    step_id=decision.step_id,
                    attempt=decision.current_attempt,
                )
                self._commit(execution)
                return self._result(execution)

            if isinstance(decision, WorkflowCompleted):
                return self._apply_terminal_decision(execution, decision)

            if isinstance(decision, WorkflowFailed):
                return self._apply_terminal_decision(execution, decision)

            if isinstance(decision, WorkflowCancelled):
                return self._apply_terminal_decision(execution, decision)

            if isinstance(decision, ApprovalCompleted):
                checkpoint = self.workflow.apply_decision(execution, decision)
                if checkpoint is not None:
                    self._record(
                        execution,
                        CheckpointBoundary.APPROVAL_RESOLVED,
                        checkpoint,
                        step_id=decision.step_id,
                    )
                    self._commit(execution)
                continue

            if isinstance(decision, NoAction):
                return self._result(execution)

            raise AgentRuntimeError(
                f"Unsupported Workflow Engine decision {type(decision).__name__}"
            )

        raise AgentRuntimeError(
            f"Execution exceeded deterministic limit of {self.max_decisions} decisions"
        )

    def load_execution(self, workflow_run_id: str) -> ExecutionState:
        """Reconstitute a detached execution and attach its checkpoint stream."""

        execution = self.uow.workflows.get(workflow_run_id)
        if execution is None:
            raise AgentRuntimeError(f"WorkflowRun {workflow_run_id} was not found")
        execution.checkpoints.extend(self.checkpoints.list(workflow_run_id))
        if not execution.checkpoints:
            raise AgentRuntimeError(
                f"WorkflowRun {workflow_run_id} has no persisted checkpoint"
            )
        execution.latest_checkpoint.verify_integrity()
        version = self.uow.workflows.get_version(workflow_run_id)
        if version is None:
            raise AgentRuntimeError(
                f"WorkflowRun {workflow_run_id} has no persistence version"
            )
        self._persistence_versions[workflow_run_id] = version
        return execution

    def _resolve_execution(
        self,
        execution_or_id: ExecutionState | str,
    ) -> tuple[ExecutionState, bool]:
        if isinstance(execution_or_id, str):
            return self.load_execution(execution_or_id), False

        run_id = execution_or_id.workflow_run.id
        stored_version = self.uow.workflows.get_version(run_id)
        if stored_version is not None:
            return self.load_execution(run_id), False
        self._persistence_versions[run_id] = None
        return execution_or_id, True

    def _prepare_resume(
        self,
        execution: ExecutionState,
        *,
        approval_outcome: ApprovalOutcome | None,
    ) -> RuntimeResult | None:
        status = execution.workflow_run.status

        if status is WorkflowRunStatus.WAITING_FOR_APPROVAL:
            if approval_outcome is None:
                self._ensure_pending_approval(execution)
                return self._result(execution)
            if approval_outcome is not ApprovalOutcome.APPROVED:
                before_terminal = self.workflow.domain.create_checkpoint(execution)
                self._record(
                    execution,
                    CheckpointBoundary.BEFORE_TERMINAL,
                    before_terminal,
                    step_id=self._waiting_step_id(execution),
                )
            decision = self.workflow.resolve_approval(
                execution,
                execution.latest_checkpoint,
                outcome=approval_outcome,
            )
            boundary = (
                CheckpointBoundary.APPROVAL_RESOLVED
                if approval_outcome is ApprovalOutcome.APPROVED
                else CheckpointBoundary.TERMINAL
            )
            self._record(
                execution,
                boundary,
                execution.latest_checkpoint,
                step_id=getattr(decision, "step_id", None),
            )
            self._commit(execution)
            if execution.workflow_run.status.is_terminal:
                return self._result(execution)
            return None

        if status is WorkflowRunStatus.RETRY_SCHEDULED:
            self.workflow.resume_from_checkpoint(execution, execution.latest_checkpoint)
            retry_step = self._active_or_ready_step(execution)
            self._record(
                execution,
                CheckpointBoundary.RECOVERED,
                execution.latest_checkpoint,
                step_id=retry_step.step_id if retry_step is not None else None,
                attempt=retry_step.attempt if retry_step is not None else None,
            )
            self._commit(execution)
            return None

        if status is WorkflowRunStatus.RUNNING:
            active = [
                step
                for step in execution.current_step_runs()
                if step.status is StepRunStatus.RUNNING
            ]
            if active:
                active_definition = execution.workflow.get_step(active[0].step_id)
                if active[0].attempt >= active_definition.max_attempts:
                    self._record(
                        execution,
                        CheckpointBoundary.BEFORE_TERMINAL,
                        execution.latest_checkpoint,
                        step_id=active[0].step_id,
                        attempt=active[0].attempt,
                    )
                try:
                    self.workflow.resume_from_checkpoint(
                        execution,
                        execution.latest_checkpoint,
                    )
                except ExecutionNotResumableError:
                    if execution.workflow_run.status.is_terminal:
                        self._record(
                            execution,
                            CheckpointBoundary.TERMINAL,
                            execution.latest_checkpoint,
                            step_id=active[0].step_id,
                            attempt=active[0].attempt,
                        )
                        self._emit_event(
                            execution,
                            ExecutionEventType.WORKFLOW_FAILED,
                            {
                                "status": execution.workflow_run.status.value,
                                "error_code": execution.workflow_run.error_code,
                                "failed_step_id": active[0].step_id,
                            },
                            severity=EventSeverity.ERROR,
                            step_run_id=active[0].id,
                        )
                        self._commit(execution)
                        return self._result(execution)
                    raise
                recovered = self._active_or_ready_step(execution)
                self._record(
                    execution,
                    CheckpointBoundary.RECOVERED,
                    execution.latest_checkpoint,
                    step_id=recovered.step_id if recovered is not None else None,
                    attempt=recovered.attempt if recovered is not None else None,
                )
                self._commit(execution)
            return None

        if status in {
            WorkflowRunStatus.WAITING_FOR_INPUT,
            WorkflowRunStatus.INITIALIZING,
            WorkflowRunStatus.CANCELLING,
        }:
            return self._result(execution)

        return None

    async def _execute_step(
        self,
        execution: ExecutionState,
        decision: StepReady,
    ) -> RuntimeResult | None:
        ready_checkpoint = self.workflow.apply_decision(execution, decision)
        if ready_checkpoint is not None:
            self._record(
                execution,
                CheckpointBoundary.STEP_READY,
                ready_checkpoint,
                step_id=decision.step_id,
                attempt=decision.attempt,
            )
            self._commit(execution)

        step_run = execution.latest_step_run(decision.step_id)
        if step_run.status is not StepRunStatus.READY:
            raise AgentRuntimeError(
                f"Step {decision.step_id} must be READY before skill execution"
            )
        self.workflow.domain.update_step_state(
            execution,
            step_id=decision.step_id,
            target_status=StepRunStatus.RUNNING,
        )
        self._emit_event(
            execution,
            ExecutionEventType.STEP_STARTED,
            {
                "step_id": decision.step_id,
                "attempt": decision.attempt,
                "skill_ref": decision.skill_ref,
            },
            step_run_id=decision.step_run_id,
        )
        self._create_checkpoint(
            execution,
            CheckpointBoundary.BEFORE_SKILL,
            step_id=decision.step_id,
            attempt=decision.attempt,
        )

        context = self.context_builder.build(execution, decision, self.memory)
        result = await self.skills.execute(
            decision,
            SkillReference.parse(decision.skill_ref),
            context.resolved_inputs,
        )

        if result.success:
            checkpoint = self.workflow.domain.update_step_state(
                execution,
                step_id=decision.step_id,
                target_status=StepRunStatus.COMPLETED,
                outputs=result.output_data,
            )
            if checkpoint is None:
                raise AgentRuntimeError("Skill completion did not create a checkpoint")
            self._emit_event(
                execution,
                ExecutionEventType.SKILL_EXECUTED,
                {
                    "step_id": decision.step_id,
                    "attempt": decision.attempt,
                    "skill_ref": decision.skill_ref,
                    "success": True,
                    "output_fields": sorted(result.output_data),
                },
                step_run_id=decision.step_run_id,
            )
            self._record(
                execution,
                CheckpointBoundary.AFTER_SKILL,
                checkpoint,
                step_id=decision.step_id,
                attempt=decision.attempt,
            )
            self._update_memory(execution, decision, result.output_data)
            self._commit(execution)
            return None

        if result.error is None:
            raise AgentRuntimeError("Failed SkillResult has no typed error")
        failure_decision = self.workflow.evaluate_failure(
            execution,
            step_id=decision.step_id,
            retryable=result.error.retryable,
            error_code=result.error.code,
            message=result.error.message,
        )
        if isinstance(failure_decision, WorkflowFailed):
            self._create_checkpoint(
                execution,
                CheckpointBoundary.BEFORE_TERMINAL,
                step_id=decision.step_id,
                attempt=decision.attempt,
            )
        checkpoint = self.workflow.apply_decision(execution, failure_decision)
        if checkpoint is None:
            raise AgentRuntimeError("Skill failure did not create a checkpoint")
        self._emit_event(
            execution,
            ExecutionEventType.SKILL_EXECUTED,
            {
                "step_id": decision.step_id,
                "attempt": decision.attempt,
                "skill_ref": decision.skill_ref,
                "success": False,
                "error_code": result.error.code,
                "retryable": result.error.retryable,
            },
            severity=EventSeverity.WARNING
            if result.error.retryable
            else EventSeverity.ERROR,
            step_run_id=decision.step_run_id,
        )
        self._record(
            execution,
            CheckpointBoundary.AFTER_SKILL,
            checkpoint,
            step_id=decision.step_id,
            attempt=decision.attempt,
        )

        if isinstance(failure_decision, RetryScheduled):
            self._record(
                execution,
                CheckpointBoundary.RETRY_SCHEDULED,
                checkpoint,
                step_id=decision.step_id,
                attempt=decision.attempt,
            )
            self._commit(execution)
            return self._result(execution)

        if isinstance(failure_decision, WorkflowFailed):
            self._record(
                execution,
                CheckpointBoundary.TERMINAL,
                checkpoint,
                step_id=decision.step_id,
                attempt=decision.attempt,
            )
            self._emit_event(
                execution,
                ExecutionEventType.WORKFLOW_FAILED,
                {
                    "status": execution.workflow_run.status.value,
                    "error_code": execution.workflow_run.error_code,
                    "failed_step_id": decision.step_id,
                },
                severity=EventSeverity.ERROR,
                step_run_id=decision.step_run_id,
            )
            self._commit(execution)
            return self._result(execution)

        raise AgentRuntimeError(
            f"Unsupported failure decision {type(failure_decision).__name__}"
        )

    def _apply_terminal_decision(
        self,
        execution: ExecutionState,
        decision: WorkflowCompleted | WorkflowFailed | WorkflowCancelled,
    ) -> RuntimeResult:
        self._create_checkpoint(
            execution,
            CheckpointBoundary.BEFORE_TERMINAL,
            step_id=getattr(decision, "failed_step_id", None)
            or getattr(decision, "step_id", None),
        )
        checkpoint = self.workflow.apply_decision(execution, decision)
        if checkpoint is None:
            raise AgentRuntimeError("Terminal decision did not create a checkpoint")
        self._record(
            execution,
            CheckpointBoundary.TERMINAL,
            checkpoint,
            step_id=getattr(decision, "failed_step_id", None)
            or getattr(decision, "step_id", None),
        )
        if isinstance(decision, WorkflowCompleted):
            self._emit_event(
                execution,
                ExecutionEventType.WORKFLOW_COMPLETED,
                {
                    "status": execution.workflow_run.status.value,
                    "output_fields": sorted(execution.workflow_run.outputs),
                },
            )
        elif isinstance(decision, WorkflowFailed):
            failed_step_id = decision.failed_step_id
            failed_step_run = (
                execution.latest_step_run(failed_step_id)
                if failed_step_id is not None
                else None
            )
            self._emit_event(
                execution,
                ExecutionEventType.WORKFLOW_FAILED,
                {
                    "status": execution.workflow_run.status.value,
                    "error_code": decision.error_code,
                    "failed_step_id": failed_step_id,
                    "retry_exhausted": decision.retry_exhausted,
                },
                severity=EventSeverity.ERROR,
                step_run_id=failed_step_run.id
                if failed_step_run is not None
                else None,
            )
        self._commit(execution)
        return self._result(execution)

    def _initialize_memory(self, execution: ExecutionState) -> None:
        self.memory.initialize_context(
            project_id=execution.workflow_run.project_id,
            workflow_run_id=execution.workflow_run.id,
            context={
                "workflow_id": execution.workflow.id,
                "workflow_version": execution.workflow.version,
                "workflow_inputs": execution.workflow_run.inputs,
                "step_outputs": {},
            },
            producer="agent_runtime.initialize",
            source_references=(
                f"workflow:{execution.workflow.id}@{execution.workflow.version}",
            ),
        )

    def _update_memory(
        self,
        execution: ExecutionState,
        decision: StepReady,
        outputs: Mapping[str, Any],
    ) -> None:
        current = thaw_json(
            self.memory.read_context(
                execution.workflow_run.project_id,
                execution.workflow_run.id,
            )
        )
        step_outputs = dict(current.get("step_outputs", {}))
        step_outputs[decision.step_id] = {
            "attempt": decision.attempt,
            "outputs": thaw_json(outputs),
        }
        self.memory.update_context(
            project_id=execution.workflow_run.project_id,
            workflow_run_id=execution.workflow_run.id,
            updates={"step_outputs": step_outputs},
            producer=f"skill:{decision.skill_ref}",
            source_references=(f"step_run:{decision.step_run_id}",),
        )

    def _record_baseline(self, execution: ExecutionState) -> None:
        if execution.checkpoints and not self.checkpoints.list_records(
            execution.workflow_run.id
        ):
            self._record(
                execution,
                CheckpointBoundary.BASELINE,
                execution.latest_checkpoint,
                emit_event=False,
            )

    def _create_checkpoint(
        self,
        execution: ExecutionState,
        boundary: CheckpointBoundary,
        *,
        step_id: str | None = None,
        attempt: int | None = None,
    ) -> Checkpoint:
        checkpoint = self.workflow.domain.create_checkpoint(execution)
        self._record(
            execution,
            boundary,
            checkpoint,
            step_id=step_id,
            attempt=attempt,
        )
        self._commit(execution)
        return checkpoint

    def _record(
        self,
        execution: ExecutionState,
        boundary: CheckpointBoundary,
        checkpoint: Checkpoint,
        *,
        step_id: str | None = None,
        attempt: int | None = None,
        emit_event: bool = True,
    ) -> None:
        is_new_checkpoint = checkpoint.id not in {
            current.id for current in self.checkpoints.list(checkpoint.workflow_run_id)
        }
        self.checkpoints.save(
            checkpoint,
            boundary=boundary,
            step_id=step_id,
            attempt=attempt,
        )
        if is_new_checkpoint and emit_event:
            self._emit_event(
                execution,
                ExecutionEventType.CHECKPOINT_CREATED,
                {
                    "checkpoint_id": checkpoint.id,
                    "checkpoint_sequence": checkpoint.sequence,
                    "boundary": boundary.value,
                    "step_id": step_id,
                    "attempt": attempt,
                    "run_status": execution.workflow_run.status.value,
                },
                step_run_id=(
                    execution.latest_step_run(step_id).id
                    if step_id is not None
                    else None
                ),
            )

    def _create_approval_request(
        self,
        execution: ExecutionState,
        *,
        step_id: str,
        step_run_id: str,
        attempt: int,
        policy_key: str,
    ) -> ApprovalRequest:
        requested_at = self._clock()
        requested_action = {
            "kind": "workflow_approval",
            "workflow_id": execution.workflow.id,
            "workflow_version": execution.workflow.version,
            "workflow_run_id": execution.workflow_run.id,
            "step_id": step_id,
            "step_run_id": step_run_id,
            "attempt": attempt,
            "policy_key": policy_key,
            "workflow_inputs": thaw_json(execution.workflow_run.inputs),
        }
        canonical_action = json.dumps(
            requested_action,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        fingerprint = "sha256:" + hashlib.sha256(
            canonical_action.encode("utf-8")
        ).hexdigest()
        approval = ApprovalRequest(
            id=self._id_factory("approval"),
            project_id=execution.workflow_run.project_id,
            workflow_run_id=execution.workflow_run.id,
            step_run_id=step_run_id,
            policy_key=policy_key,
            request_fingerprint=fingerprint,
            prompt=f"Approval required for workflow step {step_id}",
            requested_action=requested_action,
            requested_by=execution.agent_session.id,
            permitted_approver_role=policy_key,
            requested_at=requested_at,
            expires_at=requested_at + self._approval_ttl,
        )
        self.uow.approvals.save(approval, expected_version=None)
        return approval

    def _ensure_pending_approval(self, execution: ExecutionState) -> None:
        pending = self.uow.approvals.list_pending_for_run(
            execution.workflow_run.project_id,
            execution.workflow_run.id,
        )
        if pending:
            return
        step_id = self._waiting_step_id(execution)
        if step_id is None:
            raise AgentRuntimeError(
                "Waiting WorkflowRun does not identify an approval step"
            )
        step_run = execution.latest_step_run(step_id)
        step = execution.workflow.get_step(step_id)
        if step.approval_policy is None:
            raise AgentRuntimeError(
                f"Approval step {step_id} has no approval policy"
            )
        approval = self._create_approval_request(
            execution,
            step_id=step_id,
            step_run_id=step_run.id,
            attempt=step_run.attempt,
            policy_key=step.approval_policy,
        )
        self._emit_event(
            execution,
            ExecutionEventType.APPROVAL_REQUESTED,
            {
                "approval_request_id": approval.id,
                "step_id": step_id,
                "attempt": step_run.attempt,
                "policy_key": step.approval_policy,
                "expires_at": approval.expires_at.isoformat()
                if approval.expires_at is not None
                else None,
                "recovered": True,
            },
            step_run_id=step_run.id,
        )
        self._record(
            execution,
            CheckpointBoundary.WAITING_APPROVAL,
            execution.latest_checkpoint,
            step_id=step_id,
            attempt=step_run.attempt,
        )
        self._commit(execution)

    def _emit_event(
        self,
        execution: ExecutionState,
        event_type: ExecutionEventType,
        payload: Mapping[str, Any],
        *,
        severity: EventSeverity = EventSeverity.INFO,
        step_run_id: str | None = None,
    ) -> ExecutionEvent:
        run = execution.workflow_run
        current_sequence = self.uow.events.latest_sequence(
            run.project_id,
            run.id,
        )
        event = ExecutionEvent(
            id=self._id_factory("event"),
            project_id=run.project_id,
            workflow_run_id=run.id,
            sequence=current_sequence + 1,
            event_type=event_type,
            payload=EventPayload(data=payload),
            request_id=run.idempotency_key,
            occurred_at=self._clock(),
            severity=severity,
            agent_session_id=execution.agent_session.id,
            step_run_id=step_run_id,
            correlation_id=run.id,
        )
        return self.uow.events.append(
            event,
            expected_sequence=current_sequence,
        )

    def _commit(self, execution: ExecutionState) -> None:
        run_id = execution.workflow_run.id
        self._sync_domain_checkpoints(execution)
        expected_version = self._persistence_versions.get(run_id)
        try:
            next_version = self.uow.workflows.save(
                execution,
                expected_version=expected_version,
            )
            self.uow.commit()
        except Exception:
            self.uow.rollback()
            raise
        self._persistence_versions[run_id] = next_version

    def _sync_domain_checkpoints(self, execution: ExecutionState) -> None:
        persisted_ids = {
            checkpoint.id for checkpoint in self.checkpoints.list(execution.workflow_run.id)
        }
        for checkpoint in execution.checkpoints:
            if checkpoint.id not in persisted_ids:
                self._record(
                    execution,
                    CheckpointBoundary.DOMAIN_TRANSITION,
                    checkpoint,
                )
                persisted_ids.add(checkpoint.id)

    def _result(self, execution: ExecutionState) -> RuntimeResult:
        completed = tuple(
            step.id
            for step in execution.workflow.steps
            if execution.latest_step_run(step.id).status
            in {StepRunStatus.COMPLETED, StepRunStatus.SKIPPED}
        )
        return RuntimeResult(
            workflow_run_id=execution.workflow_run.id,
            agent_session_id=execution.agent_session.id,
            status=execution.workflow_run.status,
            outputs=execution.workflow_run.outputs,
            wait_reason=execution.workflow_run.wait_reason,
            error_code=execution.workflow_run.error_code,
            completed_steps=completed,
            domain_checkpoint_count=len(self.checkpoints.list(execution.workflow_run.id)),
            runtime_checkpoint_count=len(
                self.checkpoints.list_records(execution.workflow_run.id)
            ),
            memory_revision=self.memory.latest_revision_number(
                execution.workflow_run.project_id,
                execution.workflow_run.id,
            ),
        )

    @staticmethod
    def _waiting_step_id(execution: ExecutionState) -> str | None:
        reason = execution.workflow_run.wait_reason
        if reason and reason.startswith("approval:"):
            return reason.removeprefix("approval:")
        return None

    @staticmethod
    def _active_or_ready_step(execution: ExecutionState):
        matches = [
            step
            for step in execution.current_step_runs()
            if step.status in {StepRunStatus.READY, StepRunStatus.RUNNING}
        ]
        return matches[0] if len(matches) == 1 else None
