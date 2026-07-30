"""Committed fictional fixtures for the network-free V3 acceptance.

Names, identifiers, abstracts, venues, and findings are intentionally invented.
They are not adapted from real publications.
"""

from __future__ import annotations

from datetime import UTC, datetime
from collections.abc import Mapping
from typing import Any

from backend.research.contracts import PaperAuthor, PaperRecord, canonical_hash

FIXED_TIME = datetime(2026, 7, 30, 9, 0, tzinfo=UTC)
SYNTHETIC_TOPIC = "fictional evidence handoffs in imaginary archive workspaces"

_PAPER_DATA = (
    {
        "provider_id": "fictional-lantern-001",
        "title": "Lantern Weave Protocols for Imaginary Archive Navigation",
        "abstract": (
            "In a fictional archive workspace, the Lantern Weave protocol links "
            "each synthetic summary to a bounded source marker. A three-stage "
            "simulation found that explicit marker checks reduced unsupported "
            "handoffs. The simulation used a scripted navigation exercise. "
            "The authors state that the tiny imaginary archive limits transfer."
        ),
        "year": 2024,
        "venue": "Journal of Fictional Archive Systems",
        "doi": "10.99999/reagent.synthetic-lantern",
    },
    {
        "provider_id": "fictional-mosaic-002",
        "title": "Mosaic Compass Trials in Synthetic Research Rooms",
        "abstract": (
            "Mosaic Compass is a fictional evidence handoff pattern for synthetic "
            "research rooms. The trial reports that explicit marker checks reduced "
            "unsupported handoffs and improved trace inspection. The abstract does "
            "not describe the trial methodology. No limitations are stated."
        ),
        "year": 2025,
        "venue": "Proceedings of Imaginary Research Tools",
        "doi": "10.99999/reagent.synthetic-mosaic",
    },
    {
        "provider_id": "fictional-ledger-003",
        "title": "Quiet Ledger Boundaries for Invented Evidence Handoffs",
        "abstract": (
            "The Quiet Ledger study examines an invented archive workflow. It "
            "reports that strict marker checks can delay ambiguous handoffs, while "
            "a qualified fallback preserved traceability in the synthetic scenario. "
            "The authors limit the claim to one invented archive configuration."
        ),
        "year": 2026,
        "venue": "Synthetic Evidence Notes",
        "doi": None,
    },
)


def papers() -> tuple[PaperRecord, ...]:
    result: list[PaperRecord] = []
    for index, item in enumerate(_PAPER_DATA, 1):
        provider_id = str(item["provider_id"])
        doi = item["doi"]
        result.append(
            PaperRecord(
                paper_id=PaperRecord.internal_id(
                    provider="synthetic-grounded-catalog",
                    provider_id=provider_id,
                    doi=doi,
                ),
                provider_id=provider_id,
                title=str(item["title"]),
                authors=(PaperAuthor(name=f"Fictional Researcher {index}"),),
                abstract=str(item["abstract"]),
                publication_year=int(item["year"]),
                publication_venue=str(item["venue"]),
                source_provider="synthetic-grounded-catalog@1.0.0",
                source_url=f"https://example.invalid/fictional/{provider_id}",
                doi=doi,
                retrieved_at=FIXED_TIME,
                raw_metadata_hash=canonical_hash(item),
                language="en",
                metadata_limitations=("synthetic_fixture_only",),
            )
        )
    return tuple(result)


def provider_responses() -> Mapping[str, Mapping[str, Any]]:
    paper_values = papers()
    return {
        "summary:fictional-lantern-001": {
            "objective": "Examine traceable evidence handoffs in an imaginary archive.",
            "methodology": {
                "status": "EXPLICIT",
                "items": ["A scripted three-stage navigation simulation."],
            },
            "key_findings": [
                "Explicit marker checks reduced unsupported handoffs."
            ],
            "contribution": "A fictional marker-bound handoff protocol.",
            "stated_limitations": {
                "status": "EXPLICIT",
                "items": ["The imaginary archive is too small for broad transfer."],
            },
            "relevance_to_topic": "Directly addresses fictional evidence handoffs.",
            "uncertainties": ["Only abstract-level detail is available."],
            "missing_information": [],
            "evidence": [
                {
                    "span": "explicit marker checks reduced unsupported handoffs",
                    "paraphrase": "Marker checks reduced unsupported synthetic handoffs.",
                    "evidence_type": "FINDING",
                },
                {
                    "span": "tiny imaginary archive limits transfer",
                    "paraphrase": "The authors explicitly limit transferability.",
                    "evidence_type": "SOURCE_STATED_LIMITATION",
                },
            ],
        },
        "summary:fictional-mosaic-002": {
            "objective": "Study a fictional handoff pattern in synthetic research rooms.",
            "methodology": {"status": "UNAVAILABLE", "items": []},
            "key_findings": [
                "Explicit marker checks reduced unsupported handoffs."
            ],
            "contribution": "A fictional pattern for trace inspection.",
            "stated_limitations": {"status": "UNAVAILABLE", "items": []},
            "relevance_to_topic": "Directly addresses synthetic evidence handoffs.",
            "uncertainties": ["Method and limitations are absent from the abstract."],
            "missing_information": ["methodology", "stated_limitations"],
            "evidence": [
                {
                    "span": "explicit marker checks reduced unsupported handoffs",
                    "paraphrase": "Marker checks reduced unsupported synthetic handoffs.",
                    "evidence_type": "FINDING",
                }
            ],
        },
        "summary:fictional-ledger-003": {
            "objective": "Examine strict and qualified handoff boundaries.",
            "methodology": {"status": "UNAVAILABLE", "items": []},
            "key_findings": [
                "Strict checks delayed ambiguous handoffs, while a fallback preserved traceability."
            ],
            "contribution": "A qualified fictional counterpoint to strict marker checks.",
            "stated_limitations": {
                "status": "EXPLICIT",
                "items": ["The claim covers one invented archive configuration."],
            },
            "relevance_to_topic": "Addresses a tradeoff in fictional evidence handoffs.",
            "uncertainties": ["The abstract gives no quantitative measurements."],
            "missing_information": ["methodology"],
            "evidence": [
                {
                    "span": "strict marker checks can delay ambiguous handoffs",
                    "paraphrase": "Strict checks may delay ambiguous handoffs.",
                    "evidence_type": "FINDING",
                },
                {
                    "span": "qualified fallback preserved traceability",
                    "paraphrase": "A qualified fallback retained traceability.",
                    "evidence_type": "FINDING",
                },
            ],
        },
        "claims": {
            "claims": [
                {
                    "claim_key": "theme",
                    "claim_text": "The fictional studies center traceable evidence handoffs.",
                    "claim_category": "CROSS_SOURCE_THEME",
                    "paper_ordinals": [1, 2, 3],
                    "evidence_ordinals": [[1, 1], [2, 1], [3, 1]],
                    "confidence": "HIGH",
                    "inference_flag": False,
                    "limitations": ["Evidence is synthetic and abstract-only."],
                },
                {
                    "claim_key": "agreement",
                    "claim_text": "Two fictional studies report benefits from explicit marker checks.",
                    "claim_category": "AGREEMENT",
                    "paper_ordinals": [3, 2],
                    "evidence_ordinals": [[3, 1], [2, 1]],
                    "confidence": "HIGH",
                    "inference_flag": False,
                    "limitations": ["No scientific generalization is intended."],
                },
                {
                    "claim_key": "disagreement",
                    "claim_text": "Strict marker checking is portrayed as beneficial in two abstracts but potentially delaying in another.",
                    "claim_category": "DISAGREEMENT",
                    "paper_ordinals": [3, 2, 1],
                    "evidence_ordinals": [[3, 1], [2, 1], [1, 1], [1, 2]],
                    "confidence": "MEDIUM",
                    "inference_flag": False,
                    "limitations": ["The positions are qualified, not a direct replication dispute."],
                },
                {
                    "claim_key": "limitation",
                    "claim_text": "The Lantern fixture explicitly limits transfer beyond its tiny imaginary archive.",
                    "claim_category": "LIMITATION",
                    "paper_ordinals": [3],
                    "evidence_ordinals": [[3, 2]],
                    "confidence": "HIGH",
                    "inference_flag": False,
                    "limitations": ["Source-stated limitation."],
                },
                {
                    "claim_key": "gap",
                    "claim_text": "A possible next step is to compare strict and qualified checks across more fictional archive configurations.",
                    "claim_category": "RESEARCH_GAP",
                    "paper_ordinals": [3, 1],
                    "evidence_ordinals": [[3, 2], [1, 1], [1, 2]],
                    "confidence": "LOW",
                    "inference_flag": True,
                    "limitations": ["Tentative model-assisted inference."],
                },
            ]
        },
        "report": {
            "title": "Fictional Evidence Handoffs in Imaginary Archive Workspaces",
            "executive_summary": (
                "The three fictional abstracts emphasize traceable handoffs, with "
                "a qualified tradeoff around strict marker checking."
            ),
            "conclusions": (
                "The synthetic corpus demonstrates a citation-bound reporting path; "
                "it does not establish a real scientific conclusion."
            ),
            "generation_note": (
                "Generated by a deterministic synthetic provider and validated "
                "against approved abstract-only fixtures."
            ),
        },
    }
