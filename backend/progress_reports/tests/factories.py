"""Wholly fictional Progress Report acceptance fixtures."""

from __future__ import annotations

from dataclasses import replace

from backend.progress_reports.contracts import (
    ACCEPTED_REPORT_MEDIA_TYPE,
    EXPERIMENTAL_DECLARATION,
    PROGRESS_REPORT_SCHEMA_V1,
    OutputArtifactReference,
    PinReference,
    ProgressReportUploadEnvelope,
    ProgressReportV2,
    ProgressStatus,
)
from backend.workflow_packages.serialization import canonical_hash, canonical_json

HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64
HASH_C = "sha256:" + "c" * 64
PACKAGE_ID = "fictional-literature-package-v0.2"
PROJECT_ID = "project-11111111111111111111111111111111"
WORKFLOW_ID = "literature-search-local-experimental"
WORKFLOW_VERSION = "0.3.0"


def native_report(
    *,
    execution_round: int = 1,
    previous: ProgressReportV2 | None = None,
    status: ProgressStatus = ProgressStatus.IN_PROGRESS,
    context_before_checksum: str = HASH_A,
    context_after_checksum: str = HASH_B,
    continuation_reason: str | None = None,
    current_state: str = "Fictional catalog screening is recorded.",
    project_id: str = PROJECT_ID,
    package_id: str = PACKAGE_ID,
    package_checksum: str = HASH_C,
    workflow_id: str = WORKFLOW_ID,
    workflow_version: str = WORKFLOW_VERSION,
    workflow_checksum: str = HASH_A,
) -> ProgressReportV2:
    return ProgressReportV2.create(
        package_id=package_id,
        package_schema_version="workflow-package/v0.1",
        package_checksum=package_checksum,
        project_id=project_id,
        workflow_id=workflow_id,
        workflow_version=workflow_version,
        workflow_checksum=workflow_checksum,
        execution_round=execution_round,
        harness_type="codex",
        harness_version="fictional-test-harness/1.0",
        harness_session_id=f"fictional-session-{execution_round}",
        previous_report_id=previous.report_id if previous is not None else None,
        previous_report_checksum=(
            previous.report_checksum if previous is not None else None
        ),
        started_at=f"2026-08-03T0{execution_round}:00:00Z",
        completed_at=f"2026-08-03T0{execution_round}:10:00Z",
        status=status,
        completed_work=(f"Recorded fictional round {execution_round}.",),
        current_state=current_state,
        next_recommended_action="Review the local fictional outputs.",
        continuation_reason=continuation_reason,
        output_artifacts=(
            OutputArtifactReference(
                relative_path="outputs/fictional_report.md",
                artifact_kind="FICTIONAL_REPORT",
                media_type="text/markdown",
                checksum=HASH_B,
                size=42,
            ),
        ),
        context_before_checksum=context_before_checksum,
        context_after_checksum=context_after_checksum,
        warnings=(),
        errors=(),
        unresolved_questions=(),
        continuation_instructions=("Read the next local request if one exists.",),
        skill_pins=(
            PinReference(
                pin_type="SKILL",
                identity="fictional-literature-skill",
                version="0.2.0",
                checksum=HASH_A,
            ),
        ),
        template_pins=(
            PinReference(
                pin_type="TEMPLATE",
                identity="fictional-package-template",
                version="0.2.0",
                checksum=HASH_C,
            ),
        ),
        generated_at=f"2026-08-03T0{execution_round}:10:00Z",
        experimental_declaration=EXPERIMENTAL_DECLARATION,
    )


def report_bytes(report: ProgressReportV2) -> bytes:
    return (canonical_json(report) + "\n").encode("utf-8")


def upload_envelope(
    report: ProgressReportV2,
    *,
    content: bytes | None = None,
    project_id: str | None = None,
    package_id: str | None = None,
    package_checksum: str | None = None,
) -> ProgressReportUploadEnvelope:
    return ProgressReportUploadEnvelope.create(
        original_report_bytes=content if content is not None else report_bytes(report),
        project_id=project_id or report.project_id,
        package_id=package_id or report.package_id,
        package_checksum=package_checksum or report.package_checksum,
        report_schema_version=report.schema_version,
        report_id=report.report_id,
        report_checksum=report.report_checksum,
        original_report_media_type=ACCEPTED_REPORT_MEDIA_TYPE,
        uploaded_at="2026-08-03T09:00:00Z",
        uploader_type="local-cli",
        client_version="fictional-client/0.2.0",
        source_path_hint="memory/progress/reports/fictional-round.json",
        context_snapshot_metadata=None,
    )


def legacy_report_bytes() -> bytes:
    payload = {
        "report_id": "round-001",
        "package_id": "fictional-legacy-package-v0.1",
        "package_checksum": HASH_C,
        "project_identity": PROJECT_ID,
        "workflow_id": "fictional-legacy-search",
        "workflow_version": "0.1.0",
        "skill_versions": ["fictional-search@0.1.0"],
        "template_version": "0.1.0",
        "execution_round": 1,
        "harness_identity": "Codex fictional session",
        "started_at": "2026-08-01T01:00:00Z",
        "completed_at": "2026-08-01T01:05:00Z",
        "status": "COMPLETED",
        "completed_work": ["Recorded fictional legacy results."],
        "current_state": "Fictional legacy task complete.",
        "next_recommended_action": "Upload the immutable report.",
        "output_files": [
            {
                "relative_path": "outputs/fictional_report.md",
                "checksum": HASH_B,
            }
        ],
        "context_checksum": HASH_A,
        "warnings": [],
        "errors": [],
        "unresolved_questions": [],
        "continuation_instructions": ["Read local context."],
        "previous_report_id": None,
        "schema_version": PROGRESS_REPORT_SCHEMA_V1,
        "report_checksum": None,
    }
    payload["report_checksum"] = canonical_hash(payload)
    return (canonical_json(payload) + "\n").encode("utf-8")


def with_same_id_and_changed_content(report: ProgressReportV2) -> ProgressReportV2:
    changed = replace(
        report,
        current_state="A conflicting fictional state.",
    ).with_computed_identity()
    return replace(changed, report_id=report.report_id)
