"""Local immutable artifact-content adapter with path and integrity controls."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from backend.research.contracts import sha256_bytes
from backend.research.ports import (
    ArtifactContentStorage,
    ArtifactVerification,
    StoredArtifactContent,
)

DEFAULT_LOCAL_ARTIFACT_ROOT = Path("runtime_data/artifacts")


class ArtifactStorageError(RuntimeError):
    pass


class InvalidStorageKeyError(ArtifactStorageError):
    pass


class ImmutableArtifactConflictError(ArtifactStorageError):
    pass


class ArtifactIntegrityError(ArtifactStorageError):
    pass


class LocalFilesystemArtifactStorage(ArtifactContentStorage):
    """Store bytes below an injected root; records retain relative keys only."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        if not self._root.is_dir():
            raise ArtifactStorageError("Artifact root must be a directory")

    def write_immutable(
        self,
        storage_key: str,
        content: bytes,
        *,
        media_type: str,
    ) -> StoredArtifactContent:
        if not isinstance(content, bytes):
            raise TypeError("Artifact content must be bytes")
        if not media_type.strip():
            raise ValueError("media_type must be non-empty")
        path = self._path_for(storage_key, create_parent=True)
        checksum = sha256_bytes(content)
        stored = StoredArtifactContent(
            storage_key=storage_key,
            checksum=checksum,
            size=len(content),
            media_type=media_type,
        )
        if path.exists():
            self._verify_existing(path, content, checksum)
            return stored

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            if sha256_bytes(temporary_path.read_bytes()) != checksum:
                raise ArtifactIntegrityError("Temporary artifact checksum mismatch")
            try:
                os.link(temporary_path, path)
            except FileExistsError:
                self._verify_existing(path, content, checksum)
            return stored
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def read(self, storage_key: str) -> bytes:
        path = self._path_for(storage_key)
        if not path.is_file():
            raise FileNotFoundError(storage_key)
        return path.read_bytes()

    def open_read(self, storage_key: str) -> BinaryIO:
        path = self._path_for(storage_key)
        if not path.is_file():
            raise FileNotFoundError(storage_key)
        return path.open("rb")

    def verify(
        self,
        storage_key: str,
        *,
        expected_checksum: str,
        expected_size: int,
    ) -> ArtifactVerification:
        content = self.read(storage_key)
        checksum = sha256_bytes(content)
        return ArtifactVerification(
            valid=checksum == expected_checksum and len(content) == expected_size,
            actual_checksum=checksum,
            actual_size=len(content),
        )

    def _path_for(self, storage_key: str, *, create_parent: bool = False) -> Path:
        if not isinstance(storage_key, str) or not storage_key:
            raise InvalidStorageKeyError("Storage key must be non-empty")
        if "\\" in storage_key:
            raise InvalidStorageKeyError("Storage keys must use forward slashes")
        key = PurePosixPath(storage_key)
        if key.is_absolute() or any(
            part in {"", ".", ".."} for part in storage_key.split("/")
        ):
            raise InvalidStorageKeyError("Storage key must be a clean relative path")
        candidate = self._root.joinpath(*key.parts)
        current = self._root
        for part in key.parts[:-1]:
            current = current / part
            if current.is_symlink():
                raise InvalidStorageKeyError("Storage key traverses a symbolic link")
        if create_parent:
            candidate.parent.mkdir(parents=True, exist_ok=True)
        resolved_parent = candidate.parent.resolve()
        if self._root != resolved_parent and self._root not in resolved_parent.parents:
            raise InvalidStorageKeyError("Storage key escapes the configured root")
        if candidate.is_symlink():
            raise InvalidStorageKeyError("Storage key targets a symbolic link")
        return candidate

    @staticmethod
    def _verify_existing(path: Path, content: bytes, checksum: str) -> None:
        existing = path.read_bytes()
        if len(existing) != len(content) or sha256_bytes(existing) != checksum:
            raise ImmutableArtifactConflictError(
                "Immutable artifact key already contains different content"
            )
