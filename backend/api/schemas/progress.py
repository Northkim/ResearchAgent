"""Strict DTOs for explicit local Progress Report upload and cloud progress."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from backend.progress_reports.contracts import (
    ProgressReportUploadEnvelope,
    ProgressUploadReceipt,
    ProjectProgressProjection,
    UploadedProgressReport,
)

from .common import StrictDTO


class ProgressReportUploadRequest(StrictDTO):
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

    def to_contract(self) -> ProgressReportUploadEnvelope:
        return ProgressReportUploadEnvelope.from_dict(self.model_dump())


class ProgressUploadReceiptResponse(StrictDTO):
    receipt_id: str
    project_id: str
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
