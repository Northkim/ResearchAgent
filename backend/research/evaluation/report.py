"""Deterministic evaluation evidence report generation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from backend.research.contracts._serialization import canonical_json
from backend.research.ports import ArtifactContentStorage

from .candidate_pool import EvaluationArtifact
from .contracts import (
    AdjudicatedJudgment,
    CandidateJudgment,
    EvaluationCandidate,
    EvaluationMetricSummary,
    EvaluationRun,
)


class EvaluationReportGenerator:
    def __init__(self, artifact_storage: ArtifactContentStorage) -> None:
        self.artifact_storage = artifact_storage

    def generate(
        self,
        *,
        evaluation_run: EvaluationRun,
        candidates: Iterable[EvaluationCandidate],
        reviewer_judgments: Iterable[CandidateJudgment],
        adjudicated: Iterable[AdjudicatedJudgment],
        metrics: EvaluationMetricSummary,
        proposed_thresholds: Mapping[str, Any] | None = None,
    ) -> tuple[EvaluationArtifact, ...]:
        candidate_values = tuple(
            sorted(candidates, key=lambda item: (item.topic_id, item.rank))
        )
        reviewer_values = tuple(
            sorted(
                reviewer_judgments,
                key=lambda item: (item.topic_id, item.candidate_id, item.reviewer_id),
            )
        )
        adjudicated_values = tuple(
            sorted(adjudicated, key=lambda item: (item.topic_id, item.candidate_id))
        )
        base = evaluation_run.evaluation_id
        by_topic: dict[str, list[EvaluationCandidate]] = defaultdict(list)
        for candidate in candidate_values:
            by_topic[candidate.topic_id].append(candidate)
        topic_results = {
            "schema_version": "openalex-evaluation-topic-results/v1",
            "topics": [
                {
                    "topic_id": topic_id,
                    "candidate_count": len(items),
                    "judgment_count": sum(
                        item.topic_id == topic_id for item in reviewer_values
                    ),
                    "adjudicated_count": sum(
                        item.topic_id == topic_id for item in adjudicated_values
                    ),
                    "retrieval_metrics": dict(
                        metrics.per_topic_retrieval.get(topic_id, {})
                    ),
                    "metadata_only_candidates": [
                        {
                            "candidate_id": item.candidate_id,
                            "rank": item.rank,
                            "title": item.title,
                            "year": item.year,
                            "openalex_id": item.openalex_id,
                        }
                        for item in items
                    ],
                }
                for topic_id, items in sorted(by_topic.items())
            ],
            "full_abstracts_included": False,
        }
        agreement = {
            "schema_version": "openalex-reviewer-agreement/v1",
            "metric": "cohen_kappa",
            "result": metrics.reviewer_agreement.to_dict(),
            "reviewer_count": len({item.reviewer_id for item in reviewer_values}),
            "cannot_judge_excluded": True,
            "limitations": (
                "Agreement is unavailable when sample size or reviewer structure "
                "does not support Cohen kappa."
            ),
        }
        metadata_quality = {
            "schema_version": "openalex-metadata-quality/v1",
            "doi_resolution_rate": metrics.doi_resolution_rate.to_dict(),
            "abstract_availability_rate": metrics.abstract_availability_rate.to_dict(),
            "author_completeness_rate": metrics.author_completeness_rate.to_dict(),
            "venue_completeness_rate": metrics.venue_completeness_rate.to_dict(),
            "duplicate_rate": metrics.duplicate_rate.to_dict(),
            "unresolved_cluster_rate": metrics.unresolved_cluster_rate.to_dict(),
            "false_merge_rate": metrics.false_merge_rate.to_dict(),
        }
        operational = {
            "schema_version": "openalex-operational-metrics/v1",
            "request_count": metrics.request_count.to_dict(),
            "latency_ms": metrics.latency_ms.to_dict(),
            "retry_rate": metrics.retry_rate.to_dict(),
            "failure_rate": metrics.failure_rate.to_dict(),
            "provider_usage": [dict(item) for item in evaluation_run.provider_usage],
            "monetary_policy": "zero out-of-pocket cost",
        }
        metric_document = metrics.to_dict()
        artifacts = [
            self._write_json(
                f"{base}/topic_results.json",
                "topic_results.json",
                topic_results,
            ),
            self._write_json(
                f"{base}/metrics.json",
                "metrics.json",
                metric_document,
            ),
            self._write_json(
                f"{base}/reviewer_agreement.json",
                "reviewer_agreement.json",
                agreement,
            ),
            self._write_json(
                f"{base}/metadata_quality.json",
                "metadata_quality.json",
                metadata_quality,
            ),
            self._write_json(
                f"{base}/operational_metrics.json",
                "operational_metrics.json",
                operational,
            ),
        ]
        report = self._markdown(
            evaluation_run=evaluation_run,
            metrics=metrics,
            candidate_count=len(candidate_values),
            reviewer_count=len({item.reviewer_id for item in reviewer_values}),
            adjudicated_count=len(adjudicated_values),
            proposed_thresholds=proposed_thresholds or {},
        )
        stored = self.artifact_storage.write_immutable(
            f"{base}/evaluation_report.md",
            report.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
        )
        artifacts.append(
            EvaluationArtifact(
                logical_name="evaluation_report.md",
                storage_key=stored.storage_key,
                checksum=stored.checksum,
                size=stored.size,
                media_type=stored.media_type,
            )
        )
        return tuple(artifacts)

    def _write_json(
        self,
        storage_key: str,
        logical_name: str,
        value: Mapping[str, Any],
    ) -> EvaluationArtifact:
        content = canonical_json(value).encode("utf-8")
        stored = self.artifact_storage.write_immutable(
            storage_key,
            content,
            media_type="application/json",
        )
        return EvaluationArtifact(
            logical_name=logical_name,
            storage_key=stored.storage_key,
            checksum=stored.checksum,
            size=stored.size,
            media_type=stored.media_type,
        )

    @staticmethod
    def _markdown(
        *,
        evaluation_run: EvaluationRun,
        metrics: EvaluationMetricSummary,
        candidate_count: int,
        reviewer_count: int,
        adjudicated_count: int,
        proposed_thresholds: Mapping[str, Any],
    ) -> str:
        metric_lines = [
            f"- median topic Precision@5: {_format_metric(metrics.precision_at_5.to_dict())}",
            f"- median topic Precision@10: {_format_metric(metrics.precision_at_10.to_dict())}",
            f"- median topic nDCG@10: {_format_metric(metrics.ndcg_at_10.to_dict())}",
            f"- pooled Recall@K: {_format_metric(metrics.pooled_recall_at_k.to_dict())}",
            f"- relevant-paper yield: {_format_metric(metrics.relevant_paper_yield.to_dict())}",
        ]
        threshold_lines = (
            [
                f"- `{name}`: proposed `{value}`; owner approval required."
                for name, value in sorted(proposed_thresholds.items())
            ]
            or ["- No project thresholds were approved or applied."]
        )
        return "\n".join(
            [
                "# OpenAlex Discovery Evaluation Report",
                "",
                "## Evidence identity",
                "",
                f"- Evaluation ID: `{evaluation_run.evaluation_id}`",
                f"- Topic-set version: `{evaluation_run.topic_set_version}`",
                f"- Provider/adapter: `{evaluation_run.provider}@{evaluation_run.adapter_version}`",
                f"- API contract snapshot: `{evaluation_run.api_contract_snapshot}`",
                f"- Candidate count: {candidate_count}",
                f"- Human reviewer count: {reviewer_count}",
                f"- Adjudicated count: {adjudicated_count}",
                "",
                "## Measured results",
                "",
                *metric_lines,
                "",
                "These values are calculated from imported human judgments. The "
                "harness did not generate relevance labels.",
                "",
                "## Reviewer judgments",
                "",
                "Reviewers and adjudicators are human roles. `CANNOT_JUDGE` remains "
                "distinct and is not converted to irrelevant.",
                "",
                "## Proposed project thresholds",
                "",
                *threshold_lines,
                "",
                "Thresholds are ReAgent project policy, not provider guarantees or "
                "literature-established universal standards.",
                "",
                "## Provider contract facts",
                "",
                "The execution records the OpenAlex adapter and API-contract snapshot. "
                "Provider indices change, so identical future results are not guaranteed.",
                "",
                "## Engineering inference",
                "",
                "Provider promotion requires owner review of the measured results, "
                "missingness, disagreement, retention, and operational evidence. This "
                "report does not automatically promote OpenAlex or authorize another provider.",
                "",
                "## Limitations",
                "",
                *[f"- {item}" for item in metrics.limitations],
                "- The evaluation set is a ReAgent engineering set, not a universal benchmark.",
                "- Full abstracts are not reproduced in this report.",
                "- Abstract-only review cannot establish full-paper scientific quality.",
                "",
            ]
        )


def _format_metric(value: Mapping[str, Any]) -> str:
    if not value["available"]:
        return f"unavailable ({value['reason']})"
    return f"{value['value']} (n={value['sample_size']})"
