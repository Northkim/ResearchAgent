"""Bounded UI-only presentation companions for upstream research Artifacts."""

from __future__ import annotations

import re
from typing import Any, Mapping

from backend.workflow_packages.serialization import canonical_hash, canonical_json

PAPER_LIBRARY_PRESENTATION_SCHEMA = (
    "reagent.artifact-presentation.selected-paper-library/v0.1"
)
RESEARCH_IDEA_PRESENTATION_SCHEMA = (
    "reagent.artifact-presentation.selected-research-idea/v0.1"
)
MAX_PRESENTATION_BYTES = 65_536

_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_ARTIFACT = re.compile(r"^artifact-[0-9a-f]{32}$")
_UNSAFE = re.compile(
    r"(?is)(?:```|<(?:script|iframe|html|body)\b|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"\b(?:api[_ -]?key|access[_ -]?token|password|secret|bearer)\s*[:=]|"
    r"\b(?:traceback|stdout|stderr)\s*:|https?://|"
    r"(?:^|[\s\"'])(?:/(?:Users|home|Volumes|private|var|tmp)/[^\s\"']+))"
)


class UpstreamPresentationError(ValueError):
    """An upstream presentation is not a safe exact bounded projection."""


def _object(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise UpstreamPresentationError(f"{label} fields mismatch")
    return dict(value)


def _text(value: Any, label: str, maximum: int, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise UpstreamPresentationError(f"{label} must be bounded text")
    if _UNSAFE.search(value):
        raise UpstreamPresentationError(f"{label} contains unsafe or private content")
    return value.strip()


def _texts(value: Any, label: str, *, count: int, length: int) -> list[str]:
    if not isinstance(value, list) or len(value) > count:
        raise UpstreamPresentationError(f"{label} must be a bounded list")
    return [str(_text(item, label, length)) for item in value]


def _base(value: Mapping[str, Any], schema: str) -> dict[str, Any]:
    if value["schema"] != schema:
        raise UpstreamPresentationError("presentation schema mismatch")
    if not isinstance(value["artifact_id"], str) or not _ARTIFACT.fullmatch(value["artifact_id"]):
        raise UpstreamPresentationError("presentation Artifact identity is invalid")
    if not isinstance(value["artifact_checksum"], str) or not _SHA.fullmatch(value["artifact_checksum"]):
        raise UpstreamPresentationError("presentation Artifact checksum is invalid")
    return dict(value)


def _finish(value: dict[str, Any]) -> dict[str, Any]:
    checksum = value.get("presentation_checksum")
    if not isinstance(checksum, str) or not _SHA.fullmatch(checksum):
        raise UpstreamPresentationError("presentation checksum is invalid")
    payload = dict(value)
    payload.pop("presentation_checksum")
    if canonical_hash(payload) != checksum:
        raise UpstreamPresentationError("presentation checksum mismatch")
    if len(canonical_json(value).encode("utf-8")) > MAX_PRESENTATION_BYTES:
        raise UpstreamPresentationError("presentation exceeds its byte bound")
    return value


def validate_paper_library_presentation(value: Mapping[str, Any]) -> dict[str, Any]:
    item = _object(value, {
        "schema", "artifact_id", "artifact_checksum", "selected_count",
        "selection_status", "evidence_basis", "limitations", "papers",
        "papers_truncated",
        "presentation_checksum",
    }, "paper-library presentation")
    _base(item, PAPER_LIBRARY_PRESENTATION_SCHEMA)
    if isinstance(item["selected_count"], bool) or not isinstance(item["selected_count"], int) or not 0 <= item["selected_count"] <= 10_000:
        raise UpstreamPresentationError("selected paper count is invalid")
    if item["selection_status"] != "SELECTED":
        raise UpstreamPresentationError("paper selection status is invalid")
    evidence_basis = _texts(item["evidence_basis"], "evidence basis", count=4, length=80)
    limitations = _texts(item["limitations"], "paper-library limitation", count=8, length=500)
    papers = item["papers"]
    if (
        not isinstance(papers, list)
        or len(papers) > 15
        or len(papers) > item["selected_count"]
        or item["papers_truncated"] is not (len(papers) < item["selected_count"])
    ):
        raise UpstreamPresentationError("selected paper entries are invalid")
    normalized_papers: list[dict[str, Any]] = []
    for raw in papers:
        paper = _object(raw, {
            "title", "authors", "year", "identifier_kind", "identifier",
            "why_selected", "evidence_availability", "limitation",
        }, "selected paper")
        title = _text(paper["title"], "paper title", 500)
        authors = _texts(paper["authors"], "paper author", count=20, length=160)
        year = paper["year"]
        if year is not None and (isinstance(year, bool) or not isinstance(year, int) or not 1000 <= year <= 3000):
            raise UpstreamPresentationError("paper year is invalid")
        if paper["identifier_kind"] not in {"DOI", "PROVIDER_ID"}:
            raise UpstreamPresentationError("paper identifier kind is invalid")
        identifier = _text(paper["identifier"], "paper identifier", 300)
        why = _text(paper["why_selected"], "selection reason", 1_000)
        availability = _text(paper["evidence_availability"], "evidence availability", 100)
        limitation = _text(paper["limitation"], "paper limitation", 500)
        normalized_papers.append({
            **paper, "title": title, "authors": authors, "identifier": identifier,
            "why_selected": why, "evidence_availability": availability,
            "limitation": limitation,
        })
    item.update(evidence_basis=evidence_basis, limitations=limitations, papers=normalized_papers)
    return _finish(item)


def validate_research_idea_presentation(value: Mapping[str, Any]) -> dict[str, Any]:
    item = _object(value, {
        "schema", "artifact_id", "artifact_checksum", "title", "summary",
        "research_question", "observed_gap", "proposed_direction", "assumptions",
        "risks", "validation_needed", "literature_basis_count",
        "source_literature_artifact", "presentation_checksum",
    }, "research-idea presentation")
    _base(item, RESEARCH_IDEA_PRESENTATION_SCHEMA)
    for key, maximum in (
        ("title", 500), ("summary", 2_000), ("research_question", 2_000),
        ("observed_gap", 2_000), ("proposed_direction", 2_000),
    ):
        item[key] = _text(item[key], key.replace("_", " "), maximum)
    for key in ("assumptions", "risks", "validation_needed"):
        item[key] = _texts(item[key], key.replace("_", " "), count=20, length=500)
    count = item["literature_basis_count"]
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 100:
        raise UpstreamPresentationError("literature basis count is invalid")
    source = _object(item["source_literature_artifact"], {
        "artifact_id", "artifact_type", "artifact_checksum",
    }, "source Literature Artifact")
    if (
        not isinstance(source["artifact_id"], str)
        or not _ARTIFACT.fullmatch(source["artifact_id"])
        or source["artifact_type"] != "selected-paper-library/v1"
        or not isinstance(source["artifact_checksum"], str)
        or not _SHA.fullmatch(source["artifact_checksum"])
    ):
        raise UpstreamPresentationError("source Literature Artifact identity is invalid")
    item["source_literature_artifact"] = source
    return _finish(item)
