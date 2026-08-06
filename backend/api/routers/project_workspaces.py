"""Workflow catalog and Project desired-state endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from backend.project_workspaces.contracts import (
    WorkflowDefinitionLifecycle,
    WorkflowReviewStatus,
)

from ..dependencies import LocalProductServicesDependency
from ..schemas.project_workspaces import (
    CapsuleVersionCatalogResponse,
    CreateWorkflowInstanceRequest,
    DesiredProjectManifestResponse,
    RetireWorkflowInstanceRequest,
    WorkflowCatalogDetailResponse,
    WorkflowCatalogPageResponse,
    WorkflowCatalogResponse,
    WorkflowInstancePageResponse,
    WorkflowInstanceResponse,
    WorkflowVersionCatalogResponse,
    WorkspaceBootstrapResponse,
)

router = APIRouter(tags=["project-workspaces"])


def _catalog_response(definition, service) -> WorkflowCatalogResponse:
    versions = service.versions_for(definition.workflow_definition_id)
    capsules = service.capsules_for(definition.workflow_definition_id)
    published = [
        item
        for item in versions
        if item.review_status is WorkflowReviewStatus.REVIEWED
        and item.published_at is not None
    ]
    published.sort(key=lambda item: item.version)
    selected_version = published[-1] if published else None
    reviewed_capsules = [
        item
        for item in capsules
        if item.review_status is WorkflowReviewStatus.REVIEWED
        and (selected_version is None or item.workflow_version == selected_version.version)
    ]
    reviewed_capsules.sort(key=lambda item: (item.capsule_version, item.capsule_id))
    selected_capsule = reviewed_capsules[-1] if reviewed_capsules else None
    creatable = (
        definition.lifecycle is WorkflowDefinitionLifecycle.AVAILABLE
        and selected_version is not None
        and selected_capsule is not None
    )
    return WorkflowCatalogResponse(
        workflow_definition_id=definition.workflow_definition_id,
        stable_workflow_key=definition.workflow_definition_id,
        display_name=definition.display_name,
        description=definition.description,
        lifecycle=definition.lifecycle.value,
        creatable=creatable,
        allows_multiple_instances=definition.allows_multiple_instances,
        recommended_version=(
            WorkflowVersionCatalogResponse.from_contract(selected_version)
            if selected_version else None
        ),
        recommended_capsule=(
            CapsuleVersionCatalogResponse.from_contract(selected_capsule)
            if selected_capsule else None
        ),
    )


@router.get("/workflow-definitions", response_model=WorkflowCatalogPageResponse)
async def list_workflow_definitions(
    services: LocalProductServicesDependency,
) -> WorkflowCatalogPageResponse:
    definitions = services.project_workspaces.list_catalog()
    items = [
        _catalog_response(definition, services.project_workspaces)
        for definition in definitions
    ]
    return WorkflowCatalogPageResponse(items=items, total=len(items))


@router.get(
    "/workflow-definitions/{workflow_definition_id}",
    response_model=WorkflowCatalogDetailResponse,
)
async def get_workflow_definition(
    workflow_definition_id: str,
    services: LocalProductServicesDependency,
) -> WorkflowCatalogDetailResponse:
    definition = services.project_workspaces.get_catalog_definition(
        workflow_definition_id
    )
    summary = _catalog_response(definition, services.project_workspaces)
    return WorkflowCatalogDetailResponse(
        **summary.model_dump(),
        versions=[
            WorkflowVersionCatalogResponse.from_contract(item)
            for item in services.project_workspaces.versions_for(workflow_definition_id)
        ],
        capsules=[
            CapsuleVersionCatalogResponse.from_contract(item)
            for item in services.project_workspaces.capsules_for(workflow_definition_id)
        ],
    )


@router.get(
    "/projects/{project_id}/workflow-instances",
    response_model=WorkflowInstancePageResponse,
)
async def list_workflow_instances(
    project_id: str,
    services: LocalProductServicesDependency,
) -> WorkflowInstancePageResponse:
    instances = services.project_workspaces.list_instances(project_id)
    manifest = services.project_workspaces.current_manifest(project_id)
    return WorkflowInstancePageResponse(
        items=[WorkflowInstanceResponse.from_contract(item) for item in instances],
        total=len(instances),
        manifest_revision=manifest.manifest_revision,
    )


@router.post(
    "/projects/{project_id}/workflow-instances",
    response_model=WorkflowInstanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workflow_instance(
    project_id: str,
    request: CreateWorkflowInstanceRequest,
    services: LocalProductServicesDependency,
) -> WorkflowInstanceResponse:
    instance = services.project_workspaces.create_instance(
        project_id=project_id,
        **request.model_dump(),
    )
    return WorkflowInstanceResponse.from_contract(instance)


@router.get(
    "/projects/{project_id}/workflow-instances/{instance_id}",
    response_model=WorkflowInstanceResponse,
)
async def get_workflow_instance(
    project_id: str,
    instance_id: str,
    services: LocalProductServicesDependency,
) -> WorkflowInstanceResponse:
    return WorkflowInstanceResponse.from_contract(
        services.project_workspaces.get_instance(project_id, instance_id)
    )


@router.post(
    "/projects/{project_id}/workflow-instances/{instance_id}/retire",
    response_model=WorkflowInstanceResponse,
)
async def retire_workflow_instance(
    project_id: str,
    instance_id: str,
    request: RetireWorkflowInstanceRequest,
    services: LocalProductServicesDependency,
) -> WorkflowInstanceResponse:
    return WorkflowInstanceResponse.from_contract(
        services.project_workspaces.retire_instance(
            project_id=project_id,
            instance_id=instance_id,
            base_revision=request.base_revision,
        )
    )


@router.get(
    "/projects/{project_id}/manifest",
    response_model=DesiredProjectManifestResponse,
)
async def get_project_manifest(
    project_id: str,
    services: LocalProductServicesDependency,
) -> DesiredProjectManifestResponse:
    return DesiredProjectManifestResponse.from_contract(
        services.project_workspaces.current_manifest(project_id)
    )


@router.get(
    "/projects/{project_id}/workspace-bootstrap",
    response_model=WorkspaceBootstrapResponse,
)
async def get_workspace_bootstrap(
    project_id: str,
    services: LocalProductServicesDependency,
) -> WorkspaceBootstrapResponse:
    return WorkspaceBootstrapResponse.from_contract(
        services.project_workspaces.workspace_bootstrap(project_id)
    )
