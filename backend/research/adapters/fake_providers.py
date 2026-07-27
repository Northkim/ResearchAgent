"""Network-free deterministic research provider adapters."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from backend.research.contracts import (
    AccessLimitation,
    ContentType,
    PaperAuthor,
    PaperRecord,
    ProviderFailureCategory,
    ProviderOperationKind,
    ProviderUsage,
    ResearchQuery,
    SourceContent,
    canonical_hash,
    sha256_bytes,
)
from backend.research.ports import (
    LLMProvider,
    LLMStructuredRequest,
    LLMStructuredResponse,
    LLMTextRequest,
    LLMTextResponse,
    PaperSearchProvider,
    PaperSearchResult,
    ProviderError,
    ProviderIdentity,
    ProviderRequestContext,
    SourceContentProvider,
    SourceContentResult,
)

_FIXED_TIME = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)


class _FailureMixin:
    def __init__(
        self,
        *,
        failure: ProviderFailureCategory | None = None,
    ) -> None:
        self._failure = failure

    def _raise_if_configured(self, context: ProviderRequestContext) -> None:
        if context.cancellation_requested:
            raise ProviderError(
                ProviderFailureCategory.CANCELLED,
                "Deterministic provider request was cancelled",
                retryable=False,
            )
        if self._failure is not None:
            raise ProviderError(
                self._failure,
                "Configured deterministic provider failure",
                retryable=self._failure
                in {
                    ProviderFailureCategory.PROVIDER_RATE_LIMIT,
                    ProviderFailureCategory.PROVIDER_TIMEOUT,
                    ProviderFailureCategory.PROVIDER_UNAVAILABLE,
                },
                safe_details={"fake": True},
            )


class FakePaperSearchProvider(_FailureMixin, PaperSearchProvider):
    IDENTITY = ProviderIdentity(
        provider="synthetic-paper-search",
        adapter_version="1.0.0",
        model_or_endpoint="synthetic-catalog/v1",
    )

    @property
    def identity(self) -> ProviderIdentity:
        return self.IDENTITY

    async def search(
        self,
        query: ResearchQuery,
        *,
        limit: int,
        context: ProviderRequestContext,
    ) -> PaperSearchResult:
        self._raise_if_configured(context)
        if limit <= 0:
            raise ProviderError(
                ProviderFailureCategory.INVALID_QUERY,
                "Search limit must be positive",
                retryable=False,
            )
        papers = tuple(self._paper(query, index) for index in range(1, 4))[:limit]
        return PaperSearchResult(
            papers=papers,
            usage=ProviderUsage.zero_cost(
                provider=self.identity.provider,
                model_or_endpoint=self.identity.model_or_endpoint,
                operation_kind=ProviderOperationKind.SEARCH,
            ),
            request_fingerprint=context.request_fingerprint,
            retrieved_at=_FIXED_TIME,
        )

    def _paper(self, query: ResearchQuery, index: int) -> PaperRecord:
        provider_id = f"synthetic-{index}"
        title = (
            f"Synthetic Foundations of {query.topic}"
            if index == 1
            else f"Synthetic Study {index} of {query.topic}"
        )
        abstract = (
            f"Synthetic abstract {index}: this fixture discusses {query.topic} "
            "using invented, non-copyrighted evidence for deterministic tests."
        )
        raw = {
            "id": provider_id,
            "title": title,
            "abstract": abstract,
            "year": 2020 + index,
        }
        doi = f"10.5555/synthetic.{index}"
        return PaperRecord(
            paper_id=PaperRecord.internal_id(
                provider=self.identity.provider,
                provider_id=provider_id,
                doi=doi,
            ),
            provider_id=provider_id,
            title=title,
            authors=(PaperAuthor(name=f"Synthetic Author {index}"),),
            abstract=abstract,
            publication_year=2020 + index,
            publication_venue="Synthetic Research Fixtures",
            source_provider=f"{self.identity.provider}@{self.identity.adapter_version}",
            source_url=f"https://example.invalid/papers/{provider_id}",
            doi=doi,
            retrieved_at=_FIXED_TIME,
            raw_metadata_hash=canonical_hash(raw),
        )


class FakeSourceContentProvider(_FailureMixin, SourceContentProvider):
    IDENTITY = ProviderIdentity(
        provider="synthetic-source-content",
        adapter_version="1.0.0",
        model_or_endpoint="synthetic-abstracts/v1",
    )

    @property
    def identity(self) -> ProviderIdentity:
        return self.IDENTITY

    async def retrieve(
        self,
        paper: PaperRecord,
        *,
        requested_scope: str,
        context: ProviderRequestContext,
    ) -> SourceContentResult:
        self._raise_if_configured(context)
        if requested_scope not in {"abstract", "full_text"}:
            raise ProviderError(
                ProviderFailureCategory.INVALID_QUERY,
                "Unsupported requested source scope",
                retryable=False,
            )
        if paper.abstract is None:
            raise ProviderError(
                ProviderFailureCategory.CONTENT_UNAVAILABLE,
                "Synthetic paper has no abstract",
                retryable=False,
            )
        content = SourceContent(
            paper_id=paper.paper_id,
            content_type=ContentType.ABSTRACT,
            abstract=paper.abstract,
            full_text=None,
            content_source=f"{self.identity.provider}@{self.identity.adapter_version}",
            source_url=paper.source_url,
            retrieved_at=_FIXED_TIME,
            content_hash=sha256_bytes(paper.abstract.encode("utf-8")),
            access_limitation=AccessLimitation.ABSTRACT_ONLY,
            license_or_usage_metadata={"fixture": "synthetic", "redistributable": True},
        )
        return SourceContentResult(
            content=content,
            usage=ProviderUsage.zero_cost(
                provider=self.identity.provider,
                model_or_endpoint=self.identity.model_or_endpoint,
                operation_kind=ProviderOperationKind.RETRIEVE,
            ),
        )


class FakeLLMProvider(_FailureMixin, LLMProvider):
    IDENTITY = ProviderIdentity(
        provider="synthetic-llm",
        adapter_version="1.0.0",
        model_or_endpoint="deterministic-structured/v1",
    )

    @property
    def identity(self) -> ProviderIdentity:
        return self.IDENTITY

    async def generate_text(
        self,
        request: LLMTextRequest,
        *,
        context: ProviderRequestContext,
    ) -> LLMTextResponse:
        self._raise_if_configured(context)
        topic = str(request.metadata.get("topic", "the research topic"))
        return LLMTextResponse(
            text=f"Deterministic synthetic synthesis for {topic}.",
            usage=self._usage(ProviderOperationKind.GENERATE_TEXT),
            actual_identity=self.identity,
            prompt_version=request.prompt_version,
            finish_reason="stop",
            provider_request_ref="fake-request-text",
        )

    async def generate_structured(
        self,
        request: LLMStructuredRequest,
        *,
        context: ProviderRequestContext,
    ) -> LLMStructuredResponse:
        self._raise_if_configured(context)
        value: dict[str, Any] = {
            "summary": "Deterministic synthetic structured summary.",
            "prompt_version": request.prompt_version,
            "grounded": True,
        }
        expected = request.metadata.get("deterministic_output")
        if isinstance(expected, Mapping):
            value = dict(expected)
        return LLMStructuredResponse(
            value=value,
            usage=self._usage(ProviderOperationKind.GENERATE_STRUCTURED),
            actual_identity=self.identity,
            prompt_version=request.prompt_version,
            finish_reason="stop",
            provider_request_ref="fake-request-structured",
        )

    async def cancel(self, provider_request_ref: str) -> bool:
        del provider_request_ref
        return True

    def _usage(self, operation_kind: ProviderOperationKind) -> ProviderUsage:
        return ProviderUsage.zero_cost(
            provider=self.identity.provider,
            model_or_endpoint=self.identity.model_or_endpoint,
            operation_kind=operation_kind,
        )
