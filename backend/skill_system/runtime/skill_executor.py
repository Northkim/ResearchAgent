"""Stateless adapter from Workflow Engine StepReady to normalized SkillResult."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.skill_system._immutability import freeze_json
from backend.skill_system.exceptions import (
    SkillDecisionMismatchError,
    SkillExecutionFailure,
    SkillValidationError,
)
from backend.skill_system.models import SkillExecutionContext, SkillReference
from backend.skill_system.registry import SkillRegistry
from backend.skill_system.results import SkillError, SkillResult
from backend.workflow_engine.models import StepReady


class SkillExecutor:
    """Validate, execute, and normalize a skill without mutating workflow state."""

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    async def execute(
        self,
        decision: StepReady,
        skill_reference: SkillReference,
        resolved_inputs: Mapping[str, Any],
    ) -> SkillResult:
        decision_reference = SkillReference.parse(decision.skill_ref)
        if decision_reference != skill_reference:
            raise SkillDecisionMismatchError(
                f"StepReady pins {decision_reference}, not {skill_reference}"
            )

        try:
            normalized_arguments = freeze_json(resolved_inputs, path="resolved_inputs")
        except ValueError as exc:
            raise SkillDecisionMismatchError(str(exc)) from exc
        if normalized_arguments != decision.resolved_inputs:
            raise SkillDecisionMismatchError(
                "Executor resolved_inputs do not match the immutable StepReady inputs"
            )

        registered = self._registry.resolve(skill_reference)
        metadata = _execution_metadata(decision, skill_reference)

        try:
            validated_input = registered.definition.input_schema.validate(
                resolved_inputs,
                label="input",
            )
        except SkillValidationError as exc:
            return SkillResult.failed(
                SkillError(
                    code="INVALID_SKILL_INPUT",
                    message=str(exc),
                    retryable=False,
                    details={"path": exc.path},
                ),
                execution_metadata=metadata,
            )

        context = SkillExecutionContext(
            workflow_run_id=decision.workflow_run_id,
            workflow_id=decision.workflow_id,
            workflow_version=decision.workflow_version,
            step_id=decision.step_id,
            step_run_id=decision.step_run_id,
            attempt=decision.attempt,
        )

        try:
            raw_output = await registered.execute(validated_input, context)
            validated_output = registered.definition.output_schema.validate(
                raw_output,
                label="output",
            )
        except SkillExecutionFailure as exc:
            return SkillResult.failed(
                SkillError(
                    code=exc.code,
                    message=exc.message,
                    retryable=exc.retryable,
                    details=exc.details,
                ),
                execution_metadata=metadata,
            )
        except SkillValidationError as exc:
            return SkillResult.failed(
                SkillError(
                    code="INVALID_SKILL_OUTPUT",
                    message=str(exc),
                    retryable=False,
                    details={"path": exc.path},
                ),
                execution_metadata=metadata,
            )
        except Exception as exc:  # Runtime boundary normalizes implementation failures.
            return SkillResult.failed(
                SkillError(
                    code="SKILL_EXECUTION_ERROR",
                    message="Skill implementation failed",
                    retryable=False,
                    details={"exception_type": type(exc).__name__},
                ),
                execution_metadata=metadata,
            )

        return SkillResult.succeeded(
            validated_output,
            execution_metadata=metadata,
        )


def _execution_metadata(
    decision: StepReady,
    reference: SkillReference,
) -> dict[str, Any]:
    return {
        "skill_name": reference.name,
        "skill_version": reference.version,
        "workflow_run_id": decision.workflow_run_id,
        "step_id": decision.step_id,
        "step_run_id": decision.step_run_id,
        "attempt": decision.attempt,
    }
