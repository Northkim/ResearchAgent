"""Input contracts accepted by application services.

These dataclasses deliberately contain no FastAPI or Pydantic types. HTTP,
worker, and CLI adapters may all construct the same commands.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from backend.domain.enums import WorkflowStepKind


@dataclass(frozen=True, slots=True, kw_only=True)
class StepSpec:
    id: str
    kind: WorkflowStepKind
    needs: tuple[str, ...] = ()
    uses: str | None = None
    input_mapping: Mapping[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    max_attempts: int = 1
    retry_backoff: str = "exponential"
    retry_initial_seconds: float = 1.0
    retry_max_seconds: float = 30.0
    checkpoint_policy: str = "after_success"
    approval_policy: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "needs", tuple(self.needs))


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkflowSpec:
    id: str
    version: str
    name: str
    steps: tuple[StepSpec, ...]
    schema_version: str = "reagent/v1alpha1"
    input_schema: Mapping[str, Any] = field(default_factory=dict)
    outputs: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "steps", tuple(self.steps))


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateWorkflowRunCommand:
    project_id: str
    actor_user_id: str
    idempotency_key: str
    agent_profile_ref: str
    workflow: WorkflowSpec
    inputs: Mapping[str, Any] = field(default_factory=dict)


class ApprovalDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalDecisionCommand:
    approval_id: str
    decision: ApprovalDecision
    resolved_by: str
    decision_idempotency_key: str
    current_fingerprint: str | None = None
    reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
