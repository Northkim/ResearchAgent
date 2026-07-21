"""Artifact metadata persistence port; artifact bytes remain out of scope."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.domain.models import ArtifactMetadata


class ArtifactRepository(ABC):
    @abstractmethod
    def save(self, artifact: ArtifactMetadata) -> None:
        """Stage immutable artifact metadata."""

    @abstractmethod
    def get(self, artifact_id: str) -> ArtifactMetadata | None:
        """Retrieve artifact metadata by opaque ID."""

    @abstractmethod
    def list_for_project(self, project_id: str) -> tuple[ArtifactMetadata, ...]:
        """Return project-scoped artifacts deterministically."""
