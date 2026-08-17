"""Transactional deterministic in-memory implementations of all repositories."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from backend.domain.enums import ApprovalRequestStatus, WorkflowRunStatus
from backend.domain.models import ApprovalRequest, ArtifactMetadata, Checkpoint, Workflow
from backend.domain.services import ExecutionState
from backend.artifact_references.contracts import (
    ArtifactDependencyBinding,
    ArtifactPresentation,
    ArtifactReference,
    WorkflowArtifactRequirement,
)
from backend.artifact_references.errors import ArtifactReferenceConflictError
from backend.artifact_references.ports import ArtifactReferenceRepository
from backend.resource_references.contracts import (
    ProjectResourceReference,
    WorkflowResourceBinding,
    WorkflowResourceRequirement,
)
from backend.resource_references.errors import ResourceReferenceConflictError
from backend.resource_references.ports import ResourceReferenceRepository
from backend.execution_events import ExecutionEvent, ExecutionEventStore
from backend.persistence.models import (
    ApprovalRecord,
    CheckpointBoundary,
    CheckpointRecord,
    MemoryRevision,
    ProviderOperationRecord,
    WorkflowExecutionRecord,
)
from backend.persistence.models._immutability import freeze_json, thaw_json
from backend.persistence.ports import (
    ApprovalRepository,
    ArtifactRepository,
    CheckpointRepository,
    DuplicateEntityError,
    MemoryRepository,
    ProviderOperationRepository,
    StaleStateError,
    UnitOfWork,
    WorkflowRepository,
)
from backend.progress_reports import ProjectProgressProjection, UploadedProgressReport
from backend.progress_reports.ports import ProgressReportRepository
from backend.local_projects import LocalProject, LocalProjectRepository
from backend.research.contracts import ProviderOperation, SettlementState
from backend.project_workspaces.contracts import (
    CloudProject,
    DesiredProjectManifest,
    ProjectManifestEntry,
    ProjectWorkflowInstance,
    SkillDefinition,
    SkillVersion,
    WorkflowDefinitionVersionSkillPin,
    WorkflowCapsuleVersion,
    WorkflowDefinition,
    WorkflowDefinitionVersion,
    WorkflowCapsuleArtifact,
    WorkspaceInstallationAcknowledgement,
)
from backend.project_workspaces.errors import (
    ManifestRevisionConflictError,
    WorkflowFoundationConflictError,
)
from backend.project_workspaces.ports import (
    ProjectManifestRepository,
    WorkflowFoundationRepository,
    WorkspaceSyncRepository,
)


@dataclass(slots=True)
class InMemoryDatabase:
    """Shared committed state used to simulate a database across UoW instances."""

    executions: dict[str, WorkflowExecutionRecord] = field(default_factory=dict)
    checkpoint_records: dict[str, tuple[CheckpointRecord, ...]] = field(
        default_factory=dict
    )
    memory_revisions: dict[tuple[str, str], tuple[MemoryRevision, ...]] = field(
        default_factory=dict
    )
    artifacts: dict[str, ArtifactMetadata] = field(default_factory=dict)
    approvals: dict[str, ApprovalRecord] = field(default_factory=dict)
    execution_events: dict[
        tuple[str, str], tuple[ExecutionEvent, ...]
    ] = field(default_factory=dict)
    provider_operations: dict[str, ProviderOperationRecord] = field(default_factory=dict)
    progress_reports: dict[str, UploadedProgressReport] = field(default_factory=dict)
    progress_projections: dict[
        tuple[str, str, str, str], ProjectProgressProjection
    ] = field(default_factory=dict)
    local_projects: dict[str, LocalProject] = field(default_factory=dict)
    workflow_definitions: dict[str, WorkflowDefinition] = field(default_factory=dict)
    workflow_definition_versions: dict[
        tuple[str, str], WorkflowDefinitionVersion
    ] = field(default_factory=dict)
    workflow_capsule_versions: dict[
        tuple[str, str], WorkflowCapsuleVersion
    ] = field(default_factory=dict)
    skill_definitions: dict[str, SkillDefinition] = field(default_factory=dict)
    skill_versions: dict[tuple[str, str], SkillVersion] = field(default_factory=dict)
    workflow_skill_pins: dict[
        tuple[str, str, int], WorkflowDefinitionVersionSkillPin
    ] = field(default_factory=dict)
    project_workflow_instances: dict[str, ProjectWorkflowInstance] = field(
        default_factory=dict
    )
    projects: dict[str, CloudProject] = field(default_factory=dict)
    desired_manifests: dict[tuple[str, int], DesiredProjectManifest] = field(
        default_factory=dict
    )
    manifest_entries: dict[str, ProjectManifestEntry] = field(default_factory=dict)
    capsule_artifacts: dict[str, WorkflowCapsuleArtifact] = field(default_factory=dict)
    installation_acknowledgements: dict[
        str, WorkspaceInstallationAcknowledgement
    ] = field(default_factory=dict)
    local_artifact_references: dict[str, ArtifactReference] = field(default_factory=dict)
    artifact_presentations: dict[str, ArtifactPresentation] = field(default_factory=dict)
    workflow_artifact_requirements: dict[
        tuple[str, str, str], WorkflowArtifactRequirement
    ] = field(default_factory=dict)
    artifact_dependency_bindings: dict[str, ArtifactDependencyBinding] = field(
        default_factory=dict
    )
    project_resource_references: dict[str, ProjectResourceReference] = field(
        default_factory=dict
    )
    workflow_resource_requirements: dict[
        tuple[str, str, str], WorkflowResourceRequirement
    ] = field(default_factory=dict)
    workflow_resource_bindings: dict[str, WorkflowResourceBinding] = field(
        default_factory=dict
    )


class InMemoryResourceReferenceRepository(ResourceReferenceRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def add_resource(self, resource: ProjectResourceReference) -> None:
        existing = self.get_resource(resource.resource_id)
        if existing is not None and existing.immutable_identity() != resource.immutable_identity():
            raise ResourceReferenceConflictError(
                "Resource immutable identity already exists with different metadata"
            )
        if existing is None:
            self._uow._project_resource_references[resource.resource_id] = resource
            self._uow._dirty_project_resource_references.add(resource.resource_id)

    def get_resource(self, resource_id: str) -> ProjectResourceReference | None:
        return self._uow._project_resource_references.get(resource_id)

    def list_resources(
        self, project_id: str, *, offset: int = 0, limit: int = 100
    ) -> tuple[ProjectResourceReference, ...]:
        values = sorted(
            (
                item for item in self._uow._project_resource_references.values()
                if item.project_id == project_id
            ),
            key=lambda item: (item.created_at, item.resource_id),
        )
        return tuple(values[offset:offset + limit])

    def count_resources(self, project_id: str) -> int:
        return sum(
            item.project_id == project_id
            for item in self._uow._project_resource_references.values()
        )

    def add_requirement(self, requirement: WorkflowResourceRequirement) -> None:
        key = (
            requirement.workflow_definition_id,
            requirement.workflow_version,
            requirement.requirement_key,
        )
        existing = self._uow._workflow_resource_requirements.get(key)
        if existing is not None and existing != requirement:
            raise ResourceReferenceConflictError(
                "Workflow Resource Requirement immutable-content conflict"
            )
        if existing is None:
            self._uow._workflow_resource_requirements[key] = requirement
            self._uow._dirty_workflow_resource_requirements.add(key)

    def get_requirement(
        self, workflow_definition_id: str, workflow_version: str, requirement_key: str
    ) -> WorkflowResourceRequirement | None:
        return self._uow._workflow_resource_requirements.get(
            (workflow_definition_id, workflow_version, requirement_key)
        )

    def list_requirements(self) -> tuple[WorkflowResourceRequirement, ...]:
        return tuple(
            self._uow._workflow_resource_requirements[key]
            for key in sorted(self._uow._workflow_resource_requirements)
        )

    def add_binding(self, binding: WorkflowResourceBinding) -> None:
        existing = self.get_binding(binding.binding_id)
        if existing is not None and existing != binding:
            raise ResourceReferenceConflictError(
                "Workflow Resource Binding immutable-content conflict"
            )
        if existing is None:
            if any(
                item.project_id == binding.project_id
                and item.workflow_instance_id == binding.workflow_instance_id
                and item.requirement_key == binding.requirement_key
                and item.state.value == "ACTIVE"
                for item in self._uow._workflow_resource_bindings.values()
            ):
                raise DuplicateEntityError(
                    "Resource requirement already has an active binding"
                )
            self._uow._workflow_resource_bindings[binding.binding_id] = binding
            self._uow._dirty_workflow_resource_bindings.add(binding.binding_id)

    def get_binding(self, binding_id: str) -> WorkflowResourceBinding | None:
        return self._uow._workflow_resource_bindings.get(binding_id)

    def get_binding_by_idempotency(
        self, project_id: str, workflow_instance_id: str, idempotency_key: str
    ) -> WorkflowResourceBinding | None:
        return next((
            item for item in self._uow._workflow_resource_bindings.values()
            if item.project_id == project_id
            and item.workflow_instance_id == workflow_instance_id
            and item.idempotency_key == idempotency_key
        ), None)

    def list_bindings(
        self, project_id: str, workflow_instance_id: str, *, offset=0, limit=100
    ) -> tuple[WorkflowResourceBinding, ...]:
        values = sorted(
            (
                item for item in self._uow._workflow_resource_bindings.values()
                if item.project_id == project_id
                and item.workflow_instance_id == workflow_instance_id
            ),
            key=lambda item: (item.requirement_key, item.created_at, item.binding_id),
        )
        return tuple(values[offset:offset + limit])

    def list_project_bindings(
        self, project_id: str
    ) -> tuple[WorkflowResourceBinding, ...]:
        return tuple(sorted(
            (
                item for item in self._uow._workflow_resource_bindings.values()
                if item.project_id == project_id
            ),
            key=lambda item: (
                item.workflow_instance_id, item.requirement_key, item.binding_id
            ),
        ))


class InMemoryArtifactReferenceRepository(ArtifactReferenceRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def add_artifact(self, artifact: ArtifactReference) -> None:
        existing = self.get_artifact(artifact.artifact_id)
        if existing is not None:
            if existing.immutable_identity() != artifact.immutable_identity():
                raise ArtifactReferenceConflictError(
                    "Artifact immutable identity already exists with different content"
                )
            return
        path_owner = next(
            (
                item
                for item in self._uow._local_artifact_references.values()
                if item.producer_progress_receipt_id
                == artifact.producer_progress_receipt_id
                and item.relative_path == artifact.relative_path
            ),
            None,
        )
        if path_owner is not None:
            raise ArtifactReferenceConflictError(
                "Progress output path is already bound to another Artifact"
            )
        self._uow._local_artifact_references[artifact.artifact_id] = artifact
        self._uow._dirty_local_artifact_references.add(artifact.artifact_id)

    def get_artifact(self, artifact_id: str) -> ArtifactReference | None:
        return self._uow._local_artifact_references.get(artifact_id)

    def list_artifacts(
        self, *, project_id, producer_workflow_instance_id=None, artifact_type=None,
        state=None, offset=0, limit=100,
    ) -> tuple[ArtifactReference, ...]:
        values = [
            item
            for item in self._uow._local_artifact_references.values()
            if item.project_id == project_id
            and (
                producer_workflow_instance_id is None
                or item.producer_workflow_instance_id == producer_workflow_instance_id
            )
            and (artifact_type is None or item.artifact_type == artifact_type)
            and (state is None or item.state.value == state)
        ]
        values.sort(key=lambda item: (-item.produced_at.timestamp(), item.artifact_id))
        return tuple(values[offset:offset + limit])

    def count_artifacts(
        self, *, project_id, producer_workflow_instance_id=None, artifact_type=None,
        state=None,
    ) -> int:
        return len(self.list_artifacts(
            project_id=project_id,
            producer_workflow_instance_id=producer_workflow_instance_id,
            artifact_type=artifact_type,
            state=state,
            limit=1_000_000,
        ))

    def list_for_progress(self, receipt_id: str) -> tuple[ArtifactReference, ...]:
        return tuple(sorted(
            (
                item
                for item in self._uow._local_artifact_references.values()
                if item.producer_progress_receipt_id == receipt_id
            ),
            key=lambda item: (item.relative_path, item.artifact_id),
        ))

    def get_presentation(self, artifact_id: str) -> ArtifactPresentation | None:
        return self._uow._artifact_presentations.get(artifact_id)

    def add_presentation(self, presentation: ArtifactPresentation) -> None:
        if presentation.artifact_id not in self._uow._local_artifact_references:
            raise ValueError("Artifact does not exist")
        existing = self.get_presentation(presentation.artifact_id)
        if existing is not None and existing.immutable_identity() != presentation.immutable_identity():
            raise ArtifactReferenceConflictError(
                "Artifact presentation is immutable and already differs"
            )
        if existing is None:
            self._uow._artifact_presentations[presentation.artifact_id] = presentation
            self._uow._dirty_artifact_presentations.add(presentation.artifact_id)

    def add_requirement(self, requirement: WorkflowArtifactRequirement) -> None:
        key = (
            requirement.workflow_definition_id,
            requirement.workflow_version,
            requirement.requirement_key,
        )
        existing = self._uow._workflow_artifact_requirements.get(key)
        if existing is not None and existing != requirement:
            raise ArtifactReferenceConflictError(
                "Workflow Artifact Requirement immutable-content conflict"
            )
        if existing is None:
            self._uow._workflow_artifact_requirements[key] = requirement
            self._uow._dirty_workflow_artifact_requirements.add(key)

    def get_requirement(
        self, workflow_definition_id: str, workflow_version: str, requirement_key: str
    ) -> WorkflowArtifactRequirement | None:
        return self._uow._workflow_artifact_requirements.get(
            (workflow_definition_id, workflow_version, requirement_key)
        )

    def list_requirements(self) -> tuple[WorkflowArtifactRequirement, ...]:
        return tuple(
            self._uow._workflow_artifact_requirements[key]
            for key in sorted(self._uow._workflow_artifact_requirements)
        )

    def add_binding(self, binding: ArtifactDependencyBinding) -> None:
        existing = self.get_binding(binding.binding_id)
        if existing is not None and existing != binding:
            raise ArtifactReferenceConflictError(
                "Artifact dependency binding immutable-content conflict"
            )
        if existing is None:
            if any(
                item.project_id == binding.project_id
                and item.consumer_workflow_instance_id
                == binding.consumer_workflow_instance_id
                and item.requirement_key == binding.requirement_key
                and item.state.value == "ACTIVE"
                for item in self._uow._artifact_dependency_bindings.values()
            ):
                raise DuplicateEntityError("Artifact requirement already has an active binding")
            self._uow._artifact_dependency_bindings[binding.binding_id] = binding
            self._uow._dirty_artifact_dependency_bindings.add(binding.binding_id)

    def save_binding(self, binding: ArtifactDependencyBinding) -> None:
        existing = self.get_binding(binding.binding_id)
        if existing is None:
            raise ValueError("Artifact dependency binding does not exist")
        immutable_fields = (
            "binding_id", "project_id", "consumer_workflow_instance_id",
            "consumer_workflow_definition_id", "consumer_workflow_version",
            "requirement_key", "artifact_id", "expected_checksum",
            "idempotency_key", "created_at",
        )
        if any(getattr(existing, field) != getattr(binding, field) for field in immutable_fields):
            raise ArtifactReferenceConflictError(
                "Artifact dependency binding immutable-content conflict"
            )
        self._uow._artifact_dependency_bindings[binding.binding_id] = binding
        self._uow._dirty_artifact_dependency_bindings.add(binding.binding_id)

    def get_binding(self, binding_id: str) -> ArtifactDependencyBinding | None:
        return self._uow._artifact_dependency_bindings.get(binding_id)

    def get_binding_by_idempotency(
        self, project_id: str, consumer_workflow_instance_id: str, idempotency_key: str
    ) -> ArtifactDependencyBinding | None:
        return next((
            item
            for item in self._uow._artifact_dependency_bindings.values()
            if item.project_id == project_id
            and item.consumer_workflow_instance_id == consumer_workflow_instance_id
            and item.idempotency_key == idempotency_key
        ), None)

    def list_bindings(
        self, project_id: str, consumer_workflow_instance_id: str, *,
        offset: int = 0, limit: int = 100,
    ) -> tuple[ArtifactDependencyBinding, ...]:
        values = sorted(
            (
                item
                for item in self._uow._artifact_dependency_bindings.values()
                if item.project_id == project_id
                and item.consumer_workflow_instance_id == consumer_workflow_instance_id
            ),
            key=lambda item: (item.requirement_key, item.created_at, item.binding_id),
        )
        return tuple(values[offset:offset + limit])

    def list_project_bindings(
        self, project_id: str
    ) -> tuple[ArtifactDependencyBinding, ...]:
        return tuple(sorted(
            (
                item
                for item in self._uow._artifact_dependency_bindings.values()
                if item.project_id == project_id
            ),
            key=lambda item: (
                item.consumer_workflow_instance_id,
                item.requirement_key,
                item.created_at,
                item.binding_id,
            ),
        ))

    def count_bindings(
        self, project_id: str, consumer_workflow_instance_id: str
    ) -> int:
        return sum(
            item.project_id == project_id
            and item.consumer_workflow_instance_id == consumer_workflow_instance_id
            for item in self._uow._artifact_dependency_bindings.values()
        )


class InMemoryWorkflowFoundationRepository(WorkflowFoundationRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def add_skill_definition(self, definition: SkillDefinition) -> None:
        self._add_immutable(
            self._uow._skill_definitions,
            definition.skill_id,
            definition,
            "Skill Definition",
        )

    def get_skill_definition(self, skill_id: str) -> SkillDefinition | None:
        return self._uow._skill_definitions.get(skill_id)

    def list_skill_definitions(self) -> tuple[SkillDefinition, ...]:
        return tuple(self._uow._skill_definitions[key] for key in sorted(
            self._uow._skill_definitions
        ))

    def add_skill_version(self, version: SkillVersion) -> None:
        self._add_immutable(
            self._uow._skill_versions,
            (version.skill_id, version.skill_version),
            version,
            "Skill Version",
        )

    def get_skill_version(
        self, skill_id: str, skill_version: str
    ) -> SkillVersion | None:
        return self._uow._skill_versions.get((skill_id, skill_version))

    def list_skill_versions(self, skill_id: str) -> tuple[SkillVersion, ...]:
        return tuple(sorted(
            (item for item in self._uow._skill_versions.values()
             if item.skill_id == skill_id),
            key=lambda item: item.skill_version,
        ))

    def list_all_skill_versions(self) -> tuple[SkillVersion, ...]:
        return tuple(sorted(
            self._uow._skill_versions.values(),
            key=lambda item: (item.skill_id, item.skill_version),
        ))

    def add_workflow_skill_pin(
        self, pin: WorkflowDefinitionVersionSkillPin
    ) -> None:
        self._add_immutable(
            self._uow._workflow_skill_pins,
            (pin.workflow_definition_id, pin.workflow_version, pin.pin_order),
            pin,
            "Workflow Skill Pin",
        )

    def list_workflow_skill_pins(
        self, workflow_definition_id: str, workflow_version: str
    ) -> tuple[WorkflowDefinitionVersionSkillPin, ...]:
        return tuple(sorted(
            (
                item for item in self._uow._workflow_skill_pins.values()
                if item.workflow_definition_id == workflow_definition_id
                and item.workflow_version == workflow_version
            ),
            key=lambda item: (item.pin_order, item.skill_id),
        ))

    def list_all_workflow_skill_pins(
        self,
    ) -> tuple[WorkflowDefinitionVersionSkillPin, ...]:
        return tuple(sorted(
            self._uow._workflow_skill_pins.values(),
            key=lambda item: (
                item.workflow_definition_id, item.workflow_version,
                item.pin_order, item.skill_id,
            ),
        ))

    def add_definition(self, definition: WorkflowDefinition) -> None:
        self._add_immutable(
            self._uow._workflow_definitions,
            definition.workflow_definition_id,
            definition,
            "Workflow Definition",
        )

    def get_definition(self, workflow_definition_id: str) -> WorkflowDefinition | None:
        return self._uow._workflow_definitions.get(workflow_definition_id)

    def get_definition_by_stable_key(self, stable_key: str) -> WorkflowDefinition | None:
        from backend.project_workspaces.literature_search import (
            LITERATURE_SEARCH_DEFINITION_ID,
            LITERATURE_SEARCH_STABLE_KEY,
        )
        if stable_key == LITERATURE_SEARCH_STABLE_KEY:
            return self.get_definition(LITERATURE_SEARCH_DEFINITION_ID)
        return self.get_definition(stable_key)

    def list_definitions(self) -> tuple[WorkflowDefinition, ...]:
        return tuple(
            sorted(
                self._uow._workflow_definitions.values(),
                key=lambda item: item.workflow_definition_id,
            )
        )

    def add_definition_version(self, version: WorkflowDefinitionVersion) -> None:
        self._add_immutable(
            self._uow._workflow_definition_versions,
            (version.workflow_definition_id, version.version),
            version,
            "Workflow Definition Version",
        )

    def get_definition_version(
        self, workflow_definition_id: str, version: str
    ) -> WorkflowDefinitionVersion | None:
        return self._uow._workflow_definition_versions.get(
            (workflow_definition_id, version)
        )

    def list_definition_versions(
        self, workflow_definition_id: str
    ) -> tuple[WorkflowDefinitionVersion, ...]:
        return tuple(sorted(
            (
                item
                for item in self._uow._workflow_definition_versions.values()
                if item.workflow_definition_id == workflow_definition_id
            ),
            key=lambda item: item.version,
        ))

    def get_instance_maturities(
        self, project_id: str, workflow_instance_ids: tuple[str, ...]
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        for instance_id in workflow_instance_ids:
            instance = self._uow._project_workflow_instances.get(instance_id)
            if instance is None or instance.project_id != project_id:
                continue
            version = self._uow._workflow_definition_versions.get(
                (instance.workflow_definition_id, instance.workflow_version)
            )
            if version is not None:
                result[instance_id] = version.core_capability_maturity.value
        return result

    def add_capsule_version(self, capsule: WorkflowCapsuleVersion) -> None:
        self._add_immutable(
            self._uow._workflow_capsule_versions,
            (capsule.capsule_id, capsule.capsule_version),
            capsule,
            "Workflow Capsule Version",
        )

    def get_capsule_version(
        self, capsule_id: str, capsule_version: str
    ) -> WorkflowCapsuleVersion | None:
        return self._uow._workflow_capsule_versions.get((capsule_id, capsule_version))

    def list_capsule_versions(
        self, workflow_definition_id: str
    ) -> tuple[WorkflowCapsuleVersion, ...]:
        return tuple(sorted(
            (
                item
                for item in self._uow._workflow_capsule_versions.values()
                if item.workflow_definition_id == workflow_definition_id
            ),
            key=lambda item: (item.capsule_version, item.capsule_id),
        ))

    def add_workflow_instance(self, instance: ProjectWorkflowInstance) -> None:
        self._add_immutable(
            self._uow._project_workflow_instances,
            instance.workflow_instance_id,
            instance,
            "Project Workflow Instance",
        )

    def get_workflow_instance(
        self, workflow_instance_id: str
    ) -> ProjectWorkflowInstance | None:
        return self._uow._project_workflow_instances.get(workflow_instance_id)

    def list_workflow_instances(
        self, project_id: str
    ) -> tuple[ProjectWorkflowInstance, ...]:
        return tuple(sorted(
            (
                item
                for item in self._uow._project_workflow_instances.values()
                if item.project_id == project_id
            ),
            key=lambda item: (item.created_at, item.workflow_instance_id),
        ))

    def save_workflow_instance(self, instance: ProjectWorkflowInstance) -> None:
        existing = self.get_workflow_instance(instance.workflow_instance_id)
        if existing is None:
            raise ValueError("Project Workflow Instance does not exist")
        immutable = lambda value: (
            value.workflow_instance_id,
            value.project_id,
            value.workflow_definition_id,
            value.workflow_version,
            value.capsule_id,
            value.capsule_version,
            value.created_manifest_revision,
            value.legacy_package_id,
        )
        if immutable(existing) != immutable(instance):
            raise WorkflowFoundationConflictError(
                "Project Workflow Instance immutable-content conflict"
            )
        self._uow._project_workflow_instances[instance.workflow_instance_id] = instance
        self._uow._dirty_project_workflow_instances.add(instance.workflow_instance_id)

    def _add_immutable(self, collection, key, value, label: str) -> None:
        existing = collection.get(key)
        if existing is not None:
            if existing != value:
                # Seed timestamps are intentionally not identity content.
                left = tuple(
                    getattr(existing, field)
                    for field in existing.__dataclass_fields__
                    if field not in {"created_at", "updated_at", "published_at"}
                )
                right = tuple(
                    getattr(value, field)
                    for field in value.__dataclass_fields__
                    if field not in {"created_at", "updated_at", "published_at"}
                )
                if left != right:
                    raise WorkflowFoundationConflictError(
                        f"{label} immutable-content conflict"
                    )
            return
        collection[key] = value
        self._uow._workflow_foundation_dirty = True


class InMemoryProjectManifestRepository(ProjectManifestRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def add_project(self, project: CloudProject) -> None:
        if project.project_id in self._uow._projects:
            raise DuplicateEntityError("Canonical Project already exists")
        self._uow._projects[project.project_id] = project
        self._uow._dirty_projects.add(project.project_id)

    def get_project(self, project_id: str) -> CloudProject | None:
        return self._uow._projects.get(project_id)

    def add_manifest(self, manifest: DesiredProjectManifest) -> None:
        key = (manifest.project_id, manifest.manifest_revision)
        if key in self._uow._desired_manifests:
            raise DuplicateEntityError("Desired Project Manifest already exists")
        self._uow._desired_manifests[key] = manifest
        self._uow._dirty_manifests.add(key)

    def add_manifest_entries(
        self, entries: tuple[ProjectManifestEntry, ...]
    ) -> None:
        for entry in entries:
            if entry.entry_id in self._uow._manifest_entries:
                raise DuplicateEntityError("Desired Project Manifest entry already exists")
            self._uow._manifest_entries[entry.entry_id] = entry
            self._uow._dirty_manifest_entries.add(entry.entry_id)

    def get_manifest(
        self, project_id: str, manifest_revision: int
    ) -> DesiredProjectManifest | None:
        return self._uow._desired_manifests.get((project_id, manifest_revision))

    def get_current_manifest(self, project_id: str) -> DesiredProjectManifest | None:
        project = self.get_project(project_id)
        if project is None or project.current_manifest_revision == 0:
            return None
        return self.get_manifest(project_id, project.current_manifest_revision)

    def list_manifest_entries(
        self, project_id: str, manifest_revision: int
    ) -> tuple[ProjectManifestEntry, ...]:
        return tuple(sorted(
            (
                item
                for item in self._uow._manifest_entries.values()
                if item.project_id == project_id
                and item.manifest_revision == manifest_revision
            ),
            key=lambda item: (item.entry_kind.value, item.entry_id),
        ))

    def compare_and_swap_revision(
        self, *, project_id: str, base_revision: int, updated_at
    ) -> int:
        project = self.get_project(project_id)
        if project is None:
            raise ValueError("Canonical Project does not exist")
        if project.current_manifest_revision != base_revision:
            raise ManifestRevisionConflictError(
                expected=base_revision,
                current=project.current_manifest_revision,
            )
        self._uow._manifest_revision_expected[project_id] = base_revision
        from dataclasses import replace

        self._uow._projects[project_id] = replace(
            project,
            current_manifest_revision=base_revision + 1,
            updated_at=updated_at,
        )
        self._uow._dirty_projects.add(project_id)
        return base_revision + 1


class InMemoryWorkspaceSyncRepository(WorkspaceSyncRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def add_capsule_artifact(self, artifact: WorkflowCapsuleArtifact) -> None:
        existing = self.get_capsule_artifact_by_id(artifact.capsule_artifact_id)
        if existing is not None and existing != artifact:
            raise DuplicateEntityError("Workflow Capsule artifact immutable-content conflict")
        if existing is None:
            self._uow._capsule_artifacts[artifact.capsule_artifact_id] = artifact
            self._uow._dirty_capsule_artifacts.add(artifact.capsule_artifact_id)

    def get_capsule_artifact(
        self, project_id: str, workflow_instance_id: str
    ) -> WorkflowCapsuleArtifact | None:
        return next((item for item in self._uow._capsule_artifacts.values()
                     if item.project_id == project_id and item.workflow_instance_id == workflow_instance_id), None)

    def get_capsule_artifact_by_id(
        self, capsule_artifact_id: str
    ) -> WorkflowCapsuleArtifact | None:
        return self._uow._capsule_artifacts.get(capsule_artifact_id)

    def list_capsule_artifacts(
        self, project_id: str
    ) -> tuple[WorkflowCapsuleArtifact, ...]:
        return tuple(sorted(
            (item for item in self._uow._capsule_artifacts.values() if item.project_id == project_id),
            key=lambda item: item.workflow_instance_id,
        ))

    def add_acknowledgement(
        self, acknowledgement: WorkspaceInstallationAcknowledgement
    ) -> None:
        existing = self.get_acknowledgement(acknowledgement.installation_id)
        if existing is not None and existing != acknowledgement:
            raise DuplicateEntityError("Installation acknowledgement immutable-content conflict")
        if existing is None:
            self._uow._installation_acknowledgements[acknowledgement.installation_id] = acknowledgement
            self._uow._dirty_installation_acknowledgements.add(acknowledgement.installation_id)

    def get_acknowledgement_by_idempotency(
        self, workspace_id: str, idempotency_key: str
    ) -> WorkspaceInstallationAcknowledgement | None:
        return next((item for item in self._uow._installation_acknowledgements.values()
                     if item.workspace_id == workspace_id and item.idempotency_key == idempotency_key), None)

    def get_acknowledgement(
        self, installation_id: str
    ) -> WorkspaceInstallationAcknowledgement | None:
        return self._uow._installation_acknowledgements.get(installation_id)

    def list_acknowledgements(
        self, project_id: str
    ) -> tuple[WorkspaceInstallationAcknowledgement, ...]:
        return tuple(sorted(
            (
                item
                for item in self._uow._installation_acknowledgements.values()
                if item.project_id == project_id
            ),
            key=lambda item: (
                item.manifest_revision,
                item.acknowledged_at,
                item.installation_id,
            ),
        ))


class InMemoryLocalProjectRepository(LocalProjectRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def add(self, project: LocalProject) -> None:
        if project.project_id in self._uow._local_projects:
            raise DuplicateEntityError(
                f"Local project {project.project_id} already exists"
            )
        self._uow._local_projects[project.project_id] = project
        self._uow._dirty_local_projects.add(project.project_id)

    def save(self, project: LocalProject) -> None:
        if project.project_id not in self._uow._local_projects:
            raise ValueError("Local project does not exist")
        self._uow._local_projects[project.project_id] = project
        self._uow._dirty_local_projects.add(project.project_id)

    def get(self, project_id: str) -> LocalProject | None:
        return self._uow._local_projects.get(project_id)

    def list_all(self) -> tuple[LocalProject, ...]:
        return tuple(
            sorted(
                self._uow._local_projects.values(),
                key=lambda project: (project.updated_at, project.project_id),
                reverse=True,
            )
        )


class InMemoryProgressReportRepository(ProgressReportRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def lock_report_identity(self, report_id: str) -> None:
        return None

    def append(self, report: UploadedProgressReport) -> None:
        existing = self._uow._progress_reports.get(report.receipt_id)
        if existing is not None:
            if existing != report:
                raise DuplicateEntityError(
                    f"Progress receipt {report.receipt_id} has conflicting content"
                )
            return
        self._uow._progress_reports[report.receipt_id] = report
        self._uow._dirty_progress_reports.add(report.receipt_id)

    def get_receipt(self, receipt_id: str) -> UploadedProgressReport | None:
        return self._uow._progress_reports.get(receipt_id)

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
        return next(
            (
                item
                for item in self._uow._progress_reports.values()
                if item.project_id == project_id
                and item.workflow_instance_id == workflow_instance_id
                and item.package_id == package_id
                and item.package_checksum == package_checksum
                and item.report_id == report_id
                and item.report_checksum == report_checksum
                and item.original_report_checksum == original_report_checksum
            ),
            None,
        )

    def list_for_project(
        self,
        project_id: str,
        *,
        package_id: str | None = None,
        workflow_instance_id: str | None = None,
    ) -> tuple[UploadedProgressReport, ...]:
        return tuple(
            sorted(
                (
                    item
                    for item in self._uow._progress_reports.values()
                    if item.project_id == project_id
                    and (package_id is None or item.package_id == package_id)
                    and (
                        workflow_instance_id is None
                        or item.workflow_instance_id == workflow_instance_id
                    )
                ),
                key=lambda item: (item.received_at, item.receipt_id),
            )
        )

    def list_by_report_id(self, report_id: str) -> tuple[UploadedProgressReport, ...]:
        return tuple(
            sorted(
                (
                    item
                    for item in self._uow._progress_reports.values()
                    if item.report_id == report_id
                ),
                key=lambda item: (item.received_at, item.receipt_id),
            )
        )

    def list_by_original_checksum(
        self,
        original_report_checksum: str,
    ) -> tuple[UploadedProgressReport, ...]:
        return tuple(
            sorted(
                (
                    item
                    for item in self._uow._progress_reports.values()
                    if item.original_report_checksum == original_report_checksum
                ),
                key=lambda item: (item.received_at, item.receipt_id),
            )
        )

    def save_projection(self, projection: ProjectProgressProjection) -> None:
        key = (
            projection.project_id,
            projection.package_id,
            projection.workflow_id,
            projection.workflow_version,
        )
        self._uow._progress_projections[key] = projection
        self._uow._dirty_progress_projections.add(key)

    def get_projection(
        self,
        *,
        project_id: str,
        package_id: str,
        workflow_id: str,
        workflow_version: str,
    ) -> ProjectProgressProjection | None:
        return self._uow._progress_projections.get(
            (project_id, package_id, workflow_id, workflow_version)
        )


class InMemoryWorkflowRepository(WorkflowRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def save(
        self,
        execution: ExecutionState,
        *,
        expected_version: int | None,
    ) -> int:
        run_id = execution.workflow_run.id
        current = self._uow._executions.get(run_id)
        if expected_version is None:
            if current is not None:
                raise StaleStateError(
                    f"WorkflowRun {run_id} already exists at persistence version "
                    f"{current.persistence_version}"
                )
            conflicting_run = next(
                (
                    record.workflow_run.id
                    for record in self._uow._executions.values()
                    if record.workflow_run.project_id
                    == execution.workflow_run.project_id
                    and record.workflow_run.idempotency_key
                    == execution.workflow_run.idempotency_key
                    and record.workflow_run.id != run_id
                ),
                None,
            )
            if conflicting_run is not None:
                raise DuplicateEntityError(
                    "Workflow execution idempotency key is already owned by "
                    f"WorkflowRun {conflicting_run}"
                )
            next_version = 1
        else:
            if current is None:
                raise StaleStateError(f"WorkflowRun {run_id} does not exist")
            if current.persistence_version != expected_version:
                raise StaleStateError(
                    f"WorkflowRun {run_id} expected persistence version "
                    f"{expected_version}; found {current.persistence_version}"
                )
            next_version = expected_version + 1

        self._uow._workflow_expected.setdefault(run_id, expected_version)
        self._uow._executions[run_id] = WorkflowExecutionRecord.from_execution(
            execution,
            persistence_version=next_version,
        )
        self._uow._dirty_workflows.add(run_id)
        return next_version

    def get(self, workflow_run_id: str) -> ExecutionState | None:
        record = self._uow._executions.get(workflow_run_id)
        return record.to_execution() if record is not None else None

    def get_version(self, workflow_run_id: str) -> int | None:
        record = self._uow._executions.get(workflow_run_id)
        return record.persistence_version if record is not None else None

    def get_by_idempotency_key(
        self,
        project_id: str,
        idempotency_key: str,
    ) -> ExecutionState | None:
        matches = [
            record
            for record in self._uow._executions.values()
            if record.workflow_run.project_id == project_id
            and record.workflow_run.idempotency_key == idempotency_key
        ]
        if not matches:
            return None
        record = min(matches, key=lambda item: item.workflow_run.id)
        return record.to_execution()

    def list_runs(
        self,
        *,
        status: WorkflowRunStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[ExecutionState, ...]:
        records = [
            record
            for record in self._uow._executions.values()
            if status is None or record.workflow_run.status is status
        ]
        records.sort(
            key=lambda record: (
                record.workflow_run.created_at,
                record.workflow_run.id,
            ),
            reverse=True,
        )
        return tuple(
            record.to_execution() for record in records[offset : offset + limit]
        )

    def count_runs(self, *, status: WorkflowRunStatus | None = None) -> int:
        return sum(
            1
            for record in self._uow._executions.values()
            if status is None or record.workflow_run.status is status
        )

    def list_definitions(self) -> tuple[Workflow, ...]:
        definitions = {
            (record.workflow.id, record.workflow.version): record.workflow
            for record in self._uow._executions.values()
        }
        return tuple(definitions[key] for key in sorted(definitions))


class InMemoryCheckpointRepository(CheckpointRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def save(
        self,
        checkpoint: Checkpoint,
        *,
        boundary: CheckpointBoundary,
        step_id: str | None = None,
        attempt: int | None = None,
    ) -> CheckpointRecord:
        checkpoint.verify_integrity()
        run_id = checkpoint.workflow_run_id
        records = list(self._uow._checkpoint_records.get(run_id, ()))
        key = (boundary, checkpoint.id, step_id, attempt)
        for record in records:
            if record.checkpoint.id == checkpoint.id and record.checkpoint != checkpoint:
                raise DuplicateEntityError(
                    f"Checkpoint ID {checkpoint.id} has conflicting immutable content"
                )
            if (
                record.boundary,
                record.checkpoint.id,
                record.step_id,
                record.attempt,
            ) == key:
                return record

        record = CheckpointRecord(
            record_sequence=len(records) + 1,
            boundary=boundary,
            checkpoint=checkpoint,
            step_id=step_id,
            attempt=attempt,
        )
        records.append(record)
        self._uow._checkpoint_records[run_id] = tuple(records)
        self._uow._dirty_checkpoint_runs.add(run_id)
        return record

    def get_latest(self, workflow_run_id: str) -> Checkpoint | None:
        checkpoints = self.list(workflow_run_id)
        return checkpoints[-1] if checkpoints else None

    def list(self, workflow_run_id: str) -> tuple[Checkpoint, ...]:
        by_id: dict[str, Checkpoint] = {}
        for record in self.list_records(workflow_run_id):
            by_id.setdefault(record.checkpoint.id, record.checkpoint)
        return tuple(sorted(by_id.values(), key=lambda item: (item.sequence, item.id)))

    def list_records(self, workflow_run_id: str) -> tuple[CheckpointRecord, ...]:
        return self._uow._checkpoint_records.get(workflow_run_id, ())


class InMemoryMemoryRepository(MemoryRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def initialize_context(
        self,
        *,
        project_id: str,
        workflow_run_id: str,
        context: Mapping[str, Any],
        producer: str,
        source_references: tuple[str, ...] = (),
    ) -> MemoryRevision:
        existing = self.history(project_id, workflow_run_id)
        if existing:
            return existing[-1]
        return self.update_context(
            project_id=project_id,
            workflow_run_id=workflow_run_id,
            updates=context,
            producer=producer,
            source_references=source_references,
        )

    def read_context(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> Mapping[str, Any]:
        revisions = self.history(project_id, workflow_run_id)
        return revisions[-1].context if revisions else freeze_json({}, path="context")

    def update_context(
        self,
        *,
        project_id: str,
        workflow_run_id: str,
        updates: Mapping[str, Any],
        producer: str,
        source_references: tuple[str, ...] = (),
    ) -> MemoryRevision:
        key = (project_id, workflow_run_id)
        revisions = list(self._uow._memory_revisions.get(key, ()))
        merged = thaw_json(revisions[-1].context) if revisions else {}
        merged.update(thaw_json(freeze_json(updates, path="updates")))
        revision = MemoryRevision(
            project_id=project_id,
            workflow_run_id=workflow_run_id,
            revision=len(revisions) + 1,
            context=merged,
            producer=producer,
            source_references=source_references,
        )
        revisions.append(revision)
        self._uow._memory_revisions[key] = tuple(revisions)
        self._uow._dirty_memory_scopes.add(key)
        return revision

    def history(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[MemoryRevision, ...]:
        return self._uow._memory_revisions.get((project_id, workflow_run_id), ())


class InMemoryArtifactRepository(ArtifactRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def save(self, artifact: ArtifactMetadata) -> None:
        existing = self._uow._artifacts.get(artifact.id)
        if existing is not None and existing != artifact:
            raise DuplicateEntityError(
                f"Artifact ID {artifact.id} has conflicting immutable metadata"
            )
        if existing is None:
            self._uow._artifacts[artifact.id] = artifact
            self._uow._dirty_artifacts.add(artifact.id)

    def get(self, artifact_id: str) -> ArtifactMetadata | None:
        return self._uow._artifacts.get(artifact_id)

    def list_for_project(self, project_id: str) -> tuple[ArtifactMetadata, ...]:
        return tuple(
            sorted(
                (
                    artifact
                    for artifact in self._uow._artifacts.values()
                    if artifact.project_id == project_id
                ),
                key=lambda item: (
                    item.logical_artifact_id,
                    item.version,
                    item.id,
                ),
            )
        )


class InMemoryApprovalRepository(ApprovalRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def save(
        self,
        approval: ApprovalRequest,
        *,
        expected_version: int | None,
    ) -> int:
        current = self._uow._approvals.get(approval.id)
        if expected_version is None:
            if current is not None:
                raise StaleStateError(
                    f"ApprovalRequest {approval.id} already exists at persistence "
                    f"version {current.persistence_version}"
                )
            next_version = 1
        else:
            if current is None:
                raise StaleStateError(
                    f"ApprovalRequest {approval.id} does not exist"
                )
            if current.persistence_version != expected_version:
                raise StaleStateError(
                    f"ApprovalRequest {approval.id} expected persistence version "
                    f"{expected_version}; found {current.persistence_version}"
                )
            next_version = expected_version + 1

        self._uow._approval_expected.setdefault(approval.id, expected_version)
        self._uow._approvals[approval.id] = ApprovalRecord.from_approval(
            approval,
            persistence_version=next_version,
        )
        self._uow._dirty_approvals.add(approval.id)
        return next_version

    def get(self, approval_id: str) -> ApprovalRequest | None:
        record = self._uow._approvals.get(approval_id)
        return record.to_approval() if record is not None else None

    def get_version(self, approval_id: str) -> int | None:
        record = self._uow._approvals.get(approval_id)
        return record.persistence_version if record is not None else None

    def get_by_fingerprint(
        self,
        project_id: str,
        workflow_run_id: str,
        request_fingerprint: str,
    ) -> ApprovalRequest | None:
        records = [
            record
            for record in self._uow._approvals.values()
            if record.project_id == project_id
            and record.workflow_run_id == workflow_run_id
            and record.request_fingerprint == request_fingerprint
        ]
        if not records:
            return None
        return max(
            records,
            key=lambda record: (record.requested_at, record.id),
        ).to_approval()

    def list_for_run(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[ApprovalRequest, ...]:
        records = sorted(
            (
                record
                for record in self._uow._approvals.values()
                if record.project_id == project_id
                and record.workflow_run_id == workflow_run_id
            ),
            key=lambda record: (record.requested_at, record.id),
        )
        return tuple(record.to_approval() for record in records)

    def list_pending_for_run(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[ApprovalRequest, ...]:
        return tuple(
            approval
            for approval in self.list_for_run(project_id, workflow_run_id)
            if approval.status is ApprovalRequestStatus.PENDING
        )

    def list_requests(
        self,
        *,
        status: ApprovalRequestStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[ApprovalRequest, ...]:
        records = [
            record
            for record in self._uow._approvals.values()
            if status is None or record.status is status
        ]
        records.sort(
            key=lambda record: (record.requested_at, record.id),
            reverse=True,
        )
        return tuple(
            record.to_approval() for record in records[offset : offset + limit]
        )

    def count_requests(
        self,
        *,
        status: ApprovalRequestStatus | None = None,
    ) -> int:
        return sum(
            1
            for record in self._uow._approvals.values()
            if status is None or record.status is status
        )

class InMemoryExecutionEventStore(ExecutionEventStore):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def append(
        self,
        event: ExecutionEvent,
        *,
        expected_sequence: int,
    ) -> ExecutionEvent:
        existing = self.get(event.id)
        if existing is not None:
            if existing != event:
                raise DuplicateEntityError(
                    f"ExecutionEvent ID {event.id} has conflicting immutable content"
                )
            return existing

        scope = (event.project_id, event.workflow_run_id)
        events = list(self._uow._execution_events.get(scope, ()))
        current_sequence = len(events)
        if expected_sequence != current_sequence:
            raise StaleStateError(
                f"Execution event stream {scope} expected sequence "
                f"{expected_sequence}; found {current_sequence}"
            )
        if event.sequence != current_sequence + 1:
            raise StaleStateError(
                f"ExecutionEvent {event.id} must use sequence "
                f"{current_sequence + 1}; received {event.sequence}"
            )

        events.append(event)
        self._uow._execution_events[scope] = tuple(events)
        self._uow._dirty_event_streams.add(scope)
        return event

    def get(self, event_id: str) -> ExecutionEvent | None:
        for events in self._uow._execution_events.values():
            for event in events:
                if event.id == event_id:
                    return event
        return None

    def latest_sequence(self, project_id: str, workflow_run_id: str) -> int:
        return len(self._uow._execution_events.get((project_id, workflow_run_id), ()))

    def list_for_run(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[ExecutionEvent, ...]:
        return self._uow._execution_events.get((project_id, workflow_run_id), ())


class InMemoryProviderOperationRepository(ProviderOperationRepository):
    def __init__(self, unit_of_work: InMemoryUnitOfWork) -> None:
        self._uow = unit_of_work

    def save(
        self,
        operation: ProviderOperation,
        *,
        expected_version: int | None,
    ) -> int:
        current = self._uow._provider_operations.get(operation.id)
        if expected_version is None:
            if current is not None:
                raise StaleStateError(
                    f"ProviderOperation {operation.id} already exists at persistence "
                    f"version {current.persistence_version}"
                )
            owner = self.get_by_idempotency_key(
                operation.project_id,
                operation.idempotency_key,
            )
            if owner is not None and owner.id != operation.id:
                raise DuplicateEntityError(
                    "Provider operation idempotency key is already owned by "
                    f"ProviderOperation {owner.id}"
                )
            next_version = 1
        else:
            if current is None:
                raise StaleStateError(
                    f"ProviderOperation {operation.id} does not exist"
                )
            if current.persistence_version != expected_version:
                raise StaleStateError(
                    f"ProviderOperation {operation.id} expected persistence version "
                    f"{expected_version}; found {current.persistence_version}"
                )
            if operation.row_version != current.operation.row_version + 1:
                raise StaleStateError(
                    f"ProviderOperation {operation.id} domain row version must advance "
                    f"from {current.operation.row_version} to "
                    f"{current.operation.row_version + 1}"
                )
            if (
                current.operation.project_id != operation.project_id
                or current.operation.workflow_run_id != operation.workflow_run_id
                or current.operation.logical_step_id != operation.logical_step_id
                or current.operation.step_run_id != operation.step_run_id
                or current.operation.provider_category is not operation.provider_category
                or current.operation.operation_kind is not operation.operation_kind
                or current.operation.provider_identity != operation.provider_identity
                or current.operation.adapter_version != operation.adapter_version
                or current.operation.model_or_endpoint != operation.model_or_endpoint
                or current.operation.idempotency_key != operation.idempotency_key
                or current.operation.request_fingerprint != operation.request_fingerprint
                or current.operation.reservation != operation.reservation
                or current.operation.is_live_provider is not operation.is_live_provider
                or current.operation.created_at != operation.created_at
            ):
                raise DuplicateEntityError(
                    "ProviderOperation immutable request identity cannot change"
                )
            next_version = expected_version + 1
        self._uow._provider_operation_expected.setdefault(operation.id, expected_version)
        self._uow._provider_operations[operation.id] = ProviderOperationRecord(
            operation=operation,
            persistence_version=next_version,
        )
        self._uow._dirty_provider_operations.add(operation.id)
        return next_version

    def get(self, operation_id: str) -> ProviderOperation | None:
        record = self._uow._provider_operations.get(operation_id)
        return record.operation if record is not None else None

    def get_version(self, operation_id: str) -> int | None:
        record = self._uow._provider_operations.get(operation_id)
        return record.persistence_version if record is not None else None

    def get_by_idempotency_key(
        self,
        project_id: str,
        idempotency_key: str,
    ) -> ProviderOperation | None:
        matches = [
            record.operation
            for record in self._uow._provider_operations.values()
            if record.operation.project_id == project_id
            and record.operation.idempotency_key == idempotency_key
        ]
        return min(matches, key=lambda item: item.id) if matches else None

    def list_for_run(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[ProviderOperation, ...]:
        operations = [
            record.operation
            for record in self._uow._provider_operations.values()
            if record.operation.project_id == project_id
            and record.operation.workflow_run_id == workflow_run_id
        ]
        operations.sort(key=lambda item: (item.created_at, item.id))
        return tuple(operations)

    def list_unsettled(
        self,
        *,
        project_id: str | None = None,
    ) -> tuple[ProviderOperation, ...]:
        operations = [
            record.operation
            for record in self._uow._provider_operations.values()
            if record.operation.settlement_state is SettlementState.UNSETTLED
            and (project_id is None or record.operation.project_id == project_id)
        ]
        operations.sort(key=lambda item: (item.updated_at, item.id))
        return tuple(operations)


class InMemoryUnitOfWork(UnitOfWork):
    """Reusable transactional view over a shared InMemoryDatabase."""

    def __init__(self, database: InMemoryDatabase | None = None) -> None:
        self.database = database or InMemoryDatabase()
        self._workflow_repository = InMemoryWorkflowRepository(self)
        self._checkpoint_repository = InMemoryCheckpointRepository(self)
        self._memory_repository = InMemoryMemoryRepository(self)
        self._artifact_repository = InMemoryArtifactRepository(self)
        self._approval_repository = InMemoryApprovalRepository(self)
        self._event_store = InMemoryExecutionEventStore(self)
        self._provider_operation_repository = InMemoryProviderOperationRepository(self)
        self._progress_report_repository = InMemoryProgressReportRepository(self)
        self._local_project_repository = InMemoryLocalProjectRepository(self)
        self._workflow_foundation_repository = InMemoryWorkflowFoundationRepository(self)
        self._project_manifest_repository = InMemoryProjectManifestRepository(self)
        self._workspace_sync_repository = InMemoryWorkspaceSyncRepository(self)
        self._artifact_reference_repository = InMemoryArtifactReferenceRepository(self)
        self._resource_reference_repository = InMemoryResourceReferenceRepository(self)
        self._refresh()

    @property
    def workflows(self) -> WorkflowRepository:
        return self._workflow_repository

    @property
    def checkpoints(self) -> CheckpointRepository:
        return self._checkpoint_repository

    @property
    def memory(self) -> MemoryRepository:
        return self._memory_repository

    @property
    def artifacts(self) -> ArtifactRepository:
        return self._artifact_repository

    @property
    def approvals(self) -> ApprovalRepository:
        return self._approval_repository

    @property
    def events(self) -> ExecutionEventStore:
        return self._event_store

    @property
    def provider_operations(self) -> ProviderOperationRepository:
        return self._provider_operation_repository

    @property
    def progress_reports(self) -> ProgressReportRepository:
        return self._progress_report_repository

    @property
    def local_projects(self) -> LocalProjectRepository:
        return self._local_project_repository

    @property
    def workflow_foundation(self) -> WorkflowFoundationRepository:
        return self._workflow_foundation_repository

    @property
    def project_manifests(self) -> ProjectManifestRepository:
        return self._project_manifest_repository

    @property
    def workspace_sync(self) -> WorkspaceSyncRepository:
        return self._workspace_sync_repository

    @property
    def artifact_references(self) -> ArtifactReferenceRepository:
        return self._artifact_reference_repository

    @property
    def resource_references(self) -> ResourceReferenceRepository:
        return self._resource_reference_repository

    def commit(self) -> None:
        self._validate_concurrency()
        for run_id in self._dirty_workflows:
            self.database.executions[run_id] = self._executions[run_id]
        for run_id in self._dirty_checkpoint_runs:
            self.database.checkpoint_records[run_id] = self._checkpoint_records[run_id]
        for scope in self._dirty_memory_scopes:
            self.database.memory_revisions[scope] = self._memory_revisions[scope]
        for artifact_id in self._dirty_artifacts:
            self.database.artifacts[artifact_id] = self._artifacts[artifact_id]
        for approval_id in self._dirty_approvals:
            self.database.approvals[approval_id] = self._approvals[approval_id]
        for scope in self._dirty_event_streams:
            self.database.execution_events[scope] = self._execution_events[scope]
        for operation_id in self._dirty_provider_operations:
            self.database.provider_operations[operation_id] = self._provider_operations[
                operation_id
            ]
        for receipt_id in self._dirty_progress_reports:
            self.database.progress_reports[receipt_id] = self._progress_reports[receipt_id]
        for key in self._dirty_progress_projections:
            self.database.progress_projections[key] = self._progress_projections[key]
        for project_id in self._dirty_local_projects:
            self.database.local_projects[project_id] = self._local_projects[project_id]
        if self._workflow_foundation_dirty or self._dirty_project_workflow_instances:
            self.database.workflow_definitions = dict(self._workflow_definitions)
            self.database.workflow_definition_versions = dict(
                self._workflow_definition_versions
            )
            self.database.workflow_capsule_versions = dict(
                self._workflow_capsule_versions
            )
            self.database.skill_definitions = dict(self._skill_definitions)
            self.database.skill_versions = dict(self._skill_versions)
            self.database.workflow_skill_pins = dict(self._workflow_skill_pins)
            self.database.project_workflow_instances = dict(
                self._project_workflow_instances
            )
        for project_id in self._dirty_projects:
            self.database.projects[project_id] = self._projects[project_id]
        for key in self._dirty_manifests:
            self.database.desired_manifests[key] = self._desired_manifests[key]
        for entry_id in self._dirty_manifest_entries:
            self.database.manifest_entries[entry_id] = self._manifest_entries[entry_id]
        for artifact_id in self._dirty_capsule_artifacts:
            self.database.capsule_artifacts[artifact_id] = self._capsule_artifacts[artifact_id]
        for installation_id in self._dirty_installation_acknowledgements:
            self.database.installation_acknowledgements[installation_id] = (
                self._installation_acknowledgements[installation_id]
            )
        for artifact_id in self._dirty_local_artifact_references:
            self.database.local_artifact_references[artifact_id] = (
                self._local_artifact_references[artifact_id]
            )
        for artifact_id in self._dirty_artifact_presentations:
            self.database.artifact_presentations[artifact_id] = (
                self._artifact_presentations[artifact_id]
            )
        for key in self._dirty_workflow_artifact_requirements:
            self.database.workflow_artifact_requirements[key] = (
                self._workflow_artifact_requirements[key]
            )
        for binding_id in self._dirty_artifact_dependency_bindings:
            self.database.artifact_dependency_bindings[binding_id] = (
                self._artifact_dependency_bindings[binding_id]
            )
        for resource_id in self._dirty_project_resource_references:
            self.database.project_resource_references[resource_id] = (
                self._project_resource_references[resource_id]
            )
        for key in self._dirty_workflow_resource_requirements:
            self.database.workflow_resource_requirements[key] = (
                self._workflow_resource_requirements[key]
            )
        for binding_id in self._dirty_workflow_resource_bindings:
            self.database.workflow_resource_bindings[binding_id] = (
                self._workflow_resource_bindings[binding_id]
            )
        self._refresh()

    def rollback(self) -> None:
        self._refresh()

    def _validate_concurrency(self) -> None:
        for run_id in self._dirty_workflows:
            expected = self._workflow_expected[run_id]
            current = self.database.executions.get(run_id)
            current_version = current.persistence_version if current is not None else None
            if current_version != expected:
                raise StaleStateError(
                    f"WorkflowRun {run_id} expected committed persistence version "
                    f"{expected}; found {current_version}"
                )
            candidate = self._executions[run_id]
            conflicting_run = next(
                (
                    record.workflow_run.id
                    for record in self.database.executions.values()
                    if record.workflow_run.project_id
                    == candidate.workflow_run.project_id
                    and record.workflow_run.idempotency_key
                    == candidate.workflow_run.idempotency_key
                    and record.workflow_run.id != run_id
                ),
                None,
            )
            if conflicting_run is not None:
                raise DuplicateEntityError(
                    "Workflow execution idempotency key was concurrently claimed by "
                    f"WorkflowRun {conflicting_run}"
                )

        for run_id in self._dirty_checkpoint_runs:
            current_count = len(self.database.checkpoint_records.get(run_id, ()))
            expected_count = self._base_checkpoint_counts.get(run_id, 0)
            if current_count != expected_count:
                raise StaleStateError(
                    f"Checkpoint stream {run_id} expected {expected_count} records; "
                    f"found {current_count}"
                )

        for scope in self._dirty_memory_scopes:
            current_count = len(self.database.memory_revisions.get(scope, ()))
            expected_count = self._base_memory_counts.get(scope, 0)
            if current_count != expected_count:
                raise StaleStateError(
                    f"Memory scope {scope} expected revision {expected_count}; "
                    f"found {current_count}"
                )

        for artifact_id in self._dirty_artifacts:
            current = self.database.artifacts.get(artifact_id)
            if current is not None and current != self._artifacts[artifact_id]:
                raise DuplicateEntityError(
                    f"Artifact ID {artifact_id} was concurrently reused"
                )

        for approval_id in self._dirty_approvals:
            expected = self._approval_expected[approval_id]
            current = self.database.approvals.get(approval_id)
            current_version = current.persistence_version if current is not None else None
            if current_version != expected:
                raise StaleStateError(
                    f"ApprovalRequest {approval_id} expected committed persistence "
                    f"version {expected}; found {current_version}"
                )
        committed_event_ids = {
            event.id
            for events in self.database.execution_events.values()
            for event in events
        }
        for scope in self._dirty_event_streams:
            current_count = len(self.database.execution_events.get(scope, ()))
            expected_count = self._base_event_counts.get(scope, 0)
            if current_count != expected_count:
                raise StaleStateError(
                    f"Execution event stream {scope} expected sequence "
                    f"{expected_count}; found {current_count}"
                )
            for event in self._execution_events[scope][expected_count:]:
                if event.id in committed_event_ids:
                    raise DuplicateEntityError(
                        f"ExecutionEvent ID {event.id} was concurrently reused"
                    )
                committed_event_ids.add(event.id)

        committed_idempotency = {
            (record.operation.project_id, record.operation.idempotency_key): operation_id
            for operation_id, record in self.database.provider_operations.items()
        }
        for operation_id in self._dirty_provider_operations:
            expected = self._provider_operation_expected[operation_id]
            current = self.database.provider_operations.get(operation_id)
            current_version = current.persistence_version if current is not None else None
            if current_version != expected:
                raise StaleStateError(
                    f"ProviderOperation {operation_id} expected committed persistence "
                    f"version {expected}; found {current_version}"
                )
            operation = self._provider_operations[operation_id].operation
            key = (operation.project_id, operation.idempotency_key)
            owner = committed_idempotency.get(key)
            if owner is not None and owner != operation_id:
                raise DuplicateEntityError(
                    "Provider operation idempotency key was concurrently claimed by "
                    f"ProviderOperation {owner}"
                )
            committed_idempotency[key] = operation_id

        for receipt_id in self._dirty_progress_reports:
            current = self.database.progress_reports.get(receipt_id)
            candidate = self._progress_reports[receipt_id]
            if current is not None and current != candidate:
                raise DuplicateEntityError(
                    f"Progress receipt {receipt_id} was concurrently reused"
                )

        for project_id in self._dirty_local_projects:
            current = self.database.local_projects.get(project_id)
            expected = self._local_project_expected.get(project_id)
            if current != expected:
                raise StaleStateError(
                    f"Local project {project_id} changed concurrently"
                )
        for project_id, expected in self._manifest_revision_expected.items():
            current = self.database.projects.get(project_id)
            current_revision = (
                current.current_manifest_revision if current is not None else None
            )
            if current_revision != expected:
                raise ManifestRevisionConflictError(
                    expected=expected,
                    current=current_revision if current_revision is not None else -1,
                )

    def _refresh(self) -> None:
        self._executions = dict(self.database.executions)
        self._checkpoint_records = dict(self.database.checkpoint_records)
        self._memory_revisions = dict(self.database.memory_revisions)
        self._artifacts = dict(self.database.artifacts)
        self._approvals = dict(self.database.approvals)
        self._execution_events = dict(self.database.execution_events)
        self._provider_operations = dict(self.database.provider_operations)
        self._progress_reports = dict(self.database.progress_reports)
        self._progress_projections = dict(self.database.progress_projections)
        self._local_projects = dict(self.database.local_projects)
        self._workflow_definitions = dict(self.database.workflow_definitions)
        self._workflow_definition_versions = dict(
            self.database.workflow_definition_versions
        )
        self._workflow_capsule_versions = dict(self.database.workflow_capsule_versions)
        self._skill_definitions = dict(self.database.skill_definitions)
        self._skill_versions = dict(self.database.skill_versions)
        self._workflow_skill_pins = dict(self.database.workflow_skill_pins)
        self._project_workflow_instances = dict(
            self.database.project_workflow_instances
        )
        self._projects = dict(self.database.projects)
        self._desired_manifests = dict(self.database.desired_manifests)
        self._manifest_entries = dict(self.database.manifest_entries)
        self._capsule_artifacts = dict(self.database.capsule_artifacts)
        self._installation_acknowledgements = dict(
            self.database.installation_acknowledgements
        )
        self._local_artifact_references = dict(
            self.database.local_artifact_references
        )
        self._artifact_presentations = dict(self.database.artifact_presentations)
        self._workflow_artifact_requirements = dict(
            self.database.workflow_artifact_requirements
        )
        self._artifact_dependency_bindings = dict(
            self.database.artifact_dependency_bindings
        )
        self._project_resource_references = dict(
            self.database.project_resource_references
        )
        self._workflow_resource_requirements = dict(
            self.database.workflow_resource_requirements
        )
        self._workflow_resource_bindings = dict(
            self.database.workflow_resource_bindings
        )
        self._base_checkpoint_counts = {
            run_id: len(records)
            for run_id, records in self.database.checkpoint_records.items()
        }
        self._base_memory_counts = {
            scope: len(revisions)
            for scope, revisions in self.database.memory_revisions.items()
        }
        self._base_event_counts = {
            scope: len(events)
            for scope, events in self.database.execution_events.items()
        }
        self._workflow_expected: dict[str, int | None] = {}
        self._approval_expected: dict[str, int | None] = {}
        self._provider_operation_expected: dict[str, int | None] = {}
        self._local_project_expected = dict(self.database.local_projects)
        self._dirty_workflows: set[str] = set()
        self._dirty_checkpoint_runs: set[str] = set()
        self._dirty_memory_scopes: set[tuple[str, str]] = set()
        self._dirty_artifacts: set[str] = set()
        self._dirty_approvals: set[str] = set()
        self._dirty_event_streams: set[tuple[str, str]] = set()
        self._dirty_provider_operations: set[str] = set()
        self._dirty_progress_reports: set[str] = set()
        self._dirty_progress_projections: set[tuple[str, str, str, str]] = set()
        self._dirty_local_projects: set[str] = set()
        self._workflow_foundation_dirty = False
        self._dirty_project_workflow_instances: set[str] = set()
        self._dirty_projects: set[str] = set()
        self._dirty_manifests: set[tuple[str, int]] = set()
        self._dirty_manifest_entries: set[str] = set()
        self._dirty_capsule_artifacts: set[str] = set()
        self._dirty_installation_acknowledgements: set[str] = set()
        self._dirty_local_artifact_references: set[str] = set()
        self._dirty_artifact_presentations: set[str] = set()
        self._dirty_workflow_artifact_requirements: set[tuple[str, str, str]] = set()
        self._dirty_artifact_dependency_bindings: set[str] = set()
        self._dirty_project_resource_references: set[str] = set()
        self._dirty_workflow_resource_requirements: set[tuple[str, str, str]] = set()
        self._dirty_workflow_resource_bindings: set[str] = set()
        self._manifest_revision_expected: dict[str, int] = {}
