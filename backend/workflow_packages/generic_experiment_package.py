"""Provider-, runtime-, and research-domain-neutral Experiment package v0.2."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from enum import Enum

from .generic_experiment_contracts import (
    ContractRef,
    ExactIdentity,
    ImplementationSpecificationRef,
    NamedChecksum,
    ResearchObjectiveRef,
    RuntimeRequirement,
)
from .security import require_relative_path, require_sha256
from .serialization import SerializableContract, canonical_hash, to_json_value

EXPERIMENT_PACKAGE_SCHEMA = "reagent.experiment-package/v0.2"
PREPARED_PACKAGE_SCHEMA = "reagent.prepared-experiment-package/v0.2"
VALIDATED_PACKAGE_SCHEMA = "reagent.validated-experiment-package/v0.2"


class GenericExperimentPackageError(ValueError):
    pass


class PackageOrigin(str, Enum):
    REAGENT_PREPARED = "REAGENT_PREPARED"
    LOCAL_PROJECT = "LOCAL_PROJECT"
    EXTERNAL_EXACT_PACKAGE = "EXTERNAL_EXACT_PACKAGE"


def _hash_without(value: SerializableContract, field_name: str) -> str:
    payload = {
        item.name: to_json_value(getattr(value, item.name))
        for item in fields(value) if item.name != field_name
    }
    return canonical_hash(payload)


@dataclass(frozen=True, slots=True)
class LaunchTarget(SerializableContract):
    relative_path: str
    checksum: str
    launch_contract: ContractRef

    def __post_init__(self) -> None:
        require_relative_path(self.relative_path, "launch target")
        require_sha256(self.checksum, "launch target checksum")


@dataclass(frozen=True, slots=True)
class DependencyDeclaration(SerializableContract):
    declaration_type: str
    relative_path: str
    checksum: str

    def __post_init__(self) -> None:
        if not self.declaration_type or len(self.declaration_type) > 120:
            raise GenericExperimentPackageError("dependency declaration type is invalid")
        require_relative_path(self.relative_path, "dependency declaration")
        require_sha256(self.checksum, "dependency declaration checksum")


@dataclass(frozen=True, slots=True)
class ExperimentPackageManifest(SerializableContract):
    capability_checksum: str
    implementation_specification: ImplementationSpecificationRef
    launch_target: LaunchTarget
    dependency_declarations: tuple[DependencyDeclaration, ...]
    configuration_identities: tuple[NamedChecksum, ...]
    input_identities: tuple[NamedChecksum, ...]
    resource_identity_checksums: tuple[str, ...]
    runtime_requirement_checksum: str
    expected_outputs: tuple[NamedChecksum, ...]
    schema: str = field(default=EXPERIMENT_PACKAGE_SCHEMA, init=False)
    manifest_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        for name in ("capability_checksum", "runtime_requirement_checksum"):
            require_sha256(getattr(self, name), name)
        if self.implementation_specification.capability_checksum != self.capability_checksum:
            raise GenericExperimentPackageError("implementation specification Capability mismatch")
        if len(self.dependency_declarations) > 20:
            raise GenericExperimentPackageError("dependency declarations exceed the bound")
        paths = (self.launch_target.relative_path,) + tuple(item.relative_path for item in self.dependency_declarations)
        if len(paths) != len({path.casefold() for path in paths}):
            raise GenericExperimentPackageError("package paths collide")
        for checksum in self.resource_identity_checksums:
            require_sha256(checksum, "resource identity checksum")
        if not self.expected_outputs or len(self.expected_outputs) > 50:
            raise GenericExperimentPackageError("expected outputs must be bounded and non-empty")
        for identities in (self.configuration_identities, self.input_identities, self.expected_outputs):
            if len({item.name for item in identities}) != len(identities):
                raise GenericExperimentPackageError("named package identities must be unique")
        object.__setattr__(self, "manifest_checksum", _hash_without(self, "manifest_checksum"))


@dataclass(frozen=True, slots=True)
class PreparedExperimentPackageReceipt(SerializableContract):
    origin: PackageOrigin
    research_objective: ResearchObjectiveRef
    methodology_checksum: str
    capability: ExactIdentity
    implementation_specification: ImplementationSpecificationRef
    package_tree_checksum: str
    manifest_checksum: str
    launch_target_checksum: str
    dependency_declaration_checksums: tuple[str, ...]
    runtime_requirement: RuntimeRequirement
    resource_identity_checksums: tuple[str, ...]
    workflow: ExactIdentity
    capsule: ExactIdentity
    harness: ExactIdentity | None
    origin_provenance: ContractRef | None
    prepared_at: str
    schema: str = field(default=PREPARED_PACKAGE_SCHEMA, init=False)
    receipt_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        for name in (
            "methodology_checksum", "package_tree_checksum", "manifest_checksum",
            "launch_target_checksum",
        ):
            require_sha256(getattr(self, name), name)
        for checksum in (*self.dependency_declaration_checksums, *self.resource_identity_checksums):
            require_sha256(checksum, "package lineage checksum")
        if self.capability.checksum != self.implementation_specification.capability_checksum:
            raise GenericExperimentPackageError("Capability identity does not match specification")
        if self.origin is not PackageOrigin.REAGENT_PREPARED and self.origin_provenance is None:
            raise GenericExperimentPackageError("local or external package origin requires exact provenance")
        if not self.prepared_at.endswith("Z"):
            raise GenericExperimentPackageError("prepared_at must be canonical UTC text")
        object.__setattr__(self, "receipt_checksum", _hash_without(self, "receipt_checksum"))


@dataclass(frozen=True, slots=True)
class PackageSafetyEvidence(SerializableContract):
    traversal_rejected: bool
    symlinks_rejected: bool
    hardlinks_rejected: bool
    special_files_rejected: bool
    case_collisions_rejected: bool
    manifest_agreement_verified: bool
    checksums_recomputed: bool

    def __post_init__(self) -> None:
        if not all(to_json_value(self).values()):
            raise GenericExperimentPackageError("every package safety invariant must be verified")


@dataclass(frozen=True, slots=True)
class ValidatedExperimentPackage(SerializableContract):
    manifest: ExperimentPackageManifest
    prepared_receipt: PreparedExperimentPackageReceipt
    package_tree_checksum: str
    runtime_requirement_checksum: str
    resource_identity_checksums: tuple[str, ...]
    safety: PackageSafetyEvidence
    validation_status: str
    validated_at: str
    schema: str = field(default=VALIDATED_PACKAGE_SCHEMA, init=False)
    validated_package_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        if self.validation_status != "VALIDATED":
            raise GenericExperimentPackageError("only independently validated packages may be promoted")
        require_sha256(self.package_tree_checksum, "package_tree_checksum")
        require_sha256(self.runtime_requirement_checksum, "runtime_requirement_checksum")
        if (
            self.manifest.manifest_checksum != self.prepared_receipt.manifest_checksum
            or self.package_tree_checksum != self.prepared_receipt.package_tree_checksum
            or self.manifest.launch_target.checksum != self.prepared_receipt.launch_target_checksum
            or tuple(item.checksum for item in self.manifest.dependency_declarations)
            != self.prepared_receipt.dependency_declaration_checksums
            or self.runtime_requirement_checksum != self.manifest.runtime_requirement_checksum
            or self.runtime_requirement_checksum != self.prepared_receipt.runtime_requirement.requirement_checksum
            or self.resource_identity_checksums != self.manifest.resource_identity_checksums
            or self.resource_identity_checksums != self.prepared_receipt.resource_identity_checksums
            or self.prepared_receipt.research_objective.source_artifact_checksum
            not in {item.checksum for item in self.manifest.input_identities}
        ):
            raise GenericExperimentPackageError("prepared, manifest, Resource, or runtime lineage mismatch")
        if not self.validated_at.endswith("Z"):
            raise GenericExperimentPackageError("validated_at must be canonical UTC text")
        object.__setattr__(self, "validated_package_checksum", _hash_without(self, "validated_package_checksum"))
