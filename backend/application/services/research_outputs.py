"""Application queries for research artifacts and provider usage."""

from __future__ import annotations

from backend.persistence.ports import UnitOfWork
from backend.research.services import ArtifactApplicationGateway, ArtifactGatewayError

from ..errors import (
    ApplicationConflictError,
    ApplicationNotFoundError,
)
from ..views import ArtifactContentView, ArtifactView, ProviderOperationView
from ._shared import load_execution


class ListRunArtifactsService:
    def __init__(
        self,
        *,
        unit_of_work: UnitOfWork,
        artifacts: ArtifactApplicationGateway,
    ) -> None:
        self.uow = unit_of_work
        self.artifacts = artifacts

    def execute(self, workflow_run_id: str) -> tuple[ArtifactView, ...]:
        execution = load_execution(self.uow, workflow_run_id)
        return tuple(
            ArtifactView.from_artifact(item)
            for item in self.artifacts.list_for_run(
                project_id=execution.workflow_run.project_id,
                workflow_run_id=workflow_run_id,
            )
        )


class GetArtifactService:
    def __init__(self, *, artifacts: ArtifactApplicationGateway) -> None:
        self.artifacts = artifacts

    def execute(self, artifact_id: str) -> ArtifactView:
        artifact = self.artifacts.get_metadata(artifact_id)
        if artifact is None:
            raise ApplicationNotFoundError(
                f"Artifact {artifact_id} was not found"
            )
        return ArtifactView.from_artifact(artifact)


class ReadArtifactContentService:
    def __init__(self, *, artifacts: ArtifactApplicationGateway) -> None:
        self.artifacts = artifacts

    def execute(self, artifact_id: str) -> ArtifactContentView:
        artifact = self.artifacts.get_metadata(artifact_id)
        if artifact is None:
            raise ApplicationNotFoundError(
                f"Artifact {artifact_id} was not found"
            )
        try:
            content = self.artifacts.read_verified(artifact_id)
        except ArtifactGatewayError as error:
            raise ApplicationConflictError(
                f"Artifact {artifact_id} failed integrity verification"
            ) from error
        return ArtifactContentView(
            artifact=ArtifactView.from_artifact(artifact),
            content=content,
        )


class ListProviderUsageService:
    def __init__(self, *, unit_of_work: UnitOfWork) -> None:
        self.uow = unit_of_work

    def execute(self, workflow_run_id: str) -> tuple[ProviderOperationView, ...]:
        execution = load_execution(self.uow, workflow_run_id)
        return tuple(
            ProviderOperationView.from_operation(item)
            for item in self.uow.provider_operations.list_for_run(
                execution.workflow_run.project_id,
                workflow_run_id,
            )
        )
