"""Tests for immutable registration, validation, execution, and integration."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

from backend.skill_system import (
    DuplicateSkillRegistrationError,
    EmittedArtifactMetadata,
    FieldSchema,
    SkillCapabilities,
    SkillDecisionMismatchError,
    SkillDefinition,
    SkillExecutionOutput,
    SkillExecutor,
    SkillMetadata,
    SkillReference,
    SkillRegistry,
    SkillSchema,
)
from backend.research.adapters import FakeLLMProvider
from backend.research.contracts import (
    ProviderFailureCategory,
    ProviderOperationKind,
    ProviderUsage,
    canonical_hash,
)
from backend.research.ports import LLMTextRequest, ProviderRequestContext
from backend.skill_system.runtime import (
    MOCK_PAPER_SEARCH,
    MOCK_SUMMARY,
    mock_paper_search,
    register_fake_skills,
)
from backend.workflow_engine.models import StepReady


def _decision(
    *,
    skill_ref: str,
    resolved_inputs: dict[str, object],
) -> StepReady:
    return StepReady(
        workflow_run_id="run-1",
        workflow_id="literature-review",
        workflow_version="1.0.0",
        expected_run_version=2,
        checkpoint_required=True,
        reason="Skill step is ready",
        step_id="search",
        step_run_id="step-run-1",
        attempt=1,
        expected_step_version=1,
        skill_ref=skill_ref,
        resolved_inputs=resolved_inputs,
        requires_ready_transition=False,
    )


def _execute(
    executor: SkillExecutor,
    decision: StepReady,
    reference: SkillReference,
    inputs: dict[str, object],
):
    return asyncio.run(executor.execute(decision, reference, inputs))


def test_register_skill() -> None:
    registry = SkillRegistry()
    registry.register(MOCK_PAPER_SEARCH, mock_paper_search)

    assert len(registry) == 1
    assert registry.list_definitions() == (MOCK_PAPER_SEARCH,)


def test_retrieve_exact_skill_version() -> None:
    registry = SkillRegistry()
    second_version = replace(MOCK_PAPER_SEARCH, version="2.0.0")
    registry.register(second_version, mock_paper_search)
    registry.register(MOCK_PAPER_SEARCH, mock_paper_search)

    assert registry.get_definition("mock_paper_search", "1.0.0") is MOCK_PAPER_SEARCH
    assert registry.get_definition("mock_paper_search", "2.0.0") is second_version
    assert [item.version for item in registry.list_definitions()] == ["1.0.0", "2.0.0"]


def test_duplicate_version_registration_is_rejected() -> None:
    registry = SkillRegistry()
    registry.register(MOCK_PAPER_SEARCH, mock_paper_search)

    with pytest.raises(DuplicateSkillRegistrationError):
        registry.register(MOCK_PAPER_SEARCH, mock_paper_search)


def test_invalid_input_schema_returns_typed_failure() -> None:
    registry = SkillRegistry()
    register_fake_skills(registry)
    executor = SkillExecutor(registry)
    decision = _decision(
        skill_ref="mock_paper_search@1.0.0",
        resolved_inputs={"query": 42},
    )

    result = _execute(
        executor,
        decision,
        SkillReference.parse(decision.skill_ref),
        {"query": 42},
    )

    assert not result.success
    assert result.error is not None
    assert result.error.code == "INVALID_SKILL_INPUT"
    assert result.error.details["path"] == "input.query"


def test_successful_fake_skill_execution() -> None:
    registry = SkillRegistry()
    register_fake_skills(registry)
    executor = SkillExecutor(registry)
    inputs = {"query": "research agents"}
    decision = _decision(
        skill_ref="mock_paper_search@1.0.0",
        resolved_inputs=inputs,
    )

    result = _execute(
        executor,
        decision,
        SkillReference.parse(decision.skill_ref),
        inputs,
    )

    assert result.success
    assert result.error is None
    assert result.output_data["papers"] == (
        "Mock Foundations of research agents",
        "Mock Advances in research agents",
    )
    assert result.execution_metadata["step_run_id"] == "step-run-1"


def test_failed_skill_execution_is_normalized() -> None:
    registry = SkillRegistry()
    register_fake_skills(registry)
    executor = SkillExecutor(registry)
    inputs: dict[str, object] = {"papers": []}
    decision = _decision(
        skill_ref="mock_summary@1.0.0",
        resolved_inputs=inputs,
    )

    result = _execute(
        executor,
        decision,
        SkillReference.parse(decision.skill_ref),
        inputs,
    )

    assert not result.success
    assert result.error is not None
    assert result.error.code == "EMPTY_PAPERS"
    assert not result.error.retryable
    assert result.output_data == {}


def test_skill_result_is_json_serializable() -> None:
    registry = SkillRegistry()
    register_fake_skills(registry)
    executor = SkillExecutor(registry)
    inputs = {"papers": ["Paper A", "Paper B"]}
    decision = _decision(
        skill_ref="mock_summary@1.0.0",
        resolved_inputs=inputs,
    )

    result = _execute(
        executor,
        decision,
        SkillReference.parse(decision.skill_ref),
        inputs,
    )
    serialized = result.to_dict()

    assert json.loads(json.dumps(serialized)) == serialized
    assert serialized["output_data"] == {
        "summary": "Mock summary: Paper A; Paper B"
    }


def test_step_ready_compatibility_without_workflow_mutation() -> None:
    registry = SkillRegistry()
    register_fake_skills(registry)
    executor = SkillExecutor(registry)
    inputs = {"query": "persistent memory"}
    decision = _decision(
        skill_ref="mock_paper_search@1.0.0",
        resolved_inputs=inputs,
    )
    before = decision

    result = _execute(
        executor,
        decision,
        SkillReference.parse(decision.skill_ref),
        inputs,
    )

    assert result.success
    assert decision is before
    assert decision.resolved_inputs["query"] == "persistent memory"


def test_executor_rejects_arguments_that_differ_from_step_ready() -> None:
    registry = SkillRegistry()
    register_fake_skills(registry)
    executor = SkillExecutor(registry)
    decision = _decision(
        skill_ref="mock_paper_search@1.0.0",
        resolved_inputs={"query": "original"},
    )

    with pytest.raises(SkillDecisionMismatchError):
        _execute(
            executor,
            decision,
            SkillReference.parse(decision.skill_ref),
            {"query": "changed"},
        )


def _capability_test_definition(name: str) -> SkillDefinition:
    return SkillDefinition(
        name=name,
        version="1.0.0",
        description="Exercise explicit research capability injection.",
        input_schema=SkillSchema(fields={}),
        output_schema=SkillSchema(fields={"provider": FieldSchema(kind="string")}),
        metadata=SkillMetadata(
            capabilities=("llm",),
            implementation_entrypoint="test:capability",
        ),
    )


def test_skill_capabilities_are_denied_by_default() -> None:
    registry = SkillRegistry()
    definition = _capability_test_definition("research.denied_capability")

    async def requires_llm(inputs, context):
        del inputs
        context.capabilities.require_llm()
        return {"provider": "unreachable"}

    registry.register(definition, requires_llm)
    decision = _decision(skill_ref=str(definition.reference), resolved_inputs={})
    result = _execute(
        SkillExecutor(registry),
        decision,
        definition.reference,
        {},
    )

    assert not result.success
    assert result.error is not None
    assert result.error.code == "CAPABILITY_DENIED"


def test_skill_receives_only_composition_injected_provider() -> None:
    registry = SkillRegistry()
    definition = _capability_test_definition("research.injected_capability")
    fake_llm = FakeLLMProvider()

    async def identifies_llm(inputs, context):
        del inputs
        provider = context.capabilities.require_llm()
        return {"provider": provider.identity.provider}

    registry.register(definition, identifies_llm)
    decision = _decision(skill_ref=str(definition.reference), resolved_inputs={})
    result = _execute(
        SkillExecutor(
            registry,
            capability_provider=lambda ready: SkillCapabilities(llm=fake_llm),
        ),
        decision,
        definition.reference,
        {},
    )

    assert result.success
    assert result.output_data == {"provider": "synthetic-llm"}


def test_composition_cannot_grant_capability_omitted_by_skill_definition() -> None:
    registry = SkillRegistry()
    declared = _capability_test_definition("research.undeclared_capability")
    definition = replace(
        declared,
        metadata=replace(declared.metadata, capabilities=()),
    )

    async def requires_llm(inputs, context):
        del inputs
        context.capabilities.require_llm()
        return {"provider": "unreachable"}

    registry.register(definition, requires_llm)
    decision = _decision(skill_ref=str(definition.reference), resolved_inputs={})
    result = _execute(
        SkillExecutor(
            registry,
            capability_provider=lambda ready: SkillCapabilities(llm=FakeLLMProvider()),
        ),
        decision,
        definition.reference,
        {},
    )

    assert not result.success
    assert result.error is not None
    assert result.error.code == "CAPABILITY_DENIED"


def test_rich_skill_output_preserves_artifacts_and_provider_usage() -> None:
    registry = SkillRegistry()
    definition = _capability_test_definition("research.rich_output")
    usage = ProviderUsage.zero_cost(
        provider="synthetic-llm",
        model_or_endpoint="deterministic-structured/v1",
        operation_kind=ProviderOperationKind.GENERATE_STRUCTURED,
    )
    emitted = EmittedArtifactMetadata(
        artifact_id="artifact-1",
        storage_key="runs/run-1/report.md",
        checksum=canonical_hash({"report": 1}),
        media_type="text/markdown",
        size=12,
        logical_name="report.md",
    )

    async def returns_rich_output(inputs, context):
        del inputs, context
        return SkillExecutionOutput(
            output_data={"provider": "synthetic-llm"},
            emitted_artifacts=(emitted,),
            provider_usage=(usage,),
        )

    registry.register(definition, returns_rich_output)
    decision = _decision(skill_ref=str(definition.reference), resolved_inputs={})
    result = _execute(
        SkillExecutor(registry),
        decision,
        definition.reference,
        {},
    )

    assert result.success
    assert result.emitted_artifacts == (emitted,)
    assert result.provider_usage == (usage,)
    assert result.to_dict()["provider_usage"][0]["estimated_cost_minor_units"] == 0


def test_provider_error_is_normalized_at_skill_execution_boundary() -> None:
    registry = SkillRegistry()
    definition = _capability_test_definition("research.provider_failure")
    failing_llm = FakeLLMProvider(
        failure=ProviderFailureCategory.PROVIDER_TIMEOUT
    )

    async def calls_provider(inputs, context):
        del inputs
        provider = context.capabilities.require_llm()
        await provider.generate_text(
            LLMTextRequest(
                prompt_name="test",
                prompt_version="test/v1",
                messages=({"role": "user", "content": "synthetic"},),
                max_output_tokens=1,
            ),
            context=ProviderRequestContext(
                operation_id="operation-1",
                idempotency_key="request-1",
                request_fingerprint=canonical_hash({"request": 1}),
            ),
        )
        return {"provider": "unreachable"}

    registry.register(definition, calls_provider)
    decision = _decision(skill_ref=str(definition.reference), resolved_inputs={})
    result = _execute(
        SkillExecutor(
            registry,
            capability_provider=lambda ready: SkillCapabilities(llm=failing_llm),
        ),
        decision,
        definition.reference,
        {},
    )

    assert not result.success
    assert result.error is not None
    assert result.error.code == "PROVIDER_TIMEOUT"
    assert result.error.retryable
    assert result.error.details == {"fake": True}
