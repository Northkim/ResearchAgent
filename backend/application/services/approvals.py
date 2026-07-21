"""Human approval decision use case."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from backend.agent_runtime.runtime import AgentRuntimeError
from backend.domain.enums import ApprovalRequestStatus, StepRunStatus, WorkflowRunStatus
from backend.domain.exceptions import DomainError
from backend.domain.models._utils import utc_now
from backend.persistence.ports import PersistenceError, UnitOfWork
from backend.workflow_engine.exceptions import WorkflowEngineError
from backend.workflow_engine.models import ApprovalOutcome

from ..commands import ApprovalDecision, ApprovalDecisionCommand
from ..errors import (
    ApplicationConflictError,
    ApplicationNotFoundError,
    ApplicationValidationError,
)
from ..execution import ExecutionDispatcher, ExecutionRequest
from ..views import ApprovalDecisionView, ApprovalView, WorkflowRunView
from ._shared import load_execution, load_run_view


class ApprovalDecisionService:
    """Resolve an approval and the waiting runtime in one UnitOfWork."""

    def __init__(
        self,
        *,
        unit_of_work: UnitOfWork,
        dispatcher: ExecutionDispatcher,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.uow = unit_of_work
        self.dispatcher = dispatcher
        self.clock = clock

    async def execute(
        self,
        command: ApprovalDecisionCommand,
    ) -> ApprovalDecisionView:
        approval = self.uow.approvals.get(command.approval_id)
        if approval is None:
            raise ApplicationNotFoundError(
                f"ApprovalRequest {command.approval_id} was not found"
            )

        if (
            approval.status is ApprovalRequestStatus.PENDING
            and approval.expires_at is not None
            and self.clock() >= approval.expires_at
        ):
            return await self._expire_and_cancel(approval)

        target = (
            ApprovalRequestStatus.APPROVED
            if command.decision is ApprovalDecision.APPROVE
            else ApprovalRequestStatus.REJECTED
        )
        if approval.status.is_terminal:
            if (
                approval.status is target
                and approval.decision_idempotency_key
                == command.decision_idempotency_key
            ):
                return ApprovalDecisionView(
                    approval=ApprovalView.from_approval(approval),
                    workflow_run=load_run_view(
                        self.uow,
                        approval.workflow_run_id,
                    ),
                )
            raise ApplicationConflictError(
                f"ApprovalRequest {approval.id} is already {approval.status.value}"
            )

        execution = load_execution(self.uow, approval.workflow_run_id)
        self._verify_waiting_execution(execution, approval)
        expected_version = self.uow.approvals.get_version(approval.id)
        if expected_version is None:
            raise ApplicationConflictError(
                f"ApprovalRequest {approval.id} has no persistence version"
            )

        try:
            if command.decision is ApprovalDecision.APPROVE:
                if command.current_fingerprint is None:
                    raise ApplicationValidationError(
                        "current_fingerprint is required for approval"
                    )
                approval.approve(
                    resolved_by=command.resolved_by,
                    decision_idempotency_key=command.decision_idempotency_key,
                    current_fingerprint=command.current_fingerprint,
                    at=self.clock(),
                    reason=command.reason,
                    metadata=command.metadata,
                )
                outcome = ApprovalOutcome.APPROVED
            else:
                approval.reject(
                    resolved_by=command.resolved_by,
                    decision_idempotency_key=command.decision_idempotency_key,
                    at=self.clock(),
                    reason=command.reason,
                    metadata=command.metadata,
                )
                outcome = ApprovalOutcome.REJECTED

            self.uow.approvals.save(
                approval,
                expected_version=expected_version,
            )
            # AgentRuntime commits the staged approval together with the run,
            # step, checkpoint, and memory changes it makes for this outcome.
            await self.dispatcher.submit(
                ExecutionRequest(
                    workflow_run_id=approval.workflow_run_id,
                    approval_outcome=outcome,
                )
            )
            return ApprovalDecisionView(
                approval=ApprovalView.from_approval(approval),
                workflow_run=load_run_view(
                    self.uow,
                    approval.workflow_run_id,
                ),
            )
        except ApplicationValidationError:
            self.uow.rollback()
            raise
        except DomainError as error:
            self.uow.rollback()
            raise ApplicationValidationError(str(error)) from error
        except (WorkflowEngineError, AgentRuntimeError, PersistenceError) as error:
            self.uow.rollback()
            raise ApplicationConflictError(str(error)) from error
        except Exception:
            self.uow.rollback()
            raise

    async def _expire_and_cancel(self, approval) -> ApprovalDecisionView:
        execution = load_execution(self.uow, approval.workflow_run_id)
        self._verify_waiting_execution(execution, approval)
        expected_version = self.uow.approvals.get_version(approval.id)
        if expected_version is None:
            raise ApplicationConflictError(
                f"ApprovalRequest {approval.id} has no persistence version"
            )
        try:
            approval.expire(
                at=self.clock(),
                reason="Approval request expired",
                metadata={"policy": "cancel"},
            )
            self.uow.approvals.save(
                approval,
                expected_version=expected_version,
            )
            await self.dispatcher.submit(
                ExecutionRequest(
                    workflow_run_id=approval.workflow_run_id,
                    approval_outcome=ApprovalOutcome.EXPIRED,
                )
            )
            return ApprovalDecisionView(
                approval=ApprovalView.from_approval(approval),
                workflow_run=load_run_view(
                    self.uow,
                    approval.workflow_run_id,
                ),
            )
        except (DomainError, WorkflowEngineError) as error:
            self.uow.rollback()
            raise ApplicationValidationError(str(error)) from error
        except (AgentRuntimeError, PersistenceError) as error:
            self.uow.rollback()
            raise ApplicationConflictError(str(error)) from error
        except Exception:
            self.uow.rollback()
            raise

    @staticmethod
    def _verify_waiting_execution(execution, approval) -> None:
        run = execution.workflow_run
        if run.project_id != approval.project_id:
            raise ApplicationConflictError(
                "ApprovalRequest project does not match its WorkflowRun"
            )
        if run.status is not WorkflowRunStatus.WAITING_FOR_APPROVAL:
            raise ApplicationConflictError(
                f"WorkflowRun {run.id} is not waiting for approval"
            )
        waiting = [
            step
            for step in execution.current_step_runs()
            if step.status is StepRunStatus.WAITING_APPROVAL
        ]
        if len(waiting) != 1 or waiting[0].id != approval.step_run_id:
            raise ApplicationConflictError(
                "ApprovalRequest does not identify the current waiting step"
            )
