"""Persistence port for the Project Workspace Phase 1 entities."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .contracts import (
    ProjectWorkflowInstance,
    WorkflowCapsuleVersion,
    WorkflowDefinition,
    WorkflowDefinitionVersion,
)


class WorkflowFoundationRepository(ABC):
    @abstractmethod
    def add_definition(self, definition: WorkflowDefinition) -> None: ...

    @abstractmethod
    def get_definition(self, workflow_definition_id: str) -> WorkflowDefinition | None: ...

    @abstractmethod
    def get_definition_by_stable_key(self, stable_key: str) -> WorkflowDefinition | None: ...

    @abstractmethod
    def list_definitions(self) -> tuple[WorkflowDefinition, ...]: ...

    @abstractmethod
    def add_definition_version(self, version: WorkflowDefinitionVersion) -> None: ...

    @abstractmethod
    def get_definition_version(
        self, workflow_definition_id: str, version: str
    ) -> WorkflowDefinitionVersion | None: ...

    @abstractmethod
    def add_capsule_version(self, capsule: WorkflowCapsuleVersion) -> None: ...

    @abstractmethod
    def get_capsule_version(
        self, capsule_id: str, capsule_version: str
    ) -> WorkflowCapsuleVersion | None: ...

    @abstractmethod
    def add_workflow_instance(self, instance: ProjectWorkflowInstance) -> None: ...

    @abstractmethod
    def get_workflow_instance(
        self, workflow_instance_id: str
    ) -> ProjectWorkflowInstance | None: ...

    @abstractmethod
    def list_workflow_instances(
        self, project_id: str
    ) -> tuple[ProjectWorkflowInstance, ...]: ...
