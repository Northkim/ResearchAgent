"""Immutable artifact-content storage port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO


@dataclass(frozen=True, slots=True)
class StoredArtifactContent:
    storage_key: str
    checksum: str
    size: int
    media_type: str


@dataclass(frozen=True, slots=True)
class ArtifactVerification:
    valid: bool
    actual_checksum: str
    actual_size: int


class ArtifactContentStorage(ABC):
    @abstractmethod
    def write_immutable(
        self,
        storage_key: str,
        content: bytes,
        *,
        media_type: str,
    ) -> StoredArtifactContent: ...

    @abstractmethod
    def read(self, storage_key: str) -> bytes: ...

    @abstractmethod
    def open_read(self, storage_key: str) -> BinaryIO: ...

    @abstractmethod
    def verify(
        self,
        storage_key: str,
        *,
        expected_checksum: str,
        expected_size: int,
    ) -> ArtifactVerification: ...

