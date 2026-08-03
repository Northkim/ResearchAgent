from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.progress_reports.contracts import ChainState, ValidationStatus
from backend.progress_reports.contracts import (
    ACCEPTED_REPORT_MEDIA_TYPE,
    PROGRESS_REPORT_SCHEMA_V1,
    ProgressReportUploadEnvelope,
)
from backend.progress_reports.service import ProgressReportService
from backend.progress_reports.security import UnsafeProgressReportError
from backend.research.adapters import LocalFilesystemArtifactStorage

from .factories import (
    HASH_B,
    legacy_report_bytes,
    native_report,
    report_bytes,
    upload_envelope,
    with_same_id_and_changed_content,
)


def _service(database, storage):
    unit_of_work = InMemoryUnitOfWork(database)
    return ProgressReportService(
        repository=unit_of_work.progress_reports,
        content_storage=storage,
        commit_callback=unit_of_work.commit,
        clock=lambda: datetime(2026, 8, 3, 10, 0, tzinfo=UTC),
    )


def test_upload_retains_original_and_reupload_is_idempotent(tmp_path) -> None:
    database = InMemoryDatabase()
    storage = LocalFilesystemArtifactStorage(tmp_path / "artifacts")
    report = native_report()
    envelope = upload_envelope(report)
    service = _service(database, storage)

    first = service.upload(envelope)
    replay = _service(database, storage).upload(envelope)
    stored = _service(database, storage).get_report(
        project_id=report.project_id,
        report_id=report.report_id,
    )

    assert first.validation_status is ValidationStatus.ACCEPTED
    assert first.accepted_for_projection
    assert not first.idempotent_replay
    assert replay.idempotent_replay
    assert replay.receipt_id == first.receipt_id
    assert replay.receipt_checksum == first.receipt_checksum
    assert first.verify_checksum()
    assert len(database.progress_reports) == 1
    assert stored is not None
    assert _service(database, storage).read_original(stored) == report_bytes(report)


def test_legacy_v1_upload_retains_bytes_and_projects_with_explicit_warnings(
    tmp_path,
) -> None:
    import json

    database = InMemoryDatabase()
    storage = LocalFilesystemArtifactStorage(tmp_path / "artifacts")
    content = legacy_report_bytes()
    payload = json.loads(content)
    envelope = ProgressReportUploadEnvelope.create(
        original_report_bytes=content,
        project_id=payload["project_identity"],
        package_id=payload["package_id"],
        package_checksum=payload["package_checksum"],
        report_schema_version=PROGRESS_REPORT_SCHEMA_V1,
        report_id=payload["report_id"],
        report_checksum=payload["report_checksum"],
        original_report_media_type=ACCEPTED_REPORT_MEDIA_TYPE,
        uploaded_at="2026-08-03T09:00:00Z",
        uploader_type="local-cli",
        client_version="fictional-client/0.2.0",
        source_path_hint="memory/progress/reports/round-001.json",
        context_snapshot_metadata=None,
    )
    service = _service(database, storage)

    receipt = service.upload(envelope)
    stored = service.get_report(
        project_id=payload["project_identity"],
        report_id=payload["report_id"],
    )
    projection = service.get_projection(project_id=payload["project_identity"])

    assert receipt.validation_status is ValidationStatus.ACCEPTED
    assert receipt.chain_state is ChainState.LEGACY_CHAIN_WITH_WARNINGS
    assert receipt.warning_count > 0
    assert stored is not None and service.read_original(stored) == content
    assert stored.normalized_record is not None
    assert stored.normalized_record.context_before_checksum is None
    assert stored.normalized_record.context_after_checksum is None
    assert projection is not None and projection.legacy_warning_state


def test_valid_second_round_rebuilds_projection_after_restart(tmp_path) -> None:
    database = InMemoryDatabase()
    storage = LocalFilesystemArtifactStorage(tmp_path / "artifacts")
    first = native_report(context_after_checksum=HASH_B)
    second = native_report(
        execution_round=2,
        previous=first,
        context_before_checksum=HASH_B,
    )
    service = _service(database, storage)
    service.upload(upload_envelope(first))
    service.upload(upload_envelope(second))

    restarted = _service(database, storage)
    projection = restarted.get_projection(
        project_id=first.project_id,
        package_id=first.package_id,
    )

    assert projection is not None
    assert projection.latest_execution_round == 2
    assert projection.latest_accepted_report_id == second.report_id
    assert projection.completed_work_summary == (
        "Recorded fictional round 1.",
        "Recorded fictional round 2.",
    )
    assert projection.verify_checksum()
    assert len(restarted.list_reports(project_id=first.project_id)) == 2


def test_conflicting_same_report_id_is_retained_but_does_not_replace_projection(
    tmp_path,
) -> None:
    database = InMemoryDatabase()
    storage = LocalFilesystemArtifactStorage(tmp_path / "artifacts")
    original = native_report()
    conflict = with_same_id_and_changed_content(original)
    service = _service(database, storage)
    accepted = service.upload(upload_envelope(original))
    rejected = service.upload(upload_envelope(conflict))
    projection = service.get_projection(
        project_id=original.project_id,
        package_id=original.package_id,
    )

    assert accepted.accepted_for_projection
    assert rejected.validation_status is ValidationStatus.REJECTED
    assert rejected.chain_state is ChainState.IDENTITY_CONFLICT
    assert not rejected.accepted_for_projection
    assert len(database.progress_reports) == 2
    assert projection is not None
    assert projection.latest_accepted_report_id == original.report_id


def test_wrong_identity_and_invalid_checksum_are_retained_without_projection(tmp_path) -> None:
    database = InMemoryDatabase()
    storage = LocalFilesystemArtifactStorage(tmp_path / "artifacts")
    report = native_report()
    wrong_project = upload_envelope(report, project_id="wrong-fictional-project")
    invalid_payload = {**report.to_dict(), "report_checksum": "sha256:" + "0" * 64}
    import json

    invalid_bytes = (json.dumps(invalid_payload, sort_keys=True) + "\n").encode()
    invalid_checksum = upload_envelope(report, content=invalid_bytes)
    service = _service(database, storage)

    wrong_receipt = service.upload(wrong_project)
    invalid_receipt = service.upload(invalid_checksum)

    assert wrong_receipt.validation_status is ValidationStatus.REJECTED
    assert invalid_receipt.validation_status is ValidationStatus.REJECTED
    assert len(database.progress_reports) == 2
    assert service.get_projection(project_id=report.project_id) is None


def test_same_bytes_cannot_be_rebound_to_another_package_identity(tmp_path) -> None:
    database = InMemoryDatabase()
    storage = LocalFilesystemArtifactStorage(tmp_path / "artifacts")
    report = native_report()
    service = _service(database, storage)
    service.upload(upload_envelope(report))

    incompatible = upload_envelope(
        report,
        package_checksum="sha256:" + "d" * 64,
    )
    receipt = service.upload(incompatible)

    assert receipt.validation_status is ValidationStatus.REJECTED
    assert receipt.chain_state is ChainState.IDENTITY_CONFLICT
    assert len(database.progress_reports) == 2


def test_same_report_id_with_different_exact_bytes_is_a_retained_conflict(tmp_path) -> None:
    import json

    database = InMemoryDatabase()
    storage = LocalFilesystemArtifactStorage(tmp_path / "artifacts")
    report = native_report()
    service = _service(database, storage)
    service.upload(upload_envelope(report))
    reserialized = json.dumps(report.to_dict(), indent=2, ensure_ascii=False).encode()

    receipt = service.upload(upload_envelope(report, content=reserialized))

    assert receipt.validation_status is ValidationStatus.REJECTED
    assert receipt.chain_state is ChainState.IDENTITY_CONFLICT
    assert len(database.progress_reports) == 2


def test_projection_escapes_benign_untrusted_display_text(tmp_path) -> None:
    database = InMemoryDatabase()
    storage = LocalFilesystemArtifactStorage(tmp_path / "artifacts")
    report = native_report(current_state="<b>Fictional state</b>")
    service = _service(database, storage)
    service.upload(upload_envelope(report))

    projection = service.get_projection(
        project_id=report.project_id,
        package_id=report.package_id,
    )

    assert projection is not None
    assert projection.current_state_summary == "&lt;b&gt;Fictional state&lt;/b&gt;"


def test_secret_like_report_is_rejected_before_original_storage(tmp_path) -> None:
    database = InMemoryDatabase()
    storage = LocalFilesystemArtifactStorage(tmp_path / "artifacts")
    report = native_report()
    unsafe = report_bytes(report).replace(
        b"Fictional catalog screening is recorded.",
        b"sk-proj-fictionalsecret123",
    )
    envelope = upload_envelope(report, content=unsafe)

    with pytest.raises(UnsafeProgressReportError, match="secret-like"):
        _service(database, storage).upload(envelope)

    assert database.progress_reports == {}
    assert not tuple((tmp_path / "artifacts").rglob("*.json"))
