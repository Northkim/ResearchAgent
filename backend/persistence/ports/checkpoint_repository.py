"""Append-only Domain checkpoint persistence port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.domain.models import Checkpoint
from backend.persistence.models import CheckpointBoundary, CheckpointRecord


class CheckpointRepository(ABC):
    @abstractmethod
    def save(
        self,
        checkpoint: Checkpoint,
        *,
        boundary: CheckpointBoundary,
        step_id: str | None = None,
        attempt: int | None = None,
    ) -> CheckpointRecord:
        """Stage an idempotent append of checkpoint boundary metadata."""

    @abstractmethod
    def get_latest(self, workflow_run_id: str) -> Checkpoint | None:
        """Return the highest-sequence unique Domain checkpoint."""

    @abstractmethod
    def list(self, workflow_run_id: str) -> tuple[Checkpoint, ...]:
        """List unique Domain checkpoints in sequence order."""

    @abstractmethod
    def list_records(self, workflow_run_id: str) -> tuple[CheckpointRecord, ...]:
        """List all boundary records, including multiple labels per checkpoint."""

    def boundaries_for(self, workflow_run_id: str) -> tuple[CheckpointBoundary, ...]:
        return tuple(record.boundary for record in self.list_records(workflow_run_id))
