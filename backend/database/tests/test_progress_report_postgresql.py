"""PostgreSQL reload evidence for append-only cloud Progress Reports."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

from backend.database import SQLAlchemyUnitOfWork
from backend.progress_reports.service import ProgressReportService
from backend.progress_reports.tests.factories import (
    native_report,
    report_bytes,
    upload_envelope,
    with_same_id_and_changed_content,
)
from backend.project_workspaces.legacy import legacy_workflow_instance_id
from backend.research.adapters import LocalFilesystemArtifactStorage
from backend.local_projects.contracts import LocalPackageMetadata, LocalProject
from backend.project_workspaces.application import ProjectWorkspaceApplicationService
from backend.progress_reports.tests.factories import HASH_A, HASH_B


def _service(unit_of_work, storage):
    return ProgressReportService(
        repository=unit_of_work.progress_reports,
        content_storage=storage,
        commit_callback=unit_of_work.commit,
        workflow_identity_resolver=lambda envelope, normalized, requested: (
            requested or legacy_workflow_instance_id(envelope.project_id)
        ),
        clock=lambda: datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
    )


def test_postgresql_progress_history_and_projection_reload(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
    tmp_path,
) -> None:
    storage = LocalFilesystemArtifactStorage(tmp_path / "progress-originals")
    report = native_report()
    _seed_progress_project(sql_uow_factory, report)
    first_scope = sql_uow_factory()
    receipt = _service(first_scope, storage).upload(upload_envelope(report))
    first_scope.close()

    restarted_scope = sql_uow_factory()
    restarted = _service(restarted_scope, storage)
    stored = restarted.get_report(
        project_id=report.project_id,
        report_id=report.report_id,
    )
    projection = restarted.get_projection(
        project_id=report.project_id,
        package_id=report.package_id,
    )
    replay = restarted.upload(upload_envelope(report))

    assert stored is not None
    assert restarted.read_original(stored) == report_bytes(report)
    assert projection is not None and projection.latest_execution_round == 1
    assert replay.receipt_id == receipt.receipt_id
    assert replay.idempotent_replay
    assert len(restarted.list_reports(project_id=report.project_id)) == 1
    restarted_scope.close()


def test_postgresql_concurrent_identical_retry_has_one_canonical_row(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
    tmp_path,
) -> None:
    report = native_report()
    _seed_progress_project(sql_uow_factory, report)
    storage = LocalFilesystemArtifactStorage(tmp_path / "concurrent-identical")
    barrier = Barrier(2)

    def upload_once():
        scope = sql_uow_factory()
        try:
            barrier.wait(timeout=5)
            return _service(scope, storage).upload(upload_envelope(report))
        finally:
            scope.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        receipts = tuple(executor.map(lambda _: upload_once(), range(2)))
    scope = sql_uow_factory()
    try:
        rows = scope.progress_reports.list_for_project(report.project_id)
    finally:
        scope.close()
    assert len(rows) == 1
    assert {item.receipt_id for item in receipts} == {rows[0].receipt_id}
    assert sorted(item.idempotent_replay for item in receipts) == [False, True]


def test_postgresql_concurrent_same_report_id_different_payload_fails_closed(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
    tmp_path,
) -> None:
    report = native_report()
    conflict = with_same_id_and_changed_content(report)
    _seed_progress_project(sql_uow_factory, report)
    storage = LocalFilesystemArtifactStorage(tmp_path / "concurrent-conflict")
    barrier = Barrier(2)

    def upload_once(candidate):
        scope = sql_uow_factory()
        try:
            barrier.wait(timeout=5)
            receipt = _service(scope, storage).upload(upload_envelope(candidate))
            return (
                "accepted" if receipt.accepted_for_projection else "conflict",
                receipt.report_checksum,
            )
        finally:
            scope.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = tuple(executor.map(upload_once, (report, conflict)))
    scope = sql_uow_factory()
    try:
        rows = scope.progress_reports.list_for_project(report.project_id)
    finally:
        scope.close()
    assert sorted(item[0] for item in outcomes) == ["accepted", "conflict"]
    assert len(rows) == 2
    assert {row.report_id for row in rows} == {report.report_id}
    assert sum(row.accepted_for_projection for row in rows) == 1


def _seed_progress_project(sql_uow_factory, report) -> None:
    seed_scope = sql_uow_factory()
    project = LocalProject(
        project_id=report.project_id,
        name="Fictional PostgreSQL progress",
        research_topic="Fictional public topic",
        selected_workflow="LITERATURE_SEARCH",
        created_at="2026-08-03T08:00:00Z",
        updated_at="2026-08-03T08:00:00Z",
        current_package=LocalPackageMetadata(
            package_id=report.package_id,
            package_schema_version="workflow-package/v0.1",
            package_checksum=report.package_checksum,
            manifest_checksum=HASH_A,
            zip_checksum=HASH_B,
            workflow_id=report.workflow_id,
            workflow_version=report.workflow_version,
            workflow_checksum=report.workflow_checksum,
            archive_storage_key="fictional/package.zip",
            file_count=1,
            package_size_bytes=1,
            generated_at="2026-08-03T08:00:00Z",
        ),
    )
    seed_scope.local_projects.add(project)
    ProjectWorkspaceApplicationService(
        unit_of_work=seed_scope,
        clock=lambda: datetime(2026, 8, 3, 8, 0, tzinfo=UTC),
    ).initialize_project(project)
    seed_scope.commit()
    seed_scope.close()
