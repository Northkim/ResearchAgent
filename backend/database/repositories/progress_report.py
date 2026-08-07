"""SQLAlchemy persistence for immutable uploaded Progress Reports."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.database.orm import ProjectProgressProjectionORM, UploadedProgressReportORM
from backend.persistence.ports import DuplicateEntityError
from backend.progress_reports.contracts import (
    ChainState,
    ProjectProgressProjection,
    UploadedProgressReport,
    ValidationStatus,
    normalized_record_from_dict,
    projection_from_dict,
)
from backend.progress_reports.ports import ProgressReportRepository

from ._helpers import pending_instances


class SQLAlchemyProgressReportRepository(ProgressReportRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def lock_report_identity(self, report_id: str) -> None:
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:report_id, 0))"),
            {"report_id": report_id},
        )

    def append(self, report: UploadedProgressReport) -> None:
        row = next(
            (
                item
                for item in pending_instances(self.session, UploadedProgressReportORM)
                if item.receipt_id == report.receipt_id
            ),
            None,
        )
        if row is None:
            row = self.session.get(UploadedProgressReportORM, report.receipt_id)
        if row is not None:
            if self._to_domain(row) != report:
                raise DuplicateEntityError(
                    f"Progress receipt {report.receipt_id} has conflicting content"
                )
            return
        self.session.add(
            UploadedProgressReportORM(
                receipt_id=report.receipt_id,
                project_id=report.project_id,
                workflow_instance_id=report.workflow_instance_id,
                package_id=report.package_id,
                package_checksum=report.package_checksum,
                report_id=report.report_id,
                report_checksum=report.report_checksum,
                report_schema_version=report.report_schema_version,
                original_report_checksum=report.original_report_checksum,
                original_report_size=report.original_report_size,
                original_report_media_type=report.original_report_media_type,
                original_storage_key=report.original_storage_key,
                envelope_checksum=report.envelope_checksum,
                uploaded_at=_parse_time(report.uploaded_at),
                received_at=_parse_time(report.received_at),
                uploader_type=report.uploader_type,
                client_version=report.client_version,
                source_path_hint=report.source_path_hint,
                validation_status=report.validation_status.value,
                validation_errors_json=list(report.validation_errors),
                validation_warnings_json=list(report.validation_warnings),
                chain_state=report.chain_state.value,
                accepted_for_projection=report.accepted_for_projection,
                normalized_record_json=(
                    report.normalized_record.to_dict()
                    if report.normalized_record is not None
                    else None
                ),
            )
        )

    def get_receipt(self, receipt_id: str) -> UploadedProgressReport | None:
        row = next(
            (
                item
                for item in pending_instances(self.session, UploadedProgressReportORM)
                if item.receipt_id == receipt_id
            ),
            None,
        )
        if row is None:
            row = self.session.get(UploadedProgressReportORM, receipt_id)
        return self._to_domain(row) if row is not None else None

    def find_exact(
        self,
        *,
        project_id: str,
        workflow_instance_id: str,
        package_id: str,
        package_checksum: str,
        report_id: str,
        report_checksum: str,
        original_report_checksum: str,
    ) -> UploadedProgressReport | None:
        statement = select(UploadedProgressReportORM).where(
            UploadedProgressReportORM.project_id == project_id,
            UploadedProgressReportORM.workflow_instance_id == workflow_instance_id,
            UploadedProgressReportORM.package_id == package_id,
            UploadedProgressReportORM.package_checksum == package_checksum,
            UploadedProgressReportORM.report_id == report_id,
            UploadedProgressReportORM.report_checksum == report_checksum,
            UploadedProgressReportORM.original_report_checksum
            == original_report_checksum,
        )
        matches = list(self.session.scalars(statement))
        matches.extend(
            row for row in pending_instances(self.session, UploadedProgressReportORM)
            if row.project_id == project_id
            and row.workflow_instance_id == workflow_instance_id
            and row.package_id == package_id
            and row.package_checksum == package_checksum
            and row.report_id == report_id
            and row.report_checksum == report_checksum
            and row.original_report_checksum == original_report_checksum
            and row not in matches
        )
        return self._to_domain(min(matches, key=lambda row: row.receipt_id)) if matches else None

    def list_for_project(
        self,
        project_id: str,
        *,
        package_id: str | None = None,
        workflow_instance_id: str | None = None,
    ) -> tuple[UploadedProgressReport, ...]:
        statement = select(UploadedProgressReportORM).where(
            UploadedProgressReportORM.project_id == project_id
        )
        if package_id is not None:
            statement = statement.where(UploadedProgressReportORM.package_id == package_id)
        if workflow_instance_id is not None:
            statement = statement.where(
                UploadedProgressReportORM.workflow_instance_id == workflow_instance_id
            )
        rows = list(self.session.scalars(statement))
        rows.extend(
            row for row in pending_instances(self.session, UploadedProgressReportORM)
            if row.project_id == project_id
            and (package_id is None or row.package_id == package_id)
            and (
                workflow_instance_id is None
                or row.workflow_instance_id == workflow_instance_id
            )
            and row not in rows
        )
        rows.sort(key=lambda row: (row.received_at, row.receipt_id))
        return tuple(self._to_domain(row) for row in rows)

    def list_by_report_id(self, report_id: str) -> tuple[UploadedProgressReport, ...]:
        rows = list(self.session.scalars(
            select(UploadedProgressReportORM).where(
                UploadedProgressReportORM.report_id == report_id
            )
        ))
        rows.extend(
            row for row in pending_instances(self.session, UploadedProgressReportORM)
            if row.report_id == report_id and row not in rows
        )
        rows.sort(key=lambda row: (row.received_at, row.receipt_id))
        return tuple(self._to_domain(row) for row in rows)

    def list_by_original_checksum(
        self,
        original_report_checksum: str,
    ) -> tuple[UploadedProgressReport, ...]:
        rows = list(self.session.scalars(
            select(UploadedProgressReportORM).where(
                UploadedProgressReportORM.original_report_checksum
                == original_report_checksum
            )
        ))
        rows.extend(
            row for row in pending_instances(self.session, UploadedProgressReportORM)
            if row.original_report_checksum == original_report_checksum
            and row not in rows
        )
        rows.sort(key=lambda row: (row.received_at, row.receipt_id))
        return tuple(self._to_domain(row) for row in rows)

    def save_projection(self, projection: ProjectProgressProjection) -> None:
        key = (
            projection.project_id,
            projection.package_id,
            projection.workflow_id,
            projection.workflow_version,
        )
        row = self.session.get(ProjectProgressProjectionORM, key)
        if row is None:
            row = next(
                (
                    item
                    for item in pending_instances(
                        self.session, ProjectProgressProjectionORM
                    )
                    if (
                        item.project_id,
                        item.package_id,
                        item.workflow_id,
                        item.workflow_version,
                    )
                    == key
                ),
                None,
            )
        values = projection.to_dict()
        if row is None:
            self.session.add(
                ProjectProgressProjectionORM(
                    project_id=projection.project_id,
                    package_id=projection.package_id,
                    workflow_id=projection.workflow_id,
                    workflow_version=projection.workflow_version,
                    package_checksum=projection.package_checksum,
                    latest_report_id=projection.latest_accepted_report_id,
                    latest_report_checksum=projection.latest_accepted_report_checksum,
                    latest_execution_round=projection.latest_execution_round,
                    latest_status=projection.latest_status.value,
                    chain_state=projection.chain_state.value,
                    projection_checksum=projection.projection_checksum,
                    projection_json=values,
                    updated_at=_parse_time(projection.latest_upload_timestamp),
                )
            )
            return
        row.package_checksum = projection.package_checksum
        row.latest_report_id = projection.latest_accepted_report_id
        row.latest_report_checksum = projection.latest_accepted_report_checksum
        row.latest_execution_round = projection.latest_execution_round
        row.latest_status = projection.latest_status.value
        row.chain_state = projection.chain_state.value
        row.projection_checksum = projection.projection_checksum
        row.projection_json = values
        row.updated_at = _parse_time(projection.latest_upload_timestamp)

    def get_projection(
        self,
        *,
        project_id: str,
        package_id: str,
        workflow_id: str,
        workflow_version: str,
    ) -> ProjectProgressProjection | None:
        key = (project_id, package_id, workflow_id, workflow_version)
        row = self.session.get(ProjectProgressProjectionORM, key)
        if row is None:
            row = next(
                (
                    item
                    for item in pending_instances(
                        self.session, ProjectProgressProjectionORM
                    )
                    if (
                        item.project_id,
                        item.package_id,
                        item.workflow_id,
                        item.workflow_version,
                    )
                    == key
                ),
                None,
            )
        return projection_from_dict(row.projection_json) if row is not None else None

    def _all_rows(self) -> list[UploadedProgressReportORM]:
        rows = list(self.session.scalars(select(UploadedProgressReportORM)))
        rows.extend(
            row
            for row in pending_instances(self.session, UploadedProgressReportORM)
            if row not in rows
        )
        return rows

    @staticmethod
    def _to_domain(row: UploadedProgressReportORM) -> UploadedProgressReport:
        return UploadedProgressReport(
            receipt_id=row.receipt_id,
            project_id=row.project_id,
            workflow_instance_id=row.workflow_instance_id,
            package_id=row.package_id,
            package_checksum=row.package_checksum,
            report_id=row.report_id,
            report_checksum=row.report_checksum,
            report_schema_version=row.report_schema_version,
            original_report_checksum=row.original_report_checksum,
            original_report_size=row.original_report_size,
            original_report_media_type=row.original_report_media_type,
            original_storage_key=row.original_storage_key,
            envelope_checksum=row.envelope_checksum,
            uploaded_at=_format_time(row.uploaded_at),
            received_at=_format_time(row.received_at),
            uploader_type=row.uploader_type,
            client_version=row.client_version,
            source_path_hint=row.source_path_hint,
            validation_status=ValidationStatus(row.validation_status),
            validation_errors=tuple(row.validation_errors_json),
            validation_warnings=tuple(row.validation_warnings_json),
            chain_state=ChainState(row.chain_state),
            accepted_for_projection=row.accepted_for_projection,
            normalized_record=(
                normalized_record_from_dict(row.normalized_record_json)
                if row.normalized_record_json is not None
                else None
            ),
        )


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
