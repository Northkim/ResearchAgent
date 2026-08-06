"""Atomic persistence boundary spanning all repository ports."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.execution_events.ports import ExecutionEventStore
from backend.progress_reports.ports import ProgressReportRepository
from backend.local_projects.ports import LocalProjectRepository
from backend.project_workspaces.ports import (
    ProjectManifestRepository,
    WorkflowFoundationRepository,
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
