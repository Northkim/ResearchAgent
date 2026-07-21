"""Read-only product queries through frozen persistence abstractions."""

from __future__ import annotations

from backend.domain.enums import ApprovalRequestStatus, WorkflowRunStatus
from backend.persistence.ports import UnitOfWork

from ..errors import ApplicationValidationError
from ..views import (
    ApprovalPageView,
    ApprovalView,
    ExecutionEventView,
    WorkflowDefinitionView,
    WorkflowRunPageView,
    WorkflowRunSummaryView,
)
from ._shared import load_execution


def _validate_page(offset: int, limit: int) -> None:
    if offset < 0:
        raise ApplicationValidationError("offset cannot be negative")
    if limit <= 0 or limit > 100:
        raise ApplicationValidationError("limit must be between 1 and 100")


class ListWorkflowRunsService:
    def __init__(self, *, unit_of_work: UnitOfWork) -> None:
        self.uow = unit_of_work

    def execute(
        self,
        *,
        status: WorkflowRunStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> WorkflowRunPageView:
        _validate_page(offset, limit)
        executions = self.uow.workflows.list_runs(
            status=status,
            offset=offset,
            limit=limit,
        )
        return WorkflowRunPageView(
            runs=tuple(
                WorkflowRunSummaryView.from_execution(execution)
                for execution in executions
            ),
            total=self.uow.workflows.count_runs(status=status),
            offset=offset,
            limit=limit,
        )


class ListExecutionEventsService:
    def __init__(self, *, unit_of_work: UnitOfWork) -> None:
        self.uow = unit_of_work

    def execute(self, workflow_run_id: str) -> tuple[ExecutionEventView, ...]:
        execution = load_execution(self.uow, workflow_run_id)
        return tuple(
            ExecutionEventView.from_event(event)
            for event in self.uow.events.list_for_run(
                execution.workflow_run.project_id,
                execution.workflow_run.id,
            )
        )


class ListApprovalsService:
    def __init__(self, *, unit_of_work: UnitOfWork) -> None:
        self.uow = unit_of_work

    def execute(
        self,
        *,
        status: ApprovalRequestStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> ApprovalPageView:
        _validate_page(offset, limit)
        approvals = self.uow.approvals.list_requests(
            status=status,
            offset=offset,
            limit=limit,
        )
        return ApprovalPageView(
            approvals=tuple(ApprovalView.from_approval(item) for item in approvals),
            total=self.uow.approvals.count_requests(status=status),
            offset=offset,
            limit=limit,
        )


class ListWorkflowsService:
    def __init__(self, *, unit_of_work: UnitOfWork) -> None:
        self.uow = unit_of_work

    def execute(self) -> tuple[WorkflowDefinitionView, ...]:
        return tuple(
            WorkflowDefinitionView.from_workflow(workflow)
            for workflow in self.uow.workflows.list_definitions()
        )
