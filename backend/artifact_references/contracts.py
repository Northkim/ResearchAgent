"""Immutable local-product Artifact Reference and dependency contracts."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from backend.workflow_packages.security import require_relative_path, require_sha256

ARTIFACT_REFERENCE_SCHEMA = "reagent.artifact-reference/v0.1"
ARTIFACT_PAGE_SCHEMA = "reagent.artifact-reference-page/v0.1"
MATERIALIZATION_PLAN_SCHEMA = "reagent.artifact-materialization-plan/v0.1"
EXPERIMENT_PRESENTATION_SCHEMA = "reagent.artifact-presentation.experiment-record/v0.2"

_ARTIFACT_ID = re.compile(r"^artifact-[0-9a-f]{32}$")
_PROJECT_ID = re.compile(r"^project-[0-9a-f]{32}$")
_INSTANCE_ID = re.compile(r"^wfi-[0-9a-f]{32}$")
_CAPSULE_ID = re.compile(r"^capsule-[0-9a-f]{32}$")
_BINDING_ID = re.compile(r"^artifact-binding-[0-9a-f]{32}$")
_TYPE = re.compile(r"^[a-z][a-z0-9._-]{1,139}(?:/v[0-9]+(?:\.[0-9]+)?)?$")
_SCHEMA = re.compile(
    r"^(?:reagent\.artifact\.[a-z][a-z0-9._-]*/v[0-9]+\.[0-9]+|"
    r"[a-z][a-z0-9._-]{1,139}/v[0-9]+(?:\.[0-9]+)?)$"
)
_MEDIA = re.compile(r"^[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+$")
_KEY = re.compile(r"^[a-z][a-z0-9._-]{1,127}$")
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")


class ArtifactState(str, Enum):
    DECLARED = "DECLARED"
    LOCAL_AVAILABLE = "LOCAL_AVAILABLE"
    EXTERNAL_AVAILABLE = "EXTERNAL_AVAILABLE"
    METADATA_ONLY = "METADATA_ONLY"
    MISSING = "MISSING"
    STALE = "STALE"
    INCOMPATIBLE = "INCOMPATIBLE"
    RETIRED = "RETIRED"


class CompatibilityMode(str, Enum):
    EXACT = "EXACT"
    COMPATIBLE_RANGE = "COMPATIBLE_RANGE"
    CONVERTER_REQUIRED = "CONVERTER_REQUIRED"


class MaterializationMode(str, Enum):
    REFERENCE_ONLY = "REFERENCE_ONLY"
    VERIFIED_COPY = "VERIFIED_COPY"


class DependencyBindingState(str, Enum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


@dataclass(frozen=True, slots=True)
class ArtifactDeclaration:
    artifact_id: str
    artifact_type: str
    artifact_schema_version: str
    media_type: str
    relative_path: str
    content_checksum: str
    size_bytes: int
    produced_at: datetime

    def __post_init__(self) -> None:
        _match(self.artifact_id, _ARTIFACT_ID, "artifact_id")
        _match(self.artifact_type, _TYPE, "artifact_type")
        _match(self.artifact_schema_version, _SCHEMA, "artifact_schema_version")
        _match(self.media_type, _MEDIA, "media_type")
        require_relative_path(self.relative_path, "relative_path")
        if not self.relative_path.startswith("outputs/"):
            raise ValueError("Artifact producer path must be under outputs/")
        require_sha256(self.content_checksum, "content_checksum")
        if not 0 <= self.size_bytes <= 1_099_511_627_776:
            raise ValueError("size_bytes is outside the Artifact bound")
        _aware(self.produced_at, "produced_at")

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "artifact_schema_version": self.artifact_schema_version,
            "media_type": self.media_type,
            "relative_path": self.relative_path,
            "content_checksum": self.content_checksum,
            "size_bytes": self.size_bytes,
            "produced_at": self.produced_at.astimezone(timezone.utc).isoformat().replace(
                "+00:00", "Z"
            ),
        }


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    artifact_id: str
    project_id: str
    producer_workflow_instance_id: str
    producer_progress_receipt_id: str
    producer_progress_report_id: str
    producer_execution_round: int
    producer_capsule_id: str
    producer_capsule_version: str
    artifact_type: str
    artifact_schema_version: str
    media_type: str
    state: ArtifactState
    relative_path: str
    content_checksum: str
    size_bytes: int
    cloud_metadata_available: bool
    produced_at: datetime
    retired_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        _match(self.artifact_id, _ARTIFACT_ID, "artifact_id")
        _match(self.project_id, _PROJECT_ID, "project_id")
        _match(
            self.producer_workflow_instance_id,
            _INSTANCE_ID,
            "producer_workflow_instance_id",
        )
        _bounded(self.producer_progress_receipt_id, 1, 255, "producer_progress_receipt_id")
        _bounded(self.producer_progress_report_id, 1, 255, "producer_progress_report_id")
        if self.producer_execution_round < 1:
            raise ValueError("producer_execution_round must be positive")
        _match(self.producer_capsule_id, _CAPSULE_ID, "producer_capsule_id")
        _match(self.producer_capsule_version, _SEMVER, "producer_capsule_version")
        _match(self.artifact_type, _TYPE, "artifact_type")
        _match(self.artifact_schema_version, _SCHEMA, "artifact_schema_version")
        _match(self.media_type, _MEDIA, "media_type")
        require_relative_path(self.relative_path, "relative_path")
        if not self.relative_path.startswith("outputs/"):
            raise ValueError("Artifact producer path must be under outputs/")
        require_sha256(self.content_checksum, "content_checksum")
        if not 0 <= self.size_bytes <= 1_099_511_627_776:
            raise ValueError("size_bytes is outside the Artifact bound")
        if not self.cloud_metadata_available:
            raise ValueError("persisted Artifact Reference is cloud metadata")
        for field, value in (
            ("produced_at", self.produced_at),
            ("created_at", self.created_at),
            ("updated_at", self.updated_at),
        ):
            _aware(value, field)
        if self.retired_at is not None:
            _aware(self.retired_at, "retired_at")

    def immutable_identity(self) -> tuple[Any, ...]:
        return (
            self.artifact_id,
            self.project_id,
            self.producer_workflow_instance_id,
            self.producer_progress_receipt_id,
            self.producer_progress_report_id,
            self.producer_execution_round,
            self.producer_capsule_id,
            self.producer_capsule_version,
            self.artifact_type,
            self.artifact_schema_version,
            self.media_type,
            self.relative_path,
            self.content_checksum,
            self.size_bytes,
            self.produced_at,
        )


@dataclass(frozen=True, slots=True)
class ArtifactPresentation:
    """One immutable bounded Cloud presentation for one exact local Artifact."""

    artifact_id: str
    artifact_checksum: str
    schema_identity: str
    presentation_checksum: str
    payload: Mapping[str, Any]
    reported_at: datetime

    def __post_init__(self) -> None:
        _match(self.artifact_id, _ARTIFACT_ID, "artifact_id")
        require_sha256(self.artifact_checksum, "artifact_checksum")
        if self.schema_identity != EXPERIMENT_PRESENTATION_SCHEMA:
            raise ValueError("presentation schema identity is unsupported")
        require_sha256(self.presentation_checksum, "presentation_checksum")
        object.__setattr__(self, "payload", _freeze_presentation_json(self.payload))
        _aware(self.reported_at, "reported_at")

    def immutable_identity(self) -> tuple[Any, ...]:
        return (
            self.artifact_id,
            self.artifact_checksum,
            self.schema_identity,
            self.presentation_checksum,
            self.payload,
            self.reported_at,
        )


@dataclass(frozen=True, slots=True)
class WorkflowArtifactRequirement:
    workflow_definition_id: str
    workflow_version: str
    requirement_key: str
    artifact_type: str
    compatibility_mode: CompatibilityMode
    schema_constraint: str
    cardinality_min: int
    cardinality_max: int
    required: bool
    materialization_mode: MaterializationMode
    target_relative_path: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        _match(self.workflow_definition_id, _KEY, "workflow_definition_id")
        _match(self.workflow_version, _SEMVER, "workflow_version")
        _match(self.requirement_key, _KEY, "requirement_key")
        _match(self.artifact_type, _TYPE, "artifact_type")
        _bounded(self.schema_constraint, 1, 200, "schema_constraint")
        if not 0 <= self.cardinality_min <= self.cardinality_max <= 100:
            raise ValueError("Artifact requirement cardinality is invalid")
        require_relative_path(self.target_relative_path, "target_relative_path")
        if not self.target_relative_path.startswith("inputs/"):
            raise ValueError("Artifact materialization target must be under inputs/")
        _aware(self.created_at, "created_at")
        _aware(self.updated_at, "updated_at")


@dataclass(frozen=True, slots=True)
class ArtifactDependencyBinding:
    binding_id: str
    project_id: str
    consumer_workflow_instance_id: str
    consumer_workflow_definition_id: str
    consumer_workflow_version: str
    requirement_key: str
    artifact_id: str
    expected_checksum: str
    state: DependencyBindingState
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None

    def __post_init__(self) -> None:
        _match(self.binding_id, _BINDING_ID, "binding_id")
        _match(self.project_id, _PROJECT_ID, "project_id")
        _match(
            self.consumer_workflow_instance_id,
            _INSTANCE_ID,
            "consumer_workflow_instance_id",
        )
        _match(
            self.consumer_workflow_definition_id,
            _KEY,
            "consumer_workflow_definition_id",
        )
        _match(self.consumer_workflow_version, _SEMVER, "consumer_workflow_version")
        _match(self.requirement_key, _KEY, "requirement_key")
        _match(self.artifact_id, _ARTIFACT_ID, "artifact_id")
        require_sha256(self.expected_checksum, "expected_checksum")
        from uuid import UUID

        if str(UUID(self.idempotency_key)) != self.idempotency_key:
            raise ValueError("idempotency_key must use canonical UUID text")
        _aware(self.created_at, "created_at")
        _aware(self.updated_at, "updated_at")
        if self.retired_at is not None:
            _aware(self.retired_at, "retired_at")


@dataclass(frozen=True, slots=True)
class ArtifactMaterializationPlan:
    project_id: str
    workspace_id: str
    consumer_workflow_instance_id: str
    producer_workflow_instance_id: str
    binding_id: str
    requirement_key: str
    artifact_id: str
    artifact_type: str
    artifact_schema_version: str
    expected_checksum: str
    expected_size_bytes: int
    source_capsule_relative_path: str
    source_relative_path: str
    target_capsule_relative_path: str
    target_relative_path: str
    materialization_mode: MaterializationMode
    created_at: datetime
    plan_checksum: str


def freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ValueError("metadata contains a non-canonical JSON value")


def _freeze_presentation_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({
            str(key): _freeze_presentation_json(item) for key, item in value.items()
        })
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_presentation_json(item) for item in value)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ValueError("presentation contains a non-canonical JSON value")


def _match(value: str, pattern: re.Pattern[str], name: str) -> None:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValueError(f"{name} has an invalid canonical format")


def _bounded(value: str, minimum: int, maximum: int, name: str) -> None:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        raise ValueError(f"{name} length must be between {minimum} and {maximum}")


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
