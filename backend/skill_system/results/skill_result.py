"""Serializable result values returned by SkillExecutor."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from backend.research.contracts import ProviderUsage
from backend.skill_system._immutability import freeze_json, thaw_json


@dataclass(frozen=True, slots=True)
class EmittedArtifactMetadata:
    artifact_id: str
    storage_key: str
    checksum: str
    media_type: str
    size: int
    logical_name: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.artifact_id, "artifact_id"),
            (self.storage_key, "storage_key"),
            (self.checksum, "checksum"),
            (self.media_type, "media_type"),
            (self.logical_name, "logical_name"),
        ):
            if not value:
                raise ValueError(f"EmittedArtifactMetadata.{name} cannot be empty")
        key = PurePosixPath(self.storage_key)
        if (
            "\\" in self.storage_key
            or key.is_absolute()
            or any(part in {"", ".", ".."} for part in self.storage_key.split("/"))
        ):
            raise ValueError("EmittedArtifactMetadata.storage_key must be relative and safe")
        if (
            not self.checksum.startswith("sha256:")
            or len(self.checksum) != len("sha256:") + 64
            or any(character not in "0123456789abcdef" for character in self.checksum[7:])
        ):
            raise ValueError("EmittedArtifactMetadata.checksum must be SHA-256")
        if self.size < 0:
            raise ValueError("EmittedArtifactMetadata.size cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "storage_key": self.storage_key,
            "checksum": self.checksum,
            "media_type": self.media_type,
            "size": self.size,
            "logical_name": self.logical_name,
        }


@dataclass(frozen=True, slots=True)
class SkillExecutionOutput:
    """Optional rich envelope returned by a Skill implementation.

    Plain output mappings remain supported.  This envelope is used only when a
    Skill needs to hand provider usage or already-written artifact metadata to
    the executor without gaining workflow-state mutation authority.
    """

    output_data: Mapping[str, Any]
    emitted_artifacts: tuple[EmittedArtifactMetadata, ...] = ()
    provider_usage: tuple[ProviderUsage, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "output_data",
            freeze_json(self.output_data, path="output_data"),
        )
        object.__setattr__(self, "emitted_artifacts", tuple(self.emitted_artifacts))
        object.__setattr__(self, "provider_usage", tuple(self.provider_usage))
        if any(
            not isinstance(item, EmittedArtifactMetadata)
            for item in self.emitted_artifacts
        ):
            raise ValueError("SkillExecutionOutput artifacts must be metadata contracts")
        if any(not isinstance(item, ProviderUsage) for item in self.provider_usage):
            raise ValueError("SkillExecutionOutput usage must be ProviderUsage contracts")


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
    emitted_artifacts: tuple[EmittedArtifactMetadata, ...] = ()
    provider_usage: tuple[ProviderUsage, ...] = ()

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
        object.__setattr__(self, "emitted_artifacts", tuple(self.emitted_artifacts))
        object.__setattr__(self, "provider_usage", tuple(self.provider_usage))
        if any(
            not isinstance(item, EmittedArtifactMetadata)
            for item in self.emitted_artifacts
        ):
            raise ValueError("SkillResult artifacts must be metadata contracts")
        if any(not isinstance(item, ProviderUsage) for item in self.provider_usage):
            raise ValueError("SkillResult usage must be ProviderUsage contracts")
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
        emitted_artifacts: tuple[EmittedArtifactMetadata, ...] = (),
        provider_usage: tuple[ProviderUsage, ...] = (),
    ) -> SkillResult:
        return cls(
            success=True,
            output_data=output_data,
            execution_metadata=execution_metadata,
            emitted_artifacts=emitted_artifacts,
            provider_usage=provider_usage,
        )

    @classmethod
    def failed(
        cls,
        error: SkillError,
        *,
        execution_metadata: Mapping[str, Any],
        provider_usage: tuple[ProviderUsage, ...] = (),
    ) -> SkillResult:
        return cls(
            success=False,
            error=error,
            execution_metadata=execution_metadata,
            provider_usage=provider_usage,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output_data": thaw_json(self.output_data),
            "error": self.error.to_dict() if self.error is not None else None,
            "execution_metadata": thaw_json(self.execution_metadata),
            "emitted_artifacts": [item.to_dict() for item in self.emitted_artifacts],
            "provider_usage": [item.to_dict() for item in self.provider_usage],
        }
