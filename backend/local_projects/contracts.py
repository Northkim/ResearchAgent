"""Teacher-aligned local project and Package metadata contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from backend.workflow_packages.security import require_relative_path, require_sha256

LITERATURE_SEARCH_WORKFLOW = "LITERATURE_SEARCH"
_PROJECT_ID = re.compile(r"^project-[0-9a-f]{32}$")


def _required_text(value: str, field: str, *, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field} must contain 1 to {maximum} characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise ValueError(f"{field} must not contain control characters")
    return normalized


@dataclass(frozen=True, slots=True)
class LocalPackageMetadata:
    package_id: str
    package_schema_version: str
    package_checksum: str
    manifest_checksum: str
    zip_checksum: str
    workflow_id: str
    workflow_version: str
    workflow_checksum: str
    archive_storage_key: str
    file_count: int
    package_size_bytes: int
    generated_at: str

    def __post_init__(self) -> None:
        _required_text(self.package_id, "package_id", maximum=255)
        _required_text(
            self.package_schema_version,
            "package_schema_version",
            maximum=100,
        )
        _required_text(self.workflow_id, "workflow_id", maximum=255)
        _required_text(self.workflow_version, "workflow_version", maximum=100)
        require_sha256(self.package_checksum, "package_checksum")
        require_sha256(self.manifest_checksum, "manifest_checksum")
        require_sha256(self.zip_checksum, "zip_checksum")
        require_sha256(self.workflow_checksum, "workflow_checksum")
        require_relative_path(self.archive_storage_key, "archive_storage_key")
        if self.file_count <= 0 or self.package_size_bytes <= 0:
            raise ValueError("Package file count and size must be positive")
        _required_text(self.generated_at, "generated_at", maximum=100)


@dataclass(frozen=True, slots=True)
class LocalProject:
    project_id: str
    name: str
    research_topic: str
    selected_workflow: str
    created_at: str
    updated_at: str
    current_package: LocalPackageMetadata | None = None

    def __post_init__(self) -> None:
        if not _PROJECT_ID.fullmatch(self.project_id):
            raise ValueError("project_id must be a generated local project identity")
        object.__setattr__(self, "name", _required_text(self.name, "name", maximum=160))
        object.__setattr__(
            self,
            "research_topic",
            _required_text(self.research_topic, "research_topic", maximum=500),
        )
        if self.selected_workflow != LITERATURE_SEARCH_WORKFLOW:
            raise ValueError("Literature Search is the only selectable V0.1 Workflow")
        _required_text(self.created_at, "created_at", maximum=100)
        _required_text(self.updated_at, "updated_at", maximum=100)

    def with_package(
        self,
        package: LocalPackageMetadata,
        *,
        updated_at: str,
    ) -> LocalProject:
        return replace(self, current_package=package, updated_at=updated_at)
