"""Raw-silver and human-audited-silver metric boundary for synthetic fixtures."""

from __future__ import annotations

import math
from collections.abc import Mapping

from .contracts import EvaluationCandidate, MetricValue, RelevanceLabel
from .silver_contracts import (
    HumanAuditQueue,
    HumanAuditResult,
    JudgmentConsensus,
    SilverMetricReport,
    SilverMetricSet,
    SilverDisposition,
)

_GAIN = {
    RelevanceLabel.HIGHLY_RELEVANT: 3,
    RelevanceLabel.RELEVANT: 2,
    RelevanceLabel.PARTIALLY_RELEVANT: 1,
    RelevanceLabel.NOT_RELEVANT: 0,
    RelevanceLabel.CANNOT_JUDGE: 0,
}
_RELEVANT = {RelevanceLabel.HIGHLY_RELEVANT, RelevanceLabel.RELEVANT}


class SilverMetrics:
    def calculate(
        self,
        *,
        candidates: tuple[EvaluationCandidate, ...],
        consensuses: tuple[JudgmentConsensus, ...],
        audit_queue: HumanAuditQueue,
        audit_results: tuple[HumanAuditResult, ...] = (),
    ) -> SilverMetricReport:
        consensus_by_id = {item.candidate_id: item for item in consensuses}
        raw = {
            candidate_id: item.proposed_silver_label
            for candidate_id, item in consensus_by_id.items()
            if item.proposed_silver_label is not None
        }
        raw_set = self._set(candidates, raw)
        request_by_id = {
            item.audit_request_id: item for item in audit_queue.requests
        }
        if not audit_results:
            audited_set = self._unavailable(
                "No HumanAuditResult exists; raw silver values are not copied"
            )
            agreement = MetricValue(False, None, 0, "No human audit results")
            override = MetricValue(False, None, 0, "No human audit results")
        else:
            unknown = {
                item.audit_request_id for item in audit_results
            } - set(request_by_id)
            if unknown:
                raise ValueError(f"Human audit results reference unknown requests: {sorted(unknown)}")
            audited = dict(raw)
            agree_count = 0
            for result in audit_results:
                request = request_by_id[result.audit_request_id]
                audited[request.candidate_id] = result.final_label
                agree_count += result.agrees_with_silver
            audited_set = self._set(candidates, audited)
            agreement = MetricValue(
                True, agree_count / len(audit_results), len(audit_results)
            )
            override = MetricValue(
                True, (len(audit_results) - agree_count) / len(audit_results),
                len(audit_results),
            )
        needs = sum(
            item.disposition is SilverDisposition.NEEDS_HUMAN_REVIEW
            for item in consensuses
        )
        cannot = sum(
            item.proposed_silver_label is RelevanceLabel.CANNOT_JUDGE
            for item in consensuses
        )
        denominator = len(consensuses)
        return SilverMetricReport(
            raw_silver=raw_set,
            audited_silver=audited_set,
            human_audit_agreement=agreement,
            human_override_rate=override,
            needs_human_review_rate=MetricValue(
                True, 0 if not denominator else needs / denominator, denominator
            ),
            cannot_judge_rate=MetricValue(
                True, 0 if not denominator else cannot / denominator, denominator
            ),
        )

    def _set(
        self,
        candidates: tuple[EvaluationCandidate, ...],
        labels: Mapping[str, RelevanceLabel],
    ) -> SilverMetricSet:
        ordered = tuple(sorted(candidates, key=lambda item: (item.topic_id, item.rank)))
        return SilverMetricSet(
            precision_at_5=self._precision(ordered, labels, 5),
            precision_at_10=self._precision(ordered, labels, 10),
            ndcg_at_10=self._ndcg(ordered, labels, 10),
        )

    @staticmethod
    def _precision(
        candidates: tuple[EvaluationCandidate, ...],
        labels: Mapping[str, RelevanceLabel],
        k: int,
    ) -> MetricValue:
        selected = candidates[:k]
        judged = [
            labels[item.candidate_id]
            for item in selected
            if item.candidate_id in labels
            and labels[item.candidate_id] is not RelevanceLabel.CANNOT_JUDGE
        ]
        if len(judged) != len(selected):
            return MetricValue(
                False, None, len(judged), f"Raw silver labels incomplete within top {k}"
            )
        return MetricValue(
            True, sum(item in _RELEVANT for item in judged) / len(judged), len(judged)
        )

    @staticmethod
    def _ndcg(
        candidates: tuple[EvaluationCandidate, ...],
        labels: Mapping[str, RelevanceLabel],
        k: int,
    ) -> MetricValue:
        selected = candidates[:k]
        if any(item.candidate_id not in labels for item in selected):
            return MetricValue(False, None, 0, f"Raw silver labels incomplete within top {k}")
        gains = [_GAIN[labels[item.candidate_id]] for item in selected]
        dcg = sum(gain / math.log2(index + 2) for index, gain in enumerate(gains))
        ideal = sum(
            gain / math.log2(index + 2)
            for index, gain in enumerate(sorted(gains, reverse=True))
        )
        return MetricValue(True, 0.0 if ideal == 0 else dcg / ideal, len(gains))

    @staticmethod
    def _unavailable(reason: str) -> SilverMetricSet:
        value = MetricValue(False, None, 0, reason)
        return SilverMetricSet(value, value, value)
