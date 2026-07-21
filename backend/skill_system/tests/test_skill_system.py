"""Tests for immutable registration, validation, execution, and integration."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

from backend.skill_system import (
    DuplicateSkillRegistrationError,
    SkillDecisionMismatchError,
    SkillExecutor,
    SkillReference,
    SkillRegistry,
)
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
