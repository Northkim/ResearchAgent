"""Execution aggregate persistence port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.domain.enums import WorkflowRunStatus
from backend.domain.models import Workflow
from backend.domain.services import ExecutionState


class WorkflowRepository(ABC):
    @abstractmethod
    def save(
        self,
        execution: ExecutionState,
        *,
        expected_version: int | None,
    ) -> int:
        """Stage an insert/update and return its next persistence version."""

    def update_state(
        self,
        execution: ExecutionState,
        *,
        expected_version: int,
    ) -> int:
        return self.save(execution, expected_version=expected_version)

    @abstractmethod
    def get(self, workflow_run_id: str) -> ExecutionState | None:
        """Return a reconstituted detached aggregate without checkpoints."""

    @abstractmethod
    def get_version(self, workflow_run_id: str) -> int | None:
        """Return the persistence version used for optimistic concurrency."""

    @abstractmethod
    def get_by_idempotency_key(
        self,
        project_id: str,
        idempotency_key: str,
    ) -> ExecutionState | None:
        """Resolve an existing logical execution request."""

    @abstractmethod
    def list_runs(
        self,
        *,
        status: WorkflowRunStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[ExecutionState, ...]:
        """Return a deterministic newest-first page of detached executions."""

    @abstractmethod
    def count_runs(self, *, status: WorkflowRunStatus | None = None) -> int:
        """Count executions matching the same status filter as list_runs."""

    @abstractmethod
    def list_definitions(self) -> tuple[Workflow, ...]:
        """Return known immutable Workflow definitions in stable key order."""
