"""Human review-sheet export, validated import, and adjudication checks."""

from __future__ import annotations

import csv
import io
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from backend.research.contracts import canonical_hash
from backend.research.contracts._serialization import canonical_json

from .contracts import (
    AdjudicatedJudgment,
    CandidateJudgment,
    EvaluationCandidate,
    RelevanceLabel,
)

_REVIEW_COLUMNS = (
    "topic_id",
    "topic_title",
    "topic",
    "research_question",
    "candidate_id",
    "candidate_identity_hash",
    "rank",
    "title",
    "year",
    "authors",
    "venue",
    "doi",
    "openalex_id",
    "abstract_available",
    "abstract_preview",
    "reviewer_id",
    "relevance_label",
    "confidence",
    "exclusion_reason",
    "duplicate_cluster",
    "identity_ambiguity",
    "metadata_error_flags",
    "reviewer_note",
    "judged_at",
)


@dataclass(frozen=True, slots=True)
class JudgmentImportResult:
    judgments: tuple[CandidateJudgment, ...]
    file_checksum: str
    reviewer_id: str
    complete: bool
    missing_candidate_ids: tuple[str, ...]


def export_review_json(
    candidates: Iterable[EvaluationCandidate],
    *,
    reviewer_id: str = "",
) -> bytes:
    reviewer_id = _reviewer_id(reviewer_id)
    rows = [
        _review_row(candidate, reviewer_id=reviewer_id)
        for candidate in _ordered_candidates(candidates)
    ]
    return canonical_json(
        {
            "schema_version": "openalex-review-sheet/v1",
            "assigned_reviewer_id": reviewer_id or None,
            "instructions": (
                "Human reviewer must complete judgment fields; no label is inferred "
                "from rank or metadata."
            ),
            "rows": rows,
        }
    ).encode("utf-8")


def export_review_csv(
    candidates: Iterable[EvaluationCandidate],
    *,
    reviewer_id: str = "",
) -> bytes:
    reviewer_id = _reviewer_id(reviewer_id)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=_REVIEW_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for candidate in _ordered_candidates(candidates):
        row = _review_row(candidate, reviewer_id=reviewer_id)
        row["authors"] = json.dumps(row["authors"], ensure_ascii=False)
        row["metadata_error_flags"] = "[]"
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def import_review_json(
    content: bytes,
    candidates: Iterable[EvaluationCandidate],
    *,
    require_complete: bool = False,
) -> JudgmentImportResult:
    value = json.loads(content)
    if not isinstance(value, Mapping) or not isinstance(value.get("rows"), list):
        raise ValueError("Review JSON must contain a rows array")
    return _import_rows(
        value["rows"],
        candidates,
        source_content=content,
        require_complete=require_complete,
    )


def import_review_csv(
    content: bytes,
    candidates: Iterable[EvaluationCandidate],
    *,
    require_complete: bool = False,
) -> JudgmentImportResult:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or not set(_REVIEW_COLUMNS).issubset(reader.fieldnames):
        raise ValueError("Review CSV is missing required columns")
    rows: list[dict[str, Any]] = []
    for raw in reader:
        row = dict(raw)
        row["authors"] = _json_array(row.get("authors", ""), "authors")
        row["metadata_error_flags"] = _json_array(
            row.get("metadata_error_flags", ""),
            "metadata_error_flags",
        )
        rows.append(row)
    return _import_rows(
        rows,
        candidates,
        source_content=content,
        require_complete=require_complete,
    )


def adjudicate(
    *,
    candidate: EvaluationCandidate,
    source_judgments: tuple[CandidateJudgment, ...],
    final_relevance_label: RelevanceLabel,
    adjudicator_id: str,
    disagreement_reason: str | None,
    final_notes: str | None,
    adjudicated_at: datetime,
) -> AdjudicatedJudgment:
    if len(source_judgments) < 2:
        raise ValueError("Adjudication requires at least two reviewer judgments")
    if len({item.reviewer_id for item in source_judgments}) < 2:
        raise ValueError("Adjudication requires distinct reviewer IDs")
    if adjudicator_id in {item.reviewer_id for item in source_judgments}:
        raise ValueError("Adjudicator must be independent from source reviewers")
    if any(item.candidate_id != candidate.candidate_id for item in source_judgments):
        raise ValueError("Source judgment references another candidate")
    if any(
        item.candidate_identity_hash != candidate.identity_hash
        for item in source_judgments
    ):
        raise ValueError("Source judgment candidate identity has changed")
    labels = {item.relevance_label for item in source_judgments}
    if len(labels) > 1 and not disagreement_reason:
        raise ValueError("Disagreement adjudication requires a reason")
    return AdjudicatedJudgment(
        topic_id=candidate.topic_id,
        candidate_id=candidate.candidate_id,
        final_relevance_label=final_relevance_label,
        adjudicator_id=adjudicator_id,
        source_judgment_hashes=tuple(
            sorted(item.canonical_hash() for item in source_judgments)
        ),
        disagreement_reason=disagreement_reason,
        final_notes=final_notes,
        adjudicated_at=adjudicated_at,
    )


def _import_rows(
    rows: Iterable[Mapping[str, Any]],
    candidates: Iterable[EvaluationCandidate],
    *,
    source_content: bytes,
    require_complete: bool,
) -> JudgmentImportResult:
    ordered = _ordered_candidates(candidates)
    by_id = {candidate.candidate_id: candidate for candidate in ordered}
    judgments: list[CandidateJudgment] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        candidate_id = str(row.get("candidate_id", "")).strip()
        if candidate_id not in by_id:
            raise ValueError(f"Unknown candidate: {candidate_id}")
        candidate = by_id[candidate_id]
        _validate_candidate_row(row, candidate)
        identity_hash = str(row.get("candidate_identity_hash", "")).strip()
        if identity_hash != candidate.identity_hash:
            raise ValueError(f"Candidate identity changed: {candidate_id}")
        reviewer_id = str(row.get("reviewer_id", "")).strip()
        if not reviewer_id:
            raise ValueError("Reviewer ID is required")
        key = (candidate_id, reviewer_id)
        if key in seen:
            raise ValueError("Duplicate reviewer judgment")
        seen.add(key)
        label_value = str(row.get("relevance_label", "")).strip()
        if not label_value:
            raise ValueError(f"Missing relevance label for {candidate_id}")
        try:
            label = RelevanceLabel(label_value)
        except ValueError as error:
            raise ValueError(f"Invalid relevance label: {label_value}") from error
        judged_at = datetime.fromisoformat(str(row.get("judged_at", "")).strip())
        metadata_flags = row.get("metadata_error_flags", ())
        if isinstance(metadata_flags, str):
            metadata_flags = _json_array(metadata_flags, "metadata_error_flags")
        judgment = CandidateJudgment(
            topic_id=candidate.topic_id,
            candidate_id=candidate_id,
            candidate_identity_hash=identity_hash,
            reviewer_id=reviewer_id,
            relevance_label=label,
            confidence=int(row.get("confidence", 0)),
            exclusion_reason=_optional_text(row.get("exclusion_reason")),
            duplicate_cluster=_optional_text(row.get("duplicate_cluster")),
            identity_ambiguity=_boolean(row.get("identity_ambiguity", False)),
            metadata_error_flags=tuple(str(item) for item in metadata_flags),
            reviewer_note=_optional_text(row.get("reviewer_note")),
            judged_at=judged_at,
        )
        judgments.append(judgment)

    reviewer_counts = Counter(item.reviewer_id for item in judgments)
    if len(reviewer_counts) != 1:
        raise ValueError("One imported sheet must contain exactly one reviewer ID")
    reviewer_id = next(iter(reviewer_counts), "")
    judged_ids = {item.candidate_id for item in judgments}
    missing = tuple(sorted(set(by_id) - judged_ids))
    if require_complete and missing:
        raise ValueError(f"Review sheet is incomplete: {len(missing)} judgments missing")
    return JudgmentImportResult(
        judgments=tuple(
            sorted(judgments, key=lambda item: (item.topic_id, item.candidate_id))
        ),
        file_checksum=canonical_hash(
            {
                "source_sha256": canonical_hash(source_content.decode("utf-8-sig")),
                "judgments": [item.to_dict() for item in judgments],
            }
        ),
        reviewer_id=reviewer_id,
        complete=not missing,
        missing_candidate_ids=missing,
    )


def _review_row(
    candidate: EvaluationCandidate,
    *,
    reviewer_id: str = "",
) -> dict[str, Any]:
    return {
        "topic_id": candidate.topic_id,
        "topic_title": candidate.topic_title,
        "topic": candidate.topic,
        "research_question": candidate.research_question,
        "candidate_id": candidate.candidate_id,
        "candidate_identity_hash": candidate.identity_hash,
        "rank": candidate.rank,
        "title": candidate.title,
        "year": candidate.year,
        "authors": list(candidate.authors),
        "venue": candidate.venue,
        "doi": candidate.doi,
        "openalex_id": candidate.openalex_id,
        "abstract_available": candidate.abstract_available,
        "abstract_preview": candidate.abstract_preview,
        "reviewer_id": reviewer_id,
        "relevance_label": "",
        "confidence": "",
        "exclusion_reason": "",
        "duplicate_cluster": "",
        "identity_ambiguity": "",
        "metadata_error_flags": [],
        "reviewer_note": "",
        "judged_at": "",
    }


def _reviewer_id(value: str) -> str:
    normalized = value.strip()
    if normalized and (
        len(normalized) > 80
        or not all(character.isalnum() or character in "-_." for character in normalized)
    ):
        raise ValueError("Reviewer ID must be a safe pseudonymous identifier")
    return normalized


def _validate_candidate_row(
    row: Mapping[str, Any],
    candidate: EvaluationCandidate,
) -> None:
    authors = row.get("authors", ())
    if isinstance(authors, str):
        authors = _json_array(authors, "authors")
    year_value = row.get("year")
    year = None if year_value in {None, ""} else int(year_value)
    expected = {
        "topic_id": candidate.topic_id,
        "topic_title": candidate.topic_title,
        "topic": candidate.topic,
        "research_question": candidate.research_question,
        "rank": candidate.rank,
        "title": candidate.title,
        "year": candidate.year,
        "authors": tuple(candidate.authors),
        "venue": candidate.venue,
        "doi": candidate.doi,
        "openalex_id": candidate.openalex_id,
        "abstract_available": candidate.abstract_available,
        "abstract_preview": candidate.abstract_preview,
    }
    actual = {
        "topic_id": str(row.get("topic_id", "")).strip(),
        "topic_title": str(row.get("topic_title", "")).strip(),
        "topic": str(row.get("topic", "")).strip(),
        "research_question": _optional_text(row.get("research_question")),
        "rank": int(row.get("rank", 0)),
        "title": str(row.get("title", "")).strip(),
        "year": year,
        "authors": tuple(str(item) for item in authors),
        "venue": _optional_text(row.get("venue")),
        "doi": _optional_text(row.get("doi")),
        "openalex_id": str(row.get("openalex_id", "")).strip(),
        "abstract_available": _boolean(row.get("abstract_available", False)),
        "abstract_preview": _optional_text(row.get("abstract_preview")),
    }
    if actual != expected:
        raise ValueError(f"Candidate review metadata changed: {candidate.candidate_id}")


def _ordered_candidates(
    candidates: Iterable[EvaluationCandidate],
) -> tuple[EvaluationCandidate, ...]:
    result = tuple(sorted(candidates, key=lambda item: (item.topic_id, item.rank)))
    ids = [item.candidate_id for item in result]
    if len(ids) != len(set(ids)):
        raise ValueError("Candidate IDs must be unique")
    return result


def _json_array(value: str, field_name: str) -> list[Any]:
    if not value.strip():
        return []
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError(f"{field_name} must be a JSON array")
    return parsed


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no", ""}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")
