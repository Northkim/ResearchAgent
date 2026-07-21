"""Read models returned by application services."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from backend.domain.enums import (
    ApprovalRequestStatus,
    StepRunStatus,
    WorkflowRunStatus,
)
from backend.domain.models import ApprovalRequest
from backend.domain.models import Workflow
from backend.domain.services import ExecutionState
from backend.execution_events import ExecutionEvent, ExecutionEventType, EventSeverity


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class StepRunView:
    id: str
    step_id: str
    attempt: int
    status: StepRunStatus
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    error_code: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowRunView:
    id: str
    project_id: str
    workflow_id: str
    workflow_version: str
    actor_user_id: str
    agent_session_id: str
    status: WorkflowRunStatus
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    wait_reason: str | None
    error_code: str | None
    completed_steps: tuple[str, ...]
    checkpoint_count: int
    created_at: datetime
    updated_at: datetime
    steps: tuple[StepRunView, ...]

    @classmethod
    def from_execution(cls, execution: ExecutionState) -> WorkflowRunView:
        run = execution.workflow_run
        steps = tuple(
            StepRunView(
                id=step.id,
                step_id=step.step_id,
                attempt=step.attempt,
                status=step.status,
                inputs=_plain(step.inputs),
                outputs=_plain(step.outputs),
                error_code=step.error_code,
                created_at=step.created_at,
                updated_at=step.updated_at,
            )
            for step in sorted(
                execution.step_runs,
                key=lambda item: (
                    execution.workflow.steps.index(
                        execution.workflow.get_step(item.step_id)
                    ),
                    item.attempt,
                ),
            )
        )
        completed = tuple(
            step.id
            for step in execution.workflow.steps
            if execution.latest_step_run(step.id).status
            in {StepRunStatus.COMPLETED, StepRunStatus.SKIPPED}
        )
        return cls(
            id=run.id,
            project_id=run.project_id,
            workflow_id=run.workflow_id,
            workflow_version=run.workflow_version,
            actor_user_id=run.actor_user_id,
            agent_session_id=execution.agent_session.id,
            status=run.status,
            inputs=_plain(run.inputs),
            outputs=_plain(run.outputs),
            wait_reason=run.wait_reason,
            error_code=run.error_code,
            completed_steps=completed,
            checkpoint_count=len(execution.checkpoints),
            created_at=run.created_at,
            updated_at=run.updated_at,
            steps=steps,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalView:
    id: str
    project_id: str
    workflow_run_id: str
    step_run_id: str
    policy_key: str
    request_fingerprint: str
    prompt: str
    requested_action: dict[str, Any]
    requested_by: str
    permitted_approver_role: str
    requested_at: datetime
    expires_at: datetime | None
    status: ApprovalRequestStatus
    resolved_by: str | None
    resolved_at: datetime | None
    decision_reason: str | None

    @classmethod
    def from_approval(cls, approval: ApprovalRequest) -> ApprovalView:
        return cls(
            id=approval.id,
            project_id=approval.project_id,
            workflow_run_id=approval.workflow_run_id,
            step_run_id=approval.step_run_id,
            policy_key=approval.policy_key,
            request_fingerprint=approval.request_fingerprint,
            prompt=approval.prompt,
            requested_action=_plain(approval.requested_action),
            requested_by=approval.requested_by,
            permitted_approver_role=approval.permitted_approver_role,
            requested_at=approval.requested_at,
            expires_at=approval.expires_at,
            status=approval.status,
            resolved_by=approval.resolved_by,
            resolved_at=approval.resolved_at,
            decision_reason=approval.decision_reason,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalDecisionView:
    approval: ApprovalView
    workflow_run: WorkflowRunView


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowRunSummaryView:
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
    def from_execution(cls, execution: ExecutionState) -> WorkflowRunSummaryView:
        run = execution.workflow_run
        return cls(
            id=run.id,
            project_id=run.project_id,
            workflow_id=run.workflow_id,
            workflow_version=run.workflow_version,
            workflow_name=execution.workflow.name,
            status=run.status,
            wait_reason=run.wait_reason,
            error_code=run.error_code,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowRunPageView:
    runs: tuple[WorkflowRunSummaryView, ...]
    total: int
    offset: int
    limit: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalPageView:
    approvals: tuple[ApprovalView, ...]
    total: int
    offset: int
    limit: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionEventView:
    id: str
    sequence: int
    event_type: ExecutionEventType
    severity: EventSeverity
    payload: dict[str, Any]
    occurred_at: datetime
    agent_session_id: str | None
    step_run_id: str | None
    correlation_id: str | None
    causation_id: str | None

    @classmethod
    def from_event(cls, event: ExecutionEvent) -> ExecutionEventView:
        return cls(
            id=event.id,
            sequence=event.sequence,
            event_type=event.event_type,
            severity=event.severity,
            payload=event.payload.to_dict()["data"],
            occurred_at=event.occurred_at,
            agent_session_id=event.agent_session_id,
            step_run_id=event.step_run_id,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowStepDefinitionView:
    id: str
    kind: str
    needs: tuple[str, ...]
    uses: str | None
    input_mapping: dict[str, Any]
    timeout_seconds: int
    max_attempts: int
    approval_policy: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowDefinitionView:
    id: str
    version: str
    name: str
    schema_version: str
    input_schema: dict[str, Any]
    outputs: dict[str, Any]
    steps: tuple[WorkflowStepDefinitionView, ...]

    @classmethod
    def from_workflow(cls, workflow: Workflow) -> WorkflowDefinitionView:
        return cls(
            id=workflow.id,
            version=workflow.version,
            name=workflow.name,
            schema_version=workflow.schema_version,
            input_schema=_plain(workflow.input_schema),
            outputs=_plain(workflow.outputs),
            steps=tuple(
                WorkflowStepDefinitionView(
                    id=step.id,
                    kind=step.kind.value,
                    needs=step.needs,
                    uses=step.uses,
                    input_mapping=_plain(step.input_mapping),
                    timeout_seconds=step.timeout_seconds,
                    max_attempts=step.max_attempts,
                    approval_policy=step.approval_policy,
                )
                for step in workflow.steps
            ),
        )
