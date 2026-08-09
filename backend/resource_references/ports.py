"""Persistence boundary for external Resource reference metadata."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .contracts import (
    ProjectResourceReference,
    WorkflowResourceBinding,
    WorkflowResourceRequirement,
)


class ResourceReferenceRepository(ABC):
    @abstractmethod
    def add_resource(self, resource: ProjectResourceReference) -> None: ...

    @abstractmethod
    def get_resource(self, resource_id: str) -> ProjectResourceReference | None: ...

    @abstractmethod
    def list_resources(
        self, project_id: str, *, offset: int = 0, limit: int = 100
    ) -> tuple[ProjectResourceReference, ...]: ...

    @abstractmethod
    def count_resources(self, project_id: str) -> int: ...

    @abstractmethod
    def add_requirement(self, requirement: WorkflowResourceRequirement) -> None: ...

    @abstractmethod
    def get_requirement(
        self, workflow_definition_id: str, workflow_version: str, requirement_key: str
    ) -> WorkflowResourceRequirement | None: ...

    @abstractmethod
    def list_requirements(self) -> tuple[WorkflowResourceRequirement, ...]: ...

    @abstractmethod
    def add_binding(self, binding: WorkflowResourceBinding) -> None: ...

    @abstractmethod
    def get_binding(self, binding_id: str) -> WorkflowResourceBinding | None: ...

    @abstractmethod
    def get_binding_by_idempotency(
        self, project_id: str, workflow_instance_id: str, idempotency_key: str
    ) -> WorkflowResourceBinding | None: ...

    @abstractmethod
    def list_bindings(
        self,
        project_id: str,
        workflow_instance_id: str,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[WorkflowResourceBinding, ...]: ...

    @abstractmethod
    def list_project_bindings(
        self, project_id: str
    ) -> tuple[WorkflowResourceBinding, ...]: ...
