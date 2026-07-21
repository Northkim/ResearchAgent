"""Stable exception taxonomy for pure domain behavior."""


class DomainError(Exception):
    """Base class for expected domain failures."""


class DomainValidationError(DomainError):
    """Raised when an entity or command violates a domain invariant."""


class InvalidStateTransition(DomainError):
    """Raised when a lifecycle transition is not allowed."""

    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        current_status: str,
        target_status: str,
    ) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            f"Invalid {entity_type} transition for {entity_id}: "
            f"{current_status} -> {target_status}"
        )


class CheckpointIntegrityError(DomainError):
    """Raised when checkpoint content does not match its integrity hash."""


class CheckpointMismatchError(DomainError):
    """Raised when a checkpoint does not describe the supplied execution."""


class ExecutionNotResumableError(DomainError):
    """Raised when execution state cannot legally resume."""


class StepRunNotFoundError(DomainError):
    """Raised when an execution has no attempt for the requested step."""
