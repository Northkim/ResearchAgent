"""Transport-neutral application failure contract."""

from __future__ import annotations


class ApplicationError(RuntimeError):
    """Base error with a stable machine-readable code."""

    code = "APPLICATION_ERROR"


class ApplicationValidationError(ApplicationError):
    code = "INVALID_REQUEST"


class ApplicationNotFoundError(ApplicationError):
    code = "NOT_FOUND"


class ApplicationConflictError(ApplicationError):
    code = "CONFLICT"


class ApplicationUnavailableError(ApplicationError):
    code = "SERVICE_UNAVAILABLE"
