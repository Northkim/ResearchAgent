from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.research.adapters import LocalFilesystemArtifactStorage
from backend.research.contracts import (
    ProviderFailureCategory,
    ProviderOperationStatus,
    SettlementState,
    canonical_hash,
)
from backend.research.evaluation.audit_queue import (
    TEST_MAXIMUM_AUDIT_BURDEN,
    TEST_RANDOM_AUDIT_PERCENTAGE,
    HumanAuditQueueBuilder,
)
from backend.research.evaluation.cli import main
from backend.research.evaluation.contracts import RelevanceLabel
from backend.research.evaluation.fake_judge import (
    FakeAutomatedRelevanceJudge,
)
from backend.research.evaluation.judge_port import (
    AutomatedJudgeError,
    JudgeCallContext,
)
from backend.research.evaluation.operation_journal import (
    JournaledProviderOperationUnit,
)
from backend.research.evaluation.prompts import (
    POINTWISE_A_VERSION,
    POINTWISE_B_VERSION,
    JudgePromptRegistry,
)
from backend.research.evaluation.silver_aggregation import (
    TEST_AGGREGATION_POLICY_VERSION,
    TEST_CONFIDENCE_THRESHOLD,
)
from backend.research.evaluation.silver_contracts import (
    AuditQueueState,
    AutomatedJudgment,
    AutomatedJudgmentRequest,
    HumanAuditResult,
    HumanAuditStatus,
    JudgmentConsensus,
    SilverDisposition,
)
from backend.research.evaluation.silver_metrics import SilverMetrics
from backend.research.evaluation.silver_orchestrator import (
    SyntheticSilverOrchestrator,
)
from backend.research.evaluation.synthetic_fixtures import (
    SYNTHETIC_PROVIDER,
    load_synthetic_fixture_set,
)
from backend.research.services import (
    ProviderExecutionPolicy,
    ProviderOperationService,
)

FIXTURES = Path("evaluation/fixtures/synthetic_silver_v1.json")


def _fixture():
    return load_synthetic_fixture_set(FIXTURES)


def _harness(tmp_path: Path):
    fixtures = _fixture()
    judge = FakeAutomatedRelevanceJudge(
        pointwise=fixtures.pointwise_behaviors,
        pairwise=fixtures.pairwise_behaviors,
    )
    unit = JournaledProviderOperationUnit(
        tmp_path / "synthetic-evaluation" / "provider_operations.journal.jsonl"
    )
    service = ProviderOperationService(
        unit.provider_operations,
        commit_callback=unit.commit,
    )
    orchestrator = SyntheticSilverOrchestrator(
        judge=judge,
        provider_operations=service,
        execution_policy=ProviderExecutionPolicy.synthetic_relevance_judge(),
        artifact_storage=LocalFilesystemArtifactStorage(tmp_path),
    )
    return fixtures, judge, unit, orchestrator


def _run(tmp_path: Path):
    fixtures, judge, unit, orchestrator = _harness(tmp_path)
    result = orchestrator.run(
        evaluation_id="synthetic-evaluation",
        fixtures=fixtures,
    )
    return fixtures, judge, unit, orchestrator, result


def _request(candidate_id: str, prompt_version: str) -> AutomatedJudgmentRequest:
    fixture = _fixture()
    candidate = next(
        item for item in fixture.candidates if item.candidate_id == candidate_id
    )
    return AutomatedJudgmentRequest(
        evaluation_id="test",
        topic_id=candidate.topic_id,
        candidate_id=candidate.candidate_id,
        topic_description=candidate.topic,
        research_question=None,
        inclusion_rubric=("Direct or substantial topical relevance.",),
        exclusion_rubric=("Incidental or absent topic.",),
        title=candidate.title,
        bounded_abstract_preview=candidate.abstract_preview,
        publication_year=candidate.year,
        venue=candidate.venue,
        content_scope="title_and_bounded_abstract_preview_only",
        candidate_metadata_checksum=candidate.identity_hash,
        prompt_version=prompt_version,
        rubric_version=JudgePromptRegistry().rubric_version,
    )


def test_contracts_are_immutable_stable_and_prohibit_rank_inputs() -> None:
    request = _request("syn-01-highly", POINTWISE_A_VERSION)
    assert request.request_checksum == _request(
        "syn-01-highly", POINTWISE_A_VERSION
    ).request_checksum
    with pytest.raises(FrozenInstanceError):
        request.title = "mutated"  # type: ignore[misc]
    value = request.to_dict()
    value["rank"] = 1
    with pytest.raises(ValueError, match="Prohibited"):
        AutomatedJudgmentRequest.from_dict(value)
    assert isinstance(request.inclusion_rubric, tuple)


def test_invalid_label_and_confidence_are_rejected() -> None:
    fixtures = _fixture()
    judge = FakeAutomatedRelevanceJudge(pointwise=fixtures.pointwise_behaviors)
    valid = judge.judge(
        _request("syn-01-highly", POINTWISE_A_VERSION),
        context=JudgeCallContext(run_index=1, timeout_seconds=5),
    )
    with pytest.raises(ValueError):
        replace(valid, label="QUALITY_PAPER", output_checksum="")
    with pytest.raises(ValueError, match="confidence"):
        replace(valid, confidence=1.01, output_checksum="")


def test_prompt_registry_is_immutable_versioned_and_enforces_prohibited_fields() -> None:
    registry = JudgePromptRegistry()
    prompt_a = registry.get(POINTWISE_A_VERSION)
    prompt_b = registry.get(POINTWISE_B_VERSION)
    assert prompt_a.version != prompt_b.version
    assert prompt_a.prompt_hash != prompt_b.prompt_hash
    assert prompt_a.rubric_version == prompt_b.rubric_version
    with pytest.raises(TypeError):
        prompt_a.output_schema["label"] = "changed"  # type: ignore[index]
    with pytest.raises(ValueError, match="citation_count"):
        registry.validate_input_fields({"title": "synthetic", "citation_count": 9})


def test_fake_judge_is_deterministic_zero_cost_and_fixture_driven() -> None:
    fixtures = _fixture()
    judge = FakeAutomatedRelevanceJudge(pointwise=fixtures.pointwise_behaviors)
    request = _request("syn-02-relevant", POINTWISE_A_VERSION)
    first = judge.judge(
        request, context=JudgeCallContext(run_index=1, timeout_seconds=5)
    )
    second = judge.judge(
        request, context=JudgeCallContext(run_index=1, timeout_seconds=5)
    )
    assert first.output_checksum == second.output_checksum
    assert first.usage.estimated_cost_minor_units == 0
    assert first.usage.provider_request_ids == ()
    assert first.supporting_spans[0].text in (request.bounded_abstract_preview or "")


@pytest.mark.parametrize(
    ("candidate_id", "prompt_version", "category"),
    (
        ("syn-19-malformed", POINTWISE_A_VERSION, ProviderFailureCategory.LLM_STRUCTURED_OUTPUT),
        ("syn-20-timeout", POINTWISE_A_VERSION, ProviderFailureCategory.PROVIDER_TIMEOUT),
        ("syn-20-timeout", POINTWISE_B_VERSION, ProviderFailureCategory.PROVIDER_UNAVAILABLE),
    ),
)
def test_fake_judge_failure_modes(
    candidate_id: str,
    prompt_version: str,
    category: ProviderFailureCategory,
) -> None:
    fixtures = _fixture()
    judge = FakeAutomatedRelevanceJudge(pointwise=fixtures.pointwise_behaviors)
    with pytest.raises(AutomatedJudgeError) as raised:
        judge.judge(
            _request(candidate_id, prompt_version),
            context=JudgeCallContext(run_index=1, timeout_seconds=5),
        )
    assert raised.value.category is category


def test_orchestration_order_operations_settlement_and_fail_closed_paths(
    tmp_path: Path,
) -> None:
    _, judge, unit, _, result = _run(tmp_path)
    assert judge.call_log[:4] == [
        ("pointwise", "syn-01-highly", 1),
        ("pointwise", "syn-01-highly", 2),
        ("pointwise", "syn-02-relevant", 1),
        ("pointwise", "syn-02-relevant", 2),
    ]
    assert len(result.judgments) == 37
    assert result.provider_operation_count == 42
    operations = unit.provider_operations.list_for_run(
        "synthetic-silver:synthetic-evaluation",
        "synthetic-evaluation",
    )
    assert all(item.status.is_terminal for item in operations)
    assert all(item.settlement_state is not SettlementState.UNSETTLED for item in operations)
    assert sum(item.status is ProviderOperationStatus.FAILED for item in operations) == 3


def test_replay_reconstructs_without_judge_call_or_duplicate_operation(
    tmp_path: Path,
) -> None:
    _, judge, unit, orchestrator, result = _run(tmp_path)
    calls = len(judge.call_log)
    replay = orchestrator.run(
        evaluation_id="synthetic-evaluation",
        fixtures=_fixture(),
    )
    assert replay.resumed is True
    assert len(judge.call_log) == calls
    assert replay.provider_operation_count == result.provider_operation_count
    operations = unit.provider_operations.list_for_run(
        "synthetic-silver:synthetic-evaluation", "synthetic-evaluation"
    )
    assert len(operations) == 42


def test_aggregation_dispositions_cover_every_required_route(tmp_path: Path) -> None:
    _, _, _, _, result = _run(tmp_path)
    by_id = {item.candidate_id: item for item in result.consensuses}
    assert by_id["syn-01-highly"].disposition is SilverDisposition.AUTO_ACCEPTED
    assert by_id["syn-03-not"].disposition is SilverDisposition.AUTO_REJECTED
    for candidate_id in (
        "syn-11-partial",
        "syn-12-cannot",
        "syn-13-disagreement",
        "syn-14-low-confidence",
        "syn-15-missing-span",
        "syn-16-pairwise-conflict",
        "syn-17-nonenglish",
        "syn-18-metadata-warning",
        "syn-19-malformed",
        "syn-20-timeout",
    ):
        assert (
            by_id[candidate_id].disposition
            is SilverDisposition.NEEDS_HUMAN_REVIEW
        )
    assert all(
        item.aggregation_policy_version == TEST_AGGREGATION_POLICY_VERSION
        for item in result.consensuses
    )
    assert TEST_CONFIDENCE_THRESHOLD == 0.80
    assert result.pairwise_results[0].order_consistent is False


def test_audit_queue_is_deterministic_includes_required_and_no_results(
    tmp_path: Path,
) -> None:
    _, _, _, _, result = _run(tmp_path)
    queue = result.audit_queue
    assert queue.required_count == 10
    assert queue.random_sample_count == 1
    assert len(queue.requests) == 11
    assert queue.state is AuditQueueState.READY
    assert TEST_RANDOM_AUDIT_PERCENTAGE == 10
    assert all(item.status is HumanAuditStatus.PENDING for item in queue.requests)
    rebuilt = HumanAuditQueueBuilder().build(
        evaluation_id=result.evaluation_id,
        candidates=result.candidates,
        consensuses=result.consensuses,
    )
    assert [item.audit_request_id for item in queue.requests] == [
        item.audit_request_id for item in rebuilt.requests
    ]


def test_audit_cap_reports_exceeded_without_discarding_required_items(
    tmp_path: Path,
) -> None:
    _, _, _, _, result = _run(tmp_path)
    base_candidate = result.candidates[0]
    base_consensus = next(
        item
        for item in result.consensuses
        if item.disposition is SilverDisposition.NEEDS_HUMAN_REVIEW
    )
    candidates = tuple(
        replace(
            base_candidate,
            candidate_id=f"cap-{index:02}",
            rank=index,
            paper_id=f"cap-paper-{index:02}",
            openalex_id=f"synthetic://cap-{index:02}",
            normalized_metadata_hash=canonical_hash({"cap": index}),
        )
        for index in range(1, TEST_MAXIMUM_AUDIT_BURDEN + 2)
    )
    consensuses = tuple(
        replace(
            base_consensus,
            candidate_id=item.candidate_id,
            checksum="",
        )
        for item in candidates
    )
    queue = HumanAuditQueueBuilder().build(
        evaluation_id="cap-evaluation",
        candidates=candidates,
        consensuses=consensuses,
    )
    assert queue.state is AuditQueueState.AUDIT_CAP_EXCEEDED
    assert len(queue.requests) == TEST_MAXIMUM_AUDIT_BURDEN + 1


def test_silver_metrics_keep_raw_and_audited_boundaries_separate(
    tmp_path: Path,
) -> None:
    _, _, _, _, result = _run(tmp_path)
    assert result.metrics.raw_silver.precision_at_5.value == pytest.approx(0.8)
    assert result.metrics.raw_silver.precision_at_10.value == pytest.approx(0.7)
    assert result.metrics.raw_silver.ndcg_at_10.available
    assert not result.metrics.audited_silver.precision_at_5.available
    assert "not copied" in (result.metrics.audited_silver.precision_at_5.reason or "")

    request = result.audit_queue.requests[0]
    audit_result = HumanAuditResult(
        audit_request_id=request.audit_request_id,
        human_reviewer_id="synthetic-human-fixture",
        final_label=RelevanceLabel.RELEVANT,
        agrees_with_silver=False,
        override_reason="Synthetic override fixture.",
        confidence=0.9,
        reviewed_at=datetime(2026, 1, 2, tzinfo=UTC),
        request_checksum=canonical_hash(request),
    )
    audited = SilverMetrics().calculate(
        candidates=result.candidates,
        consensuses=result.consensuses,
        audit_queue=result.audit_queue,
        audit_results=(audit_result,),
    )
    assert audited.audited_silver.precision_at_5.available
    assert audited.human_override_rate.value == 1.0
    assert audited.raw_silver.to_dict() == result.metrics.raw_silver.to_dict()
    assert audited.expert_gold_labels_present is False


def test_persistence_contains_only_synthetic_data_and_integrity_replays(
    tmp_path: Path,
) -> None:
    fixtures, _, _, _, result = _run(tmp_path)
    assert all(item.provider == SYNTHETIC_PROVIDER for item in result.candidates)
    content = b"\n".join(
        path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()
    )
    assert b"REAGENT_OPENALEX_API_KEY" not in content
    assert b"api_key" not in content
    assert fixtures.checksum.encode() in content
    assert b"raw_response" not in content


def test_synthetic_cli_runs_and_verifies_replay_without_network(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "judge-synthetic",
            "cli-synthetic",
            "--fixtures",
            str(FIXTURES),
        ]
    )
    assert exit_code == 0
    value = json.loads(capsys.readouterr().out)
    assert value["synthetic_fixture_count"] == 20
    assert value["replay_verified"] is True
    assert value["replay_judge_calls"] == 0
    assert value["network_called"] is False
    assert value["real_candidate_labels_generated"] is False
