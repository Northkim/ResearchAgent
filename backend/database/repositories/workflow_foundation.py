"""SQLAlchemy adapter for local Workflow foundation persistence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.orm import (
    LocalWorkflowCapsuleVersionORM,
    LocalWorkflowDefinitionORM,
    LocalWorkflowDefinitionVersionORM,
    ProjectWorkflowInstanceORM,
)
from backend.project_workspaces.contracts import (
    ProjectWorkflowInstance,
    WorkflowCapsuleVersion,
    WorkflowDefinition,
    WorkflowDefinitionLifecycle,
    WorkflowDefinitionVersion,
    WorkflowInstanceDesiredState,
    WorkflowReviewStatus,
)
from backend.project_workspaces.errors import WorkflowFoundationConflictError
from backend.project_workspaces.literature_search import (
    LITERATURE_SEARCH_DEFINITION_ID,
    LITERATURE_SEARCH_STABLE_KEY,
)
from backend.project_workspaces.ports import WorkflowFoundationRepository

from ._helpers import pending_by_composite_key, pending_instances


class SQLAlchemyWorkflowFoundationRepository(WorkflowFoundationRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_definition(self, definition: WorkflowDefinition) -> None:
        existing = self.get_definition(definition.workflow_definition_id)
        if existing is not None:
            _require_equivalent(existing, definition, _definition_content, "Workflow Definition")
            return
        self.session.add(LocalWorkflowDefinitionORM(
            workflow_definition_id=definition.workflow_definition_id,
            display_name=definition.display_name,
            description=definition.description,
            lifecycle=definition.lifecycle.value,
            allows_multiple_instances=definition.allows_multiple_instances,
            created_at=definition.created_at,
            updated_at=definition.updated_at,
        ))

    def get_definition(self, workflow_definition_id: str) -> WorkflowDefinition | None:
        row = _pending_single(self.session, LocalWorkflowDefinitionORM, "workflow_definition_id", workflow_definition_id)
        row = row or self.session.get(LocalWorkflowDefinitionORM, workflow_definition_id)
        return _definition(row) if row is not None else None

    def get_definition_by_stable_key(self, stable_key: str) -> WorkflowDefinition | None:
        if stable_key != LITERATURE_SEARCH_STABLE_KEY:
            return None
        return self.get_definition(LITERATURE_SEARCH_DEFINITION_ID)

    def list_definitions(self) -> tuple[WorkflowDefinition, ...]:
        rows = list(self.session.scalars(select(LocalWorkflowDefinitionORM)))
        rows.extend(row for row in pending_instances(self.session, LocalWorkflowDefinitionORM) if row not in rows)
        rows.sort(key=lambda row: row.workflow_definition_id)
        return tuple(_definition(row) for row in rows)

    def add_definition_version(self, version: WorkflowDefinitionVersion) -> None:
        existing = self.get_definition_version(version.workflow_definition_id, version.version)
        if existing is not None:
            _require_equivalent(existing, version, _definition_version_content, "Workflow Definition Version")
            return
        self.session.add(LocalWorkflowDefinitionVersionORM(
            workflow_definition_id=version.workflow_definition_id,
            version=version.version,
            contract_checksum=version.contract_checksum,
            input_schema_id=version.input_schema_id,
            output_schema_id=version.output_schema_id,
            compatibility=_plain_json(version.compatibility),
            review_status=version.review_status.value,
            published_at=version.published_at,
            created_at=version.created_at,
            updated_at=version.updated_at,
        ))

    def get_definition_version(self, workflow_definition_id: str, version: str) -> WorkflowDefinitionVersion | None:
        key = (workflow_definition_id, version)
        row = pending_by_composite_key(self.session, LocalWorkflowDefinitionVersionORM, key, ("workflow_definition_id", "version"))
        row = row or self.session.get(LocalWorkflowDefinitionVersionORM, key)
        return _definition_version(row) if row is not None else None

    def add_capsule_version(self, capsule: WorkflowCapsuleVersion) -> None:
        existing = self.get_capsule_version(capsule.capsule_id, capsule.capsule_version)
        if existing is not None:
            _require_equivalent(existing, capsule, _capsule_content, "Workflow Capsule Version")
            return
        self.session.add(LocalWorkflowCapsuleVersionORM(
            capsule_id=capsule.capsule_id,
            capsule_version=capsule.capsule_version,
            workflow_definition_id=capsule.workflow_definition_id,
            workflow_version=capsule.workflow_version,
            definition_checksum=capsule.definition_checksum,
            archive_size_bytes=capsule.archive_size_bytes,
            archive_media_type=capsule.archive_media_type,
            mutable_roots=list(capsule.mutable_roots),
            capability_requirements=list(capsule.capability_requirements),
            compatibility=_plain_json(capsule.compatibility),
            review_status=capsule.review_status.value,
            legacy_package_compatible=capsule.legacy_package_compatible,
            created_at=capsule.created_at,
            updated_at=capsule.updated_at,
        ))

    def get_capsule_version(self, capsule_id: str, capsule_version: str) -> WorkflowCapsuleVersion | None:
        key = (capsule_id, capsule_version)
        row = pending_by_composite_key(self.session, LocalWorkflowCapsuleVersionORM, key, ("capsule_id", "capsule_version"))
        row = row or self.session.get(LocalWorkflowCapsuleVersionORM, key)
        return _capsule(row) if row is not None else None

    def add_workflow_instance(self, instance: ProjectWorkflowInstance) -> None:
        existing = self.get_workflow_instance(instance.workflow_instance_id)
        if existing is not None:
            _require_equivalent(existing, instance, _instance_identity_content, "Project Workflow Instance")
            return
        self.session.add(ProjectWorkflowInstanceORM(
            workflow_instance_id=instance.workflow_instance_id,
            project_id=instance.project_id,
            workflow_definition_id=instance.workflow_definition_id,
            workflow_version=instance.workflow_version,
            capsule_id=instance.capsule_id,
            capsule_version=instance.capsule_version,
            desired_state=instance.desired_state.value,
            display_name=instance.display_name,
            created_manifest_revision=instance.created_manifest_revision,
            retired_manifest_revision=instance.retired_manifest_revision,
            legacy_package_id=instance.legacy_package_id,
            created_at=instance.created_at,
            updated_at=instance.updated_at,
        ))

    def get_workflow_instance(self, workflow_instance_id: str) -> ProjectWorkflowInstance | None:
        row = _pending_single(self.session, ProjectWorkflowInstanceORM, "workflow_instance_id", workflow_instance_id)
        row = row or self.session.get(ProjectWorkflowInstanceORM, workflow_instance_id)
        return _instance(row) if row is not None else None

    def list_workflow_instances(self, project_id: str) -> tuple[ProjectWorkflowInstance, ...]:
        rows = list(self.session.scalars(select(ProjectWorkflowInstanceORM).where(ProjectWorkflowInstanceORM.project_id == project_id)))
        rows.extend(row for row in pending_instances(self.session, ProjectWorkflowInstanceORM) if row.project_id == project_id and row not in rows)
        rows.sort(key=lambda row: (row.created_at, row.workflow_instance_id))
        return tuple(_instance(row) for row in rows)


def _pending_single(session: Session, model_type, field: str, value: str):
    return next((row for row in pending_instances(session, model_type) if getattr(row, field) == value), None)


def _require_equivalent(existing, incoming, content, label: str) -> None:
    if content(existing) != content(incoming):
        raise WorkflowFoundationConflictError(f"{label} immutable-content conflict")


def _definition_content(value: WorkflowDefinition):
    return (value.workflow_definition_id, value.display_name, value.description, value.lifecycle, value.allows_multiple_instances)


def _definition_version_content(value: WorkflowDefinitionVersion):
    return (value.workflow_definition_id, value.version, value.contract_checksum, value.input_schema_id, value.output_schema_id, _plain_json(value.compatibility), value.review_status)


def _capsule_content(value: WorkflowCapsuleVersion):
    return (value.capsule_id, value.capsule_version, value.workflow_definition_id, value.workflow_version, value.definition_checksum, value.archive_size_bytes, value.archive_media_type, value.mutable_roots, value.capability_requirements, _plain_json(value.compatibility), value.review_status, value.legacy_package_compatible)


def _instance_identity_content(value: ProjectWorkflowInstance):
    # Package regeneration is not an identity change and never rewrites the
    # original legacy compatibility pin during reconciliation.
    return (value.workflow_instance_id, value.project_id, value.workflow_definition_id, value.workflow_version)


def _definition(row) -> WorkflowDefinition:
    return WorkflowDefinition(row.workflow_definition_id, row.display_name, row.description, WorkflowDefinitionLifecycle(row.lifecycle), row.allows_multiple_instances, row.created_at, row.updated_at)


def _definition_version(row) -> WorkflowDefinitionVersion:
    return WorkflowDefinitionVersion(row.workflow_definition_id, row.version, row.contract_checksum, row.input_schema_id, row.output_schema_id, row.compatibility, WorkflowReviewStatus(row.review_status), row.published_at, row.created_at, row.updated_at)


def _capsule(row) -> WorkflowCapsuleVersion:
    return WorkflowCapsuleVersion(row.capsule_id, row.capsule_version, row.workflow_definition_id, row.workflow_version, row.definition_checksum, row.archive_size_bytes, row.archive_media_type, tuple(row.mutable_roots), tuple(row.capability_requirements), row.compatibility, WorkflowReviewStatus(row.review_status), row.legacy_package_compatible, row.created_at, row.updated_at)


def _instance(row) -> ProjectWorkflowInstance:
    return ProjectWorkflowInstance(row.workflow_instance_id, row.project_id, row.workflow_definition_id, row.workflow_version, row.capsule_id, row.capsule_version, WorkflowInstanceDesiredState(row.desired_state), row.display_name, row.created_manifest_revision, row.retired_manifest_revision, row.legacy_package_id, row.created_at, row.updated_at)


def _plain_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json(item) for item in value]
    return value
