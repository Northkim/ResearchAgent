"""Deterministic cloud progress projection without research inference."""

from __future__ import annotations

from html import escape

from .contracts import (
    PROGRESS_REPORT_SCHEMA_V1,
    PROJECTION_SCHEMA_VERSION,
    ZERO_HASH,
    ProjectProgressProjection,
    UploadedProgressReport,
)


def build_projection(
    history: tuple[UploadedProgressReport, ...],
) -> ProjectProgressProjection | None:
    accepted = tuple(
        item
        for item in history
        if item.accepted_for_projection and item.normalized_record is not None
    )
    if not accepted:
        return None
    accepted = tuple(
        sorted(
            accepted,
            key=lambda item: (
                item.normalized_record.execution_round,  # type: ignore[union-attr]
                item.normalized_record.completed_at,  # type: ignore[union-attr]
                item.report_id,
            ),
        )
    )
    latest_upload = accepted[-1]
    latest = latest_upload.normalized_record
    assert latest is not None
    completed: list[str] = []
    seen: set[str] = set()
    for upload in accepted:
        record = upload.normalized_record
        assert record is not None
        for item in record.completed_work:
            if item not in seen:
                completed.append(escape(item))
                seen.add(item)
    projection = ProjectProgressProjection(
        schema_version=PROJECTION_SCHEMA_VERSION,
        project_id=latest.project_id,
        package_id=latest.package_id,
        package_schema_version=latest.package_schema_version,
        package_checksum=latest.package_checksum,
        workflow_id=latest.workflow_id,
        workflow_version=latest.workflow_version,
        latest_accepted_report_id=latest.report_id,
        latest_accepted_report_checksum=latest.report_checksum,
        latest_execution_round=latest.execution_round,
        latest_status=latest.status,
        completed_work_summary=tuple(completed),
        current_state_summary=escape(latest.current_state),
        next_recommended_action=escape(latest.next_recommended_action),
        output_artifacts=latest.output_artifacts,
        warning_count=len(latest.warnings),
        error_count=len(latest.errors),
        unresolved_question_count=len(latest.unresolved_questions),
        harness_type=latest.harness_type,
        latest_local_execution_timestamp=latest.completed_at,
        latest_upload_timestamp=latest_upload.received_at,
        chain_state=latest.chain_state,
        legacy_warning_state=any(
            item.normalized_record is not None
            and item.normalized_record.source_schema_version == PROGRESS_REPORT_SCHEMA_V1
            for item in accepted
        ),
        projection_checksum=ZERO_HASH,
    )
    return projection.with_computed_checksum()
