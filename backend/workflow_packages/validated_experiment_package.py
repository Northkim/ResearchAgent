"""Shared validated-package convergence contract; not an execution engine."""

from __future__ import annotations

from dataclasses import dataclass

from .experiment_preparation_contracts import (
    ExactArtifactReference,
    ExperimentPreparationContractError,
    HarnessIdentity,
    PreparedPackageReceipt,
    RuntimeIdentity,
    WorkflowCapsuleIdentity,
    _time,
)
from .security import require_relative_path, require_sha256
from .serialization import SerializableContract

VALIDATED_PACKAGE_SCHEMA = "reagent.validated-experiment-package/v0.1"


@dataclass(frozen=True, slots=True)
class NamedChecksum(SerializableContract):
    name: str
    sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 128:
            raise ExperimentPreparationContractError("Named identity is invalid")
        try:
            require_sha256(self.sha256, f"{self.name} checksum")
        except ValueError as error:
            raise ExperimentPreparationContractError(str(error)) from error


@dataclass(frozen=True, slots=True)
class PackageSafetyEvidence(SerializableContract):
    relative_paths_verified: bool
    traversal_rejected: bool
    symlinks_rejected: bool
    hardlinks_rejected: bool
    special_files_rejected: bool
    case_collisions_rejected: bool
    manifest_package_agreement: bool
    runtime_supported: bool
    dependencies_available_locally: bool
    package_identity_reproduced: bool

    def __post_init__(self) -> None:
        if any(getattr(self, field) is not True for field in self.__dataclass_fields__):
            raise ExperimentPreparationContractError("Validated package requires every safety invariant")


@dataclass(frozen=True, slots=True)
class ValidatedExperimentPackage(SerializableContract):
    schema: str
    package_tree_checksum: str
    manifest_checksum: str
    entrypoint_relative_path: str
    entrypoint_checksum: str
    dependency_relative_path: str
    dependency_checksum: str
    runtime: RuntimeIdentity
    configuration_identities: tuple[NamedChecksum, ...]
    input_identities: tuple[NamedChecksum, ...]
    prepared_package_receipt: PreparedPackageReceipt
    prepared_package_receipt_checksum: str
    selected_idea: ExactArtifactReference
    workflow_capsule: WorkflowCapsuleIdentity
    harness: HarnessIdentity | None
    safety: PackageSafetyEvidence
    validation_status: str
    validated_at: str

    def __post_init__(self) -> None:
        if self.schema != VALIDATED_PACKAGE_SCHEMA or self.validation_status != "VALIDATED":
            raise ExperimentPreparationContractError("Validated package identity is invalid")
        try:
            require_relative_path(self.entrypoint_relative_path, "Experiment entrypoint")
            require_relative_path(self.dependency_relative_path, "Experiment dependency file")
            for field in ("package_tree_checksum", "manifest_checksum", "entrypoint_checksum", "dependency_checksum", "prepared_package_receipt_checksum"):
                require_sha256(getattr(self, field), field)
        except ValueError as error:
            raise ExperimentPreparationContractError(str(error)) from error
        object.__setattr__(self, "configuration_identities", tuple(self.configuration_identities))
        object.__setattr__(self, "input_identities", tuple(self.input_identities))
        names = [item.name.casefold() for item in (*self.configuration_identities, *self.input_identities)]
        if len(names) != len(set(names)):
            raise ExperimentPreparationContractError("Package configuration/input identities collide")
        if not any(item.name == "selected_research_idea" and item.sha256 == self.selected_idea.sha256 for item in self.input_identities):
            raise ExperimentPreparationContractError("Validated package must bind the selected Idea bytes")
        receipt = self.prepared_package_receipt
        linked = (
            self.prepared_package_receipt_checksum == receipt.receipt_checksum
            and self.package_tree_checksum == receipt.package_tree_checksum
            and self.manifest_checksum == receipt.manifest_checksum
            and self.entrypoint_checksum == receipt.entrypoint_checksum
            and self.dependency_checksum == receipt.dependency_checksum
            and self.runtime == receipt.runtime
            and self.selected_idea == receipt.selected_idea
            and self.workflow_capsule == receipt.workflow_capsule
            and self.harness == receipt.harness
        )
        if not linked:
            raise ExperimentPreparationContractError("Validated package does not match its prepared-package receipt")
        _time(self.validated_at, "Package validation time")
