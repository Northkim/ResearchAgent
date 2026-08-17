"""Forward materializable scientific-evidence contract for Experiment v5."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Any, Mapping, Sequence

from backend.workflow_packages.experiment_capability_runtime import CapabilityEvaluationResult
from backend.workflow_packages.generic_experiment_contracts import EvaluationValidity, ProcessOutcome
from backend.workflow_packages.security import require_sha256
from backend.workflow_packages.serialization import (
    SerializableContract, canonical_hash, canonical_json, to_json_value,
)

from .generic_experiment_contracts import ExperimentRecordV4

EXPERIMENT_RECORD_V5_SCHEMA = "experiment-record/v5"
BOUNDED_SCIENTIFIC_EVIDENCE_SCHEMA = (
    "reagent.experiment-bounded-scientific-evidence/v0.1"
)
MAX_EVIDENCE_BLOCKS = 80
MAX_EVIDENCE_BYTES = 65_536

_BLOCK_ID = re.compile(r"^evidence-[a-z0-9][a-z0-9._-]{0,119}$")
_OUTPUT_ID = re.compile(r"^output-[a-z0-9][a-z0-9._-]{0,159}$")
_IDENTITY = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,159}$")
_ABSOLUTE_PATH = re.compile(
    r"(?:/" + r"Users/|/" + r"Volumes/|/home/|/private/|(?:^|\s)[A-Za-z]:\\)"
)
_FORBIDDEN = re.compile(
    r"```|<\s*/?[a-z]|-----BEGIN .*PRIVATE KEY-----|\bTraceback\b|"
    r"(?:^|\n)\s*(?:def |class |import |from \S+ import )|"
    r"(?:https?://)[^\s/@]+:[^\s/@]+@|"
    r"\b(?:OPENAI|ANTHROPIC|REAGENT)_[A-Z0-9_]*KEY\s*=|"
    r"\b(?:password|secret|token|api[_ -]?key)\s*[:=]\s*\S+|"
    r"^\s*\{.*\}\s*$",
    re.IGNORECASE | re.DOTALL,
)


class ExperimentRecordV5Error(ValueError):
    """The forward Experiment evidence carrier is unsafe or inconsistent."""


class EvidenceKind(str, Enum):
    PROSE = "PROSE"
    SCALAR = "SCALAR"
    TABLE = "TABLE"
    SERIES = "SERIES"
    FIGURE_REFERENCE = "FIGURE_REFERENCE"
    OUTPUT_REFERENCE = "OUTPUT_REFERENCE"


class EvidenceSourceKind(str, Enum):
    RESULT_PAYLOAD = "RESULT_PAYLOAD"
    EXECUTION_OUTPUT = "EXECUTION_OUTPUT"


def _hash_without(value: SerializableContract, name: str) -> str:
    return canonical_hash({
        item.name: to_json_value(getattr(value, item.name))
        for item in fields(value) if item.name != name
    })


def _safe_text(value: Any, name: str, maximum: int = 2_000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ExperimentRecordV5Error(f"{name} must be bounded non-empty text")
    if "\x00" in value or _ABSOLUTE_PATH.search(value) or _FORBIDDEN.search(value):
        raise ExperimentRecordV5Error(
            f"{name} contains code, HTML, logs, credentials, or private paths"
        )
    return value


def _scalar(value: Any, name: str) -> Any:
    if value is None or isinstance(value, (str, bool)):
        if isinstance(value, str):
            _safe_text(value, name, 500)
        return value
    if isinstance(value, int) and not isinstance(value, bool) and len(str(abs(value))) <= 100:
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ExperimentRecordV5Error(f"{name} must be a bounded finite scalar")


@dataclass(frozen=True, slots=True)
class EvidenceSourceRef(SerializableContract):
    kind: EvidenceSourceKind
    name: str
    checksum: str

    def __post_init__(self) -> None:
        if _IDENTITY.fullmatch(self.name) is None:
            raise ExperimentRecordV5Error("evidence source name is invalid")
        require_sha256(self.checksum, "evidence source checksum")
        if self.kind is EvidenceSourceKind.RESULT_PAYLOAD and self.name != "result-payload":
            raise ExperimentRecordV5Error("result-payload source identity is invalid")


@dataclass(frozen=True, slots=True)
class ScientificEvidenceBlock(SerializableContract):
    block_id: str
    kind: EvidenceKind
    label: str
    value: Any
    source_refs: tuple[EvidenceSourceRef, ...] = ()
    block_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        if _BLOCK_ID.fullmatch(self.block_id) is None:
            raise ExperimentRecordV5Error("evidence block identity is invalid")
        _safe_text(self.label, "evidence label", 120)
        if len(self.source_refs) > 20 or len(set(self.source_refs)) != len(self.source_refs):
            raise ExperimentRecordV5Error("evidence source references must be bounded and unique")
        value = self.value
        if self.kind is EvidenceKind.PROSE:
            _safe_text(value, "evidence prose")
        elif self.kind is EvidenceKind.SCALAR:
            _scalar(value, "evidence scalar")
        elif self.kind is EvidenceKind.TABLE:
            if not isinstance(value, Mapping) or set(value) != {"columns", "rows"}:
                raise ExperimentRecordV5Error("evidence table shape is invalid")
            columns, rows = value["columns"], value["rows"]
            if not isinstance(columns, (tuple, list)) or not 1 <= len(columns) <= 20:
                raise ExperimentRecordV5Error("evidence table column bound is invalid")
            for column in columns:
                _safe_text(column, "evidence table column", 100)
            if not isinstance(rows, (tuple, list)) or len(rows) > 100:
                raise ExperimentRecordV5Error("evidence table row bound is invalid")
            for row in rows:
                if not isinstance(row, (tuple, list)) or len(row) != len(columns):
                    raise ExperimentRecordV5Error("evidence table row shape is invalid")
                for cell in row:
                    _scalar(cell, "evidence table cell")
        elif self.kind is EvidenceKind.SERIES:
            if not isinstance(value, (tuple, list)) or not 1 <= len(value) <= 500:
                raise ExperimentRecordV5Error("evidence series point bound is invalid")
            for point in value:
                if not isinstance(point, Mapping) or set(point) != {"x", "y"}:
                    raise ExperimentRecordV5Error("evidence series point shape is invalid")
                _scalar(point["x"], "evidence series x")
                _scalar(point["y"], "evidence series y")
        else:
            if not isinstance(value, Mapping) or set(value) != {"output_id", "checksum"}:
                raise ExperimentRecordV5Error("evidence output reference shape is invalid")
            if not isinstance(value["output_id"], str) or _OUTPUT_ID.fullmatch(value["output_id"]) is None:
                raise ExperimentRecordV5Error("evidence output identity is invalid")
            require_sha256(value["checksum"], "evidence output checksum")
        object.__setattr__(self, "block_checksum", _hash_without(self, "block_checksum"))


@dataclass(frozen=True, slots=True)
class BoundedScientificEvidence(SerializableContract):
    capability_checksum: str
    evaluation_checksum: str
    result_payload_checksum: str
    blocks: tuple[ScientificEvidenceBlock, ...]
    schema: str = field(default=BOUNDED_SCIENTIFIC_EVIDENCE_SCHEMA, init=False)
    evidence_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        for name in ("capability_checksum", "evaluation_checksum", "result_payload_checksum"):
            require_sha256(getattr(self, name), name)
        if len(self.blocks) > MAX_EVIDENCE_BLOCKS:
            raise ExperimentRecordV5Error("bounded scientific evidence has too many blocks")
        if len({item.block_id for item in self.blocks}) != len(self.blocks):
            raise ExperimentRecordV5Error("evidence block identities must be unique")
        payload = {
            item.name: to_json_value(getattr(self, item.name))
            for item in fields(self) if item.name != "evidence_checksum"
        }
        if len(canonical_json(payload).encode("utf-8")) > MAX_EVIDENCE_BYTES:
            raise ExperimentRecordV5Error("bounded scientific evidence exceeds its byte limit")
        object.__setattr__(self, "evidence_checksum", _hash_without(self, "evidence_checksum"))


@dataclass(frozen=True, slots=True)
class ExperimentRecordV5(SerializableContract):
    lifecycle_record: ExperimentRecordV4
    bounded_scientific_evidence: BoundedScientificEvidence
    schema: str = field(default=EXPERIMENT_RECORD_V5_SCHEMA, init=False)
    record_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        receipt = self.lifecycle_record.capability_evaluation
        evidence = self.bounded_scientific_evidence
        if (
            evidence.capability_checksum != receipt.capability_checksum
            or evidence.evaluation_checksum != receipt.evaluation_checksum
            or evidence.result_payload_checksum != receipt.result_payload_checksum
        ):
            raise ExperimentRecordV5Error("bounded evidence evaluation lineage mismatch")
        _validate_sources(evidence.blocks, receipt.result_payload_checksum, receipt.execution_outputs)
        if (
            self.lifecycle_record.normalized_result.scientific_evidence_status.value
            == "NOT_AVAILABLE" and evidence.blocks
        ):
            raise ExperimentRecordV5Error("unavailable scientific evidence must not contain findings")
        object.__setattr__(self, "record_checksum", _hash_without(self, "record_checksum"))


def _validate_sources(
    blocks: Sequence[ScientificEvidenceBlock], result_payload_checksum: str,
    execution_outputs: Sequence[Any],
) -> None:
    outputs = {item.name: item.checksum for item in execution_outputs}
    output_checksums = set(outputs.values())
    for block in blocks:
        for source in block.source_refs:
            if source.kind is EvidenceSourceKind.RESULT_PAYLOAD:
                if source.checksum != result_payload_checksum:
                    raise ExperimentRecordV5Error("evidence result-payload lineage mismatch")
            elif outputs.get(source.name) != source.checksum:
                raise ExperimentRecordV5Error("evidence execution-output lineage mismatch")
        if block.kind in {EvidenceKind.FIGURE_REFERENCE, EvidenceKind.OUTPUT_REFERENCE}:
            if block.value["checksum"] not in output_checksums:
                raise ExperimentRecordV5Error("evidence output reference is not an exact execution output")


def evidence_from_capability_result(
    result: CapabilityEvaluationResult,
    blocks: Sequence[ScientificEvidenceBlock],
) -> BoundedScientificEvidence:
    """Bind Capability-owned bounded blocks to the exact local evaluation payload."""

    if canonical_hash(to_json_value(result.result_payload)) != result.receipt.result_payload_checksum:
        raise ExperimentRecordV5Error("Capability result payload checksum drifted")
    evidence = BoundedScientificEvidence(
        result.receipt.capability_checksum,
        result.receipt.evaluation_checksum,
        result.receipt.result_payload_checksum,
        tuple(blocks),
    )
    _validate_sources(evidence.blocks, result.receipt.result_payload_checksum, result.receipt.execution_outputs)
    return evidence


def finalize_experiment_record_v5(
    lifecycle_record: ExperimentRecordV4,
    result: CapabilityEvaluationResult,
    blocks: Sequence[ScientificEvidenceBlock],
) -> ExperimentRecordV5:
    """Create one v5 Artifact from exact v4 lifecycle and local Capability evidence."""

    if lifecycle_record.capability_evaluation != result.receipt:
        raise ExperimentRecordV5Error("Capability evaluation differs from finalized lifecycle")
    return ExperimentRecordV5(
        lifecycle_record,
        evidence_from_capability_result(result, blocks),
    )


def _mapping(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ExperimentRecordV5Error(f"{label} fields mismatch")
    return dict(value)


def _validated_v4_mapping(value: Any) -> dict[str, Any]:
    expected = {
        "research_objective", "methodology", "design_approval", "capability_selection",
        "capability", "implementation_specification", "resource_readiness_evidence",
        "validated_package", "runtime_requirement", "runtime_compatibility",
        "execution_plan", "run_approval", "capability_evaluation", "normalized_result",
        "owner_result_review", "presentation", "limitations", "schema", "record_checksum",
    }
    record = _mapping(value, expected, "Experiment v4 lifecycle record")
    if record["schema"] != "experiment-record/v4":
        raise ExperimentRecordV5Error("Experiment v5 requires exact v4 lifecycle lineage")
    checksum = record.pop("record_checksum")
    require_sha256(checksum, "v4 lifecycle record checksum")
    if canonical_hash(record) != checksum:
        raise ExperimentRecordV5Error("v4 lifecycle record checksum mismatch")
    record["record_checksum"] = checksum
    methodology = _mapping(record["methodology"], set(record["methodology"]), "methodology")
    boundaries = methodology.get("claim_boundaries")
    if not isinstance(boundaries, list) or not boundaries or len(boundaries) > 100:
        raise ExperimentRecordV5Error("v4 claim boundaries are unavailable or unbounded")
    for item in boundaries:
        _safe_text(item, "claim boundary", 1_000)
    normalized = _mapping(
        record["normalized_result"],
        {"process_outcome", "evaluation_validity", "scientific_evidence_status", "limitations"},
        "normalized result",
    )
    if normalized["process_outcome"] not in {item.value for item in ProcessOutcome}:
        raise ExperimentRecordV5Error("v4 process outcome is invalid")
    if normalized["evaluation_validity"] not in {item.value for item in EvaluationValidity}:
        raise ExperimentRecordV5Error("v4 evaluation validity is invalid")
    if normalized["scientific_evidence_status"] not in {
        "NOT_AVAILABLE", "LIMITED", "SUPPORTS_BOUNDED_FINDINGS", "CONTRADICTORY", "INCONCLUSIVE",
    }:
        raise ExperimentRecordV5Error("v4 scientific evidence status is invalid")
    for label, limitations in (
        ("normalized limitation", normalized["limitations"]),
        ("record limitation", record["limitations"]),
    ):
        if not isinstance(limitations, list) or len(limitations) > 40:
            raise ExperimentRecordV5Error("v4 limitations are invalid")
        for item in limitations:
            _safe_text(item, label, 1_000)
    evaluation = _mapping(record["capability_evaluation"], set(record["capability_evaluation"]), "evaluation")
    if evaluation.get("validity") != normalized["evaluation_validity"]:
        raise ExperimentRecordV5Error("v4 evaluation validity lineage mismatch")
    evaluation_checksum = evaluation.pop("evaluation_checksum", None)
    require_sha256(evaluation_checksum, "evaluation checksum")
    if canonical_hash(evaluation) != evaluation_checksum:
        raise ExperimentRecordV5Error("evaluation checksum mismatch")
    evaluation["evaluation_checksum"] = evaluation_checksum
    require_sha256(evaluation.get("capability_checksum"), "evaluation capability checksum")
    require_sha256(evaluation.get("result_payload_checksum"), "result payload checksum")
    outputs = evaluation.get("execution_outputs")
    if not isinstance(outputs, list) or not outputs or len(outputs) > 50:
        raise ExperimentRecordV5Error("evaluation outputs are invalid")
    for output in outputs:
        item = _mapping(output, {"name", "checksum"}, "evaluation output")
        if _IDENTITY.fullmatch(str(item["name"])) is None:
            raise ExperimentRecordV5Error("evaluation output name is invalid")
        require_sha256(item["checksum"], "evaluation output checksum")
    return record


def _evidence_from_mapping(value: Any) -> BoundedScientificEvidence:
    item = _mapping(value, {
        "capability_checksum", "evaluation_checksum", "result_payload_checksum",
        "blocks", "schema", "evidence_checksum",
    }, "bounded scientific evidence")
    if item["schema"] != BOUNDED_SCIENTIFIC_EVIDENCE_SCHEMA:
        raise ExperimentRecordV5Error("bounded scientific evidence schema mismatch")
    raw_blocks = item["blocks"]
    if not isinstance(raw_blocks, list) or len(raw_blocks) > MAX_EVIDENCE_BLOCKS:
        raise ExperimentRecordV5Error("bounded scientific evidence blocks are invalid")
    blocks = []
    for raw in raw_blocks:
        block = _mapping(raw, {
            "block_id", "kind", "label", "value", "source_refs", "block_checksum",
        }, "scientific evidence block")
        sources = block["source_refs"]
        if not isinstance(sources, list):
            raise ExperimentRecordV5Error("evidence source references are invalid")
        typed_sources = tuple(EvidenceSourceRef(
            EvidenceSourceKind(source["kind"]), source["name"], source["checksum"],
        ) for source in sources if isinstance(source, Mapping))
        if len(typed_sources) != len(sources):
            raise ExperimentRecordV5Error("evidence source reference shape is invalid")
        typed = ScientificEvidenceBlock(
            block["block_id"], EvidenceKind(block["kind"]), block["label"],
            block["value"], typed_sources,
        )
        if typed.block_checksum != block["block_checksum"]:
            raise ExperimentRecordV5Error("evidence block checksum mismatch")
        blocks.append(typed)
    evidence = BoundedScientificEvidence(
        item["capability_checksum"], item["evaluation_checksum"],
        item["result_payload_checksum"], tuple(blocks),
    )
    if evidence.evidence_checksum != item["evidence_checksum"]:
        raise ExperimentRecordV5Error("bounded scientific evidence checksum mismatch")
    return evidence


def validate_experiment_record_v5(value: ExperimentRecordV5 | Mapping[str, Any]) -> dict[str, Any]:
    """Validate typed finalization or materialized canonical JSON without presentation."""

    if isinstance(value, ExperimentRecordV5):
        return value.to_dict()
    record = _mapping(value, {
        "lifecycle_record", "bounded_scientific_evidence", "schema", "record_checksum",
    }, "experiment-record/v5")
    if record["schema"] != EXPERIMENT_RECORD_V5_SCHEMA:
        raise ExperimentRecordV5Error("experiment-record/v5 schema mismatch")
    lifecycle = _validated_v4_mapping(record["lifecycle_record"])
    evidence = _evidence_from_mapping(record["bounded_scientific_evidence"])
    evaluation = lifecycle["capability_evaluation"]
    if (
        evidence.capability_checksum != evaluation["capability_checksum"]
        or evidence.evaluation_checksum != evaluation["evaluation_checksum"]
        or evidence.result_payload_checksum != evaluation["result_payload_checksum"]
    ):
        raise ExperimentRecordV5Error("materialized evidence lineage mismatch")
    outputs = tuple(type("Output", (), item)() for item in evaluation["execution_outputs"])
    _validate_sources(evidence.blocks, evidence.result_payload_checksum, outputs)
    if (
        lifecycle["normalized_result"]["scientific_evidence_status"] == "NOT_AVAILABLE"
        and evidence.blocks
    ):
        raise ExperimentRecordV5Error("unavailable scientific evidence must not contain findings")
    checksum = record["record_checksum"]
    require_sha256(checksum, "experiment-record/v5 checksum")
    if canonical_hash({
        "lifecycle_record": lifecycle,
        "bounded_scientific_evidence": evidence,
        "schema": EXPERIMENT_RECORD_V5_SCHEMA,
    }) != checksum:
        raise ExperimentRecordV5Error("experiment-record/v5 checksum mismatch")
    return {
        "lifecycle_record": lifecycle,
        "bounded_scientific_evidence": evidence.to_dict(),
        "schema": EXPERIMENT_RECORD_V5_SCHEMA,
        "record_checksum": checksum,
    }
