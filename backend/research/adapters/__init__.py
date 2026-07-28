"""Infrastructure adapters for provider-independent research ports."""

from .fake_providers import (
    FakeLLMProvider,
    FakePaperSearchProvider,
    FakeSourceContentProvider,
)
from .local_artifact_storage import (
    ArtifactIntegrityError,
    ArtifactStorageError,
    DEFAULT_LOCAL_ARTIFACT_ROOT,
    ImmutableArtifactConflictError,
    InvalidStorageKeyError,
    LocalFilesystemArtifactStorage,
)
from .openalex import (
    HttpxOpenAlexTransport,
    OpenAlexConfiguration,
    OpenAlexHttpResponse,
    OpenAlexPaperSearchProvider,
    OpenAlexTransport,
)

__all__ = [
    "ArtifactIntegrityError",
    "ArtifactStorageError",
    "DEFAULT_LOCAL_ARTIFACT_ROOT",
    "FakeLLMProvider",
    "FakePaperSearchProvider",
    "FakeSourceContentProvider",
    "ImmutableArtifactConflictError",
    "InvalidStorageKeyError",
    "LocalFilesystemArtifactStorage",
    "HttpxOpenAlexTransport",
    "OpenAlexConfiguration",
    "OpenAlexHttpResponse",
    "OpenAlexPaperSearchProvider",
    "OpenAlexTransport",
]
