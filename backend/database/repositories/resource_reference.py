"""PostgreSQL adapter for Project Resource references and exact bindings."""

from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database.orm import (
    ProjectResourceReferenceORM,
    WorkflowResourceBindingORM,
    WorkflowResourceRequirementORM,
)
from backend.resource_references.contracts import (
    ProjectResourceReference,
    ResourceBindingState,
    ResourceKind,
    ResourceLifecycle,
    ResourceProvider,
    WorkflowResourceBinding,
    WorkflowResourceRequirement,
)
from backend.resource_references.errors import ResourceReferenceConflictError
from backend.resource_references.ports import ResourceReferenceRepository

from ._helpers import pending_by_composite_key, pending_instances


class SQLAlchemyResourceReferenceRepository(ResourceReferenceRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_resource(self, resource: ProjectResourceReference) -> None:
        existing = self.get_resource(resource.resource_id)
        if existing is not None:
            if existing.immutable_identity() != resource.immutable_identity():
                raise ResourceReferenceConflictError(
                    "Resource immutable identity already exists with different metadata"
                )
            return
        self.session.add(ProjectResourceReferenceORM(
            resource_id=resource.resource_id,
            project_id=resource.project_id,
            resource_kind=resource.resource_kind.value,
            provider=resource.provider.value,
            locator=resource.locator,
            exact_revision=resource.exact_revision,
            expected_content_checksum=resource.expected_content_checksum,
            display_name=resource.display_name,
            metadata_json=_thaw(resource.metadata),
            lifecycle=resource.lifecycle.value,
            retired_at=resource.retired_at,
            created_at=resource.created_at,
            updated_at=resource.updated_at,
        ))

    def get_resource(self, resource_id: str) -> ProjectResourceReference | None:
        row = next((
            item for item in pending_instances(self.session, ProjectResourceReferenceORM)
            if item.resource_id == resource_id
        ), None) or self.session.get(ProjectResourceReferenceORM, resource_id)
        return None if row is None else _resource(row)

    def list_resources(
        self, project_id: str, *, offset=0, limit=100
    ) -> tuple[ProjectResourceReference, ...]:
        rows = list(self.session.scalars(
            select(ProjectResourceReferenceORM).where(
                ProjectResourceReferenceORM.project_id == project_id
            ).order_by(
                ProjectResourceReferenceORM.created_at,
                ProjectResourceReferenceORM.resource_id,
            )
        ))
        rows.extend(
            row for row in pending_instances(self.session, ProjectResourceReferenceORM)
            if row.project_id == project_id and row not in rows
        )
        rows.sort(key=lambda row: (row.created_at, row.resource_id))
        return tuple(_resource(row) for row in rows[offset:offset + limit])

    def count_resources(self, project_id: str) -> int:
        count = int(self.session.scalar(
            select(func.count()).select_from(ProjectResourceReferenceORM).where(
                ProjectResourceReferenceORM.project_id == project_id
            )
        ) or 0)
        return count + sum(
            row.project_id == project_id
            for row in pending_instances(self.session, ProjectResourceReferenceORM)
        )

    def add_requirement(self, requirement: WorkflowResourceRequirement) -> None:
        existing = self.get_requirement(
            requirement.workflow_definition_id,
            requirement.workflow_version,
            requirement.requirement_key,
        )
        if existing is not None:
            if existing != requirement:
                raise ResourceReferenceConflictError(
                    "Workflow Resource Requirement immutable-content conflict"
                )
            return
        self.session.add(WorkflowResourceRequirementORM(
            workflow_definition_id=requirement.workflow_definition_id,
            workflow_version=requirement.workflow_version,
            requirement_key=requirement.requirement_key,
            resource_kind=requirement.resource_kind.value,
            cardinality_min=requirement.cardinality_min,
            cardinality_max=requirement.cardinality_max,
            required=requirement.required,
            allowed_providers_json=[item.value for item in requirement.allowed_providers],
            usage_description=requirement.usage_description,
            created_at=requirement.created_at,
            updated_at=requirement.updated_at,
        ))

    def get_requirement(
        self, workflow_definition_id: str, workflow_version: str, requirement_key: str
    ) -> WorkflowResourceRequirement | None:
        key = (workflow_definition_id, workflow_version, requirement_key)
        row = pending_by_composite_key(
            self.session,
            WorkflowResourceRequirementORM,
            key,
            ("workflow_definition_id", "workflow_version", "requirement_key"),
        ) or self.session.get(WorkflowResourceRequirementORM, key)
        return None if row is None else _requirement(row)

    def list_requirements(self) -> tuple[WorkflowResourceRequirement, ...]:
        rows = list(self.session.scalars(select(WorkflowResourceRequirementORM)))
        rows.extend(
            row for row in pending_instances(self.session, WorkflowResourceRequirementORM)
            if row not in rows
        )
        rows.sort(key=lambda row: (
            row.workflow_definition_id, row.workflow_version, row.requirement_key
        ))
        return tuple(_requirement(row) for row in rows)

    def add_binding(self, binding: WorkflowResourceBinding) -> None:
        existing = self.get_binding(binding.binding_id)
        if existing is not None:
            if existing != binding:
                raise ResourceReferenceConflictError(
                    "Workflow Resource Binding immutable-content conflict"
                )
            return
        self.session.add(WorkflowResourceBindingORM(
            binding_id=binding.binding_id,
            project_id=binding.project_id,
            workflow_instance_id=binding.workflow_instance_id,
            workflow_definition_id=binding.workflow_definition_id,
            workflow_version=binding.workflow_version,
            requirement_key=binding.requirement_key,
            resource_id=binding.resource_id,
            expected_content_checksum=binding.expected_content_checksum,
            state=binding.state.value,
            idempotency_key=binding.idempotency_key,
            created_at=binding.created_at,
            updated_at=binding.updated_at,
            retired_at=binding.retired_at,
        ))

    def get_binding(self, binding_id: str) -> WorkflowResourceBinding | None:
        row = next((
            item for item in pending_instances(self.session, WorkflowResourceBindingORM)
            if item.binding_id == binding_id
        ), None) or self.session.get(WorkflowResourceBindingORM, binding_id)
        return None if row is None else _binding(row)

    def get_binding_by_idempotency(
        self, project_id: str, workflow_instance_id: str, idempotency_key: str
    ) -> WorkflowResourceBinding | None:
        rows = list(self.session.scalars(
            select(WorkflowResourceBindingORM).where(
                WorkflowResourceBindingORM.project_id == project_id,
                WorkflowResourceBindingORM.workflow_instance_id == workflow_instance_id,
                WorkflowResourceBindingORM.idempotency_key == idempotency_key,
            )
        ))
        rows.extend(
            row for row in pending_instances(self.session, WorkflowResourceBindingORM)
            if row.project_id == project_id
            and row.workflow_instance_id == workflow_instance_id
            and row.idempotency_key == idempotency_key
            and row not in rows
        )
        return None if not rows else _binding(rows[0])

    def list_bindings(
        self, project_id: str, workflow_instance_id: str, *, offset=0, limit=100
    ) -> tuple[WorkflowResourceBinding, ...]:
        rows = list(self.session.scalars(
            select(WorkflowResourceBindingORM).where(
                WorkflowResourceBindingORM.project_id == project_id,
                WorkflowResourceBindingORM.workflow_instance_id == workflow_instance_id,
            )
        ))
        rows.extend(
            row for row in pending_instances(self.session, WorkflowResourceBindingORM)
            if row.project_id == project_id
            and row.workflow_instance_id == workflow_instance_id
            and row not in rows
        )
        rows.sort(key=lambda row: (row.requirement_key, row.created_at, row.binding_id))
        return tuple(_binding(row) for row in rows[offset:offset + limit])

    def list_project_bindings(
        self, project_id: str
    ) -> tuple[WorkflowResourceBinding, ...]:
        rows = list(self.session.scalars(
            select(WorkflowResourceBindingORM).where(
                WorkflowResourceBindingORM.project_id == project_id
            )
        ))
        rows.extend(
            row for row in pending_instances(self.session, WorkflowResourceBindingORM)
            if row.project_id == project_id and row not in rows
        )
        rows.sort(key=lambda row: (
            row.workflow_instance_id, row.requirement_key, row.binding_id
        ))
        return tuple(_binding(row) for row in rows)


def _resource(row: ProjectResourceReferenceORM) -> ProjectResourceReference:
    return ProjectResourceReference(
        resource_id=row.resource_id,
        project_id=row.project_id,
        resource_kind=ResourceKind(row.resource_kind),
        provider=ResourceProvider(row.provider),
        locator=row.locator,
        exact_revision=row.exact_revision,
        expected_content_checksum=row.expected_content_checksum,
        display_name=row.display_name,
        metadata=row.metadata_json,
        lifecycle=ResourceLifecycle(row.lifecycle),
        created_at=row.created_at,
        updated_at=row.updated_at,
        retired_at=row.retired_at,
    )


def _requirement(row: WorkflowResourceRequirementORM) -> WorkflowResourceRequirement:
    return WorkflowResourceRequirement(
        workflow_definition_id=row.workflow_definition_id,
        workflow_version=row.workflow_version,
        requirement_key=row.requirement_key,
        resource_kind=ResourceKind(row.resource_kind),
        cardinality_min=row.cardinality_min,
        cardinality_max=row.cardinality_max,
        required=row.required,
        allowed_providers=tuple(ResourceProvider(item) for item in row.allowed_providers_json),
        usage_description=row.usage_description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _binding(row: WorkflowResourceBindingORM) -> WorkflowResourceBinding:
    return WorkflowResourceBinding(
        binding_id=row.binding_id,
        project_id=row.project_id,
        workflow_instance_id=row.workflow_instance_id,
        workflow_definition_id=row.workflow_definition_id,
        workflow_version=row.workflow_version,
        requirement_key=row.requirement_key,
        resource_id=row.resource_id,
        expected_content_checksum=row.expected_content_checksum,
        state=ResourceBindingState(row.state),
        idempotency_key=row.idempotency_key,
        created_at=row.created_at,
        updated_at=row.updated_at,
        retired_at=row.retired_at,
    )


def _thaw(value):
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value
