"""Network-free deterministic provider adapter tests."""

from __future__ import annotations

import asyncio

import pytest

from backend.research.adapters import (
    FakeLLMProvider,
    FakePaperSearchProvider,
    FakeSourceContentProvider,
)
from backend.research.contracts import (
    AccessLimitation,
    ContentType,
    ProviderFailureCategory,
    ResearchQuery,
    canonical_hash,
)
from backend.research.ports import (
    LLMStructuredRequest,
    LLMTextRequest,
    ProviderError,
    ProviderRequestContext,
)


def _context(*, cancelled: bool = False) -> ProviderRequestContext:
    return ProviderRequestContext(
        operation_id="operation-1",
        idempotency_key="synthetic-request-1",
        request_fingerprint=canonical_hash({"request": 1}),
        cancellation_requested=cancelled,
    )


def test_fake_search_is_stable_idempotent_and_zero_cost() -> None:
    provider = FakePaperSearchProvider()
    query = ResearchQuery(topic="synthetic research agents", max_results=3)
    first = asyncio.run(provider.search(query, limit=3, context=_context()))
    replay = asyncio.run(provider.search(query, limit=3, context=_context()))

    assert first == replay
    assert len(first.papers) == 3
    assert len({paper.paper_id for paper in first.papers}) == 3
    assert first.usage.estimated_cost_minor_units == 0
    assert all("Synthetic" in paper.title for paper in first.papers)


def test_fake_source_never_promotes_abstract_to_full_text() -> None:
    search = FakePaperSearchProvider()
    paper = asyncio.run(
        search.search(
            ResearchQuery(topic="synthetic scope"),
            limit=1,
            context=_context(),
        )
    ).papers[0]
    result = asyncio.run(
        FakeSourceContentProvider().retrieve(
            paper,
            requested_scope="full_text",
            context=_context(),
        )
    )

    assert result.content.content_type is ContentType.ABSTRACT
    assert result.content.full_text is None
    assert result.content.access_limitation is AccessLimitation.ABSTRACT_ONLY
    assert result.usage.estimated_cost_minor_units == 0


def test_fake_llm_text_and_structured_generation_are_deterministic() -> None:
    provider = FakeLLMProvider()
    text_request = LLMTextRequest(
        prompt_name="synthesis",
        prompt_version="synthesis/v1",
        messages=({"role": "user", "content": "Synthetic only"},),
        max_output_tokens=100,
        metadata={"topic": "synthetic research"},
    )
    structured_request = LLMStructuredRequest(
        prompt_name="summary",
        prompt_version="summary/v1",
        messages=({"role": "user", "content": "Synthetic only"},),
        max_output_tokens=100,
        response_schema={"type": "object"},
        metadata={"deterministic_output": {"summary": "fixed"}},
    )

    first_text = asyncio.run(provider.generate_text(text_request, context=_context()))
    second_text = asyncio.run(provider.generate_text(text_request, context=_context()))
    structured = asyncio.run(
        provider.generate_structured(structured_request, context=_context())
    )

    assert first_text == second_text
    assert structured.value == {"summary": "fixed"}
    assert first_text.usage.estimated_cost_minor_units == 0
    assert structured.usage.estimated_cost_minor_units == 0


def test_fake_provider_failure_is_normalized_and_configurable() -> None:
    provider = FakePaperSearchProvider(
        failure=ProviderFailureCategory.PROVIDER_TIMEOUT
    )
    with pytest.raises(ProviderError) as captured:
        asyncio.run(
            provider.search(
                ResearchQuery(topic="synthetic failure"),
                limit=3,
                context=_context(),
            )
        )
    assert captured.value.category is ProviderFailureCategory.PROVIDER_TIMEOUT
    assert captured.value.retryable
    assert captured.value.safe_details == {"fake": True}


def test_fake_provider_honors_pre_call_cancellation() -> None:
    with pytest.raises(ProviderError) as captured:
        asyncio.run(
            FakePaperSearchProvider().search(
                ResearchQuery(topic="synthetic cancellation"),
                limit=3,
                context=_context(cancelled=True),
            )
        )
    assert captured.value.category is ProviderFailureCategory.CANCELLED
    assert not captured.value.retryable
