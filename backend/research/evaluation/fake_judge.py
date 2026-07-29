"""Fixture-driven Fake Automated Relevance Judge; never interprets candidate text."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from collections.abc import Mapping
from typing import Any

from backend.research.contracts import (
    ProviderFailureCategory,
    ProviderOperationKind,
    ProviderUsage,
    canonical_hash,
)

from .contracts import RelevanceLabel
from .judge_port import (
    AutomatedJudgeError,
    AutomatedRelevanceJudge,
    JudgeCallContext,
    JudgeIdentity,
    PairwisePreference,
)
from .prompts import JudgePromptRegistry
from .silver_contracts import (
    AutomatedJudgment,
    AutomatedJudgmentRequest,
    JudgmentMode,
    PairwiseJudgmentRequest,
    SupportingSpan,
)

FAKE_PROVIDER = "synthetic-relevance-judge"
FAKE_MODEL = "fixture-driven-relevance/v1"
FAKE_MODEL_VERSION = "synthetic-snapshot-2026-07-29"
FAKE_ADAPTER_VERSION = "fake-relevance-judge-adapter/v1"
_FIXED_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class FakePointwiseBehavior:
    label: RelevanceLabel
    confidence: float
    supporting_text: str | None
    reason: str
    uncertainties: tuple[str, ...] = ()
    insufficient_information: bool = False
    malformed: bool = False
    timeout: bool = False
    failure: bool = False


@dataclass(frozen=True, slots=True)
class FakePairwiseBehavior:
    preferred_candidate_id: str
    mirrored_preferred_candidate_id: str | None = None
    reason: str = "Synthetic fixture preference."


class FakeAutomatedRelevanceJudge(AutomatedRelevanceJudge):
    """Configurable test double with explicit behavior for every accepted request."""

    def __init__(
        self,
        *,
        pointwise: Mapping[tuple[str, str], FakePointwiseBehavior],
        pairwise: Mapping[frozenset[str], FakePairwiseBehavior] | None = None,
        prompt_registry: JudgePromptRegistry | None = None,
    ) -> None:
        self._pointwise = dict(pointwise)
        self._pairwise = dict(pairwise or {})
        self._registry = prompt_registry or JudgePromptRegistry()
        self.call_log: list[tuple[str, str, int]] = []

    @property
    def identity(self) -> JudgeIdentity:
        return JudgeIdentity(
            provider=FAKE_PROVIDER,
            model=FAKE_MODEL,
            model_version=FAKE_MODEL_VERSION,
            adapter_version=FAKE_ADAPTER_VERSION,
        )

    def judge(
        self,
        request: AutomatedJudgmentRequest,
        *,
        context: JudgeCallContext,
    ) -> AutomatedJudgment:
        self.call_log.append(("pointwise", request.candidate_id, context.run_index))
        if context.cancellation_requested:
            raise AutomatedJudgeError(
                "Synthetic call cancelled",
                category=ProviderFailureCategory.CANCELLED,
                provider_call_started=False,
            )
        behavior = self._pointwise.get((request.candidate_id, request.prompt_version))
        if behavior is None:
            raise AutomatedJudgeError(
                "No synthetic behavior configured for request",
                category=ProviderFailureCategory.PROVENANCE_VALIDATION,
                provider_call_started=False,
            )
        if behavior.timeout:
            raise AutomatedJudgeError(
                "Synthetic timeout",
                category=ProviderFailureCategory.PROVIDER_TIMEOUT,
            )
        if behavior.failure:
            raise AutomatedJudgeError(
                "Synthetic provider failure",
                category=ProviderFailureCategory.PROVIDER_UNAVAILABLE,
            )
        if behavior.malformed:
            raise AutomatedJudgeError(
                "Synthetic malformed structured output",
                category=ProviderFailureCategory.LLM_STRUCTURED_OUTPUT,
            )
        spans: tuple[SupportingSpan, ...] = ()
        if behavior.supporting_text:
            preview = request.bounded_abstract_preview or ""
            start = preview.find(behavior.supporting_text)
            if start < 0:
                raise AutomatedJudgeError(
                    "Configured supporting span is absent from synthetic preview",
                    category=ProviderFailureCategory.PROVENANCE_VALIDATION,
                    provider_call_started=False,
                )
            spans = (
                SupportingSpan(
                    text=behavior.supporting_text,
                    start=start,
                    end=start + len(behavior.supporting_text),
                ),
            )
        usage = self._usage()
        prompt = self._registry.get(request.prompt_version)
        return AutomatedJudgment(
            judgment_id=canonical_hash(
                {
                    "request_checksum": request.request_checksum,
                    "run_index": context.run_index,
                    "fake_adapter": FAKE_ADAPTER_VERSION,
                }
            ),
            evaluation_id=request.evaluation_id,
            topic_id=request.topic_id,
            candidate_id=request.candidate_id,
            run_index=context.run_index,
            judgment_mode=JudgmentMode.POINTWISE,
            judge_provider=FAKE_PROVIDER,
            judge_model=FAKE_MODEL,
            model_version=FAKE_MODEL_VERSION,
            adapter_version=FAKE_ADAPTER_VERSION,
            prompt_version=request.prompt_version,
            prompt_hash=prompt.prompt_hash,
            rubric_version=request.rubric_version,
            label=behavior.label,
            confidence=behavior.confidence,
            supporting_spans=spans,
            concise_reason=behavior.reason,
            uncertainties=behavior.uncertainties,
            insufficient_information=behavior.insufficient_information,
            input_checksum=request.request_checksum,
            usage=usage,
            latency_ms=usage.latency_ms,
            created_at=_FIXED_CREATED_AT,
        )

    def compare(
        self,
        request: PairwiseJudgmentRequest,
        *,
        context: JudgeCallContext,
    ) -> PairwisePreference:
        self.call_log.append(
            (
                "pairwise",
                f"{request.left_candidate_id}|{request.right_candidate_id}",
                context.run_index,
            )
        )
        behavior = self._pairwise.get(
            frozenset((request.left_candidate_id, request.right_candidate_id))
        )
        if behavior is None:
            raise AutomatedJudgeError(
                "No synthetic pairwise behavior configured",
                category=ProviderFailureCategory.PROVENANCE_VALIDATION,
                provider_call_started=False,
            )
        canonical_left = min(request.left_candidate_id, request.right_candidate_id)
        preferred = (
            behavior.preferred_candidate_id
            if request.left_candidate_id == canonical_left
            else behavior.mirrored_preferred_candidate_id
            or behavior.preferred_candidate_id
        )
        if preferred not in {
            request.left_candidate_id,
            request.right_candidate_id,
            "TIE",
        }:
            raise AutomatedJudgeError(
                "Synthetic pairwise fixture returned an unknown candidate",
                category=ProviderFailureCategory.LLM_STRUCTURED_OUTPUT,
            )
        return PairwisePreference(
            preferred_candidate_id=preferred,
            reason=behavior.reason,
            usage=self._usage(),
        )

    @staticmethod
    def _usage() -> ProviderUsage:
        return ProviderUsage(
            provider=FAKE_PROVIDER,
            model_or_endpoint=FAKE_MODEL,
            operation_kind=ProviderOperationKind.GENERATE_STRUCTURED,
            request_count=1,
            input_tokens=64,
            output_tokens=24,
            estimated_cost_minor_units=0,
            cost_currency="USD",
            latency_ms=1,
            retry_count=0,
            provider_request_ids=(),
        )


def pointwise_behaviors_from_fixture(
    candidates: tuple[Mapping[str, Any], ...],
) -> dict[tuple[str, str], FakePointwiseBehavior]:
    result: dict[tuple[str, str], FakePointwiseBehavior] = {}
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        for prompt_version, value in dict(candidate["pointwise"]).items():
            result[(candidate_id, prompt_version)] = FakePointwiseBehavior(
                label=RelevanceLabel(str(value.get("label", "CANNOT_JUDGE"))),
                confidence=float(value.get("confidence", 0)),
                supporting_text=value.get("supporting_text"),
                reason=str(value.get("reason", "Synthetic fixture result.")),
                uncertainties=tuple(value.get("uncertainties", ())),
                insufficient_information=bool(
                    value.get("insufficient_information", False)
                ),
                malformed=bool(value.get("malformed", False)),
                timeout=bool(value.get("timeout", False)),
                failure=bool(value.get("failure", False)),
            )
    return result
