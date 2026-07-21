"""Deterministic fake skill definitions and implementations for contract tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.skill_system.exceptions import SkillExecutionFailure
from backend.skill_system.models import (
    SkillDefinition,
    SkillExecutionContext,
    SkillMetadata,
)
from backend.skill_system.registry import SkillRegistry
from backend.skill_system.schemas import FieldSchema, SkillSchema


MOCK_PAPER_SEARCH = SkillDefinition(
    name="mock_paper_search",
    version="1.0.0",
    description="Return deterministic mock paper titles for a research query.",
    input_schema=SkillSchema(
        fields={"query": FieldSchema(kind="string")},
    ),
    output_schema=SkillSchema(
        fields={"papers": FieldSchema(kind="array", items=FieldSchema(kind="string"))},
    ),
    metadata=SkillMetadata(
        side_effect="none",
        idempotency_supported=True,
        retry_safe=True,
        implementation_entrypoint="builtin:mock_paper_search",
    ),
)


MOCK_SUMMARY = SkillDefinition(
    name="mock_summary",
    version="1.0.0",
    description="Create a deterministic summary from mock paper titles.",
    input_schema=SkillSchema(
        fields={"papers": FieldSchema(kind="array", items=FieldSchema(kind="string"))},
    ),
    output_schema=SkillSchema(
        fields={"summary": FieldSchema(kind="string")},
    ),
    metadata=SkillMetadata(
        side_effect="none",
        idempotency_supported=True,
        retry_safe=True,
        implementation_entrypoint="builtin:mock_summary",
    ),
)


async def mock_paper_search(
    inputs: Mapping[str, Any],
    context: SkillExecutionContext,
) -> Mapping[str, Any]:
    del context
    query = inputs["query"].strip()
    if not query:
        raise SkillExecutionFailure(
            "EMPTY_QUERY",
            "query must contain non-whitespace text",
        )
    return {
        "papers": [
            f"Mock Foundations of {query}",
            f"Mock Advances in {query}",
        ]
    }


async def mock_summary(
    inputs: Mapping[str, Any],
    context: SkillExecutionContext,
) -> Mapping[str, Any]:
    del context
    papers = inputs["papers"]
    if not papers:
        raise SkillExecutionFailure(
            "EMPTY_PAPERS",
            "at least one paper is required to create a summary",
        )
    return {"summary": "Mock summary: " + "; ".join(papers)}


def register_fake_skills(registry: SkillRegistry) -> None:
    """Explicitly register the Phase 3 allow-listed deterministic skills."""

    registry.register(MOCK_PAPER_SEARCH, mock_paper_search)
    registry.register(MOCK_SUMMARY, mock_summary)
