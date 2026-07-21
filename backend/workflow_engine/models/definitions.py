"""Immutable versioned definitions consumed by the Workflow Engine."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from backend.domain.enums import WorkflowStepKind
from backend.domain.models import Workflow, WorkflowStep

from ._immutability import freeze
from .retry_policy import RetryPolicy


@dataclass(frozen=True, slots=True)
class StepDefinition:
    """One definition-order-preserving node in a workflow DAG."""

    id: str
    kind: WorkflowStepKind
    needs: tuple[str, ...] = ()
    uses: str | None = None
    input_mapping: Mapping[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    checkpoint_policy: str = "after_success"
    approval_policy: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "needs", tuple(self.needs))
        object.__setattr__(self, "input_mapping", freeze(self.input_mapping))

    @classmethod
    def from_domain(cls, step: WorkflowStep) -> StepDefinition:
        return cls(
            id=step.id,
            kind=step.kind,
            needs=step.needs,
            uses=step.uses,
            input_mapping=step.input_mapping,
            timeout_seconds=step.timeout_seconds,
            retry_policy=RetryPolicy(
                max_attempts=step.max_attempts,
                backoff=step.retry_backoff,
                initial_seconds=step.retry_initial_seconds,
                max_seconds=step.retry_max_seconds,
            ),
            checkpoint_policy=step.checkpoint_policy,
            approval_policy=step.approval_policy,
        )


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    """Versioned Workflow Engine definition with deterministic tuple order."""

    id: str
    version: str
    name: str
    steps: tuple[StepDefinition, ...]
    schema_version: str = "reagent/v1alpha1"
    input_schema: Mapping[str, Any] = field(default_factory=dict)
    outputs: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "steps", tuple(self.steps))
        object.__setattr__(self, "input_schema", freeze(self.input_schema))
        object.__setattr__(self, "outputs", freeze(self.outputs))

    @classmethod
    def from_domain(cls, workflow: Workflow) -> WorkflowDefinition:
        return cls(
            id=workflow.id,
            version=workflow.version,
            name=workflow.name,
            steps=tuple(StepDefinition.from_domain(step) for step in workflow.steps),
            schema_version=workflow.schema_version,
            input_schema=workflow.input_schema,
            outputs=workflow.outputs,
        )

    def get_step(self, step_id: str) -> StepDefinition:
        for step in self.steps:
            if step.id == step_id:
                return step
        raise KeyError(step_id)

    def order_of(self, step_id: str) -> int:
        for index, step in enumerate(self.steps):
            if step.id == step_id:
                return index
        raise KeyError(step_id)
