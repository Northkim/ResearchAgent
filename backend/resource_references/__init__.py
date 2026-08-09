"""Project-scoped external Resource metadata and exact bindings."""

from .contracts import (
    ProjectResourceReference,
    ResourceBindingState,
    ResourceKind,
    ResourceLifecycle,
    ResourceProvider,
    WorkflowResourceBinding,
    WorkflowResourceRequirement,
)

__all__ = [
    "ProjectResourceReference",
    "ResourceBindingState",
    "ResourceKind",
    "ResourceLifecycle",
    "ResourceProvider",
    "WorkflowResourceBinding",
    "WorkflowResourceRequirement",
]
