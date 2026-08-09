"""Persistence boundary for local-product Artifact metadata."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .contracts import (
    ArtifactDependencyBinding,
    ArtifactReference,
    WorkflowArtifactRequirement,
)


class ArtifactReferenceRepository(ABC):
    @abstractmethod
    def add_artifact(self, artifact: ArtifactReference) -> None: ...

    @abstractmethod
    def get_artifact(self, artifact_id: str) -> ArtifactReference | None: ...

    @abstractmethod
    def list_artifacts(
        self,
        *,
        project_id: str,
        producer_workflow_instance_id: str | None = None,
        artifact_type: str | None = None,
        state: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[ArtifactReference, ...]: ...

    @abstractmethod
    def count_artifacts(
        self,
        *,
        project_id: str,
        producer_workflow_instance_id: str | None = None,
        artifact_type: str | None = None,
        state: str | None = None,
    ) -> int: ...

    @abstractmethod
    def list_for_progress(self, receipt_id: str) -> tuple[ArtifactReference, ...]: ...

    @abstractmethod
    def add_requirement(self, requirement: WorkflowArtifactRequirement) -> None: ...

    @abstractmethod
    def get_requirement(
        self, workflow_definition_id: str, workflow_version: str, requirement_key: str
    ) -> WorkflowArtifactRequirement | None: ...

    @abstractmethod
    def list_requirements(self) -> tuple[WorkflowArtifactRequirement, ...]: ...

    @abstractmethod
    def add_binding(self, binding: ArtifactDependencyBinding) -> None: ...

    @abstractmethod
    def save_binding(self, binding: ArtifactDependencyBinding) -> None: ...

    @abstractmethod
    def get_binding(self, binding_id: str) -> ArtifactDependencyBinding | None: ...

    @abstractmethod
    def get_binding_by_idempotency(
        self, project_id: str, consumer_workflow_instance_id: str, idempotency_key: str
    ) -> ArtifactDependencyBinding | None: ...

    @abstractmethod
    def list_bindings(
        self,
        project_id: str,
        consumer_workflow_instance_id: str,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[ArtifactDependencyBinding, ...]: ...

    @abstractmethod
    def list_project_bindings(
        self, project_id: str
    ) -> tuple[ArtifactDependencyBinding, ...]: ...

    @abstractmethod
    def count_bindings(
        self, project_id: str, consumer_workflow_instance_id: str
    ) -> int: ...
