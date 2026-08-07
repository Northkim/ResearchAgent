"""Stable Artifact Reference application errors."""


class ArtifactReferenceError(ValueError):
    code = "ARTIFACT_CONTRACT_VIOLATION"


class ArtifactReferenceConflictError(ArtifactReferenceError):
    code = "ARTIFACT_REFERENCE_CONFLICT"


class ArtifactTypeUnknownError(ArtifactReferenceError):
    code = "ARTIFACT_TYPE_UNKNOWN"


class ArtifactDependencyError(ArtifactReferenceError):
    code = "DEPENDENCY_UNRESOLVED"
