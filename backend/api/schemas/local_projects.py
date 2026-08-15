"""HTTP DTOs for the local V0.1 project product."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from backend.local_projects import LocalPackageMetadata, LocalProject
from backend.progress_reports import ProjectProgressProjection, ProjectWorkflowProgressProjection

from .common import StrictDTO
from .progress import ProjectAttentionResponse, ProjectProgressResponse


class CreateLocalProjectRequest(StrictDTO):
    name: str = Field(min_length=1, max_length=160)
    research_topic: str = Field(min_length=1, max_length=500)
    selected_workflow: Literal["LITERATURE_SEARCH"]
    workflow_setup: Literal[
        "literature-only", "literature-and-idea", "full-research", "custom"
    ] = "literature-only"
    custom_workflow_definition_ids: list[str] = Field(
        default_factory=list, max_length=20
    )


class LocalPackageResponse(StrictDTO):
    package_id: str
    package_schema_version: str
    package_checksum: str
    manifest_checksum: str
    zip_checksum: str
    workflow_id: str
    workflow_version: str
    workflow_checksum: str
    file_count: int
    package_size_bytes: int
    generated_at: str
    download_url: str

    @classmethod
    def from_contract(
        cls,
        project_id: str,
        package: LocalPackageMetadata,
    ) -> LocalPackageResponse:
        return cls(
            package_id=package.package_id,
            package_schema_version=package.package_schema_version,
            package_checksum=package.package_checksum,
            manifest_checksum=package.manifest_checksum,
            zip_checksum=package.zip_checksum,
            workflow_id=package.workflow_id,
            workflow_version=package.workflow_version,
            workflow_checksum=package.workflow_checksum,
            file_count=package.file_count,
            package_size_bytes=package.package_size_bytes,
            generated_at=package.generated_at,
            download_url=(
                f"/projects/{project_id}/packages/{package.package_id}/download"
            ),
        )


class LocalProjectResponse(StrictDTO):
    project_id: str
    name: str
    research_topic: str
    selected_workflow: Literal["LITERATURE_SEARCH"]
    created_at: str
    updated_at: str
    current_package: LocalPackageResponse | None
    progress: ProjectProgressResponse | None
    attention: ProjectAttentionResponse

    @classmethod
    def from_contract(
        cls,
        project: LocalProject,
        progress: ProjectProgressProjection | None,
        workflow_progress: ProjectWorkflowProgressProjection,
    ) -> LocalProjectResponse:
        return cls(
            project_id=project.project_id,
            name=project.name,
            research_topic=project.research_topic,
            selected_workflow=project.selected_workflow,
            created_at=project.created_at,
            updated_at=project.updated_at,
            current_package=(
                LocalPackageResponse.from_contract(
                    project.project_id,
                    project.current_package,
                )
                if project.current_package is not None
                else None
            ),
            progress=(
                ProjectProgressResponse.from_contract(progress)
                if progress is not None
                else None
            ),
            attention=ProjectAttentionResponse.model_validate(
                workflow_progress.attention.to_dict()
            ),
        )
