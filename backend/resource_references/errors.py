"""Stable Resource-domain conflicts."""


class ResourceReferenceConflictError(ValueError):
    """An immutable Resource identity or binding conflicts with stored state."""
