"""SQLAlchemy persistence for teacher-aligned local projects."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.orm import LocalProjectORM
from backend.local_projects import (
    LocalPackageMetadata,
    LocalProject,
    LocalProjectRepository,
)
from backend.persistence.ports import DuplicateEntityError

from ._helpers import pending_instances


class SQLAlchemyLocalProjectRepository(LocalProjectRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, project: LocalProject) -> None:
        if self.get(project.project_id) is not None:
            raise DuplicateEntityError(
                f"Local project {project.project_id} already exists"
            )
        self.session.add(self._to_row(project))

    def save(self, project: LocalProject) -> None:
        row = self._row(project.project_id)
        if row is None:
            raise ValueError("Local project does not exist")
        row.name = project.name
        row.research_topic = project.research_topic
        row.selected_workflow = project.selected_workflow
        row.updated_at = _parse_time(project.updated_at)
        package = project.current_package
        row.current_package_id = package.package_id if package else None
        row.current_package_schema_version = (
            package.package_schema_version if package else None
        )
        row.current_package_checksum = package.package_checksum if package else None
        row.current_manifest_checksum = package.manifest_checksum if package else None
        row.current_zip_checksum = package.zip_checksum if package else None
        row.current_workflow_id = package.workflow_id if package else None
        row.current_workflow_version = package.workflow_version if package else None
        row.current_workflow_checksum = package.workflow_checksum if package else None
        row.current_archive_storage_key = package.archive_storage_key if package else None
        row.current_package_file_count = package.file_count if package else None
        row.current_package_size_bytes = package.package_size_bytes if package else None
        row.current_package_generated_at = (
            _parse_time(package.generated_at) if package else None
        )

    def get(self, project_id: str) -> LocalProject | None:
        row = self._row(project_id)
        return self._to_domain(row) if row is not None else None

    def list_all(self) -> tuple[LocalProject, ...]:
        rows = list(self.session.scalars(select(LocalProjectORM)))
        rows.extend(
            row
            for row in pending_instances(self.session, LocalProjectORM)
            if row not in rows
        )
        rows.sort(key=lambda row: (row.updated_at, row.project_id), reverse=True)
        return tuple(self._to_domain(row) for row in rows)

    def _row(self, project_id: str) -> LocalProjectORM | None:
        pending = next(
            (
                row
                for row in pending_instances(self.session, LocalProjectORM)
                if row.project_id == project_id
            ),
            None,
        )
        return pending or self.session.get(LocalProjectORM, project_id)

    @staticmethod
    def _to_row(project: LocalProject) -> LocalProjectORM:
        package = project.current_package
        return LocalProjectORM(
            project_id=project.project_id,
            name=project.name,
            research_topic=project.research_topic,
            selected_workflow=project.selected_workflow,
            created_at=_parse_time(project.created_at),
            updated_at=_parse_time(project.updated_at),
            current_package_id=package.package_id if package else None,
            current_package_schema_version=(
                package.package_schema_version if package else None
            ),
            current_package_checksum=package.package_checksum if package else None,
            current_manifest_checksum=package.manifest_checksum if package else None,
            current_zip_checksum=package.zip_checksum if package else None,
            current_workflow_id=package.workflow_id if package else None,
            current_workflow_version=package.workflow_version if package else None,
            current_workflow_checksum=package.workflow_checksum if package else None,
            current_archive_storage_key=package.archive_storage_key if package else None,
            current_package_file_count=package.file_count if package else None,
            current_package_size_bytes=package.package_size_bytes if package else None,
            current_package_generated_at=(
                _parse_time(package.generated_at) if package else None
            ),
        )

    @staticmethod
    def _to_domain(row: LocalProjectORM) -> LocalProject:
        package = None
        if row.current_package_id is not None:
            package = LocalPackageMetadata(
                package_id=row.current_package_id,
                package_schema_version=row.current_package_schema_version,
                package_checksum=row.current_package_checksum,
                manifest_checksum=row.current_manifest_checksum,
                zip_checksum=row.current_zip_checksum,
                workflow_id=row.current_workflow_id,
                workflow_version=row.current_workflow_version,
                workflow_checksum=row.current_workflow_checksum,
                archive_storage_key=row.current_archive_storage_key,
                file_count=row.current_package_file_count,
                package_size_bytes=row.current_package_size_bytes,
                generated_at=_format_time(row.current_package_generated_at),
            )
        return LocalProject(
            project_id=row.project_id,
            name=row.name,
            research_topic=row.research_topic,
            selected_workflow=row.selected_workflow,
            created_at=_format_time(row.created_at),
            updated_at=_format_time(row.updated_at),
            current_package=package,
        )


def _parse_time(value: str):
    from datetime import datetime

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _format_time(value):
    from datetime import timezone

    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
