"""SQLAlchemy persistence for Capsule acquisition and installation reports."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.orm import (
    WorkflowCapsuleArtifactORM,
    WorkspaceInstallationAcknowledgementORM,
)
from backend.project_workspaces.contracts import (
    CapsuleArtifactStatus,
    InstallationAcknowledgementStatus,
    WorkflowCapsuleArtifact,
    WorkspaceInstallationAcknowledgement,
)
from backend.project_workspaces.ports import WorkspaceSyncRepository

from ._helpers import pending_instances


class SQLAlchemyWorkspaceSyncRepository(WorkspaceSyncRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_capsule_artifact(self, artifact: WorkflowCapsuleArtifact) -> None:
        existing = self.get_capsule_artifact_by_id(artifact.capsule_artifact_id)
        if existing is not None:
            if existing != artifact:
                raise ValueError("Workflow Capsule artifact immutable-content conflict")
            return
        self.session.add(WorkflowCapsuleArtifactORM(
            capsule_artifact_id=artifact.capsule_artifact_id,
            project_id=artifact.project_id,
            workflow_instance_id=artifact.workflow_instance_id,
            capsule_id=artifact.capsule_id,
            capsule_version=artifact.capsule_version,
            package_id=artifact.package_id,
            package_schema_version=artifact.package_schema_version,
            package_checksum=artifact.package_checksum,
            manifest_checksum=artifact.manifest_checksum,
            archive_checksum=artifact.archive_checksum,
            archive_size_bytes=artifact.archive_size_bytes,
            file_count=artifact.file_count,
            archive_storage_key=artifact.archive_storage_key,
            status=artifact.status.value,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
        ))

    def get_capsule_artifact(
        self, project_id: str, workflow_instance_id: str
    ) -> WorkflowCapsuleArtifact | None:
        row = next((item for item in pending_instances(self.session, WorkflowCapsuleArtifactORM)
                    if item.project_id == project_id and item.workflow_instance_id == workflow_instance_id), None)
        row = row or self.session.scalar(select(WorkflowCapsuleArtifactORM).where(
            WorkflowCapsuleArtifactORM.project_id == project_id,
            WorkflowCapsuleArtifactORM.workflow_instance_id == workflow_instance_id,
        ))
        return _artifact(row) if row is not None else None

    def get_capsule_artifact_by_id(
        self, capsule_artifact_id: str
    ) -> WorkflowCapsuleArtifact | None:
        row = next((item for item in pending_instances(self.session, WorkflowCapsuleArtifactORM)
                    if item.capsule_artifact_id == capsule_artifact_id), None)
        row = row or self.session.get(WorkflowCapsuleArtifactORM, capsule_artifact_id)
        return _artifact(row) if row is not None else None

    def list_capsule_artifacts(
        self, project_id: str
    ) -> tuple[WorkflowCapsuleArtifact, ...]:
        rows = list(self.session.scalars(select(WorkflowCapsuleArtifactORM).where(
            WorkflowCapsuleArtifactORM.project_id == project_id
        )))
        rows.extend(item for item in pending_instances(self.session, WorkflowCapsuleArtifactORM)
                    if item.project_id == project_id and item not in rows)
        rows.sort(key=lambda item: item.workflow_instance_id)
        return tuple(_artifact(row) for row in rows)

    def add_acknowledgement(
        self, acknowledgement: WorkspaceInstallationAcknowledgement
    ) -> None:
        existing = self.get_acknowledgement(acknowledgement.installation_id)
        if existing is not None:
            if _ack_payload(existing) != _ack_payload(acknowledgement):
                raise ValueError("Installation acknowledgement immutable-content conflict")
            return
        self.session.add(WorkspaceInstallationAcknowledgementORM(
            installation_id=acknowledgement.installation_id,
            project_id=acknowledgement.project_id,
            workspace_id=acknowledgement.workspace_id,
            manifest_revision=acknowledgement.manifest_revision,
            manifest_checksum=acknowledgement.manifest_checksum,
            installed_lock_schema=acknowledgement.installed_lock_schema,
            installed_lock_checksum=acknowledgement.installed_lock_checksum,
            plan_checksum=acknowledgement.plan_checksum,
            idempotency_key=acknowledgement.idempotency_key,
            status=acknowledgement.status.value,
            installed_capsules=[_plain_json(item) for item in acknowledgement.installed_capsules],
            installed_at=acknowledgement.installed_at,
            acknowledged_at=acknowledgement.acknowledged_at,
            created_at=acknowledgement.created_at,
            updated_at=acknowledgement.updated_at,
        ))

    def get_acknowledgement_by_idempotency(
        self, workspace_id: str, idempotency_key: str
    ) -> WorkspaceInstallationAcknowledgement | None:
        row = next((item for item in pending_instances(self.session, WorkspaceInstallationAcknowledgementORM)
                    if item.workspace_id == workspace_id and str(item.idempotency_key) == idempotency_key), None)
        row = row or self.session.scalar(select(WorkspaceInstallationAcknowledgementORM).where(
            WorkspaceInstallationAcknowledgementORM.workspace_id == workspace_id,
            WorkspaceInstallationAcknowledgementORM.idempotency_key == idempotency_key,
        ))
        return _ack(row) if row is not None else None

    def get_acknowledgement(
        self, installation_id: str
    ) -> WorkspaceInstallationAcknowledgement | None:
        row = next((item for item in pending_instances(self.session, WorkspaceInstallationAcknowledgementORM)
                    if item.installation_id == installation_id), None)
        row = row or self.session.get(WorkspaceInstallationAcknowledgementORM, installation_id)
        return _ack(row) if row is not None else None

    def list_acknowledgements(
        self, project_id: str
    ) -> tuple[WorkspaceInstallationAcknowledgement, ...]:
        rows = list(self.session.scalars(
            select(WorkspaceInstallationAcknowledgementORM).where(
                WorkspaceInstallationAcknowledgementORM.project_id == project_id
            )
        ))
        rows.extend(
            item
            for item in pending_instances(
                self.session, WorkspaceInstallationAcknowledgementORM
            )
            if item.project_id == project_id and item not in rows
        )
        rows.sort(key=lambda item: (item.manifest_revision, item.acknowledged_at, item.installation_id))
        return tuple(_ack(row) for row in rows)


def _artifact(row: WorkflowCapsuleArtifactORM) -> WorkflowCapsuleArtifact:
    return WorkflowCapsuleArtifact(
        row.capsule_artifact_id, row.project_id, row.workflow_instance_id,
        row.capsule_id, row.capsule_version, row.package_id,
        row.package_schema_version, row.package_checksum, row.manifest_checksum,
        row.archive_checksum, row.archive_size_bytes, row.file_count,
        row.archive_storage_key, CapsuleArtifactStatus(row.status),
        row.created_at, row.updated_at,
    )


def _ack(row: WorkspaceInstallationAcknowledgementORM) -> WorkspaceInstallationAcknowledgement:
    return WorkspaceInstallationAcknowledgement(
        row.installation_id, row.project_id, row.workspace_id,
        row.manifest_revision, row.manifest_checksum, row.installed_lock_schema,
        row.installed_lock_checksum, row.plan_checksum, str(row.idempotency_key),
        InstallationAcknowledgementStatus(row.status), tuple(row.installed_capsules),
        row.installed_at, row.acknowledged_at, row.created_at, row.updated_at,
    )


def _plain_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json(item) for item in value]
    return value


def _ack_payload(value: WorkspaceInstallationAcknowledgement) -> tuple[Any, ...]:
    return (
        value.installation_id, value.project_id, value.workspace_id,
        value.manifest_revision, value.manifest_checksum,
        value.installed_lock_schema, value.installed_lock_checksum,
        value.plan_checksum, value.idempotency_key,
        tuple(_plain_json(item) for item in value.installed_capsules),
        value.installed_at,
    )
