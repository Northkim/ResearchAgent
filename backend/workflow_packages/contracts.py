"""Immutable EXPERIMENTAL_V0_1 local Workflow Package contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from .security import reject_duplicate_paths, require_relative_path, require_sha256
from .serialization import SerializableContract, canonical_hash

EXPERIMENTAL_STATUS = "EXPERIMENTAL_V0_1"
PACKAGE_SCHEMA_VERSION = "workflow-package/v0.1"
PROGRESS_SCHEMA_VERSION = "progress-report/v0.1"
CONTEXT_SCHEMA_VERSION = "local-context/v0.1"
HARNESS_ACCEPTANCE_STATUS = "HARNESS_ACCEPTANCE_PENDING"

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]{1,127}$")


def _non_empty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty")


def _identifier(value: str, name: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase stable identifier")


def _semver(value: str, name: str) -> None:
    if not isinstance(value, str) or not _SEMVER.fullmatch(value):
        raise ValueError(f"{name} must be a semantic version")


@dataclass(frozen=True, slots=True)
class PackageFileEntry(SerializableContract):
    relative_path: str
    media_type: str
    role: str
    sha256: str
    byte_size: int
    mutable_by_harness: bool
    state_classification: str
    requirement: str

    def __post_init__(self) -> None:
        require_relative_path(self.relative_path, "PackageFileEntry.relative_path")
        _non_empty(self.media_type, "PackageFileEntry.media_type")
        _non_empty(self.role, "PackageFileEntry.role")
        require_sha256(self.sha256, "PackageFileEntry.sha256")
        if self.byte_size < 0:
            raise ValueError("PackageFileEntry.byte_size must be non-negative")
        if self.state_classification not in {"INSTRUCTION", "INPUT", "OUTPUT", "STATE", "CONFIGURATION", "SCHEMA"}:
            raise ValueError("invalid PackageFileEntry.state_classification")
        if self.requirement not in {"REQUIRED", "OPTIONAL"}:
            raise ValueError("invalid PackageFileEntry.requirement")


@dataclass(frozen=True, slots=True)
class SkillPin(SerializableContract):
    name: str
    semantic_version: str
    source_type: str
    source_identity: str
    checksum: str
    relative_path: str
    required_capabilities: tuple[str, ...] = ()
    license_name: str = "ReAgent project contribution"
    attribution: str = "Original ReAgent experimental Skill; no third-party Skill content vendored."

    def __post_init__(self) -> None:
        _identifier(self.name, "SkillPin.name")
        _semver(self.semantic_version, "SkillPin.semantic_version")
        _non_empty(self.source_type, "SkillPin.source_type")
        _non_empty(self.source_identity, "SkillPin.source_identity")
        require_sha256(self.checksum, "SkillPin.checksum")
        require_relative_path(self.relative_path, "SkillPin.relative_path")
        object.__setattr__(self, "required_capabilities", tuple(self.required_capabilities))
        if any(not item.strip() for item in self.required_capabilities):
            raise ValueError("SkillPin.required_capabilities must be non-empty strings")


@dataclass(frozen=True, slots=True)
class PromptPin(SerializableContract):
    prompt_id: str
    version: str
    checksum: str
    relative_path: str
    purpose: str

    def __post_init__(self) -> None:
        _identifier(self.prompt_id, "PromptPin.prompt_id")
        _semver(self.version, "PromptPin.version")
        require_sha256(self.checksum, "PromptPin.checksum")
        require_relative_path(self.relative_path, "PromptPin.relative_path")
        _non_empty(self.purpose, "PromptPin.purpose")


@dataclass(frozen=True, slots=True)
class PackageInputManifest(SerializableContract):
    input_id: str
    relative_path: str
    checksum: str
    read_only_required: bool
    content_type: str
    source_classification: str

    def __post_init__(self) -> None:
        _identifier(self.input_id, "PackageInputManifest.input_id")
        require_relative_path(self.relative_path, "PackageInputManifest.relative_path")
        require_sha256(self.checksum, "PackageInputManifest.checksum")
        if not self.read_only_required:
            raise ValueError("experimental package inputs must be read-only")
        _non_empty(self.content_type, "PackageInputManifest.content_type")
        if self.source_classification not in {"SYNTHETIC_OFFLINE", "OWNER_SUPPLIED", "CLOUD_SUPPLIED"}:
            raise ValueError("invalid input source classification")


@dataclass(frozen=True, slots=True)
class PackageOutputContract(SerializableContract):
    required_output_path: str
    artifact_kind: str
    media_type: str
    schema_version: str
    producer_responsibility: str
    validation_policy: str

    def __post_init__(self) -> None:
        require_relative_path(self.required_output_path, "PackageOutputContract.required_output_path")
        if not self.required_output_path.startswith("outputs/"):
            raise ValueError("package outputs must remain under outputs/")
        for name, value in (
            ("artifact_kind", self.artifact_kind),
            ("media_type", self.media_type),
            ("schema_version", self.schema_version),
            ("producer_responsibility", self.producer_responsibility),
            ("validation_policy", self.validation_policy),
        ):
            _non_empty(value, f"PackageOutputContract.{name}")


@dataclass(frozen=True, slots=True)
class WorkflowPackageManifest(SerializableContract):
    package_id: str
    package_schema_version: str
    experimental_project_identity: str
    workflow_type: str
    workflow_id: str
    workflow_version: str
    workflow_checksum: str
    package_template_id: str
    package_template_version: str
    skill_pins: tuple[SkillPin, ...]
    prompt_pins: tuple[PromptPin, ...]
    input_manifest: tuple[PackageInputManifest, ...]
    output_contracts: tuple[PackageOutputContract, ...]
    required_harness_capabilities: tuple[str, ...]
    content_scope_declaration: str
    generated_at: str
    generator_version: str
    files: tuple[PackageFileEntry, ...]
    file_manifest_checksum: str
    manifest_checksum: str
    package_checksum: str
    continuation_policy: str
    proxy_capability_declaration: str
    experimental_status_declaration: str
    harness_acceptance_status: str

    def __post_init__(self) -> None:
        _identifier(self.package_id, "WorkflowPackageManifest.package_id")
        if self.package_schema_version != PACKAGE_SCHEMA_VERSION:
            raise ValueError("unsupported package schema version")
        _identifier(self.experimental_project_identity, "experimental_project_identity")
        _identifier(self.workflow_id, "workflow_id")
        _semver(self.workflow_version, "workflow_version")
        require_sha256(self.workflow_checksum, "workflow_checksum")
        _identifier(self.package_template_id, "package_template_id")
        _semver(self.package_template_version, "package_template_version")
        object.__setattr__(self, "skill_pins", tuple(self.skill_pins))
        object.__setattr__(self, "prompt_pins", tuple(self.prompt_pins))
        object.__setattr__(self, "input_manifest", tuple(self.input_manifest))
        object.__setattr__(self, "output_contracts", tuple(self.output_contracts))
        object.__setattr__(self, "required_harness_capabilities", tuple(self.required_harness_capabilities))
        object.__setattr__(self, "files", tuple(self.files))
        reject_duplicate_paths([entry.relative_path for entry in self.files])
        reject_duplicate_paths([item.required_output_path for item in self.output_contracts])
        for name, value in (
            ("file_manifest_checksum", self.file_manifest_checksum),
            ("manifest_checksum", self.manifest_checksum),
            ("package_checksum", self.package_checksum),
        ):
            require_sha256(value, name)
        if self.experimental_status_declaration != EXPERIMENTAL_STATUS:
            raise ValueError("experimental status declaration is required")
        if self.harness_acceptance_status != HARNESS_ACCEPTANCE_STATUS:
            raise ValueError("R1A packages must remain HARNESS_ACCEPTANCE_PENDING")


@dataclass(frozen=True, slots=True)
class OutputFileReference(SerializableContract):
    relative_path: str
    checksum: str

    def __post_init__(self) -> None:
        require_relative_path(self.relative_path, "OutputFileReference.relative_path")
        if not self.relative_path.startswith("outputs/"):
            raise ValueError("Progress Report outputs must be under outputs/")
        require_sha256(self.checksum, "OutputFileReference.checksum")


@dataclass(frozen=True, slots=True)
class ProgressReport(SerializableContract):
    report_id: str
    package_id: str
    package_checksum: str
    project_identity: str
    workflow_id: str
    workflow_version: str
    skill_versions: tuple[str, ...]
    template_version: str
    execution_round: int
    harness_identity: str
    started_at: str
    completed_at: str
    status: str
    completed_work: tuple[str, ...]
    current_state: str
    next_recommended_action: str
    output_files: tuple[OutputFileReference, ...]
    context_checksum: str
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    continuation_instructions: tuple[str, ...] = ()
    previous_report_id: str | None = None
    schema_version: str = PROGRESS_SCHEMA_VERSION
    report_checksum: str = "sha256:" + "0" * 64

    def __post_init__(self) -> None:
        _identifier(self.report_id, "ProgressReport.report_id")
        _identifier(self.package_id, "ProgressReport.package_id")
        require_sha256(self.package_checksum, "ProgressReport.package_checksum")
        _identifier(self.project_identity, "ProgressReport.project_identity")
        _identifier(self.workflow_id, "ProgressReport.workflow_id")
        _semver(self.workflow_version, "ProgressReport.workflow_version")
        object.__setattr__(self, "skill_versions", tuple(self.skill_versions))
        object.__setattr__(self, "completed_work", tuple(self.completed_work))
        object.__setattr__(self, "output_files", tuple(self.output_files))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "errors", tuple(self.errors))
        object.__setattr__(self, "unresolved_questions", tuple(self.unresolved_questions))
        object.__setattr__(self, "continuation_instructions", tuple(self.continuation_instructions))
        if self.execution_round < 1:
            raise ValueError("execution_round must be positive")
        if self.status not in {"IN_PROGRESS", "COMPLETED", "BLOCKED", "FAILED"}:
            raise ValueError("invalid Progress Report status")
        require_sha256(self.context_checksum, "ProgressReport.context_checksum")
        require_sha256(self.report_checksum, "ProgressReport.report_checksum")
        if self.schema_version != PROGRESS_SCHEMA_VERSION:
            raise ValueError("unsupported Progress Report schema")

    def with_computed_checksum(self) -> ProgressReport:
        payload = self.to_dict()
        payload["report_checksum"] = None
        return replace(self, report_checksum=canonical_hash(payload))

    def verify_checksum(self) -> bool:
        return self.report_checksum == self.with_computed_checksum().report_checksum


@dataclass(frozen=True, slots=True)
class LocalContext(SerializableContract):
    package_id: str
    package_checksum: str
    workflow_id: str
    workflow_version: str
    current_workflow_state: str
    completed_outputs: tuple[str, ...]
    relevant_decisions: tuple[str, ...]
    unresolved_issues: tuple[str, ...]
    next_action: str
    latest_progress_report: str | None
    previous_session_history_pointer: str | None
    updated_at: str
    schema_version: str = CONTEXT_SCHEMA_VERSION
    context_checksum: str = "sha256:" + "0" * 64

    def __post_init__(self) -> None:
        _identifier(self.package_id, "LocalContext.package_id")
        require_sha256(self.package_checksum, "LocalContext.package_checksum")
        _identifier(self.workflow_id, "LocalContext.workflow_id")
        _semver(self.workflow_version, "LocalContext.workflow_version")
        object.__setattr__(self, "completed_outputs", tuple(self.completed_outputs))
        object.__setattr__(self, "relevant_decisions", tuple(self.relevant_decisions))
        object.__setattr__(self, "unresolved_issues", tuple(self.unresolved_issues))
        require_sha256(self.context_checksum, "LocalContext.context_checksum")
        if self.schema_version != CONTEXT_SCHEMA_VERSION:
            raise ValueError("unsupported local context schema")

    def with_computed_checksum(self) -> LocalContext:
        payload = self.to_dict()
        payload["context_checksum"] = None
        return replace(self, context_checksum=canonical_hash(payload))

    def verify_checksum(self) -> bool:
        return self.context_checksum == self.with_computed_checksum().context_checksum
