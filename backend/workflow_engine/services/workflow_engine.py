"""Pure Workflow Engine that answers what should happen next."""

from __future__ import annotations

from backend.domain.enums import AgentSessionStatus, StepRunStatus, WorkflowRunStatus, WorkflowStepKind

from ..exceptions import InvalidReferenceError, WorkflowStateError
from ..models import (
    ApprovalCompleted,
    ApprovalOutcome,
    EngineDecisionType,
    ExecutionSnapshot,
    NoAction,
    RetryScheduled,
    StepReady,
    WaitingApproval,
    WorkflowCancelled,
    WorkflowCompleted,
    WorkflowDefinition,
    WorkflowFailed,
)
from .reference_resolver import InputReferenceResolver
from .scheduler import DeterministicScheduler
from .validator import WorkflowValidator


class WorkflowEngine:
    """Validate state and return immutable decisions without mutation or I/O."""

    def __init__(
        self,
        *,
        validator: WorkflowValidator | None = None,
        scheduler: DeterministicScheduler | None = None,
        resolver: InputReferenceResolver | None = None,
    ) -> None:
        self._validator = validator or WorkflowValidator()
        self._scheduler = scheduler or DeterministicScheduler()
        self._resolver = resolver or InputReferenceResolver()

    def validate(self, definition: WorkflowDefinition) -> None:
        self._validator.validate(definition)

    def next_decision(
        self,
        definition: WorkflowDefinition,
        snapshot: ExecutionSnapshot,
    ) -> EngineDecisionType:
        self._validator.validate(definition)
        self._validate_snapshot_identity(definition, snapshot)

        if snapshot.run_status.is_terminal:
            return self._no_action(
                definition, snapshot, f"Workflow is terminal: {snapshot.run_status.value}"
            )
        if snapshot.run_status is not WorkflowRunStatus.RUNNING:
            return self._no_action(
                definition,
                snapshot,
                f"Workflow is not runnable: {snapshot.run_status.value}",
            )
        if snapshot.agent_status is not AgentSessionStatus.ACTIVE:
            return self._no_action(
                definition,
                snapshot,
                f"Agent session is not active: {snapshot.agent_status.value}",
            )

        try:
            all_successful = self._scheduler.all_successful(definition, snapshot)
            has_active_step = self._scheduler.has_active_step(definition, snapshot)
        except WorkflowStateError as error:
            return self._workflow_failed(
                definition,
                snapshot,
                error_code="INVALID_EXECUTION_STATE",
                message=str(error),
            )

        if all_successful:
            try:
                outputs = self._resolver.resolve_workflow_outputs(definition, snapshot)
            except InvalidReferenceError as error:
                return self._workflow_failed(
                    definition,
                    snapshot,
                    error_code="INVALID_WORKFLOW_OUTPUT",
                    message=str(error),
                )
            return WorkflowCompleted(
                **self._base(
                    definition,
                    snapshot,
                    checkpoint_required=True,
                    reason="All workflow steps completed",
                ),
                outputs=outputs,
            )

        if has_active_step:
            return self._no_action(
                definition, snapshot, "A workflow step is already active"
            )

        try:
            scheduled = self._scheduler.select(definition, snapshot)
        except WorkflowStateError as error:
            return self._workflow_failed(
                definition,
                snapshot,
                error_code="INVALID_EXECUTION_STATE",
                message=str(error),
            )

        if scheduled is None:
            latest = snapshot.latest_attempts()
            terminal_blockers = [
                step_id
                for step_id, step_run in latest.items()
                if step_run.status in {StepRunStatus.FAILED, StepRunStatus.CANCELLED}
            ]
            error_code = (
                "BLOCKED_BY_TERMINAL_STEP" if terminal_blockers else "WORKFLOW_DEADLOCK"
            )
            message = (
                f"Workflow is blocked by terminal steps {sorted(terminal_blockers)}"
                if terminal_blockers
                else "Workflow has no active or eligible step"
            )
            return self._workflow_failed(
                definition,
                snapshot,
                error_code=error_code,
                message=message,
            )

        step = scheduled.definition
        step_run = scheduled.step_run
        if step.kind is WorkflowStepKind.APPROVAL:
            try:
                resolved_inputs = self._resolver.resolve_step_inputs(
                    definition, step, snapshot
                )
            except InvalidReferenceError as error:
                return self._workflow_failed(
                    definition,
                    snapshot,
                    error_code="INVALID_APPROVAL_INPUT_REFERENCE",
                    message=str(error),
                    failed_step_id=step.id,
                    expected_step_version=step_run.row_version,
                )
            return WaitingApproval(
                **self._base(
                    definition,
                    snapshot,
                    checkpoint_required=True,
                    reason=f"Approval step {step.id} is ready",
                ),
                step_id=step.id,
                step_run_id=step_run.id,
                attempt=step_run.attempt,
                expected_step_version=step_run.row_version,
                approval_policy=step.approval_policy or "",
                resolved_inputs=resolved_inputs,
                requires_ready_transition=scheduled.requires_ready_transition,
            )

        try:
            resolved_inputs = self._resolver.resolve_step_inputs(
                definition, step, snapshot
            )
        except InvalidReferenceError as error:
            return self._workflow_failed(
                definition,
                snapshot,
                error_code="INVALID_STEP_INPUT_REFERENCE",
                message=str(error),
                failed_step_id=step.id,
                expected_step_version=step_run.row_version,
            )

        return StepReady(
            **self._base(
                definition,
                snapshot,
                checkpoint_required=scheduled.requires_ready_transition,
                reason=f"Skill step {step.id} is ready",
            ),
            step_id=step.id,
            step_run_id=step_run.id,
            attempt=step_run.attempt,
            expected_step_version=step_run.row_version,
            skill_ref=step.uses or "",
            resolved_inputs=resolved_inputs,
            requires_ready_transition=scheduled.requires_ready_transition,
        )

    def evaluate_failure(
        self,
        definition: WorkflowDefinition,
        snapshot: ExecutionSnapshot,
        *,
        step_id: str,
        retryable: bool,
        error_code: str,
        message: str = "",
    ) -> RetryScheduled | WorkflowFailed:
        self._validator.validate(definition)
        self._validate_snapshot_identity(definition, snapshot)
        if snapshot.run_status is not WorkflowRunStatus.RUNNING:
            raise WorkflowStateError("Failure can be evaluated only for a running workflow")
        step = definition.get_step(step_id)
        step_run = snapshot.latest_attempts().get(step_id)
        if step_run is None or step_run.status is not StepRunStatus.RUNNING:
            raise WorkflowStateError(
                f"Failure can be evaluated only for active step {step_id}"
            )

        if retryable and step.retry_policy.permits_retry(step_run.attempt):
            next_attempt = step_run.attempt + 1
            return RetryScheduled(
                **self._base(
                    definition,
                    snapshot,
                    checkpoint_required=True,
                    reason=f"Retryable failure in step {step_id}",
                ),
                step_id=step_id,
                step_run_id=step_run.id,
                current_attempt=step_run.attempt,
                next_attempt=next_attempt,
                expected_step_version=step_run.row_version,
                delay_seconds=step.retry_policy.delay_for_next_attempt(next_attempt),
                backoff=step.retry_policy.backoff,
                error_code=error_code,
            )

        return self._workflow_failed(
            definition,
            snapshot,
            error_code=error_code,
            message=message or f"Step {step_id} failed",
            failed_step_id=step_id,
            expected_step_version=step_run.row_version,
            retry_exhausted=retryable,
        )

    def evaluate_approval(
        self,
        definition: WorkflowDefinition,
        snapshot: ExecutionSnapshot,
        *,
        step_id: str,
        outcome: ApprovalOutcome,
    ) -> ApprovalCompleted | WorkflowCancelled:
        self._validator.validate(definition)
        self._validate_snapshot_identity(definition, snapshot)
        step = definition.get_step(step_id)
        if step.kind is not WorkflowStepKind.APPROVAL:
            raise WorkflowStateError(f"Step {step_id} is not an approval step")
        step_run = snapshot.latest_attempts().get(step_id)
        if step_run is None:
            raise WorkflowStateError(f"Approval step {step_id} has no execution state")

        if outcome is ApprovalOutcome.APPROVED:
            if (
                snapshot.run_status is not WorkflowRunStatus.RUNNING
                or step_run.status is not StepRunStatus.RUNNING
            ):
                raise WorkflowStateError(
                    "Approved step must first resume to RUNNING from its checkpoint"
                )
            return ApprovalCompleted(
                **self._base(
                    definition,
                    snapshot,
                    checkpoint_required=True,
                    reason=f"Approval for step {step_id} accepted",
                ),
                step_id=step_id,
                step_run_id=step_run.id,
                expected_step_version=step_run.row_version,
            )

        if (
            snapshot.run_status is not WorkflowRunStatus.WAITING_FOR_APPROVAL
            or step_run.status is not StepRunStatus.WAITING_APPROVAL
        ):
            raise WorkflowStateError(
                "Rejected or expired approval must reference a waiting step"
            )
        error_code = (
            "APPROVAL_REJECTED"
            if outcome is ApprovalOutcome.REJECTED
            else "APPROVAL_EXPIRED"
        )
        return WorkflowCancelled(
            **self._base(
                definition,
                snapshot,
                checkpoint_required=True,
                reason=f"Approval for step {step_id}: {outcome.value}",
            ),
            error_code=error_code,
            step_id=step_id,
        )

    @staticmethod
    def _base(
        definition: WorkflowDefinition,
        snapshot: ExecutionSnapshot,
        *,
        checkpoint_required: bool,
        reason: str,
    ) -> dict[str, object]:
        return {
            "workflow_run_id": snapshot.workflow_run_id,
            "workflow_id": definition.id,
            "workflow_version": definition.version,
            "expected_run_version": snapshot.run_row_version,
            "checkpoint_required": checkpoint_required,
            "reason": reason,
        }

    def _no_action(
        self,
        definition: WorkflowDefinition,
        snapshot: ExecutionSnapshot,
        reason: str,
    ) -> NoAction:
        return NoAction(
            **self._base(
                definition,
                snapshot,
                checkpoint_required=False,
                reason=reason,
            )
        )

    def _workflow_failed(
        self,
        definition: WorkflowDefinition,
        snapshot: ExecutionSnapshot,
        *,
        error_code: str,
        message: str,
        failed_step_id: str | None = None,
        expected_step_version: int | None = None,
        retry_exhausted: bool = False,
    ) -> WorkflowFailed:
        return WorkflowFailed(
            **self._base(
                definition,
                snapshot,
                checkpoint_required=True,
                reason=message,
            ),
            error_code=error_code,
            message=message,
            failed_step_id=failed_step_id,
            expected_step_version=expected_step_version,
            retry_exhausted=retry_exhausted,
        )

    @staticmethod
    def _validate_snapshot_identity(
        definition: WorkflowDefinition,
        snapshot: ExecutionSnapshot,
    ) -> None:
        if (
            snapshot.workflow_id != definition.id
            or snapshot.workflow_version != definition.version
        ):
            raise WorkflowStateError(
                "Execution snapshot does not pin the supplied Workflow definition"
            )
