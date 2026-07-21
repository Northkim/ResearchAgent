"""Execution protocol shared by registry entries and the executor."""

from __future__ import annotations

from collections.abc import Awaitable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from .skill_definition import SkillDefinition


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillExecutionContext:
    """Read-only correlation context supplied to one skill attempt.

    Phase 3 intentionally exposes no external gateways. Future runtime phases can
    add explicitly scoped ports without granting skills workflow-state mutation.
    """

    workflow_run_id: str
    workflow_id: str
    workflow_version: str
    step_id: str
    step_run_id: str
    attempt: int


class SkillImplementation(Protocol):
    """Asynchronous framework-independent callable registered for a definition."""

    def __call__(
        self,
        inputs: Mapping[str, Any],
        context: SkillExecutionContext,
    ) -> Awaitable[Mapping[str, Any]]: ...


class Skill(Protocol):
    """Conceptual executable skill interface from the architecture contract."""

    def metadata(self) -> SkillDefinition: ...

    def execute(
        self,
        inputs: Mapping[str, Any],
        context: SkillExecutionContext,
    ) -> Awaitable[Mapping[str, Any]]: ...
