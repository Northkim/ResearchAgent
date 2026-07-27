"""Immutable decisions returned by the Workflow Engine."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, TypeAlias

from ._immutability import freeze


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineDecision:
    workflow_run_id: str
    workflow_id: str
    workflow_version: str
    expected_run_version: int
    checkpoint_required: bool
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class StepReady(EngineDecision):
    step_id: str
    step_run_id: str
    attempt: int
    expected_step_version: int
    skill_ref: str
    resolved_inputs: Mapping[str, Any] = field(default_factory=dict)
    requires_ready_transition: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "resolved_inputs", freeze(self.resolved_inputs))


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowCompleted(EngineDecision):
    outputs: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "outputs", freeze(self.outputs))


@dataclass(frozen=True, slots=True, kw_only=True)
class WaitingApproval(EngineDecision):
    step_id: str
    step_run_id: str
    attempt: int
    expected_step_version: int
    approval_policy: str
    resolved_inputs: Mapping[str, Any] = field(default_factory=dict)
    requires_ready_transition: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "resolved_inputs", freeze(self.resolved_inputs))


@dataclass(frozen=True, slots=True, kw_only=True)
class RetryScheduled(EngineDecision):
    step_id: str
    step_run_id: str
    current_attempt: int
    next_attempt: int
    expected_step_version: int
    delay_seconds: float
    backoff: str
    error_code: str


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowFailed(EngineDecision):
    error_code: str
    message: str
    failed_step_id: str | None = None
    expected_step_version: int | None = None
    retry_exhausted: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalCompleted(EngineDecision):
    step_id: str
    step_run_id: str
    expected_step_version: int


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowCancelled(EngineDecision):
    error_code: str
    step_id: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class NoAction(EngineDecision):
    pass


EngineDecisionType: TypeAlias = (
    StepReady
    | WorkflowCompleted
    | WaitingApproval
    | RetryScheduled
    | WorkflowFailed
    | ApprovalCompleted
    | WorkflowCancelled
    | NoAction
)
