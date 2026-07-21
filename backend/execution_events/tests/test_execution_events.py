"""Append ordering and replay behavior for execution event streams."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.execution_events import (
    EventPayload,
    EventSeverity,
    ExecutionEvent,
    ExecutionEventType,
)
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.persistence.ports import StaleStateError


def _event(
    sequence: int,
    event_type: ExecutionEventType,
    *,
    event_id: str | None = None,
) -> ExecutionEvent:
    severity = (
        EventSeverity.ERROR
        if event_type is ExecutionEventType.WORKFLOW_FAILED
        else EventSeverity.INFO
    )
    return ExecutionEvent(
        id=event_id or f"event-{sequence}",
        project_id="project-events",
        workflow_run_id="run-events",
        sequence=sequence,
        event_type=event_type,
        payload=EventPayload(
            data={"sequence": sequence, "event": event_type.value}
        ),
        request_id="request-events",
        occurred_at=datetime(2026, 7, 21, 9, sequence, tzinfo=UTC),
        severity=severity,
        agent_session_id="session-events",
        step_run_id="step-run-events" if sequence in {2, 3} else None,
        correlation_id="correlation-events",
        causation_id=f"event-{sequence - 1}" if sequence > 1 else None,
    )


def test_event_append_enforces_contiguous_ordering() -> None:
    database = InMemoryDatabase()
    writer = InMemoryUnitOfWork(database)
    first = _event(1, ExecutionEventType.WORKFLOW_STARTED)
    second = _event(2, ExecutionEventType.STEP_STARTED)

    writer.events.append(first, expected_sequence=0)
    writer.events.append(second, expected_sequence=1)
    assert writer.events.append(second, expected_sequence=0) is second

    with pytest.raises(StaleStateError):
        writer.events.append(
            _event(4, ExecutionEventType.SKILL_EXECUTED),
            expected_sequence=2,
        )

    writer.commit()
    reader = InMemoryUnitOfWork(database)
    assert reader.events.latest_sequence("project-events", "run-events") == 2
    assert reader.events.list_for_run("project-events", "run-events") == (
        first,
        second,
    )


def test_event_replay_survives_adapter_restart_and_cursoring() -> None:
    database = InMemoryDatabase()
    writer = InMemoryUnitOfWork(database)
    event_types = tuple(ExecutionEventType)
    events = tuple(
        _event(sequence, event_type)
        for sequence, event_type in enumerate(event_types, start=1)
    )
    for event in events:
        writer.events.append(event, expected_sequence=event.sequence - 1)
    writer.commit()

    restarted = InMemoryUnitOfWork(database)
    replayed = restarted.events.replay(
        "project-events",
        "run-events",
        after_sequence=2,
    )

    assert tuple(event.sequence for event in replayed) == (3, 4, 5, 6, 7)
    assert tuple(event.event_type for event in replayed) == event_types[2:]
    assert replayed[-1].payload.to_dict() == {
        "schema_version": 1,
        "data": {"sequence": 7, "event": "WORKFLOW_FAILED"},
    }
