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

from .common import StrictDTO


class WorkflowVersionCatalogResponse(StrictDTO):
    version: str
    contract_checksum: str
    input_schema_id: str
    output_schema_id: str
    review_status: str
    published_at: str | None

    @classmethod
    def from_contract(cls, value: WorkflowDefinitionVersion):
        return cls(
            version=value.version,
            contract_checksum=value.contract_checksum,
            input_schema_id=value.input_schema_id,
            output_schema_id=value.output_schema_id,
            review_status=value.review_status.value,
            published_at=value.published_at.isoformat() if value.published_at else None,
        )


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

    @classmethod
    def from_contract(cls, value: ProjectWorkflowInstance):
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
