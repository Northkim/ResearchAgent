"""Shared persistence helpers kept inside the application boundary."""

from __future__ import annotations

from backend.domain.services import ExecutionState
from backend.persistence.ports import UnitOfWork

from ..errors import ApplicationNotFoundError
from ..views import WorkflowRunView


def load_execution(unit_of_work: UnitOfWork, workflow_run_id: str) -> ExecutionState:
    execution = unit_of_work.workflows.get(workflow_run_id)
    if execution is None:
        raise ApplicationNotFoundError(
            f"WorkflowRun {workflow_run_id} was not found"
        )
    execution.checkpoints.extend(unit_of_work.checkpoints.list(workflow_run_id))
    return execution


def load_run_view(unit_of_work: UnitOfWork, workflow_run_id: str) -> WorkflowRunView:
    return WorkflowRunView.from_execution(
        load_execution(unit_of_work, workflow_run_id)
    )
