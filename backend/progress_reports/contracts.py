"""Immutable contracts for local Progress Reports and cloud progress state."""

from __future__ import annotations

import base64
import binascii
import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from backend.workflow_packages.serialization import (
    SerializableContract,
    canonical_hash,
)
from backend.workflow_packages.security import require_relative_path, require_sha256

PROGRESS_REPORT_SCHEMA_V1 = "progress-report/v0.1"
PROGRESS_REPORT_SCHEMA_V2 = "progress-report/v0.2"
UPLOAD_SCHEMA_VERSION = "progress-report-upload/v0.1"
NORMALIZED_SCHEMA_VERSION = "normalized-progress-record/v0.2"
PROJECTION_SCHEMA_VERSION = "project-progress-projection/v0.1"
WORKFLOW_INSTANCE_PROJECTION_SCHEMA_VERSION = (
    "reagent.workflow-instance-progress/v0.1"
)
PROJECT_WORKFLOW_PROGRESS_SCHEMA_VERSION = "reagent.project-progress/v0.1"
NORMALIZER_VERSION = "reagent-progress-normalizer/0.2.0"
EXPERIMENTAL_DECLARATION = "EXPERIMENTAL_PROGRESS_REPORT_V0_2"
ACCEPTED_REPORT_MEDIA_TYPE = "application/json"
MAX_REPORT_BYTES = 256 * 1024
ZERO_HASH = "sha256:" + "0" * 64

_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]{1,255}$")
_REPORT_ID = re.compile(r"^prv2-[0-9a-f]{64}$")
_SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?$"
)


def _freeze_json(value: Any, *, path: str) -> Any:
    """Freeze JSON metadata without coupling report contracts to persistence."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        raise ValueError(f"{path} must not contain floating-point values")
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} contains a non-string object key")
            frozen[key] = _freeze_json(item, path=f"{path}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_json(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        )
    raise ValueError(f"{path} contains a non-JSON-compatible value")


class ProgressStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ChainState(str, Enum):
    VALID_CHAIN = "VALID_CHAIN"
    LEGACY_CHAIN_WITH_WARNINGS = "LEGACY_CHAIN_WITH_WARNINGS"
    INCOMPLETE_CHAIN = "INCOMPLETE_CHAIN"
    CONTINUITY_CONFLICT = "CONTINUITY_CONFLICT"
    IDENTITY_CONFLICT = "IDENTITY_CONFLICT"
    BRANCHED_HISTORY = "BRANCHED_HISTORY"


class ValidationStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


def _text(value: str, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    if not allow_empty and not value.strip():
        raise ValueError(f"{name} must be non-empty")
    if len(value) > 32_768:
        raise ValueError(f"{name} is too large")
    for character in value:
        if character in {"\n", "\t"}:
            continue
        if unicodedata.category(character).startswith("C"):
            raise ValueError(f"{name} contains a control or invalid Unicode character")
    return value


def _identifier(value: str, name: str) -> str:
    _text(value, name)
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase portable identifier")
    return value


def _semver(value: str, name: str) -> str:
    if not isinstance(value, str) or not _SEMVER.fullmatch(value):
        raise ValueError(f"{name} must be a semantic version")
    return value


def _timestamp(value: str, name: str) -> datetime:
    _text(value, name)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must include a timezone")
    return parsed


def _strings(values: tuple[str, ...], name: str) -> tuple[str, ...]:
    items = tuple(values)
    for index, value in enumerate(items):
        _text(value, f"{name}[{index}]")
    return items


@dataclass(frozen=True, slots=True)
class PinReference(SerializableContract):
    pin_type: str
    identity: str
    version: str
    checksum: str

    def __post_init__(self) -> None:
        if self.pin_type not in {"SKILL", "TEMPLATE"}:
            raise ValueError("PinReference.pin_type must be SKILL or TEMPLATE")
        _identifier(self.identity, "PinReference.identity")
        _semver(self.version, "PinReference.version")
        require_sha256(self.checksum, "PinReference.checksum")


@dataclass(frozen=True, slots=True)
class OutputArtifactReference(SerializableContract):
    relative_path: str
    artifact_kind: str
    media_type: str
    checksum: str
    size: int | None = None

    def __post_init__(self) -> None:
        require_relative_path(self.relative_path, "OutputArtifactReference.relative_path")
        if not self.relative_path.startswith("outputs/"):
            raise ValueError("Progress Report outputs must be under outputs/")
        _text(self.artifact_kind, "OutputArtifactReference.artifact_kind")
        _text(self.media_type, "OutputArtifactReference.media_type")
        require_sha256(self.checksum, "OutputArtifactReference.checksum")
        if self.size is not None and self.size < 0:
            raise ValueError("OutputArtifactReference.size must be non-negative")


@dataclass(frozen=True, slots=True)
class ProgressReportV2(SerializableContract):
    schema_version: str
    report_id: str
    report_content_checksum: str
    report_checksum: str
    package_id: str
    package_schema_version: str
    package_checksum: str
    project_id: str
    workflow_id: str
    workflow_version: str
    workflow_checksum: str
    execution_round: int
    harness_type: str
    harness_version: str | None
    harness_session_id: str
    previous_report_id: str | None
    previous_report_checksum: str | None
    started_at: str
    completed_at: str
    status: ProgressStatus
    completed_work: tuple[str, ...]
    current_state: str
    next_recommended_action: str
    continuation_reason: str | None
    output_artifacts: tuple[OutputArtifactReference, ...]
    context_before_checksum: str
    context_after_checksum: str
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    unresolved_questions: tuple[str, ...]
    continuation_instructions: tuple[str, ...]
    skill_pins: tuple[PinReference, ...]
    template_pins: tuple[PinReference, ...]
    generated_at: str
    experimental_declaration: str

    def __post_init__(self) -> None:
        if self.schema_version != PROGRESS_REPORT_SCHEMA_V2:
            raise ValueError("unsupported Progress Report schema")
        if self.report_id != "prv2-pending" and not _REPORT_ID.fullmatch(self.report_id):
            raise ValueError("report_id must be a deterministic prv2 SHA-256 identifier")
        require_sha256(self.report_content_checksum, "report_content_checksum")
        require_sha256(self.report_checksum, "report_checksum")
        _identifier(self.package_id, "package_id")
        _text(self.package_schema_version, "package_schema_version")
        require_sha256(self.package_checksum, "package_checksum")
        _identifier(self.project_id, "project_id")
        _identifier(self.workflow_id, "workflow_id")
        _semver(self.workflow_version, "workflow_version")
        require_sha256(self.workflow_checksum, "workflow_checksum")
        if self.execution_round < 1:
            raise ValueError("execution_round must be positive")
        _identifier(self.harness_type, "harness_type")
        if self.harness_version is not None:
            _text(self.harness_version, "harness_version")
        _identifier(self.harness_session_id, "harness_session_id")
        if (self.previous_report_id is None) != (self.previous_report_checksum is None):
            raise ValueError("previous report ID and checksum must be present together")
        if self.previous_report_id is not None:
            if not _REPORT_ID.fullmatch(self.previous_report_id):
                raise ValueError("previous_report_id must be a native v0.2 report ID")
            require_sha256(self.previous_report_checksum or "", "previous_report_checksum")
        started = _timestamp(self.started_at, "started_at")
        completed = _timestamp(self.completed_at, "completed_at")
        _timestamp(self.generated_at, "generated_at")
        if completed < started:
            raise ValueError("completed_at must not precede started_at")
        if not isinstance(self.status, ProgressStatus):
            object.__setattr__(self, "status", ProgressStatus(self.status))
        object.__setattr__(self, "completed_work", _strings(self.completed_work, "completed_work"))
        _text(self.current_state, "current_state")
        _text(self.next_recommended_action, "next_recommended_action")
        if self.continuation_reason is not None:
            _text(self.continuation_reason, "continuation_reason")
        object.__setattr__(self, "output_artifacts", tuple(self.output_artifacts))
        require_sha256(self.context_before_checksum, "context_before_checksum")
        require_sha256(self.context_after_checksum, "context_after_checksum")
        object.__setattr__(self, "warnings", _strings(self.warnings, "warnings"))
        object.__setattr__(self, "errors", _strings(self.errors, "errors"))
        object.__setattr__(
            self,
            "unresolved_questions",
            _strings(self.unresolved_questions, "unresolved_questions"),
        )
        object.__setattr__(
            self,
            "continuation_instructions",
            _strings(self.continuation_instructions, "continuation_instructions"),
        )
        object.__setattr__(self, "skill_pins", tuple(self.skill_pins))
        object.__setattr__(self, "template_pins", tuple(self.template_pins))
        if not self.skill_pins or any(item.pin_type != "SKILL" for item in self.skill_pins):
            raise ValueError("at least one SKILL pin is required")
        if not self.template_pins or any(
            item.pin_type != "TEMPLATE" for item in self.template_pins
        ):
            raise ValueError("at least one TEMPLATE pin is required")
        if self.experimental_declaration != EXPERIMENTAL_DECLARATION:
            raise ValueError("experimental v0.2 declaration is required")

    @classmethod
    def create(cls, **values: Any) -> ProgressReportV2:
        candidate = cls(
            schema_version=PROGRESS_REPORT_SCHEMA_V2,
            report_id="prv2-pending",
            report_content_checksum=ZERO_HASH,
            report_checksum=ZERO_HASH,
            **values,
        )
        return candidate.with_computed_identity()

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProgressReportV2:
        expected = {field.name for field in __import__("dataclasses").fields(cls)}
        unknown = set(payload) - expected
        missing = expected - set(payload)
        if unknown or missing:
            raise ValueError(
                "Progress Report fields mismatch"
                + (f"; missing={sorted(missing)}" if missing else "")
                + (f"; unknown={sorted(unknown)}" if unknown else "")
            )
        report = cls(
            **{
                **dict(payload),
                "status": ProgressStatus(payload["status"]),
                "completed_work": tuple(payload["completed_work"]),
                "output_artifacts": tuple(
                    OutputArtifactReference(**item) for item in payload["output_artifacts"]
                ),
                "warnings": tuple(payload["warnings"]),
                "errors": tuple(payload["errors"]),
                "unresolved_questions": tuple(payload["unresolved_questions"]),
                "continuation_instructions": tuple(payload["continuation_instructions"]),
                "skill_pins": tuple(PinReference(**item) for item in payload["skill_pins"]),
                "template_pins": tuple(
                    PinReference(**item) for item in payload["template_pins"]
                ),
            }
        )
        if not report.verify_identity():
            raise ValueError("Progress Report identity or checksum mismatch")
        return report

    def _content_payload(self) -> dict[str, Any]:
        payload = self.to_dict()
        for field_name in ("report_id", "report_content_checksum", "report_checksum"):
            payload.pop(field_name)
        return payload

    def with_computed_identity(self) -> ProgressReportV2:
        content_checksum = canonical_hash(self._content_payload())
        report_id_hash = canonical_hash(
            {
                "package_id": self.package_id,
                "workflow_id": self.workflow_id,
                "workflow_version": self.workflow_version,
                "execution_round": self.execution_round,
                "previous_report_id": self.previous_report_id,
                "report_content_checksum": content_checksum,
            }
        ).split(":", 1)[1]
        identified = replace(
            self,
            report_id=f"prv2-{report_id_hash}",
            report_content_checksum=content_checksum,
            report_checksum=ZERO_HASH,
        )
        checksum_payload = identified.to_dict()
        checksum_payload["report_checksum"] = None
        return replace(identified, report_checksum=canonical_hash(checksum_payload))

    def verify_identity(self) -> bool:
        expected = self.with_computed_identity()
        return (
            self.report_content_checksum == expected.report_content_checksum
            and self.report_id == expected.report_id
            and self.report_checksum == expected.report_checksum
        )


@dataclass(frozen=True, slots=True)
class ProgressReportUploadEnvelope(SerializableContract):
    upload_schema_version: str
    project_id: str
    package_id: str
    package_checksum: str
    report_schema_version: str
    report_id: str
    report_checksum: str
    original_report_media_type: str
    original_report_base64: str
    original_report_checksum: str
    original_report_size: int
    uploaded_at: str
    uploader_type: str
    client_version: str
    source_path_hint: str
    context_snapshot_metadata: Mapping[str, Any] | None
    envelope_checksum: str

    def __post_init__(self) -> None:
        if self.upload_schema_version != UPLOAD_SCHEMA_VERSION:
            raise ValueError("unsupported upload envelope schema")
        _identifier(self.project_id, "project_id")
        _identifier(self.package_id, "package_id")
        require_sha256(self.package_checksum, "package_checksum")
        if self.report_schema_version not in {
            PROGRESS_REPORT_SCHEMA_V1,
            PROGRESS_REPORT_SCHEMA_V2,
        }:
            raise ValueError("unsupported report schema")
        _text(self.report_id, "report_id")
        require_sha256(self.report_checksum, "report_checksum")
        if self.original_report_media_type != ACCEPTED_REPORT_MEDIA_TYPE:
            raise ValueError("original report media type must be application/json")
        if (
            not isinstance(self.original_report_base64, str)
            or not self.original_report_base64
            or len(self.original_report_base64) > ((MAX_REPORT_BYTES + 2) // 3) * 4
        ):
            raise ValueError("original report base64 is empty or outside the size bound")
        require_sha256(self.original_report_checksum, "original_report_checksum")
        if self.original_report_size < 1 or self.original_report_size > MAX_REPORT_BYTES:
            raise ValueError("original report size is outside the accepted bound")
        _timestamp(self.uploaded_at, "uploaded_at")
        _identifier(self.uploader_type, "uploader_type")
        _text(self.client_version, "client_version")
        require_relative_path(self.source_path_hint, "source_path_hint")
        if self.context_snapshot_metadata is not None:
            object.__setattr__(
                self,
                "context_snapshot_metadata",
                _freeze_json(
                    self.context_snapshot_metadata,
                    path="context_snapshot_metadata",
                ),
            )
        require_sha256(self.envelope_checksum, "envelope_checksum")

    @classmethod
    def create(cls, *, original_report_bytes: bytes, **values: Any) -> ProgressReportUploadEnvelope:
        from backend.workflow_packages.serialization import sha256_bytes

        candidate = cls(
            upload_schema_version=UPLOAD_SCHEMA_VERSION,
            original_report_base64=base64.b64encode(original_report_bytes).decode("ascii"),
            original_report_checksum=sha256_bytes(original_report_bytes),
            original_report_size=len(original_report_bytes),
            envelope_checksum=ZERO_HASH,
            **values,
        )
        return candidate.with_computed_checksum()

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProgressReportUploadEnvelope:
        envelope = cls(**dict(payload))
        if not envelope.verify_checksum():
            raise ValueError("upload envelope checksum mismatch")
        envelope.original_report_bytes()
        return envelope

    def original_report_bytes(self) -> bytes:
        from backend.workflow_packages.serialization import sha256_bytes

        try:
            content = base64.b64decode(self.original_report_base64, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ValueError("original report is not valid base64") from error
        if len(content) != self.original_report_size:
            raise ValueError("original report size mismatch")
        if sha256_bytes(content) != self.original_report_checksum:
            raise ValueError("original report byte checksum mismatch")
        return content

    def with_computed_checksum(self) -> ProgressReportUploadEnvelope:
        payload = self.to_dict()
        payload["envelope_checksum"] = None
        return replace(self, envelope_checksum=canonical_hash(payload))

    def verify_checksum(self) -> bool:
        return self.envelope_checksum == self.with_computed_checksum().envelope_checksum


@dataclass(frozen=True, slots=True)
class NormalizedProgressRecord(SerializableContract):
    normalized_schema_version: str
    source_schema_version: str
    normalizer_version: str
    report_id: str
    report_checksum: str
    report_content_checksum: str | None
    original_report_checksum: str
    package_id: str
    package_schema_version: str | None
    package_checksum: str
    project_id: str
    workflow_id: str
    workflow_version: str
    workflow_checksum: str | None
    execution_round: int
    harness_type: str
    harness_version: str | None
    harness_session_id: str | None
    previous_report_id: str | None
    previous_report_checksum: str | None
    started_at: str
    completed_at: str
    status: ProgressStatus
    completed_work: tuple[str, ...]
    current_state: str
    next_recommended_action: str
    continuation_reason: str | None
    output_artifacts: tuple[OutputArtifactReference, ...]
    context_before_checksum: str | None
    context_after_checksum: str | None
    legacy_context_checksum: str | None
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    unresolved_questions: tuple[str, ...]
    continuation_instructions: tuple[str, ...]
    skill_pins: tuple[PinReference, ...]
    template_pins: tuple[PinReference, ...]
    generated_at: str | None
    experimental_declaration: str
    compatibility_assumptions: tuple[str, ...]
    unavailable_fields: tuple[str, ...]
    evidence_limitations: tuple[str, ...]
    chain_state: ChainState

    def __post_init__(self) -> None:
        if self.normalized_schema_version != NORMALIZED_SCHEMA_VERSION:
            raise ValueError("invalid normalized record schema")
        for field_name in (
            "completed_work",
            "warnings",
            "errors",
            "unresolved_questions",
            "continuation_instructions",
            "compatibility_assumptions",
            "unavailable_fields",
            "evidence_limitations",
        ):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))
        object.__setattr__(self, "output_artifacts", tuple(self.output_artifacts))
        object.__setattr__(self, "skill_pins", tuple(self.skill_pins))
        object.__setattr__(self, "template_pins", tuple(self.template_pins))
        if not isinstance(self.status, ProgressStatus):
            object.__setattr__(self, "status", ProgressStatus(self.status))
        if not isinstance(self.chain_state, ChainState):
            object.__setattr__(self, "chain_state", ChainState(self.chain_state))


@dataclass(frozen=True, slots=True)
class UploadedProgressReport(SerializableContract):
    receipt_id: str
    project_id: str
    workflow_instance_id: str
    package_id: str
    package_checksum: str
    report_id: str
    report_checksum: str
    report_schema_version: str
    original_report_checksum: str
    original_report_size: int
    original_report_media_type: str
    original_storage_key: str
    envelope_checksum: str
    uploaded_at: str
    received_at: str
    uploader_type: str
    client_version: str
    source_path_hint: str
    validation_status: ValidationStatus
    validation_errors: tuple[str, ...]
    validation_warnings: tuple[str, ...]
    chain_state: ChainState
    accepted_for_projection: bool
    normalized_record: NormalizedProgressRecord | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "validation_errors", tuple(self.validation_errors))
        object.__setattr__(self, "validation_warnings", tuple(self.validation_warnings))


@dataclass(frozen=True, slots=True)
class ProgressUploadReceipt(SerializableContract):
    receipt_id: str
    project_id: str
    workflow_instance_id: str
    package_id: str
    report_id: str
    report_checksum: str
    original_report_checksum: str
    validation_status: ValidationStatus
    chain_state: ChainState
    accepted_for_projection: bool
    idempotent_replay: bool
    uploaded_at: str
    received_at: str
    warning_count: int
    error_count: int
    receipt_checksum: str

    def __post_init__(self) -> None:
        if self.warning_count < 0 or self.error_count < 0:
            raise ValueError("receipt counts must be non-negative")
        require_sha256(self.receipt_checksum, "receipt_checksum")

    def with_computed_checksum(self) -> ProgressUploadReceipt:
        payload = self.to_dict()
        payload.pop("receipt_checksum")
        payload.pop("idempotent_replay")
        return replace(self, receipt_checksum=canonical_hash(payload))

    def verify_checksum(self) -> bool:
        return self.receipt_checksum == self.with_computed_checksum().receipt_checksum


@dataclass(frozen=True, slots=True)
class ProjectProgressProjection(SerializableContract):
    schema_version: str
    project_id: str
    package_id: str
    package_schema_version: str | None
    package_checksum: str
    workflow_id: str
    workflow_version: str
    latest_accepted_report_id: str
    latest_accepted_report_checksum: str
    latest_execution_round: int
    latest_status: ProgressStatus
    completed_work_summary: tuple[str, ...]
    current_state_summary: str
    next_recommended_action: str
    output_artifacts: tuple[OutputArtifactReference, ...]
    warning_count: int
    error_count: int
    unresolved_question_count: int
    harness_type: str
    latest_local_execution_timestamp: str
    latest_upload_timestamp: str
    chain_state: ChainState
    legacy_warning_state: bool
    projection_checksum: str

    def __post_init__(self) -> None:
        if self.schema_version != PROJECTION_SCHEMA_VERSION:
            raise ValueError("invalid projection schema")
        object.__setattr__(self, "completed_work_summary", tuple(self.completed_work_summary))
        object.__setattr__(self, "output_artifacts", tuple(self.output_artifacts))
        require_sha256(self.projection_checksum, "projection_checksum")

    def with_computed_checksum(self) -> ProjectProgressProjection:
        payload = self.to_dict()
        payload["projection_checksum"] = None
        return replace(self, projection_checksum=canonical_hash(payload))

    def verify_checksum(self) -> bool:
        return self.projection_checksum == self.with_computed_checksum().projection_checksum


@dataclass(frozen=True, slots=True)
class WorkflowStageProjection(SerializableContract):
    code: str
    label: str


@dataclass(frozen=True, slots=True)
class WorkflowBlockerProjection(SerializableContract):
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class WorkflowNextActionProjection(SerializableContract):
    surface: str
    code: str
    label: str
    description: str
    command: str | None = None

    def __post_init__(self) -> None:
        if self.surface not in {"BROWSER", "LOCAL", "INFORMATIONAL", "NONE"}:
            raise ValueError("invalid Workflow next-action surface")


@dataclass(frozen=True, slots=True)
class WorkflowOutputProjection(SerializableContract):
    label: str
    artifact_id: str | None
    artifact_type: str
    artifact_schema: str
    checksum: str | None
    produced_at: str | None
    progress_round: int | None
    state: str

    def __post_init__(self) -> None:
        if self.state not in {"EXPECTED", "PRODUCED"}:
            raise ValueError("invalid Workflow Output presentation state")
        if self.state == "PRODUCED" and (
            self.artifact_id is None
            or self.checksum is None
            or self.produced_at is None
            or self.progress_round is None
        ):
            raise ValueError("produced Workflow Output requires exact identity")


@dataclass(frozen=True, slots=True)
class WorkflowActionProjection(SerializableContract):
    stage: WorkflowStageProjection
    actor: str
    attention_state: str
    blocker: WorkflowBlockerProjection | None
    next_action: WorkflowNextActionProjection
    expected_output: WorkflowOutputProjection | None
    latest_output: WorkflowOutputProjection | None

    def __post_init__(self) -> None:
        if self.actor not in {"OWNER", "AGENT", "SYSTEM", "NONE"}:
            raise ValueError("invalid Workflow presentation actor")
        if self.attention_state not in {
            "NORMAL", "OWNER_ACTION_REQUIRED", "BLOCKED",
            "ATTENTION_REQUIRED", "COMPLETED",
        }:
            raise ValueError("invalid Workflow presentation attention state")


@dataclass(frozen=True, slots=True)
class ProjectRecentChangeProjection(SerializableContract):
    summary: str
    changed_at: str | None


@dataclass(frozen=True, slots=True)
class ProjectAttentionProjection(SerializableContract):
    recommended_workflow_instance_id: str | None
    recommended_workflow_label: str | None
    action: WorkflowActionProjection
    recent_change: ProjectRecentChangeProjection
    latest_output: WorkflowOutputProjection | None


@dataclass(frozen=True, slots=True)
class WorkflowInstanceProgressProjection(SerializableContract):
    """Cloud-known research projection for exactly one Workflow Instance."""

    schema_version: str
    project_id: str
    workflow_instance_id: str
    workflow_definition_id: str
    workflow_definition_version: str
    workflow_role: str | None
    core_capability_maturity: str
    workflow_display_name: str
    instance_display_name: str
    friendly_instance_label: str
    lifecycle: str
    desired_state: str
    capsule_id: str | None
    capsule_version: str | None
    research_status: str
    latest_report_id: str | None
    latest_report_checksum: str | None
    latest_execution_round: int | None
    latest_summary: str | None
    next_recommended_action: str | None
    artifact_metadata: tuple[OutputArtifactReference, ...]
    report_count: int
    first_activity_at: str | None
    latest_activity_at: str | None
    installation_state: str
    installation_manifest_revision: int | None
    sync_uncertainty: str
    readiness: str
    next_action: str
    missing_required_inputs: tuple[str, ...]
    compatible_input_counts: Mapping[str, int]
    bound_required_inputs: tuple[str, ...]
    result_count: int
    action: WorkflowActionProjection

    def __post_init__(self) -> None:
        if self.schema_version != WORKFLOW_INSTANCE_PROJECTION_SCHEMA_VERSION:
            raise ValueError("invalid Workflow Instance Progress schema")
        if self.core_capability_maturity not in {"REVIEWED_CORE", "SCAFFOLD_CORE"}:
            raise ValueError("invalid Workflow Instance core capability maturity")
        if self.workflow_role not in {None, "INITIAL", "REVISION"}:
            raise ValueError("invalid Workflow role")
        if self.report_count < 0:
            raise ValueError("report_count must be non-negative")
        if self.result_count < 0:
            raise ValueError("result_count must be non-negative")
        object.__setattr__(self, "artifact_metadata", tuple(self.artifact_metadata))
        object.__setattr__(self, "missing_required_inputs", tuple(self.missing_required_inputs))
        object.__setattr__(self, "bound_required_inputs", tuple(self.bound_required_inputs))
        object.__setattr__(
            self,
            "compatible_input_counts",
            _freeze_json(self.compatible_input_counts, path="compatible_input_counts"),
        )


@dataclass(frozen=True, slots=True)
class ProjectWorkflowProgressProjection(SerializableContract):
    """Non-linear Project aggregation plus a bounded immutable history page."""

    schema_version: str
    project_id: str
    project_name: str
    research_topic: str
    manifest_revision: int
    cloud_observed_at: str
    active_workflow_count: int
    retired_workflow_count: int
    total_progress_report_count: int
    latest_project_activity_at: str | None
    status_counts: Mapping[str, int]
    instances: tuple[WorkflowInstanceProgressProjection, ...]
    history: tuple[UploadedProgressReport, ...]
    history_offset: int
    history_limit: int
    history_total: int
    has_more_history: bool
    dependency_edges: tuple[Mapping[str, Any], ...]
    recommended_workflow_instance_id: str | None
    recommended_next_action: str
    attention: ProjectAttentionProjection

    def __post_init__(self) -> None:
        if self.schema_version != PROJECT_WORKFLOW_PROGRESS_SCHEMA_VERSION:
            raise ValueError("invalid Project Progress schema")
        for name in (
            "active_workflow_count",
            "retired_workflow_count",
            "total_progress_report_count",
            "history_offset",
            "history_limit",
            "history_total",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        object.__setattr__(self, "status_counts", _freeze_json(self.status_counts, path="status_counts"))
        object.__setattr__(self, "instances", tuple(self.instances))
        object.__setattr__(self, "history", tuple(self.history))
        object.__setattr__(
            self,
            "dependency_edges",
            tuple(_freeze_json(item, path="dependency_edges") for item in self.dependency_edges),
        )


def immutable_metadata(value: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if value is None:
        return None
    frozen = _freeze_json(value, path="metadata")
    if not isinstance(frozen, Mapping):
        raise ValueError("metadata must be an object")
    return MappingProxyType(dict(frozen))


def normalized_record_from_dict(payload: Mapping[str, Any]) -> NormalizedProgressRecord:
    return NormalizedProgressRecord(
        **{
            **dict(payload),
            "status": ProgressStatus(payload["status"]),
            "completed_work": tuple(payload["completed_work"]),
            "output_artifacts": tuple(
                OutputArtifactReference(**item) for item in payload["output_artifacts"]
            ),
            "warnings": tuple(payload["warnings"]),
            "errors": tuple(payload["errors"]),
            "unresolved_questions": tuple(payload["unresolved_questions"]),
            "continuation_instructions": tuple(payload["continuation_instructions"]),
            "skill_pins": tuple(PinReference(**item) for item in payload["skill_pins"]),
            "template_pins": tuple(
                PinReference(**item) for item in payload["template_pins"]
            ),
            "compatibility_assumptions": tuple(payload["compatibility_assumptions"]),
            "unavailable_fields": tuple(payload["unavailable_fields"]),
            "evidence_limitations": tuple(payload["evidence_limitations"]),
            "chain_state": ChainState(payload["chain_state"]),
        }
    )


def projection_from_dict(payload: Mapping[str, Any]) -> ProjectProgressProjection:
    projection = ProjectProgressProjection(
        **{
            **dict(payload),
            "latest_status": ProgressStatus(payload["latest_status"]),
            "completed_work_summary": tuple(payload["completed_work_summary"]),
            "output_artifacts": tuple(
                OutputArtifactReference(**item) for item in payload["output_artifacts"]
            ),
            "chain_state": ChainState(payload["chain_state"]),
        }
    )
    if not projection.verify_checksum():
        raise ValueError("persisted progress projection checksum mismatch")
    return projection
