"""Pure deterministic evaluation metrics."""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable

from .contracts import (
    AdjudicatedJudgment,
    CandidateJudgment,
    EvaluationCandidate,
    EvaluationMetricSummary,
    EvaluationRun,
    MetricValue,
    RelevanceLabel,
)

RELEVANCE_GAIN = {
    RelevanceLabel.HIGHLY_RELEVANT: 3,
    RelevanceLabel.RELEVANT: 2,
    RelevanceLabel.PARTIALLY_RELEVANT: 1,
    RelevanceLabel.NOT_RELEVANT: 0,
}
_BINARY_RELEVANT = {
    RelevanceLabel.HIGHLY_RELEVANT,
    RelevanceLabel.RELEVANT,
}


class EvaluationMetrics:
    def calculate(
        self,
        *,
        candidates: Iterable[EvaluationCandidate],
        adjudicated: Iterable[AdjudicatedJudgment],
        reviewer_judgments: Iterable[CandidateJudgment] = (),
        evaluation_run: EvaluationRun | None = None,
        pooled_relevant_total: int | None = None,
        duplicate_pairs: int | None = None,
        false_merges: int | None = None,
        failed_operations: int = 0,
    ) -> EvaluationMetricSummary:
        if duplicate_pairs is not None and duplicate_pairs < 0:
            raise ValueError("duplicate_pairs cannot be negative")
        if false_merges is not None and false_merges < 0:
            raise ValueError("false_merges cannot be negative")
        if (
            duplicate_pairs is not None
            and false_merges is not None
            and false_merges > duplicate_pairs
        ):
            raise ValueError("false_merges cannot exceed duplicate_pairs")
        if failed_operations < 0:
            raise ValueError("failed_operations cannot be negative")
        ordered = tuple(sorted(candidates, key=lambda item: (item.topic_id, item.rank)))
        adjudicated_values = tuple(adjudicated)
        reviewer_values = tuple(reviewer_judgments)
        final = {item.candidate_id: item for item in adjudicated_values}
        if len(final) != len(adjudicated_values):
            raise ValueError("Adjudicated candidate IDs must be unique")
        unknown = set(final) - {item.candidate_id for item in ordered}
        if unknown:
            raise ValueError(f"Adjudication references unknown candidates: {sorted(unknown)}")

        labels = {
            candidate.candidate_id: final[candidate.candidate_id].final_relevance_label
            for candidate in ordered
            if candidate.candidate_id in final
        }
        by_topic: dict[str, tuple[EvaluationCandidate, ...]] = {
            topic_id: tuple(item for item in ordered if item.topic_id == topic_id)
            for topic_id in sorted({item.topic_id for item in ordered})
        }
        per_topic_metrics = {
            topic_id: {
                "precision_at_5": self._precision(items, labels, 5),
                "precision_at_10": self._precision(items, labels, 10),
                "ndcg_at_10": self._ndcg(items, labels, 10),
            }
            for topic_id, items in by_topic.items()
        }
        precision5 = self._median_topic_metric(
            per_topic_metrics,
            "precision_at_5",
        )
        precision10 = self._median_topic_metric(
            per_topic_metrics,
            "precision_at_10",
        )
        ndcg10 = self._median_topic_metric(per_topic_metrics, "ndcg_at_10")
        recall = self._pooled_recall(ordered, labels, pooled_relevant_total, 10)
        judged = [
            label for label in labels.values() if label is not RelevanceLabel.CANNOT_JUDGE
        ]
        relevant = sum(label in _BINARY_RELEVANT for label in judged)
        yield_metric = MetricValue(True, relevant, len(judged))
        coverage = MetricValue(
            True,
            0.0 if not ordered else len(labels) / len(ordered),
            len(ordered),
        )
        metadata = self._metadata(ordered)
        duplicate_rate = (
            MetricValue(
                False,
                None,
                0,
                "Adjudicated duplicate-pair evidence was not supplied",
            )
            if duplicate_pairs is None
            else MetricValue(
                True,
                0.0 if not ordered else duplicate_pairs / len(ordered),
                len(ordered),
            )
        )
        unresolved = sum(
            item.identity_ambiguity
            for item in reviewer_values
            if item.relevance_label is not RelevanceLabel.CANNOT_JUDGE
        )
        unresolved_metric = MetricValue(
            True,
            0.0 if not reviewer_values else unresolved / len(reviewer_values),
            len(reviewer_values),
        )
        false_merge_metric = (
            MetricValue(
                False,
                None,
                0,
                "False-merge labels were not adjudicated",
            )
            if false_merges is None or duplicate_pairs is None
            else MetricValue(
                True,
                0.0 if duplicate_pairs == 0 else false_merges / duplicate_pairs,
                duplicate_pairs,
            )
        )
        agreement = self._agreement(reviewer_values)
        request_count = evaluation_run.request_count if evaluation_run else 0
        retries = evaluation_run.retry_count if evaluation_run else 0
        usage_count = (
            len(evaluation_run.provider_usage) if evaluation_run is not None else 0
        )
        operational_unavailable = evaluation_run is None
        request_metric = (
            MetricValue(False, None, 0, "EvaluationRun operational data unavailable")
            if operational_unavailable
            else MetricValue(True, request_count, usage_count)
        )
        latency_metric = (
            MetricValue(False, None, 0, "EvaluationRun operational data unavailable")
            if operational_unavailable
            else MetricValue(True, evaluation_run.latency_ms, usage_count)
        )
        retry_metric = (
            MetricValue(False, None, 0, "EvaluationRun operational data unavailable")
            if operational_unavailable
            else MetricValue(
                True,
                0.0 if request_count == 0 else retries / request_count,
                request_count,
            )
        )
        failure_metric = (
            MetricValue(False, None, 0, "EvaluationRun operational data unavailable")
            if operational_unavailable
            else MetricValue(
                True,
                0.0 if usage_count == 0 else failed_operations / usage_count,
                usage_count,
            )
        )
        review_burden = MetricValue(
            True,
            sum(
                1
                for item in reviewer_values
                if item.identity_ambiguity
                or item.relevance_label is RelevanceLabel.CANNOT_JUDGE
                or item.metadata_error_flags
            ),
            len(reviewer_values),
        )
        limitations = (
            "Relevance gains are ReAgent project policy: 3/2/1/0.",
            "Precision and nDCG summaries are medians of per-topic values.",
            "CANNOT_JUDGE is excluded and never converted to zero.",
            "Pooled recall is unavailable without an adjudicated pooled denominator.",
            "Small topic/reviewer samples do not establish provider-wide quality.",
        )
        return EvaluationMetricSummary(
            precision_at_5=precision5,
            precision_at_10=precision10,
            ndcg_at_10=ndcg10,
            pooled_recall_at_k=recall,
            relevant_paper_yield=yield_metric,
            judgment_coverage=coverage,
            doi_resolution_rate=metadata["doi"],
            abstract_availability_rate=metadata["abstract"],
            author_completeness_rate=metadata["authors"],
            venue_completeness_rate=metadata["venue"],
            duplicate_rate=duplicate_rate,
            unresolved_cluster_rate=unresolved_metric,
            false_merge_rate=false_merge_metric,
            request_count=request_metric,
            latency_ms=latency_metric,
            retry_rate=retry_metric,
            failure_rate=failure_metric,
            manual_review_burden=review_burden,
            reviewer_agreement=agreement,
            per_topic_retrieval={
                topic_id: {
                    name: metric.to_dict()
                    for name, metric in topic_metrics.items()
                }
                for topic_id, topic_metrics in per_topic_metrics.items()
            },
            limitations=limitations,
        )

    @staticmethod
    def _median_topic_metric(
        per_topic: dict[str, dict[str, MetricValue]],
        name: str,
    ) -> MetricValue:
        if not per_topic:
            return MetricValue(False, None, 0, "No topics with candidates")
        unavailable = [
            topic_id
            for topic_id, metrics in per_topic.items()
            if not metrics[name].available
        ]
        if unavailable:
            return MetricValue(
                False,
                None,
                len(per_topic),
                f"Per-topic {name} unavailable for: {', '.join(unavailable)}",
            )
        values = [float(metrics[name].value) for metrics in per_topic.values()]
        return MetricValue(
            True,
            statistics.median(values),
            len(values),
        )

    @staticmethod
    def _precision(
        candidates: tuple[EvaluationCandidate, ...],
        labels: dict[str, RelevanceLabel],
        k: int,
    ) -> MetricValue:
        top = tuple(item for item in candidates if item.rank <= k)
        if not top:
            return MetricValue(False, None, 0, "No candidates")
        top_labels = [labels.get(item.candidate_id) for item in top]
        if any(label is None or label is RelevanceLabel.CANNOT_JUDGE for label in top_labels):
            return MetricValue(
                False,
                None,
                len(top),
                f"Top-{k} contains missing or CANNOT_JUDGE labels",
            )
        relevant = sum(label in _BINARY_RELEVANT for label in top_labels)
        return MetricValue(True, relevant / len(top), len(top))

    @staticmethod
    def _ndcg(
        candidates: tuple[EvaluationCandidate, ...],
        labels: dict[str, RelevanceLabel],
        k: int,
    ) -> MetricValue:
        if not candidates:
            return MetricValue(False, None, 0, "No candidates")
        if any(
            item.candidate_id not in labels
            or labels[item.candidate_id] is RelevanceLabel.CANNOT_JUDGE
            for item in candidates
        ):
            return MetricValue(
                False,
                None,
                len(candidates),
                "nDCG requires complete adjudicated labels without CANNOT_JUDGE",
            )
        ranked_gains = [
            RELEVANCE_GAIN[labels[item.candidate_id]]
            for item in candidates[: min(k, len(candidates))]
        ]
        ideal_gains = sorted(
            (RELEVANCE_GAIN[labels[item.candidate_id]] for item in candidates),
            reverse=True,
        )[: min(k, len(candidates))]
        dcg = sum(gain / math.log2(index + 2) for index, gain in enumerate(ranked_gains))
        ideal = sum(gain / math.log2(index + 2) for index, gain in enumerate(ideal_gains))
        if ideal == 0:
            return MetricValue(False, None, len(ranked_gains), "Ideal DCG is zero")
        return MetricValue(True, dcg / ideal, len(ranked_gains))

    @staticmethod
    def _pooled_recall(
        candidates: tuple[EvaluationCandidate, ...],
        labels: dict[str, RelevanceLabel],
        pooled_relevant_total: int | None,
        k: int,
    ) -> MetricValue:
        if pooled_relevant_total is None:
            return MetricValue(
                False,
                None,
                0,
                "No pooled-gold relevant denominator was supplied",
            )
        if pooled_relevant_total <= 0:
            return MetricValue(False, None, 0, "Pooled denominator must be positive")
        top = tuple(item for item in candidates if item.rank <= k)
        if any(
            item.candidate_id not in labels
            or labels[item.candidate_id] is RelevanceLabel.CANNOT_JUDGE
            for item in top
        ):
            return MetricValue(
                False,
                None,
                len(top),
                "Recall@K requires adjudicated top-K labels",
            )
        found = sum(labels[item.candidate_id] in _BINARY_RELEVANT for item in top)
        return MetricValue(True, found / pooled_relevant_total, pooled_relevant_total)

    @staticmethod
    def _metadata(
        candidates: tuple[EvaluationCandidate, ...],
    ) -> dict[str, MetricValue]:
        count = len(candidates)
        if count == 0:
            unavailable = MetricValue(False, None, 0, "No candidates")
            return {
                "doi": unavailable,
                "abstract": unavailable,
                "authors": unavailable,
                "venue": unavailable,
            }
        return {
            "doi": MetricValue(True, sum(item.doi is not None for item in candidates) / count, count),
            "abstract": MetricValue(
                True, sum(item.abstract_available for item in candidates) / count, count
            ),
            "authors": MetricValue(
                True, sum(bool(item.authors) for item in candidates) / count, count
            ),
            "venue": MetricValue(
                True, sum(item.venue is not None for item in candidates) / count, count
            ),
        }

    @staticmethod
    def _agreement(judgments: tuple[CandidateJudgment, ...]) -> MetricValue:
        by_reviewer: dict[str, dict[str, RelevanceLabel]] = defaultdict(dict)
        for judgment in judgments:
            if judgment.relevance_label is RelevanceLabel.CANNOT_JUDGE:
                continue
            by_reviewer[judgment.reviewer_id][judgment.candidate_id] = (
                judgment.relevance_label
            )
        if len(by_reviewer) != 2:
            return MetricValue(
                False,
                None,
                0,
                "Cohen kappa requires exactly two reviewers",
            )
        reviewer_ids = sorted(by_reviewer)
        common = sorted(
            set(by_reviewer[reviewer_ids[0]]) & set(by_reviewer[reviewer_ids[1]])
        )
        if len(common) < 2:
            return MetricValue(
                False,
                None,
                len(common),
                "At least two shared judgeable candidates are required",
            )
        first = [by_reviewer[reviewer_ids[0]][item] for item in common]
        second = [by_reviewer[reviewer_ids[1]][item] for item in common]
        observed = sum(a is b for a, b in zip(first, second, strict=True)) / len(common)
        first_counts = Counter(first)
        second_counts = Counter(second)
        expected = sum(
            (first_counts[label] / len(common)) * (second_counts[label] / len(common))
            for label in RELEVANCE_GAIN
        )
        if expected == 1:
            return MetricValue(
                False,
                None,
                len(common),
                "Kappa is undefined when expected agreement is one",
            )
        return MetricValue(True, (observed - expected) / (1 - expected), len(common))
