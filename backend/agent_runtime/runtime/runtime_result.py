"""Immutable result returned whenever the in-memory runtime yields control."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from backend.agent_runtime._immutability import freeze_json, thaw_json
from backend.domain.enums import WorkflowRunStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeResult:
    workflow_run_id: str
    agent_session_id: str
    status: WorkflowRunStatus
    outputs: Mapping[str, Any] = field(default_factory=dict)
    wait_reason: str | None = None
    error_code: str | None = None
    completed_steps: tuple[str, ...] = field(default_factory=tuple)
    domain_checkpoint_count: int = 0
    runtime_checkpoint_count: int = 0
    memory_revision: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "outputs", freeze_json(self.outputs, path="outputs"))
        object.__setattr__(self, "completed_steps", tuple(self.completed_steps))

    @property
    def is_terminal(self) -> bool:
        return self.status.is_terminal

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_run_id": self.workflow_run_id,
            "agent_session_id": self.agent_session_id,
            "status": self.status.value,
            "outputs": thaw_json(self.outputs),
            "wait_reason": self.wait_reason,
            "error_code": self.error_code,
            "completed_steps": list(self.completed_steps),
            "domain_checkpoint_count": self.domain_checkpoint_count,
            "runtime_checkpoint_count": self.runtime_checkpoint_count,
            "memory_revision": self.memory_revision,
        }
