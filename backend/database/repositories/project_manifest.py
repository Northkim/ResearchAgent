"""SQLAlchemy Desired Project Manifest repository with PostgreSQL CAS."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.database.orm import (
    ProjectDesiredManifestORM,
    ProjectManifestEntryORM,
    ProjectORM,
)
from backend.project_workspaces.contracts import (
    CloudProject,
    CloudProjectStatus,
    DesiredProjectManifest,
    ManifestDesiredAction,
    ManifestEntryKind,
    ProjectManifestEntry,
)
from backend.project_workspaces.errors import ManifestRevisionConflictError
from backend.project_workspaces.ports import ProjectManifestRepository

from ._helpers import pending_by_composite_key, pending_instances


class SQLAlchemyProjectManifestRepository(ProjectManifestRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_project(self, project: CloudProject) -> None:
        if self.get_project(project.project_id) is not None:
            raise ValueError("Canonical Project already exists")
        self.session.add(ProjectORM(
            project_id=project.project_id,
            workspace_id=project.workspace_id,
            name=project.name,
            research_topic=project.research_topic,
            status=project.status.value,
            current_manifest_revision=project.current_manifest_revision,
            legacy_local_project_id=project.legacy_local_project_id,
            created_at=project.created_at,
            updated_at=project.updated_at,
        ))

    def get_project(self, project_id: str) -> CloudProject | None:
        row = next(
            (item for item in pending_instances(self.session, ProjectORM)
             if item.project_id == project_id),
            None,
        ) or self.session.get(ProjectORM, project_id)
        return _project(row) if row is not None else None

    def add_manifest(self, manifest: DesiredProjectManifest) -> None:
        key = (manifest.project_id, manifest.manifest_revision)
        if self.get_manifest(*key) is not None:
            raise ValueError("Desired Project Manifest revision already exists")
        self.session.add(ProjectDesiredManifestORM(
            project_id=manifest.project_id,
            manifest_revision=manifest.manifest_revision,
            workspace_id=manifest.workspace_id,
            base_revision=manifest.base_revision,
            schema_version=manifest.schema_version,
            canonical_checksum=manifest.canonical_checksum,
            manifest_json=_plain_json(manifest.manifest_json),
            created_by_subject_id=manifest.created_by_subject_id,
            idempotency_key=manifest.idempotency_key,
            created_at=manifest.created_at,
            updated_at=manifest.updated_at,
        ))

    def add_manifest_entries(
        self, entries: tuple[ProjectManifestEntry, ...]
    ) -> None:
        known = {
            row.entry_id
            for row in pending_instances(self.session, ProjectManifestEntryORM)
        }
        for entry in entries:
            if entry.entry_id in known or self.session.get(ProjectManifestEntryORM, entry.entry_id):
                raise ValueError("Desired Project Manifest entry already exists")
            known.add(entry.entry_id)
            self.session.add(ProjectManifestEntryORM(
                entry_id=entry.entry_id,
                project_id=entry.project_id,
                manifest_revision=entry.manifest_revision,
                entry_kind=entry.entry_kind.value,
                workflow_instance_id=entry.workflow_instance_id,
                desired_action=entry.desired_action.value,
                entry_checksum=entry.entry_checksum,
                created_at=entry.created_at,
            ))

    def get_manifest(
        self, project_id: str, manifest_revision: int
    ) -> DesiredProjectManifest | None:
        key = (project_id, manifest_revision)
        row = pending_by_composite_key(
            self.session,
            ProjectDesiredManifestORM,
            key,
            ("project_id", "manifest_revision"),
        ) or self.session.get(ProjectDesiredManifestORM, key)
        return _manifest(row) if row is not None else None

    def get_current_manifest(self, project_id: str) -> DesiredProjectManifest | None:
        project = self.get_project(project_id)
        if project is None or project.current_manifest_revision == 0:
            return None
        return self.get_manifest(project_id, project.current_manifest_revision)

    def list_manifest_entries(
        self, project_id: str, manifest_revision: int
    ) -> tuple[ProjectManifestEntry, ...]:
        rows = list(self.session.scalars(
            select(ProjectManifestEntryORM).where(
                ProjectManifestEntryORM.project_id == project_id,
                ProjectManifestEntryORM.manifest_revision == manifest_revision,
            )
        ))
        rows.extend(
            row
            for row in pending_instances(self.session, ProjectManifestEntryORM)
            if row.project_id == project_id
            and row.manifest_revision == manifest_revision
            and row not in rows
        )
        rows.sort(key=lambda row: (row.entry_kind, row.entry_id))
        return tuple(_entry(row) for row in rows)

    def compare_and_swap_revision(
        self,
        *,
        project_id: str,
        base_revision: int,
        updated_at: datetime,
    ) -> int:
        next_revision = base_revision + 1
        updated = self.session.execute(
            update(ProjectORM)
            .where(
                ProjectORM.project_id == project_id,
                ProjectORM.current_manifest_revision == base_revision,
            )
            .values(
                current_manifest_revision=next_revision,
                updated_at=updated_at,
            )
            .returning(ProjectORM.current_manifest_revision)
        ).scalar_one_or_none()
        if updated is not None:
            return int(updated)
        current = self.session.scalar(
            select(ProjectORM.current_manifest_revision).where(
                ProjectORM.project_id == project_id
            )
        )
        if current is None:
            raise ValueError("Canonical Project does not exist")
        raise ManifestRevisionConflictError(
            expected=base_revision,
            current=int(current),
        )


def _project(row: ProjectORM) -> CloudProject:
    return CloudProject(
        project_id=row.project_id,
        workspace_id=row.workspace_id,
        name=row.name,
        research_topic=row.research_topic,
        status=CloudProjectStatus(row.status),
        current_manifest_revision=row.current_manifest_revision,
        legacy_local_project_id=row.legacy_local_project_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _manifest(row: ProjectDesiredManifestORM) -> DesiredProjectManifest:
    return DesiredProjectManifest(
        project_id=row.project_id,
        manifest_revision=row.manifest_revision,
        workspace_id=row.workspace_id,
        base_revision=row.base_revision,
        schema_version=row.schema_version,
        canonical_checksum=row.canonical_checksum,
        manifest_json=row.manifest_json,
        created_by_subject_id=row.created_by_subject_id,
        idempotency_key=str(row.idempotency_key),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _entry(row: ProjectManifestEntryORM) -> ProjectManifestEntry:
    return ProjectManifestEntry(
        entry_id=row.entry_id,
        project_id=row.project_id,
        manifest_revision=row.manifest_revision,
        entry_kind=ManifestEntryKind(row.entry_kind),
        workflow_instance_id=row.workflow_instance_id,
        desired_action=ManifestDesiredAction(row.desired_action),
        entry_checksum=row.entry_checksum,
        created_at=row.created_at,
    )


def _plain_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json(item) for item in value]
    return value
