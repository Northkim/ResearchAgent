"""Type-preserving resolution for the v1 reference syntax."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from typing import Any

from backend.domain.enums import StepRunStatus

from ..exceptions import InvalidReferenceError
from ..models import ExecutionSnapshot, StepDefinition, WorkflowDefinition
from ..models._immutability import freeze

INPUT_REFERENCE = re.compile(r"^\$\{inputs\.([A-Za-z][A-Za-z0-9_-]*)\}$")
NODE_OUTPUT_REFERENCE = re.compile(
    r"^\$\{nodes\.([A-Za-z][A-Za-z0-9_-]*)\.outputs\.([A-Za-z][A-Za-z0-9_-]*)\}$"
)


def iter_reference_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        if "${" in value:
            yield value
        return
    if isinstance(value, Mapping):
        for item in value.values():
            yield from iter_reference_strings(item)
        return
    if isinstance(value, (tuple, list)):
        for item in value:
            yield from iter_reference_strings(item)


class InputReferenceResolver:
    """Resolve exact whole-value references without evaluating code."""

    def resolve_step_inputs(
        self,
        definition: WorkflowDefinition,
        step: StepDefinition,
        snapshot: ExecutionSnapshot,
    ) -> Mapping[str, Any]:
        ancestors = self.ancestors_of(definition, step.id)
        latest_attempts = snapshot.latest_attempts()

        def resolve(value: Any) -> Any:
            if isinstance(value, str):
                input_match = INPUT_REFERENCE.fullmatch(value)
                if input_match:
                    input_name = input_match.group(1)
                    if input_name not in snapshot.workflow_inputs:
                        raise InvalidReferenceError(
                            f"Step {step.id} references missing workflow input {input_name}"
                        )
                    return freeze(snapshot.workflow_inputs[input_name])

                node_match = NODE_OUTPUT_REFERENCE.fullmatch(value)
                if node_match:
                    source_step_id, output_name = node_match.groups()
                    if source_step_id not in ancestors:
                        raise InvalidReferenceError(
                            f"Step {step.id} references non-ancestor step {source_step_id}"
                        )
                    source_run = latest_attempts.get(source_step_id)
                    if source_run is None:
                        raise InvalidReferenceError(
                            f"Step {step.id} references missing state for {source_step_id}"
                        )
                    if source_run.status not in {
                        StepRunStatus.COMPLETED,
                        StepRunStatus.SKIPPED,
                    }:
                        raise InvalidReferenceError(
                            f"Step {step.id} references incomplete step {source_step_id}"
                        )
                    if output_name not in source_run.outputs:
                        raise InvalidReferenceError(
                            f"Step {step.id} references missing output "
                            f"{source_step_id}.{output_name}"
                        )
                    return freeze(source_run.outputs[output_name])

                if "${" in value:
                    raise InvalidReferenceError(
                        f"Step {step.id} contains unsupported reference {value!r}"
                    )
                return value

            if isinstance(value, Mapping):
                return freeze({str(key): resolve(item) for key, item in value.items()})
            if isinstance(value, (tuple, list)):
                return tuple(resolve(item) for item in value)
            return value

        return freeze(
            {str(key): resolve(value) for key, value in step.input_mapping.items()}
        )

    def resolve_workflow_outputs(
        self,
        definition: WorkflowDefinition,
        snapshot: ExecutionSnapshot,
    ) -> Mapping[str, Any]:
        latest_attempts = snapshot.latest_attempts()
        resolved: dict[str, Any] = {}
        for output_name, reference in definition.outputs.items():
            match = NODE_OUTPUT_REFERENCE.fullmatch(reference)
            if match is None:
                raise InvalidReferenceError(
                    f"Workflow output {output_name} has invalid reference {reference!r}"
                )
            step_id, field_name = match.groups()
            step_run = latest_attempts.get(step_id)
            if step_run is None or step_run.status not in {
                StepRunStatus.COMPLETED,
                StepRunStatus.SKIPPED,
            }:
                raise InvalidReferenceError(
                    f"Workflow output {output_name} references incomplete step {step_id}"
                )
            if field_name not in step_run.outputs:
                raise InvalidReferenceError(
                    f"Workflow output {output_name} references missing "
                    f"{step_id}.{field_name}"
                )
            resolved[str(output_name)] = freeze(step_run.outputs[field_name])
        return freeze(resolved)

    def ancestors_of(
        self, definition: WorkflowDefinition, step_id: str
    ) -> frozenset[str]:
        step_by_id = {step.id: step for step in definition.steps}
        if step_id not in step_by_id:
            raise InvalidReferenceError(f"Unknown step {step_id}")
        ancestors: set[str] = set()
        pending = list(step_by_id[step_id].needs)
        while pending:
            ancestor_id = pending.pop()
            if ancestor_id in ancestors:
                continue
            ancestor = step_by_id.get(ancestor_id)
            if ancestor is None:
                raise InvalidReferenceError(
                    f"Step {step_id} has missing dependency {ancestor_id}"
                )
            ancestors.add(ancestor_id)
            pending.extend(ancestor.needs)
        return frozenset(ancestors)
