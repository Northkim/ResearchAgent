"""Exact runtime boundary for unpublished Experiment Capabilities.

Implementations are injected as immutable, checksum-bound bindings.  This
module deliberately provides no registry, discovery, import, or installation
mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from backend.resource_references.experiment_requirement_contracts import (
    ExperimentResourceRequirementRef,
)

from .generic_experiment_contracts import (
    CAPABILITY_SCHEMA,
    CapabilityAssessment,
    CapabilityEvaluationReceipt,
    CapabilityOperation,
    ExperimentCapability,
    GenericMethodology,
    ImplementationSpecificationRef,
    PreparationRequirement,
    ResearchObjectiveRef,
    RuntimeRequirement,
)
from .generic_experiment_package import (
    ExperimentPackageManifest,
    PreparedExperimentPackageReceipt,
)
from .security import require_sha256
from .serialization import SerializableContract, canonical_hash, to_json_value

CAPABILITY_DESCRIPTOR_SCHEMA = "reagent.experiment-capability-implementation-descriptor/v0.1"
CAPABILITY_REQUIREMENTS_SCHEMA = "reagent.experiment-capability-requirements/v0.1"


class ExperimentCapabilityRuntimeError(ValueError):
    """The exact Capability execution boundary was violated."""


def _hash_without(value: SerializableContract, field_name: str) -> str:
    return canonical_hash({
        item.name: to_json_value(getattr(value, item.name))
        for item in fields(value) if item.name != field_name
    })


@dataclass(frozen=True, slots=True)
class CapabilityImplementationDescriptor(SerializableContract):
    """Future-Capsule-supplied exact implementation identity."""

    capability: ExperimentCapability
    interface_identity: str
    skill_identity_checksum: str
    capsule_identity_checksum: str
    implementation_entrypoint: str
    implementation_entrypoint_checksum: str
    fallback_equivalence_key: str | None = None
    classification: str = "REVIEWED_EXPERIMENT_CAPABILITY"
    schema: str = field(default=CAPABILITY_DESCRIPTOR_SCHEMA, init=False)
    descriptor_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        if self.interface_identity != CAPABILITY_SCHEMA:
            raise ExperimentCapabilityRuntimeError("CAPABILITY_INTERFACE_DRIFT")
        for value, name in (
            (self.skill_identity_checksum, "skill_identity_checksum"),
            (self.capsule_identity_checksum, "capsule_identity_checksum"),
            (self.implementation_entrypoint_checksum, "implementation_entrypoint_checksum"),
        ):
            require_sha256(value, name)
        if (
            self.skill_identity_checksum != self.capability.skill.checksum
            or self.capsule_identity_checksum != self.capability.capsule.checksum
            or self.implementation_entrypoint != self.capability.implementation_entrypoint
            or self.implementation_entrypoint_checksum
            != self.capability.implementation_entrypoint_checksum
        ):
            raise ExperimentCapabilityRuntimeError("CAPABILITY_IMPLEMENTATION_DRIFT")
        if self.fallback_equivalence_key is not None and (
            not self.fallback_equivalence_key.strip()
            or len(self.fallback_equivalence_key) > 200
        ):
            raise ExperimentCapabilityRuntimeError("fallback equivalence identity is invalid")
        if self.classification not in {
            "REVIEWED_EXPERIMENT_CAPABILITY", "REFERENCE_EXPERIMENT_CAPABILITY",
            "TEST_ONLY_EXPERIMENT_CAPABILITY",
        }:
            raise ExperimentCapabilityRuntimeError("Capability classification is invalid")
        object.__setattr__(self, "descriptor_checksum", _hash_without(self, "descriptor_checksum"))


@dataclass(frozen=True, slots=True)
class ValidatedOpaqueSpecification:
    """Capability-owned local data; Core may hash it but never interpret it."""

    reference: ImplementationSpecificationRef
    local_data: Any

    def __post_init__(self) -> None:
        if canonical_hash(to_json_value(self.local_data)) != self.reference.specification_checksum:
            raise ExperimentCapabilityRuntimeError("CAPABILITY_SPECIFICATION_DRIFT")


@dataclass(frozen=True, slots=True)
class CapabilityRequirementDeclaration(SerializableContract):
    capability_checksum: str
    specification_reference_checksum: str
    resource_requirements: tuple[ExperimentResourceRequirementRef, ...]
    preparation_requirements: tuple[PreparationRequirement, ...]
    runtime_requirement: RuntimeRequirement
    schema: str = field(default=CAPABILITY_REQUIREMENTS_SCHEMA, init=False)
    declaration_checksum: str = field(init=False)

    def __post_init__(self) -> None:
        require_sha256(self.capability_checksum, "capability_checksum")
        require_sha256(self.specification_reference_checksum, "specification_reference_checksum")
        if len(self.resource_requirements) > 50 or len(self.preparation_requirements) > 50:
            raise ExperimentCapabilityRuntimeError("Capability requirements exceed the bound")
        if any(item.capability_checksum != self.capability_checksum for item in self.resource_requirements):
            raise ExperimentCapabilityRuntimeError("Resource requirement Capability lineage mismatch")
        if any(item.capability_checksum != self.capability_checksum for item in self.preparation_requirements):
            raise ExperimentCapabilityRuntimeError("Preparation requirement Capability lineage mismatch")
        if len({item.requirement_checksum for item in self.resource_requirements}) != len(self.resource_requirements):
            raise ExperimentCapabilityRuntimeError("Resource requirements must be unique")
        if len({item.requirement_checksum for item in self.preparation_requirements}) != len(self.preparation_requirements):
            raise ExperimentCapabilityRuntimeError("Preparation requirements must be unique")
        object.__setattr__(self, "declaration_checksum", _hash_without(self, "declaration_checksum"))


@dataclass(frozen=True, slots=True)
class CapabilityPreparationContext:
    objective: ResearchObjectiveRef
    methodology: GenericMethodology
    specification: ValidatedOpaqueSpecification
    requirements: CapabilityRequirementDeclaration
    resource_identity_checksums: tuple[str, ...]
    prepared_at: str


@dataclass(frozen=True, slots=True)
class PreparedCapabilityCandidate:
    manifest: ExperimentPackageManifest
    receipt: PreparedExperimentPackageReceipt


@dataclass(frozen=True, slots=True)
class CapabilityEvaluationResult:
    receipt: CapabilityEvaluationReceipt
    scientific_evidence_status: str
    result_payload: Any


@runtime_checkable
class ExperimentCapabilityImplementation(Protocol):
    descriptor: CapabilityImplementationDescriptor

    def assess_support(
        self, objective: ResearchObjectiveRef, methodology: GenericMethodology,
    ) -> CapabilityAssessment: ...

    def validate_specification(
        self, methodology: GenericMethodology, specification: Any,
    ) -> ValidatedOpaqueSpecification: ...

    def declare_requirements(
        self, methodology: GenericMethodology, specification: ValidatedOpaqueSpecification,
    ) -> CapabilityRequirementDeclaration: ...

    def prepare(
        self, candidate_root: Path, context: CapabilityPreparationContext,
    ) -> PreparedCapabilityCandidate: ...

    def evaluate(self, context: Any) -> CapabilityEvaluationResult: ...

    def present(self, context: Any) -> Any: ...


@dataclass(frozen=True, slots=True)
class CapabilityBinding:
    descriptor: CapabilityImplementationDescriptor
    implementation: object

    def __post_init__(self) -> None:
        if getattr(self.implementation, "descriptor", None) != self.descriptor:
            raise ExperimentCapabilityRuntimeError("CAPABILITY_IMPLEMENTATION_DRIFT")
        method_by_operation = {
            CapabilityOperation.ASSESS_SUPPORT: "assess_support",
            CapabilityOperation.DECLARE_REQUIREMENTS: "declare_requirements",
            CapabilityOperation.PREPARE: "prepare",
            CapabilityOperation.EVALUATE: "evaluate",
            CapabilityOperation.PRESENT: "present",
        }
        for operation in self.descriptor.capability.operations:
            if not callable(getattr(self.implementation, method_by_operation[operation], None)):
                raise ExperimentCapabilityRuntimeError(
                    f"Capability does not implement declared operation {operation.value}"
                )
        if self.descriptor.capability.implementation_spec_schema is not None and not callable(
            getattr(self.implementation, "validate_specification", None)
        ):
            raise ExperimentCapabilityRuntimeError("Capability specification validator is unavailable")


class BoundedCapabilityResolver:
    """Immutable exact resolver over a compiler-supplied bounded sequence."""

    def __init__(self, bindings: tuple[CapabilityBinding, ...]) -> None:
        if not bindings or len(bindings) > 40:
            raise ExperimentCapabilityRuntimeError("Capability candidate set is empty or unbounded")
        checksums = tuple(item.descriptor.capability.capability_checksum for item in bindings)
        if len(set(checksums)) != len(checksums):
            raise ExperimentCapabilityRuntimeError("Capability candidates must be exact and unique")
        self._bindings = tuple(bindings)

    @property
    def bindings(self) -> tuple[CapabilityBinding, ...]:
        return self._bindings

    def resolve(self, capability: ExperimentCapability) -> CapabilityBinding:
        matches = tuple(
            item for item in self._bindings
            if item.descriptor.capability.capability_checksum == capability.capability_checksum
        )
        if len(matches) != 1 or matches[0].descriptor.capability != capability:
            raise ExperimentCapabilityRuntimeError("CAPABILITY_IMPLEMENTATION_DRIFT")
        return matches[0]

    @staticmethod
    def invoke(binding: CapabilityBinding, operation: CapabilityOperation, *args: Any) -> Any:
        if operation not in binding.descriptor.capability.operations:
            raise ExperimentCapabilityRuntimeError(
                f"CAPABILITY_OPERATION_NOT_DECLARED:{operation.value}"
            )
        method = {
            CapabilityOperation.ASSESS_SUPPORT: "assess_support",
            CapabilityOperation.DECLARE_REQUIREMENTS: "declare_requirements",
            CapabilityOperation.PREPARE: "prepare",
            CapabilityOperation.EVALUATE: "evaluate",
            CapabilityOperation.PRESENT: "present",
        }[operation]
        return getattr(binding.implementation, method)(*args)
