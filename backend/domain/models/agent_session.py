"""Agent-session entity and lifecycle rules."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..enums import AgentSessionStatus
from ..exceptions import InvalidStateTransition
from ._utils import freeze_value, require_aware, require_non_empty, utc_now

_AGENT_SESSION_TRANSITIONS: dict[
    AgentSessionStatus, frozenset[AgentSessionStatus]
] = {
    AgentSessionStatus.CREATED: frozenset(
        {AgentSessionStatus.INITIALIZING, AgentSessionStatus.CANCELLING}
    ),
    AgentSessionStatus.INITIALIZING: frozenset(
        {
            AgentSessionStatus.ACTIVE,
            AgentSessionStatus.FAILED,
            AgentSessionStatus.CANCELLING,
        }
    ),
    AgentSessionStatus.ACTIVE: frozenset(
        {
            AgentSessionStatus.WAITING,
            AgentSessionStatus.COMPLETED,
            AgentSessionStatus.FAILED,
            AgentSessionStatus.CANCELLING,
        }
    ),
    AgentSessionStatus.WAITING: frozenset(
        {
            AgentSessionStatus.ACTIVE,
            AgentSessionStatus.FAILED,
            AgentSessionStatus.CANCELLING,
        }
    ),
    AgentSessionStatus.CANCELLING: frozenset({AgentSessionStatus.CANCELLED}),
    AgentSessionStatus.COMPLETED: frozenset(),
    AgentSessionStatus.FAILED: frozenset(),
    AgentSessionStatus.CANCELLED: frozenset(),
}


@dataclass(slots=True)
class AgentSession:
    """A runtime participant associated with one project and workflow run."""

    id: str
    project_id: str
    workflow_run_id: str
    agent_profile_ref: str
    role: str = "primary"
    status: AgentSessionStatus = AgentSessionStatus.CREATED
    state: Mapping[str, Any] = field(default_factory=dict)
    row_version: int = 0
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        for value, name in (
            (self.id, "AgentSession.id"),
            (self.project_id, "AgentSession.project_id"),
            (self.workflow_run_id, "AgentSession.workflow_run_id"),
            (self.agent_profile_ref, "AgentSession.agent_profile_ref"),
            (self.role, "AgentSession.role"),
        ):
            require_non_empty(value, name)
        require_aware(self.created_at, "AgentSession.created_at")
        require_aware(self.updated_at, "AgentSession.updated_at")
        self.state = freeze_value(self.state)

    def transition_to(
        self, target: AgentSessionStatus, *, at: datetime | None = None
    ) -> None:
        if target not in _AGENT_SESSION_TRANSITIONS[self.status]:
            raise InvalidStateTransition(
                "AgentSession", self.id, self.status.value, target.value
            )

        timestamp = at or utc_now()
        require_aware(timestamp, "AgentSession transition timestamp")
        self.status = target
        self.updated_at = timestamp
        self.row_version += 1
