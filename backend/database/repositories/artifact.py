"""SQLAlchemy immutable ArtifactRepository adapter."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.orm import ArtifactORM
from backend.domain.models import ArtifactMetadata
from backend.persistence.models._immutability import thaw_json
from backend.persistence.ports import ArtifactRepository, DuplicateEntityError

from ._helpers import pending_by_id, pending_instances


class SQLAlchemyArtifactRepository(ArtifactRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, artifact: ArtifactMetadata) -> None:
        row = pending_by_id(self.session, ArtifactORM, artifact.id)
        if row is None:
            row = self.session.get(ArtifactORM, artifact.id)
        if row is not None:
            if self._to_domain(row) != artifact:
                raise DuplicateEntityError(
                    f"Artifact ID {artifact.id} has conflicting immutable metadata"
                )
            return
        self.session.add(
            ArtifactORM(
                id=artifact.id,
                project_id=artifact.project_id,
                logical_artifact_id=artifact.logical_artifact_id,
                logical_name=artifact.logical_name,
                version=artifact.version,
                kind=artifact.kind,
                storage_ref=artifact.storage_ref,
                checksum=artifact.checksum,
                media_type=artifact.media_type,
                size=artifact.size,
                producer_run_id=artifact.producer_run_id,
                producer_step_run_id=artifact.producer_step_run_id,
                metadata_json=thaw_json(artifact.metadata),
                created_at=artifact.created_at,
            )
        )

    def get(self, artifact_id: str) -> ArtifactMetadata | None:
        row = pending_by_id(self.session, ArtifactORM, artifact_id)
        if row is None:
            row = self.session.get(ArtifactORM, artifact_id)
        return self._to_domain(row) if row is not None else None

    def list_for_project(self, project_id: str) -> tuple[ArtifactMetadata, ...]:
        rows = list(
            self.session.scalars(
                select(ArtifactORM)
                .where(ArtifactORM.project_id == project_id)
                .order_by(
                    ArtifactORM.logical_artifact_id,
                    ArtifactORM.version,
                    ArtifactORM.id,
                )
            )
        )
        rows.extend(
            row
            for row in pending_instances(self.session, ArtifactORM)
            if row.project_id == project_id and row not in rows
        )
        rows.sort(
            key=lambda row: (row.logical_artifact_id, row.version, row.id)
        )
        return tuple(self._to_domain(row) for row in rows)

    @staticmethod
    def _to_domain(row: ArtifactORM) -> ArtifactMetadata:
        return ArtifactMetadata(
            id=row.id,
            project_id=row.project_id,
            logical_artifact_id=row.logical_artifact_id,
            logical_name=row.logical_name,
            version=row.version,
            kind=row.kind,
            storage_ref=row.storage_ref,
            checksum=row.checksum,
            media_type=row.media_type,
            size=row.size,
            producer_run_id=row.producer_run_id,
            producer_step_run_id=row.producer_step_run_id,
            metadata=row.metadata_json,
            created_at=row.created_at,
        )
