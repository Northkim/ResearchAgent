class WorkflowFoundationConflictError(RuntimeError):
    """A stable identity already exists with different immutable content."""


class ManifestRevisionConflictError(RuntimeError):
    def __init__(self, *, expected: int, current: int) -> None:
        super().__init__("Desired Project Manifest revision changed")
        self.expected = expected
        self.current = current
