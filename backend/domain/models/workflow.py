"""Immutable, versioned workflow aggregate."""

from __future__ import annotations

import re
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ..exceptions import DomainValidationError
from ._utils import freeze_value, require_non_empty
from .workflow_step import WorkflowStep

_OUTPUT_REFERENCE = re.compile(
    r"^\$\{nodes\.([A-Za-z][A-Za-z0-9_-]*)\.outputs\.([A-Za-z][A-Za-z0-9_-]*)\}$"
)


@dataclass(frozen=True, slots=True)
class Workflow:
    """A validated static DAG pinned to one immutable version."""

    id: str
    version: str
    name: str
    steps: tuple[WorkflowStep, ...]
    schema_version: str = "reagent/v1alpha1"
    input_schema: Mapping[str, Any] = field(default_factory=dict)
    outputs: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_empty(self.id, "Workflow.id")
        require_non_empty(self.version, "Workflow.version")
        require_non_empty(self.name, "Workflow.name")
        if self.schema_version != "reagent/v1alpha1":
            raise DomainValidationError(
                f"Unsupported workflow schema version: {self.schema_version}"
            )

        object.__setattr__(self, "steps", tuple(self.steps))
        if not self.steps:
            raise DomainValidationError("Workflow must contain at least one step")

        step_ids = [step.id for step in self.steps]
        if len(set(step_ids)) != len(step_ids):
            raise DomainValidationError("Workflow step IDs must be unique")

        known_ids = set(step_ids)
        for step in self.steps:
            missing = set(step.needs) - known_ids
            if missing:
                missing_list = ", ".join(sorted(missing))
                raise DomainValidationError(
                    f"WorkflowStep {step.id} has missing dependencies: {missing_list}"
                )

        self._validate_acyclic()
        for output_name, reference in self.outputs.items():
            require_non_empty(str(output_name), "Workflow output name")
            if not isinstance(reference, str):
                raise DomainValidationError(
                    f"Workflow output {output_name} must be a string reference"
                )
            match = _OUTPUT_REFERENCE.fullmatch(reference)
            if match is None:
                raise DomainValidationError(
                    f"Workflow output {output_name} has an unsupported reference"
                )
            referenced_step_id = match.group(1)
            if referenced_step_id not in known_ids:
                raise DomainValidationError(
                    f"Workflow output {output_name} references missing step "
                    f"{referenced_step_id}"
                )
        object.__setattr__(self, "input_schema", freeze_value(self.input_schema))
        object.__setattr__(self, "outputs", freeze_value(self.outputs))

    @property
    def roots(self) -> tuple[WorkflowStep, ...]:
        return tuple(step for step in self.steps if not step.needs)

    def get_step(self, step_id: str) -> WorkflowStep:
        for step in self.steps:
            if step.id == step_id:
                return step
        raise DomainValidationError(f"Workflow has no step named {step_id}")

    def dependents_of(self, step_id: str) -> tuple[WorkflowStep, ...]:
        return tuple(step for step in self.steps if step_id in step.needs)

    def _validate_acyclic(self) -> None:
        inbound_count = {step.id: len(step.needs) for step in self.steps}
        dependents: dict[str, list[str]] = {step.id: [] for step in self.steps}
        for step in self.steps:
            for dependency in step.needs:
                dependents[dependency].append(step.id)

        ready = deque(step.id for step in self.steps if inbound_count[step.id] == 0)
        visited = 0
        while ready:
            step_id = ready.popleft()
            visited += 1
            for dependent_id in dependents[step_id]:
                inbound_count[dependent_id] -= 1
                if inbound_count[dependent_id] == 0:
                    ready.append(dependent_id)

        if visited != len(self.steps):
            raise DomainValidationError("Workflow dependencies must form an acyclic graph")
