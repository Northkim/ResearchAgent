"""Provider-independent automated relevance judge boundary."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from backend.research.contracts import ProviderFailureCategory, ProviderUsage

from .silver_contracts import (
    AutomatedJudgment,
    AutomatedJudgmentRequest,
    PairwiseJudgmentRequest,
)


@dataclass(frozen=True, slots=True)
class JudgeIdentity:
    provider: str
    model: str
    model_version: str
    adapter_version: str


@dataclass(frozen=True, slots=True)
class JudgeCallContext:
    run_index: int
    timeout_seconds: int
    cancellation_requested: bool = False


@dataclass(frozen=True, slots=True)
class PairwisePreference:
    preferred_candidate_id: str
    reason: str
    usage: ProviderUsage


class AutomatedJudgeError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        category: ProviderFailureCategory,
        provider_call_started: bool = True,
    ) -> None:
        self.category = category
        self.provider_call_started = provider_call_started
        super().__init__(message)


class AutomatedRelevanceJudge(ABC):
    @property
    @abstractmethod
    def identity(self) -> JudgeIdentity: ...

    @abstractmethod
    def judge(
        self,
        request: AutomatedJudgmentRequest,
        *,
        context: JudgeCallContext,
    ) -> AutomatedJudgment: ...

    @abstractmethod
    def compare(
        self,
        request: PairwiseJudgmentRequest,
        *,
        context: JudgeCallContext,
    ) -> PairwisePreference: ...
