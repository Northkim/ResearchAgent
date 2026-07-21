"""Immutable, redaction-safe records for observable execution history."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from backend.domain.exceptions import DomainValidationError

from ._immutability import freeze_json, thaw_json


class ExecutionEventType(str, Enum):
    """Stable v1 event taxonomy for workflow execution history."""

    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    STEP_STARTED = "STEP_STARTED"
    SKILL_EXECUTED = "SKILL_EXECUTED"
    CHECKPOINT_CREATED = "CHECKPOINT_CREATED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"


class EventSeverity(str, Enum):
    """Provider-neutral severity retained with each event."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


def _require_non_empty(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise DomainValidationError(f"{field_name} must be a non-empty string")


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DomainValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class EventPayload:
    """Versioned JSON-compatible payload crossing the event-storage port."""

    data: Mapping[str, Any] = field(default_factory=dict)
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version <= 0:
            raise DomainValidationError("EventPayload.schema_version must be positive")
        try:
            frozen = freeze_json(self.data, path="EventPayload.data")
        except ValueError as error:
            raise DomainValidationError(str(error)) from error
        if not isinstance(frozen, Mapping):
            raise DomainValidationError("EventPayload.data must be an object")
        object.__setattr__(self, "data", frozen)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "data": thaw_json(self.data),
        }


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    """One immutable event in a project-scoped workflow-run stream."""

    id: str
    project_id: str
    workflow_run_id: str
    sequence: int
    event_type: ExecutionEventType
    payload: EventPayload
    request_id: str
    occurred_at: datetime
    severity: EventSeverity = EventSeverity.INFO
    agent_session_id: str | None = None
    step_run_id: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None

    def __post_init__(self) -> None:
        for value, name in (
            (self.id, "ExecutionEvent.id"),
            (self.project_id, "ExecutionEvent.project_id"),
            (self.workflow_run_id, "ExecutionEvent.workflow_run_id"),
            (self.request_id, "ExecutionEvent.request_id"),
        ):
            _require_non_empty(value, name)
        for value, name in (
            (self.agent_session_id, "ExecutionEvent.agent_session_id"),
            (self.step_run_id, "ExecutionEvent.step_run_id"),
            (self.correlation_id, "ExecutionEvent.correlation_id"),
            (self.causation_id, "ExecutionEvent.causation_id"),
        ):
            if value is not None:
                _require_non_empty(value, name)
        if self.sequence <= 0:
            raise DomainValidationError("ExecutionEvent.sequence must be positive")
        _require_aware(self.occurred_at, "ExecutionEvent.occurred_at")
