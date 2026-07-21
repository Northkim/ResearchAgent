"""Static validation for versioned v1 Workflow Engine definitions."""

from __future__ import annotations

import re
from collections import deque
from collections.abc import Mapping
from typing import Any

from backend.domain.enums import WorkflowStepKind

from ..exceptions import InvalidReferenceError, InvalidWorkflowDefinitionError
from ..models import WorkflowDefinition
from .reference_resolver import (
    INPUT_REFERENCE,
    NODE_OUTPUT_REFERENCE,
    InputReferenceResolver,
    iter_reference_strings,
)

_STEP_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


class WorkflowValidator:
    """Reject invalid graphs and references before engine decisions."""

    def validate(self, definition: WorkflowDefinition) -> None:
        if not definition.id.strip() or not definition.version.strip():
            raise InvalidWorkflowDefinitionError(
                "Workflow id and version must be non-empty"
            )
        if not definition.name.strip():
            raise InvalidWorkflowDefinitionError("Workflow name must be non-empty")
        if definition.schema_version != "reagent/v1alpha1":
            raise InvalidWorkflowDefinitionError(
                f"Unsupported schema version {definition.schema_version}"
            )
        if not definition.steps:
            raise InvalidWorkflowDefinitionError("Workflow must contain a step")

        step_ids = [step.id for step in definition.steps]
        if len(step_ids) != len(set(step_ids)):
            raise InvalidWorkflowDefinitionError("Workflow contains duplicate step ids")
        known_ids = set(step_ids)

        for step in definition.steps:
            if not _STEP_ID.fullmatch(step.id):
                raise InvalidWorkflowDefinitionError(
                    f"Invalid workflow step id {step.id!r}"
                )
            if len(step.needs) != len(set(step.needs)):
                raise InvalidWorkflowDefinitionError(
                    f"Step {step.id} contains duplicate dependencies"
                )
            if step.id in step.needs:
                raise InvalidWorkflowDefinitionError(
                    f"Step {step.id} cannot depend on itself"
                )
            missing = set(step.needs) - known_ids
            if missing:
                raise InvalidWorkflowDefinitionError(
                    f"Step {step.id} has missing dependencies: "
                    f"{', '.join(sorted(missing))}"
                )
            if step.timeout_seconds <= 0:
                raise InvalidWorkflowDefinitionError(
                    f"Step {step.id} timeout must be positive"
                )
            if step.checkpoint_policy != "after_success":
                raise InvalidWorkflowDefinitionError(
                    f"Step {step.id} uses an unsupported checkpoint policy"
                )
            if step.kind is WorkflowStepKind.SKILL:
                if not step.uses or "@" not in step.uses:
                    raise InvalidWorkflowDefinitionError(
                        f"Skill step {step.id} must pin skill_id@version"
                    )
            elif step.kind is WorkflowStepKind.APPROVAL:
                if step.uses is not None or not step.approval_policy:
                    raise InvalidWorkflowDefinitionError(
                        f"Approval step {step.id} requires only an approval policy"
                    )
            else:
                raise InvalidWorkflowDefinitionError(
                    f"Step {step.id} has unsupported kind {step.kind!r}"
                )

        self._validate_acyclic(definition)
        resolver = InputReferenceResolver()
        for step in definition.steps:
            ancestors = resolver.ancestors_of(definition, step.id)
            for reference in iter_reference_strings(step.input_mapping):
                self._validate_step_reference(
                    definition, step.id, ancestors, reference
                )

        for output_name, reference in definition.outputs.items():
            if not str(output_name).strip():
                raise InvalidReferenceError("Workflow output name cannot be empty")
            match = NODE_OUTPUT_REFERENCE.fullmatch(reference)
            if match is None:
                raise InvalidReferenceError(
                    f"Workflow output {output_name} has invalid reference {reference!r}"
                )
            if match.group(1) not in known_ids:
                raise InvalidReferenceError(
                    f"Workflow output {output_name} references missing step "
                    f"{match.group(1)}"
                )

    def _validate_step_reference(
        self,
        definition: WorkflowDefinition,
        step_id: str,
        ancestors: frozenset[str],
        reference: str,
    ) -> None:
        input_match = INPUT_REFERENCE.fullmatch(reference)
        if input_match:
            input_name = input_match.group(1)
            if input_name not in definition.input_schema:
                raise InvalidReferenceError(
                    f"Step {step_id} references undefined input {input_name}"
                )
            return

        node_match = NODE_OUTPUT_REFERENCE.fullmatch(reference)
        if node_match:
            referenced_step = node_match.group(1)
            if referenced_step not in ancestors:
                raise InvalidReferenceError(
                    f"Step {step_id} references non-ancestor step {referenced_step}"
                )
            return

        raise InvalidReferenceError(
            f"Step {step_id} contains unsupported reference {reference!r}"
        )

    @staticmethod
    def _validate_acyclic(definition: WorkflowDefinition) -> None:
        inbound = {step.id: len(step.needs) for step in definition.steps}
        dependents: dict[str, list[str]] = {step.id: [] for step in definition.steps}
        for step in definition.steps:
            for dependency in step.needs:
                dependents[dependency].append(step.id)

        ready = deque(step.id for step in definition.steps if not step.needs)
        visited = 0
        while ready:
            step_id = ready.popleft()
            visited += 1
            for dependent in dependents[step_id]:
                inbound[dependent] -= 1
                if inbound[dependent] == 0:
                    ready.append(dependent)
        if visited != len(definition.steps):
            raise InvalidWorkflowDefinitionError(
                "Workflow dependencies contain a cycle"
            )
