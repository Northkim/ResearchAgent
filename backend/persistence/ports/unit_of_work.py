"""Atomic persistence boundary spanning all repository ports."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.execution_events.ports import ExecutionEventStore
from backend.artifact_references.ports import ArtifactReferenceRepository
from backend.progress_reports.ports import ProgressReportRepository
from backend.local_projects.ports import LocalProjectRepository
from backend.resource_references.ports import ResourceReferenceRepository
from backend.project_workspaces.ports import (
    ProjectManifestRepository,
    WorkflowFoundationRepository,
    WorkspaceSyncRepository,
)

from .approval_repository import ApprovalRepository
from .artifact_repository import ArtifactRepository
from .checkpoint_repository import CheckpointRepository
from .memory_repository import MemoryRepository
from .provider_operation_repository import ProviderOperationRepository
from .workflow_repository import WorkflowRepository


class UnitOfWork(ABC):
    @property
    @abstractmethod
    def workflows(self) -> WorkflowRepository: ...

    @property
    @abstractmethod
    def checkpoints(self) -> CheckpointRepository: ...

    @property
    @abstractmethod
    def memory(self) -> MemoryRepository: ...

    @property
    @abstractmethod
    def artifacts(self) -> ArtifactRepository: ...

    @property
    @abstractmethod
    def approvals(self) -> ApprovalRepository: ...

    @property
    @abstractmethod
    def events(self) -> ExecutionEventStore: ...

    @property
    @abstractmethod
    def provider_operations(self) -> ProviderOperationRepository: ...

    @property
    @abstractmethod
    def progress_reports(self) -> ProgressReportRepository: ...

    @property
    @abstractmethod
    def local_projects(self) -> LocalProjectRepository: ...

    @property
    def workflow_foundation(self) -> WorkflowFoundationRepository:
        """Optional additive local-product repository for Phase 1 adapters."""

        raise NotImplementedError("workflow foundation persistence is unavailable")

    @property
    def project_manifests(self) -> ProjectManifestRepository:
        """Optional canonical Project/Desired Manifest repository."""

        raise NotImplementedError("Project Manifest persistence is unavailable")

    @property
    def workspace_sync(self) -> WorkspaceSyncRepository:
        """Optional Capsule acquisition/installation observation repository."""

        raise NotImplementedError("Workspace sync persistence is unavailable")

    @property
    def artifact_references(self) -> ArtifactReferenceRepository:
        """Optional local-product Artifact metadata repository."""

        raise NotImplementedError("Artifact Reference persistence is unavailable")

    @property
    def resource_references(self) -> ResourceReferenceRepository:
        """Optional Project-scoped external Resource metadata repository."""

        raise NotImplementedError("Resource Reference persistence is unavailable")

    def delete_project_cloud_state(self, project_id: str) -> None:
        """Stage deletion of one Project's Cloud-owned persistence graph."""

        raise NotImplementedError("Project deletion persistence is unavailable")

    @abstractmethod
    def commit(self) -> None:
        """Atomically publish all staged repository changes."""

    @abstractmethod
    def rollback(self) -> None:
        """Discard all staged repository changes."""

    def __enter__(self) -> UnitOfWork:
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if exc_type is not None:
            self.rollback()
