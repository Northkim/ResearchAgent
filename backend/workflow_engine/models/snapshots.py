"""Read-only execution snapshots supplied to the Workflow Engine."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from backend.domain.enums import AgentSessionStatus, StepRunStatus, WorkflowRunStatus
from backend.domain.services import ExecutionState

from ..exceptions import WorkflowStateError
from ._immutability import freeze


@dataclass(frozen=True, slots=True)
class StepRunSnapshot:
    id: str
    step_id: str
    attempt: int
    status: StepRunStatus
    row_version: int
    inputs: Mapping[str, Any] = field(default_factory=dict)
    outputs: Mapping[str, Any] = field(default_factory=dict)
    error_code: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "inputs", freeze(self.inputs))
        object.__setattr__(self, "outputs", freeze(self.outputs))


@dataclass(frozen=True, slots=True)
class ExecutionSnapshot:
    workflow_run_id: str
    workflow_id: str
    workflow_version: str
    run_status: WorkflowRunStatus
    run_row_version: int
    workflow_inputs: Mapping[str, Any]
    agent_session_id: str
    agent_status: AgentSessionStatus
    agent_row_version: int
    step_runs: tuple[StepRunSnapshot, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "workflow_inputs", freeze(self.workflow_inputs))
        object.__setattr__(self, "step_runs", tuple(self.step_runs))

    @classmethod
    def from_execution(cls, execution: ExecutionState) -> ExecutionSnapshot:
        return cls(
            workflow_run_id=execution.workflow_run.id,
            workflow_id=execution.workflow_run.workflow_id,
            workflow_version=execution.workflow_run.workflow_version,
            run_status=execution.workflow_run.status,
            run_row_version=execution.workflow_run.row_version,
            workflow_inputs=execution.workflow_run.inputs,
            agent_session_id=execution.agent_session.id,
            agent_status=execution.agent_session.status,
            agent_row_version=execution.agent_session.row_version,
            step_runs=tuple(
                StepRunSnapshot(
                    id=step_run.id,
                    step_id=step_run.step_id,
                    attempt=step_run.attempt,
                    status=step_run.status,
                    row_version=step_run.row_version,
                    inputs=step_run.inputs,
                    outputs=step_run.outputs,
                    error_code=step_run.error_code,
                )
                for step_run in execution.step_runs
            ),
        )

    def latest_attempts(self) -> Mapping[str, StepRunSnapshot]:
        latest: dict[str, StepRunSnapshot] = {}
        seen_attempts: set[tuple[str, int]] = set()
        for step_run in self.step_runs:
            key = (step_run.step_id, step_run.attempt)
            if key in seen_attempts:
                raise WorkflowStateError(
                    f"Duplicate attempt {step_run.attempt} for step {step_run.step_id}"
                )
            seen_attempts.add(key)
            previous = latest.get(step_run.step_id)
            if previous is None or step_run.attempt > previous.attempt:
                latest[step_run.step_id] = step_run
        return freeze(latest)
