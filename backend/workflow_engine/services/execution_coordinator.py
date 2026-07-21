"""Application-style integration between Engine decisions and domain transitions."""

from __future__ import annotations

from backend.domain.enums import StepRunStatus, WorkflowRunStatus
from backend.domain.models import Checkpoint
from backend.domain.services import ExecutionCoordinator, ExecutionState

from ..exceptions import StaleDecisionError, WorkflowStateError
from ..models import (
    ApprovalCompleted,
    ApprovalOutcome,
    EngineDecision,
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
from .workflow_engine import WorkflowEngine


class WorkflowExecutionCoordinator:
    """Apply pure Engine decisions using the domain mutation coordinator."""

    def __init__(
        self,
        *,
        engine: WorkflowEngine | None = None,
        domain_coordinator: ExecutionCoordinator | None = None,
    ) -> None:
        self.engine = engine or WorkflowEngine()
        self.domain = domain_coordinator or ExecutionCoordinator()

    def decide(self, execution: ExecutionState) -> EngineDecisionType:
        return self.engine.next_decision(
            WorkflowDefinition.from_domain(execution.workflow),
            ExecutionSnapshot.from_execution(execution),
        )

    def evaluate_failure(
        self,
        execution: ExecutionState,
        *,
        step_id: str,
        retryable: bool,
        error_code: str,
        message: str = "",
    ) -> RetryScheduled | WorkflowFailed:
        return self.engine.evaluate_failure(
            WorkflowDefinition.from_domain(execution.workflow),
            ExecutionSnapshot.from_execution(execution),
            step_id=step_id,
            retryable=retryable,
            error_code=error_code,
            message=message,
        )

    def apply_decision(
        self,
        execution: ExecutionState,
        decision: EngineDecisionType,
    ) -> Checkpoint | None:
        self._validate_decision(execution, decision)

        if isinstance(decision, StepReady):
            if decision.requires_ready_transition:
                return self.domain.mark_step_ready(
                    execution,
                    step_id=decision.step_id,
                    inputs=decision.resolved_inputs,
                )
            return None

        if isinstance(decision, WaitingApproval):
            if decision.requires_ready_transition:
                self.domain.mark_step_ready(
                    execution, step_id=decision.step_id, checkpoint=False
                )
            self.domain.update_step_state(
                execution,
                step_id=decision.step_id,
                target_status=StepRunStatus.RUNNING,
            )
            return self.domain.update_step_state(
                execution,
                step_id=decision.step_id,
                target_status=StepRunStatus.WAITING_APPROVAL,
            )

        if isinstance(decision, RetryScheduled):
            return self.domain.update_step_state(
                execution,
                step_id=decision.step_id,
                target_status=StepRunStatus.FAILED,
                error_code=decision.error_code,
                retryable=True,
            )

        if isinstance(decision, WorkflowCompleted):
            return self.domain.complete_workflow(
                execution, outputs=decision.outputs
            )

        if isinstance(decision, WorkflowFailed):
            if decision.failed_step_id is not None:
                failed_step = execution.latest_step_run(decision.failed_step_id)
                if failed_step.status is StepRunStatus.RUNNING:
                    return self.domain.update_step_state(
                        execution,
                        step_id=decision.failed_step_id,
                        target_status=StepRunStatus.FAILED,
                        error_code=decision.error_code,
                        retryable=False,
                    )
            return self.domain.fail_execution(
                execution, error_code=decision.error_code
            )

        if isinstance(decision, ApprovalCompleted):
            return self.domain.update_step_state(
                execution,
                step_id=decision.step_id,
                target_status=StepRunStatus.COMPLETED,
            )

        if isinstance(decision, WorkflowCancelled):
            return self.domain.cancel_execution(execution)

        if isinstance(decision, NoAction):
            return None

        raise WorkflowStateError(
            f"Unsupported Engine decision {type(decision).__name__}"
        )

    def resolve_approval(
        self,
        execution: ExecutionState,
        checkpoint: Checkpoint,
        *,
        outcome: ApprovalOutcome,
    ) -> ApprovalCompleted | WorkflowCancelled:
        wait_reason = execution.workflow_run.wait_reason
        if not wait_reason or not wait_reason.startswith("approval:"):
            raise WorkflowStateError("Execution is not waiting on an approval step")
        step_id = wait_reason.removeprefix("approval:")
        definition = WorkflowDefinition.from_domain(execution.workflow)

        if outcome is ApprovalOutcome.APPROVED:
            self.domain.resume_from_checkpoint(execution, checkpoint)
            decision = self.engine.evaluate_approval(
                definition,
                ExecutionSnapshot.from_execution(execution),
                step_id=step_id,
                outcome=outcome,
            )
        else:
            decision = self.engine.evaluate_approval(
                definition,
                ExecutionSnapshot.from_execution(execution),
                step_id=step_id,
                outcome=outcome,
            )
        self.apply_decision(execution, decision)
        return decision

    def resume_from_checkpoint(
        self,
        execution: ExecutionState,
        checkpoint: Checkpoint,
    ) -> EngineDecisionType:
        if execution.workflow_run.status is WorkflowRunStatus.WAITING_FOR_APPROVAL:
            raise WorkflowStateError(
                "Approval checkpoints require resolve_approval with a typed outcome"
            )
        self.domain.resume_from_checkpoint(execution, checkpoint)
        return self.decide(execution)

    @staticmethod
    def _validate_decision(
        execution: ExecutionState,
        decision: EngineDecision,
    ) -> None:
        run = execution.workflow_run
        if (
            decision.workflow_run_id != run.id
            or decision.workflow_id != run.workflow_id
            or decision.workflow_version != run.workflow_version
        ):
            raise StaleDecisionError("Decision belongs to another workflow run/version")
        if decision.expected_run_version != run.row_version:
            raise StaleDecisionError(
                f"Decision expected run version {decision.expected_run_version}; "
                f"current version is {run.row_version}"
            )

        step_id = getattr(decision, "step_id", None)
        expected_step_version = getattr(decision, "expected_step_version", None)
        if step_id is not None and expected_step_version is not None:
            current_step = execution.latest_step_run(step_id)
            if current_step.row_version != expected_step_version:
                raise StaleDecisionError(
                    f"Decision expected step {step_id} version "
                    f"{expected_step_version}; current version is "
                    f"{current_step.row_version}"
                )
