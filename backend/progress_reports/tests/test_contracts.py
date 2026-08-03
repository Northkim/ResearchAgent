from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from backend.progress_reports.contracts import (
    MAX_REPORT_BYTES,
    ProgressReportUploadEnvelope,
    ProgressReportV2,
    ProgressStatus,
)

from .factories import HASH_A, HASH_B, native_report, upload_envelope


def test_v2_identity_is_stable_non_cyclic_and_sensitive_to_content() -> None:
    first = native_report()
    second = native_report()
    changed = native_report(current_state="Another fictional state.")

    assert first == second
    assert first.verify_identity()
    assert first.report_id == second.report_id
    assert first.report_checksum == second.report_checksum
    assert first.report_id != changed.report_id
    assert first.report_checksum != changed.report_checksum
    assert first.report_content_checksum != changed.report_content_checksum


def test_identity_verification_rejects_each_tampered_identity_field() -> None:
    report = native_report()

    assert not replace(report, report_content_checksum=HASH_A).verify_identity()
    assert not replace(report, report_checksum=HASH_B).verify_identity()
    with pytest.raises(ValueError, match="identity or checksum"):
        ProgressReportV2.from_dict(
            {**report.to_dict(), "current_state": "Tampered fictional state."}
        )


def test_context_before_and_after_are_explicit_and_may_match_for_no_op() -> None:
    changed = native_report(
        context_before_checksum=HASH_A,
        context_after_checksum=HASH_B,
    )
    no_op = native_report(
        context_before_checksum=HASH_A,
        context_after_checksum=HASH_A,
    )

    assert changed.context_before_checksum != changed.context_after_checksum
    assert no_op.context_before_checksum == no_op.context_after_checksum
    assert "context_checksum" not in no_op.to_dict()


def test_contract_rejects_invalid_status_round_and_predecessor_pair() -> None:
    values = native_report().to_dict()
    values["status"] = "UNKNOWN"
    with pytest.raises(ValueError):
        ProgressReportV2.from_dict(values)

    with pytest.raises(ValueError, match="positive"):
        native_report(execution_round=0)

    report = native_report()
    with pytest.raises(ValueError, match="present together"):
        replace(report, previous_report_id="prv2-" + "1" * 64)


def test_nested_collections_and_contract_are_immutable() -> None:
    report = native_report()

    with pytest.raises(FrozenInstanceError):
        report.current_state = "mutated"  # type: ignore[misc]
    assert isinstance(report.completed_work, tuple)
    assert isinstance(report.output_artifacts, tuple)
    with pytest.raises(TypeError):
        report.completed_work[0] = "mutated"  # type: ignore[index]


def test_upload_envelope_checksum_media_type_size_and_metadata_are_strict() -> None:
    envelope = ProgressReportUploadEnvelope.create(
        original_report_bytes=b"{}",
        project_id="fictional-project",
        package_id="fictional-package",
        package_checksum=HASH_A,
        report_schema_version="progress-report/v0.2",
        report_id=native_report().report_id,
        report_checksum=HASH_B,
        original_report_media_type="application/json",
        uploaded_at="2026-08-03T09:00:00Z",
        uploader_type="local-cli",
        client_version="fictional/1.0",
        source_path_hint="memory/progress/reports/fictional.json",
        context_snapshot_metadata={"supplied": False},
    )

    assert envelope.verify_checksum()
    with pytest.raises(TypeError):
        envelope.context_snapshot_metadata["supplied"] = True  # type: ignore[index]
    with pytest.raises(ValueError, match="media type"):
        replace(envelope, original_report_media_type="text/plain")
    with pytest.raises(ValueError, match="size"):
        ProgressReportUploadEnvelope.create(
            original_report_bytes=b"x" * (MAX_REPORT_BYTES + 1),
            project_id="fictional-project",
            package_id="fictional-package",
            package_checksum=HASH_A,
            report_schema_version="progress-report/v0.2",
            report_id=native_report().report_id,
            report_checksum=HASH_B,
            original_report_media_type="application/json",
            uploaded_at="2026-08-03T09:00:00Z",
            uploader_type="local-cli",
            client_version="fictional/1.0",
            source_path_hint="memory/progress/reports/fictional.json",
            context_snapshot_metadata=None,
        )
    with pytest.raises(ValueError, match="checksum mismatch"):
        ProgressReportUploadEnvelope.from_dict(
            {**envelope.to_dict(), "client_version": "tampered/1.0"}
        )
