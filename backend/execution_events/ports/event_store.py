"""Append-only persistence boundary for execution events."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.execution_events.models import ExecutionEvent


class ExecutionEventStore(ABC):
    @abstractmethod
    def append(
        self,
        event: ExecutionEvent,
        *,
        expected_sequence: int,
    ) -> ExecutionEvent:
        """Stage an event after the exact expected stream sequence."""

    @abstractmethod
    def get(self, event_id: str) -> ExecutionEvent | None:
        """Return an event by its globally unique identity."""

    @abstractmethod
    def latest_sequence(self, project_id: str, workflow_run_id: str) -> int:
        """Return zero for an empty stream, otherwise its latest sequence."""

    @abstractmethod
    def list_for_run(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[ExecutionEvent, ...]:
        """Return the complete stream in strictly increasing sequence order."""

    def replay(
        self,
        project_id: str,
        workflow_run_id: str,
        *,
        after_sequence: int = 0,
    ) -> tuple[ExecutionEvent, ...]:
        """Read immutable events after a durable consumer cursor."""

        if after_sequence < 0:
            raise ValueError("after_sequence cannot be negative")
        return tuple(
            event
            for event in self.list_for_run(project_id, workflow_run_id)
            if event.sequence > after_sequence
        )
