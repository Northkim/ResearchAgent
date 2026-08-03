"""PostgreSQL reload evidence for append-only cloud Progress Reports."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from backend.database import SQLAlchemyUnitOfWork
from backend.progress_reports.service import ProgressReportService
from backend.progress_reports.tests.factories import native_report, report_bytes, upload_envelope
from backend.research.adapters import LocalFilesystemArtifactStorage


def _service(unit_of_work, storage):
    return ProgressReportService(
        repository=unit_of_work.progress_reports,
        content_storage=storage,
        commit_callback=unit_of_work.commit,
        clock=lambda: datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
    )


def test_postgresql_progress_history_and_projection_reload(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
    tmp_path,
) -> None:
    storage = LocalFilesystemArtifactStorage(tmp_path / "progress-originals")
    report = native_report()
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
