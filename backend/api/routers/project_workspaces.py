"""Workflow catalog and Project desired-state endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query, Response, status
from pydantic import Field

from backend.project_workspaces.contracts import (
    WorkflowDefinitionLifecycle,
    WorkflowReviewStatus,
)
from backend.controlled_local_run_approvals import (
    ControlledLocalRunApproval,
    ControlledLocalRunApprovalService,
    ControlledLocalRunSummary,
)
from backend.application.errors import ApplicationCodedValidationError

from ..dependencies import LocalProductServicesDependency, UnitOfWorkDependency
from ..schemas.project_workspaces import (
    CapsuleVersionCatalogResponse,
    CreateWorkflowInstanceRequest,
    CreateProjectResourceRequest,
    CreateWorkflowResourceBindingRequest,
    DesiredProjectManifestResponse,
    RetireWorkflowInstanceRequest,
    SkillCatalogDetailResponse,
    SkillCatalogPageResponse,
    SkillCatalogResponse,
    SkillVersionResponse,
    ProjectResourcePageResponse,
    ProjectResourceResponse,
    WorkflowResourceBindingPageResponse,
    WorkflowResourceBindingResponse,
    WorkflowCatalogDetailResponse,
    WorkflowCatalogPageResponse,
    WorkflowCatalogResponse,
    WorkflowInstancePageResponse,
    WorkflowInstanceResponse,
    WorkflowVersionCatalogResponse,
    WorkspaceBootstrapResponse,
    WorkspaceSyncAcknowledgementRequest,
    WorkspaceSyncAcknowledgementResponse,
    WorkspaceSyncPlanRequest,
    WorkspaceSyncPlanResponse,
    ControlledLocalRunApprovalReportRequest,
    ControlledLocalRunApprovalDecisionRequest,
    ControlledLocalRunApprovalConsumeRequest,
    ControlledLocalRunApprovalResponse,
    ControlledLocalRunApprovalProjectionResponse,
    ControlledLocalRunApprovalConsumptionResponse,
)
from ..schemas.common import StrictDTO

router = APIRouter(tags=["project-workspaces"])


class StartWritingRevisionRequest(StrictDTO):
    parent_manuscript_artifact_id: str = Field(min_length=41, max_length=41)
    causal_review_artifact_id: str = Field(min_length=41, max_length=41)
    base_revision: int = Field(ge=1)


def _controlled_approval_service(services, unit_of_work):
    return ControlledLocalRunApprovalService(
        repository=unit_of_work.controlled_local_run_approvals,
        instance_resolver=services.project_workspaces.get_instance,
        commit_callback=unit_of_work.commit,
    )


def _catalog_response(definition, service, resource_service) -> WorkflowCatalogResponse:
    versions = service.versions_for(definition.workflow_definition_id)
    capsules = service.capsules_for(definition.workflow_definition_id)
    published = [
        item
        for item in versions
        if item.review_status is WorkflowReviewStatus.REVIEWED
        and item.published_at is not None
        and item.compatibility.get("default_project_setup", True) is True
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
            WorkflowVersionCatalogResponse.from_contract(
                selected_version,
                service.requirements_for(
                    selected_version.workflow_definition_id, selected_version.version
                ),
                service.skill_projections_for(
                    selected_version.workflow_definition_id, selected_version.version
                ),
                resource_service.requirements_for(
                    selected_version.workflow_definition_id, selected_version.version
                ),
            )
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
        _catalog_response(
            definition, services.project_workspaces, services.resource_references
        )
        for definition in definitions
    ]
    return WorkflowCatalogPageResponse(items=items, total=len(items))


def _skill_version_response(value) -> SkillVersionResponse:
    return SkillVersionResponse(
        version=value.skill_version,
        checksum=value.content_checksum,
        manifest_schema_version=value.manifest_schema_version,
        trust=value.trust_tier.value,
        review_status=value.review_status.value,
        published_at=value.published_at.isoformat() if value.published_at else None,
    )


def _skill_response(definition, service) -> SkillCatalogResponse:
    versions = list(service.skill_versions_for(definition.skill_id))
    versions.sort(key=lambda item: item.skill_version)
    current = versions[-1] if versions else None
    return SkillCatalogResponse(
        skill_id=definition.skill_id,
        display_name=definition.display_name,
        description=definition.description,
        lifecycle=definition.lifecycle.value,
        source_class=definition.source_class.value,
        trust=definition.trust_tier.value,
        current_version=_skill_version_response(current) if current else None,
    )


@router.get("/skills", response_model=SkillCatalogPageResponse)
async def list_skills(
    services: LocalProductServicesDependency,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> SkillCatalogPageResponse:
    definitions, total = services.project_workspaces.list_skills(
        offset=offset, limit=limit
    )
    return SkillCatalogPageResponse(
        items=[
            _skill_response(item, services.project_workspaces)
            for item in definitions
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/skills/{skill_id}", response_model=SkillCatalogDetailResponse)
async def get_skill(
    skill_id: str,
    services: LocalProductServicesDependency,
) -> SkillCatalogDetailResponse:
    definition = services.project_workspaces.get_skill(skill_id)
    summary = _skill_response(definition, services.project_workspaces)
    versions = services.project_workspaces.skill_versions_for(skill_id)
    usages = services.project_workspaces.workflow_usages_for_skill(skill_id)
    return SkillCatalogDetailResponse(
        **summary.model_dump(),
        versions=[_skill_version_response(item) for item in versions],
        workflow_usages=[{
            "workflow_definition_id": workflow_id,
            "workflow_version": workflow_version,
            "skill_version": pin.skill_version,
            "checksum": pin.skill_checksum,
            "purpose": pin.purpose,
        } for workflow_id, workflow_version, pin, _, _ in usages],
    )


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
    summary = _catalog_response(
        definition, services.project_workspaces, services.resource_references
    )
    return WorkflowCatalogDetailResponse(
        **summary.model_dump(),
        versions=[
            WorkflowVersionCatalogResponse.from_contract(
                item, services.project_workspaces.requirements_for(
                    item.workflow_definition_id, item.version
                ), services.project_workspaces.skill_projections_for(
                    item.workflow_definition_id, item.version
                ), services.resource_references.requirements_for(
                    item.workflow_definition_id, item.version
                )
            )
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
        items=[WorkflowInstanceResponse.from_contract(
            item,
            services.project_workspaces.skill_projections_for(
                item.workflow_definition_id, item.workflow_version
            ),
            services.resource_references.requirements_for(
                item.workflow_definition_id, item.workflow_version
            ),
        ) for item in instances],
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
    return WorkflowInstanceResponse.from_contract(
        instance,
        services.project_workspaces.skill_projections_for(
            instance.workflow_definition_id, instance.workflow_version
        ),
        services.resource_references.requirements_for(
            instance.workflow_definition_id, instance.workflow_version
        ),
    )


@router.post(
    "/projects/{project_id}/writing-revisions",
    response_model=WorkflowInstanceResponse,
)
async def start_writing_revision(
    project_id: str,
    request: StartWritingRevisionRequest,
    services: LocalProductServicesDependency,
) -> WorkflowInstanceResponse:
    instance = services.project_workspaces.start_writing_revision(
        project_id=project_id,
        **request.model_dump(),
    )
    return WorkflowInstanceResponse.from_contract(
        instance,
        services.project_workspaces.skill_projections_for(
            instance.workflow_definition_id, instance.workflow_version
        ),
        services.resource_references.requirements_for(
            instance.workflow_definition_id, instance.workflow_version
        ),
    )


@router.get(
    "/projects/{project_id}/workflow-instances/{instance_id}",
    response_model=WorkflowInstanceResponse,
)
async def get_workflow_instance(
    project_id: str,
    instance_id: str,
    services: LocalProductServicesDependency,
) -> WorkflowInstanceResponse:
    instance = services.project_workspaces.get_instance(project_id, instance_id)
    return WorkflowInstanceResponse.from_contract(
        instance,
        services.project_workspaces.skill_projections_for(
            instance.workflow_definition_id, instance.workflow_version
        ),
        services.resource_references.requirements_for(
            instance.workflow_definition_id, instance.workflow_version
        ),
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
    instance = services.project_workspaces.retire_instance(
            project_id=project_id,
            instance_id=instance_id,
            base_revision=request.base_revision,
        )
    return WorkflowInstanceResponse.from_contract(
        instance,
        services.project_workspaces.skill_projections_for(
            instance.workflow_definition_id, instance.workflow_version
        ),
        services.resource_references.requirements_for(
            instance.workflow_definition_id, instance.workflow_version
        ),
    )


@router.get(
    "/projects/{project_id}/resources",
    response_model=ProjectResourcePageResponse,
)
async def list_project_resources(
    project_id: str,
    services: LocalProductServicesDependency,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> ProjectResourcePageResponse:
    resources, total = services.resource_references.list_resources(
        project_id, offset=offset, limit=limit
    )
    return ProjectResourcePageResponse(
        items=[ProjectResourceResponse.from_contract(item) for item in resources],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/projects/{project_id}/resources",
    response_model=ProjectResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_resource(
    project_id: str,
    request: CreateProjectResourceRequest,
    services: LocalProductServicesDependency,
) -> ProjectResourceResponse:
    value = services.resource_references.create_resource(
        project_id=project_id, **request.model_dump()
    )
    return ProjectResourceResponse.from_contract(value)


@router.get(
    "/projects/{project_id}/resources/{resource_id}",
    response_model=ProjectResourceResponse,
)
async def get_project_resource(
    project_id: str,
    resource_id: str,
    services: LocalProductServicesDependency,
) -> ProjectResourceResponse:
    return ProjectResourceResponse.from_contract(
        services.resource_references.get_resource(project_id, resource_id)
    )


def _resource_binding_response(value, service):
    resource = service.get_resource(value.project_id, value.resource_id)
    return WorkflowResourceBindingResponse.from_contract(value, resource)


@router.get(
    "/projects/{project_id}/workflow-instances/{instance_id}/resource-bindings",
    response_model=WorkflowResourceBindingPageResponse,
)
async def list_workflow_resource_bindings(
    project_id: str,
    instance_id: str,
    services: LocalProductServicesDependency,
) -> WorkflowResourceBindingPageResponse:
    values = services.resource_references.binding_projections(project_id, instance_id)
    return WorkflowResourceBindingPageResponse(
        items=[
            WorkflowResourceBindingResponse.from_contract(binding, resource)
            for binding, resource in values
        ],
        total=len(values),
    )


@router.post(
    "/projects/{project_id}/workflow-instances/{instance_id}/resource-bindings",
    response_model=WorkflowResourceBindingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workflow_resource_binding(
    project_id: str,
    instance_id: str,
    request: CreateWorkflowResourceBindingRequest,
    services: LocalProductServicesDependency,
) -> WorkflowResourceBindingResponse:
    value = services.resource_references.bind_resource(
        project_id=project_id,
        workflow_instance_id=instance_id,
        **request.model_dump(),
    )
    return _resource_binding_response(value, services.resource_references)


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


@router.post(
    "/projects/{project_id}/workspace/sync-plan",
    response_model=WorkspaceSyncPlanResponse,
)
async def create_workspace_sync_plan(
    project_id: str,
    request: WorkspaceSyncPlanRequest,
    services: LocalProductServicesDependency,
) -> WorkspaceSyncPlanResponse:
    plan = services.workspace_sync.create_plan(
        project_id=project_id,
        workspace_id=request.workspace_id,
        installed_manifest_revision=request.installed_manifest_revision,
        installed_lock_checksum=request.installed_lock_checksum,
        installed_capsules=tuple(item.model_dump() for item in request.installed_capsules),
        idempotency_key=request.idempotency_key,
        dry_run=request.dry_run,
    )
    return WorkspaceSyncPlanResponse.from_contract(plan)


@router.get(
    "/projects/{project_id}/workflow-instances/{instance_id}/capsule-artifacts/"
    "{capsule_artifact_id}/download"
)
async def download_workspace_capsule_artifact(
    project_id: str,
    instance_id: str,
    capsule_artifact_id: str,
    services: LocalProductServicesDependency,
) -> Response:
    content, artifact = services.workspace_sync.read_artifact(
        project_id=project_id,
        workflow_instance_id=instance_id,
        capsule_artifact_id=capsule_artifact_id,
    )
    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.package_id}.zip"',
            "X-Content-Type-Options": "nosniff",
            "ETag": f'"{artifact.archive_checksum}"',
            "X-ReAgent-Project-ID": artifact.project_id,
            "X-ReAgent-Workflow-Instance-ID": artifact.workflow_instance_id,
            "X-ReAgent-Capsule-ID": artifact.capsule_id,
            "X-ReAgent-Capsule-Version": artifact.capsule_version,
        },
    )


@router.post(
    "/projects/{project_id}/workspace/sync-ack",
    response_model=WorkspaceSyncAcknowledgementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def acknowledge_workspace_sync(
    project_id: str,
    request: WorkspaceSyncAcknowledgementRequest,
    services: LocalProductServicesDependency,
) -> WorkspaceSyncAcknowledgementResponse:
    acknowledgement = services.workspace_sync.acknowledge(
        project_id=project_id,
        document=request.model_dump(),
    )
    return WorkspaceSyncAcknowledgementResponse.from_contract(acknowledgement)


@router.post(
    "/projects/{project_id}/workflow-instances/{instance_id}/run-approvals",
    response_model=ControlledLocalRunApprovalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def report_controlled_local_run_approval(
    project_id: str,
    instance_id: str,
    request: ControlledLocalRunApprovalReportRequest,
    services: LocalProductServicesDependency,
    unit_of_work: UnitOfWorkDependency,
) -> ControlledLocalRunApprovalResponse:
    try:
        summary = ControlledLocalRunSummary.from_mapping(
            request.summary.model_dump(by_alias=True)
        )
        value = ControlledLocalRunApproval(
            request_id=request.request_id,
            project_id=request.project_id,
            workflow_instance_id=request.workflow_instance_id,
            research_objective_checksum=request.research_objective_checksum,
            execution_plan_checksum=request.execution_plan_checksum,
            validated_package_checksum=request.validated_package_checksum,
            runtime_compatibility_checksum=request.runtime_compatibility_checksum,
            capability_checksum=request.capability_checksum,
            summary=summary,
            created_at=request.created_at,
            request_checksum=request.request_checksum,
            schema=request.schema_id,
        )
    except ValueError as error:
        raise ApplicationCodedValidationError(
            str(error), code="RUN_APPROVAL_REQUEST_INVALID"
        ) from error
    if value.project_id != project_id or value.workflow_instance_id != instance_id:
        raise ApplicationCodedValidationError(
            "Run Approval body differs from its Project route",
            code="RUN_APPROVAL_SCOPE_MISMATCH",
        )
    return ControlledLocalRunApprovalResponse.from_contract(
        _controlled_approval_service(services, unit_of_work).report(value)
    )


@router.get(
    "/projects/{project_id}/workflow-instances/{instance_id}/run-approval",
    response_model=ControlledLocalRunApprovalProjectionResponse,
)
async def observe_controlled_local_run_approval(
    project_id: str,
    instance_id: str,
    services: LocalProductServicesDependency,
    unit_of_work: UnitOfWorkDependency,
) -> ControlledLocalRunApprovalProjectionResponse:
    value = _controlled_approval_service(services, unit_of_work).observe(
        project_id, instance_id
    )
    actions = {
        None: "REPORT_EXACT_RUN_APPROVAL_REQUEST",
        "REQUESTED": "OWNER_APPROVAL_REQUIRED",
        "APPROVED": "CONSUME_APPROVAL_LOCALLY",
        "REJECTED": "REVISE_OR_KEEP_EXPERIMENT",
        "CONSUMED": "EXECUTE_APPROVED_ATTEMPT_LOCALLY",
        "SUPERSEDED": "REPORT_CURRENT_EXACT_RUN_APPROVAL_REQUEST",
    }
    return ControlledLocalRunApprovalProjectionResponse(
        request=(
            None if value is None
            else ControlledLocalRunApprovalResponse.from_contract(value)
        ),
        next_action=actions[None if value is None else value.status.value],
    )


@router.post(
    "/projects/{project_id}/workflow-instances/{instance_id}/run-approvals/"
    "{request_id}/approve",
    response_model=ControlledLocalRunApprovalResponse,
)
async def approve_controlled_local_run(
    project_id: str,
    instance_id: str,
    request_id: str,
    request: ControlledLocalRunApprovalDecisionRequest,
    services: LocalProductServicesDependency,
    unit_of_work: UnitOfWorkDependency,
) -> ControlledLocalRunApprovalResponse:
    return ControlledLocalRunApprovalResponse.from_contract(
        _controlled_approval_service(services, unit_of_work).approve(
            project_id, instance_id, request_id,
            execution_plan_checksum=request.execution_plan_checksum,
            request_checksum=request.request_checksum,
            idempotency_key=request.idempotency_key,
        )
    )


@router.post(
    "/projects/{project_id}/workflow-instances/{instance_id}/run-approvals/"
    "{request_id}/reject",
    response_model=ControlledLocalRunApprovalResponse,
)
async def reject_controlled_local_run(
    project_id: str,
    instance_id: str,
    request_id: str,
    request: ControlledLocalRunApprovalDecisionRequest,
    services: LocalProductServicesDependency,
    unit_of_work: UnitOfWorkDependency,
) -> ControlledLocalRunApprovalResponse:
    return ControlledLocalRunApprovalResponse.from_contract(
        _controlled_approval_service(services, unit_of_work).reject(
            project_id, instance_id, request_id,
            execution_plan_checksum=request.execution_plan_checksum,
            request_checksum=request.request_checksum,
            idempotency_key=request.idempotency_key,
            reason=request.reason,
        )
    )


@router.post(
    "/projects/{project_id}/workflow-instances/{instance_id}/run-approvals/"
    "{request_id}/consume",
    response_model=ControlledLocalRunApprovalConsumptionResponse,
)
async def consume_controlled_local_run(
    project_id: str,
    instance_id: str,
    request_id: str,
    request: ControlledLocalRunApprovalConsumeRequest,
    services: LocalProductServicesDependency,
    unit_of_work: UnitOfWorkDependency,
) -> ControlledLocalRunApprovalConsumptionResponse:
    return ControlledLocalRunApprovalConsumptionResponse.from_contract(
        _controlled_approval_service(services, unit_of_work).consume(
            project_id, instance_id, request_id,
            execution_plan_checksum=request.execution_plan_checksum,
            attempt_id=request.attempt_id,
        )
    )
