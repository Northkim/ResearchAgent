"""Application-facing artifact metadata/content gateway."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.domain.models import ArtifactMetadata
from backend.persistence.ports import UnitOfWork
from backend.research.contracts import sha256_bytes
from backend.research.ports import ArtifactContentStorage


class ArtifactGatewayError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CreateArtifactContent:
    id: str
    project_id: str
    workflow_run_id: str
    step_run_id: str | None
    logical_artifact_id: str
    logical_name: str
    version: int
    kind: str
    storage_key: str
    media_type: str
    content: bytes
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None


class ArtifactApplicationGateway:
    """Write bytes first, then stage immutable metadata in the caller's UoW."""

    def __init__(
        self,
        *,
        unit_of_work: UnitOfWork,
        content_storage: ArtifactContentStorage,
    ) -> None:
        self.uow = unit_of_work
        self.storage = content_storage

    def create(self, request: CreateArtifactContent) -> ArtifactMetadata:
        stored = self.storage.write_immutable(
            request.storage_key,
            request.content,
            media_type=request.media_type,
        )
        kwargs: dict[str, Any] = {}
        if request.created_at is not None:
            kwargs["created_at"] = request.created_at
        artifact = ArtifactMetadata(
            id=request.id,
            project_id=request.project_id,
            logical_artifact_id=request.logical_artifact_id,
            logical_name=request.logical_name,
            version=request.version,
            kind=request.kind,
            storage_ref=stored.storage_key,
            checksum=stored.checksum,
            media_type=stored.media_type,
            size=stored.size,
            producer_run_id=request.workflow_run_id,
            producer_step_run_id=request.step_run_id,
            metadata=request.metadata,
            **kwargs,
        )
        self.uow.artifacts.save(artifact)
        return artifact

    def list_for_run(
        self,
        *,
        project_id: str,
        workflow_run_id: str,
    ) -> tuple[ArtifactMetadata, ...]:
        return tuple(
            artifact
            for artifact in self.uow.artifacts.list_for_project(project_id)
            if artifact.producer_run_id == workflow_run_id
        )

    def get_metadata(self, artifact_id: str) -> ArtifactMetadata | None:
        return self.uow.artifacts.get(artifact_id)

    def read_verified(self, artifact_id: str) -> bytes:
        artifact = self.uow.artifacts.get(artifact_id)
        if artifact is None:
            raise ArtifactGatewayError(f"Artifact {artifact_id} was not found")
        content = self.storage.read(artifact.storage_ref)
        if len(content) != artifact.size or sha256_bytes(content) != artifact.checksum:
            raise ArtifactGatewayError(
                f"Artifact {artifact_id} failed checksum or size verification"
            )
        return content
