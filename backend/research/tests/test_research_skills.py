"""Fast deterministic tests for the executable v2 research Skills."""

from __future__ import annotations

import asyncio
import pytest

from backend.demo.seed import (
    RESEARCH_WORKFLOW_HASH,
    load_research_workflow,
)
from backend.persistence.adapters import InMemoryUnitOfWork
from backend.research.adapters import (
    FakeLLMProvider,
    FakePaperSearchProvider,
    FakeSourceContentProvider,
    LocalFilesystemArtifactStorage,
)
from backend.research.services import ProviderOperationService
from backend.research.skills import (
    generate_research_report,
    normalize_paper_metadata,
    persist_research_artifacts,
    rank_and_select_papers,
    retrieve_source_content,
    search_papers,
    summarize_sources,
    synthesize_literature,
    validate_research_query,
)
from backend.skill_system.exceptions import SkillExecutionFailure
from backend.skill_system.models import SkillCapabilities, SkillExecutionContext


def _context(
    step_id: str,
    *,
    uow: InMemoryUnitOfWork,
    storage: LocalFilesystemArtifactStorage,
) -> SkillExecutionContext:
    return SkillExecutionContext(
        project_id="research-project",
        workflow_run_id="research-run",
        workflow_id="guided-literature-review",
        workflow_version="2.0.0",
        step_id=step_id,
        step_run_id=f"step-run-{step_id}",
        attempt=1,
        capabilities=SkillCapabilities(
            paper_search=FakePaperSearchProvider(),
            source_content=FakeSourceContentProvider(),
            llm=FakeLLMProvider(),
            artifact_storage=storage,
            provider_operations=ProviderOperationService(
                uow.provider_operations,
                commit_callback=uow.commit,
            ),
        ),
    )


async def _execute_valid_chain(tmp_path):
    uow = InMemoryUnitOfWork()
    storage = LocalFilesystemArtifactStorage(tmp_path / "artifacts")
    query = await validate_research_query(
        {
            "topic": "persistent research agent auditability",
            "year_from": 2020,
            "year_to": 2026,
            "max_papers": 3,
        },
        _context("validate_query", uow=uow, storage=storage),
    )
    search = await search_papers(
        {"query": query["query"]},
        _context("search_papers", uow=uow, storage=storage),
    )
    normalized = await normalize_paper_metadata(
        {"papers": search.output_data["papers"]},
        _context("normalize_and_deduplicate", uow=uow, storage=storage),
    )
    ranked = await rank_and_select_papers(
        {
            "query": query["query"],
            "papers": normalized.output_data["papers"],
            "max_papers": 3,
        },
        _context("rank_and_select", uow=uow, storage=storage),
    )
    retrieved = await retrieve_source_content(
        {
            "selected_papers": ranked.output_data["selected_papers"],
            "selected_paper_ids": ranked.output_data["selected_paper_ids"],
            "selected_papers_checksum": ranked.output_data[
                "selected_papers_checksum"
            ],
        },
        _context("retrieve_source_content", uow=uow, storage=storage),
    )
    summarized = await summarize_sources(
        {
            "selected_papers": ranked.output_data["selected_papers"],
            "source_contents": retrieved.output_data["source_contents"],
        },
        _context("summarize_sources", uow=uow, storage=storage),
    )
    synthesized = await synthesize_literature(
        {
            "paper_summaries": summarized.output_data["paper_summaries"],
            "evidence_units": summarized.output_data["evidence_units"],
        },
        _context("synthesize_findings", uow=uow, storage=storage),
    )
    report = await generate_research_report(
        {
            "query": query["query"],
            "selected_papers": ranked.output_data["selected_papers"],
            "ranked_papers": ranked.output_data["ranked_papers"],
            "paper_summaries": summarized.output_data["paper_summaries"],
            "synthesis": synthesized.output_data["synthesis"],
            "grounded_claims": synthesized.output_data["grounded_claims"],
        },
        _context("generate_report", uow=uow, storage=storage),
    )
    inputs = {
        "query": query["query"],
        "papers": normalized.output_data["papers"],
        "ranked_papers": ranked.output_data["ranked_papers"],
        "selected_papers": ranked.output_data["selected_papers"],
        "source_contents": retrieved.output_data["source_contents"],
        "paper_summaries": summarized.output_data["paper_summaries"],
        "evidence_units": synthesized.output_data["evidence_units"],
        "grounded_claims": synthesized.output_data["grounded_claims"],
        "report": report.output_data["report"],
        "citations": report.output_data["citations"],
        "workflow_hash": f"sha256:{RESEARCH_WORKFLOW_HASH}",
    }
    return uow, storage, inputs


def test_v2_workflow_has_frozen_dag_and_pinned_skills() -> None:
    workflow = load_research_workflow()
    assert [step.id for step in workflow.steps] == [
        "validate_query",
        "search_papers",
        "normalize_and_deduplicate",
        "rank_and_select",
        "approve_sources",
        "retrieve_source_content",
        "summarize_sources",
        "synthesize_findings",
        "generate_report",
        "persist_artifacts",
    ]
    assert all(
        step.uses is None or step.uses.endswith("@1.0.0")
        for step in workflow.steps
    )


def test_query_validation_rejects_reversed_year_range(tmp_path) -> None:
    async def scenario() -> None:
        with pytest.raises(SkillExecutionFailure) as captured:
            await validate_research_query(
                {
                    "topic": "synthetic topic",
                    "year_from": 2026,
                    "year_to": 2020,
                    "max_papers": 3,
                },
                _context(
                    "validate_query",
                    uow=InMemoryUnitOfWork(),
                    storage=LocalFilesystemArtifactStorage(tmp_path),
                ),
            )
        assert captured.value.code == "INVALID_RESEARCH_QUERY"

    asyncio.run(scenario())


def test_complete_skill_chain_is_abstract_only_zero_cost_and_publishable(
    tmp_path,
) -> None:
    async def scenario() -> None:
        uow, storage, inputs = await _execute_valid_chain(tmp_path)
        published = await persist_research_artifacts(
            inputs,
            _context("persist_artifacts", uow=uow, storage=storage),
        )
        assert published.output_data["publication"]["publishable"] is True
        assert published.output_data["publication"]["paper_count"] == 3
        assert published.output_data["publication"]["abstract_only"] is True
        assert {item.logical_name for item in published.emitted_artifacts} == {
            "report.md",
            "provenance.json",
            "usage.json",
        }
        operations = uow.provider_operations.list_for_run(
            "research-project", "research-run"
        )
        assert len(operations) == 9
        assert all(item.status.value == "SUCCEEDED" for item in operations)
        assert all(
            item.actual_usage is not None
            and item.actual_usage.estimated_cost_minor_units == 0
            for item in operations
        )

    asyncio.run(scenario())


def test_publication_fails_closed_when_selected_paper_count_is_mutated(
    tmp_path,
) -> None:
    async def scenario() -> None:
        uow, storage, inputs = await _execute_valid_chain(tmp_path)
        ranked = list(inputs["ranked_papers"])
        ranked[-1] = {
            **ranked[-1],
            "inclusion_status": "excluded",
            "exclusion_reason": "Mutation after approval.",
            "rank": None,
        }
        mutated = {**inputs, "ranked_papers": ranked}
        with pytest.raises(SkillExecutionFailure) as captured:
            await persist_research_artifacts(
                mutated,
                _context("persist_artifacts", uow=uow, storage=storage),
            )
        assert captured.value.code == "PROVENANCE_VALIDATION_FAILED"
        assert any(
            item["code"] == "INSUFFICIENT_SELECTED_PAPERS"
            for item in captured.value.details["issues"]
        )

    asyncio.run(scenario())
