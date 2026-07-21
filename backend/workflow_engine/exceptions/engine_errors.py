"""Domain-level errors raised by pure Workflow Engine validation."""

from backend.domain.exceptions import DomainError


class WorkflowEngineError(DomainError):
    """Base class for Workflow Engine contract failures."""


class InvalidWorkflowDefinitionError(WorkflowEngineError):
    """Raised when a workflow definition is not a valid static DAG."""


class InvalidReferenceError(InvalidWorkflowDefinitionError):
    """Raised when an input or output reference is invalid or unavailable."""


class InvalidRetryPolicyError(InvalidWorkflowDefinitionError):
    """Raised when retry metadata violates the v1 contract."""


class WorkflowStateError(WorkflowEngineError):
    """Raised when an execution snapshot is internally inconsistent."""


class StaleDecisionError(WorkflowStateError):
    """Raised when applying a decision to a newer aggregate version."""
