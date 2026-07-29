"""Deterministic TEST_POLICY_ONLY human-audit queue generation."""

from __future__ import annotations

import hashlib
import math
from datetime import UTC, datetime
from collections import defaultdict
from collections.abc import Mapping

from backend.research.contracts import canonical_hash

from .contracts import EvaluationCandidate
from .silver_contracts import (
    AuditQueueState,
    HumanAuditReason,
    HumanAuditRequest,
    HumanAuditQueue,
    HumanAuditStatus,
    HumanAuditType,
    JudgmentConsensus,
    SilverDisposition,
)

TEST_AUDIT_POLICY_VERSION = "reagent-human-audit/TEST_POLICY_ONLY/v1"
TEST_RANDOM_AUDIT_PERCENTAGE = 10
TEST_RANDOM_SEED = "reagent-synthetic-audit-seed/v1"
TEST_SAMPLING_VERSION = "sha256-topic-stratified/TEST_POLICY_ONLY/v1"
TEST_MAXIMUM_AUDIT_BURDEN = 20
_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


class HumanAuditQueueBuilder:
    def build(
        self,
        *,
        evaluation_id: str,
        candidates: tuple[EvaluationCandidate, ...],
        consensuses: tuple[JudgmentConsensus, ...],
    ) -> HumanAuditQueue:
        by_candidate = {item.candidate_id: item for item in candidates}
        if set(by_candidate) != {item.candidate_id for item in consensuses}:
            raise ValueError("Audit queue requires one consensus per known candidate")
        required = tuple(
            item
            for item in consensuses
            if item.disposition is SilverDisposition.NEEDS_HUMAN_REVIEW
        )
        eligible_by_topic: dict[str, list[JudgmentConsensus]] = defaultdict(list)
        for consensus in consensuses:
            if consensus.disposition is not SilverDisposition.NEEDS_HUMAN_REVIEW:
                candidate = by_candidate[consensus.candidate_id]
                eligible_by_topic[candidate.topic_id].append(consensus)
        sampled: list[JudgmentConsensus] = []
        for topic_id in sorted(eligible_by_topic):
            eligible = eligible_by_topic[topic_id]
            sample_count = max(
                1,
                math.ceil(len(eligible) * TEST_RANDOM_AUDIT_PERCENTAGE / 100),
            )
            sampled.extend(
                sorted(
                    eligible,
                    key=lambda item: self._sample_key(
                        evaluation_id, topic_id, item.candidate_id
                    ),
                )[:sample_count]
            )
        requests: list[HumanAuditRequest] = []
        for consensus in required:
            requests.append(
                self._request(
                    evaluation_id=evaluation_id,
                    candidate=by_candidate[consensus.candidate_id],
                    consensus=consensus,
                    audit_type=HumanAuditType.REQUIRED,
                    reasons=consensus.audit_reasons,
                )
            )
        for consensus in sampled:
            requests.append(
                self._request(
                    evaluation_id=evaluation_id,
                    candidate=by_candidate[consensus.candidate_id],
                    consensus=consensus,
                    audit_type=HumanAuditType.RANDOM_CONSENSUS,
                    reasons=(HumanAuditReason.RANDOM_CONSENSUS_AUDIT,),
                )
            )
        requests.sort(
            key=lambda item: (
                item.audit_type is HumanAuditType.RANDOM_CONSENSUS,
                by_candidate[item.candidate_id].topic_id,
                by_candidate[item.candidate_id].rank,
            )
        )
        state = (
            AuditQueueState.AUDIT_CAP_EXCEEDED
            if len(requests) > TEST_MAXIMUM_AUDIT_BURDEN
            else AuditQueueState.READY
        )
        return HumanAuditQueue(
            evaluation_id=evaluation_id,
            requests=tuple(requests),
            required_count=len(required),
            random_sample_count=len(sampled),
            maximum_burden=TEST_MAXIMUM_AUDIT_BURDEN,
            state=state,
            policy_version=TEST_AUDIT_POLICY_VERSION,
        )

    @staticmethod
    def _sample_key(evaluation_id: str, topic_id: str, candidate_id: str) -> str:
        value = "|".join(
            (
                TEST_RANDOM_SEED,
                TEST_SAMPLING_VERSION,
                evaluation_id,
                topic_id,
                candidate_id,
            )
        )
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _request(
        *,
        evaluation_id: str,
        candidate: EvaluationCandidate,
        consensus: JudgmentConsensus,
        audit_type: HumanAuditType,
        reasons: tuple[HumanAuditReason, ...],
    ) -> HumanAuditRequest:
        request_id = canonical_hash(
            {
                "evaluation_id": evaluation_id,
                "candidate_id": candidate.candidate_id,
                "consensus_checksum": consensus.checksum,
                "audit_type": audit_type.value,
                "sampling_version": TEST_SAMPLING_VERSION,
            }
        )
        return HumanAuditRequest(
            audit_request_id=request_id,
            evaluation_id=evaluation_id,
            topic_id=candidate.topic_id,
            candidate_id=candidate.candidate_id,
            proposed_silver_label=consensus.proposed_silver_label,
            audit_reasons=reasons,
            judgment_ids=consensus.source_judgment_ids,
            consensus_checksum=consensus.checksum,
            candidate_checksum=candidate.identity_hash,
            audit_type=audit_type,
            sampling_seed=TEST_RANDOM_SEED,
            sampling_version=TEST_SAMPLING_VERSION,
            status=HumanAuditStatus.PENDING,
            created_at=_CREATED_AT,
        )
