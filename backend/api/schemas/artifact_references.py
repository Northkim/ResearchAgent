"""Strict HTTP DTOs for bounded Artifact metadata and dependencies."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import StrictDTO


class ArtifactPresentationResponse(StrictDTO):
    schema_identity: str
    artifact_id: str
    artifact_checksum: str
    presentation_checksum: str
    payload: dict
    reported_at: datetime


class ArtifactReferenceResponse(StrictDTO):
    schema_version: str
    artifact_id: str
    project_id: str
    producer_workflow_instance_id: str
    producer_progress_receipt_id: str
    producer_progress_report_id: str
    producer_execution_round: int
    producer_capsule_id: str
    producer_capsule_version: str
    producer_core_capability_maturity: str
    artifact_type: str
    artifact_schema_version: str
    media_type: str
    state: str
    relative_path: str
    content_checksum: str
    size_bytes: int
    cloud_metadata_available: bool
    produced_at: datetime
    retired_at: datetime | None
    created_at: datetime
    updated_at: datetime
    presentation: ArtifactPresentationResponse | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


class ArtifactReferencePageResponse(StrictDTO):
    schema_version: str
    project_id: str
    artifacts: list[ArtifactReferenceResponse]
    offset: int
    limit: int
    total: int
    has_more: bool


class ArtifactDependencyBindRequest(StrictDTO):
    requirement_key: str = Field(pattern=r"^[a-z][a-z0-9._-]{1,127}$")
    artifact_id: str = Field(pattern=r"^artifact-[0-9a-f]{32}$")
    idempotency_key: str
    replace_binding_id: str | None = Field(
        default=None, pattern=r"^artifact-binding-[0-9a-f]{32}$"
    )


class ArtifactDependencyResponse(StrictDTO):
    binding_id: str
    project_id: str
    consumer_workflow_instance_id: str
    consumer_workflow_definition_id: str
    consumer_workflow_version: str
    requirement_key: str
    artifact_id: str
    expected_checksum: str
    state: str
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None


class ArtifactDependencyPageResponse(StrictDTO):
    schema_version: str = "reagent.artifact-dependency-page/v0.1"
    project_id: str
    consumer_workflow_instance_id: str
    dependencies: list[ArtifactDependencyResponse]
    offset: int
    limit: int
    total: int
    has_more: bool


class ArtifactMaterializationItemResponse(StrictDTO):
    binding_id: str
    requirement_key: str
    consumer_workflow_instance_id: str
    producer_workflow_instance_id: str
    artifact_id: str
    artifact_type: str
    artifact_schema_version: str
    expected_checksum: str
    expected_size_bytes: int
    source_capsule_relative_path: str
    source_relative_path: str
    target_capsule_relative_path: str
    target_relative_path: str
    materialization_mode: str


class ArtifactMaterializationPlanResponse(StrictDTO):
    schema_version: str
    project_id: str
    workspace_id: str
    consumer_workflow_instance_id: str
    artifacts: list[ArtifactMaterializationItemResponse]
    created_at: datetime
    plan_checksum: str
