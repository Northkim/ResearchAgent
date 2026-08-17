"""Unpublished generic experiment-record/v4 and safe presentation foundation."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Any

from backend.workflow_packages.generic_experiment_contracts import (
    CapabilityEvaluationReceipt,
    CapabilitySelection,
    CompatibilityStatus,
    ContractRef,
    DesignApproval,
    EvaluationValidity,
    ExperimentCapability,
    GenericMethodology,
    ImplementationSpecificationRef,
    NormalizedExperimentResult,
    ProcessOutcome,
    ResearchObjectiveRef,
    RuntimeCompatibility,
    RuntimeRequirement,
    ScientificEvidenceStatus,
)
from backend.workflow_packages.generic_experiment_package import ValidatedExperimentPackage
from backend.workflow_packages.security import require_sha256
from backend.workflow_packages.serialization import SerializableContract, canonical_hash, canonical_json, to_json_value

PRESENTATION_SCHEMA = "reagent.artifact-presentation.experiment-record/v0.2"
EXPERIMENT_RECORD_V4_SCHEMA = "experiment-record/v4"
_ARTIFACT_ID = re.compile(r"^artifact-[0-9a-f]{32}$")
_ABSOLUTE_PATH = re.compile(
    r"(?:^|\s)(?:/" + r"Users/|/" + r"Volumes/|/home/|[A-Za-z]:\\)"
)
_FORBIDDEN = re.compile(
    r"```|<\s*/?[a-z]|-----BEGIN .*PRIVATE " + r"KEY-----|\bTraceback\b|"
    r"(?:https?://)[^\s/@]+:[^\s/@]+@",
    re.IGNORECASE,
)
_OUTPUT_ID = re.compile(r"^output-[a-z0-9][a-z0-9._-]{0,159}$")


class GenericExperimentArtifactError(ValueError):
    pass


class PresentationKind(str, Enum):
    PROSE = "PROSE"
    SCALAR = "SCALAR"
    TABLE = "TABLE"
    SERIES = "SERIES"
    FIGURE_REFERENCE = "FIGURE_REFERENCE"
    OUTPUT_REFERENCE = "OUTPUT_REFERENCE"


def _safe_text(value: Any, name: str, maximum: int = 2_000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise GenericExperimentArtifactError(f"{name} must be bounded non-empty text")
    if _ABSOLUTE_PATH.search(value) or _FORBIDDEN.search(value) or "\x00" in value:
        raise GenericExperimentArtifactError(f"{name} contains code, private paths, logs, or credentials")
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
    raise GenericExperimentArtifactError(f"{name} must be a bounded scalar")


def _hash_without(value: SerializableContract, field_name: str) -> str:
    payload = {
        item.name: to_json_value(getattr(value, item.name))
        for item in fields(value) if item.name != field_name
    }
    return canonical_hash(payload)


@dataclass(frozen=True, slots=True)
class PresentationBlock(SerializableContract):
    kind: PresentationKind
    label: str
    value: Any

    def __post_init__(self) -> None:
        _safe_text(self.label, "presentation label", 120)
        value = self.value
        if self.kind is PresentationKind.PROSE:
            _safe_text(value, "prose")
        elif self.kind is PresentationKind.SCALAR:
            _scalar(value, "scalar")
        elif self.kind is PresentationKind.TABLE:
            if not isinstance(value, dict) or set(value) != {"columns", "rows"}:
                raise GenericExperimentArtifactError("table must contain columns and rows")
            columns, rows = value["columns"], value["rows"]
            if not isinstance(columns, (tuple, list)) or not 1 <= len(columns) <= 20:
                raise GenericExperimentArtifactError("table column bound is invalid")
            for column in columns:
                _safe_text(column, "table column", 100)
            if not isinstance(rows, (tuple, list)) or len(rows) > 100:
                raise GenericExperimentArtifactError("table row bound is invalid")
            for row in rows:
                if not isinstance(row, (tuple, list)) or len(row) != len(columns):
                    raise GenericExperimentArtifactError("table row shape is invalid")
                for cell in row:
                    _scalar(cell, "table cell")
        elif self.kind is PresentationKind.SERIES:
            if not isinstance(value, (tuple, list)) or not 1 <= len(value) <= 500:
                raise GenericExperimentArtifactError("series point bound is invalid")
            for point in value:
                if not isinstance(point, dict) or set(point) != {"x", "y"}:
                    raise GenericExperimentArtifactError("series points require x and y")
                _scalar(point["x"], "series x")
                _scalar(point["y"], "series y")
        else:
            if not isinstance(value, dict) or set(value) != {"output_id", "checksum"}:
                raise GenericExperimentArtifactError("output reference shape is invalid")
            if not isinstance(value["output_id"], str) or _OUTPUT_ID.fullmatch(value["output_id"]) is None:
                raise GenericExperimentArtifactError("output reference identity is invalid")
            require_sha256(value["checksum"], "output reference checksum")


@dataclass(frozen=True, slots=True)
class GenericExperimentPresentation(SerializableContract):
    artifact_id: str
    artifact_checksum: str
    blocks: tuple[PresentationBlock, ...]
    schema: str = field(default=PRESENTATION_SCHEMA, init=False)
    presentation_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        if _ARTIFACT_ID.fullmatch(self.artifact_id) is None:
            raise GenericExperimentArtifactError("presentation Artifact ID is invalid")
        require_sha256(self.artifact_checksum, "artifact_checksum")
        if not self.blocks or len(self.blocks) > 80:
            raise GenericExperimentArtifactError("presentation blocks must be bounded and non-empty")
        payload = {
            item.name: to_json_value(getattr(self, item.name))
            for item in fields(self) if item.name != "presentation_checksum"
        }
        if len(canonical_json(payload).encode()) > 65_536:
            raise GenericExperimentArtifactError("presentation exceeds its byte bound")
        object.__setattr__(self, "presentation_checksum", _hash_without(self, "presentation_checksum"))


@dataclass(frozen=True, slots=True)
class ExperimentRecordV4(SerializableContract):
    research_objective: ResearchObjectiveRef
    methodology: GenericMethodology
    design_approval: DesignApproval
    capability_selection: CapabilitySelection
    capability: ExperimentCapability
    implementation_specification: ImplementationSpecificationRef
    resource_readiness_evidence: tuple[ContractRef, ...]
    validated_package: ValidatedExperimentPackage
    runtime_requirement: RuntimeRequirement
    runtime_compatibility: RuntimeCompatibility
    execution_plan: ContractRef
    run_approval: ContractRef
    capability_evaluation: CapabilityEvaluationReceipt
    normalized_result: NormalizedExperimentResult
    owner_result_review: ContractRef
    presentation: ContractRef
    limitations: tuple[str, ...]
    schema: str = field(default=EXPERIMENT_RECORD_V4_SCHEMA, init=False)
    record_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        if self.methodology.research_objective != self.research_objective:
            raise GenericExperimentArtifactError("Methodology objective lineage mismatch")
        self.design_approval.validate(self.methodology)
        if len(self.resource_readiness_evidence) > 50 or len({item.checksum for item in self.resource_readiness_evidence}) != len(self.resource_readiness_evidence):
            raise GenericExperimentArtifactError("Resource readiness evidence must be bounded and unique")
        if (
            self.capability_selection.methodology_checksum != self.methodology.methodology_checksum
            or
            self.capability_selection.selected_capability_checksum != self.capability.capability_checksum
            or self.implementation_specification.capability_checksum != self.capability.capability_checksum
            or self.implementation_specification.methodology_checksum != self.methodology.methodology_checksum
            or self.validated_package.manifest.capability_checksum != self.capability.capability_checksum
            or self.validated_package.prepared_receipt.research_objective != self.research_objective
            or self.validated_package.prepared_receipt.methodology_checksum != self.methodology.methodology_checksum
            or self.runtime_requirement.requirement_checksum != self.validated_package.runtime_requirement_checksum
            or self.runtime_compatibility.runtime_requirement_checksum != self.runtime_requirement.requirement_checksum
            or self.capability_evaluation.capability_checksum != self.capability.capability_checksum
            or self.capability_evaluation.objective_checksum != self.research_objective.objective_ref_checksum
            or self.capability_evaluation.methodology_checksum != self.methodology.methodology_checksum
            or self.capability_evaluation.implementation_specification_checksum
            != self.implementation_specification.specification_checksum
            or self.capability_evaluation.execution_plan_checksum != self.execution_plan.checksum
        ):
            raise GenericExperimentArtifactError("Experiment v4 exact lineage is inconsistent")
        if self.runtime_compatibility.status is not CompatibilityStatus.COMPATIBLE:
            raise GenericExperimentArtifactError("final Experiment requires compatible runtime evidence")
        if (
            self.normalized_result.evaluation_validity != self.capability_evaluation.validity
            or self.normalized_result.process_outcome is ProcessOutcome.NOT_RUN
        ):
            raise GenericExperimentArtifactError("normalized result conflicts with execution/evaluation evidence")
        if len(self.limitations) > 40:
            raise GenericExperimentArtifactError("limitations exceed the bound")
        for limitation in self.limitations:
            _safe_text(limitation, "limitation", 1_000)
        object.__setattr__(self, "record_checksum", _hash_without(self, "record_checksum"))
