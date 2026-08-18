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
MANUSCRIPT_PRESENTATION_SCHEMA = (
    "reagent.artifact-presentation.manuscript-draft/v0.1"
)
REVIEW_PRESENTATION_SCHEMA = (
    "reagent.artifact-presentation.review-report/v0.1"
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


def _reference(value: Any, label: str, accepted: set[str]) -> dict[str, str]:
    item = _object(value, {"artifact_id", "artifact_type", "artifact_checksum"}, label)
    if (
        not isinstance(item["artifact_id"], str)
        or not _ARTIFACT.fullmatch(item["artifact_id"])
        or item["artifact_type"] not in accepted
        or not isinstance(item["artifact_checksum"], str)
        or not _SHA.fullmatch(item["artifact_checksum"])
    ):
        raise UpstreamPresentationError(f"{label} identity is invalid")
    return item


def _count(value: Any, label: str, maximum: int = 100_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise UpstreamPresentationError(f"{label} is invalid")
    return value


def validate_manuscript_presentation(value: Mapping[str, Any]) -> dict[str, Any]:
    item = _object(value, {
        "schema", "artifact_id", "artifact_checksum", "mode", "title", "summary",
        "sections", "evidence_coverage", "result_availability", "limitations",
        "owner_review_status", "source_artifacts", "parent_manuscript", "causal_review",
        "changed_sections", "change_summary", "issue_dispositions",
        "unresolved_issue_count", "presentation_checksum",
    }, "manuscript presentation")
    _base(item, MANUSCRIPT_PRESENTATION_SCHEMA)
    if item["mode"] not in {"INITIAL", "REVISION"}:
        raise UpstreamPresentationError("manuscript mode is invalid")
    item["title"] = _text(item["title"], "manuscript title", 500)
    item["summary"] = _text(item["summary"], "manuscript summary", 2_000)
    item["sections"] = _texts(item["sections"], "manuscript section", count=30, length=200)
    coverage = _object(item["evidence_coverage"], {
        "claim_count", "supported_claim_count", "planned_claim_count",
        "unavailable_claim_count",
    }, "evidence coverage")
    for key in coverage:
        coverage[key] = _count(coverage[key], key)
    if sum(coverage[key] for key in (
        "supported_claim_count", "planned_claim_count", "unavailable_claim_count"
    )) > coverage["claim_count"]:
        raise UpstreamPresentationError("evidence coverage exceeds claim count")
    item["evidence_coverage"] = coverage
    if item["result_availability"] not in {"AVAILABLE", "UNAVAILABLE"}:
        raise UpstreamPresentationError("result availability is invalid")
    item["limitations"] = _texts(item["limitations"], "manuscript limitation", count=20, length=500)
    if item["owner_review_status"] not in {"APPROVED", "NOT_REPORTED"}:
        raise UpstreamPresentationError("Owner review status is invalid")
    sources = item["source_artifacts"]
    if not isinstance(sources, list) or len(sources) > 10:
        raise UpstreamPresentationError("source Artifact list is invalid")
    normalized_sources: list[dict[str, Any]] = []
    for raw in sources:
        source = _object(raw, {"role", "artifact_id", "artifact_type", "artifact_checksum"}, "source Artifact")
        source["role"] = _text(source["role"], "source role", 80)
        normalized_sources.append({
            "role": source["role"],
            **_reference({key: source[key] for key in ("artifact_id", "artifact_type", "artifact_checksum")}, "source Artifact", {
                "selected-research-idea/v1", "selected-paper-library/v1", "experiment-record/v5",
            }),
        })
    item["source_artifacts"] = normalized_sources
    parent = item["parent_manuscript"]
    review = item["causal_review"]
    if item["mode"] == "INITIAL":
        if parent is not None or review is not None or item["changed_sections"] or item["change_summary"] is not None or item["issue_dispositions"] or item["unresolved_issue_count"]:
            raise UpstreamPresentationError("initial manuscript contains Revision-only presentation data")
    else:
        item["parent_manuscript"] = _reference(parent, "parent manuscript", {"manuscript-draft/v4"})
        item["causal_review"] = _reference(review, "causal Review", {"review-report/v3"})
    item["changed_sections"] = _texts(item["changed_sections"], "changed section", count=30, length=200)
    item["change_summary"] = _text(item["change_summary"], "change summary", 1_500, optional=True)
    dispositions = item["issue_dispositions"]
    if not isinstance(dispositions, list) or len(dispositions) > 100:
        raise UpstreamPresentationError("issue disposition list is invalid")
    for raw in dispositions:
        disposition = _object(raw, {"issue_id", "disposition"}, "issue disposition")
        _text(disposition["issue_id"], "Review issue identity", 160)
        _text(disposition["disposition"], "Review issue disposition", 80)
    item["unresolved_issue_count"] = _count(item["unresolved_issue_count"], "unresolved issue count", 100)
    return _finish(item)


def validate_review_presentation(value: Mapping[str, Any]) -> dict[str, Any]:
    item = _object(value, {
        "schema", "artifact_id", "artifact_checksum", "reviewed_manuscript",
        "scope", "status", "summary", "issues", "requested_revisions",
        "unresolved_evidence_gaps", "reproducibility_findings", "limitations",
        "owner_review_status", "presentation_checksum",
    }, "Review presentation")
    _base(item, REVIEW_PRESENTATION_SCHEMA)
    item["reviewed_manuscript"] = _reference(
        item["reviewed_manuscript"], "reviewed manuscript", {"manuscript-draft/v4"}
    )
    item["scope"] = _text(item["scope"], "Review scope", 1_500)
    if item["status"] not in {"NO_BLOCKING_ISSUES", "REVISION_REQUIRED", "INSUFFICIENT_EVIDENCE"}:
        raise UpstreamPresentationError("Review status is invalid")
    item["summary"] = _text(item["summary"], "Review summary", 2_000)
    issues = item["issues"]
    if not isinstance(issues, list) or len(issues) > 100:
        raise UpstreamPresentationError("Review issue list is invalid")
    for raw in issues:
        issue = _object(raw, {
            "issue_id", "severity", "blocking", "anchor", "rationale", "requested_revision",
        }, "Review issue")
        _text(issue["issue_id"], "Review issue identity", 160)
        if issue["severity"] not in {"MAJOR", "MINOR"} or not isinstance(issue["blocking"], bool):
            raise UpstreamPresentationError("Review issue classification is invalid")
        for key, maximum in (("anchor", 300), ("rationale", 1_000), ("requested_revision", 1_000)):
            issue[key] = _text(issue[key], key.replace("_", " "), maximum, optional=True)
    for key, label in (
        ("requested_revisions", "requested revision"),
        ("unresolved_evidence_gaps", "unresolved evidence gap"),
        ("reproducibility_findings", "reproducibility finding"),
        ("limitations", "Review limitation"),
    ):
        item[key] = _texts(item[key], label, count=30, length=500)
    if item["owner_review_status"] not in {"APPROVED", "NOT_REPORTED"}:
        raise UpstreamPresentationError("Owner review status is invalid")
    return _finish(item)
