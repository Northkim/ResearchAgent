"""DTOs for Workflow catalog and cloud Desired Project state."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from backend.project_workspaces.contracts import (
    DesiredProjectManifest,
    ProjectWorkflowInstance,
    WorkflowCapsuleVersion,
    WorkflowDefinition,
    WorkflowDefinitionVersion,
    WorkspaceBootstrapDescriptor,
)
from backend.workflow_packages.serialization import to_json_value
from backend.project_workspaces.bootstrap import workspace_bootstrap_document
from backend.project_workspaces.sync import (
    WorkspaceSyncPlan,
    acknowledgement_document,
    sync_plan_document,
)

from .common import StrictDTO


class WorkflowVersionCatalogResponse(StrictDTO):
    version: str
    contract_checksum: str
    input_schema_id: str
    output_schema_id: str
    review_status: str
    core_capability_maturity: str
    published_at: str | None
    artifact_requirements: list[dict[str, Any]]
    skills: list[dict[str, Any]] = Field(default_factory=list)
    resource_requirements: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def from_contract(
        cls, value: WorkflowDefinitionVersion, requirements=(), skills=(),
        resource_requirements=(),
    ):
        return cls(
            version=value.version,
            contract_checksum=value.contract_checksum,
            input_schema_id=value.input_schema_id,
            output_schema_id=value.output_schema_id,
            review_status=value.review_status.value,
            core_capability_maturity=value.core_capability_maturity.value,
            published_at=value.published_at.isoformat() if value.published_at else None,
            artifact_requirements=[{
                "requirement_key": item.requirement_key,
                "artifact_type": item.artifact_type,
                "schema_constraint": item.schema_constraint,
                "required": item.required,
                "target_relative_path": item.target_relative_path,
            } for item in requirements],
            skills=[{
                "skill_id": pin.skill_id,
                "display_name": definition.display_name,
                "version": pin.skill_version,
                "checksum": pin.skill_checksum,
                "trust": version.trust_tier.value,
                "purpose": pin.purpose,
            } for pin, definition, version in skills],
            resource_requirements=[{
                "requirement_key": item.requirement_key,
                "resource_kind": item.resource_kind.value,
                "required": item.required,
                "cardinality_min": item.cardinality_min,
                "cardinality_max": item.cardinality_max,
                "allowed_providers": [value.value for value in item.allowed_providers],
                "usage_description": item.usage_description,
            } for item in resource_requirements],
        )


class CreateProjectResourceRequest(StrictDTO):
    resource_kind: str = Field(min_length=2, max_length=64)
    provider: str = Field(min_length=2, max_length=64)
    locator: str = Field(min_length=3, max_length=300)
    exact_revision: str = Field(min_length=7, max_length=128)
    expected_content_checksum: str = Field(min_length=71, max_length=71)
    display_name: str = Field(min_length=1, max_length=160)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectResourceResponse(StrictDTO):
    resource_id: str
    project_id: str
    resource_kind: str
    provider: str
    locator: str
    exact_revision: str
    expected_content_checksum: str
    display_name: str
    metadata: dict[str, Any]
    lifecycle: str
    created_at: str

    @classmethod
    def from_contract(cls, value):
        return cls(
            resource_id=value.resource_id,
            project_id=value.project_id,
            resource_kind=value.resource_kind.value,
            provider=value.provider.value,
            locator=value.locator,
            exact_revision=value.exact_revision,
            expected_content_checksum=value.expected_content_checksum,
            display_name=value.display_name,
            metadata=to_json_value(value.metadata),
            lifecycle=value.lifecycle.value,
            created_at=value.created_at.isoformat(),
        )


class ProjectResourcePageResponse(StrictDTO):
    items: list[ProjectResourceResponse]
    total: int
    offset: int
    limit: int


class CreateWorkflowResourceBindingRequest(StrictDTO):
    requirement_key: str = Field(min_length=2, max_length=128)
    resource_id: str = Field(min_length=41, max_length=41)
    idempotency_key: str = Field(min_length=36, max_length=36)


class WorkflowResourceBindingResponse(StrictDTO):
    binding_id: str
    project_id: str
    workflow_instance_id: str
    workflow_definition_id: str
    workflow_version: str
    requirement_key: str
    resource_id: str
    expected_content_checksum: str
    state: str
    resource: ProjectResourceResponse

    @classmethod
    def from_contract(cls, value, resource):
        return cls(
            binding_id=value.binding_id,
            project_id=value.project_id,
            workflow_instance_id=value.workflow_instance_id,
            workflow_definition_id=value.workflow_definition_id,
            workflow_version=value.workflow_version,
            requirement_key=value.requirement_key,
            resource_id=value.resource_id,
            expected_content_checksum=value.expected_content_checksum,
            state=value.state.value,
            resource=ProjectResourceResponse.from_contract(resource),
        )


class WorkflowResourceBindingPageResponse(StrictDTO):
    items: list[WorkflowResourceBindingResponse]
    total: int


class SkillVersionResponse(StrictDTO):
    version: str
    checksum: str
    manifest_schema_version: str
    trust: str
    review_status: str
    published_at: str | None


class SkillCatalogResponse(StrictDTO):
    skill_id: str
    display_name: str
    description: str
    lifecycle: str
    source_class: str
    trust: str
    current_version: SkillVersionResponse | None


class SkillCatalogPageResponse(StrictDTO):
    items: list[SkillCatalogResponse]
    total: int
    offset: int
    limit: int


class SkillCatalogDetailResponse(SkillCatalogResponse):
    versions: list[SkillVersionResponse]
    workflow_usages: list[dict[str, Any]]


class CapsuleVersionCatalogResponse(StrictDTO):
    capsule_id: str
    capsule_version: str
    workflow_version: str
    definition_checksum: str
    review_status: str
    trust_classification: str | None
    legacy_package_compatible: bool

    @classmethod
    def from_contract(cls, value: WorkflowCapsuleVersion):
        return cls(
            capsule_id=value.capsule_id,
            capsule_version=value.capsule_version,
            workflow_version=value.workflow_version,
            definition_checksum=value.definition_checksum,
            review_status=value.review_status.value,
            trust_classification=value.compatibility.get("trust_classification"),
            legacy_package_compatible=value.legacy_package_compatible,
        )


class WorkflowCatalogResponse(StrictDTO):
    workflow_definition_id: str
    stable_workflow_key: str
    display_name: str
    description: str
    lifecycle: str
    creatable: bool
    allows_multiple_instances: bool
    recommended_version: WorkflowVersionCatalogResponse | None
    recommended_capsule: CapsuleVersionCatalogResponse | None


class WorkflowCatalogPageResponse(StrictDTO):
    items: list[WorkflowCatalogResponse]
    total: int


class WorkflowCatalogDetailResponse(WorkflowCatalogResponse):
    versions: list[WorkflowVersionCatalogResponse]
    capsules: list[CapsuleVersionCatalogResponse]


class CreateWorkflowInstanceRequest(StrictDTO):
    workflow_definition_id: str = Field(min_length=2, max_length=128)
    workflow_version: str = Field(min_length=5, max_length=100)
    capsule_id: str = Field(min_length=40, max_length=40)
    capsule_version: str = Field(min_length=5, max_length=100)
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    base_revision: int = Field(ge=1)


class RetireWorkflowInstanceRequest(StrictDTO):
    base_revision: int = Field(ge=1)


class WorkflowInstanceResponse(StrictDTO):
    workflow_instance_id: str
    project_id: str
    workflow_definition_id: str
    workflow_version: str
    capsule_id: str | None
    capsule_version: str | None
    desired_state: str
    display_name: str
    created_manifest_revision: int
    retired_manifest_revision: int | None
    in_current_manifest: bool
    created_at: str
    updated_at: str
    skills: list[dict[str, Any]] = Field(default_factory=list)
    resource_requirements: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def from_contract(
        cls, value: ProjectWorkflowInstance, skills=(), resource_requirements=()
    ):
        return cls(
            workflow_instance_id=value.workflow_instance_id,
            project_id=value.project_id,
            workflow_definition_id=value.workflow_definition_id,
            workflow_version=value.workflow_version,
            capsule_id=value.capsule_id,
            capsule_version=value.capsule_version,
            desired_state=value.desired_state.value,
            display_name=value.display_name,
            created_manifest_revision=value.created_manifest_revision,
            retired_manifest_revision=value.retired_manifest_revision,
            in_current_manifest=value.desired_state.value == "ACTIVE",
            created_at=value.created_at.isoformat(),
            updated_at=value.updated_at.isoformat(),
            skills=[{
                "skill_id": pin.skill_id,
                "display_name": definition.display_name,
                "version": pin.skill_version,
                "checksum": pin.skill_checksum,
                "trust": version.trust_tier.value,
                "purpose": pin.purpose,
            } for pin, definition, version in skills],
            resource_requirements=[{
                "requirement_key": item.requirement_key,
                "resource_kind": item.resource_kind.value,
                "required": item.required,
                "cardinality_min": item.cardinality_min,
                "cardinality_max": item.cardinality_max,
                "allowed_providers": [value.value for value in item.allowed_providers],
                "usage_description": item.usage_description,
            } for item in resource_requirements],
        )


class WorkflowInstancePageResponse(StrictDTO):
    items: list[WorkflowInstanceResponse]
    total: int
    manifest_revision: int


class DesiredProjectManifestResponse(StrictDTO):
    project_id: str
    workspace_id: str
    manifest_revision: int
    base_revision: int
    schema_version: str
    canonical_checksum: str
    manifest: dict[str, Any]
    created_at: str

    @classmethod
    def from_contract(cls, value: DesiredProjectManifest):
        document = to_json_value(value.manifest_json)
        assert isinstance(document, dict)
        return cls(
            project_id=value.project_id,
            workspace_id=value.workspace_id,
            manifest_revision=value.manifest_revision,
            base_revision=value.base_revision,
            schema_version=value.schema_version,
            canonical_checksum=value.canonical_checksum,
            manifest=document,
            created_at=value.created_at.isoformat(),
        )


class WorkspaceBootstrapResponse(StrictDTO):
    schema_version: str
    workspace_schema_version: str
    project_id: str
    workspace_id: str
    cloud_origin_id: str
    project_api_path: str
    workspace_lifecycle: str
    bootstrap_manifest_revision: int
    desired_manifest_checksum: str
    desired_manifest: dict[str, Any]
    workflow_capsules: list[dict[str, Any]]
    created_at: str
    descriptor_checksum: str

    @classmethod
    def from_contract(cls, value: WorkspaceBootstrapDescriptor):
        return cls.model_validate(workspace_bootstrap_document(value))


class InstalledCapsuleObservation(StrictDTO):
    workflow_instance_id: str = Field(pattern=r"^wfi-[0-9a-f]{32}$")
    workflow_definition_id: str = Field(min_length=2, max_length=128)
    workflow_definition_version: str = Field(min_length=5, max_length=100)
    capsule_id: str = Field(pattern=r"^capsule-[0-9a-f]{32}$")
    capsule_version: str = Field(min_length=5, max_length=100)
    capsule_definition_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    package_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    relative_path: str = Field(min_length=1, max_length=500)


class WorkspaceSyncPlanRequest(StrictDTO):
    workspace_id: str = Field(min_length=42, max_length=42)
    installed_manifest_revision: int = Field(ge=0)
    installed_lock_checksum: str | None = Field(default=None, min_length=71, max_length=71)
    installed_capsules: list[InstalledCapsuleObservation] = Field(default_factory=list, max_length=100)
    idempotency_key: str = Field(min_length=36, max_length=36)
    dry_run: bool = False


class WorkspaceSyncPlanResponse(StrictDTO):
    schema_version: str
    installation_id: str
    project_id: str
    workspace_id: str
    base_manifest_revision: int
    target_manifest_revision: int
    target_manifest_checksum: str
    installed_lock_checksum: str | None
    plan_checksum: str
    state: str
    actions: list[dict[str, Any]]
    created_at: str
    expires_at: str

    @classmethod
    def from_contract(cls, value: WorkspaceSyncPlan):
        return cls.model_validate(sync_plan_document(value))


class WorkspaceSyncAcknowledgementRequest(StrictDTO):
    schema_version: str = Field(pattern=r"^reagent\.capsule-installation-ack/v0\.1$")
    installation_id: str = Field(pattern=r"^install-[0-9a-f]{32}$")
    project_id: str = Field(pattern=r"^project-[0-9a-f]{32}$")
    workspace_id: str = Field(pattern=r"^workspace-[0-9a-f]{32}$")
    manifest_revision: int = Field(ge=1)
    manifest_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plan_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    installed_lock_schema: str = Field(pattern=r"^reagent\.workspace-installed-lock/v0\.1$")
    installed_lock_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    idempotency_key: str = Field(min_length=36, max_length=36)
    installed_capsules: list[dict[str, Any]] = Field(max_length=100)
    installed_at: str


class WorkspaceSyncAcknowledgementResponse(StrictDTO):
    schema_version: str
    installation_id: str
    project_id: str
    workspace_id: str
    manifest_revision: int
    installed_lock_checksum: str
    status: str
    idempotency_key: str
    acknowledged_at: str

    @classmethod
    def from_contract(cls, value):
        return cls.model_validate(acknowledgement_document(value))
