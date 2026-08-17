"""Unpublished, research-domain-neutral Experiment contract foundations.

These contracts describe identity and lifecycle evidence only.  They do not
select Artifacts, discover code, admit execution, or install dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields
from enum import Enum
from pathlib import PurePosixPath, PureWindowsPath
from typing import ClassVar

from .security import require_relative_path, require_sha256
from .serialization import SerializableContract, canonical_hash, to_json_value

OBJECTIVE_SCHEMA = "reagent.experiment-research-objective-ref/v0.1"
METHODOLOGY_SCHEMA = "reagent.experiment-methodology/v0.2"
DESIGN_APPROVAL_SCHEMA = "reagent.experiment-design-approval/v0.2"
CAPABILITY_SCHEMA = "reagent.experiment-capability/v0.1"
CAPABILITY_SELECTION_SCHEMA = "reagent.experiment-capability-selection/v0.1"
IMPLEMENTATION_SPEC_REF_SCHEMA = "reagent.experiment-implementation-specification-ref/v0.1"
PREPARATION_REQUIREMENT_SCHEMA = "reagent.experiment-preparation-requirement/v0.1"
RUNTIME_REQUIREMENT_SCHEMA = "reagent.experiment-runtime-requirement/v0.1"
RUNTIME_CANDIDATE_SCHEMA = "reagent.experiment-runtime-candidate/v0.1"
RUNTIME_COMPATIBILITY_SCHEMA = "reagent.experiment-runtime-compatibility/v0.1"
CAPABILITY_EVALUATION_SCHEMA = "reagent.experiment-capability-evaluation/v0.1"

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,199}$")
_ARTIFACT_ID = re.compile(r"^artifact-[0-9a-f]{32}$")
_SCHEMA = re.compile(r"^[a-z0-9][a-z0-9._-]*(?:/[a-z0-9._-]+)+$")
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_FORBIDDEN_SUMMARY = re.compile(
    r"```|<\s*(?:script|style)|\b(?:def|class|import)\s+|#!|\x00", re.IGNORECASE
)
SUPPORTED_OBJECTIVE_ARTIFACT_TYPES = frozenset({"selected-research-idea/v1"})


class GenericExperimentContractError(ValueError):
    pass


def _text(value: str, name: str, maximum: int = 1_000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise GenericExperimentContractError(f"{name} must be bounded non-empty text")
    return value


def _texts(values: tuple[str, ...], name: str, maximum: int = 40) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not values or len(values) > maximum:
        raise GenericExperimentContractError(f"{name} must be a bounded non-empty tuple")
    return tuple(_text(value, name) for value in values)


def _optional_texts(values: tuple[str, ...], name: str, maximum: int = 40) -> tuple[str, ...]:
    if not isinstance(values, tuple) or len(values) > maximum:
        raise GenericExperimentContractError(f"{name} must be a bounded tuple")
    return tuple(_text(value, name) for value in values)


def _identity(value: str, name: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise GenericExperimentContractError(f"{name} has an invalid identity")
    return value


def _schema(value: str, name: str) -> str:
    if not isinstance(value, str) or _SCHEMA.fullmatch(value) is None:
        raise GenericExperimentContractError(f"{name} has an invalid schema identity")
    return value


def _timestamp(value: str, name: str) -> str:
    if not isinstance(value, str) or _TIMESTAMP.fullmatch(value) is None:
        raise GenericExperimentContractError(f"{name} must be canonical UTC text")
    return value


def _checksum_payload(value: SerializableContract, field_name: str) -> str:
    payload = {
        item.name: to_json_value(getattr(value, item.name))
        for item in fields(value) if item.name != field_name
    }
    return canonical_hash(payload)


def _absolute_path(value: str) -> bool:
    return PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()


@dataclass(frozen=True, slots=True)
class ContractRef(SerializableContract):
    schema_identity: str
    checksum: str

    def __post_init__(self) -> None:
        _schema(self.schema_identity, "schema_identity")
        require_sha256(self.checksum, "checksum")


@dataclass(frozen=True, slots=True)
class ExactIdentity(SerializableContract):
    identity: str
    version: str
    checksum: str

    def __post_init__(self) -> None:
        _identity(self.identity, "identity")
        if _SEMVER.fullmatch(self.version) is None:
            raise GenericExperimentContractError("version must use semantic versioning")
        require_sha256(self.checksum, "checksum")


@dataclass(frozen=True, slots=True)
class NamedChecksum(SerializableContract):
    name: str
    checksum: str

    def __post_init__(self) -> None:
        _identity(self.name, "name")
        require_sha256(self.checksum, "checksum")


@dataclass(frozen=True, slots=True)
class ResearchObjectiveRef(SerializableContract):
    source_artifact_type: str
    source_artifact_id: str
    source_artifact_checksum: str
    objective_summary: str
    schema: str = field(default=OBJECTIVE_SCHEMA, init=False)
    objective_ref_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        if self.source_artifact_type not in SUPPORTED_OBJECTIVE_ARTIFACT_TYPES:
            raise GenericExperimentContractError("objective source Artifact type is unsupported")
        if _ARTIFACT_ID.fullmatch(self.source_artifact_id) is None:
            raise GenericExperimentContractError("source_artifact_id is invalid")
        require_sha256(self.source_artifact_checksum, "source_artifact_checksum")
        _text(self.objective_summary, "objective_summary", 2_000)
        object.__setattr__(self, "objective_ref_checksum", _checksum_payload(self, "objective_ref_checksum"))


@dataclass(frozen=True, slots=True)
class GenericMethodology(SerializableContract):
    research_objective: ResearchObjectiveRef
    questions_or_hypotheses: tuple[str, ...]
    inputs_or_materials: tuple[str, ...]
    protocol: tuple[str, ...]
    observations_or_outputs: tuple[str, ...]
    evaluation_criteria: tuple[str, ...]
    reproducibility_controls: tuple[str, ...]
    resource_constraints: tuple[str, ...]
    compute_constraints: tuple[str, ...]
    network_policy: str
    assumptions: tuple[str, ...]
    claim_boundaries: tuple[str, ...]
    unresolved_material_decisions: tuple[str, ...] = ()
    domain_methodology_ref: ContractRef | None = None
    schema: str = field(default=METHODOLOGY_SCHEMA, init=False)
    methodology_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        for name in (
            "questions_or_hypotheses", "inputs_or_materials", "protocol",
            "observations_or_outputs", "evaluation_criteria", "reproducibility_controls",
            "resource_constraints", "compute_constraints", "assumptions", "claim_boundaries",
        ):
            _texts(getattr(self, name), name)
        _optional_texts(self.unresolved_material_decisions, "unresolved_material_decisions")
        if self.network_policy not in {"DISABLED", "BOUNDED_DECLARED"}:
            raise GenericExperimentContractError("network_policy is invalid")
        object.__setattr__(self, "methodology_checksum", _checksum_payload(self, "methodology_checksum"))


@dataclass(frozen=True, slots=True)
class DesignApproval(SerializableContract):
    research_objective_checksum: str
    methodology_checksum: str
    frozen_scientific_requirements_checksum: str
    evaluation_criteria_checksum: str
    claim_boundaries_checksum: str
    approved_at: str
    authorization_scope: str = field(default="PREPARATION_ONLY", init=False)
    schema: str = field(default=DESIGN_APPROVAL_SCHEMA, init=False)
    approval_checksum: str = field(init=False)

    @classmethod
    def approve(cls, methodology: GenericMethodology, approved_at: str) -> "DesignApproval":
        if methodology.unresolved_material_decisions:
            raise GenericExperimentContractError("material methodology decisions remain unresolved")
        return cls(
            methodology.research_objective.objective_ref_checksum,
            methodology.methodology_checksum,
            canonical_hash({"methodology": methodology.methodology_checksum, "protocol": methodology.protocol}),
            canonical_hash(methodology.evaluation_criteria),
            canonical_hash(methodology.claim_boundaries),
            approved_at,
        )

    def __post_init__(self) -> None:
        for name in (
            "research_objective_checksum", "methodology_checksum",
            "frozen_scientific_requirements_checksum", "evaluation_criteria_checksum",
            "claim_boundaries_checksum",
        ):
            require_sha256(getattr(self, name), name)
        _timestamp(self.approved_at, "approved_at")
        object.__setattr__(self, "approval_checksum", _checksum_payload(self, "approval_checksum"))

    def validate(self, methodology: GenericMethodology) -> None:
        if (
            self.research_objective_checksum != methodology.research_objective.objective_ref_checksum
            or self.methodology_checksum != methodology.methodology_checksum
            or self.frozen_scientific_requirements_checksum
            != canonical_hash({"methodology": methodology.methodology_checksum, "protocol": methodology.protocol})
            or self.evaluation_criteria_checksum != canonical_hash(methodology.evaluation_criteria)
            or self.claim_boundaries_checksum != canonical_hash(methodology.claim_boundaries)
        ):
            raise GenericExperimentContractError("methodology drift invalidates Design Approval")


class CapabilityOperation(str, Enum):
    ASSESS_SUPPORT = "ASSESS_SUPPORT"
    PREPARE = "PREPARE"
    DECLARE_REQUIREMENTS = "DECLARE_REQUIREMENTS"
    EVALUATE = "EVALUATE"
    PRESENT = "PRESENT"


@dataclass(frozen=True, slots=True)
class ExperimentCapability(SerializableContract):
    interface_version: str
    skill: ExactIdentity
    capsule: ExactIdentity
    implementation_entrypoint: str | None
    implementation_entrypoint_checksum: str | None
    operations: tuple[CapabilityOperation, ...]
    implementation_spec_schema: str | None = None
    evaluation_schema: str | None = None
    presentation_schema: str | None = None
    schema: str = field(default=CAPABILITY_SCHEMA, init=False)
    capability_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        if _SEMVER.fullmatch(self.interface_version) is None:
            raise GenericExperimentContractError("capability interface_version is invalid")
        if not self.operations or len(set(self.operations)) != len(self.operations):
            raise GenericExperimentContractError("capability operations must be non-empty and unique")
        if self.implementation_entrypoint is None:
            if self.implementation_entrypoint_checksum is not None:
                raise GenericExperimentContractError("entrypoint checksum has no entrypoint")
        else:
            require_relative_path(self.implementation_entrypoint, "implementation_entrypoint")
            require_sha256(self.implementation_entrypoint_checksum, "implementation_entrypoint_checksum")
        for name in ("implementation_spec_schema", "evaluation_schema", "presentation_schema"):
            value = getattr(self, name)
            if value is not None:
                _schema(value, name)
        object.__setattr__(self, "capability_checksum", _checksum_payload(self, "capability_checksum"))


class SupportStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    NEEDS_OWNER_DECISION = "NEEDS_OWNER_DECISION"


@dataclass(frozen=True, slots=True)
class CapabilityAssessment(SerializableContract):
    capability_checksum: str
    objective_checksum: str
    methodology_checksum: str
    status: SupportStatus
    reasons: tuple[str, ...]
    presentation_order: int = 0
    assessment_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        for name in ("capability_checksum", "objective_checksum", "methodology_checksum"):
            require_sha256(getattr(self, name), name)
        _texts(self.reasons, "assessment reasons", 10)
        if not 0 <= self.presentation_order <= 10_000:
            raise GenericExperimentContractError("presentation_order is invalid")
        object.__setattr__(self, "assessment_checksum", _checksum_payload(self, "assessment_checksum"))


class SelectionMateriality(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    MATERIAL_DIFFERENCE = "MATERIAL_DIFFERENCE"
    NON_MATERIAL_FALLBACK_EQUIVALENT = "NON_MATERIAL_FALLBACK_EQUIVALENT"


class SelectionOutcome(str, Enum):
    AUTOMATIC_PREPARATION_UNSUPPORTED = "AUTOMATIC_PREPARATION_UNSUPPORTED"
    CAPABILITY_ASSESSMENT_OWNER_DECISION_REQUIRED = "CAPABILITY_ASSESSMENT_OWNER_DECISION_REQUIRED"
    AUTO_SELECTED = "AUTO_SELECTED"
    PREPARATION_CAPABILITY_SELECTION_REQUIRED = "PREPARATION_CAPABILITY_SELECTION_REQUIRED"
    OWNER_CONFIRMED = "OWNER_CONFIRMED"


@dataclass(frozen=True, slots=True)
class CapabilitySelection(SerializableContract):
    methodology_checksum: str
    assessments: tuple[CapabilityAssessment, ...]
    materiality: SelectionMateriality
    selected_capability_checksum: str | None
    rationale: str
    owner_confirmation_checksum: str | None
    outcome: SelectionOutcome = field(init=False)
    schema: str = field(default=CAPABILITY_SELECTION_SCHEMA, init=False)
    selection_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        require_sha256(self.methodology_checksum, "methodology_checksum")
        if len(self.assessments) > 40:
            raise GenericExperimentContractError("capability assessments exceed the bound")
        if any(item.methodology_checksum != self.methodology_checksum for item in self.assessments):
            raise GenericExperimentContractError("assessment methodology lineage mismatch")
        if len({item.capability_checksum for item in self.assessments}) != len(self.assessments):
            raise GenericExperimentContractError("capability assessments must be unique")
        if len({item.objective_checksum for item in self.assessments}) > 1:
            raise GenericExperimentContractError("capability assessments disagree on objective identity")
        _text(self.rationale, "selection rationale")
        supported = tuple(item for item in self.assessments if item.status is SupportStatus.SUPPORTED)
        awaiting_owner = tuple(
            item for item in self.assessments if item.status is SupportStatus.NEEDS_OWNER_DECISION
        )
        selected = self.selected_capability_checksum
        if selected is not None:
            require_sha256(selected, "selected_capability_checksum")
        if self.owner_confirmation_checksum is not None:
            require_sha256(self.owner_confirmation_checksum, "owner_confirmation_checksum")
        if awaiting_owner:
            outcome = SelectionOutcome.CAPABILITY_ASSESSMENT_OWNER_DECISION_REQUIRED
            if selected is not None:
                raise GenericExperimentContractError("unresolved support assessment cannot select a capability")
        elif not supported:
            outcome = SelectionOutcome.AUTOMATIC_PREPARATION_UNSUPPORTED
            if selected is not None:
                raise GenericExperimentContractError("unsupported selection cannot select a capability")
        elif len(supported) == 1:
            outcome = SelectionOutcome.AUTO_SELECTED
            expected = supported[0].capability_checksum
            if selected != expected or self.materiality is not SelectionMateriality.NOT_APPLICABLE:
                raise GenericExperimentContractError("single supported capability must be selected automatically")
        elif self.materiality is SelectionMateriality.NON_MATERIAL_FALLBACK_EQUIVALENT:
            outcome = SelectionOutcome.AUTO_SELECTED
            expected = min(supported, key=lambda item: (item.presentation_order, item.capability_checksum)).capability_checksum
            if selected != expected:
                raise GenericExperimentContractError("non-material fallback selection is not deterministic")
        else:
            if self.materiality is not SelectionMateriality.MATERIAL_DIFFERENCE:
                raise GenericExperimentContractError("multiple capabilities require explicit materiality")
            if self.owner_confirmation_checksum is None:
                outcome = SelectionOutcome.PREPARATION_CAPABILITY_SELECTION_REQUIRED
                if selected is not None:
                    raise GenericExperimentContractError("material selection requires Owner confirmation")
            else:
                outcome = SelectionOutcome.OWNER_CONFIRMED
                if selected not in {item.capability_checksum for item in supported}:
                    raise GenericExperimentContractError("Owner-selected capability was not supported")
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "selection_checksum", _checksum_payload(self, "selection_checksum"))


@dataclass(frozen=True, slots=True)
class ImplementationSpecificationRef(SerializableContract):
    capability_checksum: str
    specification_schema: str
    methodology_checksum: str
    specification_checksum: str
    validation_receipt: ContractRef
    summary: tuple[tuple[str, str], ...] = ()
    schema: str = field(default=IMPLEMENTATION_SPEC_REF_SCHEMA, init=False)
    reference_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        for name in ("capability_checksum", "methodology_checksum", "specification_checksum"):
            require_sha256(getattr(self, name), name)
        _schema(self.specification_schema, "specification_schema")
        if len(self.summary) > 20:
            raise GenericExperimentContractError("implementation summary exceeds its item bound")
        for label, value in self.summary:
            _text(label, "summary label", 100)
            _text(value, "summary value", 500)
            if _FORBIDDEN_SUMMARY.search(value) or _absolute_path(value):
                raise GenericExperimentContractError("implementation summary must be non-executable and portable")
        object.__setattr__(self, "reference_checksum", _checksum_payload(self, "reference_checksum"))


@dataclass(frozen=True, slots=True)
class PreparationRequirement(SerializableContract):
    requirement_key: str
    capability_checksum: str
    requirement_family: str
    version_constraint: str | None
    required_capabilities: tuple[str, ...]
    required: bool = True
    schema: str = field(default=PREPARATION_REQUIREMENT_SCHEMA, init=False)
    requirement_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        _identity(self.requirement_key, "requirement_key")
        require_sha256(self.capability_checksum, "capability_checksum")
        _identity(self.requirement_family, "requirement_family")
        if self.version_constraint is not None:
            _text(self.version_constraint, "version_constraint", 120)
        _optional_texts(self.required_capabilities, "required_capabilities", 30)
        object.__setattr__(self, "requirement_checksum", _checksum_payload(self, "requirement_checksum"))


@dataclass(frozen=True, slots=True)
class RuntimeRequirement(SerializableContract):
    runtime_family: str
    version_constraint: str
    required_capabilities: tuple[str, ...]
    dependency_declarations: tuple[ContractRef, ...]
    launch_contract: ContractRef
    network_policy: str
    resource_constraints: tuple[tuple[str, str], ...]
    schema: str = field(default=RUNTIME_REQUIREMENT_SCHEMA, init=False)
    requirement_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        _identity(self.runtime_family, "runtime_family")
        _text(self.version_constraint, "version_constraint", 120)
        _optional_texts(self.required_capabilities, "required_capabilities", 30)
        if len(self.dependency_declarations) > 20:
            raise GenericExperimentContractError("dependency declarations exceed the bound")
        if len({item.checksum for item in self.dependency_declarations}) != len(self.dependency_declarations):
            raise GenericExperimentContractError("dependency declarations must be unique")
        if self.network_policy not in {"DISABLED", "BOUNDED_DECLARED"}:
            raise GenericExperimentContractError("runtime network_policy is invalid")
        if len(self.resource_constraints) > 20:
            raise GenericExperimentContractError("resource constraints exceed the bound")
        for name, value in self.resource_constraints:
            _identity(name, "resource constraint name")
            _text(value, "resource constraint value", 120)
        object.__setattr__(self, "requirement_checksum", _checksum_payload(self, "requirement_checksum"))


@dataclass(frozen=True, slots=True)
class LocalRuntimeCandidate(SerializableContract):
    candidate_id: str
    runtime_family: str
    runtime_version: str
    local_launcher_path: str
    available_capabilities: tuple[str, ...]
    environment_checksum: str
    dependency_identity_checksums: tuple[str, ...]
    locally_verified: bool
    schema: str = field(default=RUNTIME_CANDIDATE_SCHEMA, init=False)
    portable_identity_checksum: str = field(init=False)
    local_receipt_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        _identity(self.candidate_id, "candidate_id")
        _identity(self.runtime_family, "runtime_family")
        _text(self.runtime_version, "runtime_version", 80)
        if not _absolute_path(self.local_launcher_path):
            raise GenericExperimentContractError("local_launcher_path must be an absolute local-only path")
        _optional_texts(self.available_capabilities, "available_capabilities", 50)
        require_sha256(self.environment_checksum, "environment_checksum")
        for checksum in self.dependency_identity_checksums:
            require_sha256(checksum, "dependency_identity_checksum")
        if len(self.dependency_identity_checksums) > 20 or len(set(self.dependency_identity_checksums)) != len(self.dependency_identity_checksums):
            raise GenericExperimentContractError("local dependency identities must be bounded and unique")
        portable = {
            "runtime_family": self.runtime_family, "runtime_version": self.runtime_version,
            "available_capabilities": self.available_capabilities,
            "environment_checksum": self.environment_checksum,
            "dependency_identity_checksums": self.dependency_identity_checksums,
        }
        object.__setattr__(self, "portable_identity_checksum", canonical_hash(portable))
        object.__setattr__(self, "local_receipt_checksum", _checksum_payload(self, "local_receipt_checksum"))

    def portable_identity(self) -> dict[str, object]:
        return {
            "runtime_family": self.runtime_family,
            "runtime_version": self.runtime_version,
            "available_capabilities": list(self.available_capabilities),
            "environment_checksum": self.environment_checksum,
            "dependency_identity_checksums": list(self.dependency_identity_checksums),
            "portable_identity_checksum": self.portable_identity_checksum,
        }


class CompatibilityStatus(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"


@dataclass(frozen=True, slots=True)
class RuntimeCompatibility(SerializableContract):
    runtime_requirement_checksum: str
    portable_runtime_identity_checksum: str
    environment_checksum: str
    status: CompatibilityStatus
    reasons: tuple[str, ...]
    verified_at: str
    schema: str = field(default=RUNTIME_COMPATIBILITY_SCHEMA, init=False)
    compatibility_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        for name in ("runtime_requirement_checksum", "portable_runtime_identity_checksum", "environment_checksum"):
            require_sha256(getattr(self, name), name)
        _texts(self.reasons, "compatibility reasons", 20)
        _timestamp(self.verified_at, "verified_at")
        object.__setattr__(self, "compatibility_checksum", _checksum_payload(self, "compatibility_checksum"))


class EvaluationValidity(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    VALID = "VALID"
    INVALID = "INVALID"
    INDETERMINATE = "INDETERMINATE"


class ProcessOutcome(str, Enum):
    NOT_RUN = "NOT_RUN"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"


class ScientificEvidenceStatus(str, Enum):
    NOT_AVAILABLE = "NOT_AVAILABLE"
    LIMITED = "LIMITED"
    SUPPORTS_BOUNDED_FINDINGS = "SUPPORTS_BOUNDED_FINDINGS"
    CONTRADICTORY = "CONTRADICTORY"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True, slots=True)
class CapabilityEvaluationReceipt(SerializableContract):
    capability_checksum: str
    objective_checksum: str
    methodology_checksum: str
    implementation_specification_checksum: str
    execution_plan_checksum: str
    execution_outputs: tuple[NamedChecksum, ...]
    expected_output_contract_checksum: str
    evaluation_schema: str
    result_payload_checksum: str
    validity: EvaluationValidity
    limitations: tuple[str, ...]
    evaluated_at: str
    schema: str = field(default=CAPABILITY_EVALUATION_SCHEMA, init=False)
    evaluation_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        for name in (
            "capability_checksum", "objective_checksum", "methodology_checksum",
            "implementation_specification_checksum", "execution_plan_checksum",
            "expected_output_contract_checksum", "result_payload_checksum",
        ):
            require_sha256(getattr(self, name), name)
        if not self.execution_outputs or len(self.execution_outputs) > 50:
            raise GenericExperimentContractError("execution outputs must be bounded and non-empty")
        if len({item.name for item in self.execution_outputs}) != len(self.execution_outputs):
            raise GenericExperimentContractError("execution output identities must be unique")
        _schema(self.evaluation_schema, "evaluation_schema")
        _optional_texts(self.limitations, "limitations", 40)
        _timestamp(self.evaluated_at, "evaluated_at")
        object.__setattr__(self, "evaluation_checksum", _checksum_payload(self, "evaluation_checksum"))


@dataclass(frozen=True, slots=True)
class NormalizedExperimentResult(SerializableContract):
    process_outcome: ProcessOutcome
    evaluation_validity: EvaluationValidity
    scientific_evidence_status: ScientificEvidenceStatus
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        _optional_texts(self.limitations, "limitations", 40)
        if self.process_outcome is not ProcessOutcome.SUCCEEDED and self.evaluation_validity is EvaluationValidity.VALID:
            raise GenericExperimentContractError("a non-successful process cannot claim valid evaluation")
        if self.evaluation_validity is not EvaluationValidity.VALID and self.scientific_evidence_status is ScientificEvidenceStatus.SUPPORTS_BOUNDED_FINDINGS:
            raise GenericExperimentContractError("invalid evaluation cannot support bounded findings")
