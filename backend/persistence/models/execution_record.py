"""Immutable persistence representation and Domain reconstitution mapping."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.domain.enums import AgentSessionStatus, StepRunStatus, WorkflowRunStatus
from backend.domain.models import (
    AgentSession,
    Checkpoint,
    StepRun,
    Workflow,
    WorkflowRun,
)
from backend.domain.services import ExecutionState

from ._immutability import freeze_json, thaw_json


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowRunRecord:
    id: str
    project_id: str
    workflow_id: str
    workflow_version: str
    actor_user_id: str
    idempotency_key: str
    inputs: Mapping[str, Any]
    status: WorkflowRunStatus
    outputs: Mapping[str, Any]
    wait_reason: str | None
    error_code: str | None
    row_version: int
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "inputs", freeze_json(self.inputs, path="run.inputs"))
        object.__setattr__(self, "outputs", freeze_json(self.outputs, path="run.outputs"))

    @classmethod
    def from_domain(cls, run: WorkflowRun) -> WorkflowRunRecord:
        return cls(
            id=run.id,
            project_id=run.project_id,
            workflow_id=run.workflow_id,
            workflow_version=run.workflow_version,
            actor_user_id=run.actor_user_id,
            idempotency_key=run.idempotency_key,
            inputs=run.inputs,
            status=run.status,
            outputs=run.outputs,
            wait_reason=run.wait_reason,
            error_code=run.error_code,
            row_version=run.row_version,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    def to_domain(self) -> WorkflowRun:
        return WorkflowRun(
            id=self.id,
            project_id=self.project_id,
            workflow_id=self.workflow_id,
            workflow_version=self.workflow_version,
            actor_user_id=self.actor_user_id,
            idempotency_key=self.idempotency_key,
            inputs=thaw_json(self.inputs),
            status=self.status,
            outputs=thaw_json(self.outputs),
            wait_reason=self.wait_reason,
            error_code=self.error_code,
            row_version=self.row_version,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class AgentSessionRecord:
    id: str
    project_id: str
    workflow_run_id: str
    agent_profile_ref: str
    role: str
    status: AgentSessionStatus
    state: Mapping[str, Any]
    row_version: int
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", freeze_json(self.state, path="agent.state"))

    @classmethod
    def from_domain(cls, session: AgentSession) -> AgentSessionRecord:
        return cls(
            id=session.id,
            project_id=session.project_id,
            workflow_run_id=session.workflow_run_id,
            agent_profile_ref=session.agent_profile_ref,
            role=session.role,
            status=session.status,
            state=session.state,
            row_version=session.row_version,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    def to_domain(self) -> AgentSession:
        return AgentSession(
            id=self.id,
            project_id=self.project_id,
            workflow_run_id=self.workflow_run_id,
            agent_profile_ref=self.agent_profile_ref,
            role=self.role,
            status=self.status,
            state=thaw_json(self.state),
            row_version=self.row_version,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class StepRunRecord:
    id: str
    workflow_run_id: str
    step_id: str
    attempt: int
    idempotency_key: str
    inputs: Mapping[str, Any]
    status: StepRunStatus
    outputs: Mapping[str, Any]
    error_code: str | None
    row_version: int
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "inputs", freeze_json(self.inputs, path="step.inputs"))
        object.__setattr__(self, "outputs", freeze_json(self.outputs, path="step.outputs"))

    @classmethod
    def from_domain(cls, step: StepRun) -> StepRunRecord:
        return cls(
            id=step.id,
            workflow_run_id=step.workflow_run_id,
            step_id=step.step_id,
            attempt=step.attempt,
            idempotency_key=step.idempotency_key,
            inputs=step.inputs,
            status=step.status,
            outputs=step.outputs,
            error_code=step.error_code,
            row_version=step.row_version,
            created_at=step.created_at,
            updated_at=step.updated_at,
            started_at=step.started_at,
            finished_at=step.finished_at,
        )

    def to_domain(self) -> StepRun:
        return StepRun(
            id=self.id,
            workflow_run_id=self.workflow_run_id,
            step_id=self.step_id,
            attempt=self.attempt,
            idempotency_key=self.idempotency_key,
            inputs=thaw_json(self.inputs),
            status=self.status,
            outputs=thaw_json(self.outputs),
            error_code=self.error_code,
            row_version=self.row_version,
            created_at=self.created_at,
            updated_at=self.updated_at,
            started_at=self.started_at,
            finished_at=self.finished_at,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowExecutionRecord:
    """One immutable persisted revision of an execution aggregate."""

    persistence_version: int
    workflow: Workflow
    workflow_run: WorkflowRunRecord
    agent_session: AgentSessionRecord
    step_runs: tuple[StepRunRecord, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.persistence_version <= 0:
            raise ValueError("Persistence version must be positive")
        object.__setattr__(self, "step_runs", tuple(self.step_runs))

    @classmethod
    def from_execution(
        cls,
        execution: ExecutionState,
        *,
        persistence_version: int,
    ) -> WorkflowExecutionRecord:
        return cls(
            persistence_version=persistence_version,
            workflow=execution.workflow,
            workflow_run=WorkflowRunRecord.from_domain(execution.workflow_run),
            agent_session=AgentSessionRecord.from_domain(execution.agent_session),
            step_runs=tuple(StepRunRecord.from_domain(step) for step in execution.step_runs),
        )

    def to_execution(
        self,
        *,
        checkpoints: Sequence[Checkpoint] = (),
    ) -> ExecutionState:
        return ExecutionState(
            workflow=self.workflow,
            workflow_run=self.workflow_run.to_domain(),
            agent_session=self.agent_session.to_domain(),
            step_runs=[record.to_domain() for record in self.step_runs],
            checkpoints=list(checkpoints),
        )
