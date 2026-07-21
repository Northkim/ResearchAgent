"""Checkpoint data plus the application boundary that caused the write."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from backend.domain.models import Checkpoint


class CheckpointBoundary(str, Enum):
    BASELINE = "BASELINE"
    INITIALIZED = "INITIALIZED"
    STEP_READY = "STEP_READY"
    BEFORE_SKILL = "BEFORE_SKILL"
    AFTER_SKILL = "AFTER_SKILL"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    RECOVERED = "RECOVERED"
    APPROVAL_RESOLVED = "APPROVAL_RESOLVED"
    BEFORE_TERMINAL = "BEFORE_TERMINAL"
    TERMINAL = "TERMINAL"
    DOMAIN_TRANSITION = "DOMAIN_TRANSITION"


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointRecord:
    record_sequence: int
    boundary: CheckpointBoundary
    checkpoint: Checkpoint
    step_id: str | None = None
    attempt: int | None = None

    def __post_init__(self) -> None:
        if self.record_sequence <= 0:
            raise ValueError("Checkpoint record sequence must be positive")
        self.checkpoint.verify_integrity()
