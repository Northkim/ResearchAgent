"""Workflow-run command and query endpoints containing transport mapping only."""

from fastapi import APIRouter, Query, status

from backend.domain.enums import WorkflowRunStatus

from ..dependencies import ServicesDependency
from ..schemas import (
    ArtifactResponse,
    CreateCatalogRunRequest,
    CreateRunRequest,
    ExecutionEventResponse,
    ProviderOperationResponse,
    WorkflowRunPageResponse,
    WorkflowRunResponse,
)

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=WorkflowRunPageResponse)
async def list_runs(
    services: ServicesDependency,
    status_filter: WorkflowRunStatus | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> WorkflowRunPageResponse:
    view = services.list_workflow_runs.execute(
        status=status_filter,
        offset=offset,
        limit=limit,
    )
    return WorkflowRunPageResponse.from_view(view)


@router.post(
    "",
    response_model=WorkflowRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_run(
    request: CreateRunRequest,
    services: ServicesDependency,
) -> WorkflowRunResponse:
    view = services.create_workflow_run.execute(request.to_command())
    return WorkflowRunResponse.from_view(view)


@router.post(
    "/from-catalog",
    response_model=WorkflowRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_catalog_run(
    request: CreateCatalogRunRequest,
    services: ServicesDependency,
) -> WorkflowRunResponse:
    view = services.create_catalog_workflow_run.execute(request.to_command())
    return WorkflowRunResponse.from_view(view)


@router.get("/{workflow_run_id}", response_model=WorkflowRunResponse)
async def get_run(
    workflow_run_id: str,
    services: ServicesDependency,
) -> WorkflowRunResponse:
    view = services.get_workflow_run.execute(workflow_run_id)
    return WorkflowRunResponse.from_view(view)


@router.get(
    "/{workflow_run_id}/events",
    response_model=list[ExecutionEventResponse],
)
async def list_run_events(
    workflow_run_id: str,
    services: ServicesDependency,
) -> list[ExecutionEventResponse]:
    events = services.list_execution_events.execute(workflow_run_id)
    return [ExecutionEventResponse.from_view(event) for event in events]


@router.get(
    "/{workflow_run_id}/artifacts",
    response_model=list[ArtifactResponse],
)
async def list_run_artifacts(
    workflow_run_id: str,
    services: ServicesDependency,
) -> list[ArtifactResponse]:
    return [
        ArtifactResponse.from_view(item)
        for item in services.list_run_artifacts.execute(workflow_run_id)
    ]


@router.get(
    "/{workflow_run_id}/provider-usage",
    response_model=list[ProviderOperationResponse],
)
async def list_provider_usage(
    workflow_run_id: str,
    services: ServicesDependency,
) -> list[ProviderOperationResponse]:
    return [
        ProviderOperationResponse.from_view(item)
        for item in services.list_provider_usage.execute(workflow_run_id)
    ]


@router.post("/{workflow_run_id}/resume", response_model=WorkflowRunResponse)
async def resume_run(
    workflow_run_id: str,
    services: ServicesDependency,
) -> WorkflowRunResponse:
    view = await services.resume_workflow_run.execute(workflow_run_id)
    return WorkflowRunResponse.from_view(view)


@router.post("/{workflow_run_id}/cancel", response_model=WorkflowRunResponse)
async def cancel_run(
    workflow_run_id: str,
    services: ServicesDependency,
) -> WorkflowRunResponse:
    view = services.cancel_workflow_run.execute(workflow_run_id)
    return WorkflowRunResponse.from_view(view)
    ProviderOperationResponse,
