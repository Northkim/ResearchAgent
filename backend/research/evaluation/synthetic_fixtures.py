"""Strict loader for committed, wholly synthetic silver-evaluation fixtures."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping
from typing import Any

from backend.research.contracts import canonical_hash

from .contracts import EvaluationCandidate
from .fake_judge import (
    FakePairwiseBehavior,
    pointwise_behaviors_from_fixture,
)

SYNTHETIC_FIXTURE_SCHEMA = "reagent-synthetic-silver-fixtures/v1"
SYNTHETIC_PROVIDER = "synthetic-silver-fixture"


@dataclass(frozen=True, slots=True)
class SyntheticFixtureSet:
    version: str
    candidates: tuple[EvaluationCandidate, ...]
    candidate_languages: Mapping[str, str]
    metadata_warnings: Mapping[str, tuple[str, ...]]
    pointwise_behaviors: Mapping[Any, Any]
    pairwise_behaviors: Mapping[frozenset[str], FakePairwiseBehavior]
    pairwise_pairs: tuple[tuple[str, str], ...]
    checksum: str


def load_synthetic_fixture_set(path: str | Path) -> SyntheticFixtureSet:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("schema_version") != SYNTHETIC_FIXTURE_SCHEMA:
        raise ValueError("Unsupported synthetic fixture schema")
    if value.get("fixture_kind") != "wholly-synthetic-no-real-paper-content":
        raise ValueError("Fixture set is not marked wholly synthetic")
    candidate_values = tuple(value["candidates"])
    ids = tuple(str(item["candidate_id"]) for item in candidate_values)
    if len(ids) != len(set(ids)):
        raise ValueError("Synthetic candidate IDs must be unique")
    candidates: list[EvaluationCandidate] = []
    languages: dict[str, str] = {}
    warnings: dict[str, tuple[str, ...]] = {}
    for rank, item in enumerate(candidate_values, start=1):
        if item.get("source_marker") != SYNTHETIC_PROVIDER:
            raise ValueError("Every candidate must carry the synthetic source marker")
        title = str(item["title"])
        preview = item.get("abstract_preview")
        metadata_hash = canonical_hash(
            {
                "synthetic": True,
                "candidate_id": item["candidate_id"],
                "title": title,
                "abstract_preview": preview,
            }
        )
        candidates.append(
            EvaluationCandidate(
                topic_id=str(item.get("topic_id", "synthetic-topic")),
                topic_title=str(item.get("topic_title", "Synthetic Topic")),
                topic=str(item.get("topic", "synthetic relevance evaluation")),
                research_question=item.get("research_question"),
                candidate_id=str(item["candidate_id"]),
                rank=int(item.get("rank", rank)),
                paper_id=f"synthetic-paper-{item['candidate_id']}",
                openalex_id=f"synthetic://{item['candidate_id']}",
                title=title,
                authors=("Synthetic Author",),
                year=2026,
                venue="Synthetic Fixture Venue",
                doi=None,
                abstract_available=preview is not None,
                normalized_metadata_hash=metadata_hash,
                search_execution_id="synthetic-fixture-execution",
                provider=SYNTHETIC_PROVIDER,
                adapter_version="synthetic-fixture-loader/v1",
                abstract_preview=preview,
            )
        )
        languages[str(item["candidate_id"])] = str(item.get("language", "en"))
        warnings[str(item["candidate_id"])] = tuple(item.get("metadata_warnings", ()))
    pairwise: dict[frozenset[str], FakePairwiseBehavior] = {}
    pairs: list[tuple[str, str]] = []
    for item in value.get("pairwise", ()):
        left, right = str(item["left_candidate_id"]), str(item["right_candidate_id"])
        if left not in ids or right not in ids:
            raise ValueError("Pairwise fixture references unknown candidate")
        key = frozenset((left, right))
        if key in pairwise:
            raise ValueError("Duplicate pairwise fixture")
        pairwise[key] = FakePairwiseBehavior(
            preferred_candidate_id=str(item["preferred_candidate_id"]),
            mirrored_preferred_candidate_id=item.get("mirrored_preferred_candidate_id"),
            reason=str(item.get("reason", "Synthetic fixture preference.")),
        )
        pairs.append((left, right))
    fixture_checksum = canonical_hash(value)
    return SyntheticFixtureSet(
        version=str(value["version"]),
        candidates=tuple(candidates),
        candidate_languages=languages,
        metadata_warnings=warnings,
        pointwise_behaviors=pointwise_behaviors_from_fixture(candidate_values),
        pairwise_behaviors=pairwise,
        pairwise_pairs=tuple(pairs),
        checksum=fixture_checksum,
    )
