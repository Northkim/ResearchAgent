"""Read-only HTTP DTOs for frontend discovery and monitoring."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.application.views import (
    ExecutionEventView,
    WorkflowDefinitionView,
    WorkflowRunPageView,
    WorkflowRunSummaryView,
)
from backend.domain.enums import WorkflowRunStatus
from backend.execution_events import EventSeverity, ExecutionEventType

from .common import StrictDTO


class WorkflowRunSummaryResponse(StrictDTO):
    id: str
    project_id: str
    workflow_id: str
    workflow_version: str
    workflow_name: str
    status: WorkflowRunStatus
    wait_reason: str | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_view(
        cls,
        view: WorkflowRunSummaryView,
    ) -> WorkflowRunSummaryResponse:
        return cls(**{field: getattr(view, field) for field in cls.model_fields})


class WorkflowRunPageResponse(StrictDTO):
    runs: list[WorkflowRunSummaryResponse]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_view(cls, view: WorkflowRunPageView) -> WorkflowRunPageResponse:
        return cls(
            runs=[WorkflowRunSummaryResponse.from_view(run) for run in view.runs],
            total=view.total,
            offset=view.offset,
            limit=view.limit,
        )


class ExecutionEventResponse(StrictDTO):
    id: str
    sequence: int
    type: ExecutionEventType
    severity: EventSeverity
    payload: dict[str, Any]
    timestamp: datetime
    agent_session_id: str | None
    step_run_id: str | None
    correlation_id: str | None
    causation_id: str | None

    @classmethod
    def from_view(cls, view: ExecutionEventView) -> ExecutionEventResponse:
        return cls(
            id=view.id,
            sequence=view.sequence,
            type=view.event_type,
            severity=view.severity,
            payload=view.payload,
            timestamp=view.occurred_at,
            agent_session_id=view.agent_session_id,
            step_run_id=view.step_run_id,
            correlation_id=view.correlation_id,
            causation_id=view.causation_id,
        )


class WorkflowStepDefinitionResponse(StrictDTO):
    id: str
    kind: str
    needs: list[str]
    uses: str | None
    input_mapping: dict[str, Any]
    timeout_seconds: int
    max_attempts: int
    approval_policy: str | None


class WorkflowDefinitionResponse(StrictDTO):
    id: str
    version: str
    name: str
    schema_version: str
    input_schema: dict[str, Any]
    outputs: dict[str, Any]
    steps: list[WorkflowStepDefinitionResponse]

    @classmethod
    def from_view(
        cls,
        view: WorkflowDefinitionView,
    ) -> WorkflowDefinitionResponse:
        return cls(
            id=view.id,
            version=view.version,
            name=view.name,
            schema_version=view.schema_version,
            input_schema=view.input_schema,
            outputs=view.outputs,
            steps=[
                WorkflowStepDefinitionResponse(
                    id=step.id,
                    kind=step.kind,
                    needs=list(step.needs),
                    uses=step.uses,
                    input_mapping=step.input_mapping,
                    timeout_seconds=step.timeout_seconds,
                    max_attempts=step.max_attempts,
                    approval_policy=step.approval_policy,
                )
                for step in view.steps
            ],
        )
