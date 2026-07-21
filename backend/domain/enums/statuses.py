"""Lifecycle and workflow enumerations used by the domain core."""

from enum import Enum


class WorkflowRunStatus(str, Enum):
    """Canonical externally visible workflow-run states."""

    CREATED = "CREATED"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    # Compatibility name required by the Phase 1 task.
    WAITING_APPROVAL = "WAITING_FOR_APPROVAL"
    WAITING_FOR_INPUT = "WAITING_FOR_INPUT"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"

    @property
    def is_terminal(self) -> bool:
        return self in {
            WorkflowRunStatus.COMPLETED,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELLED,
        }


class StepRunStatus(str, Enum):
    """Lifecycle states for one workflow-step attempt."""

    CREATED = "CREATED"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    WAITING_FOR_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    SUCCEEDED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"

    @property
    def is_terminal(self) -> bool:
        return self in {
            StepRunStatus.COMPLETED,
            StepRunStatus.FAILED,
            StepRunStatus.SKIPPED,
            StepRunStatus.CANCELLED,
        }


class AgentSessionStatus(str, Enum):
    """Lifecycle states for a runtime agent participant."""

    CREATED = "CREATED"
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    RUNNING = "ACTIVE"
    WAITING = "WAITING"
    WAITING_APPROVAL = "WAITING"
    WAITING_FOR_APPROVAL = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"

    @property
    def is_terminal(self) -> bool:
        return self in {
            AgentSessionStatus.COMPLETED,
            AgentSessionStatus.FAILED,
            AgentSessionStatus.CANCELLED,
        }


class WorkflowStepKind(str, Enum):
    """Step kinds allowed by the frozen v1 workflow contract."""

    SKILL = "skill"
    APPROVAL = "approval"


class ApprovalRequestStatus(str, Enum):
    """Lifecycle states for a durable human approval gate."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

    @property
    def is_terminal(self) -> bool:
        return self is not ApprovalRequestStatus.PENDING
