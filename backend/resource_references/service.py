"""Cloud metadata service for Project Resources and exact Workflow bindings."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid5

from backend.application.errors import (
    ApplicationCodedAuthorizationError,
    ApplicationCodedConflictError,
    ApplicationCodedNotFoundError,
    ApplicationCodedValidationError,
)
from .contracts import (
    ProjectResourceReference,
    ResourceBindingState,
    ResourceKind,
    ResourceLifecycle,
    ResourceProvider,
    WorkflowResourceBinding,
)

if TYPE_CHECKING:
    from backend.persistence.ports import UnitOfWork

_NAMESPACE = UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966")


class ResourceReferenceService:
    """Persist reference metadata only; resolver bytes and credentials stay local."""

    def __init__(self, *, unit_of_work: UnitOfWork, clock=None) -> None:
        self._uow = unit_of_work
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._requirements_cache = None

    def create_resource(
        self,
        *,
        project_id: str,
        resource_kind: str,
        provider: str,
        locator: str,
        exact_revision: str,
        expected_content_checksum: str,
        display_name: str,
        metadata: dict,
    ) -> ProjectResourceReference:
        self._require_project(project_id)
        try:
            kind = ResourceKind(resource_kind)
            source = ResourceProvider(provider)
            identity = uuid5(
                _NAMESPACE,
                "project-resource/v1|project=" + project_id
                + "|kind=" + kind.value
                + "|provider=" + source.value
                + "|locator=" + locator
                + "|revision=" + exact_revision
                + "|checksum=" + expected_content_checksum,
            )
            now = self._clock()
            candidate = ProjectResourceReference(
                resource_id="resource-" + identity.hex,
                project_id=project_id,
                resource_kind=kind,
                provider=source,
                locator=locator,
                exact_revision=exact_revision,
                expected_content_checksum=expected_content_checksum,
                display_name=display_name,
                metadata=metadata,
                lifecycle=ResourceLifecycle.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        except (TypeError, ValueError) as error:
            raise ApplicationCodedValidationError(
                str(error), code="RESOURCE_REFERENCE_INVALID"
            ) from error
        existing = self._uow.resource_references.get_resource(candidate.resource_id)
        if existing is not None:
            if existing.immutable_identity() != candidate.immutable_identity():
                raise ApplicationCodedConflictError(
                    "Resource identity conflicts with existing metadata",
                    code="RESOURCE_REFERENCE_CONFLICT",
                )
            return existing
        self._uow.resource_references.add_resource(candidate)
        self._uow.commit()
        return candidate

    def list_resources(self, project_id: str, *, offset: int = 0, limit: int = 50):
        self._require_project(project_id)
        if offset < 0 or not 1 <= limit <= 100:
            raise ApplicationCodedValidationError(
                "Resource pagination is outside the supported bound",
                code="RESOURCE_PAGINATION_INVALID",
            )
        return (
            self._uow.resource_references.list_resources(
                project_id, offset=offset, limit=limit
            ),
            self._uow.resource_references.count_resources(project_id),
        )

    def get_resource(self, project_id: str, resource_id: str):
        self._require_project(project_id)
        value = self._uow.resource_references.get_resource(resource_id)
        if value is None:
            raise ApplicationCodedNotFoundError(
                "Resource Reference not found", code="RESOURCE_REFERENCE_NOT_FOUND"
            )
        if value.project_id != project_id:
            raise ApplicationCodedAuthorizationError(
                "Resource is outside the Project scope",
                code="PROJECT_SCOPE_MISMATCH",
            )
        return value

    def requirements_for(self, workflow_definition_id: str, workflow_version: str):
        if self._requirements_cache is None:
            self._requirements_cache = self._uow.resource_references.list_requirements()
        return tuple(
            item for item in self._requirements_cache
            if item.workflow_definition_id == workflow_definition_id
            and item.workflow_version == workflow_version
        )

    def bind_resource(
        self,
        *,
        project_id: str,
        workflow_instance_id: str,
        requirement_key: str,
        resource_id: str,
        idempotency_key: str,
    ) -> WorkflowResourceBinding:
        self._require_project(project_id)
        instance = self._uow.workflow_foundation.get_workflow_instance(
            workflow_instance_id
        )
        if instance is None or instance.project_id != project_id:
            raise ApplicationCodedAuthorizationError(
                "Workflow Instance is outside the Project scope",
                code="PROJECT_SCOPE_MISMATCH",
            )
        resource = self.get_resource(project_id, resource_id)
        requirement = self._uow.resource_references.get_requirement(
            instance.workflow_definition_id,
            instance.workflow_version,
            requirement_key,
        )
        if requirement is None:
            raise ApplicationCodedValidationError(
                "Workflow Resource Requirement is unavailable",
                code="RESOURCE_REQUIREMENT_NOT_FOUND",
            )
        if resource.resource_kind is not requirement.resource_kind:
            raise ApplicationCodedValidationError(
                "Resource kind is incompatible with the requirement",
                code="RESOURCE_KIND_MISMATCH",
            )
        if resource.provider not in requirement.allowed_providers:
            raise ApplicationCodedValidationError(
                "Resource provider is incompatible with the requirement",
                code="RESOURCE_PROVIDER_MISMATCH",
            )
        replay = self._uow.resource_references.get_binding_by_idempotency(
            project_id, workflow_instance_id, idempotency_key
        )
        if replay is not None:
            if (
                replay.requirement_key != requirement_key
                or replay.resource_id != resource_id
            ):
                raise ApplicationCodedConflictError(
                    "Resource binding idempotency key has different content",
                    code="IDEMPOTENCY_CONFLICT",
                )
            return replay
        active = tuple(
            item for item in self._uow.resource_references.list_bindings(
                project_id, workflow_instance_id
            )
            if item.requirement_key == requirement_key
            and item.state is ResourceBindingState.ACTIVE
        )
        if active:
            raise ApplicationCodedConflictError(
                "Resource requirement already has an active exact binding",
                code="RESOURCE_BINDING_CONFLICT",
            )
        try:
            identifier = uuid5(
                _NAMESPACE,
                "workflow-resource-binding/v1|project=" + project_id
                + "|instance=" + workflow_instance_id
                + "|requirement=" + requirement_key
                + "|resource=" + resource_id
                + "|idempotency=" + idempotency_key,
            )
            now = self._clock()
            binding = WorkflowResourceBinding(
                binding_id="resource-binding-" + identifier.hex,
                project_id=project_id,
                workflow_instance_id=workflow_instance_id,
                workflow_definition_id=instance.workflow_definition_id,
                workflow_version=instance.workflow_version,
                requirement_key=requirement_key,
                resource_id=resource_id,
                expected_content_checksum=resource.expected_content_checksum,
                state=ResourceBindingState.ACTIVE,
                idempotency_key=idempotency_key,
                created_at=now,
                updated_at=now,
            )
        except (TypeError, ValueError) as error:
            raise ApplicationCodedValidationError(
                str(error), code="RESOURCE_BINDING_INVALID"
            ) from error
        self._uow.resource_references.add_binding(binding)
        self._uow.commit()
        return binding

    def list_bindings(
        self, project_id: str, workflow_instance_id: str, *, offset=0, limit=100
    ):
        self._require_project(project_id)
        instance = self._uow.workflow_foundation.get_workflow_instance(
            workflow_instance_id
        )
        if instance is None or instance.project_id != project_id:
            raise ApplicationCodedAuthorizationError(
                "Workflow Instance is outside the Project scope",
                code="PROJECT_SCOPE_MISMATCH",
            )
        return self._uow.resource_references.list_bindings(
            project_id, workflow_instance_id, offset=offset, limit=limit
        )

    def binding_projections(self, project_id: str, workflow_instance_id: str):
        bindings = self.list_bindings(project_id, workflow_instance_id)
        resources, _ = self.list_resources(project_id, offset=0, limit=100)
        by_id = {item.resource_id: item for item in resources}
        try:
            return tuple((binding, by_id[binding.resource_id]) for binding in bindings)
        except KeyError as error:
            raise ApplicationCodedConflictError(
                "Resource binding authority is incomplete",
                code="RESOURCE_BINDING_CONFLICT",
            ) from error

    def _require_project(self, project_id: str):
        value = self._uow.project_manifests.get_project(project_id)
        if value is None:
            raise ApplicationCodedNotFoundError(
                "Project not found", code="PROJECT_NOT_FOUND"
            )
        return value
