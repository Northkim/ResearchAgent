"""Project/run-scoped working-memory persistence port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from backend.persistence.models import MemoryRevision


class MemoryRepository(ABC):
    @abstractmethod
    def initialize_context(
        self,
        *,
        project_id: str,
        workflow_run_id: str,
        context: Mapping[str, Any],
        producer: str,
        source_references: tuple[str, ...] = (),
    ) -> MemoryRevision:
        """Create revision one, or return the existing latest revision."""

    @abstractmethod
    def read_context(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> Mapping[str, Any]:
        """Retrieve the latest immutable context value."""

    @abstractmethod
    def update_context(
        self,
        *,
        project_id: str,
        workflow_run_id: str,
        updates: Mapping[str, Any],
        producer: str,
        source_references: tuple[str, ...] = (),
    ) -> MemoryRevision:
        """Stage a new append-only context revision."""

    @abstractmethod
    def history(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[MemoryRevision, ...]:
        """Return revisions in ascending order."""

    def latest_revision_number(self, project_id: str, workflow_run_id: str) -> int:
        revisions = self.history(project_id, workflow_run_id)
        return revisions[-1].revision if revisions else 0
