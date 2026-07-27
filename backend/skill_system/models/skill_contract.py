"""Execution protocol shared by registry entries and the executor."""

from __future__ import annotations

from collections.abc import Awaitable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from backend.research.ports import (
    ArtifactContentStorage,
    LLMProvider,
    PaperSearchProvider,
    SourceContentProvider,
)
from backend.research.services import ProviderOperationService
from backend.skill_system.exceptions import SkillCapabilityDeniedError

if TYPE_CHECKING:
    from .skill_definition import SkillDefinition
    from backend.skill_system.results import SkillExecutionOutput


@dataclass(frozen=True, slots=True)
class SkillCapabilities:
    """Explicit, deny-by-default capability bundle for one Skill invocation."""

    paper_search: PaperSearchProvider | None = None
    source_content: SourceContentProvider | None = None
    llm: LLMProvider | None = None
    artifact_storage: ArtifactContentStorage | None = None
    provider_operations: ProviderOperationService | None = None

    def restricted_to(self, declared: tuple[str, ...]) -> SkillCapabilities:
        """Remove grants not declared by the immutable Skill definition."""

        allowed = frozenset(declared)
        return SkillCapabilities(
            paper_search=self.paper_search if "paper_search" in allowed else None,
            source_content=self.source_content if "source_content" in allowed else None,
            llm=self.llm if "llm" in allowed else None,
            artifact_storage=(
                self.artifact_storage if "artifact_storage" in allowed else None
            ),
            provider_operations=(
                self.provider_operations if "provider_operations" in allowed else None
            ),
        )

    def require_paper_search(self) -> PaperSearchProvider:
        return self._require("paper_search", self.paper_search)

    def require_source_content(self) -> SourceContentProvider:
        return self._require("source_content", self.source_content)

    def require_llm(self) -> LLMProvider:
        return self._require("llm", self.llm)

    def require_artifact_storage(self) -> ArtifactContentStorage:
        return self._require("artifact_storage", self.artifact_storage)

    def require_provider_operations(self) -> ProviderOperationService:
        return self._require("provider_operations", self.provider_operations)

    @staticmethod
    def _require(name: str, value: Any) -> Any:
        if value is None:
            raise SkillCapabilityDeniedError(f"Skill capability {name} was not granted")
        return value


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
    capabilities: SkillCapabilities = field(default_factory=SkillCapabilities)
    project_id: str = ""


class SkillImplementation(Protocol):
    """Asynchronous framework-independent callable registered for a definition."""

    def __call__(
        self,
        inputs: Mapping[str, Any],
        context: SkillExecutionContext,
    ) -> Awaitable[Mapping[str, Any] | SkillExecutionOutput]: ...


class Skill(Protocol):
    """Conceptual executable skill interface from the architecture contract."""

    def metadata(self) -> SkillDefinition: ...

    def execute(
        self,
        inputs: Mapping[str, Any],
        context: SkillExecutionContext,
    ) -> Awaitable[Mapping[str, Any] | SkillExecutionOutput]: ...
