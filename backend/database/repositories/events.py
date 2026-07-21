"""SQLAlchemy append-only ExecutionEventStore adapter."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.orm import ExecutionEventORM
from backend.execution_events import (
    EventPayload,
    EventSeverity,
    ExecutionEvent,
    ExecutionEventStore,
    ExecutionEventType,
)
from backend.persistence.ports import DuplicateEntityError, StaleStateError

from ._helpers import pending_by_id, pending_instances


class SQLAlchemyExecutionEventStore(ExecutionEventStore):
    def __init__(self, session: Session) -> None:
        self.session = session

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
        current_sequence = self.latest_sequence(
            event.project_id,
            event.workflow_run_id,
        )
        if expected_sequence != current_sequence:
            raise StaleStateError(
                "Execution event stream "
                f"{(event.project_id, event.workflow_run_id)} expected sequence "
                f"{expected_sequence}; found {current_sequence}"
            )
        if event.sequence != current_sequence + 1:
            raise StaleStateError(
                f"ExecutionEvent {event.id} must use sequence "
                f"{current_sequence + 1}; received {event.sequence}"
            )
        self.session.add(
            ExecutionEventORM(
                id=event.id,
                project_id=event.project_id,
                workflow_run_id=event.workflow_run_id,
                sequence=event.sequence,
                event_type=event.event_type.value,
                severity=event.severity.value,
                payload_schema_version=event.payload.schema_version,
                payload_json=dict(event.payload.to_dict()["data"]),
                request_id=event.request_id,
                occurred_at=event.occurred_at,
                agent_session_id=event.agent_session_id,
                step_run_id=event.step_run_id,
                correlation_id=event.correlation_id,
                causation_id=event.causation_id,
            )
        )
        return event

    def get(self, event_id: str) -> ExecutionEvent | None:
        row = pending_by_id(self.session, ExecutionEventORM, event_id)
        if row is None:
            row = self.session.get(ExecutionEventORM, event_id)
        return self._to_contract(row) if row is not None else None

    def latest_sequence(self, project_id: str, workflow_run_id: str) -> int:
        events = self.list_for_run(project_id, workflow_run_id)
        return events[-1].sequence if events else 0

    def list_for_run(
        self,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[ExecutionEvent, ...]:
        rows = list(
            self.session.scalars(
                select(ExecutionEventORM)
                .where(
                    ExecutionEventORM.project_id == project_id,
                    ExecutionEventORM.workflow_run_id == workflow_run_id,
                )
                .order_by(ExecutionEventORM.sequence)
            )
        )
        rows.extend(
            row
            for row in pending_instances(self.session, ExecutionEventORM)
            if row.project_id == project_id
            and row.workflow_run_id == workflow_run_id
            and row not in rows
        )
        rows.sort(key=lambda row: row.sequence)
        return tuple(self._to_contract(row) for row in rows)

    @staticmethod
    def _to_contract(row: ExecutionEventORM) -> ExecutionEvent:
        return ExecutionEvent(
            id=row.id,
            project_id=row.project_id,
            workflow_run_id=row.workflow_run_id,
            sequence=row.sequence,
            event_type=ExecutionEventType(row.event_type),
            payload=EventPayload(
                data=row.payload_json,
                schema_version=row.payload_schema_version,
            ),
            request_id=row.request_id,
            occurred_at=row.occurred_at,
            severity=EventSeverity(row.severity),
            agent_session_id=row.agent_session_id,
            step_run_id=row.step_run_id,
            correlation_id=row.correlation_id,
            causation_id=row.causation_id,
        )
