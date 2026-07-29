"""Composition-owned provider budget and live-execution policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from collections.abc import Mapping

from backend.research.contracts import ProviderBudget, ProviderReservation


@dataclass(frozen=True, slots=True)
class ProviderExecutionPolicy:
    """Policy injected into Skills; adapters never read process configuration."""

    budget: ProviderBudget = field(default_factory=ProviderBudget.fake_only_default)
    live_provider_names: frozenset[str] = frozenset()
    reservations: Mapping[str, ProviderReservation] = field(default_factory=dict)
    operation_timeout_seconds: int = 60

    def __post_init__(self) -> None:
        if self.operation_timeout_seconds <= 0:
            raise ValueError("operation_timeout_seconds must be positive")
        names = frozenset(name.strip() for name in self.live_provider_names)
        if any(not name for name in names):
            raise ValueError("live_provider_names cannot contain empty values")
        object.__setattr__(self, "live_provider_names", names)
        object.__setattr__(
            self,
            "reservations",
            MappingProxyType(dict(self.reservations)),
        )

    def reservation_for(self, provider: str) -> ProviderReservation:
        return self.reservations.get(provider, ProviderReservation())

    @classmethod
    def fake_only(cls) -> ProviderExecutionPolicy:
        return cls()

    @classmethod
    def supervised_openalex(cls) -> ProviderExecutionPolicy:
        return cls(
            budget=ProviderBudget(
                max_provider_requests=12,
                max_llm_calls=10,
                max_input_tokens=0,
                max_output_tokens=0,
                max_cost_minor_units=0,
                max_runtime_seconds=90,
                live_provider_enabled=True,
            ),
            live_provider_names=frozenset({"openalex"}),
            # One free-budget preflight plus initial Works request and two retries.
            reservations={"openalex": ProviderReservation(request_count=4)},
            operation_timeout_seconds=90,
        )

    @classmethod
    def supervised_multilingual_openalex(cls) -> ProviderExecutionPolicy:
        """Four one-page variants: one free-credit preflight and one Works call each."""

        return cls(
            budget=ProviderBudget(
                max_provider_requests=8,
                max_llm_calls=0,
                max_input_tokens=0,
                max_output_tokens=0,
                max_cost_minor_units=0,
                max_runtime_seconds=120,
                live_provider_enabled=True,
            ),
            live_provider_names=frozenset({"openalex"}),
            reservations={"openalex": ProviderReservation(request_count=2)},
            operation_timeout_seconds=30,
        )
