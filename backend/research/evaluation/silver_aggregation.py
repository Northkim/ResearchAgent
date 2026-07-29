"""Versioned TEST_POLICY_ONLY aggregation for synthetic judge verification."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping

from .contracts import RelevanceLabel
from .silver_contracts import (
    AgreementState,
    AutomatedJudgment,
    ConsistencyState,
    EvidenceState,
    HumanAuditReason,
    JudgmentConsensus,
    MetadataWarningState,
    PairwiseConsistencyResult,
    SilverDisposition,
)

TEST_AGGREGATION_POLICY_VERSION = (
    "reagent-silver-aggregation/TEST_POLICY_ONLY/v1"
)
TEST_CONFIDENCE_THRESHOLD = 0.80


class JudgmentAggregator:
    """Pure aggregation. Values here are not approved for any real judge."""

    def aggregate(
        self,
        *,
        candidate_id: str,
        judgments: tuple[AutomatedJudgment, ...],
        content_language: str,
        metadata_warnings: tuple[str, ...] = (),
        pairwise_results: tuple[PairwiseConsistencyResult, ...] = (),
    ) -> JudgmentConsensus:
        ordered = tuple(sorted(judgments, key=lambda item: item.run_index))
        labels = tuple(item.label for item in ordered)
        distribution = Counter(item.value for item in labels)
        agreement = (
            AgreementState.INCOMPLETE
            if len(ordered) != 2
            else AgreementState.AGREEMENT
            if len(set(labels)) == 1
            else AgreementState.DISAGREEMENT
        )
        evidence = (
            EvidenceState.NOT_AVAILABLE
            if ordered
            and all(item.insufficient_information for item in ordered)
            else EvidenceState.PRESENT
            if ordered and all(item.supporting_spans or item.concise_reason for item in ordered)
            and all(
                item.supporting_spans
                for item in ordered
                if item.label is not RelevanceLabel.CANNOT_JUDGE
            )
            else EvidenceState.MISSING
        )
        involved = tuple(
            item
            for item in pairwise_results
            if candidate_id in {item.left_candidate_id, item.right_candidate_id}
        )
        consistency = (
            ConsistencyState.CONFLICT
            if any(not item.order_consistent for item in involved)
            else ConsistencyState.CONSISTENT
            if involved
            else ConsistencyState.NOT_CHECKED
        )
        metadata_state = (
            MetadataWarningState.WARNING
            if metadata_warnings
            else MetadataWarningState.CLEAR
        )
        reasons: list[HumanAuditReason] = []
        if agreement is AgreementState.INCOMPLETE:
            reasons.append(HumanAuditReason.CANNOT_JUDGE)
        elif agreement is AgreementState.DISAGREEMENT:
            reasons.append(HumanAuditReason.LABEL_DISAGREEMENT)
        if any(item.label is RelevanceLabel.PARTIALLY_RELEVANT for item in ordered):
            reasons.append(HumanAuditReason.PARTIAL_LABEL)
        if any(item.label is RelevanceLabel.CANNOT_JUDGE for item in ordered):
            reasons.append(HumanAuditReason.CANNOT_JUDGE)
        if any(item.confidence < TEST_CONFIDENCE_THRESHOLD for item in ordered):
            reasons.append(HumanAuditReason.LOW_CONFIDENCE)
        if evidence is EvidenceState.MISSING:
            reasons.append(HumanAuditReason.MISSING_SUPPORTING_EVIDENCE)
        if consistency is ConsistencyState.CONFLICT:
            reasons.append(HumanAuditReason.PAIRWISE_CONFLICT)
        if content_language.lower() != "en":
            reasons.append(HumanAuditReason.NON_ENGLISH)
        if metadata_warnings:
            reasons.append(HumanAuditReason.METADATA_WARNING)
        reasons = list(dict.fromkeys(reasons))

        agreed_label = labels[0] if len(set(labels)) == 1 and labels else None
        high_confidence = len(ordered) == 2 and all(
            item.confidence >= TEST_CONFIDENCE_THRESHOLD for item in ordered
        )
        can_automate = (
            agreement is AgreementState.AGREEMENT
            and high_confidence
            and evidence is EvidenceState.PRESENT
            and consistency is not ConsistencyState.CONFLICT
            and metadata_state is MetadataWarningState.CLEAR
            and content_language.lower() == "en"
            and not reasons
        )
        if can_automate and agreed_label in {
            RelevanceLabel.HIGHLY_RELEVANT,
            RelevanceLabel.RELEVANT,
        }:
            disposition = SilverDisposition.AUTO_ACCEPTED
            reason = "TEST_POLICY_ONLY: two high-confidence relevant labels agree."
        elif can_automate and agreed_label is RelevanceLabel.NOT_RELEVANT:
            disposition = SilverDisposition.AUTO_REJECTED
            reason = "TEST_POLICY_ONLY: two high-confidence NOT_RELEVANT labels agree."
        else:
            disposition = SilverDisposition.NEEDS_HUMAN_REVIEW
            reason = (
                "TEST_POLICY_ONLY: human audit required: "
                + ", ".join(item.value for item in reasons or (HumanAuditReason.CANNOT_JUDGE,))
            )
            if not reasons:
                reasons.append(HumanAuditReason.CANNOT_JUDGE)
        return JudgmentConsensus(
            candidate_id=candidate_id,
            source_judgment_ids=tuple(item.judgment_id for item in ordered),
            label_distribution=dict(sorted(distribution.items())),
            confidence_values=tuple(item.confidence for item in ordered),
            agreement_state=agreement,
            supporting_evidence_state=evidence,
            pairwise_consistency_state=consistency,
            metadata_warning_state=metadata_state,
            disposition=disposition,
            proposed_silver_label=agreed_label,
            disposition_reason=reason,
            aggregation_policy_version=TEST_AGGREGATION_POLICY_VERSION,
            audit_reasons=tuple(reasons),
        )
