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
from .presets import resolve_project_setup
from .bootstrap import build_workspace_bootstrap_descriptor
from .service import (
    ensure_literature_search_foundation,
    ensure_production_workflow_foundation,
)


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
        self._skill_projection_cache = None
        self._skill_version_cache = None

    def initialize_project(self, project: LocalProject) -> None:
        """Bridge an existing pre-B7 Project without changing its immutable pins."""

        definition, version, capsule = ensure_literature_search_foundation(
            self._uow, now=_parse_timestamp(project.created_at)
        )
        self._initialize_project_with_pin(project, definition, version, capsule)

    def initialize_new_project(self, project: LocalProject) -> None:
        """Create a post-B7 Project on the reviewed production Literature pin."""

        now = _parse_timestamp(project.created_at)
        definition, version, capsule, _, _, _ = ensure_production_workflow_foundation(
            self._uow, now=now
        )
        self._initialize_project_with_pin(project, definition, version, capsule)

    def initialize_project_setup(
        self,
        project: LocalProject,
        setup: str,
        custom_workflow_definition_ids: tuple[str, ...],
    ) -> None:
        """Atomically translate one product setup into revision-1 instances."""

        now = _parse_timestamp(project.created_at)
        ensure_production_workflow_foundation(self._uow, now=now)
        try:
            workflow_ids = resolve_project_setup(
                setup, custom_workflow_definition_ids
            )
        except ValueError as error:
            raise ApplicationCodedValidationError(
                str(error), code="PROJECT_WORKFLOW_SETUP_INVALID"
            ) from error
        pins = tuple(self._current_creatable_pin(item) for item in workflow_ids)
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
        instances = tuple(
            ProjectWorkflowInstance(
                workflow_instance_id=(
                    legacy_workflow_instance_id(project.project_id)
                    if index == 0 and definition.workflow_definition_id
                    == "literature-search-local-experimental"
                    else self._instance_id_factory()
                ),
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
            for index, (definition, version, capsule) in enumerate(pins)
        )
        capsules = {
            (capsule.capsule_id, capsule.capsule_version): capsule
            for _, _, capsule in pins
        }
        manifest, entries = build_desired_manifest(
            project=canonical,
            instances=instances,
            capsules=capsules,
            revision=1,
            base_revision=0,
            idempotency_key=initial_manifest_idempotency_key(project.project_id),
            now=now,
        )
        self._uow.project_manifests.add_project(canonical)
        for instance in instances:
            self._uow.workflow_foundation.add_workflow_instance(instance)
        self._uow.project_manifests.add_manifest(manifest)
        self._uow.project_manifests.add_manifest_entries(entries)

    def _initialize_project_with_pin(
        self,
        project: LocalProject,
        definition: WorkflowDefinition,
        version: WorkflowDefinitionVersion,
        capsule: WorkflowCapsuleVersion,
    ) -> None:
        now = _parse_timestamp(project.created_at)
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

    def requirements_for(self, workflow_definition_id: str, workflow_version: str):
        return tuple(
            item for item in self._uow.artifact_references.list_requirements()
            if item.workflow_definition_id == workflow_definition_id
            and item.workflow_version == workflow_version
        )

    def list_skills(self, *, offset: int = 0, limit: int = 50):
        if offset < 0 or not 1 <= limit <= 100:
            raise ApplicationCodedValidationError(
                "Skill pagination is outside the supported bound",
                code="SKILL_PAGINATION_INVALID",
            )
        values = self._uow.workflow_foundation.list_skill_definitions()
        return values[offset:offset + limit], len(values)

    def get_skill(self, skill_id: str):
        definition = self._uow.workflow_foundation.get_skill_definition(skill_id)
        if definition is None:
            raise ApplicationCodedNotFoundError(
                "Skill Definition not found", code="SKILL_DEFINITION_NOT_FOUND"
            )
        return definition

    def skill_versions_for(self, skill_id: str):
        if self._skill_version_cache is None:
            values = {}
            for item in self._uow.workflow_foundation.list_all_skill_versions():
                values.setdefault(item.skill_id, []).append(item)
            self._skill_version_cache = {
                key: tuple(sorted(items, key=lambda item: item.skill_version))
                for key, items in values.items()
            }
        return self._skill_version_cache.get(skill_id, ())

    def skill_projections_for(
        self, workflow_definition_id: str, workflow_version: str
    ):
        if self._skill_projection_cache is None:
            definitions = {
                item.skill_id: item
                for item in self._uow.workflow_foundation.list_skill_definitions()
            }
            versions = {
                (item.skill_id, item.skill_version): item
                for items in (
                    self.skill_versions_for(skill_id)
                    for skill_id in definitions
                )
                for item in items
            }
            values = {}
            for pin in self._uow.workflow_foundation.list_all_workflow_skill_pins():
                definition = definitions.get(pin.skill_id)
                version = versions.get((pin.skill_id, pin.skill_version))
                if definition is None or version is None:
                    raise ApplicationCodedConflictError(
                        "Workflow Skill projection references missing authority",
                        code="WORKFLOW_SKILL_PIN_INVALID",
                    )
                if version.content_checksum != pin.skill_checksum:
                    raise ApplicationCodedConflictError(
                        "Workflow Skill pin checksum conflicts with Skill Version",
                        code="WORKFLOW_SKILL_PIN_INVALID",
                    )
                values.setdefault(
                    (pin.workflow_definition_id, pin.workflow_version), []
                ).append((pin, definition, version))
            self._skill_projection_cache = {
                key: tuple(sorted(items, key=lambda item: item[0].pin_order))
                for key, items in values.items()
            }
        return self._skill_projection_cache.get(
            (workflow_definition_id, workflow_version), ()
        )

    def workflow_usages_for_skill(self, skill_id: str):
        self.skill_projections_for("__cache__", "0.0.0")
        return tuple(
            (workflow_id, workflow_version, pin, definition, version)
            for (workflow_id, workflow_version), items
            in self._skill_projection_cache.items()
            for pin, definition, version in items
            if pin.skill_id == skill_id
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

    def _current_creatable_pin(
        self, workflow_definition_id: str
    ) -> tuple[WorkflowDefinition, WorkflowDefinitionVersion, WorkflowCapsuleVersion]:
        definition = self.get_catalog_definition(workflow_definition_id)
        if definition.lifecycle is not WorkflowDefinitionLifecycle.AVAILABLE:
            raise ApplicationCodedConflictError(
                "Workflow Definition is not available for Project setup",
                code="WORKFLOW_UNAVAILABLE",
            )
        versions = sorted(
            (
                item for item in self.versions_for(workflow_definition_id)
                if item.review_status is WorkflowReviewStatus.REVIEWED
                and item.published_at is not None
                and item.compatibility.get("default_project_setup", True) is True
            ),
            key=lambda item: _semver_key(item.version),
        )
        if not versions:
            raise ApplicationCodedConflictError(
                "Workflow has no published current version",
                code="WORKFLOW_VERSION_UNAVAILABLE",
            )
        version = versions[-1]
        capsules = sorted(
            (
                item for item in self.capsules_for(workflow_definition_id)
                if item.workflow_version == version.version
                and item.review_status is WorkflowReviewStatus.REVIEWED
            ),
            key=lambda item: (_semver_key(item.capsule_version), item.capsule_id),
        )
        if not capsules:
            raise ApplicationCodedConflictError(
                "Workflow has no published current Capsule",
                code="CAPSULE_UNAVAILABLE",
            )
        return definition, version, capsules[-1]

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


def _semver_key(value: str) -> tuple[int, int, int, str]:
    core, _, suffix = value.partition("-")
    major, minor, patch = core.split(".")
    return int(major), int(minor), int(patch), suffix
