"""Inactive Anthropic structured-output adapter substrate.

No SDK, network transport, credential lookup, or default composition wiring is
present.  Phase 9C-1 tests inject an in-memory transport.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from backend.research.contracts import (
    ProviderFailureCategory,
    ProviderOperationKind,
    ProviderUsage,
    canonical_hash,
    canonical_json,
)
from backend.research.ports import (
    ProviderError,
    ProviderIdentity,
    ProviderRequestContext,
    StructuredFinishState,
    StructuredGenerationProvider,
    StructuredGenerationRequest,
    StructuredGenerationResult,
)


class AnthropicStructuredTransport(Protocol):
    async def send(
        self,
        request: Mapping[str, Any],
        *,
        timeout_seconds: int,
    ) -> Mapping[str, Any]: ...

    async def cancel(self, provider_request_id: str) -> bool: ...


class AnthropicStructuredAdapter(StructuredGenerationProvider):
    """Protocol mapper targeting ``claude-sonnet-5`` without live reachability."""

    IDENTITY = ProviderIdentity(
        provider="anthropic",
        adapter_version="anthropic-structured-substrate/v1",
        model_or_endpoint="claude-sonnet-5",
    )

    def __init__(self, transport: AnthropicStructuredTransport) -> None:
        self._transport = transport

    @property
    def identity(self) -> ProviderIdentity:
        return self.IDENTITY

    async def generate(
        self,
        request: StructuredGenerationRequest,
        *,
        context: ProviderRequestContext,
    ) -> StructuredGenerationResult:
        if context.cancellation_requested:
            raise ProviderError(
                ProviderFailureCategory.CANCELLED,
                "Structured generation was cancelled before transport execution",
                retryable=False,
            )
        wire_request = {
            "model": self.identity.model_or_endpoint,
            "max_tokens": request.maximum_output_tokens,
            "system": request.system_instruction,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "SOURCE_DATA_BEGIN\n"
                        + canonical_json(request.untrusted_data_payload)
                        + "\nSOURCE_DATA_END"
                    ),
                }
            ],
            "output_config": {
                "format": {
                    "type": "json_schema",
                    "schema": dict(request.structured_output_schema),
                }
            },
            "metadata": {
                "request_fingerprint": request.request_fingerprint,
                "prompt_version": request.prompt_version,
                "prompt_hash": request.prompt_hash,
            },
        }
        try:
            response = await self._transport.send(
                wire_request,
                timeout_seconds=request.timeout_seconds,
            )
        except TimeoutError as error:
            raise ProviderError(
                ProviderFailureCategory.PROVIDER_TIMEOUT,
                "Anthropic transport timed out",
                retryable=True,
                safe_details={"adapter": self.identity.adapter_version},
            ) from error
        except ProviderError:
            raise
        except Exception as error:
            raise ProviderError(
                ProviderFailureCategory.PROVIDER_UNAVAILABLE,
                "Anthropic transport failed",
                retryable=True,
                safe_details={"adapter": self.identity.adapter_version},
            ) from error
        try:
            value = response["structured_value"]
            usage_data = response["usage"]
            request_id = str(response["request_id"])
            stop_reason = str(response.get("stop_reason", "end_turn"))
            if not isinstance(value, Mapping) or not isinstance(usage_data, Mapping):
                raise TypeError("invalid structured response fields")
            usage = ProviderUsage(
                provider=self.identity.provider,
                model_or_endpoint=self.identity.model_or_endpoint,
                operation_kind=ProviderOperationKind.GENERATE_STRUCTURED,
                request_count=1,
                input_tokens=int(usage_data["input_tokens"]),
                output_tokens=int(usage_data["output_tokens"]),
                estimated_cost_minor_units=int(
                    usage_data.get("estimated_cost_minor_units", 0)
                ),
                cost_currency=str(usage_data.get("cost_currency", "USD")),
                latency_ms=int(response.get("latency_ms", 0)),
                retry_count=int(response.get("retry_count", 0)),
                provider_request_ids=(request_id,),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ProviderError(
                ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE,
                "Anthropic response did not satisfy the normalized contract",
                retryable=False,
                safe_details={"adapter": self.identity.adapter_version},
            ) from error
        finish = {
            "end_turn": StructuredFinishState.COMPLETE,
            "max_tokens": StructuredFinishState.MAX_TOKENS,
            "refusal": StructuredFinishState.REFUSED,
        }.get(stop_reason, StructuredFinishState.COMPLETE)
        normalized = dict(value)
        return StructuredGenerationResult(
            provider_identity=self.identity.provider,
            model_identity=self.identity.model_or_endpoint,
            model_version=str(response.get("model", self.identity.model_or_endpoint)),
            adapter_version=self.identity.adapter_version,
            provider_request_id=request_id,
            normalized_value=normalized,
            raw_text_retained=False,
            usage=usage,
            estimated_cost_minor_units=usage.estimated_cost_minor_units or 0,
            cost_currency=usage.cost_currency or "USD",
            latency_ms=usage.latency_ms,
            retry_count=usage.retry_count,
            finish_state=finish,
            response_checksum=canonical_hash(normalized),
            schema_version="structured-generation-result/v1",
        )

    async def cancel(self, provider_request_id: str) -> bool:
        return await self._transport.cancel(provider_request_id)
