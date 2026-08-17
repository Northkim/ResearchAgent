"""Unpublished local contracts for forward Experiment preparation.

These contracts define identity and approval boundaries for the future
Experiment 0.5 path.  They do not publish a Workflow, admit execution, persist
state, or change the historical Experiment 0.4 runner.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping

from .security import reject_sensitive_content, require_relative_path, require_sha256
from .serialization import SerializableContract, canonical_hash, to_json_value

METHODOLOGY_SCHEMA = "reagent.experiment-methodology/v0.1"
DESIGN_APPROVAL_SCHEMA = "reagent.experiment-design-approval/v0.1"
PREPARED_PACKAGE_SCHEMA = "reagent.prepared-experiment-package/v0.1"
RUN_APPROVAL_SCHEMA = "reagent.experiment-run-approval/v0.1"
FORWARD_EXPERIMENT_DEFINITION_VERSION = "0.5.0"
FORWARD_EXPERIMENT_CAPSULE_VERSION = "0.8.0"
FORWARD_EXPERIMENT_ARTIFACT_TYPE = "experiment-record/v3"

_ARTIFACT_ID = re.compile(r"^artifact-[0-9a-f]{32}$")
_CAPSULE_ID = re.compile(r"^capsule-[0-9a-f]{32}$")
_SEMVER = re.compile(r"^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$")
_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{1,127}$")
_REMOTE_IDENTITY = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+){1,4}$")


class ExperimentPreparationContractError(ValueError):
    """A local Experiment-preparation contract is invalid."""


class PackageOrigin(str, Enum):
    REAGENT_PREPARED = "REAGENT_PREPARED"
    LOCAL_PROJECT = "LOCAL_PROJECT"
    EXTERNAL_EXACT_PACKAGE = "EXTERNAL_EXACT_PACKAGE"


class BuilderFamily(str, Enum):
    SKLEARN_TABULAR_CLASSIFICATION_V1 = "SKLEARN_TABULAR_CLASSIFICATION_V1"


class MethodologicalEffect(str, Enum):
    SCIENTIFIC_INTERPRETATION = "SCIENTIFIC_INTERPRETATION"
    REPRODUCIBILITY = "REPRODUCIBILITY"
    EVALUATION = "EVALUATION"
    RESOURCE_REQUIREMENTS = "RESOURCE_REQUIREMENTS"
    CLAIM_BOUNDARIES = "CLAIM_BOUNDARIES"


def _text(value: Any, label: str, *, maximum: int = 2_000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ExperimentPreparationContractError(f"{label} must be bounded non-empty text")
    return value


def _texts(value: Any, label: str, *, minimum: int = 0, maximum: int = 100) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not minimum <= len(value) <= maximum:
        raise ExperimentPreparationContractError(f"{label} must be a bounded array")
    result = tuple(_text(item, label) for item in value)
    if len(result) != len(set(result)):
        raise ExperimentPreparationContractError(f"{label} contains duplicates")
    return result


def _time(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ExperimentPreparationContractError(f"{label} is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ExperimentPreparationContractError(f"{label} is invalid") from error
    if parsed.tzinfo is None:
        raise ExperimentPreparationContractError(f"{label} requires a timezone")
    return value


def _exact(value: Mapping[str, Any], fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ExperimentPreparationContractError(f"{label} fields mismatch")
    return dict(value)


def _enum(enum: type[Enum], value: Any, label: str) -> Any:
    try:
        return enum(value)
    except (TypeError, ValueError) as error:
        raise ExperimentPreparationContractError(f"{label} is invalid") from error


def _verified_checksum(payload: Mapping[str, Any], checksum: str, label: str) -> None:
    try:
        require_sha256(checksum, label)
    except ValueError as error:
        raise ExperimentPreparationContractError(str(error)) from error
    if canonical_hash(payload) != checksum:
        raise ExperimentPreparationContractError(f"{label} mismatch")


@dataclass(frozen=True, slots=True)
class ExactArtifactReference(SerializableContract):
    artifact_id: str
    artifact_type: str
    sha256: str

    def __post_init__(self) -> None:
        if not _ARTIFACT_ID.fullmatch(self.artifact_id):
            raise ExperimentPreparationContractError("Artifact identity is invalid")
        _text(self.artifact_type, "Artifact type", maximum=160)
        try:
            require_sha256(self.sha256, "Artifact checksum")
        except ValueError as error:
            raise ExperimentPreparationContractError(str(error)) from error

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ExactArtifactReference":
        return cls(**_exact(value, {"artifact_id", "artifact_type", "sha256"}, "Artifact reference"))


@dataclass(frozen=True, slots=True)
class WorkflowCapsuleIdentity(SerializableContract):
    workflow_definition_id: str
    workflow_version: str
    workflow_checksum: str
    capsule_id: str
    capsule_version: str
    capsule_checksum: str

    def __post_init__(self) -> None:
        if not _STABLE_ID.fullmatch(self.workflow_definition_id):
            raise ExperimentPreparationContractError("Workflow Definition identity is invalid")
        if not _SEMVER.fullmatch(self.workflow_version) or not _SEMVER.fullmatch(self.capsule_version):
            raise ExperimentPreparationContractError("Workflow or Capsule version is invalid")
        if not _CAPSULE_ID.fullmatch(self.capsule_id):
            raise ExperimentPreparationContractError("Capsule identity is invalid")
        for label, value in (("Workflow checksum", self.workflow_checksum), ("Capsule checksum", self.capsule_checksum)):
            try:
                require_sha256(value, label)
            except ValueError as error:
                raise ExperimentPreparationContractError(str(error)) from error

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WorkflowCapsuleIdentity":
        return cls(**_exact(value, {
            "workflow_definition_id", "workflow_version", "workflow_checksum",
            "capsule_id", "capsule_version", "capsule_checksum",
        }, "Workflow/Capsule identity"))


@dataclass(frozen=True, slots=True)
class HarnessIdentity(SerializableContract):
    harness: str
    version: str
    session_id: str | None

    def __post_init__(self) -> None:
        _text(self.harness, "Harness identity", maximum=80)
        _text(self.version, "Harness version", maximum=80)
        if self.session_id is not None:
            _text(self.session_id, "Harness session", maximum=160)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "HarnessIdentity":
        return cls(**_exact(value, {"harness", "version", "session_id"}, "Harness identity"))


@dataclass(frozen=True, slots=True)
class RuntimeIdentity(SerializableContract):
    runtime: str
    runtime_version: str
    environment_checksum: str

    def __post_init__(self) -> None:
        _text(self.runtime, "Runtime", maximum=40)
        _text(self.runtime_version, "Runtime version", maximum=80)
        try:
            require_sha256(self.environment_checksum, "Runtime environment checksum")
        except ValueError as error:
            raise ExperimentPreparationContractError(str(error)) from error

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RuntimeIdentity":
        return cls(**_exact(value, {"runtime", "runtime_version", "environment_checksum"}, "Runtime identity"))


@dataclass(frozen=True, slots=True)
class ComputeRuntimeBounds(SerializableContract):
    expected_wall_seconds: int
    maximum_wall_seconds: int
    maximum_cpu_count: int
    maximum_output_bytes: int

    def __post_init__(self) -> None:
        values = (self.expected_wall_seconds, self.maximum_wall_seconds, self.maximum_cpu_count, self.maximum_output_bytes)
        if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in values):
            raise ExperimentPreparationContractError("Compute/runtime bounds must be positive integers")
        if self.expected_wall_seconds > self.maximum_wall_seconds:
            raise ExperimentPreparationContractError("Expected runtime exceeds the maximum runtime")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ComputeRuntimeBounds":
        return cls(**_exact(value, {
            "expected_wall_seconds", "maximum_wall_seconds", "maximum_cpu_count", "maximum_output_bytes",
        }, "Compute/runtime bounds"))


@dataclass(frozen=True, slots=True)
class ImplementationDecision(SerializableContract):
    decision: str
    rationale: str
    scientific_meaning_unchanged: bool

    def __post_init__(self) -> None:
        _text(self.decision, "Implementation decision")
        _text(self.rationale, "Implementation rationale")
        if self.scientific_meaning_unchanged is not True:
            raise ExperimentPreparationContractError("Implementation decisions may not change scientific meaning")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ImplementationDecision":
        return cls(**_exact(value, {"decision", "rationale", "scientific_meaning_unchanged"}, "Implementation decision"))


@dataclass(frozen=True, slots=True)
class UnresolvedMethodologicalDecision(SerializableContract):
    question: str
    material_effects: tuple[MethodologicalEffect, ...]

    def __post_init__(self) -> None:
        _text(self.question, "Unresolved methodological question")
        effects = tuple(_enum(MethodologicalEffect, item, "Methodological effect") for item in self.material_effects)
        if not effects or len(effects) != len(set(effects)):
            raise ExperimentPreparationContractError("Unresolved decision requires unique material effects")
        object.__setattr__(self, "material_effects", effects)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "UnresolvedMethodologicalDecision":
        item = _exact(value, {"question", "material_effects"}, "Unresolved methodological decision")
        return cls(item["question"], tuple(item["material_effects"]))


@dataclass(frozen=True, slots=True)
class ExperimentMethodology(SerializableContract):
    schema: str
    selected_idea: ExactArtifactReference
    frozen_scientific_requirements: tuple[str, ...]
    implementation_decisions: tuple[ImplementationDecision, ...]
    unresolved_methodological_decisions: tuple[UnresolvedMethodologicalDecision, ...]
    dataset: str
    experiment_conditions: tuple[str, ...]
    evaluation_protocol: tuple[str, ...]
    metrics: tuple[str, ...]
    robustness_analysis: tuple[str, ...]
    leakage_controls: tuple[str, ...]
    seeds: tuple[int, ...]
    repetitions: int
    compute_runtime_bounds: ComputeRuntimeBounds
    network_policy: str
    assumptions: tuple[str, ...]
    claim_boundaries: tuple[str, ...]
    expected_scientific_outputs: tuple[str, ...]
    methodology_checksum: str

    def __post_init__(self) -> None:
        if self.schema != METHODOLOGY_SCHEMA or self.selected_idea.artifact_type != "selected-research-idea/v1":
            raise ExperimentPreparationContractError("Methodology identity is invalid")
        for field, minimum in (("frozen_scientific_requirements", 1), ("experiment_conditions", 1), ("evaluation_protocol", 1), ("metrics", 1), ("claim_boundaries", 1), ("expected_scientific_outputs", 1)):
            object.__setattr__(self, field, _texts(getattr(self, field), field, minimum=minimum))
        for field in ("robustness_analysis", "leakage_controls", "assumptions"):
            object.__setattr__(self, field, _texts(getattr(self, field), field))
        object.__setattr__(self, "implementation_decisions", tuple(self.implementation_decisions))
        object.__setattr__(self, "unresolved_methodological_decisions", tuple(self.unresolved_methodological_decisions))
        _text(self.dataset, "Dataset")
        if not isinstance(self.repetitions, int) or isinstance(self.repetitions, bool) or self.repetitions < 1:
            raise ExperimentPreparationContractError("Repetitions must be positive")
        seeds = tuple(self.seeds)
        if not seeds or len(seeds) > 1_000 or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
            raise ExperimentPreparationContractError("Seeds must be a bounded integer array")
        object.__setattr__(self, "seeds", seeds)
        if self.network_policy != "DISABLED":
            raise ExperimentPreparationContractError("Prepared Experiment network policy must be DISABLED")
        payload = self.to_dict()
        checksum = payload.pop("methodology_checksum")
        _verified_checksum(payload, checksum, "Methodology checksum")

    @classmethod
    def create(cls, **values: Any) -> "ExperimentMethodology":
        values = {"schema": METHODOLOGY_SCHEMA, **values}
        payload = to_json_value(values)
        return cls(**values, methodology_checksum=canonical_hash(payload))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ExperimentMethodology":
        fields = {field.name for field in cls.__dataclass_fields__.values()}
        item = _exact(value, fields, "Experiment methodology")
        return cls(
            **{key: item[key] for key in fields - {"selected_idea", "implementation_decisions", "unresolved_methodological_decisions", "compute_runtime_bounds"}},
            selected_idea=ExactArtifactReference.from_mapping(item["selected_idea"]),
            implementation_decisions=tuple(ImplementationDecision.from_mapping(entry) for entry in item["implementation_decisions"]),
            unresolved_methodological_decisions=tuple(UnresolvedMethodologicalDecision.from_mapping(entry) for entry in item["unresolved_methodological_decisions"]),
            compute_runtime_bounds=ComputeRuntimeBounds.from_mapping(item["compute_runtime_bounds"]),
        )


@dataclass(frozen=True, slots=True)
class DesignApproval(SerializableContract):
    schema: str
    decision: str
    authorization_scope: str
    methodology_checksum: str
    selected_idea: ExactArtifactReference
    scientific_requirements_checksum: str
    evaluation_protocol_checksum: str
    claim_boundaries_checksum: str
    approved_at: str
    approval_checksum: str

    def __post_init__(self) -> None:
        if (self.schema, self.decision, self.authorization_scope) != (DESIGN_APPROVAL_SCHEMA, "APPROVED", "IMPLEMENTATION_PREPARATION_ONLY"):
            raise ExperimentPreparationContractError("Design approval semantics are invalid")
        _time(self.approved_at, "Design approval time")
        payload = self.to_dict()
        checksum = payload.pop("approval_checksum")
        _verified_checksum(payload, checksum, "Design approval checksum")
        for field in ("methodology_checksum", "scientific_requirements_checksum", "evaluation_protocol_checksum", "claim_boundaries_checksum"):
            try:
                require_sha256(getattr(self, field), field)
            except ValueError as error:
                raise ExperimentPreparationContractError(str(error)) from error

    @classmethod
    def create(cls, methodology: ExperimentMethodology, *, approved_at: str) -> "DesignApproval":
        payload = {
            "schema": DESIGN_APPROVAL_SCHEMA, "decision": "APPROVED",
            "authorization_scope": "IMPLEMENTATION_PREPARATION_ONLY",
            "methodology_checksum": methodology.methodology_checksum,
            "selected_idea": methodology.selected_idea,
            "scientific_requirements_checksum": canonical_hash(methodology.frozen_scientific_requirements),
            "evaluation_protocol_checksum": canonical_hash(methodology.evaluation_protocol),
            "claim_boundaries_checksum": canonical_hash(methodology.claim_boundaries),
            "approved_at": approved_at,
        }
        return cls(**payload, approval_checksum=canonical_hash(payload))

    def validate_methodology(self, methodology: ExperimentMethodology) -> None:
        expected = DesignApproval.create(methodology, approved_at=self.approved_at)
        if expected != self:
            raise ExperimentPreparationContractError("Methodology drift invalidates design approval")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "DesignApproval":
        fields = {field.name for field in cls.__dataclass_fields__.values()}
        item = _exact(value, fields, "Design approval")
        return cls(**{key: item[key] for key in fields - {"selected_idea"}}, selected_idea=ExactArtifactReference.from_mapping(item["selected_idea"]))


@dataclass(frozen=True, slots=True)
class BuilderIdentity(SerializableContract):
    family: BuilderFamily
    version: str
    template_checksum: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "family", _enum(BuilderFamily, self.family, "Builder family"))
        _text(self.version, "Builder version", maximum=80)
        try:
            require_sha256(self.template_checksum, "Builder template checksum")
        except ValueError as error:
            raise ExperimentPreparationContractError(str(error)) from error

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "BuilderIdentity":
        return cls(**_exact(value, {"family", "version", "template_checksum"}, "Builder identity"))


@dataclass(frozen=True, slots=True)
class SanitizedGitProvenance(SerializableContract):
    dirty: bool
    head_revision: str | None
    remote_identity: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.dirty, bool):
            raise ExperimentPreparationContractError("Git dirty state is invalid")
        if self.head_revision is not None and not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", self.head_revision):
            raise ExperimentPreparationContractError("Git HEAD is invalid")
        if self.remote_identity is not None and not _REMOTE_IDENTITY.fullmatch(self.remote_identity):
            raise ExperimentPreparationContractError("Git remote identity must be credential-free")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SanitizedGitProvenance":
        return cls(**_exact(value, {"dirty", "head_revision", "remote_identity"}, "Git provenance"))


@dataclass(frozen=True, slots=True)
class PreparedPackageReceipt(SerializableContract):
    schema: str
    origin_type: PackageOrigin
    selected_idea: ExactArtifactReference
    workflow_capsule: WorkflowCapsuleIdentity
    harness: HarnessIdentity | None
    builder: BuilderIdentity | None
    git: SanitizedGitProvenance | None
    package_tree_checksum: str
    manifest_checksum: str
    entrypoint_checksum: str
    dependency_checksum: str
    runtime: RuntimeIdentity
    validation_result: str
    prepared_at: str
    receipt_checksum: str

    def __post_init__(self) -> None:
        if self.schema != PREPARED_PACKAGE_SCHEMA:
            raise ExperimentPreparationContractError("Prepared-package receipt schema is invalid")
        object.__setattr__(self, "origin_type", _enum(PackageOrigin, self.origin_type, "Package origin"))
        if self.selected_idea.artifact_type != "selected-research-idea/v1" or self.validation_result != "VALIDATED":
            raise ExperimentPreparationContractError("Prepared-package receipt identity is invalid")
        if (self.origin_type is PackageOrigin.REAGENT_PREPARED) != (self.builder is not None):
            raise ExperimentPreparationContractError("Only ReAgent-prepared packages require Builder identity")
        if self.origin_type is PackageOrigin.REAGENT_PREPARED and self.git is not None:
            raise ExperimentPreparationContractError("ReAgent-prepared packages do not require Git provenance")
        for field in ("package_tree_checksum", "manifest_checksum", "entrypoint_checksum", "dependency_checksum"):
            try:
                require_sha256(getattr(self, field), field)
            except ValueError as error:
                raise ExperimentPreparationContractError(str(error)) from error
        _time(self.prepared_at, "Preparation time")
        payload = self.to_dict()
        checksum = payload.pop("receipt_checksum")
        try:
            serialized = str(to_json_value(payload)).encode("utf-8")
            reject_sensitive_content(serialized, path="prepared-package-receipt")
        except ValueError as error:
            raise ExperimentPreparationContractError(str(error)) from error
        if b"/home/" in serialized or re.search(rb"https?://[^\s/@]+:[^\s/@]+@", serialized):
            raise ExperimentPreparationContractError("Prepared-package receipt contains private local or credential data")
        _verified_checksum(payload, checksum, "Prepared-package receipt checksum")

    @classmethod
    def create(cls, **values: Any) -> "PreparedPackageReceipt":
        values = {"schema": PREPARED_PACKAGE_SCHEMA, "validation_result": "VALIDATED", **values}
        return cls(**values, receipt_checksum=canonical_hash(to_json_value(values)))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PreparedPackageReceipt":
        fields = {field.name for field in cls.__dataclass_fields__.values()}
        item = _exact(value, fields, "Prepared-package receipt")
        return cls(
            **{key: item[key] for key in fields - {"selected_idea", "workflow_capsule", "harness", "builder", "git", "runtime"}},
            selected_idea=ExactArtifactReference.from_mapping(item["selected_idea"]),
            workflow_capsule=WorkflowCapsuleIdentity.from_mapping(item["workflow_capsule"]),
            harness=None if item["harness"] is None else HarnessIdentity.from_mapping(item["harness"]),
            builder=None if item["builder"] is None else BuilderIdentity.from_mapping(item["builder"]),
            git=None if item["git"] is None else SanitizedGitProvenance.from_mapping(item["git"]),
            runtime=RuntimeIdentity.from_mapping(item["runtime"]),
        )


@dataclass(frozen=True, slots=True)
class RunApprovalFoundation(SerializableContract):
    schema: str
    decision: str
    scope: str
    prepared_package_receipt_checksum: str
    execution_plan_checksum: str
    command: tuple[str, ...]
    runtime: RuntimeIdentity
    metrics: tuple[str, ...]
    run_seed_scope: tuple[int, ...]
    execution_limits: ComputeRuntimeBounds
    network_policy: str
    expected_outputs: tuple[str, ...]
    approved_at: str
    approval_checksum: str

    def __post_init__(self) -> None:
        if (self.schema, self.decision, self.scope, self.network_policy) != (RUN_APPROVAL_SCHEMA, "APPROVED", "ONE_EXECUTION", "DISABLED"):
            raise ExperimentPreparationContractError("Run approval semantics are invalid")
        try:
            require_sha256(self.prepared_package_receipt_checksum, "Prepared-package receipt checksum")
            require_sha256(self.execution_plan_checksum, "Execution-plan checksum")
        except ValueError as error:
            raise ExperimentPreparationContractError(str(error)) from error
        command = tuple(_text(item, "Command argument", maximum=1_000) for item in self.command)
        if not command:
            raise ExperimentPreparationContractError("Run approval requires an exact command")
        object.__setattr__(self, "command", command)
        object.__setattr__(self, "metrics", _texts(self.metrics, "Run metrics", minimum=1))
        object.__setattr__(self, "expected_outputs", _texts(self.expected_outputs, "Expected outputs", minimum=1))
        seeds = tuple(self.run_seed_scope)
        if not seeds or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
            raise ExperimentPreparationContractError("Run approval seed scope is invalid")
        object.__setattr__(self, "run_seed_scope", seeds)
        _time(self.approved_at, "Run approval time")
        payload = self.to_dict()
        checksum = payload.pop("approval_checksum")
        _verified_checksum(payload, checksum, "Run approval checksum")

    @classmethod
    def create(cls, **values: Any) -> "RunApprovalFoundation":
        values = {"schema": RUN_APPROVAL_SCHEMA, "decision": "APPROVED", "scope": "ONE_EXECUTION", "network_policy": "DISABLED", **values}
        return cls(**values, approval_checksum=canonical_hash(to_json_value(values)))

    def validate_execution_plan(self, plan: Mapping[str, Any], receipt: PreparedPackageReceipt) -> None:
        if canonical_hash(plan) != self.execution_plan_checksum or receipt.receipt_checksum != self.prepared_package_receipt_checksum:
            raise ExperimentPreparationContractError("Package or execution-plan drift invalidates run approval")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RunApprovalFoundation":
        fields = {field.name for field in cls.__dataclass_fields__.values()}
        item = _exact(value, fields, "Run approval")
        return cls(
            **{key: item[key] for key in fields - {"runtime", "execution_limits"}},
            runtime=RuntimeIdentity.from_mapping(item["runtime"]),
            execution_limits=ComputeRuntimeBounds.from_mapping(item["execution_limits"]),
        )
