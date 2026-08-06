"""Cloud desired-state use cases for Workflow catalog and Project instances."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timezone
from typing import Callable

from backend.application.errors import (
    ApplicationCodedAuthorizationError,
    ApplicationCodedConflictError,
    ApplicationCodedNotFoundError,
    ApplicationCodedValidationError,
)
from backend.local_projects import LocalProject
from backend.persistence.ports import UnitOfWork

from .contracts import (
    CloudProject,
    CloudProjectStatus,
    DesiredProjectManifest,
    ProjectManifestEntry,
    ProjectWorkflowInstance,
    WorkflowCapsuleVersion,
    WorkflowDefinition,
    WorkflowDefinitionLifecycle,
    WorkflowDefinitionVersion,
    WorkflowInstanceDesiredState,
    WorkflowReviewStatus,
    WorkspaceBootstrapDescriptor,
)
from .errors import ManifestRevisionConflictError
from .legacy import (
    initial_manifest_idempotency_key,
    legacy_workflow_instance_id,
    workspace_id_for_project,
)
from .manifest import build_desired_manifest, mutation_idempotency_key
from .bootstrap import build_workspace_bootstrap_descriptor
from .service import ensure_literature_search_foundation


class ProjectWorkspaceApplicationService:
    """Transaction orchestrator; routers never own persistence decisions."""

    def __init__(
        self,
        *,
        unit_of_work: UnitOfWork,
        clock: Callable[[], datetime],
        instance_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._uow = unit_of_work
        self._clock = clock
        self._instance_id_factory = instance_id_factory or (
            lambda: "wfi-" + uuid.uuid4().hex
        )

    def initialize_project(self, project: LocalProject) -> None:
        """Bridge legacy Project creation into canonical desired state atomically."""

        now = _parse_timestamp(project.created_at)
        definition, version, capsule = ensure_literature_search_foundation(
            self._uow, now=now
        )
        canonical = CloudProject(
            project_id=project.project_id,
            workspace_id=workspace_id_for_project(project.project_id),
            name=project.name,
            research_topic=project.research_topic,
            status=CloudProjectStatus.ACTIVE,
            current_manifest_revision=1,
            legacy_local_project_id=project.project_id,
            created_at=now,
            updated_at=now,
        )
        instance = ProjectWorkflowInstance(
            workflow_instance_id=legacy_workflow_instance_id(project.project_id),
            project_id=project.project_id,
            workflow_definition_id=definition.workflow_definition_id,
            workflow_version=version.version,
            capsule_id=capsule.capsule_id,
            capsule_version=capsule.capsule_version,
            desired_state=WorkflowInstanceDesiredState.ACTIVE,
            display_name=definition.display_name,
            created_manifest_revision=1,
            retired_manifest_revision=None,
            legacy_package_id=None,
            created_at=now,
            updated_at=now,
        )
        manifest, entries = build_desired_manifest(
            project=canonical,
            instances=(instance,),
            capsules={(capsule.capsule_id, capsule.capsule_version): capsule},
            revision=1,
            base_revision=0,
            idempotency_key=initial_manifest_idempotency_key(project.project_id),
            now=now,
        )
        self._uow.project_manifests.add_project(canonical)
        self._uow.workflow_foundation.add_workflow_instance(instance)
        self._uow.project_manifests.add_manifest(manifest)
        self._uow.project_manifests.add_manifest_entries(entries)

    def list_catalog(self) -> tuple[WorkflowDefinition, ...]:
        return self._uow.workflow_foundation.list_definitions()

    def get_catalog_definition(self, workflow_definition_id: str) -> WorkflowDefinition:
        definition = self._uow.workflow_foundation.get_definition(
            workflow_definition_id
        )
        if definition is None:
            raise ApplicationCodedNotFoundError(
                "Workflow Definition not found", code="WORKFLOW_DEFINITION_NOT_FOUND"
            )
        return definition

    def versions_for(
        self, workflow_definition_id: str
    ) -> tuple[WorkflowDefinitionVersion, ...]:
        return self._uow.workflow_foundation.list_definition_versions(
            workflow_definition_id
        )

    def capsules_for(
        self, workflow_definition_id: str
    ) -> tuple[WorkflowCapsuleVersion, ...]:
        return self._uow.workflow_foundation.list_capsule_versions(
            workflow_definition_id
        )

    def list_instances(self, project_id: str) -> tuple[ProjectWorkflowInstance, ...]:
        self._require_project(project_id)
        return self._uow.workflow_foundation.list_workflow_instances(project_id)

    def get_instance(
        self, project_id: str, instance_id: str
    ) -> ProjectWorkflowInstance:
        self._require_project(project_id)
        instance = self._uow.workflow_foundation.get_workflow_instance(instance_id)
        if instance is None:
            raise ApplicationCodedNotFoundError(
                "Workflow Instance not found", code="WORKFLOW_INSTANCE_NOT_FOUND"
            )
        if instance.project_id != project_id:
            raise ApplicationCodedAuthorizationError(
                "Workflow Instance is outside the Project scope",
                code="PROJECT_SCOPE_MISMATCH",
            )
        return instance

    def current_manifest(self, project_id: str) -> DesiredProjectManifest:
        self._require_project(project_id)
        manifest = self._uow.project_manifests.get_current_manifest(project_id)
        if manifest is None:
            raise ApplicationCodedNotFoundError(
                "Desired Project Manifest not found", code="PROJECT_MANIFEST_NOT_FOUND"
            )
        return manifest

    def workspace_bootstrap(self, project_id: str) -> WorkspaceBootstrapDescriptor:
        project = self._require_project(project_id)
        manifest = self.current_manifest(project_id)
        local_project = self._uow.local_projects.get(project_id)
        if local_project is None:
            raise ApplicationCodedConflictError(
                "Workspace bootstrap requires the compatible local Project record",
                code="WORKSPACE_BOOTSTRAP_NOT_AVAILABLE",
            )
        entries = self._uow.project_manifests.list_manifest_entries(
            project_id, manifest.manifest_revision
        )
        instances = self._uow.workflow_foundation.list_workflow_instances(project_id)
        capsules: dict[tuple[str, str], WorkflowCapsuleVersion] = {}
        for instance in instances:
            if instance.capsule_id is None or instance.capsule_version is None:
                continue
            capsule = self._uow.workflow_foundation.get_capsule_version(
                instance.capsule_id, instance.capsule_version
            )
            if capsule is not None:
                capsules[(capsule.capsule_id, capsule.capsule_version)] = capsule
        return build_workspace_bootstrap_descriptor(
            project=project,
            local_project=local_project,
            manifest=manifest,
            entries=entries,
            instances=instances,
            capsules=capsules,
        )

    def create_instance(
        self,
        *,
        project_id: str,
        workflow_definition_id: str,
        workflow_version: str,
        capsule_id: str,
        capsule_version: str,
        display_name: str | None,
        base_revision: int,
    ) -> ProjectWorkflowInstance:
        project = self._require_project(project_id)
        definition, version, capsule = self._require_creatable_pin(
            workflow_definition_id=workflow_definition_id,
            workflow_version=workflow_version,
            capsule_id=capsule_id,
            capsule_version=capsule_version,
        )
        now = _utc(self._clock())
        revision = base_revision + 1
        instance = ProjectWorkflowInstance(
            workflow_instance_id=self._instance_id_factory(),
            project_id=project_id,
            workflow_definition_id=definition.workflow_definition_id,
            workflow_version=version.version,
            capsule_id=capsule.capsule_id,
            capsule_version=capsule.capsule_version,
            desired_state=WorkflowInstanceDesiredState.ACTIVE,
            display_name=display_name or definition.display_name,
            created_manifest_revision=revision,
            retired_manifest_revision=None,
            legacy_package_id=None,
            created_at=now,
            updated_at=now,
        )
        try:
            next_revision = self._uow.project_manifests.compare_and_swap_revision(
                project_id=project_id,
                base_revision=base_revision,
                updated_at=now,
            )
            if next_revision != revision:
                raise RuntimeError("manifest revision did not advance exactly once")
            self._uow.workflow_foundation.add_workflow_instance(instance)
            all_instances = (*self._uow.workflow_foundation.list_workflow_instances(project_id),)
            manifest, entries = self._build_mutation_manifest(
                project=project,
                instances=all_instances,
                revision=revision,
                base_revision=base_revision,
                operation_key=f"create:{instance.workflow_instance_id}",
                now=now,
            )
            self._uow.project_manifests.add_manifest(manifest)
            self._uow.project_manifests.add_manifest_entries(entries)
            self._uow.commit()
        except ManifestRevisionConflictError as error:
            self._uow.rollback()
            raise _revision_conflict(error) from error
        except Exception:
            self._uow.rollback()
            raise
        return instance

    def retire_instance(
        self, *, project_id: str, instance_id: str, base_revision: int
    ) -> ProjectWorkflowInstance:
        project = self._require_project(project_id)
        instance = self.get_instance(project_id, instance_id)
        if instance.desired_state is WorkflowInstanceDesiredState.RETIRED:
            raise ApplicationCodedConflictError(
                "Workflow Instance is already retired",
                code="WORKFLOW_INSTANCE_INVALID_STATE",
            )
        now = _utc(self._clock())
        revision = base_revision + 1
        retired = replace(
            instance,
            desired_state=WorkflowInstanceDesiredState.RETIRED,
            retired_manifest_revision=revision,
            updated_at=now,
        )
        try:
            next_revision = self._uow.project_manifests.compare_and_swap_revision(
                project_id=project_id,
                base_revision=base_revision,
                updated_at=now,
            )
            if next_revision != revision:
                raise RuntimeError("manifest revision did not advance exactly once")
            self._uow.workflow_foundation.save_workflow_instance(retired)
            instances = self._uow.workflow_foundation.list_workflow_instances(project_id)
            manifest, entries = self._build_mutation_manifest(
                project=project,
                instances=instances,
                revision=revision,
                base_revision=base_revision,
                operation_key=f"retire:{instance_id}",
                now=now,
            )
            self._uow.project_manifests.add_manifest(manifest)
            self._uow.project_manifests.add_manifest_entries(entries)
            self._uow.commit()
        except ManifestRevisionConflictError as error:
            self._uow.rollback()
            raise _revision_conflict(error) from error
        except Exception:
            self._uow.rollback()
            raise
        return retired

    def _require_project(self, project_id: str) -> CloudProject:
        project = self._uow.project_manifests.get_project(project_id)
        if project is None:
            raise ApplicationCodedNotFoundError(
                "Project not found", code="PROJECT_NOT_FOUND"
            )
        return project

    def _require_creatable_pin(
        self,
        *,
        workflow_definition_id: str,
        workflow_version: str,
        capsule_id: str,
        capsule_version: str,
    ) -> tuple[WorkflowDefinition, WorkflowDefinitionVersion, WorkflowCapsuleVersion]:
        definition = self.get_catalog_definition(workflow_definition_id)
        if definition.lifecycle is not WorkflowDefinitionLifecycle.AVAILABLE:
            raise ApplicationCodedConflictError(
                "Workflow Definition is not available for instance creation",
                code="WORKFLOW_UNAVAILABLE",
            )
        version = self._uow.workflow_foundation.get_definition_version(
            workflow_definition_id, workflow_version
        )
        if version is None:
            raise ApplicationCodedNotFoundError(
                "Workflow Definition Version not found",
                code="WORKFLOW_VERSION_NOT_FOUND",
            )
        if version.review_status is not WorkflowReviewStatus.REVIEWED:
            raise ApplicationCodedConflictError(
                "Workflow Definition Version is not published",
                code="WORKFLOW_VERSION_UNAVAILABLE",
            )
        capsule = self._uow.workflow_foundation.get_capsule_version(
            capsule_id, capsule_version
        )
        if capsule is None:
            raise ApplicationCodedNotFoundError(
                "Workflow Capsule Version not found", code="CAPSULE_VERSION_NOT_FOUND"
            )
        if (
            capsule.workflow_definition_id != workflow_definition_id
            or capsule.workflow_version != workflow_version
            or capsule.review_status is not WorkflowReviewStatus.REVIEWED
        ):
            raise ApplicationCodedConflictError(
                "Workflow Capsule Version is unavailable for the selected Workflow",
                code="CAPSULE_UNAVAILABLE",
            )
        return definition, version, capsule

    def _build_mutation_manifest(
        self,
        *,
        project: CloudProject,
        instances: tuple[ProjectWorkflowInstance, ...],
        revision: int,
        base_revision: int,
        operation_key: str,
        now: datetime,
    ) -> tuple[DesiredProjectManifest, tuple[ProjectManifestEntry, ...]]:
        capsules: dict[tuple[str, str], WorkflowCapsuleVersion] = {}
        for instance in instances:
            if instance.capsule_id is None or instance.capsule_version is None:
                raise ApplicationCodedConflictError(
                    "Workflow Instance lacks an exact Capsule pin",
                    code="CAPSULE_UNAVAILABLE",
                )
            capsule = self._uow.workflow_foundation.get_capsule_version(
                instance.capsule_id, instance.capsule_version
            )
            if capsule is None:
                raise ApplicationCodedConflictError(
                    "Workflow Instance Capsule pin is unavailable",
                    code="CAPSULE_UNAVAILABLE",
                )
            capsules[(capsule.capsule_id, capsule.capsule_version)] = capsule
        return build_desired_manifest(
            project=project,
            instances=instances,
            capsules=capsules,
            revision=revision,
            base_revision=base_revision,
            idempotency_key=mutation_idempotency_key(
                project_id=project.project_id,
                revision=revision,
                operation_key=operation_key,
            ),
            now=now,
        )


def _revision_conflict(error: ManifestRevisionConflictError) -> ApplicationCodedConflictError:
    return ApplicationCodedConflictError(
        "Desired Project Manifest revision conflict",
        code="MANIFEST_REVISION_CONFLICT",
        details={"expected_revision": error.expected, "current_revision": error.current},
    )


def _parse_timestamp(value: str) -> datetime:
    return _utc(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("clock must be timezone-aware")
    return value.astimezone(timezone.utc)
