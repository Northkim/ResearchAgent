"""Immutable checkpoint entity with integrity verification."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..exceptions import CheckpointIntegrityError, DomainValidationError
from ._utils import require_aware, require_non_empty


@dataclass(frozen=True, slots=True)
class Checkpoint:
    """Append-only serialized recovery point for one workflow run."""

    id: str
    workflow_run_id: str
    agent_session_id: str
    sequence: int
    state_json: str
    state_hash: str
    created_at: datetime
    parent_id: str | None = None

    def __post_init__(self) -> None:
        for value, name in (
            (self.id, "Checkpoint.id"),
            (self.workflow_run_id, "Checkpoint.workflow_run_id"),
            (self.agent_session_id, "Checkpoint.agent_session_id"),
            (self.state_json, "Checkpoint.state_json"),
            (self.state_hash, "Checkpoint.state_hash"),
        ):
            require_non_empty(value, name)
        if self.sequence <= 0:
            raise DomainValidationError("Checkpoint.sequence must be positive")
        require_aware(self.created_at, "Checkpoint.created_at")

    @classmethod
    def create(
        cls,
        *,
        checkpoint_id: str,
        workflow_run_id: str,
        agent_session_id: str,
        sequence: int,
        state: Mapping[str, Any],
        created_at: datetime,
        parent_id: str | None = None,
    ) -> Checkpoint:
        state_json = json.dumps(
            state,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        state_hash = hashlib.sha256(state_json.encode("utf-8")).hexdigest()
        return cls(
            id=checkpoint_id,
            workflow_run_id=workflow_run_id,
            agent_session_id=agent_session_id,
            sequence=sequence,
            state_json=state_json,
            state_hash=state_hash,
            created_at=created_at,
            parent_id=parent_id,
        )

    def verify_integrity(self) -> None:
        actual_hash = hashlib.sha256(self.state_json.encode("utf-8")).hexdigest()
        if actual_hash != self.state_hash:
            raise CheckpointIntegrityError(
                f"Checkpoint {self.id} failed integrity verification"
            )

    def restore_state(self) -> dict[str, Any]:
        self.verify_integrity()
        state = json.loads(self.state_json)
        if not isinstance(state, dict):
            raise CheckpointIntegrityError(
                f"Checkpoint {self.id} does not contain an object state"
            )
        return state
