"""Project-scoped typed Artifact metadata and dependency APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, status

from backend.artifact_references.service import binding_document
from backend.persistence.ports import DuplicateEntityError
from backend.application.errors import ApplicationCodedConflictError

from ..dependencies import ProgressServicesDependency
from ..schemas import (
    ArtifactDependencyBindRequest,
    ArtifactDependencyPageResponse,
    ArtifactDependencyResponse,
    ArtifactMaterializationPlanResponse,
    ArtifactReferencePageResponse,
)
from ..schemas.artifact_references import ArtifactPresentationResponse

router = APIRouter(prefix="/projects/{project_id}", tags=["local-artifact-references"])


@router.put(
    "/artifacts/{artifact_id}/presentation",
    response_model=ArtifactPresentationResponse,
)
async def report_artifact_presentation(
    project_id: str,
    artifact_id: str,
    payload: dict[str, Any],
    services: ProgressServicesDependency,
) -> ArtifactPresentationResponse:
    return ArtifactPresentationResponse.model_validate(
        services.artifact_references.report_presentation(
            project_id=project_id,
            artifact_id=artifact_id,
            payload=payload,
        )
    )


@router.get("/artifacts", response_model=ArtifactReferencePageResponse)
async def list_project_artifacts(
    project_id: str,
    services: ProgressServicesDependency,
    workflow_instance_id: str | None = Query(default=None),
    artifact_type: str | None = Query(default=None),
    artifact_state: str | None = Query(default=None, alias="state"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
) -> ArtifactReferencePageResponse:
    return ArtifactReferencePageResponse.model_validate(
        services.artifact_references.list_artifacts(
            project_id=project_id,
            producer_workflow_instance_id=workflow_instance_id,
            artifact_type=artifact_type,
            state=artifact_state,
            offset=offset,
            limit=limit,
        )
    )


@router.get(
    "/workflow-instances/{instance_id}/artifacts",
    response_model=ArtifactReferencePageResponse,
)
async def list_workflow_instance_artifacts(
    project_id: str,
    instance_id: str,
    services: ProgressServicesDependency,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
) -> ArtifactReferencePageResponse:
    return ArtifactReferencePageResponse.model_validate(
        services.artifact_references.list_artifacts(
            project_id=project_id,
            producer_workflow_instance_id=instance_id,
            artifact_type=None,
            state=None,
            offset=offset,
            limit=limit,
        )
    )


@router.post(
    "/workflow-instances/{instance_id}/artifact-dependencies",
    response_model=ArtifactDependencyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bind_artifact_dependency(
    project_id: str,
    instance_id: str,
    request: ArtifactDependencyBindRequest,
    services: ProgressServicesDependency,
) -> ArtifactDependencyResponse:
    try:
        binding = services.artifact_references.bind_dependency(
            project_id=project_id,
            consumer_workflow_instance_id=instance_id,
            requirement_key=request.requirement_key,
            artifact_id=request.artifact_id,
            idempotency_key=request.idempotency_key,
            replace_binding_id=request.replace_binding_id,
        )
    except DuplicateEntityError as error:
        raise ApplicationCodedConflictError(
            "Concurrent Artifact dependency mutation conflicted",
            code="DEPENDENCY_BINDING_CONFLICT",
        ) from error
    return ArtifactDependencyResponse.model_validate(binding_document(binding))


@router.get(
    "/workflow-instances/{instance_id}/artifact-dependencies",
    response_model=ArtifactDependencyPageResponse,
)
async def list_artifact_dependencies(
    project_id: str,
    instance_id: str,
    services: ProgressServicesDependency,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
) -> ArtifactDependencyPageResponse:
    return ArtifactDependencyPageResponse.model_validate(
        services.artifact_references.list_dependencies(
            project_id=project_id,
            consumer_workflow_instance_id=instance_id,
            offset=offset,
            limit=limit,
        )
    )


@router.get(
    "/workflow-instances/{instance_id}/artifact-materialization-plan",
    response_model=ArtifactMaterializationPlanResponse,
)
async def get_artifact_materialization_plan(
    project_id: str,
    instance_id: str,
    services: ProgressServicesDependency,
) -> ArtifactMaterializationPlanResponse:
    return ArtifactMaterializationPlanResponse.model_validate(
        services.artifact_references.materialization_plan(
            project_id=project_id,
            consumer_workflow_instance_id=instance_id,
        )
    )
