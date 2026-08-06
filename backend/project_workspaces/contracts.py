"""Phase 1 domain contracts for local Workflow persistence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from backend.workflow_packages.security import require_sha256

_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{1,127}$")
_CAPSULE_ID = re.compile(r"^capsule-[0-9a-f]{32}$")
_WORKFLOW_INSTANCE_ID = re.compile(r"^wfi-[0-9a-f]{32}$")
_PROJECT_ID = re.compile(r"^project-[0-9a-f]{32}$")
_WORKSPACE_ID = re.compile(r"^workspace-[0-9a-f]{32}$")
_ENTRY_ID = re.compile(r"^entry-[0-9a-f]{32}$")
_SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$"
)


class WorkflowDefinitionLifecycle(str, Enum):
    AVAILABLE = "AVAILABLE"
    PLANNED = "PLANNED"
    RETIRED = "RETIRED"


class WorkflowReviewStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    RETIRED = "RETIRED"


class WorkflowInstanceDesiredState(str, Enum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class CapsuleTrustClassification(str, Enum):
    TRUSTED_BUILT_IN_UNSIGNED = "TRUSTED_BUILT_IN_UNSIGNED"


class CloudProjectStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ManifestEntryKind(str, Enum):
    WORKFLOW_INSTANCE = "WORKFLOW_INSTANCE"


class ManifestDesiredAction(str, Enum):
    ENSURE_PRESENT = "ENSURE_PRESENT"
    RETIRE = "RETIRE"


@dataclass(frozen=True, slots=True)
class CloudProject:
    project_id: str
    workspace_id: str
    name: str
    research_topic: str
    status: CloudProjectStatus
    current_manifest_revision: int
    legacy_local_project_id: str | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        _require_match(self.project_id, _PROJECT_ID, "project_id")
        _require_match(self.workspace_id, _WORKSPACE_ID, "workspace_id")
        _require_bounded(self.name, 1, 200, "name")
        _require_bounded(self.research_topic, 1, 4000, "research_topic")
        if self.current_manifest_revision < 0:
            raise ValueError("current_manifest_revision must be non-negative")
        if self.legacy_local_project_id is not None:
            _require_match(
                self.legacy_local_project_id,
                _PROJECT_ID,
                "legacy_local_project_id",
            )
        _require_aware(self.created_at, "created_at")
        _require_aware(self.updated_at, "updated_at")


@dataclass(frozen=True, slots=True)
class DesiredProjectManifest:
    project_id: str
    manifest_revision: int
    workspace_id: str
    base_revision: int
    schema_version: str
    canonical_checksum: str
    manifest_json: Mapping[str, Any]
    created_by_subject_id: str
    idempotency_key: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        _require_match(self.project_id, _PROJECT_ID, "project_id")
        _require_match(self.workspace_id, _WORKSPACE_ID, "workspace_id")
        if self.manifest_revision < 1:
            raise ValueError("manifest_revision must be positive")
        if self.base_revision < 0 or self.base_revision >= self.manifest_revision:
            raise ValueError("base_revision must precede manifest_revision")
        if self.manifest_revision != self.base_revision + 1:
            raise ValueError("manifest revision must increase exactly once")
        if self.schema_version != "reagent.project-desired-manifest/v0.1":
            raise ValueError("unsupported desired manifest schema")
        require_sha256(self.canonical_checksum, "canonical_checksum")
        object.__setattr__(self, "manifest_json", _freeze_json(self.manifest_json))
        _require_bounded(self.created_by_subject_id, 1, 255, "created_by_subject_id")
        try:
            from uuid import UUID

            parsed = UUID(self.idempotency_key)
        except (ValueError, AttributeError) as error:
            raise ValueError("idempotency_key must be a UUID") from error
        if str(parsed) != self.idempotency_key:
            raise ValueError("idempotency_key must use canonical UUID text")
        _require_aware(self.created_at, "created_at")
        _require_aware(self.updated_at, "updated_at")


@dataclass(frozen=True, slots=True)
class ProjectManifestEntry:
    entry_id: str
    project_id: str
    manifest_revision: int
    entry_kind: ManifestEntryKind
    workflow_instance_id: str
    desired_action: ManifestDesiredAction
    entry_checksum: str
    created_at: datetime

    def __post_init__(self) -> None:
        _require_match(self.entry_id, _ENTRY_ID, "entry_id")
        _require_match(self.project_id, _PROJECT_ID, "project_id")
        _require_match(
            self.workflow_instance_id,
            _WORKFLOW_INSTANCE_ID,
            "workflow_instance_id",
        )
        if self.manifest_revision < 1:
            raise ValueError("manifest_revision must be positive")
        require_sha256(self.entry_checksum, "entry_checksum")
        _require_aware(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    workflow_definition_id: str
    display_name: str
    description: str
    lifecycle: WorkflowDefinitionLifecycle
    allows_multiple_instances: bool
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        _require_match(self.workflow_definition_id, _STABLE_ID, "workflow_definition_id")
        _require_bounded(self.display_name, 1, 120, "display_name")
        _require_bounded(self.description, 0, 2000, "description")
        _require_aware(self.created_at, "created_at")
        _require_aware(self.updated_at, "updated_at")


@dataclass(frozen=True, slots=True)
class WorkflowDefinitionVersion:
    workflow_definition_id: str
    version: str
    contract_checksum: str
    input_schema_id: str
    output_schema_id: str
    compatibility: Mapping[str, Any]
    review_status: WorkflowReviewStatus
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        _require_match(self.workflow_definition_id, _STABLE_ID, "workflow_definition_id")
        _require_match(self.version, _SEMVER, "version")
        require_sha256(self.contract_checksum, "contract_checksum")
        _require_bounded(self.input_schema_id, 1, 200, "input_schema_id")
        _require_bounded(self.output_schema_id, 1, 200, "output_schema_id")
        object.__setattr__(self, "compatibility", _freeze_json(self.compatibility))
        if self.published_at is not None:
            _require_aware(self.published_at, "published_at")
        _require_aware(self.created_at, "created_at")
        _require_aware(self.updated_at, "updated_at")


@dataclass(frozen=True, slots=True)
class WorkflowCapsuleVersion:
    capsule_id: str
    capsule_version: str
    workflow_definition_id: str
    workflow_version: str
    definition_checksum: str
    archive_size_bytes: int
    archive_media_type: str
    mutable_roots: tuple[str, ...]
    capability_requirements: tuple[str, ...]
    compatibility: Mapping[str, Any]
    review_status: WorkflowReviewStatus
    legacy_package_compatible: bool
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        _require_match(self.capsule_id, _CAPSULE_ID, "capsule_id")
        _require_match(self.capsule_version, _SEMVER, "capsule_version")
        _require_match(self.workflow_definition_id, _STABLE_ID, "workflow_definition_id")
        _require_match(self.workflow_version, _SEMVER, "workflow_version")
        require_sha256(self.definition_checksum, "definition_checksum")
        if not 0 <= self.archive_size_bytes <= 536_870_912:
            raise ValueError("archive_size_bytes must be between 0 and 536870912")
        _require_bounded(self.archive_media_type, 1, 100, "archive_media_type")
        _require_ascii_tuple(self.mutable_roots, "mutable_roots")
        _require_ascii_tuple(self.capability_requirements, "capability_requirements")
        object.__setattr__(self, "compatibility", _freeze_json(self.compatibility))
        _require_aware(self.created_at, "created_at")
        _require_aware(self.updated_at, "updated_at")


@dataclass(frozen=True, slots=True)
class ProjectWorkflowInstance:
    workflow_instance_id: str
    project_id: str
    workflow_definition_id: str
    workflow_version: str
    capsule_id: str | None
    capsule_version: str | None
    desired_state: WorkflowInstanceDesiredState
    display_name: str
    created_manifest_revision: int
    retired_manifest_revision: int | None
    legacy_package_id: str | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        _require_match(self.workflow_instance_id, _WORKFLOW_INSTANCE_ID, "workflow_instance_id")
        _require_match(self.project_id, _PROJECT_ID, "project_id")
        _require_match(self.workflow_definition_id, _STABLE_ID, "workflow_definition_id")
        _require_match(self.workflow_version, _SEMVER, "workflow_version")
        if (self.capsule_id is None) != (self.capsule_version is None):
            raise ValueError("capsule_id and capsule_version must both be set or both be absent")
        if self.capsule_id is not None:
            _require_match(self.capsule_id, _CAPSULE_ID, "capsule_id")
            _require_match(self.capsule_version or "", _SEMVER, "capsule_version")
        _require_bounded(self.display_name, 1, 160, "display_name")
        if self.created_manifest_revision < 0:
            raise ValueError("created_manifest_revision must be non-negative")
        if self.retired_manifest_revision is not None and self.retired_manifest_revision < 0:
            raise ValueError("retired_manifest_revision must be non-negative")
        if self.desired_state is WorkflowInstanceDesiredState.RETIRED:
            if self.retired_manifest_revision is None:
                raise ValueError("retired instance requires retired_manifest_revision")
        elif self.retired_manifest_revision is not None:
            raise ValueError("active instance cannot have retired_manifest_revision")
        if self.legacy_package_id is not None:
            _require_bounded(self.legacy_package_id, 1, 255, "legacy_package_id")
        _require_aware(self.created_at, "created_at")
        _require_aware(self.updated_at, "updated_at")


def _require_match(value: str, pattern: re.Pattern[str], name: str) -> None:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValueError(f"{name} has an invalid canonical format")


def _require_bounded(value: str, minimum: int, maximum: int, name: str) -> None:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        raise ValueError(f"{name} length must be between {minimum} and {maximum}")


def _require_aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _require_ascii_tuple(values: tuple[str, ...], name: str) -> None:
    if not isinstance(values, tuple):
        raise ValueError(f"{name} must be an immutable tuple")
    if any(not value or not value.isascii() for value in values):
        raise ValueError(f"{name} values must be non-empty ASCII strings")


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ValueError("compatibility must contain canonical JSON values")
