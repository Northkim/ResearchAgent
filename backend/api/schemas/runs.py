"""Workflow-run HTTP DTOs and adapter mapping."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from backend.application.commands import (
    CreateCatalogWorkflowRunCommand,
    CreateWorkflowRunCommand,
    StepSpec,
    WorkflowSpec,
)
from backend.application.views import WorkflowRunView
from backend.domain.enums import StepRunStatus, WorkflowRunStatus, WorkflowStepKind

from .common import StrictDTO


class WorkflowStepRequest(StrictDTO):
    id: str = Field(min_length=1)
    kind: WorkflowStepKind
    needs: list[str] = Field(default_factory=list)
    uses: str | None = None
    input_mapping: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=300, gt=0)
    max_attempts: int = Field(default=1, gt=0)
    retry_backoff: Literal["fixed", "linear", "exponential"] = "exponential"
    retry_initial_seconds: float = Field(default=1.0, ge=0)
    retry_max_seconds: float = Field(default=30.0, ge=0)
    checkpoint_policy: Literal["after_success"] = "after_success"
    approval_policy: str | None = None

    def to_spec(self) -> StepSpec:
        return StepSpec(
            id=self.id,
            kind=self.kind,
            needs=tuple(self.needs),
            uses=self.uses,
            input_mapping=self.input_mapping,
            timeout_seconds=self.timeout_seconds,
            max_attempts=self.max_attempts,
            retry_backoff=self.retry_backoff,
            retry_initial_seconds=self.retry_initial_seconds,
            retry_max_seconds=self.retry_max_seconds,
            checkpoint_policy=self.checkpoint_policy,
            approval_policy=self.approval_policy,
        )


class WorkflowRequest(StrictDTO):
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    name: str = Field(min_length=1)
    schema_version: Literal["reagent/v1alpha1"] = "reagent/v1alpha1"
    input_schema: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, str] = Field(default_factory=dict)
    steps: list[WorkflowStepRequest] = Field(min_length=1)

    def to_spec(self) -> WorkflowSpec:
        return WorkflowSpec(
            id=self.id,
            version=self.version,
            name=self.name,
            schema_version=self.schema_version,
            input_schema=self.input_schema,
            outputs=self.outputs,
            steps=tuple(step.to_spec() for step in self.steps),
        )


class CreateRunRequest(StrictDTO):
    project_id: str = Field(min_length=1)
    actor_user_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    agent_profile_ref: str = Field(min_length=1)
    workflow: WorkflowRequest
    inputs: dict[str, Any] = Field(default_factory=dict)

    def to_command(self) -> CreateWorkflowRunCommand:
        return CreateWorkflowRunCommand(
            project_id=self.project_id,
            actor_user_id=self.actor_user_id,
            idempotency_key=self.idempotency_key,
            agent_profile_ref=self.agent_profile_ref,
            workflow=self.workflow.to_spec(),
            inputs=self.inputs,
        )


class CreateCatalogRunRequest(StrictDTO):
    project_id: str = Field(min_length=1)
    actor_user_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    agent_profile_ref: str = Field(min_length=1)
    workflow_id: str = Field(min_length=1)
    workflow_version: str = Field(min_length=1)
    inputs: dict[str, Any] = Field(default_factory=dict)

    def to_command(self) -> CreateCatalogWorkflowRunCommand:
        return CreateCatalogWorkflowRunCommand(
            project_id=self.project_id,
            actor_user_id=self.actor_user_id,
            idempotency_key=self.idempotency_key,
            agent_profile_ref=self.agent_profile_ref,
            workflow_id=self.workflow_id,
            workflow_version=self.workflow_version,
            inputs=self.inputs,
        )


class StepRunResponse(StrictDTO):
    id: str
    step_id: str
    attempt: int
    status: StepRunStatus
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    error_code: str | None
    created_at: datetime
    updated_at: datetime


class WorkflowRunResponse(StrictDTO):
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
    completed_steps: list[str]
    checkpoint_count: int
    created_at: datetime
    updated_at: datetime
    steps: list[StepRunResponse]

    @classmethod
    def from_view(cls, view: WorkflowRunView) -> WorkflowRunResponse:
        return cls(
            id=view.id,
            project_id=view.project_id,
            workflow_id=view.workflow_id,
            workflow_version=view.workflow_version,
            actor_user_id=view.actor_user_id,
            agent_session_id=view.agent_session_id,
            status=view.status,
            inputs=view.inputs,
            outputs=view.outputs,
            wait_reason=view.wait_reason,
            error_code=view.error_code,
            completed_steps=list(view.completed_steps),
            checkpoint_count=view.checkpoint_count,
            created_at=view.created_at,
            updated_at=view.updated_at,
            steps=[
                StepRunResponse(
                    id=step.id,
                    step_id=step.step_id,
                    attempt=step.attempt,
                    status=step.status,
                    inputs=step.inputs,
                    outputs=step.outputs,
                    error_code=step.error_code,
                    created_at=step.created_at,
                    updated_at=step.updated_at,
                )
                for step in view.steps
            ],
        )
