"""Bounded Cloud presentation contracts for unpublished forward Artifacts."""

from __future__ import annotations

import math
import re
from typing import Any, Mapping

from backend.workflow_packages.serialization import canonical_hash, canonical_json

EXPERIMENT_RECORD_PRESENTATION_SCHEMA = "reagent.artifact-presentation.experiment-record/v0.1"
_ARTIFACT_ID = re.compile(r"^artifact-[0-9a-f]{32}$")
_CHECKSUM = re.compile(r"^sha256:[0-9a-f]{64}$")
_ABSOLUTE_PATH = re.compile(r"(?:^|\s)(?:/Users/|/Volumes/|/home/|[A-Za-z]:\\)")
_FORBIDDEN_TEXT = re.compile(
    r"```|-----BEGIN .*PRIVATE KEY-----|\bTraceback \(most recent call last\)|"
    r"(?:^|\s)(?:def |class |import |from \S+ import )|(?:https?://)[^\s/@]+:[^\s/@]+@",
    re.IGNORECASE,
)
_EVIDENCE = {"SUFFICIENT_FOR_BOUNDED_CLAIMS", "LIMITED", "INSUFFICIENT", "UNAVAILABLE"}
_ORIGINS = {"REAGENT_PREPARED", "LOCAL_PROJECT", "EXTERNAL_EXACT_PACKAGE"}
_PROCESS = {"SUCCEEDED", "FAILED", "TIMED_OUT", "CANCELLED", "INTERRUPTED"}


class ArtifactPresentationContractError(ValueError):
    """A bounded Artifact presentation violates its disclosure contract."""


def _object(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ArtifactPresentationContractError(f"{label} fields mismatch")
    return dict(value)


def _text(value: Any, label: str, *, maximum: int = 1_000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ArtifactPresentationContractError(f"{label} must be bounded non-empty text")
    if "\n" in value or "\r" in value or _ABSOLUTE_PATH.search(value) or _FORBIDDEN_TEXT.search(value):
        raise ArtifactPresentationContractError(f"{label} contains source, logs, credentials, or local paths")
    return value


def _texts(value: Any, label: str, *, maximum: int = 40) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        raise ArtifactPresentationContractError(f"{label} must be a bounded array")
    return [_text(item, label) for item in value]


def _status(value: Any, allowed: set[str], label: str) -> str:
    if value not in allowed:
        raise ArtifactPresentationContractError(f"{label} is invalid")
    return str(value)


def validate_experiment_record_presentation(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a small typed summary bound to exact experiment-record/v3 bytes."""

    result = _object(value, {
        "schema", "artifact", "selected_idea_summary", "experiment_source_mode",
        "methodology_summary", "preparation_status", "design_approval_status",
        "run_approval_status", "provenance_status", "execution_outcome",
        "primary_metrics", "comparisons", "robustness_summary",
        "scientific_evidence_status", "limitations", "presentation_checksum",
    }, "Experiment presentation")
    if result["schema"] != EXPERIMENT_RECORD_PRESENTATION_SCHEMA:
        raise ArtifactPresentationContractError("Experiment presentation schema mismatch")
    artifact = _object(result["artifact"], {"artifact_id", "artifact_type", "sha256"}, "Artifact identity")
    if not _ARTIFACT_ID.fullmatch(str(artifact["artifact_id"])) or artifact["artifact_type"] != "experiment-record/v3" or not _CHECKSUM.fullmatch(str(artifact["sha256"])):
        raise ArtifactPresentationContractError("Experiment presentation Artifact identity is invalid")
    idea = _object(result["selected_idea_summary"], {"title", "research_question", "dataset", "claim_boundary"}, "Idea summary")
    idea = {key: _text(item, f"Idea {key}") for key, item in idea.items()}
    methodology = _object(result["methodology_summary"], {
        "conditions", "evaluation_protocol", "metrics", "robustness_analysis",
        "leakage_controls", "reproducibility_controls", "claim_boundaries",
    }, "Methodology summary")
    methodology = {key: _texts(item, f"Methodology {key}") for key, item in methodology.items()}
    metrics = result["primary_metrics"]
    if not isinstance(metrics, list) or len(metrics) > 30:
        raise ArtifactPresentationContractError("Primary metrics must be bounded")
    normalized_metrics = []
    for raw in metrics:
        metric = _object(raw, {"name", "value", "unit"}, "Primary metric")
        _text(metric["name"], "Metric name", maximum=120)
        if isinstance(metric["value"], bool) or not isinstance(metric["value"], (int, float)) or not math.isfinite(metric["value"]):
            raise ArtifactPresentationContractError("Metric value must be finite")
        if metric["unit"] is not None:
            _text(metric["unit"], "Metric unit", maximum=80)
        normalized_metrics.append(metric)
    normalized = {
        "schema": EXPERIMENT_RECORD_PRESENTATION_SCHEMA,
        "artifact": artifact,
        "selected_idea_summary": idea,
        "experiment_source_mode": _status(result["experiment_source_mode"], _ORIGINS, "Experiment source mode"),
        "methodology_summary": methodology,
        "preparation_status": _status(result["preparation_status"], {"NOT_STARTED", "PREPARING", "VALIDATED", "FAILED"}, "Preparation status"),
        "design_approval_status": _status(result["design_approval_status"], {"NOT_APPROVED", "APPROVED", "INVALIDATED"}, "Design approval status"),
        "run_approval_status": _status(result["run_approval_status"], {"NOT_APPROVED", "APPROVED", "INVALIDATED", "CONSUMED"}, "Run approval status"),
        "provenance_status": _status(result["provenance_status"], {"CONTENT_IDENTIFIED", "VALIDATED", "DRIFTED"}, "Provenance status"),
        "execution_outcome": _status(result["execution_outcome"], _PROCESS, "Execution outcome"),
        "primary_metrics": normalized_metrics,
        "comparisons": _texts(result["comparisons"], "Comparisons"),
        "robustness_summary": _text(result["robustness_summary"], "Robustness summary"),
        "scientific_evidence_status": _status(result["scientific_evidence_status"], _EVIDENCE, "Scientific evidence status"),
        "limitations": _texts(result["limitations"], "Limitations"),
    }
    checksum = result["presentation_checksum"]
    if not isinstance(checksum, str) or not _CHECKSUM.fullmatch(checksum) or canonical_hash(normalized) != checksum:
        raise ArtifactPresentationContractError("Presentation checksum mismatch")
    normalized["presentation_checksum"] = checksum
    if len(canonical_json(normalized).encode("utf-8")) > 32_768:
        raise ArtifactPresentationContractError("Experiment presentation exceeds its byte bound")
    return normalized
