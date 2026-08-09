"""Canonical Project Resource references, requirements, and exact bindings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID

from backend.workflow_packages.security import require_sha256
from backend.workflow_packages.serialization import canonical_json

RESOURCE_REFERENCE_SCHEMA = "reagent.project-resource-reference/v0.1"
RESOURCE_PAGE_SCHEMA = "reagent.project-resource-page/v0.1"
RESOURCE_BINDING_PAGE_SCHEMA = "reagent.workflow-resource-binding-page/v0.1"
RESOURCE_INDEX_SCHEMA = "reagent.workspace-resource-index/v0.1"

_RESOURCE_ID = re.compile(r"^resource-[0-9a-f]{32}$")
_BINDING_ID = re.compile(r"^resource-binding-[0-9a-f]{32}$")
_PROJECT_ID = re.compile(r"^project-[0-9a-f]{32}$")
_INSTANCE_ID = re.compile(r"^wfi-[0-9a-f]{32}$")
_KEY = re.compile(r"^[a-z][a-z0-9._-]{1,127}$")
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_LOCATOR = re.compile(r"^[A-Za-z0-9._-]{1,120}/[A-Za-z0-9._-]{1,180}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_LOCAL_REVISION = re.compile(r"^[a-z0-9][a-z0-9._-]{6,127}$")
_FLOATING_REVISIONS = {"main", "master", "latest", "head", "develop", "trunk"}


class ResourceKind(str, Enum):
    SOURCE_REPOSITORY = "SOURCE_REPOSITORY"
    DATASET = "DATASET"
    MODEL = "MODEL"
    CHECKPOINT = "CHECKPOINT"
    GENERIC_FILE = "GENERIC_FILE"


class ResourceProvider(str, Enum):
    GITHUB = "GITHUB"
    HUGGING_FACE = "HUGGING_FACE"
    LOCAL_TEST = "LOCAL_TEST"


class ResourceLifecycle(str, Enum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class ResourceBindingState(str, Enum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


@dataclass(frozen=True, slots=True)
class ProjectResourceReference:
    resource_id: str
    project_id: str
    resource_kind: ResourceKind
    provider: ResourceProvider
    locator: str
    exact_revision: str
    expected_content_checksum: str
    display_name: str
    metadata: Mapping[str, Any]
    lifecycle: ResourceLifecycle
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None = None

    def __post_init__(self) -> None:
        _match(self.resource_id, _RESOURCE_ID, "resource_id")
        _match(self.project_id, _PROJECT_ID, "project_id")
        validate_locator(self.provider, self.locator)
        validate_exact_revision(self.provider, self.exact_revision)
        require_sha256(
            self.expected_content_checksum, "expected_content_checksum"
        )
        _bounded(self.display_name, 1, 160, "display_name")
        frozen = _freeze_json(self.metadata)
        if len(canonical_json(_thaw_json(frozen)).encode("utf-8")) > 16_384:
            raise ValueError("Resource metadata exceeds the reviewed bound")
        object.__setattr__(self, "metadata", frozen)
        _aware(self.created_at, "created_at")
        _aware(self.updated_at, "updated_at")
        if self.retired_at is not None:
            _aware(self.retired_at, "retired_at")

    def immutable_identity(self) -> tuple[Any, ...]:
        return (
            self.resource_id,
            self.project_id,
            self.resource_kind,
            self.provider,
            self.locator,
            self.exact_revision,
            self.expected_content_checksum,
            self.display_name,
            self.metadata,
        )


@dataclass(frozen=True, slots=True)
class WorkflowResourceRequirement:
    workflow_definition_id: str
    workflow_version: str
    requirement_key: str
    resource_kind: ResourceKind
    cardinality_min: int
    cardinality_max: int
    required: bool
    allowed_providers: tuple[ResourceProvider, ...]
    usage_description: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        _match(self.workflow_definition_id, _KEY, "workflow_definition_id")
        _match(self.workflow_version, _SEMVER, "workflow_version")
        _match(self.requirement_key, _KEY, "requirement_key")
        if not 0 <= self.cardinality_min <= self.cardinality_max <= 20:
            raise ValueError("Resource requirement cardinality is invalid")
        if not isinstance(self.allowed_providers, tuple) or not self.allowed_providers:
            raise ValueError("Resource requirement must declare allowed providers")
        if len(set(self.allowed_providers)) != len(self.allowed_providers):
            raise ValueError("Resource requirement providers must be unique")
        _bounded(self.usage_description, 1, 500, "usage_description")
        _aware(self.created_at, "created_at")
        _aware(self.updated_at, "updated_at")


@dataclass(frozen=True, slots=True)
class WorkflowResourceBinding:
    binding_id: str
    project_id: str
    workflow_instance_id: str
    workflow_definition_id: str
    workflow_version: str
    requirement_key: str
    resource_id: str
    expected_content_checksum: str
    state: ResourceBindingState
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None = None

    def __post_init__(self) -> None:
        _match(self.binding_id, _BINDING_ID, "binding_id")
        _match(self.project_id, _PROJECT_ID, "project_id")
        _match(self.workflow_instance_id, _INSTANCE_ID, "workflow_instance_id")
        _match(self.workflow_definition_id, _KEY, "workflow_definition_id")
        _match(self.workflow_version, _SEMVER, "workflow_version")
        _match(self.requirement_key, _KEY, "requirement_key")
        _match(self.resource_id, _RESOURCE_ID, "resource_id")
        require_sha256(
            self.expected_content_checksum, "expected_content_checksum"
        )
        if str(UUID(self.idempotency_key)) != self.idempotency_key:
            raise ValueError("idempotency_key must use canonical UUID text")
        _aware(self.created_at, "created_at")
        _aware(self.updated_at, "updated_at")
        if self.retired_at is not None:
            _aware(self.retired_at, "retired_at")


def validate_locator(provider: ResourceProvider, locator: str) -> None:
    _bounded(locator, 3, 300, "locator")
    if (
        _LOCATOR.fullmatch(locator) is None
        or "://" in locator
        or "\\" in locator
        or any(char.isspace() or ord(char) < 32 for char in locator)
        or any(char in locator for char in "$`;&|<>@?#%=")
    ):
        raise ValueError("locator must be a credential-free provider identity")
    if provider is ResourceProvider.LOCAL_TEST and not locator.startswith("fixture/"):
        raise ValueError("LOCAL_TEST locator must use the fixture namespace")


def validate_exact_revision(provider: ResourceProvider, revision: str) -> None:
    _bounded(revision, 7, 128, "exact_revision")
    if revision.casefold() in _FLOATING_REVISIONS:
        raise ValueError("Resource revision must not be floating")
    if provider in {ResourceProvider.GITHUB, ResourceProvider.HUGGING_FACE}:
        if _COMMIT.fullmatch(revision) is None:
            raise ValueError("External Resource revision must be an exact commit")
    elif _LOCAL_REVISION.fullmatch(revision) is None:
        raise ValueError("LOCAL_TEST revision has an invalid immutable identity")


def _match(value: str, pattern: re.Pattern[str], name: str) -> None:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValueError(f"{name} has an invalid canonical format")


def _bounded(value: str, minimum: int, maximum: int, name: str) -> None:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        raise ValueError(f"{name} length is outside the reviewed bound")


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ValueError("Resource metadata contains a non-canonical value")


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value
