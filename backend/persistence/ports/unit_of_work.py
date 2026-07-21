"""Atomic persistence boundary spanning all repository ports."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.execution_events.ports import ExecutionEventStore

from .approval_repository import ApprovalRepository
from .artifact_repository import ArtifactRepository
from .checkpoint_repository import CheckpointRepository
from .memory_repository import MemoryRepository
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
