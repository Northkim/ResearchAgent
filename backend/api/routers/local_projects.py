"""Teacher-aligned local project and Workflow Package endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from ..dependencies import LocalProductServicesDependency
from ..schemas import (
    CreateLocalProjectRequest,
    LocalPackageResponse,
    LocalProjectResponse,
)

router = APIRouter(prefix="/projects", tags=["local-projects"])


def _project_response(project, services) -> LocalProjectResponse:
    package = project.current_package
    projection = None
    if package is not None:
        projection = services.progress_reports.get_projection(
            project_id=project.project_id,
            package_id=package.package_id,
        )
    return LocalProjectResponse.from_contract(project, projection)


@router.post(
    "",
    response_model=LocalProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_local_project(
    request: CreateLocalProjectRequest,
    services: LocalProductServicesDependency,
) -> LocalProjectResponse:
    project = services.local_projects.create(**request.model_dump())
    return _project_response(project, services)


@router.get("", response_model=list[LocalProjectResponse])
async def list_local_projects(
    services: LocalProductServicesDependency,
) -> list[LocalProjectResponse]:
    return [
        _project_response(project, services)
        for project in services.local_projects.list_projects()
    ]


@router.get("/{project_id}", response_model=LocalProjectResponse)
async def get_local_project(
    project_id: str,
    services: LocalProductServicesDependency,
) -> LocalProjectResponse:
    return _project_response(services.local_projects.get(project_id), services)


@router.post(
    "/{project_id}/packages",
    response_model=LocalPackageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_local_package(
    project_id: str,
    services: LocalProductServicesDependency,
) -> LocalPackageResponse:
    project = services.local_projects.generate_package(project_id)
    assert project.current_package is not None
    return LocalPackageResponse.from_contract(project_id, project.current_package)


@router.get(
    "/{project_id}/packages/latest",
    response_model=LocalPackageResponse,
)
async def get_latest_local_package(
    project_id: str,
    services: LocalProductServicesDependency,
) -> LocalPackageResponse:
    package = services.local_projects.latest_package(project_id)
    return LocalPackageResponse.from_contract(project_id, package)


@router.get("/{project_id}/packages/{package_id}/download")
async def download_local_package(
    project_id: str,
    package_id: str,
    services: LocalProductServicesDependency,
) -> Response:
    package = services.local_projects.latest_package(project_id)
    content, filename = services.local_projects.read_package_archive(
        project_id,
        package_id,
    )
    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
            "ETag": f'"{package.zip_checksum}"',
        },
    )
