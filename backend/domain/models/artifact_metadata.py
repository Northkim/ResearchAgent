"""Immutable metadata for a versioned artifact object."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..exceptions import DomainValidationError
from ._utils import freeze_value, require_aware, require_non_empty, utc_now


@dataclass(frozen=True, slots=True)
class ArtifactMetadata:
    """Metadata and provenance for one immutable artifact version."""

    id: str
    project_id: str
    logical_artifact_id: str
    logical_name: str
    version: int
    kind: str
    storage_ref: str
    checksum: str
    media_type: str
    size: int
    producer_run_id: str | None = None
    producer_step_run_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        for value, name in (
            (self.id, "ArtifactMetadata.id"),
            (self.project_id, "ArtifactMetadata.project_id"),
            (self.logical_artifact_id, "ArtifactMetadata.logical_artifact_id"),
            (self.logical_name, "ArtifactMetadata.logical_name"),
            (self.kind, "ArtifactMetadata.kind"),
            (self.storage_ref, "ArtifactMetadata.storage_ref"),
            (self.checksum, "ArtifactMetadata.checksum"),
            (self.media_type, "ArtifactMetadata.media_type"),
        ):
            require_non_empty(value, name)
        if self.version <= 0:
            raise DomainValidationError("ArtifactMetadata.version must be positive")
        if self.size < 0:
            raise DomainValidationError("ArtifactMetadata.size cannot be negative")
        require_aware(self.created_at, "ArtifactMetadata.created_at")
        object.__setattr__(self, "metadata", freeze_value(self.metadata))
