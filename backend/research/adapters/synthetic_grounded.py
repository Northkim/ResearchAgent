"""Fixture-driven, deterministic structured-generation provider for V3."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from backend.research.contracts import (
    ProviderFailureCategory,
    ProviderOperationKind,
    ProviderUsage,
    canonical_hash,
)
from backend.research.ports import (
    PaperSearchProvider,
    PaperSearchResult,
    ProviderError,
    ProviderIdentity,
    ProviderRequestContext,
    StructuredFinishState,
    StructuredGenerationProvider,
    StructuredGenerationRequest,
    StructuredGenerationResult,
)
from backend.research.synthetic_grounded_fixtures import FIXED_TIME, papers


class SyntheticGroundedProvider(StructuredGenerationProvider):
    IDENTITY = ProviderIdentity(
        provider="synthetic-grounded-generation",
        adapter_version="fixture-structured-adapter/v1",
        model_or_endpoint="fixture-driven-grounding/v1",
    )

    def __init__(
        self,
        responses: Mapping[str, Mapping[str, Any]],
        *,
        failures: Mapping[str, ProviderFailureCategory] | None = None,
    ) -> None:
        self._responses = MappingProxyType(
            {key: MappingProxyType(dict(value)) for key, value in responses.items()}
        )
        self._failures = MappingProxyType(dict(failures or {}))
        self.calls: Counter[str] = Counter()

    @property
    def identity(self) -> ProviderIdentity:
        return self.IDENTITY

    async def generate(
        self,
        request: StructuredGenerationRequest,
        *,
        context: ProviderRequestContext,
    ) -> StructuredGenerationResult:
        fixture_key = request.untrusted_data_payload.get("fixture_key")
        if not isinstance(fixture_key, str) or not fixture_key:
            raise ProviderError(
                ProviderFailureCategory.INVALID_QUERY,
                "Synthetic grounded requests require an explicit fixture_key",
                retryable=False,
            )
        self.calls[fixture_key] += 1
        if context.cancellation_requested:
            raise ProviderError(
                ProviderFailureCategory.CANCELLED,
                "Synthetic grounded request was cancelled",
                retryable=False,
            )
        failure = self._failures.get(fixture_key)
        if failure is not None:
            raise ProviderError(
                failure,
                "Configured synthetic grounded provider failure",
                retryable=failure
                in {
                    ProviderFailureCategory.PROVIDER_TIMEOUT,
                    ProviderFailureCategory.PROVIDER_UNAVAILABLE,
                    ProviderFailureCategory.PROVIDER_RATE_LIMIT,
                },
                safe_details={"synthetic": True},
            )
        try:
            value = dict(self._responses[fixture_key])
        except KeyError as error:
            raise ProviderError(
                ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE,
                f"No committed synthetic response exists for {fixture_key}",
                retryable=False,
                safe_details={"synthetic": True, "fixture_key": fixture_key},
            ) from error
        usage = ProviderUsage(
            provider=self.identity.provider,
            model_or_endpoint=self.identity.model_or_endpoint,
            operation_kind=ProviderOperationKind.GENERATE_STRUCTURED,
            request_count=1,
            input_tokens=100 + len(fixture_key),
            output_tokens=50 + len(value),
            estimated_cost_minor_units=0,
            cost_currency="USD",
            latency_ms=1,
            retry_count=0,
            provider_request_ids=(
                "synthetic-request-"
                + canonical_hash(
                    {"fixture_key": fixture_key, "request": request.request_fingerprint}
                )[7:23],
            ),
        )
        return StructuredGenerationResult(
            provider_identity=self.identity.provider,
            model_identity=self.identity.model_or_endpoint,
            model_version="fixture-snapshot-2026-07-30",
            adapter_version=self.identity.adapter_version,
            provider_request_id=usage.provider_request_ids[0],
            normalized_value=value,
            raw_text_retained=False,
            usage=usage,
            estimated_cost_minor_units=0,
            cost_currency="USD",
            latency_ms=1,
            retry_count=0,
            finish_state=StructuredFinishState.COMPLETE,
            response_checksum=canonical_hash(value),
            schema_version="structured-generation-result/v1",
        )

    async def cancel(self, provider_request_id: str) -> bool:
        del provider_request_id
        return True


class SyntheticGroundedPaperSearchProvider(PaperSearchProvider):
    IDENTITY = ProviderIdentity(
        provider="synthetic-grounded-catalog",
        adapter_version="1.0.0",
        model_or_endpoint="fictional-catalog/v1",
    )

    @property
    def identity(self) -> ProviderIdentity:
        return self.IDENTITY

    async def search(self, query, *, limit: int, context: ProviderRequestContext):
        del query
        if limit < 3:
            raise ProviderError(
                ProviderFailureCategory.INVALID_QUERY,
                "V3 synthetic acceptance requires at least three papers",
                retryable=False,
            )
        selected = papers()[:limit]
        return PaperSearchResult(
            papers=selected,
            usage=ProviderUsage.zero_cost(
                provider=self.identity.provider,
                model_or_endpoint=self.identity.model_or_endpoint,
                operation_kind=ProviderOperationKind.SEARCH,
            ),
            request_fingerprint=context.request_fingerprint,
            retrieved_at=FIXED_TIME,
        )
