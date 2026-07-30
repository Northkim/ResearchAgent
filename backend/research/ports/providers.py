"""Framework-independent provider ports and normalized result envelopes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from backend.research.contracts import (
    FieldRejectionDiagnostic,
    PaperRecord,
    ProviderFailureCategory,
    ProviderUsage,
    ResearchQuery,
    SearchExecution,
    SearchPlan,
    SearchStatistics,
    SourceContent,
)
from backend.research.contracts._serialization import freeze_json, require_aware, require_non_empty


@dataclass(frozen=True, slots=True)
class ProviderIdentity:
    provider: str
    adapter_version: str
    model_or_endpoint: str

    def __post_init__(self) -> None:
        require_non_empty(self.provider, "ProviderIdentity.provider")
        require_non_empty(self.adapter_version, "ProviderIdentity.adapter_version")
        require_non_empty(self.model_or_endpoint, "ProviderIdentity.model_or_endpoint")


@dataclass(frozen=True, slots=True)
class ProviderRequestContext:
    operation_id: str
    idempotency_key: str
    request_fingerprint: str
    deadline: datetime | None = None
    cancellation_requested: bool = False

    def __post_init__(self) -> None:
        require_non_empty(self.operation_id, "ProviderRequestContext.operation_id")
        require_non_empty(self.idempotency_key, "ProviderRequestContext.idempotency_key")
        require_non_empty(self.request_fingerprint, "ProviderRequestContext.request_fingerprint")
        if self.deadline is not None:
            require_aware(self.deadline, "ProviderRequestContext.deadline")


class ProviderError(RuntimeError):
    """Normalized provider failure; raw SDK objects never cross the port."""

    def __init__(
        self,
        category: ProviderFailureCategory,
        message: str,
        *,
        retryable: bool,
        safe_details: Mapping[str, Any] | None = None,
    ) -> None:
        self.category = category
        self.retryable = retryable
        self.safe_details = freeze_json(safe_details or {})
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class PaperSearchResult:
    papers: tuple[PaperRecord, ...]
    usage: ProviderUsage
    request_fingerprint: str
    retrieved_at: datetime
    complete: bool = True
    warnings: tuple[str, ...] = ()
    search_plan: SearchPlan | None = None
    search_execution: SearchExecution | None = None
    search_statistics: SearchStatistics | None = None
    rejection_diagnostics: tuple[FieldRejectionDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "papers", tuple(self.papers))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(
            self,
            "rejection_diagnostics",
            tuple(self.rejection_diagnostics),
        )
        require_aware(self.retrieved_at, "PaperSearchResult.retrieved_at")
        evidence = (self.search_plan, self.search_execution, self.search_statistics)
        if any(item is not None for item in evidence) and not all(
            item is not None for item in evidence
        ):
            raise ValueError("PaperSearchResult search evidence must be all-or-none")


@dataclass(frozen=True, slots=True)
class SourceContentResult:
    content: SourceContent
    usage: ProviderUsage


@dataclass(frozen=True, slots=True)
class LLMTextRequest:
    prompt_name: str
    prompt_version: str
    messages: tuple[Mapping[str, Any], ...]
    max_output_tokens: int
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_empty(self.prompt_name, "LLMTextRequest.prompt_name")
        require_non_empty(self.prompt_version, "LLMTextRequest.prompt_version")
        if self.max_output_tokens <= 0:
            raise ValueError("LLMTextRequest.max_output_tokens must be positive")
        object.__setattr__(self, "messages", tuple(freeze_json(item) for item in self.messages))
        object.__setattr__(self, "metadata", freeze_json(self.metadata))


@dataclass(frozen=True, slots=True)
class LLMStructuredRequest(LLMTextRequest):
    response_schema: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super(LLMStructuredRequest, self).__post_init__()
        if not self.response_schema:
            raise ValueError("LLMStructuredRequest.response_schema cannot be empty")
        object.__setattr__(self, "response_schema", freeze_json(self.response_schema))


@dataclass(frozen=True, slots=True)
class LLMTextResponse:
    text: str
    usage: ProviderUsage
    actual_identity: ProviderIdentity
    prompt_version: str
    finish_reason: str
    provider_request_ref: str | None = None


@dataclass(frozen=True, slots=True)
class LLMStructuredResponse:
    value: Mapping[str, Any]
    usage: ProviderUsage
    actual_identity: ProviderIdentity
    prompt_version: str
    finish_reason: str
    provider_request_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", freeze_json(self.value))


class PaperSearchProvider(ABC):
    @property
    @abstractmethod
    def identity(self) -> ProviderIdentity: ...

    def request_identity(
        self,
        query: ResearchQuery,
        *,
        limit: int,
    ) -> Mapping[str, Any]:
        """Return provider-specific, credential-free request identity metadata."""

        return {"query": query.to_dict(), "limit": limit}

    @abstractmethod
    async def search(
        self,
        query: ResearchQuery,
        *,
        limit: int,
        context: ProviderRequestContext,
    ) -> PaperSearchResult: ...


class SourceContentProvider(ABC):
    @property
    @abstractmethod
    def identity(self) -> ProviderIdentity: ...

    @abstractmethod
    async def retrieve(
        self,
        paper: PaperRecord,
        *,
        requested_scope: str,
        context: ProviderRequestContext,
    ) -> SourceContentResult: ...


class LLMProvider(ABC):
    @property
    @abstractmethod
    def identity(self) -> ProviderIdentity: ...

    @abstractmethod
    async def generate_text(
        self,
        request: LLMTextRequest,
        *,
        context: ProviderRequestContext,
    ) -> LLMTextResponse: ...

    @abstractmethod
    async def generate_structured(
        self,
        request: LLMStructuredRequest,
        *,
        context: ProviderRequestContext,
    ) -> LLMStructuredResponse: ...

    @abstractmethod
    async def cancel(self, provider_request_ref: str) -> bool: ...


class StructuredFinishState(str, Enum):
    COMPLETE = "COMPLETE"
    MAX_TOKENS = "MAX_TOKENS"
    REFUSED = "REFUSED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class StructuredGenerationRequest:
    operation_kind: str
    model_policy: Mapping[str, Any]
    prompt_version: str
    prompt_hash: str
    system_instruction: str
    untrusted_data_payload: Mapping[str, Any]
    structured_output_schema: Mapping[str, Any]
    maximum_output_tokens: int
    timeout_seconds: int
    request_fingerprint: str
    input_checksum: str
    schema_version: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.operation_kind, "operation_kind"),
            (self.prompt_version, "prompt_version"),
            (self.prompt_hash, "prompt_hash"),
            (self.system_instruction, "system_instruction"),
            (self.request_fingerprint, "request_fingerprint"),
            (self.input_checksum, "input_checksum"),
            (self.schema_version, "schema_version"),
        ):
            require_non_empty(value, f"StructuredGenerationRequest.{name}")
        if self.maximum_output_tokens <= 0 or self.timeout_seconds <= 0:
            raise ValueError("Structured generation token/timeout limits must be positive")
        object.__setattr__(self, "model_policy", freeze_json(self.model_policy))
        object.__setattr__(
            self, "untrusted_data_payload", freeze_json(self.untrusted_data_payload)
        )
        object.__setattr__(
            self, "structured_output_schema", freeze_json(self.structured_output_schema)
        )


@dataclass(frozen=True, slots=True)
class StructuredGenerationResult:
    provider_identity: str
    model_identity: str
    model_version: str
    adapter_version: str
    provider_request_id: str
    normalized_value: Mapping[str, Any]
    raw_text_retained: bool
    usage: ProviderUsage
    estimated_cost_minor_units: int
    cost_currency: str
    latency_ms: int
    retry_count: int
    finish_state: StructuredFinishState
    response_checksum: str
    schema_version: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.provider_identity, "provider_identity"),
            (self.model_identity, "model_identity"),
            (self.model_version, "model_version"),
            (self.adapter_version, "adapter_version"),
            (self.provider_request_id, "provider_request_id"),
            (self.cost_currency, "cost_currency"),
            (self.response_checksum, "response_checksum"),
            (self.schema_version, "schema_version"),
        ):
            require_non_empty(value, f"StructuredGenerationResult.{name}")
        if min(
            self.estimated_cost_minor_units,
            self.latency_ms,
            self.retry_count,
        ) < 0:
            raise ValueError("Structured generation counters cannot be negative")
        object.__setattr__(self, "normalized_value", freeze_json(self.normalized_value))


class StructuredGenerationProvider(ABC):
    """Provider-independent structured generation port used by V3 only."""

    @property
    @abstractmethod
    def identity(self) -> ProviderIdentity: ...

    @abstractmethod
    async def generate(
        self,
        request: StructuredGenerationRequest,
        *,
        context: ProviderRequestContext,
    ) -> StructuredGenerationResult: ...

    @abstractmethod
    async def cancel(self, provider_request_id: str) -> bool: ...
