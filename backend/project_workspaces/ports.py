"""Persistence port for the Project Workspace Phase 1 entities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from .contracts import (
    CloudProject,
    DesiredProjectManifest,
    ProjectManifestEntry,
    ProjectWorkflowInstance,
    WorkflowCapsuleVersion,
    WorkflowDefinition,
    WorkflowDefinitionVersion,
    WorkflowCapsuleArtifact,
    WorkspaceInstallationAcknowledgement,
)


class WorkflowFoundationRepository(ABC):
    @abstractmethod
    def add_definition(self, definition: WorkflowDefinition) -> None: ...

    @abstractmethod
    def get_definition(self, workflow_definition_id: str) -> WorkflowDefinition | None: ...

    @abstractmethod
    def get_definition_by_stable_key(self, stable_key: str) -> WorkflowDefinition | None: ...

    @abstractmethod
    def list_definitions(self) -> tuple[WorkflowDefinition, ...]: ...

    @abstractmethod
    def add_definition_version(self, version: WorkflowDefinitionVersion) -> None: ...

    @abstractmethod
    def get_definition_version(
        self, workflow_definition_id: str, version: str
    ) -> WorkflowDefinitionVersion | None: ...

    @abstractmethod
    def list_definition_versions(
        self, workflow_definition_id: str
    ) -> tuple[WorkflowDefinitionVersion, ...]: ...

    @abstractmethod
    def add_capsule_version(self, capsule: WorkflowCapsuleVersion) -> None: ...

    @abstractmethod
    def get_capsule_version(
        self, capsule_id: str, capsule_version: str
    ) -> WorkflowCapsuleVersion | None: ...

    @abstractmethod
    def list_capsule_versions(
        self, workflow_definition_id: str
    ) -> tuple[WorkflowCapsuleVersion, ...]: ...

    @abstractmethod
    def add_workflow_instance(self, instance: ProjectWorkflowInstance) -> None: ...

    @abstractmethod
    def get_workflow_instance(
        self, workflow_instance_id: str
    ) -> ProjectWorkflowInstance | None: ...

    @abstractmethod
    def list_workflow_instances(
        self, project_id: str
    ) -> tuple[ProjectWorkflowInstance, ...]: ...

    @abstractmethod
    def save_workflow_instance(self, instance: ProjectWorkflowInstance) -> None: ...


class ProjectManifestRepository(ABC):
    @abstractmethod
    def add_project(self, project: CloudProject) -> None: ...

    @abstractmethod
    def get_project(self, project_id: str) -> CloudProject | None: ...

    @abstractmethod
    def add_manifest(self, manifest: DesiredProjectManifest) -> None: ...

    @abstractmethod
    def add_manifest_entries(
        self, entries: tuple[ProjectManifestEntry, ...]
    ) -> None: ...

    @abstractmethod
    def get_manifest(
        self, project_id: str, manifest_revision: int
    ) -> DesiredProjectManifest | None: ...

    @abstractmethod
    def get_current_manifest(self, project_id: str) -> DesiredProjectManifest | None: ...

    @abstractmethod
    def list_manifest_entries(
        self, project_id: str, manifest_revision: int
    ) -> tuple[ProjectManifestEntry, ...]: ...

    @abstractmethod
    def compare_and_swap_revision(
        self,
        *,
        project_id: str,
        base_revision: int,
        updated_at: datetime,
    ) -> int: ...


class WorkspaceSyncRepository(ABC):
    @abstractmethod
    def add_capsule_artifact(self, artifact: WorkflowCapsuleArtifact) -> None: ...

    @abstractmethod
    def get_capsule_artifact(
        self, project_id: str, workflow_instance_id: str
    ) -> WorkflowCapsuleArtifact | None: ...

    @abstractmethod
    def get_capsule_artifact_by_id(
        self, capsule_artifact_id: str
    ) -> WorkflowCapsuleArtifact | None: ...

    @abstractmethod
    def list_capsule_artifacts(
        self, project_id: str
    ) -> tuple[WorkflowCapsuleArtifact, ...]: ...

    @abstractmethod
    def add_acknowledgement(
        self, acknowledgement: WorkspaceInstallationAcknowledgement
    ) -> None: ...

    @abstractmethod
    def get_acknowledgement_by_idempotency(
        self, workspace_id: str, idempotency_key: str
    ) -> WorkspaceInstallationAcknowledgement | None: ...

    @abstractmethod
    def get_acknowledgement(
        self, installation_id: str
    ) -> WorkspaceInstallationAcknowledgement | None: ...

    @abstractmethod
    def list_acknowledgements(
        self, project_id: str
    ) -> tuple[WorkspaceInstallationAcknowledgement, ...]: ...
