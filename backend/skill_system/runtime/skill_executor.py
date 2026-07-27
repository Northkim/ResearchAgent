"""Stateless adapter from Workflow Engine StepReady to normalized SkillResult."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable

from backend.research.ports import ProviderError
from backend.skill_system._immutability import freeze_json
from backend.skill_system.exceptions import (
    SkillDecisionMismatchError,
    SkillCapabilityDeniedError,
    SkillExecutionFailure,
    SkillValidationError,
)
from backend.skill_system.models import (
    SkillCapabilities,
    SkillExecutionContext,
    SkillReference,
)
from backend.skill_system.registry import SkillRegistry
from backend.skill_system.results import SkillError, SkillExecutionOutput, SkillResult
from backend.workflow_engine.models import StepReady


class SkillExecutor:
    """Validate, execute, and normalize a skill without mutating workflow state."""

    def __init__(
        self,
        registry: SkillRegistry,
        *,
        capability_provider: Callable[[StepReady], SkillCapabilities] | None = None,
    ) -> None:
        self._registry = registry
        self._capability_provider = capability_provider

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

        granted_capabilities = (
            self._capability_provider(decision)
            if self._capability_provider is not None
            else SkillCapabilities()
        ).restricted_to(registered.definition.metadata.capabilities)
        context = SkillExecutionContext(
            workflow_run_id=decision.workflow_run_id,
            workflow_id=decision.workflow_id,
            workflow_version=decision.workflow_version,
            step_id=decision.step_id,
            step_run_id=decision.step_run_id,
            attempt=decision.attempt,
            capabilities=granted_capabilities,
        )

        try:
            raw_result = await registered.execute(validated_input, context)
            if isinstance(raw_result, SkillExecutionOutput):
                raw_output = raw_result.output_data
                emitted_artifacts = raw_result.emitted_artifacts
                provider_usage = raw_result.provider_usage
            else:
                raw_output = raw_result
                emitted_artifacts = ()
                provider_usage = ()
            validated_output = registered.definition.output_schema.validate(
                raw_output,
                label="output",
            )
        except SkillCapabilityDeniedError as exc:
            return SkillResult.failed(
                SkillError(
                    code="CAPABILITY_DENIED",
                    message=str(exc),
                    retryable=False,
                ),
                execution_metadata=metadata,
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
        except ProviderError as exc:
            return SkillResult.failed(
                SkillError(
                    code=exc.category.value,
                    message=str(exc),
                    retryable=exc.retryable,
                    details=exc.safe_details,
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
            emitted_artifacts=emitted_artifacts,
            provider_usage=provider_usage,
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
