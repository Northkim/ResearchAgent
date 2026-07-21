"""Immutable workflow-step definition."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ..enums import WorkflowStepKind
from ..exceptions import DomainValidationError
from ._utils import freeze_value, require_non_empty

_STEP_ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    """One immutable node in a versioned workflow DAG."""

    id: str
    kind: WorkflowStepKind
    needs: tuple[str, ...] = ()
    uses: str | None = None
    input_mapping: Mapping[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    max_attempts: int = 1
    retry_backoff: str = "exponential"
    retry_initial_seconds: float = 1.0
    retry_max_seconds: float = 30.0
    checkpoint_policy: str = "after_success"
    approval_policy: str | None = None

    def __post_init__(self) -> None:
        require_non_empty(self.id, "WorkflowStep.id")
        if not _STEP_ID_PATTERN.fullmatch(self.id):
            raise DomainValidationError(
                "WorkflowStep.id must start with a letter and contain only "
                "letters, digits, underscores, or hyphens"
            )

        object.__setattr__(self, "needs", tuple(self.needs))
        if len(set(self.needs)) != len(self.needs):
            raise DomainValidationError(f"WorkflowStep {self.id} has duplicate dependencies")
        if self.id in self.needs:
            raise DomainValidationError(f"WorkflowStep {self.id} cannot depend on itself")

        if self.kind is WorkflowStepKind.SKILL:
            if not self.uses or "@" not in self.uses:
                raise DomainValidationError(
                    f"Skill step {self.id} must pin a skill as skill_id@version"
                )
            if self.approval_policy is not None:
                raise DomainValidationError(
                    f"Skill step {self.id} cannot define approval_policy directly"
                )
        elif self.kind is WorkflowStepKind.APPROVAL:
            if self.uses is not None:
                raise DomainValidationError(f"Approval step {self.id} cannot define uses")
            require_non_empty(self.approval_policy or "", "WorkflowStep.approval_policy")

        if self.timeout_seconds <= 0:
            raise DomainValidationError("WorkflowStep.timeout_seconds must be positive")
        if self.max_attempts <= 0:
            raise DomainValidationError("WorkflowStep.max_attempts must be positive")
        if self.retry_backoff not in {"fixed", "linear", "exponential"}:
            raise DomainValidationError(
                "WorkflowStep.retry_backoff must be fixed, linear, or exponential"
            )
        if self.retry_initial_seconds < 0:
            raise DomainValidationError(
                "WorkflowStep.retry_initial_seconds cannot be negative"
            )
        if self.retry_max_seconds < self.retry_initial_seconds:
            raise DomainValidationError(
                "WorkflowStep.retry_max_seconds cannot be smaller than "
                "retry_initial_seconds"
            )
        if self.checkpoint_policy != "after_success":
            raise DomainValidationError(
                "V1 supports only the after_success checkpoint policy"
            )

        object.__setattr__(self, "input_mapping", freeze_value(self.input_mapping))
