"""Strict DTOs for explicit local Progress Report upload and cloud progress."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from backend.progress_reports.contracts import (
    ProjectWorkflowProgressProjection,
    ProgressReportUploadEnvelope,
    ProgressUploadReceipt,
    ProjectProgressProjection,
    UploadedProgressReport,
)
from backend.artifact_references.contracts import ArtifactDeclaration

from .common import StrictDTO


class ProgressReportUploadRequest(StrictDTO):
    workflow_instance_id: str | None = Field(
        default=None,
        pattern=r"^wfi-[0-9a-f]{32}$",
    )
    upload_schema_version: str
    project_id: str
    package_id: str
    package_checksum: str
    report_schema_version: str
    report_id: str
    report_checksum: str
    original_report_media_type: str
    original_report_base64: str = Field(min_length=1, max_length=400_000)
    original_report_checksum: str
    original_report_size: int = Field(gt=0, le=256 * 1024)
    uploaded_at: str
    uploader_type: str
    client_version: str
    source_path_hint: str
    context_snapshot_metadata: dict[str, Any] | None = None
    envelope_checksum: str
    artifact_declarations: list["ArtifactDeclarationRequest"] = Field(
        default_factory=list,
        max_length=100,
    )

    def to_contract(self) -> ProgressReportUploadEnvelope:
        payload = self.model_dump()
        payload.pop("workflow_instance_id")
        payload.pop("artifact_declarations")
        return ProgressReportUploadEnvelope.from_dict(payload)

    def to_artifact_declarations(self) -> tuple[ArtifactDeclaration, ...]:
        return tuple(item.to_contract() for item in self.artifact_declarations)


class ArtifactDeclarationRequest(StrictDTO):
    artifact_id: str = Field(pattern=r"^artifact-[0-9a-f]{32}$")
    artifact_type: str = Field(
        pattern=r"^[a-z][a-z0-9._-]{1,139}(?:/v[0-9]+(?:\.[0-9]+)?)?$"
    )
    artifact_schema_version: str = Field(
        pattern=(
            r"^(?:reagent\.artifact\.[a-z][a-z0-9._-]*/v[0-9]+\.[0-9]+|"
            r"[a-z][a-z0-9._-]{1,139}/v[0-9]+(?:\.[0-9]+)?)$"
        )
    )
    media_type: str
    relative_path: str
    content_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0, le=1_099_511_627_776)
    produced_at: datetime

    def to_contract(self) -> ArtifactDeclaration:
        return ArtifactDeclaration(**self.model_dump())


class ProgressUploadReceiptResponse(StrictDTO):
    receipt_id: str
    project_id: str
    workflow_instance_id: str
    package_id: str
    report_id: str
    report_checksum: str
    original_report_checksum: str
    validation_status: str
    chain_state: str
    accepted_for_projection: bool
    idempotent_replay: bool
    uploaded_at: str
    received_at: str
    warning_count: int
    error_count: int
    receipt_checksum: str

    @classmethod
    def from_contract(
        cls,
        receipt: ProgressUploadReceipt,
    ) -> ProgressUploadReceiptResponse:
        return cls.model_validate(receipt.to_dict())


class UploadedProgressReportResponse(StrictDTO):
    receipt_id: str
    project_id: str
    workflow_instance_id: str
    package_id: str
    package_checksum: str
    report_id: str
    report_checksum: str
    report_schema_version: str
    original_report_checksum: str
    original_report_size: int
    original_report_media_type: str
    envelope_checksum: str
    uploaded_at: str
    received_at: str
    uploader_type: str
    client_version: str
    source_path_hint: str
    validation_status: str
    validation_errors: list[str]
    validation_warnings: list[str]
    chain_state: str
    accepted_for_projection: bool
    normalized_record: dict[str, Any] | None

    @classmethod
    def from_contract(
        cls,
        report: UploadedProgressReport,
    ) -> UploadedProgressReportResponse:
        payload = report.to_dict()
        payload.pop("original_storage_key")
        return cls.model_validate(payload)


class ProjectProgressResponse(StrictDTO):
    schema_version: str
    project_id: str
    package_id: str
    package_schema_version: str | None
    package_checksum: str
    workflow_id: str
    workflow_version: str
    latest_accepted_report_id: str
    latest_accepted_report_checksum: str
    latest_execution_round: int
    latest_status: str
    completed_work_summary: list[str]
    current_state_summary: str
    next_recommended_action: str
    output_artifacts: list[dict[str, Any]]
    warning_count: int
    error_count: int
    unresolved_question_count: int
    harness_type: str
    latest_local_execution_timestamp: str
    latest_upload_timestamp: str
    chain_state: str
    legacy_warning_state: bool
    projection_checksum: str

    @classmethod
    def from_contract(
        cls,
        projection: ProjectProgressProjection,
    ) -> ProjectProgressResponse:
        return cls.model_validate(projection.to_dict())


class WorkflowInstanceProgressResponse(StrictDTO):
    schema_version: str
    project_id: str
    workflow_instance_id: str
    workflow_definition_id: str
    workflow_definition_version: str
    core_capability_maturity: str
    workflow_display_name: str
    instance_display_name: str
    lifecycle: str
    desired_state: str
    capsule_id: str | None
    capsule_version: str | None
    research_status: str
    latest_report_id: str | None
    latest_report_checksum: str | None
    latest_execution_round: int | None
    latest_summary: str | None
    next_recommended_action: str | None
    artifact_metadata: list[dict[str, Any]]
    report_count: int
    first_activity_at: str | None
    latest_activity_at: str | None
    installation_state: str
    installation_manifest_revision: int | None
    sync_uncertainty: str


class ProjectWorkflowProgressResponse(StrictDTO):
    schema_version: str
    project_id: str
    project_name: str
    research_topic: str
    manifest_revision: int
    cloud_observed_at: str
    active_workflow_count: int
    retired_workflow_count: int
    total_progress_report_count: int
    latest_project_activity_at: str | None
    status_counts: dict[str, int]
    instances: list[WorkflowInstanceProgressResponse]
    history: list[UploadedProgressReportResponse]
    history_offset: int
    history_limit: int
    history_total: int
    has_more_history: bool
    dependency_edges: list[dict[str, Any]]
    # V0.x Literature Search compatibility projection. New clients use
    # ``instances``; these additive fields keep the accepted result view alive.
    package_id: str | None = None
    package_schema_version: str | None = None
    package_checksum: str | None = None
    workflow_id: str | None = None
    workflow_version: str | None = None
    latest_accepted_report_id: str | None = None
    latest_accepted_report_checksum: str | None = None
    latest_execution_round: int | None = None
    latest_status: str | None = None
    completed_work_summary: list[str] = Field(default_factory=list)
    current_state_summary: str | None = None
    next_recommended_action: str | None = None
    output_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    warning_count: int = 0
    error_count: int = 0
    unresolved_question_count: int = 0
    harness_type: str | None = None
    latest_local_execution_timestamp: str | None = None
    latest_upload_timestamp: str | None = None
    chain_state: str | None = None
    legacy_warning_state: bool = False
    projection_checksum: str | None = None

    @classmethod
    def from_contract(
        cls,
        projection: ProjectWorkflowProgressProjection,
        legacy_projection: ProjectProgressProjection | None = None,
    ) -> ProjectWorkflowProgressResponse:
        legacy = legacy_projection.to_dict() if legacy_projection is not None else {}
        legacy.pop("schema_version", None)
        legacy.pop("project_id", None)
        return cls(
            schema_version=projection.schema_version,
            project_id=projection.project_id,
            project_name=projection.project_name,
            research_topic=projection.research_topic,
            manifest_revision=projection.manifest_revision,
            cloud_observed_at=projection.cloud_observed_at,
            active_workflow_count=projection.active_workflow_count,
            retired_workflow_count=projection.retired_workflow_count,
            total_progress_report_count=projection.total_progress_report_count,
            latest_project_activity_at=projection.latest_project_activity_at,
            status_counts=dict(projection.status_counts),
            instances=[
                WorkflowInstanceProgressResponse.model_validate(item.to_dict())
                for item in projection.instances
            ],
            history=[
                UploadedProgressReportResponse.from_contract(item)
                for item in projection.history
            ],
            history_offset=projection.history_offset,
            history_limit=projection.history_limit,
            history_total=projection.history_total,
            has_more_history=projection.has_more_history,
            dependency_edges=[dict(item) for item in projection.dependency_edges],
            **legacy,
        )


class WorkflowInstanceProgressPageResponse(StrictDTO):
    schema_version: str = "reagent.workflow-instance-progress/v0.1"
    project_id: str
    workflow_instance_id: str
    projection: WorkflowInstanceProgressResponse
    history: list[UploadedProgressReportResponse]
    history_offset: int
    history_limit: int
    history_total: int
    has_more_history: bool

    @classmethod
    def from_contract(
        cls,
        projection: ProjectWorkflowProgressProjection,
        workflow_instance_id: str,
    ) -> WorkflowInstanceProgressPageResponse:
        instance = next(
            item
            for item in projection.instances
            if item.workflow_instance_id == workflow_instance_id
        )
        return cls(
            project_id=projection.project_id,
            workflow_instance_id=workflow_instance_id,
            projection=WorkflowInstanceProgressResponse.model_validate(
                instance.to_dict()
            ),
            history=[
                UploadedProgressReportResponse.from_contract(item)
                for item in projection.history
            ],
            history_offset=projection.history_offset,
            history_limit=projection.history_limit,
            history_total=projection.history_total,
            has_more_history=projection.has_more_history,
        )
