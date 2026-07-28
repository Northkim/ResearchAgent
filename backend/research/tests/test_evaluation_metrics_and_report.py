from __future__ import annotations

from datetime import UTC, datetime

from backend.research.adapters import LocalFilesystemArtifactStorage
from backend.research.contracts import canonical_hash
from backend.research.evaluation.contracts import (
    AdjudicatedJudgment,
    CandidateJudgment,
    EvaluationCandidate,
    EvaluationCompletionState,
    EvaluationRun,
    RelevanceLabel,
)
from backend.research.evaluation.metrics import EvaluationMetrics
from backend.research.evaluation.report import EvaluationReportGenerator

NOW = datetime(2026, 7, 28, 10, 0, tzinfo=UTC)


def _candidate(index: int, topic_id: str = "topic") -> EvaluationCandidate:
    return EvaluationCandidate(
        topic_id=topic_id,
        topic_title=f"Synthetic evaluation topic {topic_id}",
        topic=f"synthetic topic query {topic_id}",
        research_question="Which synthetic candidates are relevant?",
        candidate_id=f"{topic_id}-candidate-{index}",
        rank=index,
        paper_id=f"{topic_id}-paper-{index}",
        openalex_id=f"W{topic_id}{index}",
        title=f"Synthetic title {index}",
        authors=() if index == 10 else ("Author",),
        year=2025,
        venue=None if index == 9 else "Venue",
        doi=None if index == 8 else f"10.1000/{index}",
        abstract_available=index != 7,
        normalized_metadata_hash=canonical_hash(
            {"metadata": index, "topic": topic_id}
        ),
        search_execution_id=canonical_hash({"search": topic_id}),
        provider="openalex",
        adapter_version="1.0.0",
        abstract_preview="PROHIBITED_FULL_ABSTRACT_CANARY",
    )


def _review(candidate: EvaluationCandidate, reviewer: str, label: RelevanceLabel):
    return CandidateJudgment(
        topic_id=candidate.topic_id,
        candidate_id=candidate.candidate_id,
        candidate_identity_hash=candidate.identity_hash,
        reviewer_id=reviewer,
        relevance_label=label,
        confidence=4,
        exclusion_reason=None,
        duplicate_cluster=None,
        identity_ambiguity=False,
        metadata_error_flags=(),
        reviewer_note=None,
        judged_at=NOW,
    )


def _adjudicated(candidate: EvaluationCandidate, label: RelevanceLabel):
    return AdjudicatedJudgment(
        topic_id=candidate.topic_id,
        candidate_id=candidate.candidate_id,
        final_relevance_label=label,
        adjudicator_id="human-adjudicator",
        source_judgment_hashes=(canonical_hash("a"), canonical_hash("b")),
        disagreement_reason=None,
        final_notes=None,
        adjudicated_at=NOW,
    )


def _run() -> EvaluationRun:
    return EvaluationRun(
        evaluation_id="evaluation-test",
        topic_set_version="1.0.0",
        provider="openalex",
        adapter_version="1.0.0",
        api_contract_snapshot="openalex-works-api/2026-07-27",
        query_fingerprints={"topic": canonical_hash("query")},
        candidate_pool_checksums={"topic": canonical_hash("pool")},
        started_at=NOW,
        completed_at=NOW,
        request_count=2,
        latency_ms=120,
        retry_count=0,
        provider_usage=(
            {
                "provider": "openalex",
                "request_count": 2,
                "latency_ms": 120,
                "retry_count": 0,
            },
        ),
        completion_state=EvaluationCompletionState.CANDIDATES_COMPLETE,
    )


def test_metrics_precision_ndcg_metadata_agreement_and_unavailable_recall() -> None:
    candidates = tuple(_candidate(index) for index in range(1, 11))
    labels = (
        RelevanceLabel.HIGHLY_RELEVANT,
        RelevanceLabel.RELEVANT,
        RelevanceLabel.RELEVANT,
        RelevanceLabel.PARTIALLY_RELEVANT,
        RelevanceLabel.NOT_RELEVANT,
        RelevanceLabel.RELEVANT,
        RelevanceLabel.NOT_RELEVANT,
        RelevanceLabel.RELEVANT,
        RelevanceLabel.PARTIALLY_RELEVANT,
        RelevanceLabel.NOT_RELEVANT,
    )
    adjudicated = tuple(
        _adjudicated(candidate, label)
        for candidate, label in zip(candidates, labels, strict=True)
    )
    reviews = tuple(
        _review(candidate, reviewer, label)
        for reviewer in ("reviewer-a", "reviewer-b")
        for candidate, label in zip(candidates, labels, strict=True)
    )
    metrics = EvaluationMetrics().calculate(
        candidates=candidates,
        adjudicated=adjudicated,
        reviewer_judgments=reviews,
        evaluation_run=_run(),
    )
    assert metrics.precision_at_5.value == 0.6
    assert metrics.precision_at_10.value == 0.5
    assert metrics.ndcg_at_10.available is True
    assert metrics.pooled_recall_at_k.available is False
    assert "denominator" in metrics.pooled_recall_at_k.reason
    assert metrics.doi_resolution_rate.value == 0.9
    assert metrics.abstract_availability_rate.value == 0.9
    assert metrics.author_completeness_rate.value == 0.9
    assert metrics.venue_completeness_rate.value == 0.9
    assert metrics.reviewer_agreement.value == 1.0
    assert metrics.request_count.value == 2
    assert metrics.duplicate_rate.available is False
    assert metrics.false_merge_rate.available is False


def test_cannot_judge_and_partial_or_zero_candidate_metrics_fail_honestly() -> None:
    candidates = tuple(_candidate(index) for index in range(1, 6))
    partial = (_adjudicated(candidates[0], RelevanceLabel.CANNOT_JUDGE),)
    metrics = EvaluationMetrics().calculate(
        candidates=candidates,
        adjudicated=partial,
    )
    assert metrics.precision_at_5.available is False
    assert metrics.ndcg_at_10.available is False
    assert metrics.relevant_paper_yield.value == 0
    assert metrics.request_count.available is False

    empty = EvaluationMetrics().calculate(candidates=(), adjudicated=())
    assert empty.precision_at_5.available is False
    assert empty.doi_resolution_rate.available is False


def test_retrieval_metrics_are_calculated_per_topic_then_summarized() -> None:
    topic_a = tuple(_candidate(index, "topic-a") for index in range(1, 6))
    topic_b = tuple(_candidate(index, "topic-b") for index in range(1, 6))
    adjudicated = tuple(
        _adjudicated(candidate, RelevanceLabel.RELEVANT)
        for candidate in topic_a
    ) + tuple(
        _adjudicated(candidate, RelevanceLabel.NOT_RELEVANT)
        for candidate in topic_b
    )
    metrics = EvaluationMetrics().calculate(
        candidates=(*topic_a, *topic_b),
        adjudicated=adjudicated,
    )
    assert metrics.precision_at_5.value == 0.5
    assert metrics.precision_at_5.sample_size == 2
    assert (
        metrics.per_topic_retrieval["topic-a"]["precision_at_5"]["value"]
        == 1.0
    )
    assert (
        metrics.per_topic_retrieval["topic-b"]["precision_at_5"]["value"]
        == 0.0
    )


def test_report_is_deterministic_separates_inference_and_omits_abstracts(tmp_path) -> None:
    candidates = tuple(_candidate(index) for index in range(1, 3))
    labels = (RelevanceLabel.RELEVANT, RelevanceLabel.NOT_RELEVANT)
    adjudicated = tuple(
        _adjudicated(candidate, label)
        for candidate, label in zip(candidates, labels, strict=True)
    )
    reviews = tuple(
        _review(candidate, reviewer, label)
        for reviewer in ("reviewer-a", "reviewer-b")
        for candidate, label in zip(candidates, labels, strict=True)
    )
    metrics = EvaluationMetrics().calculate(
        candidates=candidates,
        adjudicated=adjudicated,
        reviewer_judgments=reviews,
        evaluation_run=_run(),
    )
    storage = LocalFilesystemArtifactStorage(tmp_path)
    generator = EvaluationReportGenerator(storage)
    first = generator.generate(
        evaluation_run=_run(),
        candidates=candidates,
        reviewer_judgments=reviews,
        adjudicated=adjudicated,
        metrics=metrics,
        proposed_thresholds={"precision_at_5": 0.7},
    )
    second = generator.generate(
        evaluation_run=_run(),
        candidates=candidates,
        reviewer_judgments=reviews,
        adjudicated=adjudicated,
        metrics=metrics,
        proposed_thresholds={"precision_at_5": 0.7},
    )
    assert [item.checksum for item in first] == [item.checksum for item in second]
    report = storage.read("evaluation-test/evaluation_report.md").decode()
    assert "## Measured results" in report
    assert "## Reviewer judgments" in report
    assert "## Engineering inference" in report
    assert "## Limitations" in report
    assert "PROHIBITED_FULL_ABSTRACT_CANARY" not in report
    assert all(item.media_type for item in first)
