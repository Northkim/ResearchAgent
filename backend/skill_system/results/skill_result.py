"""Serializable result values returned by SkillExecutor."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from backend.skill_system._immutability import freeze_json, thaw_json


@dataclass(frozen=True, slots=True)
class SkillError:
    code: str
    message: str
    retryable: bool = False
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("Skill error code cannot be empty")
        if not self.message:
            raise ValueError("Skill error message cannot be empty")
        object.__setattr__(self, "details", freeze_json(self.details, path="error.details"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "details": thaw_json(self.details),
        }


@dataclass(frozen=True, slots=True)
class SkillResult:
    """The only execution outcome exposed to an Agent Runtime caller."""

    success: bool
    output_data: Mapping[str, Any] = field(default_factory=dict)
    error: SkillError | None = None
    execution_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "output_data",
            freeze_json(self.output_data, path="output_data"),
        )
        object.__setattr__(
            self,
            "execution_metadata",
            freeze_json(self.execution_metadata, path="execution_metadata"),
        )
        if self.success and self.error is not None:
            raise ValueError("Successful SkillResult cannot contain an error")
        if not self.success and self.error is None:
            raise ValueError("Failed SkillResult must contain an error")
        if not self.success and self.output_data:
            raise ValueError("Failed SkillResult cannot contain output data")

    @classmethod
    def succeeded(
        cls,
        output_data: Mapping[str, Any],
        *,
        execution_metadata: Mapping[str, Any],
    ) -> SkillResult:
        return cls(
            success=True,
            output_data=output_data,
            execution_metadata=execution_metadata,
        )

    @classmethod
    def failed(
        cls,
        error: SkillError,
        *,
        execution_metadata: Mapping[str, Any],
    ) -> SkillResult:
        return cls(
            success=False,
            error=error,
            execution_metadata=execution_metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output_data": thaw_json(self.output_data),
            "error": self.error.to_dict() if self.error is not None else None,
            "execution_metadata": thaw_json(self.execution_metadata),
        }
