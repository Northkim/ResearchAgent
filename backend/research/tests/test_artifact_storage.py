"""Local immutable artifact-content storage integrity tests."""

from __future__ import annotations

import pytest

from backend.research.adapters import (
    ImmutableArtifactConflictError,
    InvalidStorageKeyError,
    LocalFilesystemArtifactStorage,
)


def test_write_read_verify_restart_and_idempotent_replay(tmp_path) -> None:
    root = tmp_path / "isolated-artifacts"
    storage = LocalFilesystemArtifactStorage(root)
    key = "projects/project-1/runs/run-1/artifacts/report/v1/report.md"
    first = storage.write_immutable(key, b"synthetic report", media_type="text/markdown")
    replay = storage.write_immutable(key, b"synthetic report", media_type="text/markdown")
    restarted = LocalFilesystemArtifactStorage(root)

    assert first == replay
    assert restarted.read(key) == b"synthetic report"
    assert restarted.verify(
        key,
        expected_checksum=first.checksum,
        expected_size=first.size,
    ).valid


def test_immutable_conflict_and_checksum_mismatch_are_detected(tmp_path) -> None:
    storage = LocalFilesystemArtifactStorage(tmp_path)
    key = "artifacts/papers.json"
    stored = storage.write_immutable(key, b"one", media_type="application/json")
    with pytest.raises(ImmutableArtifactConflictError):
        storage.write_immutable(key, b"two", media_type="application/json")
    (tmp_path / "artifacts" / "papers.json").write_bytes(b"tampered")
    assert not storage.verify(
        key,
        expected_checksum=stored.checksum,
        expected_size=stored.size,
    ).valid


@pytest.mark.parametrize(
    "key",
    (
        "../escape",
        "/absolute/path",
        "safe/../../escape",
        "safe\\windows",
        "safe//empty",
        "safe/./dot",
    ),
)
def test_path_traversal_is_rejected(tmp_path, key: str) -> None:
    storage = LocalFilesystemArtifactStorage(tmp_path)
    with pytest.raises(InvalidStorageKeyError):
        storage.write_immutable(key, b"x", media_type="application/octet-stream")


def test_symbolic_link_escape_is_rejected(tmp_path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    outside.mkdir()
    storage = LocalFilesystemArtifactStorage(root)
    (root / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(InvalidStorageKeyError):
        storage.write_immutable(
            "linked/escape.bin",
            b"x",
            media_type="application/octet-stream",
        )
