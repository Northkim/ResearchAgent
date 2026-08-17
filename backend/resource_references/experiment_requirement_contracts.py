"""Forward Experiment bridge to the existing exact Resource subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from enum import Enum

from backend.workflow_packages.security import require_sha256
from backend.workflow_packages.serialization import SerializableContract, canonical_hash, to_json_value

from .contracts import (
    ProjectResourceReference,
    ResourceBindingState,
    ResourceKind,
    ResourceProvider,
    WorkflowResourceBinding,
    WorkflowResourceRequirement,
)

RESOURCE_REQUIREMENT_REF_SCHEMA = "reagent.experiment-resource-requirement-ref/v0.1"
RESOURCE_READINESS_SCHEMA = "reagent.experiment-resource-readiness/v0.1"


class ExperimentResourceContractError(ValueError):
    pass


class ResourceReadiness(str, Enum):
    UNBOUND = "UNBOUND"
    BOUND_METADATA_ONLY = "BOUND_METADATA_ONLY"
    RESOLVED_VERIFIED = "RESOLVED_VERIFIED"
    UNAVAILABLE = "UNAVAILABLE"
    DRIFTED = "DRIFTED"


def _hash_without(value: SerializableContract, field_name: str) -> str:
    payload = {
        item.name: to_json_value(getattr(value, item.name))
        for item in fields(value) if item.name != field_name
    }
    return canonical_hash(payload)


@dataclass(frozen=True, slots=True)
class ExperimentResourceRequirementRef(SerializableContract):
    capability_checksum: str
    workflow_definition_id: str
    workflow_version: str
    requirement_key: str
    resource_kind: str
    cardinality_min: int
    cardinality_max: int
    required: bool
    allowed_providers: tuple[str, ...]
    usage_description: str
    schema: str = field(default=RESOURCE_REQUIREMENT_REF_SCHEMA, init=False)
    requirement_checksum: str = field(init=False)

    @classmethod
    def from_workflow_requirement(
        cls, capability_checksum: str, requirement: WorkflowResourceRequirement
    ) -> "ExperimentResourceRequirementRef":
        return cls(
            capability_checksum, requirement.workflow_definition_id,
            requirement.workflow_version, requirement.requirement_key,
            requirement.resource_kind.value, requirement.cardinality_min,
            requirement.cardinality_max, requirement.required,
            tuple(item.value for item in requirement.allowed_providers),
            requirement.usage_description,
        )

    def __post_init__(self) -> None:
        require_sha256(self.capability_checksum, "capability_checksum")
        try:
            ResourceKind(self.resource_kind)
            tuple(ResourceProvider(value) for value in self.allowed_providers)
        except ValueError as error:
            raise ExperimentResourceContractError("Resource requirement uses unknown existing taxonomy") from error
        if (
            not self.allowed_providers
            or len(set(self.allowed_providers)) != len(self.allowed_providers)
            or self.cardinality_min < 0
            or self.cardinality_max < self.cardinality_min
            or self.cardinality_max > 20
        ):
            raise ExperimentResourceContractError("Resource requirement projection is invalid")
        object.__setattr__(self, "requirement_checksum", _hash_without(self, "requirement_checksum"))


@dataclass(frozen=True, slots=True)
class ExperimentResourceReadinessEvidence(SerializableContract):
    requirement_checksum: str
    readiness: ResourceReadiness
    binding_id: str | None
    resource_id: str | None
    expected_content_checksum: str | None
    verified_content_checksum: str | None
    schema: str = field(default=RESOURCE_READINESS_SCHEMA, init=False)
    readiness_checksum: str = field(init=False)

    @classmethod
    def from_existing_state(
        cls,
        requirement: ExperimentResourceRequirementRef,
        *,
        binding: WorkflowResourceBinding | None = None,
        resource: ProjectResourceReference | None = None,
        local_resolution_status: str | None = None,
        verified_content_checksum: str | None = None,
    ) -> "ExperimentResourceReadinessEvidence":
        if binding is None:
            return cls(requirement.requirement_checksum, ResourceReadiness.UNBOUND, None, None, None, None)
        if resource is None or binding.state is not ResourceBindingState.ACTIVE:
            raise ExperimentResourceContractError("active exact binding and ResourceReference must agree")
        if (
            binding.requirement_key != requirement.requirement_key
            or binding.workflow_definition_id != requirement.workflow_definition_id
            or binding.workflow_version != requirement.workflow_version
            or resource.resource_id != binding.resource_id
            or resource.resource_kind.value != requirement.resource_kind
            or resource.provider.value not in requirement.allowed_providers
            or resource.expected_content_checksum != binding.expected_content_checksum
        ):
            raise ExperimentResourceContractError("Resource binding lineage is inconsistent")
        statuses = {
            None: ResourceReadiness.BOUND_METADATA_ONLY,
            "UNRESOLVED": ResourceReadiness.BOUND_METADATA_ONLY,
            "UNAVAILABLE": ResourceReadiness.UNAVAILABLE,
            "DRIFTED": ResourceReadiness.DRIFTED,
            "RESOLVED_VERIFIED": ResourceReadiness.RESOLVED_VERIFIED,
        }
        if local_resolution_status not in statuses:
            raise ExperimentResourceContractError("local Resource readiness status is unsupported")
        status = statuses[local_resolution_status]
        if status is ResourceReadiness.RESOLVED_VERIFIED:
            require_sha256(verified_content_checksum, "verified_content_checksum")
            if verified_content_checksum != binding.expected_content_checksum:
                raise ExperimentResourceContractError("verified Resource bytes do not match the exact binding")
        elif verified_content_checksum is not None:
            raise ExperimentResourceContractError("unverified Resource state cannot carry verified bytes")
        return cls(
            requirement.requirement_checksum, status, binding.binding_id,
            binding.resource_id, binding.expected_content_checksum,
            verified_content_checksum,
        )

    def __post_init__(self) -> None:
        require_sha256(self.requirement_checksum, "requirement_checksum")
        if self.readiness is ResourceReadiness.UNBOUND:
            if any((self.binding_id, self.resource_id, self.expected_content_checksum, self.verified_content_checksum)):
                raise ExperimentResourceContractError("unbound Resource evidence cannot carry identities")
        else:
            if not self.binding_id or not self.resource_id:
                raise ExperimentResourceContractError("bound Resource evidence requires exact identities")
            require_sha256(self.expected_content_checksum, "expected_content_checksum")
        object.__setattr__(self, "readiness_checksum", _hash_without(self, "readiness_checksum"))
