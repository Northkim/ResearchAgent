"""Workflow-step attempt entity and lifecycle rules."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..enums import StepRunStatus
from ..exceptions import DomainValidationError, InvalidStateTransition
from ._utils import freeze_value, require_aware, require_non_empty, utc_now

_STEP_RUN_TRANSITIONS: dict[StepRunStatus, frozenset[StepRunStatus]] = {
    StepRunStatus.CREATED: frozenset(
        {StepRunStatus.READY, StepRunStatus.SKIPPED, StepRunStatus.CANCELLED}
    ),
    StepRunStatus.READY: frozenset(
        {StepRunStatus.RUNNING, StepRunStatus.SKIPPED, StepRunStatus.CANCELLED}
    ),
    StepRunStatus.RUNNING: frozenset(
        {
            StepRunStatus.WAITING_APPROVAL,
            StepRunStatus.COMPLETED,
            StepRunStatus.FAILED,
            StepRunStatus.CANCELLED,
        }
    ),
    StepRunStatus.WAITING_APPROVAL: frozenset(
        {StepRunStatus.RUNNING, StepRunStatus.CANCELLED}
    ),
    StepRunStatus.COMPLETED: frozenset(),
    StepRunStatus.FAILED: frozenset(),
    StepRunStatus.SKIPPED: frozenset(),
    StepRunStatus.CANCELLED: frozenset(),
}


@dataclass(slots=True)
class StepRun:
    """One immutable-in-history attempt to execute a workflow step."""

    id: str
    workflow_run_id: str
    step_id: str
    attempt: int
    idempotency_key: str
    inputs: Mapping[str, Any] = field(default_factory=dict)
    status: StepRunStatus = StepRunStatus.CREATED
    outputs: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    row_version: int = 0
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def __post_init__(self) -> None:
        for value, name in (
            (self.id, "StepRun.id"),
            (self.workflow_run_id, "StepRun.workflow_run_id"),
            (self.step_id, "StepRun.step_id"),
            (self.idempotency_key, "StepRun.idempotency_key"),
        ):
            require_non_empty(value, name)
        if self.attempt <= 0:
            raise DomainValidationError("StepRun.attempt must be positive")
        require_aware(self.created_at, "StepRun.created_at")
        require_aware(self.updated_at, "StepRun.updated_at")
        self.inputs = freeze_value(self.inputs)
        self.outputs = dict(self.outputs)

    def transition_to(
        self,
        target: StepRunStatus,
        *,
        at: datetime | None = None,
        inputs: Mapping[str, Any] | None = None,
        outputs: Mapping[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        if target not in _STEP_RUN_TRANSITIONS[self.status]:
            raise InvalidStateTransition(
                "StepRun", self.id, self.status.value, target.value
            )
        if inputs is not None and target is not StepRunStatus.READY:
            raise DomainValidationError(
                "StepRun inputs can be assigned only when entering READY"
            )

        timestamp = at or utc_now()
        require_aware(timestamp, "StepRun transition timestamp")
        self.status = target
        self.updated_at = timestamp
        self.row_version += 1
        if target is StepRunStatus.RUNNING and self.started_at is None:
            self.started_at = timestamp
        if target.is_terminal:
            self.finished_at = timestamp
        if inputs is not None:
            self.inputs = freeze_value(inputs)
        if outputs is not None:
            self.outputs = dict(outputs)
        self.error_code = error_code if target is StepRunStatus.FAILED else None
