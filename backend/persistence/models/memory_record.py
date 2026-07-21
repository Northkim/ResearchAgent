"""Immutable revision of project/run-scoped working context."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ._immutability import freeze_json


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryRevision:
    project_id: str
    workflow_run_id: str
    revision: int
    context: Mapping[str, Any]
    producer: str
    source_references: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.project_id or not self.workflow_run_id or not self.producer:
            raise ValueError("Memory scope and producer must be non-empty")
        if self.revision <= 0:
            raise ValueError("Memory revision must be positive")
        object.__setattr__(self, "context", freeze_json(self.context, path="context"))
        object.__setattr__(self, "source_references", tuple(self.source_references))
