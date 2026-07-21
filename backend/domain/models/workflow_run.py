"""Workflow-run aggregate root and lifecycle rules."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..enums import WorkflowRunStatus
from ..exceptions import InvalidStateTransition
from ._utils import freeze_value, require_aware, require_non_empty, utc_now

_WORKFLOW_RUN_TRANSITIONS: dict[WorkflowRunStatus, frozenset[WorkflowRunStatus]] = {
    WorkflowRunStatus.CREATED: frozenset(
        {WorkflowRunStatus.INITIALIZING, WorkflowRunStatus.CANCELLING}
    ),
    WorkflowRunStatus.INITIALIZING: frozenset(
        {
            WorkflowRunStatus.RUNNING,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELLING,
        }
    ),
    WorkflowRunStatus.RUNNING: frozenset(
        {
            WorkflowRunStatus.WAITING_FOR_APPROVAL,
            WorkflowRunStatus.WAITING_FOR_INPUT,
            WorkflowRunStatus.RETRY_SCHEDULED,
            WorkflowRunStatus.COMPLETED,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELLING,
        }
    ),
    WorkflowRunStatus.WAITING_FOR_APPROVAL: frozenset(
        {WorkflowRunStatus.RUNNING, WorkflowRunStatus.CANCELLING}
    ),
    WorkflowRunStatus.WAITING_FOR_INPUT: frozenset(
        {WorkflowRunStatus.RUNNING, WorkflowRunStatus.CANCELLING}
    ),
    WorkflowRunStatus.RETRY_SCHEDULED: frozenset(
        {WorkflowRunStatus.RUNNING, WorkflowRunStatus.CANCELLING}
    ),
    WorkflowRunStatus.CANCELLING: frozenset({WorkflowRunStatus.CANCELLED}),
    WorkflowRunStatus.COMPLETED: frozenset(),
    WorkflowRunStatus.FAILED: frozenset(),
    WorkflowRunStatus.CANCELLED: frozenset(),
}


@dataclass(slots=True)
class WorkflowRun:
    """Externally visible execution aggregate with optimistic versioning."""

    id: str
    project_id: str
    workflow_id: str
    workflow_version: str
    actor_user_id: str
    idempotency_key: str
    inputs: Mapping[str, Any]
    status: WorkflowRunStatus = WorkflowRunStatus.CREATED
    outputs: dict[str, Any] = field(default_factory=dict)
    wait_reason: str | None = None
    error_code: str | None = None
    row_version: int = 0
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        for value, name in (
            (self.id, "WorkflowRun.id"),
            (self.project_id, "WorkflowRun.project_id"),
            (self.workflow_id, "WorkflowRun.workflow_id"),
            (self.workflow_version, "WorkflowRun.workflow_version"),
            (self.actor_user_id, "WorkflowRun.actor_user_id"),
            (self.idempotency_key, "WorkflowRun.idempotency_key"),
        ):
            require_non_empty(value, name)
        require_aware(self.created_at, "WorkflowRun.created_at")
        require_aware(self.updated_at, "WorkflowRun.updated_at")
        self.inputs = freeze_value(self.inputs)
        self.outputs = dict(self.outputs)

    def transition_to(
        self,
        target: WorkflowRunStatus,
        *,
        at: datetime | None = None,
        wait_reason: str | None = None,
        error_code: str | None = None,
    ) -> None:
        if target not in _WORKFLOW_RUN_TRANSITIONS[self.status]:
            raise InvalidStateTransition(
                "WorkflowRun", self.id, self.status.value, target.value
            )

        timestamp = at or utc_now()
        require_aware(timestamp, "WorkflowRun transition timestamp")
        self.status = target
        self.updated_at = timestamp
        self.row_version += 1
        self.wait_reason = wait_reason if target in {
            WorkflowRunStatus.WAITING_FOR_APPROVAL,
            WorkflowRunStatus.WAITING_FOR_INPUT,
            WorkflowRunStatus.RETRY_SCHEDULED,
        } else None
        self.error_code = error_code if target is WorkflowRunStatus.FAILED else None

    def set_outputs(self, outputs: Mapping[str, Any]) -> None:
        self.outputs = dict(outputs)
