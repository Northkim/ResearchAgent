"""Provider-neutral persistence boundary failures."""


class PersistenceError(Exception):
    """Base class for persistence contract failures."""


class StaleStateError(PersistenceError):
    """Raised when expected persistence version does not match stored state."""


class DuplicateEntityError(PersistenceError):
    """Raised when an immutable identity is reused with different content."""
