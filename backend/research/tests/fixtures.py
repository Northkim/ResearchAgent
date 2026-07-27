"""Synthetic, copyright-safe research contract fixtures."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.research.contracts import (
    AccessLimitation,
    CitationReference,
    ClaimConfidence,
    ClaimKind,
    ContentType,
    EvidenceScope,
    EvidenceUnit,
    GroundedClaim,
    InclusionStatus,
    PaperAuthor,
    PaperRecord,
    ProviderCategory,
    ProviderOperation,
    ProviderOperationKind,
    ProviderReservation,
    ProviderUsage,
    ProviderVersion,
    ProvenanceManifest,
    RankedPaper,
    ResearchReport,
    SourceContent,
    canonical_hash,
    sha256_bytes,
)

FIXED_TIME = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)


def papers() -> tuple[PaperRecord, ...]:
    result = []
    for index in range(1, 4):
        doi = f"10.5555/synthetic.{index}"
        result.append(
            PaperRecord(
                paper_id=PaperRecord.internal_id(
                    provider="synthetic-search",
                    provider_id=f"paper-{index}",
                    doi=doi,
                ),
                provider_id=f"paper-{index}",
                title=f"Synthetic paper {index}",
                authors=(PaperAuthor(name=f"Synthetic Author {index}"),),
                abstract=f"Synthetic abstract evidence {index}.",
                publication_year=2020 + index,
                publication_venue="Synthetic Venue",
                source_provider="synthetic-search@1.0.0",
                source_url=f"https://example.invalid/paper-{index}",
                doi=doi,
                retrieved_at=FIXED_TIME,
                raw_metadata_hash=canonical_hash({"paper": index}),
            )
        )
    return tuple(result)


def valid_manifest() -> ProvenanceManifest:
    paper_records = papers()
    sources = tuple(
        SourceContent(
            paper_id=paper.paper_id,
            content_type=ContentType.ABSTRACT,
            abstract=paper.abstract,
            full_text=None,
            content_source="synthetic-source@1.0.0",
            source_url=paper.source_url,
            retrieved_at=FIXED_TIME,
            content_hash=sha256_bytes((paper.abstract or "").encode()),
            access_limitation=AccessLimitation.ABSTRACT_ONLY,
            license_or_usage_metadata={"synthetic": True},
        )
        for paper in paper_records
    )
    ranked = tuple(
        RankedPaper(
            paper_id=paper.paper_id,
            relevance_score=1 - index / 10,
            ranking_explanation="Deterministic synthetic query match.",
            inclusion_status=InclusionStatus.SELECTED,
            exclusion_reason=None,
            rank=index,
            ranker_version="synthetic-ranker@1.0.0",
        )
        for index, paper in enumerate(paper_records, start=1)
    )
    citations = tuple(
        CitationReference(
            citation_id=f"citation-{index}",
            paper_id=paper.paper_id,
            title=paper.title,
            authors=tuple(author.name for author in paper.authors),
            year=paper.publication_year,
            source_url=paper.source_url,
            doi=paper.doi,
            report_citation_label=f"[P{index}]",
        )
        for index, paper in enumerate(paper_records, start=1)
    )
    evidence = tuple(
        EvidenceUnit(
            evidence_id=f"evidence-{index}",
            paper_id=paper.paper_id,
            source_content_hash=sources[index - 1].content_hash,
            source_location="abstract",
            source_excerpt=None,
            source_summary=f"Synthetic bounded source summary {index}.",
            evidence_hash=canonical_hash({"evidence": index}),
            supported_claim_ids=("claim-1",),
            content_scope=EvidenceScope.ABSTRACT,
        )
        for index, paper in enumerate(paper_records, start=1)
    )
    claims = (
        GroundedClaim(
            claim_id="claim-1",
            claim_text="The synthetic sources share a test-only theme.",
            supporting_evidence_ids=tuple(item.evidence_id for item in evidence),
            confidence=ClaimConfidence.MEDIUM,
            limitations=("Synthetic fixtures are not research findings.",),
            claim_kind=ClaimKind.CROSS_SOURCE_SYNTHESIS,
            generation_model="synthetic-llm/deterministic-v1",
            prompt_version="synthesis-prompt/v1",
        ),
    )
    report_id = "report-artifact-1"
    provenance_id = "provenance-artifact-1"
    report = ResearchReport(
        report_id="report-1",
        project_id="project-1",
        workflow_run_id="run-1",
        title="Synthetic literature review",
        executive_summary="A test-only summary [P1] [P2] [P3].",
        methodology={"source_scope": "abstract-first"},
        selected_papers=citations,
        paper_summaries=tuple({"paper_id": paper.paper_id} for paper in paper_records),
        thematic_synthesis={"claim_ids": ["claim-1"]},
        disagreements=(),
        limitations=("Abstract-only synthetic evidence.",),
        research_gaps=(),
        references=citations,
        provenance_artifact_id=provenance_id,
        generated_at=FIXED_TIME,
        markdown="# Synthetic review\n\nClaim [P1] [P2] [P3].",
        source_scope_by_paper={paper.paper_id: "abstract" for paper in paper_records},
    )
    operation = ProviderOperation(
        id="operation-1",
        project_id="project-1",
        workflow_run_id="run-1",
        logical_step_id="search_papers",
        step_run_id="step-run-1",
        provider_category=ProviderCategory.PAPER_SEARCH,
        operation_kind=ProviderOperationKind.SEARCH,
        provider_identity="synthetic-search",
        adapter_version="1.0.0",
        model_or_endpoint="fixture/v1",
        idempotency_key="operation-search-1",
        request_fingerprint=canonical_hash({"query": "synthetic"}),
        reservation=ProviderReservation(),
        created_at=FIXED_TIME,
        updated_at=FIXED_TIME,
    ).mark_running(at=FIXED_TIME).settle_success(
        ProviderUsage.zero_cost(
            provider="synthetic-search",
            model_or_endpoint="fixture/v1",
            operation_kind=ProviderOperationKind.SEARCH,
        ),
        at=FIXED_TIME,
    )
    return ProvenanceManifest(
        project_id="project-1",
        workflow_run_id="run-1",
        workflow_id="guided-literature-review",
        workflow_version="2.0.0",
        workflow_hash=canonical_hash({"workflow": "2.0.0"}),
        skill_versions={"search_papers": "research.search_papers@1.0.0"},
        prompt_versions={"synthesis": "synthesis-prompt/v1"},
        provider_versions=(
            ProviderVersion(
                provider="synthetic-search",
                adapter_version="1.0.0",
                model_or_endpoint="fixture/v1",
            ),
        ),
        papers=paper_records,
        source_contents=sources,
        ranked_papers=ranked,
        citations=citations,
        evidence_units=evidence,
        grounded_claims=claims,
        report=report,
        report_artifact_id=report_id,
        provenance_artifact_id=provenance_id,
        artifact_checksums={
            report_id: canonical_hash({"report": 1}),
            provenance_id: canonical_hash({"provenance": 1}),
        },
        provider_operations=(operation,),
    )
