"""Typed failures at Skill System contract boundaries."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class SkillSystemError(Exception):
    """Base class for Skill System failures."""


class InvalidSkillDefinitionError(SkillSystemError):
    """Raised when immutable skill metadata violates the contract."""


class InvalidSkillReferenceError(SkillSystemError):
    """Raised when a pinned skill reference cannot be parsed."""


class DuplicateSkillRegistrationError(SkillSystemError):
    """Raised when the same name and immutable version are registered twice."""


class SkillNotFoundError(SkillSystemError):
    """Raised when an exact registered skill version cannot be found."""


class SkillValidationError(SkillSystemError):
    """Raised when a skill input or output does not conform to its schema."""

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


class SkillDecisionMismatchError(SkillSystemError):
    """Raised when executor arguments do not match the immutable StepReady decision."""


class SkillExecutionFailure(SkillSystemError):
    """A normalized failure deliberately reported by a skill implementation."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = dict(details or {})
        super().__init__(message)
