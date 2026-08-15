#!/usr/bin/env python3
"""Self-contained Project Workspace lifecycle CLI.

This module intentionally uses only the Python standard library. Bootstrap
copies the same reviewed source to the Workspace root as ``reagent_local.py``.
Explicit ``sync`` performs reviewed pull-only Capsule installation; it never
executes downloaded content or rewrites existing Capsule research state.
Explicit ``artifact`` commands verify local producer bytes and materialize
checksum-bound copies without sharing writable files between Capsules.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import runpy
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable

try:
    import fcntl
except ImportError:  # pragma: no cover - supported V0.1 platform provides it
    fcntl = None

BOOTSTRAP_SCHEMA = "reagent.workspace-bootstrap/v0.1"
WORKSPACE_SCHEMA = "reagent.project-workspace/v0.1"
REGISTRY_SCHEMA = "reagent.workspace-capsule-registry/v0.1"
INSTALLED_LOCK_SCHEMA = "reagent.workspace-installed-lock/v0.1"
SYNC_PLAN_SCHEMA = "reagent.workspace-sync-plan/v0.1"
SYNC_ACK_SCHEMA = "reagent.capsule-installation-ack/v0.1"
SYNC_ACK_RECEIPT_SCHEMA = "reagent.workspace-sync-ack-receipt/v0.1"
ARTIFACT_INDEX_SCHEMA = "reagent.workspace-artifact-index/v0.1"
RESOURCE_INDEX_SCHEMA = "reagent.workspace-resource-index/v0.1"
ARTIFACT_PAGE_SCHEMA = "reagent.artifact-reference-page/v0.1"
MATERIALIZATION_PLAN_SCHEMA = "reagent.artifact-materialization-plan/v0.1"
MATERIALIZATION_RECEIPT_SCHEMA = "reagent.artifact-materialization-receipt/v0.1"
PACKAGE_SCHEMA = "workflow-package/v0.1"
DESIRED_MANIFEST_SCHEMA = "reagent.project-desired-manifest/v0.1"
WORKFLOW_ID = "literature-search-local-experimental"
WORKFLOW_VERSION = "0.3.0"
PACKAGE_TEMPLATE_ID = "literature-search-package-experimental"
CAPSULE_VERSION = "0.5.0"
TRUST_CLASSIFICATION = "TRUSTED_BUILT_IN_UNSIGNED"
SUPPORTED_CAPSULE_PINS = {
    (WORKFLOW_ID, WORKFLOW_VERSION, CAPSULE_VERSION): (
        PACKAGE_TEMPLATE_ID,
        True,
    ),
    (WORKFLOW_ID, "0.4.0", "0.6.0"): (
        PACKAGE_TEMPLATE_ID,
        False,
    ),
    ("idea-discovery-local-experimental", "0.1.0", "0.1.0"): (
        "idea-discovery-package-experimental",
        False,
    ),
    ("idea-discovery-local-experimental", "0.2.0", "0.2.0"): (
        "idea-discovery-package-experimental",
        False,
    ),
    ("idea-discovery-local-experimental", "0.2.0", "0.3.0"): (
        "idea-discovery-package-experimental",
        False,
    ),
    ("writing-local-experimental", "0.1.0", "0.1.0"): (
        "writing-scaffold-package-experimental",
        False,
    ),
    ("writing-local-experimental", "0.2.0", "0.2.0"): (
        "writing-scaffold-package-experimental",
        False,
    ),
    ("writing-local-experimental", "0.2.0", "0.3.0"): (
        "writing-scaffold-package-experimental",
        False,
    ),
    ("writing-local-experimental", "0.2.0", "0.4.0"): (
        "writing-scaffold-package-experimental",
        False,
    ),
    ("writing-local-experimental", "0.3.0", "0.5.0"): (
        "writing-scaffold-package-experimental",
        False,
    ),
    ("writing-local-experimental", "0.4.0", "0.6.0"): (
        "writing-scaffold-package-experimental",
        False,
    ),
    ("review-local-experimental", "0.1.0", "0.1.0"): (
        "review-scaffold-package-experimental",
        False,
    ),
    ("review-local-experimental", "0.2.0", "0.2.0"): (
        "review-scaffold-package-experimental",
        False,
    ),
    ("review-local-experimental", "0.2.0", "0.3.0"): (
        "review-scaffold-package-experimental",
        False,
    ),
    ("review-local-experimental", "0.2.0", "0.4.0"): (
        "review-scaffold-package-experimental",
        False,
    ),
    ("review-local-experimental", "0.3.0", "0.5.0"): (
        "review-scaffold-package-experimental",
        False,
    ),
    ("reproduction-experiment-local-experimental", "0.1.0", "0.1.0"): (
        "reproduction-experiment-scaffold-package-experimental",
        False,
    ),
    ("reproduction-experiment-local-experimental", "0.2.0", "0.2.0"): (
        "reproduction-experiment-scaffold-package-experimental",
        False,
    ),
    ("reproduction-experiment-local-experimental", "0.3.0", "0.3.0"): (
        "reproduction-experiment-scaffold-package-experimental",
        False,
    ),
    ("reproduction-experiment-local-experimental", "0.3.0", "0.4.0"): (
        "reproduction-experiment-scaffold-package-experimental",
        False,
    ),
    ("reproduction-experiment-local-experimental", "0.3.0", "0.5.0"): (
        "reproduction-experiment-scaffold-package-experimental",
        False,
    ),
    ("reproduction-experiment-local-experimental", "0.4.0", "0.6.0"): (
        "reproduction-experiment-scaffold-package-experimental",
        False,
    ),
    ("reproduction-experiment-local-experimental", "0.4.0", "0.7.0"): (
        "reproduction-experiment-scaffold-package-experimental",
        False,
    ),
}
LEGACY_NAMESPACE = uuid.UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966")

WORKSPACE_DESCRIPTOR = "project.json"
BOOTSTRAP_CACHE = ".reagent/bootstrap.json"
DESIRED_MANIFEST_CACHE = ".reagent/desired-manifest.json"
CAPSULE_REGISTRY = ".reagent/capsule-registry.json"
INSTALLED_LOCK = ".reagent/installed-lock.json"
SYNC_JOURNAL = ".reagent/sync/current.json"
SYNC_LOCK = ".reagent/runtime/sync.lock"
ACKNOWLEDGEMENTS_ROOT = ".reagent/acknowledgements"
INSTALL_RECEIPTS_ROOT = ".reagent/receipts/installations"
ARTIFACT_INDEX = ".reagent/artifact-index.json"
RESOURCE_INDEX = ".reagent/resource-index.json"
RESOURCE_ROOT = "resources"
MATERIALIZATION_RECEIPTS_ROOT = ".reagent/receipts/materializations"
PROGRESS_RECEIPTS_ROOT = ".reagent/receipts/progress"
WORKFLOW_LIST_SCHEMA = "reagent.workspace-workflow-list/v0.1"
PROGRESS_REPORT_SCHEMA = "progress-report/v0.2"
PROGRESS_RECEIPT_SCHEMA = "reagent.workspace-progress-ack/v0.1"

EXIT_SUCCESS = 0
EXIT_USAGE = 2
EXIT_IDENTITY = 10
EXIT_CLOUD = 20
EXIT_ACK_PENDING = 30
EXIT_CONCURRENCY = 40
EXIT_VALIDATION = 50
EXIT_FILESYSTEM = 60
EXIT_INTERNAL = 70

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
PROJECT_ID = re.compile(r"^project-[0-9a-f]{32}$")
WORKSPACE_ID = re.compile(r"^workspace-[0-9a-f]{32}$")
WORKFLOW_INSTANCE_ID = re.compile(r"^wfi-[0-9a-f]{32}$")
CAPSULE_ID = re.compile(r"^capsule-[0-9a-f]{32}$")
ARTIFACT_ID = re.compile(r"^artifact-[0-9a-f]{32}$")
BINDING_ID = re.compile(r"^artifact-binding-[0-9a-f]{32}$")
RESOURCE_ID = re.compile(r"^resource-[0-9a-f]{32}$")
RESOURCE_BINDING_ID = re.compile(r"^resource-binding-[0-9a-f]{32}$")
STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{1,127}$")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")
MAX_FILES = 5_000
MAX_PACKAGE_BYTES = 536_870_912
MAX_FILE_BYTES = 134_217_728
MAX_CONTROL_JSON_BYTES = 2_097_152
REAL_PROVIDER_DISCLOSURE_VERSION = "reagent.openalex-owner-disclosure/v0.1"
REAL_PROVIDER_CONFIRMATION = "continue-real-search"
PROVIDER_CREDENTIAL_ENV_VARS = (
    "REAGENT_OPENALEX_API_KEY",
    "OPENALEX_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
)

PROGRESS_REPORT_FIELDS = {
    "schema_version", "report_id", "report_content_checksum", "report_checksum",
    "package_id", "package_schema_version", "package_checksum", "project_id",
    "workflow_id", "workflow_version", "workflow_checksum", "execution_round",
    "harness_type", "harness_version", "harness_session_id", "previous_report_id",
    "previous_report_checksum", "started_at", "completed_at", "status",
    "completed_work", "current_state", "next_recommended_action",
    "continuation_reason", "output_artifacts", "context_before_checksum",
    "context_after_checksum", "warnings", "errors", "unresolved_questions",
    "continuation_instructions", "skill_pins", "template_pins", "generated_at",
    "experimental_declaration",
}

_SECRET_PATTERNS = (
    re.compile(b"sk-" + rb"ant-[A-Za-z0-9_-]{8,}"),
    re.compile(b"sk-" + rb"proj-[A-Za-z0-9_-]{8,}"),
    re.compile(b"-----BEGIN " + rb"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"(?:ANTHROPIC|OPENAI)_API_KEY\s*=[^\s<]+"),
    re.compile(
        rb"(?:REAGENT_)?OPENALEX_API_KEY\s*=\s*(?!['\"]?<)[^\s]+"
    ),
    re.compile(b"postgres" + rb"(?:ql)?://[^\s/:]+:[^\s/@]+@"),
    re.compile(b"/" + b"Users/"),
    re.compile(b"/" + b"Volumes/"),
    re.compile(rb"[A-Za-z]:\\\\"),
)
_CREDENTIAL_PATTERNS = _SECRET_PATTERNS[:6]

_WORKSPACE_FIELDS = {
    "schema_version",
    "project_id",
    "workspace_id",
    "created_at",
    "desired_manifest_path",
    "installed_lock_path",
    "capsules_root",
    "artifact_materialization_root",
    "resource_root",
    "secret_policy",
    "cloud_origin_id",
    "bootstrap_manifest_revision",
    "bootstrap_manifest_checksum",
    "workspace_lifecycle",
    "descriptor_checksum",
}

_BOOTSTRAP_FIELDS = {
    "schema_version",
    "workspace_schema_version",
    "project_id",
    "workspace_id",
    "cloud_origin_id",
    "project_api_path",
    "workspace_lifecycle",
    "bootstrap_manifest_revision",
    "desired_manifest_checksum",
    "desired_manifest",
    "workflow_capsules",
    "created_at",
    "descriptor_checksum",
}

_CAPSULE_FIELDS = {
    "workflow_instance_id",
    "workflow_definition_id",
    "workflow_definition_version",
    "capsule_id",
    "capsule_version",
    "capsule_definition_checksum",
    "desired_state",
    "legacy_package_compatible",
    "package_schema_version",
    "package_template_id",
    "trust_classification",
    "legacy_package",
}

_PACKAGE_REFERENCE_FIELDS = {
    "package_id",
    "package_schema_version",
    "package_checksum",
    "manifest_checksum",
    "zip_checksum",
    "download_path",
}


class WorkspaceCLIError(RuntimeError):
    """Safe, stable CLI failure with an application code and exit class."""

    def __init__(self, code: str, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code


@dataclass(frozen=True, slots=True)
class WorkspaceOperationResult:
    status: str
    project_id: str
    workspace_id: str
    manifest_revision: int
    workflow_instance_id: str | None = None
    capsule_relative_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "schema_version": "reagent.workspace-operation-result/v0.1",
            "status": self.status,
            "project_id": self.project_id,
            "workspace_id": self.workspace_id,
            "manifest_revision": self.manifest_revision,
        }
        if self.workflow_instance_id is not None:
            value["workflow_instance_id"] = self.workflow_instance_id
        if self.capsule_relative_path is not None:
            value["capsule_relative_path"] = self.capsule_relative_path
        return value


@dataclass(frozen=True, slots=True)
class WorkspaceSyncResult:
    status: str
    project_id: str
    workspace_id: str
    manifest_revision: int
    installed_capsules: int
    retained_capsules: int
    acknowledgement_status: str
    lock_checksum: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "reagent.workspace-sync-result/v0.1",
            "status": self.status,
            "project_id": self.project_id,
            "workspace_id": self.workspace_id,
            "manifest_revision": self.manifest_revision,
            "installed_capsules": self.installed_capsules,
            "retained_capsules": self.retained_capsules,
            "acknowledgement_status": self.acknowledgement_status,
            "lock_checksum": self.lock_checksum,
        }


@dataclass(frozen=True, slots=True)
class ArtifactOperationResult:
    status: str
    project_id: str
    workspace_id: str
    artifact_count: int
    materialized_count: int = 0
    consumer_workflow_instance_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "schema_version": "reagent.artifact-operation-result/v0.1",
            "status": self.status,
            "project_id": self.project_id,
            "workspace_id": self.workspace_id,
            "artifact_count": self.artifact_count,
            "materialized_count": self.materialized_count,
        }
        if self.consumer_workflow_instance_id is not None:
            value["consumer_workflow_instance_id"] = (
                self.consumer_workflow_instance_id
            )
        return value


@dataclass(frozen=True, slots=True)
class WorkflowRunResult:
    status: str
    project_id: str
    workspace_id: str
    workflow_instance_id: str
    capsule_relative_path: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "reagent.workflow-run-result/v0.1",
            "status": self.status,
            "project_id": self.project_id,
            "workspace_id": self.workspace_id,
            "workflow_instance_id": self.workflow_instance_id,
            "capsule_relative_path": self.capsule_relative_path,
        }


@dataclass(frozen=True, slots=True)
class LocalProgressReadiness:
    """One authoritative local upload-readiness decision for list and run."""

    state: str
    reports: tuple[dict[str, Any], ...]
    reason: str | None = None


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def validate_bootstrap_descriptor(document: Any) -> dict[str, Any]:
    value = _object(document, "Workspace bootstrap descriptor")
    _exact_fields(value, _BOOTSTRAP_FIELDS, "Workspace bootstrap descriptor")
    if value["schema_version"] != BOOTSTRAP_SCHEMA:
        raise _identity("WORKSPACE_SCHEMA_UNSUPPORTED", "Unsupported Workspace bootstrap schema")
    if value["workspace_schema_version"] != WORKSPACE_SCHEMA:
        raise _identity("WORKSPACE_SCHEMA_UNSUPPORTED", "Unsupported Project Workspace schema")
    _match(value["project_id"], PROJECT_ID, "project_id")
    _match(value["workspace_id"], WORKSPACE_ID, "workspace_id")
    _match(value["cloud_origin_id"], STABLE_ID, "cloud_origin_id")
    if value["project_api_path"] != f"/projects/{value['project_id']}":
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Project API identity does not match Project")
    if value["workspace_lifecycle"] != "ACTIVE":
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Workspace lifecycle is not bootstrap-compatible")
    revision = _positive_int(value["bootstrap_manifest_revision"], "bootstrap_manifest_revision")
    _checksum(value["desired_manifest_checksum"], "desired_manifest_checksum")
    _timestamp(value["created_at"], "created_at")

    manifest = _object(value["desired_manifest"], "Desired Project Manifest")
    if (
        manifest.get("schema_version") != DESIRED_MANIFEST_SCHEMA
        or manifest.get("project_id") != value["project_id"]
        or manifest.get("workspace_id") != value["workspace_id"]
        or manifest.get("manifest_revision") != revision
        or manifest.get("canonical_checksum") != value["desired_manifest_checksum"]
    ):
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Desired Manifest identity is inconsistent")
    manifest_payload = dict(manifest)
    manifest_checksum = manifest_payload.pop("canonical_checksum", None)
    if canonical_hash(manifest_payload) != manifest_checksum:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Desired Manifest checksum is invalid")

    capsules = value["workflow_capsules"]
    if not isinstance(capsules, list) or not capsules or len(capsules) > 100:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Workspace bootstrap Capsule list is invalid")
    seen: set[str] = set()
    previous = ""
    capsule_documents: dict[str, dict[str, Any]] = {}
    for raw in capsules:
        capsule = _object(raw, "Workspace Capsule pin")
        _exact_fields(capsule, _CAPSULE_FIELDS, "Workspace Capsule pin")
        instance_id = capsule["workflow_instance_id"]
        _match(instance_id, WORKFLOW_INSTANCE_ID, "workflow_instance_id")
        if instance_id in seen or instance_id < previous:
            raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Workspace Capsule pins are not uniquely ordered")
        seen.add(instance_id)
        capsule_documents[instance_id] = capsule
        previous = instance_id
        _match(capsule["workflow_definition_id"], STABLE_ID, "workflow_definition_id")
        _match(capsule["workflow_definition_version"], SEMVER, "workflow_definition_version")
        _match(capsule["capsule_id"], CAPSULE_ID, "capsule_id")
        _match(capsule["capsule_version"], SEMVER, "capsule_version")
        _checksum(capsule["capsule_definition_checksum"], "capsule_definition_checksum")
        if capsule["desired_state"] not in {"ACTIVE", "RETIRED"}:
            raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Workspace Capsule desired state is invalid")
        if not isinstance(capsule["legacy_package_compatible"], bool):
            raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Legacy compatibility flag is invalid")
        if not isinstance(capsule["package_schema_version"], str):
            raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Package schema compatibility is invalid")
        _match(capsule["package_template_id"], STABLE_ID, "package_template_id")
        if capsule["trust_classification"] != TRUST_CLASSIFICATION:
            raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Capsule trust is not accepted")
        package = capsule["legacy_package"]
        if package is not None:
            package = _object(package, "Legacy Package reference")
            _exact_fields(package, _PACKAGE_REFERENCE_FIELDS, "Legacy Package reference")
            if not isinstance(package["package_id"], str) or not package["package_id"]:
                raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Legacy Package identity is invalid")
            if package["package_schema_version"] != capsule["package_schema_version"]:
                raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Legacy Package schema pin is inconsistent")
            for field in ("package_checksum", "manifest_checksum", "zip_checksum"):
                _checksum(package[field], field)
            expected_prefix = f"/projects/{value['project_id']}/packages/{package['package_id']}/"
            if package["download_path"] != expected_prefix + "download":
                raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Legacy Package download identity is invalid")

    desired_instances = manifest.get("workflow_instances")
    if not isinstance(desired_instances, list) or len(desired_instances) != len(capsule_documents):
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Desired Manifest Capsule pins are incomplete")
    desired_by_id = {
        item.get("workflow_instance_id"): item
        for item in desired_instances
        if isinstance(item, dict)
    }
    if set(desired_by_id) != set(capsule_documents):
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Desired Manifest Capsule identities disagree")
    for instance_id, capsule in capsule_documents.items():
        desired = desired_by_id[instance_id]
        if (
            desired.get("workflow_definition_id") != capsule["workflow_definition_id"]
            or desired.get("workflow_definition_version")
            != capsule["workflow_definition_version"]
            or desired.get("capsule_id") != capsule["capsule_id"]
            or desired.get("capsule_version") != capsule["capsule_version"]
            or desired.get("capsule_definition_checksum")
            != capsule["capsule_definition_checksum"]
            or desired.get("desired_state") != capsule["desired_state"]
        ):
            raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Desired Manifest Capsule pin is inconsistent")

    payload = dict(value)
    descriptor_checksum = payload.pop("descriptor_checksum")
    _checksum(descriptor_checksum, "descriptor_checksum")
    if canonical_hash(payload) != descriptor_checksum:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Workspace bootstrap checksum is invalid")
    return value


def validate_workspace_descriptor(document: Any) -> dict[str, Any]:
    value = _object(document, "Project Workspace descriptor")
    _exact_fields(value, _WORKSPACE_FIELDS, "Project Workspace descriptor")
    if value["schema_version"] != WORKSPACE_SCHEMA:
        raise _identity("WORKSPACE_SCHEMA_UNSUPPORTED", "Unsupported Project Workspace schema")
    _match(value["project_id"], PROJECT_ID, "project_id")
    _match(value["workspace_id"], WORKSPACE_ID, "workspace_id")
    _timestamp(value["created_at"], "created_at")
    constants = {
        "desired_manifest_path": DESIRED_MANIFEST_CACHE,
        "installed_lock_path": ".reagent/installed-lock.json",
        "capsules_root": "capsules",
        "artifact_materialization_root": "artifacts/materialized",
        "resource_root": "resources",
        "secret_policy": "PROHIBITED",
        "workspace_lifecycle": "ACTIVE",
    }
    if any(value.get(field) != expected for field, expected in constants.items()):
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Project Workspace policy fields are invalid")
    _match(value["cloud_origin_id"], STABLE_ID, "cloud_origin_id")
    _positive_int(value["bootstrap_manifest_revision"], "bootstrap_manifest_revision")
    _checksum(value["bootstrap_manifest_checksum"], "bootstrap_manifest_checksum")
    payload = dict(value)
    checksum = payload.pop("descriptor_checksum")
    _checksum(checksum, "descriptor_checksum")
    if canonical_hash(payload) != checksum:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Project Workspace descriptor checksum is invalid")
    return value


def bootstrap_workspace(
    *,
    target: str | Path,
    descriptor: Any,
    now: datetime | None = None,
    cli_source: bytes | None = None,
) -> WorkspaceOperationResult:
    bootstrap = validate_bootstrap_descriptor(descriptor)
    target_path = Path(target).expanduser()
    _reject_symlink_chain(target_path)
    if target_path.exists():
        if not target_path.is_dir() or target_path.is_symlink():
            raise _filesystem("FILESYSTEM_OPERATION_FAILED", "Workspace target must be a real directory")
        if any(target_path.iterdir()):
            return _existing_workspace_result(target_path, bootstrap)
    parent = target_path.parent
    if not parent.is_dir() or parent.is_symlink():
        raise _filesystem("FILESYSTEM_OPERATION_FAILED", "Workspace parent must be a real directory")
    parent_identity = _directory_identity(parent)
    timestamp = _utc_text(now or datetime.now(timezone.utc))
    workspace_payload = {
        "schema_version": WORKSPACE_SCHEMA,
        "project_id": bootstrap["project_id"],
        "workspace_id": bootstrap["workspace_id"],
        "created_at": timestamp,
        "desired_manifest_path": DESIRED_MANIFEST_CACHE,
        "installed_lock_path": ".reagent/installed-lock.json",
        "capsules_root": "capsules",
        "artifact_materialization_root": "artifacts/materialized",
        "resource_root": "resources",
        "secret_policy": "PROHIBITED",
        "cloud_origin_id": bootstrap["cloud_origin_id"],
        "bootstrap_manifest_revision": bootstrap["bootstrap_manifest_revision"],
        "bootstrap_manifest_checksum": bootstrap["desired_manifest_checksum"],
        "workspace_lifecycle": "ACTIVE",
    }
    workspace_document = {
        **workspace_payload,
        "descriptor_checksum": canonical_hash(workspace_payload),
    }
    registry = _empty_registry(bootstrap, timestamp)
    script = cli_source if cli_source is not None else Path(__file__).read_bytes()
    if not script or b"def main(" not in script:
        raise _filesystem("FILESYSTEM_OPERATION_FAILED", "Workspace CLI source is invalid")

    try:
        staging = Path(tempfile.mkdtemp(prefix=".reagent-bootstrap-", dir=parent))
    except OSError as error:
        raise _filesystem("FILESYSTEM_OPERATION_FAILED", "Workspace staging could not be created") from error
    published = False
    removed_empty_target = False
    try:
        (staging / ".reagent").mkdir(mode=0o700)
        (staging / "capsules").mkdir(mode=0o700)
        (staging / RESOURCE_ROOT).mkdir(mode=0o700)
        _atomic_write_json(staging / BOOTSTRAP_CACHE, bootstrap)
        _atomic_write_json(staging / DESIRED_MANIFEST_CACHE, bootstrap["desired_manifest"])
        _atomic_write_json(staging / CAPSULE_REGISTRY, registry)
        _atomic_write_bytes(staging / "AGENT.md", _workspace_agent().encode("utf-8"), mode=0o600)
        _atomic_write_bytes(staging / "reagent_local.py", script, mode=0o700)
        _atomic_write_json(staging / WORKSPACE_DESCRIPTOR, workspace_document)
        _validate_workspace_root(staging)
        _fsync_tree(staging)
        if _directory_identity(parent) != parent_identity:
            raise _filesystem("FILESYSTEM_OPERATION_FAILED", "Workspace parent changed during bootstrap")
        if target_path.exists():
            if any(target_path.iterdir()):
                raise _filesystem("WORKSPACE_PARTIAL_STATE", "Workspace target changed during bootstrap")
            target_path.rmdir()
            removed_empty_target = True
        os.replace(staging, target_path)
        published = True
        _fsync_directory(parent)
    except WorkspaceCLIError:
        if removed_empty_target and not target_path.exists():
            target_path.mkdir(mode=0o700)
        raise
    except OSError as error:
        if removed_empty_target and not target_path.exists():
            target_path.mkdir(mode=0o700)
        raise _filesystem("FILESYSTEM_OPERATION_FAILED", "Workspace bootstrap filesystem operation failed") from error
    finally:
        if not published and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    return WorkspaceOperationResult(
        status="CREATED",
        project_id=bootstrap["project_id"],
        workspace_id=bootstrap["workspace_id"],
        manifest_revision=bootstrap["bootstrap_manifest_revision"],
    )


def load_workspace(root: str | Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    workspace = Path(root).expanduser()
    _reject_symlink_chain(workspace)
    if not workspace.is_dir() or workspace.is_symlink():
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Workspace root must be a real directory")
    descriptor = validate_workspace_descriptor(_read_json(workspace / WORKSPACE_DESCRIPTOR))
    bootstrap = validate_bootstrap_descriptor(_read_json(workspace / BOOTSTRAP_CACHE))
    if (
        descriptor["project_id"] != bootstrap["project_id"]
        or descriptor["workspace_id"] != bootstrap["workspace_id"]
        or descriptor["bootstrap_manifest_revision"] != bootstrap["bootstrap_manifest_revision"]
        or descriptor["bootstrap_manifest_checksum"] != bootstrap["desired_manifest_checksum"]
    ):
        raise _identity("WORKSPACE_IDENTITY_CONFLICT", "Workspace identity and bootstrap cache disagree")
    validate_registry(_read_json(workspace / CAPSULE_REGISTRY), descriptor)
    return workspace, descriptor, bootstrap


def validate_registry(document: Any, workspace: dict[str, Any]) -> dict[str, Any]:
    value = _object(document, "Workspace Capsule registry")
    expected_fields = {
        "schema_version", "project_id", "workspace_id", "created_at", "entries", "registry_checksum"
    }
    _exact_fields(value, expected_fields, "Workspace Capsule registry")
    if (
        value["schema_version"] != REGISTRY_SCHEMA
        or value["project_id"] != workspace["project_id"]
        or value["workspace_id"] != workspace["workspace_id"]
    ):
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Workspace Capsule registry identity is invalid")
    _timestamp(value["created_at"], "created_at")
    entries = value["entries"]
    if not isinstance(entries, list) or len(entries) > 100:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Workspace Capsule registry entries are invalid")
    ids: list[str] = []
    for entry in entries:
        item = _object(entry, "Workspace Capsule registry entry")
        required = {
            "workflow_instance_id", "workflow_definition_id", "workflow_definition_version",
            "capsule_id", "capsule_version", "capsule_definition_checksum",
            "capsule_relative_path", "package_id", "package_checksum", "manifest_checksum",
            "source_tree_checksum", "adoption_status", "adopted_at",
        }
        _exact_fields(item, required, "Workspace Capsule registry entry")
        _match(item["workflow_instance_id"], WORKFLOW_INSTANCE_ID, "workflow_instance_id")
        _safe_package_path(item["capsule_relative_path"])
        for field in (
            "capsule_definition_checksum", "package_checksum", "manifest_checksum", "source_tree_checksum"
        ):
            _checksum(item[field], field)
        if item["adoption_status"] != "ADOPTED_LEGACY_PACKAGE":
            raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Capsule adoption status is invalid")
        _timestamp(item["adopted_at"], "adopted_at")
        ids.append(item["workflow_instance_id"])
    if ids != sorted(set(ids)):
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Workspace Capsule registry ordering is invalid")
    payload = dict(value)
    checksum = payload.pop("registry_checksum")
    _checksum(checksum, "registry_checksum")
    if canonical_hash(payload) != checksum:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Workspace Capsule registry checksum is invalid")
    return value


def adopt_legacy_package(
    *,
    source: str | Path,
    workspace_root: str | Path,
    bootstrap_descriptor: Any | None = None,
    now: datetime | None = None,
) -> WorkspaceOperationResult:
    workspace, workspace_descriptor, cached_bootstrap = load_workspace(workspace_root)
    bootstrap = (
        validate_bootstrap_descriptor(bootstrap_descriptor)
        if bootstrap_descriptor is not None
        else cached_bootstrap
    )
    if (
        bootstrap["project_id"] != workspace_descriptor["project_id"]
        or bootstrap["workspace_id"] != workspace_descriptor["workspace_id"]
    ):
        raise _identity("WORKSPACE_IDENTITY_CONFLICT", "Adoption descriptor belongs to another Workspace")
    if (
        bootstrap["bootstrap_manifest_revision"]
        < workspace_descriptor["bootstrap_manifest_revision"]
    ):
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Adoption descriptor is older than the Workspace")

    source_path = Path(source).expanduser()
    _reject_symlink_chain(source_path)
    if not source_path.exists() or source_path.is_symlink():
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package source is unavailable")
    source_stat = source_path.stat()
    extracted: tempfile.TemporaryDirectory[str] | None = None
    source_root = source_path
    source_file_checksum: str | None = None
    try:
        if source_path.is_file():
            source_file_checksum = _hash_file(source_path)
            extracted = tempfile.TemporaryDirectory(prefix="reagent-legacy-package-")
            source_root = _extract_archive_safely(source_path, Path(extracted.name))
            expected_archives = {
                item["legacy_package"]["zip_checksum"]
                for item in bootstrap["workflow_capsules"]
                if item.get("legacy_package") is not None
            }
            if source_file_checksum not in expected_archives:
                raise _package_error(
                    "LEGACY_PACKAGE_CHECKSUM_MISMATCH",
                    "Legacy Package archive does not match Cloud bootstrap metadata",
                )
        elif not source_path.is_dir():
            raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package source type is unsupported")

        manifest, tree_checksum = _validate_legacy_package(source_root, bootstrap)
        capsule = _select_capsule(bootstrap, manifest)
        relative_path = (
            f"capsules/{capsule['workflow_definition_id']}/"
            f"{capsule['workflow_instance_id']}/{capsule['capsule_version']}"
        )
        destination = workspace / relative_path
        _ensure_destination_parents(workspace, destination.parent)
        destination_parent_identity = _directory_identity(destination.parent)
        registry_path = workspace / CAPSULE_REGISTRY
        registry = validate_registry(_read_json(registry_path), workspace_descriptor)

        if destination.exists() or destination.is_symlink():
            if destination.is_symlink() or not destination.is_dir():
                raise _filesystem("CAPSULE_ADOPTION_CONFLICT", "Capsule destination has an unsafe type")
            existing_manifest, existing_checksum = _validate_legacy_package(destination, bootstrap)
            if (
                existing_manifest["package_id"] != manifest["package_id"]
                or existing_checksum != tree_checksum
            ):
                raise _filesystem("CAPSULE_ADOPTION_CONFLICT", "Capsule destination contains different state")
            _record_adoption(
                registry_path=registry_path,
                registry=registry,
                workspace=workspace_descriptor,
                capsule=capsule,
                manifest=manifest,
                source_tree_checksum=tree_checksum,
                relative_path=relative_path,
                adopted_at=_utc_text(now or datetime.now(timezone.utc)),
            )
            return WorkspaceOperationResult(
                status="ALREADY_ADOPTED",
                project_id=workspace_descriptor["project_id"],
                workspace_id=workspace_descriptor["workspace_id"],
                manifest_revision=bootstrap["bootstrap_manifest_revision"],
                workflow_instance_id=capsule["workflow_instance_id"],
                capsule_relative_path=relative_path,
            )

        try:
            staging = Path(tempfile.mkdtemp(prefix=".reagent-adopt-", dir=destination.parent))
        except OSError as error:
            raise _filesystem("FILESYSTEM_OPERATION_FAILED", "Capsule staging could not be created") from error
        published = False
        try:
            _copy_tree_safely(source_root, staging)
            copied_manifest, copied_checksum = _validate_legacy_package(staging, bootstrap)
            if copied_manifest["package_id"] != manifest["package_id"] or copied_checksum != tree_checksum:
                raise _package_error("LEGACY_PACKAGE_CHECKSUM_MISMATCH", "Copied Package state failed verification")
            if _tree_checksum(source_root) != tree_checksum:
                raise _package_error("LEGACY_PACKAGE_CHECKSUM_MISMATCH", "Source Package changed during adoption")
            if source_file_checksum is not None and _hash_file(source_path) != source_file_checksum:
                raise _package_error("LEGACY_PACKAGE_CHECKSUM_MISMATCH", "Source archive changed during adoption")
            if source_path.stat() != source_stat:
                # Metadata-only access-time changes are ignored, but identity, size,
                # modification time and inode changes are not.
                current = source_path.stat()
                if (
                    current.st_dev,
                    current.st_ino,
                    current.st_size,
                    current.st_mtime_ns,
                ) != (
                    source_stat.st_dev,
                    source_stat.st_ino,
                    source_stat.st_size,
                    source_stat.st_mtime_ns,
                ):
                    raise _package_error("LEGACY_PACKAGE_CHECKSUM_MISMATCH", "Source Package identity changed during adoption")
            _fsync_tree(staging)
            _reject_symlink_chain(destination.parent)
            if _directory_identity(destination.parent) != destination_parent_identity:
                raise _filesystem("UNSAFE_PACKAGE_PATH", "Capsule destination changed during adoption")
            _assert_within(workspace, destination)
            os.replace(staging, destination)
            published = True
            _fsync_directory(destination.parent)
            try:
                _record_adoption(
                    registry_path=registry_path,
                    registry=registry,
                    workspace=workspace_descriptor,
                    capsule=capsule,
                    manifest=manifest,
                    source_tree_checksum=tree_checksum,
                    relative_path=relative_path,
                    adopted_at=_utc_text(now or datetime.now(timezone.utc)),
                )
            except Exception as error:
                raise _filesystem(
                    "WORKSPACE_PARTIAL_STATE",
                    "Capsule copy is valid but registry publication is pending; rerun adoption",
                ) from error
        except WorkspaceCLIError:
            raise
        except OSError as error:
            raise _filesystem("FILESYSTEM_OPERATION_FAILED", "Capsule adoption filesystem operation failed") from error
        finally:
            if not published and staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
        return WorkspaceOperationResult(
            status="ADOPTED",
            project_id=workspace_descriptor["project_id"],
            workspace_id=workspace_descriptor["workspace_id"],
            manifest_revision=bootstrap["bootstrap_manifest_revision"],
            workflow_instance_id=capsule["workflow_instance_id"],
            capsule_relative_path=relative_path,
        )
    finally:
        if extracted is not None:
            extracted.cleanup()


def _validate_legacy_package(
    root: Path,
    bootstrap: dict[str, Any],
    *,
    expected_instance_id: str | None = None,
    require_legacy_compatibility: bool = True,
) -> tuple[dict[str, Any], str]:
    if root.is_symlink() or not root.is_dir():
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package root must be a real directory")
    manifest = _read_package_json(root / "package-manifest.json")
    if manifest.get("package_schema_version") != PACKAGE_SCHEMA:
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package schema is unsupported")
    pin = (
        manifest.get("workflow_id"),
        manifest.get("workflow_version"),
        manifest.get("package_template_version"),
    )
    expected_pin = SUPPORTED_CAPSULE_PINS.get(pin)
    if expected_pin is None or manifest.get("package_template_id") != expected_pin[0]:
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package Workflow or template is unsupported")
    project_id = manifest.get("experimental_project_identity")
    _match_package(project_id, PROJECT_ID, "experimental_project_identity")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries or len(entries) > MAX_FILES:
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package file manifest is invalid")
    normalized: list[dict[str, Any]] = []
    declared: dict[str, dict[str, Any]] = {}
    case_paths: dict[str, str] = {}
    for raw in entries:
        entry = _object_package(raw, "Package file entry")
        path = _safe_package_path(entry.get("relative_path"))
        _record_case_path(case_paths, path)
        if path in declared:
            raise _package_error("UNSAFE_PACKAGE_PATH", "Legacy Package contains duplicate paths")
        if not isinstance(entry.get("mutable_by_harness"), bool):
            raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Package mutable-file policy is invalid")
        item = dict(entry)
        if item["mutable_by_harness"]:
            item["sha256"] = None
            item["byte_size"] = None
        else:
            _checksum_package(item.get("sha256"), "file checksum")
            if not isinstance(item.get("byte_size"), int) or item["byte_size"] < 0:
                raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Package immutable file size is invalid")
        normalized.append(item)
        declared[path] = entry
    if manifest.get("file_manifest_checksum") != canonical_hash(normalized):
        raise _package_error("LEGACY_PACKAGE_CHECKSUM_MISMATCH", "Package file manifest checksum is invalid")
    manifest_payload = dict(manifest)
    manifest_payload["manifest_checksum"] = None
    manifest_payload["package_checksum"] = None
    manifest_payload["files"] = normalized
    if manifest.get("manifest_checksum") != canonical_hash(manifest_payload):
        raise _package_error("LEGACY_PACKAGE_CHECKSUM_MISMATCH", "Package manifest checksum is invalid")
    package_payload = {
        "package_id": manifest.get("package_id"),
        "package_schema_version": manifest.get("package_schema_version"),
        "file_manifest_checksum": manifest.get("file_manifest_checksum"),
        "manifest_checksum": manifest.get("manifest_checksum"),
    }
    if manifest.get("package_checksum") != canonical_hash(package_payload):
        raise _package_error("LEGACY_PACKAGE_CHECKSUM_MISMATCH", "Package checksum is invalid")

    capsule = _select_capsule(
        bootstrap,
        manifest,
        expected_instance_id=expected_instance_id,
        require_legacy_compatibility=require_legacy_compatibility,
    )
    package_reference = capsule.get("legacy_package")
    if package_reference is None:
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Bootstrap descriptor does not authorize a legacy Package")
    if (
        manifest.get("package_id") != package_reference["package_id"]
        or manifest.get("package_checksum") != package_reference["package_checksum"]
        or manifest.get("manifest_checksum") != package_reference["manifest_checksum"]
    ):
        raise _package_error("LEGACY_PACKAGE_IDENTITY_MISMATCH", "Legacy Package does not match Cloud bootstrap metadata")

    output_paths = {
        item.get("required_output_path")
        for item in manifest.get("output_contracts", [])
        if isinstance(item, dict)
    }
    dynamic_input_paths = _declared_dynamic_input_paths(root, declared)
    dynamic_runtime_paths = _declared_runtime_dynamic_paths(root, declared)
    allowed_dynamic = (
        "memory/progress/reports/",
        "memory/progress/receipts/",
        "memory/search/operations/",
        # Production finalizers publish validated, content-addressed Workflow
        # results below this root. These bytes are intentionally absent from
        # the immutable package file manifest, while the Capsule's validator
        # and Artifact output contract constrain their schema and filename.
        "outputs/artifacts/",
    )
    actual_files: set[str] = set()
    total_bytes = 0
    for path, relative, kind in _walk_safe_tree(root):
        _record_case_path(case_paths, relative, allow_same=True)
        if kind == "directory":
            continue
        if relative == "package-manifest.json":
            content = path.read_bytes()
            _reject_secrets(content)
            total_bytes += len(content)
            continue
        content = path.read_bytes()
        total_bytes += len(content)
        if total_bytes > MAX_PACKAGE_BYTES or len(content) > MAX_FILE_BYTES:
            raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package exceeds size limits")
        try:
            if relative in dynamic_input_paths or relative.startswith("outputs/artifacts/"):
                _reject_credentials(content)
            else:
                _reject_secrets(content)
        except WorkspaceCLIError as error:
            raise _package_error(
                error.code,
                f"{error} in {relative}",
            ) from error
        if path.name == ".DS_Store":
            if len(content) > 1_048_576:
                raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "macOS metadata exceeds the safe bound")
            continue
        entry = declared.get(relative)
        if (
            entry is None
            and relative not in output_paths
            and relative not in dynamic_input_paths
            and relative not in dynamic_runtime_paths
            and relative != "memory/current-artifact.json"
            and not relative.startswith(allowed_dynamic)
        ):
            raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package contains undeclared files")
        if entry is not None:
            actual_files.add(relative)
            if not entry["mutable_by_harness"]:
                if entry["sha256"] != sha256_bytes(content) or entry["byte_size"] != len(content):
                    raise _package_error("LEGACY_PACKAGE_CHECKSUM_MISMATCH", "Immutable Package file checksum is invalid")
    missing = sorted(
        path
        for path, entry in declared.items()
        if entry.get("requirement") == "REQUIRED" and path not in actual_files
    )
    if missing:
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package required files are missing")
    required_paths = {
        "AGENT.md", "reagent_local.py", "workflow/workflow.json",
        "memory/context.md", "inputs/project.json", "validate_package.py",
        "progress_report.py",
    }
    if manifest.get("workflow_id") == WORKFLOW_ID:
        required_paths |= {"memory/round-control.json", "inputs/research_request.json"}
    if not required_paths.issubset(declared):
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package execution contract is incomplete")
    try:
        workflow = json.loads((root / "workflow/workflow.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Workflow definition is invalid") from error
    if manifest.get("workflow_checksum") != canonical_hash(workflow):
        raise _package_error("LEGACY_PACKAGE_CHECKSUM_MISMATCH", "Legacy Workflow checksum is invalid")
    return manifest, _tree_checksum(root)


def _declared_dynamic_input_paths(
    root: Path, declared: dict[str, dict[str, Any]]
) -> set[str]:
    """Read exact materialization paths from supported immutable descriptors."""

    dynamic_input_paths = {"inputs/selected-paper-library.json"}
    for descriptor_path in (
        "workflow/scaffold.json",
        "workflow/real-experiment.json",
        "workflow/real-writing.json",
        "workflow/real-review.json",
        "workflow/writing-revision.json",
    ):
        descriptor_entry = declared.get(descriptor_path)
        if descriptor_entry is None:
            continue
        descriptor_bytes = (root / descriptor_path).read_bytes()
        if (
            descriptor_entry.get("mutable_by_harness") is not False
            or sha256_bytes(descriptor_bytes) != descriptor_entry.get("sha256")
        ):
            raise _package_error(
                "LEGACY_PACKAGE_CHECKSUM_MISMATCH",
                "Workflow input contract checksum is invalid",
            )
        descriptor = _object_package(
            _read_json(root / descriptor_path), "Workflow input contract"
        )
        requirements = descriptor.get("input_requirements", [])
        if not isinstance(requirements, list):
            raise _package_error(
                "LEGACY_PACKAGE_UNSUPPORTED",
                "Workflow input requirements are invalid",
            )
        for requirement in requirements:
            target = _safe_package_path(
                _object_package(requirement, "Workflow input requirement").get(
                    "target_relative_path"
                )
            )
            if not target.startswith("inputs/"):
                raise _package_error(
                    "UNSAFE_PACKAGE_PATH",
                    "Workflow input target must stay below inputs",
                )
            dynamic_input_paths.add(target)
    return dynamic_input_paths


def _declared_runtime_dynamic_paths(
    root: Path, declared: dict[str, dict[str, Any]]
) -> set[str]:
    """Read exact mutable working paths from supported reviewed descriptors."""

    paths: set[str] = set()
    for descriptor_path in (
        "workflow/real-writing.json", "workflow/real-review.json",
        "workflow/writing-revision.json",
    ):
        descriptor_entry = declared.get(descriptor_path)
        if descriptor_entry is None:
            continue
        descriptor_bytes = (root / descriptor_path).read_bytes()
        if (
            descriptor_entry.get("mutable_by_harness") is not False
            or sha256_bytes(descriptor_bytes) != descriptor_entry.get("sha256")
        ):
            raise _package_error(
                "LEGACY_PACKAGE_CHECKSUM_MISMATCH",
                "reviewed runtime contract checksum is invalid",
            )
        descriptor = _object_package(
            _read_json(root / descriptor_path), "reviewed runtime contract"
        )
        values = descriptor.get("runtime_dynamic_paths")
        if not isinstance(values, list) or not values:
            raise _package_error(
                "LEGACY_PACKAGE_UNSUPPORTED",
                "reviewed runtime paths are invalid",
            )
        for value in values:
            path = _safe_package_path(value)
            if (
                path.endswith("/")
                or not path.startswith(("memory/", "outputs/"))
                or path in paths
            ):
                raise _package_error(
                    "UNSAFE_PACKAGE_PATH", "reviewed runtime path is unsafe"
                )
            paths.add(path)
    return paths


def _select_capsule(
    bootstrap: dict[str, Any],
    manifest: dict[str, Any],
    *,
    expected_instance_id: str | None = None,
    require_legacy_compatibility: bool = True,
) -> dict[str, Any]:
    project_id = manifest.get("experimental_project_identity")
    expected_workspace = "workspace-" + str(project_id).removeprefix("project-")
    expected_instance = expected_instance_id or _legacy_instance_id(str(project_id))
    if project_id != bootstrap["project_id"] or expected_workspace != bootstrap["workspace_id"]:
        raise _package_error("LEGACY_PACKAGE_IDENTITY_MISMATCH", "Legacy Package belongs to another Project Workspace")
    matches = [
        item
        for item in bootstrap["workflow_capsules"]
        if item["workflow_instance_id"] == expected_instance
        and item["workflow_definition_id"] == manifest.get("workflow_id")
    ]
    if len(matches) != 1:
        raise _package_error("LEGACY_PACKAGE_IDENTITY_MISMATCH", "Legacy Package Workflow Instance identity is unavailable")
    capsule = matches[0]
    if (
        capsule["desired_state"] != "ACTIVE"
        or (
            require_legacy_compatibility
            and not capsule["legacy_package_compatible"]
        )
        or capsule["workflow_definition_version"] != manifest.get("workflow_version")
        or capsule["capsule_version"] != manifest.get("package_template_version")
        or capsule["package_schema_version"] != manifest.get("package_schema_version")
        or capsule["package_template_id"] != manifest.get("package_template_id")
    ):
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package is incompatible with the desired Capsule pin")
    return capsule


def _record_adoption(
    *,
    registry_path: Path,
    registry: dict[str, Any],
    workspace: dict[str, Any],
    capsule: dict[str, Any],
    manifest: dict[str, Any],
    source_tree_checksum: str,
    relative_path: str,
    adopted_at: str,
) -> None:
    _reject_symlink_chain(registry_path.parent)
    entry = {
        "workflow_instance_id": capsule["workflow_instance_id"],
        "workflow_definition_id": capsule["workflow_definition_id"],
        "workflow_definition_version": capsule["workflow_definition_version"],
        "capsule_id": capsule["capsule_id"],
        "capsule_version": capsule["capsule_version"],
        "capsule_definition_checksum": capsule["capsule_definition_checksum"],
        "capsule_relative_path": relative_path,
        "package_id": manifest["package_id"],
        "package_checksum": manifest["package_checksum"],
        "manifest_checksum": manifest["manifest_checksum"],
        "source_tree_checksum": source_tree_checksum,
        "adoption_status": "ADOPTED_LEGACY_PACKAGE",
        "adopted_at": adopted_at,
    }
    entries = [
        item
        for item in registry["entries"]
        if item["workflow_instance_id"] != capsule["workflow_instance_id"]
    ]
    existing = next(
        (
            item for item in registry["entries"]
            if item["workflow_instance_id"] == capsule["workflow_instance_id"]
        ),
        None,
    )
    if existing is not None:
        comparable_existing = dict(existing)
        comparable_entry = dict(entry)
        comparable_existing.pop("adopted_at", None)
        comparable_entry.pop("adopted_at", None)
        if comparable_existing != comparable_entry:
            raise _filesystem("CAPSULE_ADOPTION_CONFLICT", "Capsule registry already binds different state")
        return
    entries.append(entry)
    entries.sort(key=lambda item: item["workflow_instance_id"])
    payload = {
        "schema_version": REGISTRY_SCHEMA,
        "project_id": workspace["project_id"],
        "workspace_id": workspace["workspace_id"],
        "created_at": registry["created_at"],
        "entries": entries,
    }
    updated = {**payload, "registry_checksum": canonical_hash(payload)}
    _atomic_write_json(registry_path, updated)


def _extract_archive_safely(archive: Path, output: Path) -> Path:
    try:
        bundle = zipfile.ZipFile(archive, "r")
    except (OSError, zipfile.BadZipFile) as error:
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package archive is invalid") from error
    with bundle:
        seen: set[str] = set()
        case_paths: dict[str, str] = {}
        total = 0
        infos = bundle.infolist()
        if len(infos) > MAX_FILES:
            raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package archive has too many entries")
        for info in infos:
            raw = info.filename.rstrip("/")
            if not raw:
                continue
            name = _safe_package_path(raw)
            _record_case_path(case_paths, name)
            if name in seen:
                raise _package_error("UNSAFE_PACKAGE_PATH", "Legacy Package archive contains duplicate paths")
            seen.add(name)
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode) or (mode and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode))):
                raise _package_error("UNSAFE_PACKAGE_PATH", "Legacy Package archive contains an unsafe file type")
            if info.file_size < 0 or info.file_size > MAX_FILE_BYTES:
                raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package archive entry exceeds size limits")
            total += info.file_size
            if total > MAX_PACKAGE_BYTES:
                raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package archive exceeds size limits")
            if info.compress_size == 0 and info.file_size > 0:
                raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package archive compression is unsafe")
            if info.compress_size and info.file_size / info.compress_size > 200:
                raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package archive compression ratio is unsafe")
            target = output / name
            _assert_within(output, target)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info, "r") as source, target.open("xb") as destination:
                shutil.copyfileobj(source, destination, length=1024 * 1024)
        roots = [item for item in output.iterdir()]
        if len(roots) == 1 and roots[0].is_dir() and (roots[0] / "package-manifest.json").is_file():
            return roots[0]
        return output


def _copy_tree_safely(source: Path, destination: Path) -> None:
    for path, relative, kind in _walk_safe_tree(source):
        target = destination / relative
        _assert_within(destination, target)
        if kind == "directory":
            target.mkdir(mode=0o700, parents=True, exist_ok=True)
        else:
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            _copy_file(path, target)


def _copy_file(source: Path, destination: Path) -> None:
    with source.open("rb") as input_file, destination.open("xb") as output_file:
        while True:
            chunk = input_file.read(1024 * 1024)
            if not chunk:
                break
            output_file.write(chunk)
        output_file.flush()
        os.fsync(output_file.fileno())
    os.chmod(destination, stat.S_IMODE(source.stat(follow_symlinks=False).st_mode) & 0o700)


def _walk_safe_tree(root: Path) -> Iterable[tuple[Path, str, str]]:
    count = 0
    case_paths: dict[str, str] = {}
    for base, directories, files in os.walk(root, topdown=True, followlinks=False):
        directories.sort()
        files.sort()
        base_path = Path(base)
        for name in (*directories, *files):
            path = base_path / name
            relative = path.relative_to(root).as_posix()
            _safe_package_path(relative)
            _record_case_path(case_paths, relative)
            metadata = path.lstat()
            count += 1
            if count > MAX_FILES:
                raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package contains too many filesystem entries")
            if stat.S_ISLNK(metadata.st_mode):
                raise _package_error("UNSAFE_PACKAGE_PATH", "Legacy Package symbolic links are forbidden")
            if stat.S_ISDIR(metadata.st_mode):
                yield path, relative, "directory"
            elif stat.S_ISREG(metadata.st_mode):
                if metadata.st_nlink != 1:
                    raise _package_error("UNSAFE_PACKAGE_PATH", "Legacy Package hard links are forbidden")
                yield path, relative, "file"
            else:
                raise _package_error("UNSAFE_PACKAGE_PATH", "Legacy Package special files are forbidden")


def _tree_checksum(root: Path) -> str:
    entries: list[dict[str, Any]] = []
    for path, relative, kind in _walk_safe_tree(root):
        if kind == "directory":
            entries.append({"path": relative, "kind": kind})
        else:
            content = path.read_bytes()
            entries.append(
                {
                    "path": relative,
                    "kind": kind,
                    "size": len(content),
                    "checksum": sha256_bytes(content),
                }
            )
    return canonical_hash(entries)


def _immutable_contract_checksum(root: Path, manifest: dict[str, Any]) -> str:
    """Bind protected Package content while excluding declared mutable state."""

    entries: list[dict[str, Any]] = []
    for raw in manifest["files"]:
        if raw["mutable_by_harness"]:
            continue
        relative = _safe_package_path(raw["relative_path"])
        path = root / relative
        _assert_within(root, path)
        if path.is_symlink() or not path.is_file():
            raise _identity("LOCAL_CAPSULE_DRIFT", "Immutable Capsule file is unavailable")
        content = path.read_bytes()
        entries.append({
            "relative_path": relative,
            "sha256": sha256_bytes(content),
            "byte_size": len(content),
        })
    entries.sort(key=lambda item: item["relative_path"])
    return canonical_hash({
        "package_id": manifest["package_id"],
        "package_checksum": manifest["package_checksum"],
        "immutable_files": entries,
    })


def _existing_workspace_result(
    target: Path,
    bootstrap: dict[str, Any],
) -> WorkspaceOperationResult:
    try:
        _, workspace, cached = load_workspace(target)
    except WorkspaceCLIError as error:
        if (target / WORKSPACE_DESCRIPTOR).exists():
            raise
        raise _filesystem(
            "WORKSPACE_PARTIAL_STATE",
            "Non-empty target is not a valid Project Workspace",
        ) from error
    if (
        workspace["project_id"] != bootstrap["project_id"]
        or workspace["workspace_id"] != bootstrap["workspace_id"]
    ):
        raise _identity("WORKSPACE_IDENTITY_CONFLICT", "Target belongs to another Project Workspace")
    if workspace["schema_version"] != bootstrap["workspace_schema_version"]:
        raise _identity("WORKSPACE_SCHEMA_UNSUPPORTED", "Existing Workspace schema is incompatible")
    if cached["bootstrap_manifest_revision"] > bootstrap["bootstrap_manifest_revision"]:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Bootstrap descriptor is older than the Workspace")
    if (
        cached["bootstrap_manifest_revision"] == bootstrap["bootstrap_manifest_revision"]
        and cached["desired_manifest_checksum"] != bootstrap["desired_manifest_checksum"]
    ):
        raise _identity("WORKSPACE_IDENTITY_CONFLICT", "Manifest revision has conflicting content")
    return WorkspaceOperationResult(
        status="ALREADY_BOOTSTRAPPED",
        project_id=workspace["project_id"],
        workspace_id=workspace["workspace_id"],
        manifest_revision=workspace["bootstrap_manifest_revision"],
    )


def _validate_workspace_root(root: Path) -> None:
    workspace = validate_workspace_descriptor(_read_json(root / WORKSPACE_DESCRIPTOR))
    bootstrap = validate_bootstrap_descriptor(_read_json(root / BOOTSTRAP_CACHE))
    if (
        workspace["project_id"] != bootstrap["project_id"]
        or workspace["workspace_id"] != bootstrap["workspace_id"]
        or workspace["bootstrap_manifest_checksum"] != bootstrap["desired_manifest_checksum"]
    ):
        raise _identity("WORKSPACE_IDENTITY_CONFLICT", "Staged Workspace identity is inconsistent")
    validate_registry(_read_json(root / CAPSULE_REGISTRY), workspace)
    if (root / ".reagent/installed-lock.json").exists():
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Bootstrap must not create an Installed Lock")


def _empty_registry(bootstrap: dict[str, Any], created_at: str) -> dict[str, Any]:
    payload = {
        "schema_version": REGISTRY_SCHEMA,
        "project_id": bootstrap["project_id"],
        "workspace_id": bootstrap["workspace_id"],
        "created_at": created_at,
        "entries": [],
    }
    return {**payload, "registry_checksum": canonical_hash(payload)}


def _workspace_agent() -> str:
    return """# ReAgent Project Workspace

This is a long-lived local Project Workspace. Cloud files describe desired
configuration only; they do not prove local installation or execution state.

- Treat `project.json` as immutable identity metadata.
- Each adopted Capsule is isolated below `capsules/` and follows its own
  `AGENT.md` and declared mutable roots.
- Never place credentials, database URLs, access tokens, or private keys in
  this Workspace.
- Do not write into another Capsule or outside this Workspace.
- Run `python reagent_local.py sync .` explicitly to pull reviewed, exact-pinned
  Capsules. Sync never executes downloaded code or deletes retired Capsules.
- Run `python reagent_local.py artifact refresh .` to verify producer bytes into
  `.reagent/artifact-index.json`, then use the explicit `artifact materialize`
  command for one checksum-bound consumer. Materialization copies bytes; it
  never creates shared writable links or silently selects the latest Artifact.
- `.reagent/installed-lock.json` is local installed-state metadata; cloud
  acknowledgement is not a backup of this Workspace.
- Cloud Artifact References are metadata, not stored Artifact bytes or a backup.
"""


def _legacy_instance_id(project_id: str) -> str:
    name = (
        f"legacy-workflow-instance/v1|project={project_id}|"
        "workflow=LITERATURE_SEARCH"
    )
    return "wfi-" + uuid.uuid5(LEGACY_NAMESPACE, name).hex


def _ensure_destination_parents(workspace: Path, parent: Path) -> None:
    _assert_within(workspace, parent)
    current = workspace
    for part in parent.relative_to(workspace).parts:
        current = current / part
        if current.exists() or current.is_symlink():
            if current.is_symlink() or not current.is_dir():
                raise _filesystem("UNSAFE_PACKAGE_PATH", "Capsule destination contains an unsafe path")
        else:
            current.mkdir(mode=0o700)


def _reject_symlink_chain(path: Path) -> None:
    absolute = path.absolute()
    existing: list[Path] = []
    current = absolute
    while True:
        if current.exists() or current.is_symlink():
            existing.append(current)
        if current == current.parent:
            break
        current = current.parent
    for candidate in reversed(existing):
        if candidate.is_symlink():
            system_aliases = {
                "/tmp": "/private/tmp",
                "/var": "/private/var",
            }
            expected = system_aliases.get(candidate.as_posix())
            if expected is not None and candidate.resolve().as_posix() == expected:
                continue
            raise _filesystem("UNSAFE_PACKAGE_PATH", "Symbolic-link path components are forbidden")


def _assert_within(root: Path, candidate: Path) -> None:
    root_resolved = root.resolve(strict=True)
    candidate_parent = candidate.parent.resolve(strict=False)
    try:
        candidate_parent.relative_to(root_resolved)
    except ValueError as error:
        raise _filesystem("UNSAFE_PACKAGE_PATH", "Filesystem path escapes its allowed root") from error


def _safe_package_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise _package_error("UNSAFE_PACKAGE_PATH", "Package path is unsafe")
    path = PurePosixPath(value)
    parts = value.split("/")
    if path.is_absolute() or any(part in {"", ".", ".."} for part in parts):
        raise _package_error("UNSAFE_PACKAGE_PATH", "Package path is unsafe")
    if re.match(r"^[A-Za-z]:", value):
        raise _package_error("UNSAFE_PACKAGE_PATH", "Absolute Package path is forbidden")
    if any(part == ".env" or part.startswith(".env.") for part in parts):
        raise _package_error("UNSAFE_PACKAGE_PATH", "Environment files are forbidden")
    if value.lower().endswith((".sqlite", ".sqlite3", ".db", ".pem", ".key")):
        raise _package_error("UNSAFE_PACKAGE_PATH", "Sensitive runtime file type is forbidden")
    return value


def _record_case_path(
    known: dict[str, str],
    value: str,
    *,
    allow_same: bool = False,
) -> None:
    folded = value.casefold()
    existing = known.get(folded)
    if existing is not None and (existing != value or not allow_same):
        raise _package_error("UNSAFE_PACKAGE_PATH", "Package paths collide after portable normalization")
    known[folded] = value


def _read_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Required Workspace metadata is missing")
    if path.stat(follow_symlinks=False).st_size > MAX_CONTROL_JSON_BYTES:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Workspace metadata exceeds size limits")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Workspace metadata is invalid") from error


def _read_package_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package manifest is missing")
    if path.stat(follow_symlinks=False).st_size > MAX_CONTROL_JSON_BYTES:
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package manifest exceeds size limits")
    try:
        return _object_package(json.loads(path.read_text(encoding="utf-8")), "Package manifest")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package manifest is invalid") from error


def _atomic_write_json(path: Path, value: Any) -> None:
    _atomic_write_bytes(path, (canonical_json(value) + "\n").encode("utf-8"), mode=0o600)


def _atomic_write_bytes(path: Path, content: bytes, *, mode: int) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary.unlink(missing_ok=True)
        raise


def _fsync_tree(root: Path) -> None:
    for base, directories, files in os.walk(root, topdown=False, followlinks=False):
        base_path = Path(base)
        for name in files:
            path = base_path / name
            if path.is_symlink():
                raise _filesystem("UNSAFE_PACKAGE_PATH", "Symbolic link appeared during publication")
            with path.open("rb") as handle:
                os.fsync(handle.fileno())
        for name in directories:
            _fsync_directory(base_path / name)
        _fsync_directory(base_path)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _directory_identity(path: Path) -> tuple[int, int]:
    value = path.stat(follow_symlinks=False)
    return value.st_dev, value.st_ino


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _reject_secrets(content: bytes) -> None:
    if any(pattern.search(content) for pattern in _SECRET_PATTERNS):
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package contains prohibited credential material")


def _reject_credentials(content: bytes) -> None:
    if any(pattern.search(content) for pattern in _CREDENTIAL_PATTERNS):
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Materialized Artifact contains prohibited credential material")


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", f"{name} must be an object")
    return value


def _object_package(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", f"{name} must be an object")
    return value


def _exact_fields(value: dict[str, Any], fields: set[str], name: str) -> None:
    if set(value) != fields:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", f"{name} fields are invalid")


def _match(value: Any, pattern: re.Pattern[str], name: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", f"{name} is invalid")
    return value


def _match_package(value: Any, pattern: re.Pattern[str], name: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise _package_error("LEGACY_PACKAGE_IDENTITY_MISMATCH", f"{name} is invalid")
    return value


def _checksum(value: Any, name: str) -> str:
    if not isinstance(value, str) or SHA256.fullmatch(value) is None:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", f"{name} is invalid")
    return value


def _checksum_package(value: Any, name: str) -> str:
    if not isinstance(value, str) or SHA256.fullmatch(value) is None:
        raise _package_error("LEGACY_PACKAGE_CHECKSUM_MISMATCH", f"{name} is invalid")
    return value


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", f"{name} must be positive")
    return value


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or len(value) > 35:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", f"{name} is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", f"{name} is invalid") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", f"{name} requires a timezone")
    return parsed


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Workspace clock must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _identity(code: str, message: str) -> WorkspaceCLIError:
    return WorkspaceCLIError(code, message, EXIT_IDENTITY)


def _package_error(code: str, message: str) -> WorkspaceCLIError:
    return WorkspaceCLIError(code, message, EXIT_VALIDATION)


def _filesystem(code: str, message: str) -> WorkspaceCLIError:
    return WorkspaceCLIError(code, message, EXIT_FILESYSTEM)


class HTTPWorkspaceSyncTransport:
    """Loopback-only JSON/ZIP transport with no persisted credential."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise WorkspaceCLIError(
                "WORKSPACE_SYNC_NOT_AVAILABLE",
                "Workspace sync requires a loopback ReAgent API URL",
                EXIT_CLOUD,
            )
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise WorkspaceCLIError(
                "WORKSPACE_SYNC_NOT_AVAILABLE",
                "Workspace sync API URL must not contain credentials or query data",
                EXIT_CLOUD,
            )
        self._base_url = base_url.rstrip("/")

    def create_plan(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._json_request(
            "POST", f"/projects/{project_id}/workspace/sync-plan", payload
        )

    def download(self, path: str, expected: dict[str, Any] | None = None) -> bytes:
        if not path.startswith("/projects/") or not path.endswith("/download"):
            raise WorkspaceCLIError(
                "CAPSULE_DOWNLOAD_FAILED", "Capsule acquisition path is invalid", EXIT_CLOUD
            )
        request = urllib.request.Request(self._base_url + path, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status != 200:
                    raise OSError("unexpected response status")
                if response.geturl() != self._base_url + path:
                    raise OSError("Capsule download redirect is forbidden")
                if expected is not None:
                    artifact = expected["artifact"]
                    path_parts = path.split("/")
                    expected_headers = {
                        "X-ReAgent-Project-ID": path_parts[2],
                        "X-ReAgent-Workflow-Instance-ID": expected["workflow_instance_id"],
                        "X-ReAgent-Capsule-ID": expected["capsule_id"],
                        "X-ReAgent-Capsule-Version": expected["capsule_version"],
                        "ETag": f'"{artifact["archive_checksum"]}"',
                    }
                    if any(response.headers.get(key) != value for key, value in expected_headers.items()):
                        raise OSError("Capsule download response identity mismatch")
                content = response.read(MAX_PACKAGE_BYTES + 1)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError) as error:
            raise WorkspaceCLIError(
                "CAPSULE_DOWNLOAD_FAILED", "Capsule download did not complete", EXIT_CLOUD
            ) from error
        if len(content) > MAX_PACKAGE_BYTES:
            raise _package_error("UNSAFE_CAPSULE_ARCHIVE", "Capsule archive exceeds size limits")
        return content

    def acknowledge(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._json_request(
            "POST", f"/projects/{project_id}/workspace/sync-ack", payload
        )

    def list_artifacts(
        self, project_id: str, *, offset: int = 0, limit: int = 100
    ) -> dict[str, Any]:
        query = urllib.parse.urlencode({"offset": offset, "limit": limit})
        return self._json_get(f"/projects/{project_id}/artifacts?{query}")

    def materialization_plan(
        self, project_id: str, consumer_workflow_instance_id: str
    ) -> dict[str, Any]:
        _match(
            consumer_workflow_instance_id,
            WORKFLOW_INSTANCE_ID,
            "consumer_workflow_instance_id",
        )
        return self._json_get(
            f"/projects/{project_id}/workflow-instances/"
            f"{consumer_workflow_instance_id}/artifact-materialization-plan"
        )

    def list_resources(
        self, project_id: str, *, offset: int = 0, limit: int = 100
    ) -> dict[str, Any]:
        query = urllib.parse.urlencode({"offset": offset, "limit": limit})
        return self._json_get(f"/projects/{project_id}/resources?{query}")

    def list_resource_bindings(
        self, project_id: str, workflow_instance_id: str
    ) -> dict[str, Any]:
        _match(workflow_instance_id, WORKFLOW_INSTANCE_ID, "workflow_instance_id")
        return self._json_get(
            f"/projects/{project_id}/workflow-instances/"
            f"{workflow_instance_id}/resource-bindings"
        )

    def literature_execution_mode(
        self, project_id: str, package_identity: dict[str, str]
    ) -> dict[str, Any]:
        """Fetch the server-authorized mode bound to one exact Package."""

        fields = {
            "package_id", "package_checksum", "workflow_id",
            "workflow_version", "workflow_checksum",
        }
        if set(package_identity) != fields:
            raise _identity(
                "LOCAL_CAPSULE_DRIFT", "Literature Package identity is incomplete"
            )
        query = urllib.parse.urlencode(package_identity)
        return self._json_get(
            f"/projects/{project_id}/local-sessions/execution-mode?{query}"
        )

    def grant_real_provider_consent(
        self,
        project_id: str,
        package_identity: dict[str, str],
        *,
        confirmation: str,
    ) -> dict[str, Any]:
        return self._json_request(
            "POST",
            f"/projects/{project_id}/local-sessions/real-provider-consent",
            {
                **package_identity,
                "disclosure_version": REAL_PROVIDER_DISCLOSURE_VERSION,
                "confirmation": confirmation,
            },
        )

    def workflow_instance_progress(
        self, project_id: str, workflow_instance_id: str
    ) -> dict[str, Any]:
        """Read one exact Instance history, including accepted predecessor identity."""

        _match(workflow_instance_id, WORKFLOW_INSTANCE_ID, "workflow_instance_id")
        offset = 0
        history: list[dict[str, Any]] = []
        first: dict[str, Any] | None = None
        while True:
            query = urllib.parse.urlencode({"offset": offset, "limit": 100})
            page = self._json_get(
                f"/projects/{project_id}/workflow-instances/"
                f"{workflow_instance_id}/progress?{query}"
            )
            if first is None:
                first = page
            items = page.get("history")
            if not isinstance(items, list) or not all(
                isinstance(item, dict) for item in items
            ):
                raise _identity(
                    "CLOUD_PROGRESS_INVALID", "Cloud Progress history is invalid"
                )
            history.extend(items)
            if not page.get("has_more_history"):
                break
            if not items or len(history) > MAX_FILES:
                raise _identity(
                    "CLOUD_PROGRESS_INVALID", "Cloud Progress pagination is invalid"
                )
            offset += len(items)
        assert first is not None
        return {**first, "history": history, "history_total": len(history)}

    def upload_progress_report(
        self,
        project_id: str,
        workflow_instance_id: str,
        manifest: dict[str, Any],
        report: dict[str, Any],
        envelope: dict[str, Any],
    ) -> dict[str, Any]:
        """Use one fresh exact-report upload-only session; never expose its token."""

        _match(workflow_instance_id, WORKFLOW_INSTANCE_ID, "workflow_instance_id")
        identity = {
            "package_id": manifest["package_id"],
            "package_checksum": manifest["package_checksum"],
            "workflow_id": manifest["workflow_id"],
            "workflow_version": manifest["workflow_version"],
            "workflow_checksum": manifest["workflow_checksum"],
        }
        session = self._json_request(
            "POST",
            f"/projects/{project_id}/local-sessions",
            {
                **identity,
                "mode": "UPLOAD_ONLY",
                "execution_round": report["execution_round"],
                "report_id": report["report_id"],
                "report_content_checksum": report["report_content_checksum"],
            },
        )
        if (
            session.get("mode") != "UPLOAD_ONLY"
            or not isinstance(session.get("session_id"), str)
            or not isinstance(session.get("session_token"), str)
        ):
            raise _identity(
                "CLOUD_PROGRESS_INVALID", "Upload-only session response is invalid"
            )
        session_id = urllib.parse.quote(session["session_id"], safe="")
        query = urllib.parse.urlencode({
            "workflow_id": manifest["workflow_id"],
            "workflow_version": manifest["workflow_version"],
            "workflow_checksum": manifest["workflow_checksum"],
        })
        try:
            return self._authenticated_json_request(
                "POST",
                f"/projects/{project_id}/local-sessions/{session_id}/"
                f"progress-reports?{query}",
                envelope,
                session["session_token"],
            )
        finally:
            identity_query = urllib.parse.urlencode(identity)
            self._authenticated_empty_request(
                "DELETE",
                f"/projects/{project_id}/local-sessions/{session_id}?{identity_query}",
                session["session_token"],
            )

    def _json_get(self, path: str) -> dict[str, Any]:
        request = urllib.request.Request(self._base_url + path, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status != 200 or response.geturl() != self._base_url + path:
                    raise OSError("unexpected Artifact metadata response")
                content = response.read(2_097_153)
        except urllib.error.HTTPError as error:
            try:
                body = json.loads(error.read(65_536).decode("utf-8"))
                code = body.get("error", {}).get("code", "ARTIFACT_REFERENCE_NOT_FOUND")
            except Exception:
                code = "ARTIFACT_REFERENCE_NOT_FOUND"
            raise WorkspaceCLIError(
                code, "Cloud rejected the Artifact metadata request", EXIT_CLOUD
            ) from error
        except (OSError, urllib.error.URLError) as error:
            raise WorkspaceCLIError(
                "WORKSPACE_SYNC_NOT_AVAILABLE",
                "Local ReAgent API is unavailable",
                EXIT_CLOUD,
            ) from error
        if len(content) > 2_097_152:
            raise WorkspaceCLIError(
                "ARTIFACT_INDEX_INVALID",
                "Artifact metadata response exceeds size limits",
                EXIT_CLOUD,
            )
        try:
            value = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise WorkspaceCLIError(
                "ARTIFACT_INDEX_INVALID",
                "Artifact metadata response is invalid",
                EXIT_CLOUD,
            ) from error
        return _object(value, "Artifact metadata response")

    def _json_request(
        self, method: str, path: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        data = (canonical_json(payload) + "\n").encode("utf-8")
        if len(data) > 1_048_576:
            raise WorkspaceCLIError(
                "WORKSPACE_SYNC_NOT_AVAILABLE", "Workspace sync request is too large", EXIT_CLOUD
            )
        request = urllib.request.Request(
            self._base_url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read(1_048_577)
        except urllib.error.HTTPError as error:
            try:
                body = json.loads(error.read(65_536).decode("utf-8"))
                code = body.get("error", {}).get("code", "WORKSPACE_SYNC_NOT_AVAILABLE")
            except Exception:
                code = "WORKSPACE_SYNC_NOT_AVAILABLE"
            exit_code = EXIT_CONCURRENCY if error.code == 409 else EXIT_CLOUD
            raise WorkspaceCLIError(code, "Cloud rejected the Workspace sync operation", exit_code) from error
        except (OSError, urllib.error.URLError) as error:
            raise WorkspaceCLIError(
                "WORKSPACE_SYNC_NOT_AVAILABLE", "Local ReAgent API is unavailable", EXIT_CLOUD
            ) from error
        if len(content) > 1_048_576:
            raise WorkspaceCLIError(
                "WORKSPACE_SYNC_NOT_AVAILABLE", "Workspace sync response is too large", EXIT_CLOUD
            )
        try:
            value = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise WorkspaceCLIError(
                "WORKSPACE_SYNC_NOT_AVAILABLE", "Workspace sync response is invalid", EXIT_CLOUD
            ) from error
        return _object(value, "Workspace sync response")

    def _authenticated_json_request(
        self, method: str, path: str, payload: dict[str, Any], token: str
    ) -> dict[str, Any]:
        data = (canonical_json(payload) + "\n").encode("utf-8")
        request = urllib.request.Request(
            self._base_url + path,
            data=data,
            method=method,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read(1_048_577)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError) as error:
            raise WorkspaceCLIError(
                "PROGRESS_UPLOAD_FAILED",
                "Cloud Progress upload did not complete",
                EXIT_CLOUD,
            ) from error
        if len(content) > 1_048_576:
            raise _identity("CLOUD_PROGRESS_INVALID", "Cloud Progress receipt is too large")
        try:
            return _object(json.loads(content.decode("utf-8")), "Cloud Progress receipt")
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise _identity(
                "CLOUD_PROGRESS_INVALID", "Cloud Progress receipt is invalid"
            ) from error

    def _authenticated_empty_request(
        self, method: str, path: str, token: str
    ) -> None:
        request = urllib.request.Request(
            self._base_url + path,
            method=method,
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response.read(1)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError):
            # Upload-only sessions are short-lived and report-scoped. Cleanup
            # failure never replaces an already known upload outcome.
            return


class _WorkspaceWriteLock:
    def __init__(self, workspace: Path) -> None:
        self.path = workspace / SYNC_LOCK
        self.handle = None

    def __enter__(self):
        if fcntl is None:
            raise _filesystem("WORKSPACE_BUSY", "OS Workspace locking is unavailable")
        _reject_symlink_chain(self.path.parent)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise _filesystem("WORKSPACE_BUSY", "Workspace sync lock path is unsafe")
        self.handle = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            self.handle.close()
            raise WorkspaceCLIError(
                "WORKSPACE_BUSY", "Another Workspace sync owns the write lock", EXIT_CONCURRENCY
            ) from error
        self.handle.seek(0)
        self.handle.truncate()
        self.handle.write(canonical_json({"schema_version": "reagent.workspace-write-lock/v0.1", "pid": os.getpid()}))
        self.handle.flush()
        os.fsync(self.handle.fileno())
        return self

    def __exit__(self, exc_type, exc, traceback):
        assert self.handle is not None
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()


def sync_workspace(
    *,
    workspace_root: str | Path,
    transport: Any,
    dry_run: bool = False,
    now: datetime | None = None,
) -> WorkspaceSyncResult:
    workspace, descriptor, cached_bootstrap = load_workspace(workspace_root)
    with _WorkspaceWriteLock(workspace):
        pending = _pending_acknowledgements(workspace, descriptor)
        if pending:
            lock = validate_installed_lock(_read_json(workspace / INSTALLED_LOCK), descriptor)
            try:
                receipt = _retry_pending_ack(workspace, descriptor, pending[0], transport)
            except WorkspaceCLIError as error:
                if error.code != "ACKNOWLEDGEMENT_STALE":
                    return _sync_result("ACK_PENDING", lock, "ACK_PENDING")
                path, envelope = pending[0]
                _atomic_write_json(path, {**envelope, "local_status": "ACKNOWLEDGED_STALE"})
            else:
                return _sync_result("ACKNOWLEDGED", lock, receipt["status"])

        lock = _load_or_migrate_lock(
            workspace, descriptor, cached_bootstrap, now=now or datetime.now(timezone.utc)
        )
        installed = [] if lock is None else [
            _installed_observation(item) for item in lock["installed_capsules"]
            if item["lifecycle"] == "ACTIVE"
        ]
        idempotency_key = str(uuid.uuid5(
            LEGACY_NAMESPACE,
            "workspace-sync/v1|"
            f"workspace={descriptor['workspace_id']}|"
            f"base={0 if lock is None else lock['manifest_revision']}|"
            f"lock={None if lock is None else lock['lock_checksum']}",
        ))
        plan = transport.create_plan(descriptor["project_id"], {
            "workspace_id": descriptor["workspace_id"],
            "installed_manifest_revision": 0 if lock is None else lock["manifest_revision"],
            "installed_lock_checksum": None if lock is None else lock["lock_checksum"],
            "installed_capsules": installed,
            "idempotency_key": idempotency_key,
            "dry_run": dry_run,
        })
        plan = validate_sync_plan(plan, descriptor)
        if dry_run:
            return WorkspaceSyncResult(
                status="PLAN_CREATED",
                project_id=descriptor["project_id"],
                workspace_id=descriptor["workspace_id"],
                manifest_revision=plan["target_manifest_revision"],
                installed_capsules=0 if lock is None else len(lock["installed_capsules"]),
                retained_capsules=0 if lock is None else sum(item["lifecycle"] == "RETAINED_NOT_DESIRED" for item in lock["installed_capsules"]),
                acknowledgement_status="NOT_SENT",
                lock_checksum=None if lock is None else lock["lock_checksum"],
            )
        return _execute_sync_plan(
            workspace=workspace,
            descriptor=descriptor,
            cached_bootstrap=cached_bootstrap,
            plan=plan,
            prior_lock=lock,
            transport=transport,
            now=now or datetime.now(timezone.utc),
        )


def validate_sync_plan(document: Any, workspace: dict[str, Any]) -> dict[str, Any]:
    value = _object(document, "Workspace sync plan")
    fields = {
        "schema_version", "installation_id", "project_id", "workspace_id",
        "base_manifest_revision", "target_manifest_revision", "target_manifest_checksum",
        "installed_lock_checksum", "plan_checksum", "state", "actions",
        "created_at", "expires_at",
    }
    _exact_fields(value, fields, "Workspace sync plan")
    if value["schema_version"] != SYNC_PLAN_SCHEMA:
        raise _identity("WORKSPACE_SCHEMA_UNSUPPORTED", "Workspace sync plan schema is unsupported")
    if value["project_id"] != workspace["project_id"] or value["workspace_id"] != workspace["workspace_id"]:
        raise _identity("WORKSPACE_IDENTITY_CONFLICT", "Workspace sync plan identity mismatch")
    _checksum(value["target_manifest_checksum"], "target_manifest_checksum")
    if value["installed_lock_checksum"] is not None:
        _checksum(value["installed_lock_checksum"], "installed_lock_checksum")
    payload = dict(value)
    checksum = payload.pop("plan_checksum")
    _checksum(checksum, "plan_checksum")
    if canonical_hash(payload) != checksum:
        raise _identity("SYNC_MANIFEST_CONFLICT", "Workspace sync plan checksum is invalid")
    actions = value["actions"]
    if not isinstance(actions, list) or len(actions) > 100:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Workspace sync actions are invalid")
    previous = ""
    for expected_sequence, action in enumerate(actions, 1):
        item = _object(action, "Workspace sync action")
        required = {
            "sequence", "action_type", "workflow_instance_id",
            "workflow_definition_id", "workflow_definition_version",
            "capsule_id", "capsule_version", "capsule_definition_checksum",
            "trust_classification", "destination_relative_path", "artifact",
        }
        if set(item) != required:
            raise _identity("SYNC_MANIFEST_CONFLICT", "Workspace sync action fields are invalid")
        if item.get("sequence") != expected_sequence:
            raise _identity("SYNC_MANIFEST_CONFLICT", "Workspace sync action ordering is invalid")
        instance_id = item.get("workflow_instance_id")
        _match(instance_id, WORKFLOW_INSTANCE_ID, "workflow_instance_id")
        if instance_id < previous:
            raise _identity("SYNC_MANIFEST_CONFLICT", "Workspace sync actions are not deterministic")
        previous = instance_id
        if item.get("action_type") not in {
            "NOOP", "INSTALL_CAPSULE", "CONFLICT", "UNAVAILABLE", "RETAINED_NOT_DESIRED"
        }:
            raise _identity("SYNC_MANIFEST_CONFLICT", "Workspace sync action type is invalid")
        pin = (
            item["workflow_definition_id"],
            item["workflow_definition_version"],
            item["capsule_version"],
        )
        if pin not in SUPPORTED_CAPSULE_PINS or item["trust_classification"] != TRUST_CLASSIFICATION:
            raise _identity("CAPSULE_TRUST_REJECTED", "Workspace sync Capsule pin or trust is unsupported")
        _match(item["capsule_id"], CAPSULE_ID, "capsule_id")
        expected_path = (
            f"capsules/{item['workflow_definition_id']}/"
            f"{item['workflow_instance_id']}/{item['capsule_version']}"
        )
        if item.get("destination_relative_path") != expected_path:
            raise _identity("CAPSULE_IDENTITY_MISMATCH", "Capsule destination identity is invalid")
        _safe_package_path(item["destination_relative_path"])
        _checksum(item.get("capsule_definition_checksum"), "capsule_definition_checksum")
        if item.get("action_type") == "INSTALL_CAPSULE":
            _validate_acquisition(item.get("artifact"), value, item)
    return value


def validate_installed_lock(document: Any, workspace: dict[str, Any]) -> dict[str, Any]:
    try:
        return _validate_installed_lock(document, workspace)
    except WorkspaceCLIError as error:
        if error.code in {"INSTALLED_LOCK_INVALID", "INSTALLED_LOCK_CONFLICT"}:
            raise
        raise _identity("INSTALLED_LOCK_INVALID", "Installed Workspace Lock is invalid") from error


def _validate_installed_lock(document: Any, workspace: dict[str, Any]) -> dict[str, Any]:
    value = _object(document, "Installed Workspace Lock")
    fields = {
        "schema_version", "project_id", "workspace_id", "manifest_revision",
        "manifest_checksum", "lock_checksum", "installed_capsules",
        "installed_skills", "materialized_artifacts", "resolved_resources", "written_at",
    }
    _exact_fields(value, fields, "Installed Workspace Lock")
    if value["schema_version"] != INSTALLED_LOCK_SCHEMA:
        raise _identity("INSTALLED_LOCK_INVALID", "Installed Workspace Lock schema is unsupported")
    if value["project_id"] != workspace["project_id"] or value["workspace_id"] != workspace["workspace_id"]:
        raise _identity("INSTALLED_LOCK_CONFLICT", "Installed Workspace Lock identity mismatch")
    _positive_int(value["manifest_revision"], "manifest_revision")
    _checksum(value["manifest_checksum"], "manifest_checksum")
    if any(value[field] != [] for field in ("installed_skills", "materialized_artifacts", "resolved_resources")):
        raise _identity("INSTALLED_LOCK_INVALID", "Unsupported Installed Lock content is present")
    entries = value["installed_capsules"]
    if not isinstance(entries, list) or len(entries) > 100:
        raise _identity("INSTALLED_LOCK_INVALID", "Installed Capsule list is invalid")
    ids = []
    for entry in entries:
        item = _object(entry, "Installed Capsule")
        required = {
            "workflow_instance_id", "workflow_definition_id", "workflow_definition_version",
            "capsule_id", "capsule_version", "capsule_definition_checksum",
            "package_id", "package_checksum", "manifest_checksum", "immutable_contract_checksum",
            "relative_path", "lifecycle", "installation_source", "verification_status",
        }
        _exact_fields(item, required, "Installed Capsule")
        _match(item["workflow_instance_id"], WORKFLOW_INSTANCE_ID, "workflow_instance_id")
        _safe_package_path(item["relative_path"])
        for field in ("capsule_definition_checksum", "package_checksum", "manifest_checksum", "immutable_contract_checksum"):
            _checksum(item[field], field)
        if item["lifecycle"] not in {"ACTIVE", "RETAINED_NOT_DESIRED"}:
            raise _identity("INSTALLED_LOCK_INVALID", "Installed Capsule lifecycle is invalid")
        if item["verification_status"] != "VERIFIED":
            raise _identity("INSTALLED_LOCK_INVALID", "Installed Capsule verification status is invalid")
        ids.append(item["workflow_instance_id"])
    if ids != sorted(set(ids)):
        raise _identity("INSTALLED_LOCK_INVALID", "Installed Capsule ordering is invalid")
    _timestamp(value["written_at"], "written_at")
    payload = dict(value)
    checksum = payload.pop("lock_checksum")
    _checksum(checksum, "lock_checksum")
    if canonical_hash(payload) != checksum:
        raise _identity("INSTALLED_LOCK_INVALID", "Installed Workspace Lock checksum is invalid")
    return value


def _load_or_migrate_lock(workspace, descriptor, bootstrap, *, now):
    path = workspace / INSTALLED_LOCK
    if path.exists() or path.is_symlink():
        if path.is_symlink():
            raise _identity("INSTALLED_LOCK_INVALID", "Installed Workspace Lock path is unsafe")
        lock = validate_installed_lock(_read_json(path), descriptor)
        _verify_locked_capsules(workspace, lock, bootstrap)
        return lock
    registry = validate_registry(_read_json(workspace / CAPSULE_REGISTRY), descriptor)
    if not registry["entries"]:
        return None
    entries = []
    for item in registry["entries"]:
        destination = workspace / item["capsule_relative_path"]
        _assert_within(workspace, destination)
        migration_bootstrap = _bootstrap_for_registry_entry(bootstrap, item)
        manifest, _ = _validate_legacy_package(
            destination,
            migration_bootstrap,
            expected_instance_id=item["workflow_instance_id"],
        )
        immutable_checksum = _immutable_contract_checksum(destination, manifest)
        if (
            manifest["package_id"] != item["package_id"]
            or manifest["package_checksum"] != item["package_checksum"]
            or manifest["manifest_checksum"] != item["manifest_checksum"]
        ):
            raise _identity("LOCAL_CAPSULE_DRIFT", "B3 Capsule registry conflicts with local content")
        entries.append(_lock_entry_from_registry(item, immutable_checksum))
    lock = _build_lock(
        descriptor=descriptor,
        manifest_revision=bootstrap["bootstrap_manifest_revision"],
        manifest_checksum=bootstrap["desired_manifest_checksum"],
        entries=entries,
        written_at=_utc_text(now),
    )
    _atomic_write_json(path, lock)
    validate_installed_lock(_read_json(path), descriptor)
    return lock


def _bootstrap_for_registry_entry(bootstrap, item):
    return {
        **bootstrap,
        "workflow_capsules": [{
            "workflow_instance_id": item["workflow_instance_id"],
            "workflow_definition_id": item["workflow_definition_id"],
            "workflow_definition_version": item["workflow_definition_version"],
            "capsule_id": item["capsule_id"],
            "capsule_version": item["capsule_version"],
            "capsule_definition_checksum": item["capsule_definition_checksum"],
            "desired_state": "ACTIVE",
            "legacy_package_compatible": True,
            "package_schema_version": PACKAGE_SCHEMA,
            "package_template_id": PACKAGE_TEMPLATE_ID,
            "trust_classification": TRUST_CLASSIFICATION,
            "legacy_package": {
                "package_id": item["package_id"],
                "package_schema_version": PACKAGE_SCHEMA,
                "package_checksum": item["package_checksum"],
                "manifest_checksum": item["manifest_checksum"],
                "zip_checksum": "sha256:" + "0" * 64,
                "download_path": (
                    f"/projects/{bootstrap['project_id']}/packages/"
                    f"{item['package_id']}/download"
                ),
            },
        }],
    }


def _execute_sync_plan(*, workspace, descriptor, cached_bootstrap, plan, prior_lock, transport, now):
    if (
        plan["state"] == "NO_CHANGE"
        and prior_lock is not None
        and _has_acknowledged_lock(workspace, descriptor, prior_lock)
    ):
        return _sync_result("NO_CHANGE", prior_lock, "ACKNOWLEDGED")
    journal = {
        "schema_version": "reagent.workspace-sync-transaction/v0.1",
        "installation_id": plan["installation_id"],
        "project_id": descriptor["project_id"],
        "workspace_id": descriptor["workspace_id"],
        "manifest_revision": plan["target_manifest_revision"],
        "manifest_checksum": plan["target_manifest_checksum"],
        "plan_checksum": plan["plan_checksum"],
        "state": "PLAN_CREATED",
        "completed_instances": [],
    }
    _write_journal(workspace, journal)
    entries = {
        item["workflow_instance_id"]: dict(item)
        for item in ([] if prior_lock is None else prior_lock["installed_capsules"])
    }
    for action in plan["actions"]:
        action_type = action["action_type"]
        instance_id = action["workflow_instance_id"]
        if action_type == "CONFLICT":
            raise _filesystem("CAPSULE_INSTALLATION_CONFLICT", "Installed Capsule pin conflicts with Desired Manifest")
        if action_type == "UNAVAILABLE":
            raise WorkspaceCLIError("CAPSULE_ARTIFACT_UNAVAILABLE", "Desired Capsule artifact is unavailable", EXIT_CLOUD)
        if action_type == "RETAINED_NOT_DESIRED":
            if instance_id in entries:
                entries[instance_id]["lifecycle"] = "RETAINED_NOT_DESIRED"
            continue
        if action_type == "NOOP":
            if instance_id in entries:
                entries[instance_id]["lifecycle"] = "ACTIVE"
            continue
        entry = _install_action(workspace, descriptor, plan, action, transport)
        entries[instance_id] = entry
        journal["state"] = "INSTALLED"
        journal["completed_instances"] = sorted(set(journal["completed_instances"] + [instance_id]))
        _write_journal(workspace, journal)
    for instance_id, entry in entries.items():
        if not any(action["workflow_instance_id"] == instance_id and action["action_type"] in {"NOOP", "INSTALL_CAPSULE"} for action in plan["actions"]):
            entry["lifecycle"] = "RETAINED_NOT_DESIRED"
    lock = _build_lock(
        descriptor=descriptor,
        manifest_revision=plan["target_manifest_revision"],
        manifest_checksum=plan["target_manifest_checksum"],
        entries=list(entries.values()),
        written_at=_utc_text(now),
    )
    _atomic_write_json(workspace / INSTALLED_LOCK, lock)
    lock = validate_installed_lock(_read_json(workspace / INSTALLED_LOCK), descriptor)
    journal["state"] = "LOCK_WRITTEN"
    _write_journal(workspace, journal)
    ack = _ack_envelope(plan, lock, descriptor, now)
    ack_path = workspace / ACKNOWLEDGEMENTS_ROOT / f"{plan['installation_id']}.json"
    _atomic_write_json(ack_path, {**ack, "local_status": "ACK_PENDING"})
    _write_install_receipt(workspace, plan, lock, now)
    try:
        receipt = transport.acknowledge(descriptor["project_id"], ack)
    except WorkspaceCLIError:
        journal["state"] = "ACK_PENDING"
        _write_journal(workspace, journal)
        return _sync_result("ACK_PENDING", lock, "ACK_PENDING")
    _store_ack_receipt(ack_path, ack, receipt)
    journal["state"] = "ACKNOWLEDGED"
    _write_journal(workspace, journal)
    return _sync_result("NO_CHANGE" if plan["state"] == "NO_CHANGE" else "SYNCED", lock, "ACKNOWLEDGED")


def _install_action(workspace, descriptor, plan, action, transport):
    artifact = action["artifact"]
    content = transport.download(artifact["download_path"], action)
    if sha256_bytes(content) != artifact["archive_checksum"]:
        raise _package_error("CAPSULE_CHECKSUM_MISMATCH", "Downloaded Capsule archive checksum mismatch")
    destination = workspace / action["destination_relative_path"]
    _ensure_destination_parents(workspace, destination.parent)
    if destination.exists() or destination.is_symlink():
        if destination.is_symlink() or not destination.is_dir():
            raise _filesystem("CAPSULE_INSTALLATION_CONFLICT", "Capsule destination has an unsafe type")
        bootstrap = _bootstrap_for_action(descriptor, plan, action)
        manifest, _ = _validate_legacy_package(
            destination,
            bootstrap,
            expected_instance_id=action["workflow_instance_id"],
            require_legacy_compatibility=False,
        )
        return _lock_entry(
            action,
            artifact,
            manifest,
            _immutable_contract_checksum(destination, manifest),
            "CLOUD_ACQUISITION",
        )
    parent_identity = _directory_identity(destination.parent)
    staging = Path(tempfile.mkdtemp(prefix=".reagent-sync-", dir=destination.parent))
    archive = staging.parent / f".{plan['installation_id']}.{action['workflow_instance_id']}.zip"
    published = False
    try:
        _atomic_write_bytes(archive, content, mode=0o600)
        extracted_root = _extract_archive_safely(archive, staging)
        bootstrap = _bootstrap_for_action(descriptor, plan, action)
        manifest, _ = _validate_legacy_package(
            extracted_root,
            bootstrap,
            expected_instance_id=action["workflow_instance_id"],
            require_legacy_compatibility=False,
        )
        immutable_checksum = _immutable_contract_checksum(extracted_root, manifest)
        if extracted_root != staging:
            replacement = staging.parent / f".{staging.name}.content"
            os.replace(extracted_root, replacement)
            shutil.rmtree(staging, ignore_errors=True)
            staging = replacement
        _fsync_tree(staging)
        _reject_symlink_chain(destination.parent)
        if _directory_identity(destination.parent) != parent_identity:
            raise _filesystem("UNSAFE_CAPSULE_ARCHIVE", "Capsule target changed during installation")
        os.replace(staging, destination)
        published = True
        _fsync_directory(destination.parent)
        verified_manifest, _ = _validate_legacy_package(
            destination,
            bootstrap,
            expected_instance_id=action["workflow_instance_id"],
            require_legacy_compatibility=False,
        )
        if (
            _immutable_contract_checksum(destination, verified_manifest) != immutable_checksum
            or verified_manifest["package_checksum"] != manifest["package_checksum"]
        ):
            raise _filesystem("CAPSULE_INSTALLATION_FAILED", "Published Capsule failed verification")
        return _lock_entry(action, artifact, manifest, immutable_checksum, "CLOUD_ACQUISITION")
    finally:
        archive.unlink(missing_ok=True)
        if not published and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def _validate_acquisition(raw, plan, action):
    artifact = _object(raw, "Capsule acquisition")
    required = {
        "capsule_artifact_id", "package_id", "package_schema_version", "package_checksum",
        "manifest_checksum", "archive_checksum", "archive_size_bytes", "file_count",
        "media_type", "download_path",
    }
    _exact_fields(artifact, required, "Capsule acquisition")
    for field in ("package_checksum", "manifest_checksum", "archive_checksum"):
        _checksum(artifact[field], field)
    if artifact["package_schema_version"] != PACKAGE_SCHEMA:
        raise _identity("CAPSULE_VERSION_MISMATCH", "Capsule Package schema is unsupported")
    if (
        isinstance(artifact["archive_size_bytes"], bool)
        or not isinstance(artifact["archive_size_bytes"], int)
        or not 0 <= artifact["archive_size_bytes"] <= MAX_PACKAGE_BYTES
        or isinstance(artifact["file_count"], bool)
        or not isinstance(artifact["file_count"], int)
        or not 1 <= artifact["file_count"] <= MAX_FILES
    ):
        raise _identity("CAPSULE_ARTIFACT_UNAVAILABLE", "Capsule artifact bounds are invalid")
    if artifact["media_type"] != "application/zip":
        raise _identity("CAPSULE_ARTIFACT_UNAVAILABLE", "Capsule media type is unsupported")
    prefix = (
        f"/projects/{plan['project_id']}/workflow-instances/"
        f"{action['workflow_instance_id']}/capsule-artifacts/"
    )
    if not artifact["download_path"].startswith(prefix) or not artifact["download_path"].endswith("/download"):
        raise _identity("CAPSULE_IDENTITY_MISMATCH", "Capsule download identity is invalid")


def _bootstrap_for_action(descriptor, plan, action):
    artifact = action["artifact"]
    template_id, legacy_compatible = SUPPORTED_CAPSULE_PINS[
        (
            action["workflow_definition_id"],
            action["workflow_definition_version"],
            action["capsule_version"],
        )
    ]
    capsule = {
        "workflow_instance_id": action["workflow_instance_id"],
        "workflow_definition_id": action["workflow_definition_id"],
        "workflow_definition_version": action["workflow_definition_version"],
        "capsule_id": action["capsule_id"],
        "capsule_version": action["capsule_version"],
        "capsule_definition_checksum": action["capsule_definition_checksum"],
        "desired_state": "ACTIVE",
        "legacy_package_compatible": legacy_compatible,
        "package_schema_version": artifact["package_schema_version"],
        "package_template_id": template_id,
        "trust_classification": action["trust_classification"],
        "legacy_package": {
            "package_id": artifact["package_id"],
            "package_schema_version": artifact["package_schema_version"],
            "package_checksum": artifact["package_checksum"],
            "manifest_checksum": artifact["manifest_checksum"],
            "zip_checksum": artifact["archive_checksum"],
            "download_path": artifact["download_path"],
        },
    }
    return {
        "project_id": descriptor["project_id"],
        "workspace_id": descriptor["workspace_id"],
        "bootstrap_manifest_revision": plan["target_manifest_revision"],
        "desired_manifest_checksum": plan["target_manifest_checksum"],
        "workflow_capsules": [capsule],
    }


def _build_lock(*, descriptor, manifest_revision, manifest_checksum, entries, written_at):
    ordered = sorted(entries, key=lambda item: item["workflow_instance_id"])
    payload = {
        "schema_version": INSTALLED_LOCK_SCHEMA,
        "project_id": descriptor["project_id"],
        "workspace_id": descriptor["workspace_id"],
        "manifest_revision": manifest_revision,
        "manifest_checksum": manifest_checksum,
        "installed_capsules": ordered,
        "installed_skills": [],
        "materialized_artifacts": [],
        "resolved_resources": [],
        "written_at": written_at,
    }
    return {**payload, "lock_checksum": canonical_hash(payload)}


def _lock_entry_from_registry(item, immutable_checksum):
    return {
        "workflow_instance_id": item["workflow_instance_id"],
        "workflow_definition_id": item["workflow_definition_id"],
        "workflow_definition_version": item["workflow_definition_version"],
        "capsule_id": item["capsule_id"],
        "capsule_version": item["capsule_version"],
        "capsule_definition_checksum": item["capsule_definition_checksum"],
        "package_id": item["package_id"],
        "package_checksum": item["package_checksum"],
        "manifest_checksum": item["manifest_checksum"],
        "immutable_contract_checksum": immutable_checksum,
        "relative_path": item["capsule_relative_path"],
        "lifecycle": "ACTIVE",
        "installation_source": "B3_LEGACY_ADOPTION",
        "verification_status": "VERIFIED",
    }


def _lock_entry(action, artifact, manifest, immutable_checksum, source):
    return {
        "workflow_instance_id": action["workflow_instance_id"],
        "workflow_definition_id": action["workflow_definition_id"],
        "workflow_definition_version": action["workflow_definition_version"],
        "capsule_id": action["capsule_id"],
        "capsule_version": action["capsule_version"],
        "capsule_definition_checksum": action["capsule_definition_checksum"],
        "package_id": manifest["package_id"],
        "package_checksum": artifact["package_checksum"],
        "manifest_checksum": artifact["manifest_checksum"],
        "immutable_contract_checksum": immutable_checksum,
        "relative_path": action["destination_relative_path"],
        "lifecycle": "ACTIVE",
        "installation_source": source,
        "verification_status": "VERIFIED",
    }


def _installed_observation(item):
    return {key: item[key] for key in (
        "workflow_instance_id", "workflow_definition_id", "workflow_definition_version",
        "capsule_id", "capsule_version", "capsule_definition_checksum",
        "package_checksum", "relative_path",
    )}


def _verify_locked_capsules(workspace, lock, bootstrap):
    for item in lock["installed_capsules"]:
        destination = workspace / item["relative_path"]
        _assert_within(workspace, destination)
        pin = (
            item["workflow_definition_id"],
            item["workflow_definition_version"],
            item["capsule_version"],
        )
        if pin not in SUPPORTED_CAPSULE_PINS:
            raise _identity("CAPSULE_TRUST_REJECTED", "Installed Capsule pin is unsupported")
        template_id, legacy_compatible = SUPPORTED_CAPSULE_PINS[pin]
        synthetic = {
            **bootstrap,
            "workflow_capsules": [{
                "workflow_instance_id": item["workflow_instance_id"],
                "workflow_definition_id": item["workflow_definition_id"],
                "workflow_definition_version": item["workflow_definition_version"],
                "capsule_id": item["capsule_id"],
                "capsule_version": item["capsule_version"],
                "capsule_definition_checksum": item["capsule_definition_checksum"],
                "desired_state": "ACTIVE",
                "legacy_package_compatible": legacy_compatible,
                "package_schema_version": PACKAGE_SCHEMA,
                "package_template_id": template_id,
                "trust_classification": TRUST_CLASSIFICATION,
                "legacy_package": {
                    "package_id": item["package_id"],
                    "package_schema_version": PACKAGE_SCHEMA,
                    "package_checksum": item["package_checksum"],
                    "manifest_checksum": item["manifest_checksum"],
                    "zip_checksum": "sha256:" + "0" * 64,
                    "download_path": f"/projects/{lock['project_id']}/packages/{item['package_id']}/download",
                },
            }],
        }
        try:
            manifest, _ = _validate_legacy_package(
                destination,
                synthetic,
                expected_instance_id=item["workflow_instance_id"],
                require_legacy_compatibility=False,
            )
        except WorkspaceCLIError as error:
            if pin[0] in {
                "writing-local-experimental",
                "review-local-experimental",
                "reproduction-experiment-local-experimental",
            } and pin[1:] in {
                ("0.2.0", "0.2.0"),
                ("0.2.0", "0.3.0"),
                ("0.2.0", "0.4.0"),
                ("0.3.0", "0.3.0"),
                ("0.3.0", "0.4.0"),
                ("0.3.0", "0.5.0"),
            }:
                raise _identity(
                    "LOCAL_CAPSULE_DRIFT",
                    "A required built-in Skill is missing or changed. "
                    "Restore the verified Capsule, then run sync.",
                ) from error
            raise
        if (
            manifest["package_checksum"] != item["package_checksum"]
            or _immutable_contract_checksum(destination, manifest)
            != item["immutable_contract_checksum"]
        ):
            raise _identity("LOCAL_CAPSULE_DRIFT", "Installed Capsule immutable or local state drift was detected")


def _ack_envelope(plan, lock, descriptor, now):
    active = [
        {key: item[key] for key in (
            "workflow_instance_id", "workflow_definition_id", "workflow_definition_version",
            "capsule_id", "capsule_version", "capsule_definition_checksum",
        )}
        for item in lock["installed_capsules"] if item["lifecycle"] == "ACTIVE"
    ]
    return {
        "schema_version": SYNC_ACK_SCHEMA,
        "installation_id": plan["installation_id"],
        "project_id": descriptor["project_id"],
        "workspace_id": descriptor["workspace_id"],
        "manifest_revision": lock["manifest_revision"],
        "manifest_checksum": lock["manifest_checksum"],
        "plan_checksum": plan["plan_checksum"],
        "installed_lock_schema": INSTALLED_LOCK_SCHEMA,
        "installed_lock_checksum": lock["lock_checksum"],
        "idempotency_key": str(uuid.uuid5(LEGACY_NAMESPACE, f"workspace-sync-ack/v1|installation={plan['installation_id']}")),
        "installed_capsules": active,
        "installed_at": _utc_text(now),
    }


def _pending_acknowledgements(workspace, descriptor):
    root = workspace / ACKNOWLEDGEMENTS_ROOT
    if not root.exists():
        return []
    if root.is_symlink() or not root.is_dir():
        raise _identity("INSTALLED_LOCK_INVALID", "Acknowledgement path is unsafe")
    pending = []
    for path in sorted(root.glob("*.json")):
        if path.is_symlink():
            raise _identity("INSTALLED_LOCK_INVALID", "Acknowledgement receipt path is unsafe")
        value = _read_json(path)
        if value.get("local_status") == "ACK_PENDING":
            if value.get("project_id") != descriptor["project_id"] or value.get("workspace_id") != descriptor["workspace_id"]:
                raise _identity("INSTALLED_LOCK_CONFLICT", "Acknowledgement identity mismatch")
            pending.append((path, value))
    return pending


def _has_acknowledged_lock(workspace, descriptor, lock):
    root = workspace / ACKNOWLEDGEMENTS_ROOT
    if not root.exists():
        return False
    if root.is_symlink() or not root.is_dir():
        raise _identity("INSTALLED_LOCK_INVALID", "Acknowledgement path is unsafe")
    for path in sorted(root.glob("*.json")):
        if path.is_symlink():
            raise _identity("INSTALLED_LOCK_INVALID", "Acknowledgement receipt path is unsafe")
        value = _read_json(path)
        if (
            value.get("local_status") == "ACKNOWLEDGED"
            and value.get("project_id") == descriptor["project_id"]
            and value.get("workspace_id") == descriptor["workspace_id"]
            and value.get("manifest_revision") == lock["manifest_revision"]
            and value.get("installed_lock_checksum") == lock["lock_checksum"]
        ):
            return True
    return False


def _retry_pending_ack(workspace, descriptor, pending, transport):
    path, value = pending
    payload = dict(value)
    payload.pop("local_status", None)
    receipt = transport.acknowledge(descriptor["project_id"], payload)
    _store_ack_receipt(path, payload, receipt)
    return receipt


def _store_ack_receipt(path, envelope, receipt):
    if receipt.get("schema_version") != SYNC_ACK_RECEIPT_SCHEMA or receipt.get("installation_id") != envelope["installation_id"]:
        raise WorkspaceCLIError("ACKNOWLEDGEMENT_REJECTED", "Cloud acknowledgement receipt is invalid", EXIT_CLOUD)
    _atomic_write_json(path, {**envelope, "local_status": "ACKNOWLEDGED", "cloud_receipt": receipt})


def _write_journal(workspace, journal):
    payload = dict(journal)
    payload["journal_checksum"] = canonical_hash(payload)
    _atomic_write_json(workspace / SYNC_JOURNAL, payload)


def _write_install_receipt(workspace, plan, lock, now):
    payload = {
        "schema_version": "reagent.workspace-installation-receipt/v0.1",
        "installation_id": plan["installation_id"],
        "project_id": lock["project_id"],
        "workspace_id": lock["workspace_id"],
        "manifest_revision": lock["manifest_revision"],
        "manifest_checksum": lock["manifest_checksum"],
        "plan_checksum": plan["plan_checksum"],
        "installed_lock_checksum": lock["lock_checksum"],
        "installed_at": _utc_text(now),
    }
    payload["receipt_checksum"] = canonical_hash(payload)
    _atomic_write_json(workspace / INSTALL_RECEIPTS_ROOT / f"{plan['installation_id']}.json", payload)


def _sync_result(status, lock, ack_status):
    return WorkspaceSyncResult(
        status=status,
        project_id=lock["project_id"],
        workspace_id=lock["workspace_id"],
        manifest_revision=lock["manifest_revision"],
        installed_capsules=sum(item["lifecycle"] == "ACTIVE" for item in lock["installed_capsules"]),
        retained_capsules=sum(item["lifecycle"] == "RETAINED_NOT_DESIRED" for item in lock["installed_capsules"]),
        acknowledgement_status=ack_status,
        lock_checksum=lock["lock_checksum"],
    )


def validate_artifact_index(
    document: Any, workspace: dict[str, Any]
) -> dict[str, Any]:
    try:
        return _validate_artifact_index(document, workspace)
    except WorkspaceCLIError as error:
        if error.code.startswith("ARTIFACT_INDEX_"):
            raise
        raise WorkspaceCLIError(
            "ARTIFACT_INDEX_INVALID",
            "Workspace Artifact Index is invalid",
            EXIT_VALIDATION,
        ) from error


def _read_artifact_index(
    path: Path, workspace: dict[str, Any]
) -> dict[str, Any]:
    try:
        return validate_artifact_index(_read_json(path), workspace)
    except WorkspaceCLIError as error:
        if error.code.startswith("ARTIFACT_INDEX_"):
            raise
        raise WorkspaceCLIError(
            "ARTIFACT_INDEX_INVALID",
            "Workspace Artifact Index cannot be read safely",
            EXIT_VALIDATION,
        ) from error


def _validate_artifact_index(
    document: Any, workspace: dict[str, Any]
) -> dict[str, Any]:
    value = _object(document, "Workspace Artifact Index")
    fields = {
        "schema_version", "project_id", "workspace_id", "artifacts",
        "updated_at", "index_checksum",
    }
    _exact_fields(value, fields, "Workspace Artifact Index")
    if value["schema_version"] != ARTIFACT_INDEX_SCHEMA:
        raise _identity("ARTIFACT_INDEX_INVALID", "Artifact Index schema is unsupported")
    if (
        value["project_id"] != workspace["project_id"]
        or value["workspace_id"] != workspace["workspace_id"]
    ):
        raise _identity("ARTIFACT_INDEX_CONFLICT", "Artifact Index identity mismatch")
    artifacts = value["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) > 10_000:
        raise _identity("ARTIFACT_INDEX_INVALID", "Artifact Index entries are invalid")
    identities: list[str] = []
    paths: dict[str, str] = {}
    for raw in artifacts:
        item = _object(raw, "Artifact Index entry")
        required = {
            "artifact_id", "artifact_type", "artifact_schema_version",
            "producer_workflow_instance_id", "producer_capsule_version",
            "producer_relative_path", "content_checksum", "size_bytes",
            "verification_status", "last_verified_at", "local_relative_path",
        }
        _exact_fields(item, required, "Artifact Index entry")
        _match(item["artifact_id"], ARTIFACT_ID, "artifact_id")
        _match(
            item["producer_workflow_instance_id"],
            WORKFLOW_INSTANCE_ID,
            "producer_workflow_instance_id",
        )
        _match(item["producer_capsule_version"], SEMVER, "producer_capsule_version")
        _match(
            item["artifact_type"],
            re.compile(r"^[a-z][a-z0-9._-]{1,139}(?:/v[0-9]+(?:\.[0-9]+)?)?$"),
            "artifact_type",
        )
        if (
            not isinstance(item["artifact_schema_version"], str)
            or not re.fullmatch(
                r"(?:reagent\.artifact\.[a-z][a-z0-9._-]*/v[0-9]+\.[0-9]+|"
                r"[a-z][a-z0-9._-]{1,139}/v[0-9]+(?:\.[0-9]+)?)",
                item["artifact_schema_version"],
            )
        ):
            raise _identity("ARTIFACT_INDEX_INVALID", "Artifact schema identity is invalid")
        producer_path = _safe_artifact_path(item["producer_relative_path"], root="outputs")
        local_path = _safe_artifact_path(item["local_relative_path"])
        _checksum(item["content_checksum"], "content_checksum")
        if (
            isinstance(item["size_bytes"], bool)
            or not isinstance(item["size_bytes"], int)
            or not 0 <= item["size_bytes"] <= MAX_FILE_BYTES
        ):
            raise _identity("ARTIFACT_INDEX_INVALID", "Artifact size is invalid")
        if item["verification_status"] != "VERIFIED":
            raise _identity("ARTIFACT_INDEX_INVALID", "Artifact is not verified")
        _timestamp(item["last_verified_at"], "last_verified_at")
        identities.append(item["artifact_id"])
        _record_case_path(paths, local_path)
        if not local_path.endswith(producer_path):
            raise _identity("ARTIFACT_INDEX_INVALID", "Artifact local path is inconsistent")
    if identities != sorted(set(identities)):
        raise _identity("ARTIFACT_INDEX_INVALID", "Artifact Index ordering is invalid")
    _timestamp(value["updated_at"], "updated_at")
    payload = dict(value)
    checksum = payload.pop("index_checksum")
    _checksum(checksum, "index_checksum")
    if canonical_hash(payload) != checksum:
        raise _identity("ARTIFACT_INDEX_INVALID", "Artifact Index checksum is invalid")
    return value


def refresh_artifact_index(
    *,
    workspace_root: str | Path,
    transport: Any,
    now: datetime | None = None,
) -> ArtifactOperationResult:
    workspace, descriptor, _ = load_workspace(workspace_root)
    with _WorkspaceWriteLock(workspace):
        index_path = workspace / ARTIFACT_INDEX
        if index_path.is_symlink():
            raise _identity("ARTIFACT_INDEX_INVALID", "Artifact Index path is unsafe")
        if index_path.exists():
            if not index_path.is_file():
                raise _identity("ARTIFACT_INDEX_INVALID", "Artifact Index path is invalid")
            _read_artifact_index(index_path, descriptor)
        lock = _require_installed_lock(workspace, descriptor)
        installed = {
            item["workflow_instance_id"]: item
            for item in lock["installed_capsules"]
        }
        cloud_artifacts = _fetch_all_artifacts(transport, descriptor["project_id"])
        timestamp = _utc_text(now or datetime.now(timezone.utc))
        entries: list[dict[str, Any]] = []
        for artifact in cloud_artifacts:
            if artifact.get("state") != "LOCAL_AVAILABLE":
                continue
            _validate_cloud_artifact(artifact, descriptor)
            instance_id = artifact["producer_workflow_instance_id"]
            capsule = installed.get(instance_id)
            if capsule is None:
                raise WorkspaceCLIError(
                    "ARTIFACT_BYTES_NOT_AVAILABLE",
                    "Producer Capsule is not installed in this Workspace",
                    EXIT_VALIDATION,
                )
            if artifact["producer_capsule_version"] != capsule["capsule_version"]:
                raise _identity(
                    "ARTIFACT_INDEX_CONFLICT",
                    "Artifact producer Capsule pin conflicts with Installed Lock",
                )
            producer_path = _safe_artifact_path(
                artifact["relative_path"], root="outputs"
            )
            capsule_path = _safe_artifact_path(capsule["relative_path"])
            local_relative_path = f"{capsule_path}/{producer_path}"
            source = workspace / local_relative_path
            content_checksum, size = _verified_regular_file(
                source,
                allowed_root=workspace / capsule_path,
                missing_code="ARTIFACT_BYTES_NOT_AVAILABLE",
            )
            if (
                content_checksum != artifact["content_checksum"]
                or size != artifact["size_bytes"]
            ):
                raise WorkspaceCLIError(
                    "LOCAL_ARTIFACT_DRIFT",
                    "Producer Artifact bytes no longer match Cloud metadata",
                    EXIT_VALIDATION,
                )
            entries.append({
                "artifact_id": artifact["artifact_id"],
                "artifact_type": artifact["artifact_type"],
                "artifact_schema_version": artifact["artifact_schema_version"],
                "producer_workflow_instance_id": instance_id,
                "producer_capsule_version": artifact["producer_capsule_version"],
                "producer_relative_path": producer_path,
                "content_checksum": content_checksum,
                "size_bytes": size,
                "verification_status": "VERIFIED",
                "last_verified_at": timestamp,
                "local_relative_path": local_relative_path,
            })
        entries.sort(key=lambda item: item["artifact_id"])
        payload = {
            "schema_version": ARTIFACT_INDEX_SCHEMA,
            "project_id": descriptor["project_id"],
            "workspace_id": descriptor["workspace_id"],
            "artifacts": entries,
            "updated_at": timestamp,
        }
        document = {**payload, "index_checksum": canonical_hash(payload)}
        _atomic_write_json(index_path, document)
        _read_artifact_index(index_path, descriptor)
        return ArtifactOperationResult(
            status="INDEX_REFRESHED",
            project_id=descriptor["project_id"],
            workspace_id=descriptor["workspace_id"],
            artifact_count=len(entries),
        )


def artifact_status(workspace_root: str | Path) -> dict[str, Any]:
    workspace, descriptor, _ = load_workspace(workspace_root)
    path = workspace / ARTIFACT_INDEX
    if not path.exists() and not path.is_symlink():
        return {
            "schema_version": "reagent.artifact-status/v0.1",
            "status": "NO_INDEX",
            "project_id": descriptor["project_id"],
            "workspace_id": descriptor["workspace_id"],
            "artifact_count": 0,
            "verified_count": 0,
            "drift_count": 0,
        }
    if path.is_symlink():
        raise _identity("ARTIFACT_INDEX_INVALID", "Artifact Index path is unsafe")
    index = _read_artifact_index(path, descriptor)
    verified = 0
    drift = 0
    for item in index["artifacts"]:
        candidate = workspace / item["local_relative_path"]
        try:
            checksum, size = _verified_regular_file(
                candidate,
                allowed_root=workspace,
                missing_code="ARTIFACT_BYTES_NOT_AVAILABLE",
            )
        except WorkspaceCLIError:
            drift += 1
            continue
        if checksum == item["content_checksum"] and size == item["size_bytes"]:
            verified += 1
        else:
            drift += 1
    return {
        "schema_version": "reagent.artifact-status/v0.1",
        "status": "VERIFIED" if drift == 0 else "LOCAL_ARTIFACT_DRIFT",
        "project_id": descriptor["project_id"],
        "workspace_id": descriptor["workspace_id"],
        "artifact_count": len(index["artifacts"]),
        "verified_count": verified,
        "drift_count": drift,
        "index_checksum": index["index_checksum"],
    }


def materialize_artifacts(
    *,
    workspace_root: str | Path,
    consumer_workflow_instance_id: str,
    transport: Any,
    dry_run: bool = False,
    now: datetime | None = None,
) -> ArtifactOperationResult:
    workspace, descriptor, _ = load_workspace(workspace_root)
    _match(
        consumer_workflow_instance_id,
        WORKFLOW_INSTANCE_ID,
        "consumer_workflow_instance_id",
    )
    plan = validate_materialization_plan(
        transport.materialization_plan(
            descriptor["project_id"], consumer_workflow_instance_id
        ),
        descriptor,
    )
    if dry_run:
        return ArtifactOperationResult(
            status="PLAN_CREATED",
            project_id=descriptor["project_id"],
            workspace_id=descriptor["workspace_id"],
            artifact_count=len(plan["artifacts"]),
            consumer_workflow_instance_id=consumer_workflow_instance_id,
        )
    with _WorkspaceWriteLock(workspace):
        lock = _require_installed_lock(workspace, descriptor)
        installed = {
            item["workflow_instance_id"]: item
            for item in lock["installed_capsules"]
        }
        index_path = workspace / ARTIFACT_INDEX
        if index_path.is_symlink() or not index_path.is_file():
            raise _identity("ARTIFACT_INDEX_INVALID", "Artifact Index is unavailable")
        index = _read_artifact_index(index_path, descriptor)
        indexed = {item["artifact_id"]: item for item in index["artifacts"]}
        completed = 0
        for item in plan["artifacts"]:
            consumer = installed.get(item["consumer_workflow_instance_id"])
            producer = installed.get(item["producer_workflow_instance_id"])
            if consumer is None:
                raise WorkspaceCLIError(
                    "DEPENDENCY_UNRESOLVED",
                    "Consumer Capsule is not installed",
                    EXIT_VALIDATION,
                )
            if producer is None:
                raise WorkspaceCLIError(
                    "ARTIFACT_BYTES_NOT_AVAILABLE",
                    "Producer Capsule bytes are unavailable",
                    EXIT_VALIDATION,
                )
            entry = indexed.get(item["artifact_id"])
            if entry is None:
                raise WorkspaceCLIError(
                    "ARTIFACT_BYTES_NOT_AVAILABLE",
                    "Artifact has not been verified into the Workspace Index",
                    EXIT_VALIDATION,
                )
            _require_plan_index_match(item, entry, producer, consumer)
            _materialize_one(
                workspace=workspace,
                descriptor=descriptor,
                plan=plan,
                item=item,
                index_entry=entry,
                timestamp=_utc_text(now or datetime.now(timezone.utc)),
            )
            completed += 1
        return ArtifactOperationResult(
            status="MATERIALIZED" if completed else "NO_DEPENDENCIES",
            project_id=descriptor["project_id"],
            workspace_id=descriptor["workspace_id"],
            artifact_count=len(index["artifacts"]),
            materialized_count=completed,
            consumer_workflow_instance_id=consumer_workflow_instance_id,
        )


def validate_materialization_plan(
    document: Any, workspace: dict[str, Any]
) -> dict[str, Any]:
    value = _object(document, "Artifact materialization plan")
    fields = {
        "schema_version", "project_id", "workspace_id",
        "consumer_workflow_instance_id", "artifacts", "created_at",
        "plan_checksum",
    }
    _exact_fields(value, fields, "Artifact materialization plan")
    if value["schema_version"] != MATERIALIZATION_PLAN_SCHEMA:
        raise _identity("MATERIALIZATION_PLAN_INVALID", "Materialization plan schema is unsupported")
    if (
        value["project_id"] != workspace["project_id"]
        or value["workspace_id"] != workspace["workspace_id"]
    ):
        raise _identity("MATERIALIZATION_PLAN_INVALID", "Materialization plan identity mismatch")
    _match(
        value["consumer_workflow_instance_id"],
        WORKFLOW_INSTANCE_ID,
        "consumer_workflow_instance_id",
    )
    artifacts = value["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) > 100:
        raise _identity("MATERIALIZATION_PLAN_INVALID", "Materialization plan entries are invalid")
    order: list[tuple[str, str]] = []
    targets: dict[str, str] = {}
    for raw in artifacts:
        item = _object(raw, "Artifact materialization entry")
        required = {
            "binding_id", "requirement_key", "consumer_workflow_instance_id",
            "producer_workflow_instance_id", "artifact_id", "artifact_type",
            "artifact_schema_version", "expected_checksum", "expected_size_bytes",
            "source_capsule_relative_path", "source_relative_path",
            "target_capsule_relative_path", "target_relative_path",
            "materialization_mode",
        }
        _exact_fields(item, required, "Artifact materialization entry")
        _match(item["binding_id"], BINDING_ID, "binding_id")
        _match(item["artifact_id"], ARTIFACT_ID, "artifact_id")
        for field in ("consumer_workflow_instance_id", "producer_workflow_instance_id"):
            _match(item[field], WORKFLOW_INSTANCE_ID, field)
        if item["consumer_workflow_instance_id"] != value["consumer_workflow_instance_id"]:
            raise _identity("MATERIALIZATION_PLAN_INVALID", "Consumer identity is inconsistent")
        _checksum(item["expected_checksum"], "expected_checksum")
        if (
            isinstance(item["expected_size_bytes"], bool)
            or not isinstance(item["expected_size_bytes"], int)
            or not 0 <= item["expected_size_bytes"] <= MAX_FILE_BYTES
        ):
            raise _identity("MATERIALIZATION_PLAN_INVALID", "Artifact size is unsupported")
        _safe_artifact_path(item["source_capsule_relative_path"], root="capsules")
        _safe_artifact_path(item["source_relative_path"], root="outputs")
        _safe_artifact_path(item["target_capsule_relative_path"], root="capsules")
        target = _safe_artifact_path(item["target_relative_path"], root="inputs")
        _record_case_path(targets, f"{item['target_capsule_relative_path']}/{target}")
        if item["materialization_mode"] != "VERIFIED_COPY":
            raise _identity("MATERIALIZATION_PLAN_INVALID", "Materialization mode is not supported")
        order.append((item["requirement_key"], item["artifact_id"]))
    if order != sorted(set(order)):
        raise _identity("MATERIALIZATION_PLAN_INVALID", "Materialization plan ordering is invalid")
    _timestamp(value["created_at"], "created_at")
    payload = dict(value)
    checksum = payload.pop("plan_checksum")
    _checksum(checksum, "plan_checksum")
    if canonical_hash(payload) != checksum:
        raise _identity("MATERIALIZATION_PLAN_INVALID", "Materialization plan checksum is invalid")
    return value


def _fetch_all_artifacts(transport: Any, project_id: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = _object(
            transport.list_artifacts(project_id, offset=offset, limit=100),
            "Artifact Reference page",
        )
        required = {
            "schema_version", "project_id", "artifacts", "offset", "limit",
            "total", "has_more",
        }
        _exact_fields(page, required, "Artifact Reference page")
        if page["schema_version"] != ARTIFACT_PAGE_SCHEMA or page["project_id"] != project_id:
            raise _identity("ARTIFACT_INDEX_INVALID", "Artifact page identity is invalid")
        if page["offset"] != offset or page["limit"] != 100:
            raise _identity("ARTIFACT_INDEX_INVALID", "Artifact pagination is inconsistent")
        batch = page["artifacts"]
        if not isinstance(batch, list) or len(batch) > 100:
            raise _identity("ARTIFACT_INDEX_INVALID", "Artifact page entries are invalid")
        values.extend(batch)
        if not page["has_more"]:
            if len(values) != page["total"]:
                raise _identity("ARTIFACT_INDEX_INVALID", "Artifact page total is inconsistent")
            return values
        if not batch:
            raise _identity("ARTIFACT_INDEX_INVALID", "Artifact pagination made no progress")
        offset += len(batch)


def _validate_cloud_artifact(artifact: Any, workspace: dict[str, Any]) -> None:
    value = _object(artifact, "Cloud Artifact Reference")
    required = {
        "schema_version", "artifact_id", "project_id",
        "producer_workflow_instance_id", "producer_progress_receipt_id",
        "producer_progress_report_id", "producer_execution_round",
        "producer_capsule_id", "producer_capsule_version", "artifact_type",
        "producer_core_capability_maturity",
        "artifact_schema_version", "media_type", "state", "relative_path",
        "content_checksum", "size_bytes", "cloud_metadata_available",
        "produced_at", "retired_at", "created_at", "updated_at",
    }
    _exact_fields(value, required, "Cloud Artifact Reference")
    if value["schema_version"] != "reagent.artifact-reference/v0.1":
        raise _identity("ARTIFACT_INDEX_INVALID", "Cloud Artifact schema is unsupported")
    if value["project_id"] != workspace["project_id"]:
        raise _identity("ARTIFACT_PROJECT_MISMATCH", "Cloud Artifact Project mismatch")
    _match(value["artifact_id"], ARTIFACT_ID, "artifact_id")
    _match(value["producer_workflow_instance_id"], WORKFLOW_INSTANCE_ID, "producer_workflow_instance_id")
    _match(value["producer_capsule_version"], SEMVER, "producer_capsule_version")
    if value["producer_core_capability_maturity"] not in {
        "REVIEWED_CORE", "SCAFFOLD_CORE"
    }:
        raise _identity("ARTIFACT_INDEX_INVALID", "Artifact producer maturity is invalid")
    _safe_artifact_path(value["relative_path"], root="outputs")
    _checksum(value["content_checksum"], "content_checksum")
    if (
        isinstance(value["size_bytes"], bool)
        or not isinstance(value["size_bytes"], int)
        or not 0 <= value["size_bytes"] <= MAX_FILE_BYTES
        or value["cloud_metadata_available"] is not True
    ):
        raise _identity("ARTIFACT_INDEX_INVALID", "Cloud Artifact bounds are invalid")


def _require_installed_lock(workspace: Path, descriptor: dict[str, Any]) -> dict[str, Any]:
    path = workspace / INSTALLED_LOCK
    if path.is_symlink() or not path.is_file():
        raise _identity("INSTALLED_LOCK_MISSING", "Installed Workspace Lock is required")
    return validate_installed_lock(_read_json(path), descriptor)


def _safe_artifact_path(value: Any, *, root: str | None = None) -> str:
    try:
        result = _safe_package_path(value)
    except WorkspaceCLIError as error:
        raise WorkspaceCLIError("UNSAFE_ARTIFACT_PATH", str(error), EXIT_VALIDATION) from error
    if root is not None and not result.startswith(root + "/"):
        raise WorkspaceCLIError(
            "UNSAFE_ARTIFACT_PATH",
            f"Artifact path must be under {root}/",
            EXIT_VALIDATION,
        )
    return result


def _verified_regular_file(
    path: Path, *, allowed_root: Path, missing_code: str
) -> tuple[str, int]:
    _reject_symlink_chain(path.parent)
    _assert_within(allowed_root, path)
    try:
        value = path.stat(follow_symlinks=False)
    except OSError as error:
        raise WorkspaceCLIError(missing_code, "Artifact bytes are unavailable", EXIT_VALIDATION) from error
    if not stat.S_ISREG(value.st_mode) or path.is_symlink() or value.st_nlink != 1:
        raise WorkspaceCLIError(
            "UNSAFE_ARTIFACT_PATH",
            "Artifact source must be one unlinked regular file",
            EXIT_VALIDATION,
        )
    if value.st_size > MAX_FILE_BYTES:
        raise WorkspaceCLIError(
            "ARTIFACT_CONTRACT_VIOLATION",
            "Artifact exceeds the supported local materialization bound",
            EXIT_VALIDATION,
        )
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    digest = hashlib.sha256()
    size = 0
    try:
        opened = os.fstat(descriptor)
        if (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
        ) != (
            value.st_dev,
            value.st_ino,
            value.st_size,
            value.st_mtime_ns,
        ):
            raise WorkspaceCLIError(
                "LOCAL_ARTIFACT_DRIFT",
                "Artifact source changed during verification",
                EXIT_VALIDATION,
            )
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    finally:
        os.close(descriptor)
    return "sha256:" + digest.hexdigest(), size


def _copy_verified_artifact(
    source: Path,
    destination: Any,
    *,
    allowed_root: Path,
    expected_checksum: str,
    expected_size: int,
) -> None:
    """Copy from one no-follow descriptor while validating the exact bytes.

    Opening and hashing the source through the same descriptor closes the gap
    between pre-copy verification and copying.  A producer replacing or
    mutating the source during materialization therefore fails closed.
    """

    _reject_symlink_chain(source.parent)
    _assert_within(allowed_root, source)
    try:
        before = source.stat(follow_symlinks=False)
        descriptor = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as error:
        raise WorkspaceCLIError(
            "ARTIFACT_BYTES_NOT_AVAILABLE",
            "Artifact bytes are unavailable",
            EXIT_VALIDATION,
        ) from error
    digest = hashlib.sha256()
    size = 0
    try:
        opened = os.fstat(descriptor)
        identity = (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
        )
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or identity
            != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        ):
            raise WorkspaceCLIError(
                "UNSAFE_ARTIFACT_PATH",
                "Artifact source changed or is not one unlinked regular file",
                EXIT_VALIDATION,
            )
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
            destination.write(chunk)
        after = os.fstat(descriptor)
        if (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ) != identity:
            raise WorkspaceCLIError(
                "LOCAL_ARTIFACT_DRIFT",
                "Artifact source changed during materialization",
                EXIT_VALIDATION,
            )
    finally:
        os.close(descriptor)
    actual_checksum = "sha256:" + digest.hexdigest()
    if actual_checksum != expected_checksum or size != expected_size:
        raise WorkspaceCLIError(
            "LOCAL_ARTIFACT_DRIFT",
            "Producer Artifact changed after Index verification",
            EXIT_VALIDATION,
        )
    destination.flush()
    os.fsync(destination.fileno())


def _require_plan_index_match(item, entry, producer, consumer) -> None:
    expected = {
        "producer_workflow_instance_id": item["producer_workflow_instance_id"],
        "artifact_type": item["artifact_type"],
        "artifact_schema_version": item["artifact_schema_version"],
        "producer_relative_path": item["source_relative_path"],
        "content_checksum": item["expected_checksum"],
        "size_bytes": item["expected_size_bytes"],
    }
    if any(entry.get(field) != value for field, value in expected.items()):
        raise WorkspaceCLIError(
            "ARTIFACT_INDEX_CONFLICT",
            "Artifact Index differs from the Cloud materialization plan",
            EXIT_VALIDATION,
        )
    if (
        producer["relative_path"] != item["source_capsule_relative_path"]
        or consumer["relative_path"] != item["target_capsule_relative_path"]
    ):
        raise WorkspaceCLIError(
            "MATERIALIZATION_PLAN_INVALID",
            "Materialization Capsule path differs from Installed Lock",
            EXIT_VALIDATION,
        )


def _materialize_one(*, workspace, descriptor, plan, item, index_entry, timestamp):
    source = workspace / index_entry["local_relative_path"]
    source_checksum, source_size = _verified_regular_file(
        source,
        allowed_root=workspace / item["source_capsule_relative_path"],
        missing_code="ARTIFACT_BYTES_NOT_AVAILABLE",
    )
    if (
        source_checksum != item["expected_checksum"]
        or source_size != item["expected_size_bytes"]
    ):
        raise WorkspaceCLIError(
            "LOCAL_ARTIFACT_DRIFT",
            "Producer Artifact changed after Index verification",
            EXIT_VALIDATION,
        )
    target_capsule = workspace / item["target_capsule_relative_path"]
    target = target_capsule / item["target_relative_path"]
    _assert_within(target_capsule, target)
    _ensure_destination_parents(workspace, target.parent)
    _reject_symlink_chain(target.parent)
    parent_identity = _directory_identity(target.parent)
    receipt_path = workspace / MATERIALIZATION_RECEIPTS_ROOT / f"{item['binding_id']}.json"
    if receipt_path.is_symlink():
        raise _identity("MATERIALIZED_ARTIFACT_DRIFT", "Materialization receipt path is unsafe")
    if target.exists() or target.is_symlink():
        if target.is_symlink():
            raise WorkspaceCLIError("MATERIALIZATION_CONFLICT", "Consumer target is a symlink", EXIT_VALIDATION)
        checksum, size = _verified_regular_file(
            target, allowed_root=target_capsule, missing_code="MATERIALIZATION_CONFLICT"
        )
        if checksum != item["expected_checksum"] or size != item["expected_size_bytes"]:
            code = "MATERIALIZED_ARTIFACT_DRIFT" if receipt_path.exists() else "MATERIALIZATION_CONFLICT"
            raise WorkspaceCLIError(code, "Consumer target contains different bytes", EXIT_VALIDATION)
        if receipt_path.exists():
            existing = _validate_materialization_receipt(
                _read_json(receipt_path), descriptor
            )
            candidate = _materialization_receipt(
                descriptor, plan, item, existing["materialized_at"]
            )
            if existing != candidate:
                raise WorkspaceCLIError(
                    "MATERIALIZATION_CONFLICT",
                    "Materialization receipt differs from the requested binding",
                    EXIT_VALIDATION,
                )
            return
        candidate = _materialization_receipt(descriptor, plan, item, timestamp)
        _atomic_write_json(receipt_path, candidate)
        return
    descriptor_fd, temporary_name = tempfile.mkstemp(
        prefix=f".{item['artifact_id']}.", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor_fd, "wb", closefd=True) as handle:
            _copy_verified_artifact(
                source,
                handle,
                allowed_root=workspace / item["source_capsule_relative_path"],
                expected_checksum=source_checksum,
                expected_size=source_size,
            )
        copied_checksum, copied_size = _verified_regular_file(
            temporary,
            allowed_root=target.parent,
            missing_code="MATERIALIZATION_CONFLICT",
        )
        if copied_checksum != source_checksum or copied_size != source_size:
            raise WorkspaceCLIError(
                "ARTIFACT_CHECKSUM_MISMATCH",
                "Staged consumer input failed checksum verification",
                EXIT_VALIDATION,
            )
        _reject_symlink_chain(target.parent)
        if _directory_identity(target.parent) != parent_identity:
            raise WorkspaceCLIError(
                "UNSAFE_ARTIFACT_PATH",
                "Consumer target parent changed during materialization",
                EXIT_VALIDATION,
            )
        try:
            os.link(temporary, target, follow_symlinks=False)
        except FileExistsError as error:
            raise WorkspaceCLIError(
                "MATERIALIZATION_CONFLICT",
                "Consumer target appeared during materialization",
                EXIT_VALIDATION,
            ) from error
        temporary.unlink()
        _fsync_directory(target.parent)
        final_checksum, final_size = _verified_regular_file(
            target, allowed_root=target_capsule, missing_code="MATERIALIZATION_CONFLICT"
        )
        if final_checksum != source_checksum or final_size != source_size:
            raise WorkspaceCLIError(
                "ARTIFACT_CHECKSUM_MISMATCH",
                "Published consumer input failed checksum verification",
                EXIT_VALIDATION,
            )
        _atomic_write_json(
            receipt_path,
            _materialization_receipt(descriptor, plan, item, timestamp),
        )
        _validate_materialization_receipt(_read_json(receipt_path), descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def _materialization_receipt(descriptor, plan, item, timestamp):
    payload = {
        "schema_version": MATERIALIZATION_RECEIPT_SCHEMA,
        "project_id": descriptor["project_id"],
        "workspace_id": descriptor["workspace_id"],
        "consumer_workflow_instance_id": item["consumer_workflow_instance_id"],
        "requirement_key": item["requirement_key"],
        "binding_id": item["binding_id"],
        "artifact_id": item["artifact_id"],
        "producer_workflow_instance_id": item["producer_workflow_instance_id"],
        "artifact_type": item["artifact_type"],
        "artifact_schema_version": item["artifact_schema_version"],
        "source_checksum": item["expected_checksum"],
        "target_relative_path": (
            f"{item['target_capsule_relative_path']}/{item['target_relative_path']}"
        ),
        "target_checksum": item["expected_checksum"],
        "materialized_at": timestamp,
        "materialization_version": "0.1.0",
        "plan_checksum": plan["plan_checksum"],
    }
    return {**payload, "receipt_checksum": canonical_hash(payload)}


def _validate_materialization_receipt(document, descriptor):
    value = _object(document, "Artifact materialization receipt")
    required = {
        "schema_version", "project_id", "workspace_id",
        "consumer_workflow_instance_id", "requirement_key", "binding_id",
        "artifact_id", "producer_workflow_instance_id", "artifact_type",
        "artifact_schema_version", "source_checksum", "target_relative_path",
        "target_checksum", "materialized_at", "materialization_version",
        "plan_checksum", "receipt_checksum",
    }
    _exact_fields(value, required, "Artifact materialization receipt")
    if value["schema_version"] != MATERIALIZATION_RECEIPT_SCHEMA:
        raise _identity("MATERIALIZED_ARTIFACT_DRIFT", "Materialization receipt schema is invalid")
    if value["project_id"] != descriptor["project_id"] or value["workspace_id"] != descriptor["workspace_id"]:
        raise _identity("MATERIALIZED_ARTIFACT_DRIFT", "Materialization receipt identity mismatch")
    _safe_artifact_path(value["target_relative_path"], root="capsules")
    for field in ("source_checksum", "target_checksum", "plan_checksum"):
        _checksum(value[field], field)
    _timestamp(value["materialized_at"], "materialized_at")
    payload = dict(value)
    checksum = payload.pop("receipt_checksum")
    _checksum(checksum, "receipt_checksum")
    if canonical_hash(payload) != checksum:
        raise _identity("MATERIALIZED_ARTIFACT_DRIFT", "Materialization receipt checksum is invalid")
    return value


def _progress_report_identity(report: dict[str, Any]) -> dict[str, str]:
    content = {
        key: value
        for key, value in report.items()
        if key not in {"report_id", "report_content_checksum", "report_checksum"}
    }
    content_checksum = canonical_hash(content)
    report_id = "prv2-" + canonical_hash({
        "package_id": report.get("package_id"),
        "workflow_id": report.get("workflow_id"),
        "workflow_version": report.get("workflow_version"),
        "execution_round": report.get("execution_round"),
        "previous_report_id": report.get("previous_report_id"),
        "report_content_checksum": content_checksum,
    }).split(":", 1)[1]
    identified = {
        **report,
        "report_id": report_id,
        "report_content_checksum": content_checksum,
        "report_checksum": None,
    }
    return {
        "report_content_checksum": content_checksum,
        "report_id": report_id,
        "report_checksum": canonical_hash(identified),
    }


def _validated_local_progress_chain(
    capsule: Path, manifest: dict[str, Any], *, allow_context_mismatch: bool = False
) -> list[dict[str, Any]]:
    """Return a strict, semantically ordered, contiguous local report chain.

    Current output bytes are deliberately validated by the separate exact
    output validator below.  Keeping the concerns separate lets one narrowly
    proven historical renderer defect be recognized without adding a generic
    output-integrity bypass.
    """

    reports_root = capsule / "memory/progress/reports"
    if reports_root.is_symlink():
        raise _identity("LOCAL_PROGRESS_INVALID", "Local Progress history path is unsafe")
    if not reports_root.exists():
        return []
    if not reports_root.is_dir():
        raise _identity("LOCAL_PROGRESS_INVALID", "Local Progress history path is invalid")
    reports: list[dict[str, Any]] = []
    paths = list(reports_root.glob("prv2-*.json"))
    if len(paths) > MAX_FILES:
        raise _identity("LOCAL_PROGRESS_INVALID", "Local Progress history is too large")
    for path in paths:
        metadata = path.stat(follow_symlinks=False)
        if (
            path.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or not 0 < metadata.st_size <= MAX_CONTROL_JSON_BYTES
        ):
            raise _identity("LOCAL_PROGRESS_INVALID", "Local Progress history contains an unsafe entry")
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise _identity("LOCAL_PROGRESS_INVALID", "Local Progress history is invalid") from error
        if not isinstance(report, dict) or set(report) != PROGRESS_REPORT_FIELDS:
            raise _identity("LOCAL_PROGRESS_INVALID", "Local Progress Report fields are invalid")
        identity = _progress_report_identity(report)
        execution_round = report.get("execution_round")
        if (
            report.get("schema_version") != PROGRESS_REPORT_SCHEMA
            or path.name != f"{report.get('report_id')}.json"
            or any(report.get(field) != value for field, value in identity.items())
            or isinstance(execution_round, bool)
            or not isinstance(execution_round, int)
            or execution_round < 1
            or report.get("status") not in {
                "IN_PROGRESS", "COMPLETED", "BLOCKED", "FAILED", "CANCELLED"
            }
        ):
            raise _identity("LOCAL_PROGRESS_INVALID", "Local Progress identity is invalid")
        if any(
            report.get(field) != manifest.get(manifest_field)
            for field, manifest_field in {
                "project_id": "experimental_project_identity",
                "package_id": "package_id",
                "package_checksum": "package_checksum",
                "package_schema_version": "package_schema_version",
                "workflow_id": "workflow_id",
                "workflow_version": "workflow_version",
                "workflow_checksum": "workflow_checksum",
            }.items()
        ):
            raise _identity("LOCAL_PROGRESS_INVALID", "Local Progress package identity is invalid")
        for field in (
            "report_content_checksum", "report_checksum", "package_checksum",
            "workflow_checksum", "context_before_checksum", "context_after_checksum",
        ):
            _checksum(report.get(field), field)
        for field in ("started_at", "completed_at", "generated_at"):
            _timestamp(report.get(field), field)
        if _timestamp(report["completed_at"], "completed_at") < _timestamp(
            report["started_at"], "started_at"
        ):
            raise _identity("LOCAL_PROGRESS_INVALID", "Local Progress timestamps are invalid")
        for field in (
            "completed_work", "warnings", "errors", "unresolved_questions",
            "continuation_instructions", "skill_pins", "template_pins",
        ):
            if not isinstance(report.get(field), list):
                raise _identity("LOCAL_PROGRESS_INVALID", f"Local Progress {field} is invalid")
        for field in ("current_state", "next_recommended_action"):
            if not isinstance(report.get(field), str) or not report[field].strip():
                raise _identity("LOCAL_PROGRESS_INVALID", f"Local Progress {field} is invalid")
        outputs = report.get("output_artifacts")
        if not isinstance(outputs, list) or len(outputs) > 100:
            raise _identity("LOCAL_PROGRESS_INVALID", "Local Progress outputs are invalid")
        for output in outputs:
            if not isinstance(output, dict) or set(output) != {
                "relative_path", "artifact_kind", "media_type", "checksum", "size"
            }:
                raise _identity("LOCAL_PROGRESS_INVALID", "Local Progress output fields are invalid")
            _safe_artifact_path(output["relative_path"], root="outputs")
            _checksum(output.get("checksum"), "output checksum")
            if (
                isinstance(output.get("size"), bool)
                or not isinstance(output.get("size"), int)
                or not 0 <= output["size"] <= MAX_FILE_BYTES
            ):
                raise _identity("LOCAL_PROGRESS_INVALID", "Local Progress output size is invalid")
        if (report.get("previous_report_id") is None) != (
            report.get("previous_report_checksum") is None
        ):
            raise _identity("LOCAL_PROGRESS_INVALID", "Local Progress predecessor identity is invalid")
        reports.append(report)
    reports.sort(key=lambda item: (item["execution_round"], item["report_id"]))
    if not reports:
        return reports
    rounds = [item["execution_round"] for item in reports]
    if len(rounds) != len(set(rounds)):
        raise _identity("LOCAL_PROGRESS_BRANCHED", "Local Progress contains two reports for one execution round")
    if rounds != list(range(1, len(reports) + 1)):
        raise _identity("LOCAL_PROGRESS_GAP", "Local Progress execution rounds are not contiguous from round 1")
    if reports[0]["previous_report_id"] is not None:
        raise _identity("LOCAL_PROGRESS_INVALID", "Local Progress round 1 names a predecessor")
    for previous, current in zip(reports, reports[1:]):
        if (
            current["previous_report_id"] != previous["report_id"]
            or current["previous_report_checksum"] != previous["report_checksum"]
            or current["context_before_checksum"] != previous["context_after_checksum"]
        ):
            raise _identity("LOCAL_PROGRESS_GAP", "Local Progress predecessor chain is invalid")
    context = capsule / "memory/context.md"
    context_checksum, _ = _verified_regular_file(
        context, allowed_root=capsule, missing_code="LOCAL_PROGRESS_INVALID"
    )
    if (
        reports[-1]["context_after_checksum"] != context_checksum
        and not allow_context_mismatch
    ):
        raise _identity("LOCAL_PROGRESS_INVALID", "Local Progress does not match current local context")
    return reports


def _validate_latest_progress_outputs_exact(
    capsule: Path, reports: list[dict[str, Any]],
) -> None:
    """Require every output claimed by the latest round to match current bytes."""

    if not reports:
        return
    # Mutable Workflow outputs may legitimately differ from earlier rounds.
    # Only the latest round claims the current output bytes.
    for output in reports[-1]["output_artifacts"]:
        relative = _safe_artifact_path(output["relative_path"], root="outputs")
        checksum, size = _verified_regular_file(
            capsule / relative,
            allowed_root=capsule,
            missing_code="LOCAL_PROGRESS_INVALID",
        )
        if checksum != output["checksum"] or size != output["size"]:
            raise _identity("LOCAL_PROGRESS_INVALID", "Latest local Progress output integrity is invalid")


def _validated_local_progress_reports(
    capsule: Path, manifest: dict[str, Any], *, allow_context_mismatch: bool = False
) -> list[dict[str, Any]]:
    """Return a fully validated report chain with exact current output bytes."""

    reports = _validated_local_progress_chain(
        capsule, manifest, allow_context_mismatch=allow_context_mismatch
    )
    _validate_latest_progress_outputs_exact(capsule, reports)
    return reports


_LEGACY_SCAFFOLD_DRIFT_PINS = {
    ("writing-local-experimental", "0.2.0", "0.3.0"),
    ("review-local-experimental", "0.2.0", "0.3.0"),
    ("reproduction-experiment-local-experimental", "0.3.0", "0.4.0"),
}

_LEGACY_EXPERIMENT_V0_4_IDENTITY = {
    "workflow_id": "reproduction-experiment-local-experimental",
    "workflow_version": "0.3.0",
    "capsule_version": "0.4.0",
    "capsule_id": "capsule-be6448913e6c3d00512ecb2e8a5f00ae",
    "capsule_definition_checksum": (
        "sha256:be6448913e6c3d00512ecb2e8a5f00ae70e9746e7e79d71657c93e25d917c96a"
    ),
    "package_template_id": (
        "reproduction-experiment-scaffold-package-experimental"
    ),
    "generator_version": (
        "reagent-reproduction-experiment-local-experimental-compiler/0.4.0"
    ),
    "workflow_checksum": (
        "sha256:5851dc2ca70d4f47c73c0a7d84fe7a2beb4f67f853f103667c10079b7990cf81"
    ),
}


def _scaffold_provenance_is_exact(
    workspace: Path,
    descriptor: dict[str, Any],
    installed: dict[str, Any],
    capsule: Path,
) -> bool:
    """Validate exact bound input identity using only durable local receipts."""

    config = _read_package_json(capsule / "workflow/scaffold.json")
    provenance = _read_package_json(capsule / "memory/input-provenance.json")
    requirements = config.get("input_requirements")
    records = provenance.get("artifacts")
    if (
        config.get("workflow_id") != installed["workflow_definition_id"]
        or provenance.get("schema_version")
        != "reagent.scaffold-input-provenance/v0.1"
        or provenance.get("workflow_instance_id") != installed["workflow_instance_id"]
        or not isinstance(requirements, list)
        or not isinstance(records, dict)
    ):
        return False
    contracts = {
        item.get("requirement_key"): item
        for item in requirements if isinstance(item, dict)
    }
    if None in contracts or set(records) - set(contracts):
        return False
    required = {
        key for key, item in contracts.items() if item.get("required") is True
    }
    if not required.issubset(records):
        return False
    receipts_root = workspace / MATERIALIZATION_RECEIPTS_ROOT
    if receipts_root.is_symlink() or not receipts_root.is_dir():
        return False
    receipts: dict[str, dict[str, Any]] = {}
    for path in receipts_root.glob("artifact-binding-*.json"):
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
            return False
        receipt = _validate_materialization_receipt(_read_json(path), descriptor)
        if receipt["consumer_workflow_instance_id"] != installed["workflow_instance_id"]:
            continue
        key = receipt["requirement_key"]
        if key in receipts:
            return False
        receipts[key] = receipt
    if set(receipts) != set(records):
        return False
    for key, record in records.items():
        contract = contracts[key]
        receipt = receipts[key]
        if not isinstance(record, dict) or set(record) != {
            "artifact_id", "artifact_type", "sha256", "relative_path"
        }:
            return False
        expected_target = f"{installed['relative_path']}/{contract['target_relative_path']}"
        if (
            record != {
                "artifact_id": receipt["artifact_id"],
                "artifact_type": receipt["artifact_type"],
                "sha256": receipt["target_checksum"],
                "relative_path": contract["target_relative_path"],
            }
            or receipt["target_relative_path"] != expected_target
            or receipt["artifact_type"] != contract["artifact_type"]
        ):
            return False
        checksum, _ = _verified_regular_file(
            workspace / expected_target,
            allowed_root=capsule,
            missing_code="LOCAL_PROGRESS_INVALID",
        )
        if checksum != receipt["target_checksum"]:
            return False
    return True


def _legacy_scaffold_context_drift_is_exact(
    *,
    workspace: Path,
    descriptor: dict[str, Any],
    installed: dict[str, Any],
    capsule: Path,
    manifest: dict[str, Any],
    reports: list[dict[str, Any]],
) -> bool:
    """Recognize only the deterministic historical post-finalize rewrite.

    Historical interactive runners called ``_update_context`` after the Agent
    had already finalized.  Since report N then existed, that exact function
    wrote ``completed_rounds=N+1`` before its duplicate finalize failed.
    """

    pin = (
        installed.get("workflow_definition_id", manifest["workflow_id"]),
        installed.get("workflow_definition_version", manifest["workflow_version"]),
        installed.get("capsule_version", manifest["package_template_version"]),
    )
    if pin not in _LEGACY_SCAFFOLD_DRIFT_PINS or not reports:
        return False
    latest = reports[-1]
    if latest.get("status") != "COMPLETED" or latest.get("current_state") != "COMPLETED":
        return False
    context_path = capsule / "memory/context.md"
    current_checksum, _ = _verified_regular_file(
        context_path, allowed_root=capsule, missing_code="LOCAL_PROGRESS_INVALID"
    )
    if current_checksum == latest["context_after_checksum"]:
        return False
    current = _read_package_json(capsule / "memory/current-artifact.json")
    if set(current) != {"relative_path", "artifact_kind", "media_type", "checksum", "size"}:
        return False
    if current not in latest["output_artifacts"]:
        return False
    artifact_checksum, artifact_size = _verified_regular_file(
        capsule / _safe_artifact_path(current["relative_path"], root="outputs"),
        allowed_root=capsule,
        missing_code="LOCAL_PROGRESS_INVALID",
    )
    if artifact_checksum != current["checksum"] or artifact_size != current["size"]:
        return False
    try:
        validator = runpy.run_path(str(capsule / "validate_package.py"))
        artifact = _read_package_json(capsule / current["relative_path"])
        validator["validate_scaffold_artifact"](artifact)
        runtime = runpy.run_path(str(capsule / "reagent_local.py"))
        config = _read_package_json(capsule / "workflow/scaffold.json")
        provenance = _read_package_json(capsule / "memory/input-provenance.json")
        expected_artifact, expected_human = runtime["_scaffold_payload"](
            config, provenance["artifacts"], capsule
        )
        if artifact != expected_artifact:
            return False
        human_path = capsule / _safe_artifact_path(
            config["human_output_path"], root="outputs"
        )
        _human_checksum, _human_size = _verified_regular_file(
            human_path, allowed_root=capsule, missing_code="LOCAL_PROGRESS_INVALID"
        )
        if human_path.read_bytes() != expected_human:
            return False
    except Exception:
        return False
    try:
        provenance_exact = _scaffold_provenance_is_exact(
            workspace, descriptor, installed, capsule
        )
    except (OSError, WorkspaceCLIError):
        provenance_exact = False
    if not provenance_exact:
        return False
    raw = context_path.read_bytes()
    prefix = b"# Scaffold Workflow Context\n\n```json\n"
    suffix = b"\n```\n"
    if not raw.startswith(prefix) or not raw.endswith(suffix):
        return False
    try:
        context = json.loads(raw[len(prefix):-len(suffix)].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    expected_fields = {
        "schema_version", "workflow_id", "core_capability_maturity",
        "completed_rounds", "latest_artifact", "continuation", "updated_at",
    }
    if set(context) != expected_fields:
        return False
    if context != {
        "schema_version": "reagent.scaffold-context/v0.1",
        "workflow_id": manifest["workflow_id"],
        "core_capability_maturity": "SCAFFOLD_CORE",
        "completed_rounds": latest["execution_round"] + 1,
        "latest_artifact": current,
        "continuation": "Read local files; prior chat history is not required.",
        "updated_at": context.get("updated_at"),
    }:
        return False
    try:
        context_time = _timestamp(context["updated_at"], "updated_at")
        completed_time = _timestamp(latest["completed_at"], "completed_at")
    except WorkspaceCLIError:
        return False
    if context_time < completed_time:
        return False
    canonical = prefix + canonical_json(context).encode("utf-8") + suffix
    return raw == canonical and current["artifact_kind"] in {
        "manuscript-draft/v1", "review-report/v1", "experiment-record/v1"
    }


def _legacy_experiment_v0_4_release_is_exact(
    *, installed: dict[str, Any], capsule: Path, manifest: dict[str, Any],
) -> bool:
    """Bind the exception to the one reviewed historical Capsule release."""

    identity = _LEGACY_EXPERIMENT_V0_4_IDENTITY
    expected_installed = {
        "workflow_definition_id": identity["workflow_id"],
        "workflow_definition_version": identity["workflow_version"],
        "capsule_version": identity["capsule_version"],
        "capsule_id": identity["capsule_id"],
        "capsule_definition_checksum": identity["capsule_definition_checksum"],
        "package_id": manifest.get("package_id"),
        "package_checksum": manifest.get("package_checksum"),
        "manifest_checksum": manifest.get("manifest_checksum"),
        "verification_status": "VERIFIED",
    }
    if any(
        installed.get(field) != value
        for field, value in expected_installed.items()
    ):
        return False
    if any(
        manifest.get(field) != value
        for field, value in {
            "package_schema_version": PACKAGE_SCHEMA,
            "package_template_id": identity["package_template_id"],
            "package_template_version": identity["capsule_version"],
            "generator_version": identity["generator_version"],
            "workflow_id": identity["workflow_id"],
            "workflow_version": identity["workflow_version"],
            "workflow_checksum": identity["workflow_checksum"],
        }.items()
    ):
        return False
    immutable_checksum = installed.get("immutable_contract_checksum")
    if not isinstance(immutable_checksum, str):
        return False
    try:
        return immutable_checksum == _immutable_contract_checksum(capsule, manifest)
    except (OSError, WorkspaceCLIError, KeyError, TypeError):
        return False


def _legacy_experiment_v0_4_output_and_context_drift_is_exact(
    *,
    workspace: Path,
    descriptor: dict[str, Any],
    installed: dict[str, Any],
    capsule: Path,
    manifest: dict[str, Any],
    reports: list[dict[str, Any]],
) -> bool:
    """Prove the combined Experiment 0.4 plan-A -> plan-B failure fingerprint.

    The immutable report remains bound to the owner-reviewed human plan A.
    The only accepted current-output mismatch is the exact deterministic plan
    B written by the verified historical runner after that report existed.
    Every other output, especially experiment-record/v1, stays exact.
    """

    if (
        not reports
        or not _legacy_experiment_v0_4_release_is_exact(
            installed=installed, capsule=capsule, manifest=manifest
        )
    ):
        return False
    latest = reports[-1]
    if (
        latest.get("status") != "COMPLETED"
        or latest.get("current_state") != "COMPLETED"
    ):
        return False
    try:
        config = _read_package_json(capsule / "workflow/scaffold.json")
    except (OSError, WorkspaceCLIError):
        return False
    identity = _LEGACY_EXPERIMENT_V0_4_IDENTITY
    if any(
        config.get(field) != value
        for field, value in {
            "workflow_id": identity["workflow_id"],
            "workflow_version": identity["workflow_version"],
            "workflow_kind": "EXPERIMENT",
            "core_capability_maturity": "SCAFFOLD_CORE",
            "human_output_path": "outputs/experiment_plan.md",
            "output_artifact_type": "experiment-record/v1",
            "supported_mode": "IDEA_EXPERIMENT",
        }.items()
    ):
        return False
    outputs = latest.get("output_artifacts")
    if not isinstance(outputs, list) or len(outputs) != 2:
        return False
    human = [
        item for item in outputs
        if item.get("relative_path") == "outputs/experiment_plan.md"
    ]
    typed = [item for item in outputs if item.get("artifact_kind") == "experiment-record/v1"]
    if len(human) != 1 or len(typed) != 1:
        return False
    human_record = human[0]
    if (
        human_record.get("artifact_kind") != "EXPERIMENT_SCAFFOLD_PLACEHOLDER"
        or human_record.get("media_type") != "text/markdown"
        or typed[0].get("media_type") != "application/json"
        or typed[0].get("relative_path") == human_record["relative_path"]
    ):
        return False
    try:
        human_checksum, human_size = _verified_regular_file(
            capsule / "outputs/experiment_plan.md",
            allowed_root=capsule,
            missing_code="LOCAL_PROGRESS_INVALID",
        )
        # This branch proves a rewrite.  Byte-equal human output belongs to the
        # existing context-only legacy path, never this exception.
        if (
            human_checksum == human_record["checksum"]
            and human_size == human_record["size"]
        ):
            return False
        for output in typed:
            relative = _safe_artifact_path(output["relative_path"], root="outputs")
            checksum, size = _verified_regular_file(
                capsule / relative,
                allowed_root=capsule,
                missing_code="LOCAL_PROGRESS_INVALID",
            )
            if checksum != output["checksum"] or size != output["size"]:
                return False
    except (OSError, WorkspaceCLIError, KeyError, TypeError):
        return False
    # Reuse the existing exact historical renderer, Artifact/provenance proof,
    # and canonical N+1 context proof.  In particular it byte-compares the
    # current Markdown with the historical Capsule's own _scaffold_payload().
    return _legacy_scaffold_context_drift_is_exact(
        workspace=workspace,
        descriptor=descriptor,
        installed=installed,
        capsule=capsule,
        manifest=manifest,
        reports=reports,
    )


def _accepted_cloud_progress(
    page: dict[str, Any],
    *,
    descriptor: dict[str, Any],
    installed: dict[str, Any],
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    if (
        page.get("schema_version") != "reagent.workflow-instance-progress/v0.1"
        or page.get("project_id") != descriptor["project_id"]
        or page.get("workflow_instance_id") != installed["workflow_instance_id"]
        or not isinstance(page.get("projection"), dict)
        or not isinstance(page.get("history"), list)
    ):
        raise _identity("CLOUD_PROGRESS_INVALID", "Cloud Progress identity is invalid")
    projection = page["projection"]
    if (
        projection.get("project_id") != descriptor["project_id"]
        or projection.get("workflow_instance_id") != installed["workflow_instance_id"]
    ):
        raise _identity("CLOUD_PROGRESS_INVALID", "Cloud Progress projection identity is invalid")
    accepted: list[dict[str, Any]] = []
    for uploaded in page["history"]:
        if not isinstance(uploaded, dict):
            raise _identity("CLOUD_PROGRESS_INVALID", "Cloud Progress history is invalid")
        if uploaded.get("accepted_for_projection") is not True:
            continue
        normalized = uploaded.get("normalized_record")
        if not isinstance(normalized, dict):
            raise _identity("CLOUD_PROGRESS_INVALID", "Accepted Cloud Progress lacks a normalized record")
        if (
            uploaded.get("project_id") != descriptor["project_id"]
            or uploaded.get("workflow_instance_id") != installed["workflow_instance_id"]
            or uploaded.get("package_id") != manifest["package_id"]
            or uploaded.get("package_checksum") != manifest["package_checksum"]
            or normalized.get("project_id") != descriptor["project_id"]
            or normalized.get("package_id") != manifest["package_id"]
            or normalized.get("package_checksum") != manifest["package_checksum"]
            or normalized.get("workflow_id") != manifest["workflow_id"]
            or normalized.get("workflow_version") != manifest["workflow_version"]
            or normalized.get("workflow_checksum") != manifest["workflow_checksum"]
            or normalized.get("report_id") != uploaded.get("report_id")
            or normalized.get("report_checksum") != uploaded.get("report_checksum")
        ):
            raise _identity("CLOUD_PROGRESS_INVALID", "Cloud Progress package scope is invalid")
        accepted.append(uploaded)
    accepted.sort(key=lambda item: (
        item["normalized_record"]["execution_round"], item["report_id"]
    ))
    rounds = [item["normalized_record"]["execution_round"] for item in accepted]
    if rounds != list(range(1, len(accepted) + 1)):
        raise _identity("CLOUD_PROGRESS_INVALID", "Accepted Cloud Progress is not a contiguous chain")
    latest = projection.get("latest_execution_round")
    if latest != (rounds[-1] if rounds else None):
        raise _identity("CLOUD_PROGRESS_INVALID", "Cloud Progress latest round is inconsistent")
    return accepted


def _progress_receipt_payload(
    *,
    descriptor: dict[str, Any],
    installed: dict[str, Any],
    manifest: dict[str, Any],
    report: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    required = {
        "receipt_id", "project_id", "workflow_instance_id", "package_id",
        "report_id", "report_checksum", "original_report_checksum",
        "validation_status", "chain_state", "accepted_for_projection",
        "uploaded_at", "received_at", "warning_count", "error_count",
        "receipt_checksum",
    }
    if not required.issubset(receipt):
        raise _identity("CLOUD_PROGRESS_INVALID", "Cloud Progress receipt is incomplete")
    if any(
        receipt.get(field) != value
        for field, value in {
            "project_id": descriptor["project_id"],
            "workflow_instance_id": installed["workflow_instance_id"],
            "package_id": manifest["package_id"],
            "report_id": report["report_id"],
            "report_checksum": report["report_checksum"],
            "validation_status": "ACCEPTED",
            "chain_state": "VALID_CHAIN",
            "accepted_for_projection": True,
        }.items()
    ):
        raise _identity("CLOUD_PROGRESS_INVALID", "Cloud Progress receipt was not accepted for the exact report")
    if not isinstance(receipt.get("receipt_id"), str) or not re.fullmatch(
        r"progress-receipt-[0-9a-f]{64}", receipt["receipt_id"]
    ):
        raise _identity("CLOUD_PROGRESS_INVALID", "Cloud Progress receipt ID is invalid")
    _timestamp(receipt.get("uploaded_at"), "uploaded_at")
    _timestamp(receipt.get("received_at"), "received_at")
    original_report_checksum = receipt.get("original_report_checksum")
    _checksum(original_report_checksum, "original_report_checksum")
    _checksum(receipt.get("receipt_checksum"), "receipt_checksum")
    checksum_payload = {
        key: receipt[key]
        for key in (
            "receipt_id", "project_id", "workflow_instance_id", "package_id",
            "report_id", "report_checksum", "original_report_checksum",
            "validation_status", "chain_state", "accepted_for_projection",
            "uploaded_at", "received_at", "warning_count", "error_count",
        )
    }
    if canonical_hash(checksum_payload) != receipt["receipt_checksum"]:
        raise _identity("CLOUD_PROGRESS_INVALID", "Cloud Progress receipt checksum is invalid")
    payload = {
        "schema_version": PROGRESS_RECEIPT_SCHEMA,
        "project_id": descriptor["project_id"],
        "workspace_id": descriptor["workspace_id"],
        "workflow_instance_id": installed["workflow_instance_id"],
        "package_id": manifest["package_id"],
        "package_checksum": manifest["package_checksum"],
        "execution_round": report["execution_round"],
        "report_id": report["report_id"],
        "report_checksum": report["report_checksum"],
        "original_report_checksum": original_report_checksum,
        "receipt_id": receipt["receipt_id"],
        "cloud_receipt_checksum": receipt["receipt_checksum"],
        "acknowledged_at": receipt["received_at"],
    }
    return {**payload, "acknowledgement_checksum": canonical_hash(payload)}


def _history_receipt(uploaded: dict[str, Any]) -> dict[str, Any]:
    receipt = {
        "receipt_id": uploaded.get("receipt_id"),
        "project_id": uploaded.get("project_id"),
        "workflow_instance_id": uploaded.get("workflow_instance_id"),
        "package_id": uploaded.get("package_id"),
        "report_id": uploaded.get("report_id"),
        "report_checksum": uploaded.get("report_checksum"),
        "original_report_checksum": uploaded.get("original_report_checksum"),
        "validation_status": uploaded.get("validation_status"),
        "chain_state": uploaded.get("chain_state"),
        "accepted_for_projection": uploaded.get("accepted_for_projection"),
        "uploaded_at": uploaded.get("uploaded_at"),
        "received_at": uploaded.get("received_at"),
        "warning_count": len(uploaded.get("validation_warnings", [])),
        "error_count": len(uploaded.get("validation_errors", [])),
    }
    return {**receipt, "receipt_checksum": canonical_hash(receipt)}


def _progress_receipt_path(
    workspace: Path, workflow_instance_id: str, report_id: str
) -> Path:
    _match(workflow_instance_id, WORKFLOW_INSTANCE_ID, "workflow_instance_id")
    if not isinstance(report_id, str) or not re.fullmatch(r"prv2-[0-9a-f]{64}", report_id):
        raise _identity("LOCAL_PROGRESS_INVALID", "Progress Report ID is invalid")
    return workspace / PROGRESS_RECEIPTS_ROOT / workflow_instance_id / f"{report_id}.json"


def _store_progress_acknowledgement(
    *,
    workspace: Path,
    descriptor: dict[str, Any],
    installed: dict[str, Any],
    manifest: dict[str, Any],
    report: dict[str, Any],
    receipt: dict[str, Any],
) -> None:
    payload = _progress_receipt_payload(
        descriptor=descriptor,
        installed=installed,
        manifest=manifest,
        report=report,
        receipt=receipt,
    )
    path = _progress_receipt_path(
        workspace, installed["workflow_instance_id"], report["report_id"]
    )
    if path.is_symlink():
        raise _identity("LOCAL_PROGRESS_INVALID", "Progress acknowledgement path is unsafe")
    if path.exists():
        existing = _read_json(path)
        if existing != payload:
            raise _identity("LOCAL_PROGRESS_CONFLICT", "Progress acknowledgement conflicts with Cloud history")
        return
    _reject_symlink_chain(path.parent)
    _atomic_write_json(path, payload)


def _progress_upload_envelope(
    capsule: Path,
    workflow_instance_id: str,
    report: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    path = capsule / "memory/progress/reports" / f"{report['report_id']}.json"
    content = path.read_bytes()
    declarations: list[dict[str, Any]] = []
    current_path = capsule / "memory/current-artifact.json"
    if current_path.exists() and not current_path.is_symlink():
        current = _object(_read_json(current_path), "current Artifact")
        _exact_fields(current, {
            "relative_path", "artifact_kind", "media_type", "checksum", "size",
        }, "current Artifact")
        if current not in report.get("output_artifacts", []):
            raise _identity("LOCAL_PROGRESS_INVALID", "Current Artifact is absent from Progress")
        artifact_path = capsule / _safe_artifact_path(current["relative_path"], root="outputs")
        checksum, size = _verified_regular_file(
            artifact_path, allowed_root=capsule, missing_code="LOCAL_PROGRESS_INVALID"
        )
        if checksum != current["checksum"] or size != current["size"]:
            raise _identity("LOCAL_PROGRESS_INVALID", "Current Artifact bytes drifted")
        artifact_id = "artifact-" + uuid.uuid5(
            uuid.UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966"),
            "production-artifact/v1|package=" + report["package_id"]
            + "|report=" + report["report_id"]
            + "|path=" + current["relative_path"]
            + "|checksum=" + current["checksum"],
        ).hex
        declarations.append({
            "artifact_id": artifact_id,
            "artifact_type": current["artifact_kind"],
            "artifact_schema_version": current["artifact_kind"],
            "media_type": current["media_type"],
            "relative_path": current["relative_path"],
            "content_checksum": current["checksum"],
            "size_bytes": current["size"],
            "produced_at": report["completed_at"],
        })
    payload = {
        "workflow_instance_id": workflow_instance_id,
        "upload_schema_version": "progress-report-upload/v0.1",
        "project_id": report["project_id"],
        "package_id": report["package_id"],
        "package_checksum": report["package_checksum"],
        "report_schema_version": report["schema_version"],
        "report_id": report["report_id"],
        "report_checksum": report["report_checksum"],
        "original_report_media_type": "application/json",
        "original_report_base64": base64.b64encode(content).decode("ascii"),
        "original_report_checksum": "sha256:" + hashlib.sha256(content).hexdigest(),
        "original_report_size": len(content),
        "uploaded_at": _utc_text(now),
        "uploader_type": "local-cli",
        "client_version": "reagent-workspace-progress-recovery/0.1.0",
        "source_path_hint": f"memory/progress/reports/{report['report_id']}.json",
        "context_snapshot_metadata": None,
        "artifact_declarations": declarations,
        "envelope_checksum": None,
    }
    envelope = dict(payload)
    envelope.pop("workflow_instance_id")
    envelope.pop("artifact_declarations")
    payload["envelope_checksum"] = canonical_hash(envelope)
    return payload


def _recover_progress_backlog(
    *,
    workspace: Path,
    descriptor: dict[str, Any],
    installed: dict[str, Any],
    capsule: Path,
    manifest: dict[str, Any],
    reports: list[dict[str, Any]],
    transport: Any,
) -> int:
    """Upload only Cloud-missing reports, in exact execution-round order."""

    page = transport.workflow_instance_progress(
        descriptor["project_id"], installed["workflow_instance_id"]
    )
    accepted = _accepted_cloud_progress(
        page, descriptor=descriptor, installed=installed, manifest=manifest
    )
    if len(accepted) > len(reports):
        raise _identity("PROGRESS_HISTORY_CONFLICT", "Cloud Progress is ahead of local history")
    for report, uploaded in zip(reports, accepted):
        if (
            report["report_id"] != uploaded.get("report_id")
            or report["report_checksum"] != uploaded.get("report_checksum")
            or report["execution_round"]
            != uploaded.get("normalized_record", {}).get("execution_round")
        ):
            raise _identity("PROGRESS_HISTORY_CONFLICT", "Cloud and local Progress histories diverge")
        _store_progress_acknowledgement(
            workspace=workspace,
            descriptor=descriptor,
            installed=installed,
            manifest=manifest,
            report=report,
            receipt=_history_receipt(uploaded),
        )
    uploaded_count = 0
    for report in reports[len(accepted):]:
        if report["execution_round"] != len(accepted) + uploaded_count + 1:
            raise _identity("LOCAL_PROGRESS_GAP", "Pending Progress does not continue Cloud history")
        receipt = transport.upload_progress_report(
            descriptor["project_id"],
            installed["workflow_instance_id"],
            manifest,
            report,
            _progress_upload_envelope(
                capsule,
                installed["workflow_instance_id"],
                report,
                datetime.now(timezone.utc),
            ),
        )
        # A response alone is not continuity authority. Re-read the exact
        # Instance projection before persisting local acknowledgement.
        confirmed = _accepted_cloud_progress(
            transport.workflow_instance_progress(
                descriptor["project_id"], installed["workflow_instance_id"]
            ),
            descriptor=descriptor,
            installed=installed,
            manifest=manifest,
        )
        expected_count = len(accepted) + uploaded_count + 1
        if len(confirmed) != expected_count:
            raise _identity("CLOUD_PROGRESS_INVALID", "Cloud did not acknowledge the uploaded Progress round")
        latest = confirmed[-1]
        if (
            latest.get("report_id") != report["report_id"]
            or latest.get("report_checksum") != report["report_checksum"]
            or receipt.get("receipt_id") != latest.get("receipt_id")
        ):
            raise _identity("CLOUD_PROGRESS_INVALID", "Cloud acknowledged a different Progress Report")
        _store_progress_acknowledgement(
            workspace=workspace,
            descriptor=descriptor,
            installed=installed,
            manifest=manifest,
            report=report,
            receipt=receipt,
        )
        uploaded_count += 1
    return uploaded_count


def run_workflow(
    *,
    workspace_root: str | Path,
    workflow_instance_id: str,
    transport: Any,
    api_url: str,
    preflight_only: bool = False,
    codex_executable: str | None = None,
    consent_input: Callable[[str], str] = input,
) -> WorkflowRunResult:
    """Explicitly preflight and enter one exact installed Workflow Capsule."""

    workspace, descriptor, bootstrap = load_workspace(workspace_root)
    _match(workflow_instance_id, WORKFLOW_INSTANCE_ID, "workflow_instance_id")
    with _WorkspaceWriteLock(workspace):
        lock = _require_installed_lock(workspace, descriptor)
        _verify_locked_capsules(workspace, lock, bootstrap)
        installed = next(
            (
                item
                for item in lock["installed_capsules"]
                if item["workflow_instance_id"] == workflow_instance_id
                and item["lifecycle"] == "ACTIVE"
            ),
            None,
        )
        if installed is None:
            raise WorkspaceCLIError(
                "DEPENDENCY_UNRESOLVED",
                "The requested Workflow Capsule is not actively installed",
                EXIT_VALIDATION,
            )
        capsule = workspace / installed["relative_path"]
        _scan_capsule_for_credentials(capsule)
        command = _capsule_runner_command(capsule)
        pin = (
            installed["workflow_definition_id"],
            installed["workflow_definition_version"],
            installed["capsule_version"],
        )
        is_idea = pin in {
            ("idea-discovery-local-experimental", "0.1.0", "0.1.0"),
            ("idea-discovery-local-experimental", "0.2.0", "0.2.0"),
            ("idea-discovery-local-experimental", "0.2.0", "0.3.0"),
        }
        is_scaffold = (
            pin[0] in {
                "writing-local-experimental",
                "review-local-experimental",
                "reproduction-experiment-local-experimental",
            }
            and pin[1:] in {
                ("0.1.0", "0.1.0"), ("0.2.0", "0.2.0"),
                ("0.2.0", "0.3.0"),
                ("0.2.0", "0.4.0"),
                ("0.3.0", "0.3.0"), ("0.3.0", "0.4.0"),
                ("0.3.0", "0.5.0"),
            }
            and pin not in {
                ("writing-local-experimental", "0.3.0", "0.5.0"),
                ("review-local-experimental", "0.3.0", "0.5.0"),
            }
        )
        is_real_experiment = pin in {
            ("reproduction-experiment-local-experimental", "0.4.0", "0.6.0"),
            ("reproduction-experiment-local-experimental", "0.4.0", "0.7.0"),
        }
        is_real_writing = pin == (
            "writing-local-experimental", "0.3.0", "0.5.0"
        )
        is_real_review = pin == (
            "review-local-experimental", "0.3.0", "0.5.0"
        )
        is_writing_revision = pin == (
            "writing-local-experimental", "0.4.0", "0.6.0"
        )
        is_literature = pin[0] == WORKFLOW_ID
        manifest = _read_package_json(capsule / "package-manifest.json")
        local_reports: list[dict[str, Any]] = []
        if not preflight_only and (is_idea or is_scaffold or is_real_experiment or is_real_writing or is_real_review or is_writing_revision):
            readiness = _evaluate_local_progress_readiness(
                workspace=workspace,
                descriptor=descriptor,
                installed=installed,
                capsule=capsule,
                manifest=manifest,
            )
            if readiness.state == "INVALID":
                raise _identity(
                    "LOCAL_PROGRESS_INVALID",
                    readiness.reason or "Local Progress cannot be safely recovered",
                )
            local_reports = list(readiness.reports)
            if local_reports:
                if readiness.state != "ACKNOWLEDGED":
                    _recover_progress_backlog(
                        workspace=workspace,
                        descriptor=descriptor,
                        installed=installed,
                        capsule=capsule,
                        manifest=manifest,
                        reports=local_reports,
                        transport=transport,
                    )
                if local_reports[-1]["status"] == "COMPLETED":
                    return WorkflowRunResult(
                        status="PROGRESS_SYNCHRONIZED",
                        project_id=descriptor["project_id"],
                        workspace_id=descriptor["workspace_id"],
                        workflow_instance_id=workflow_instance_id,
                        capsule_relative_path=installed["relative_path"],
                    )
        if is_idea:
            plan = validate_materialization_plan(
                transport.materialization_plan(
                    descriptor["project_id"], workflow_instance_id
                ),
                descriptor,
            )
            if len(plan["artifacts"]) != 1:
                raise WorkspaceCLIError(
                    "DEPENDENCY_UNRESOLVED",
                    "Idea Discovery requires one explicitly bound paper library",
                    EXIT_VALIDATION,
                )
            item = plan["artifacts"][0]
            receipt_path = (
                workspace
                / MATERIALIZATION_RECEIPTS_ROOT
                / f"{item['binding_id']}.json"
            )
            if receipt_path.is_symlink() or not receipt_path.is_file():
                raise WorkspaceCLIError(
                    "DEPENDENCY_UNRESOLVED",
                    "Idea Discovery input has not been explicitly materialized",
                    EXIT_VALIDATION,
                )
            receipt = _validate_materialization_receipt(
                _read_json(receipt_path), descriptor
            )
            expected_target = (
                f"{item['target_capsule_relative_path']}/"
                f"{item['target_relative_path']}"
            )
            if any(
                receipt[field] != value
                for field, value in {
                    "consumer_workflow_instance_id": workflow_instance_id,
                    "binding_id": item["binding_id"],
                    "artifact_id": item["artifact_id"],
                    "source_checksum": item["expected_checksum"],
                    "target_checksum": item["expected_checksum"],
                    "target_relative_path": expected_target,
                }.items()
            ):
                raise WorkspaceCLIError(
                    "MATERIALIZED_ARTIFACT_DRIFT",
                    "Idea Discovery materialization receipt differs from the Cloud binding",
                    EXIT_VALIDATION,
                )
            target = workspace / expected_target
            checksum, size = _verified_regular_file(
                target,
                allowed_root=capsule,
                missing_code="ARTIFACT_BYTES_NOT_AVAILABLE",
            )
            if checksum != item["expected_checksum"] or size != item["expected_size_bytes"]:
                raise WorkspaceCLIError(
                    "MATERIALIZED_ARTIFACT_DRIFT",
                    "Idea Discovery materialized input checksum drifted",
                    EXIT_VALIDATION,
                )
            _require_nonempty_selected_library(target)
            if not preflight_only:
                _prepare_idea_output_provenance(
                    capsule=capsule,
                    artifact_id=item["artifact_id"],
                    checksum=item["expected_checksum"],
                )
            command.extend([
                "run",
                ".",
                "--workflow-instance",
                workflow_instance_id,
                "--api-url",
                api_url,
            ])
            if preflight_only:
                command.append("--preflight-only")
            if codex_executable is not None:
                command.extend(["--codex-executable", codex_executable])
        elif is_real_writing:
            _prepare_scaffold_input_provenance(
                workspace=workspace,
                descriptor=descriptor,
                capsule=capsule,
                workflow_instance_id=workflow_instance_id,
                transport=transport,
                real_writing=True,
            )
            command.extend([
                "run", ".", "--workflow-instance", workflow_instance_id,
                "--api-url", api_url,
            ])
            if preflight_only:
                command.append("--preflight-only")
            if codex_executable is not None:
                command.extend(["--codex-executable", codex_executable])
        elif is_writing_revision:
            _prepare_scaffold_input_provenance(
                workspace=workspace,
                descriptor=descriptor,
                capsule=capsule,
                workflow_instance_id=workflow_instance_id,
                transport=transport,
                writing_revision=True,
            )
            command.extend([
                "run", ".", "--workflow-instance", workflow_instance_id,
                "--api-url", api_url,
            ])
            if preflight_only:
                command.append("--preflight-only")
            if codex_executable is not None:
                command.extend(["--codex-executable", codex_executable])
        elif is_real_review:
            _prepare_scaffold_input_provenance(
                workspace=workspace,
                descriptor=descriptor,
                capsule=capsule,
                workflow_instance_id=workflow_instance_id,
                transport=transport,
                real_review=True,
            )
            command.extend([
                "run", ".", "--workflow-instance", workflow_instance_id,
                "--api-url", api_url,
            ])
            if preflight_only:
                command.append("--preflight-only")
            if codex_executable is not None:
                command.extend(["--codex-executable", codex_executable])
        elif is_real_experiment:
            _prepare_scaffold_input_provenance(
                workspace=workspace,
                descriptor=descriptor,
                capsule=capsule,
                workflow_instance_id=workflow_instance_id,
                transport=transport,
                real_experiment=True,
            )
            _prepare_real_experiment_resource(
                workspace=workspace,
                descriptor=descriptor,
                capsule=capsule,
                workflow_instance_id=workflow_instance_id,
                transport=transport,
            )
            command.extend([
                "run", ".", "--workflow-instance", workflow_instance_id,
                "--api-url", api_url,
            ])
            if preflight_only:
                command.append("--preflight-only")
            if codex_executable is not None:
                command.extend(["--codex-executable", codex_executable])
        elif is_scaffold:
            if pin in {
                ("reproduction-experiment-local-experimental", "0.3.0", "0.3.0"),
                ("reproduction-experiment-local-experimental", "0.3.0", "0.4.0"),
                ("reproduction-experiment-local-experimental", "0.3.0", "0.5.0"),
            }:
                resource_projection = _verify_bound_resources(
                    workspace=workspace,
                    descriptor=descriptor,
                    workflow_instance_id=workflow_instance_id,
                    transport=transport,
                )
                if pin[2] in {"0.4.0", "0.5.0"}:
                    _prepare_experiment_resource_provenance(
                        capsule=capsule,
                        workflow_instance_id=workflow_instance_id,
                        projection=resource_projection,
                    )
            _prepare_scaffold_input_provenance(
                workspace=workspace,
                descriptor=descriptor,
                capsule=capsule,
                workflow_instance_id=workflow_instance_id,
                transport=transport,
            )
            command.extend([
                "run", ".", "--workflow-instance", workflow_instance_id,
                "--api-url", api_url,
            ])
            if preflight_only:
                command.append("--preflight-only")
            if codex_executable is not None:
                command.extend(["--codex-executable", codex_executable])
        elif preflight_only:
            namespace = runpy.run_path(str(capsule / "validate_package.py"))
            try:
                validation = namespace["validate"](capsule, pristine=False)
            except Exception as error:
                raise _identity(
                    "LOCAL_CAPSULE_DRIFT", "Workflow Capsule preflight failed"
                ) from error
            if validation.get("valid") is not True:
                raise _identity("LOCAL_CAPSULE_DRIFT", "Workflow Capsule is invalid")
            return WorkflowRunResult(
                status="PREFLIGHT_READY",
                project_id=descriptor["project_id"],
                workspace_id=descriptor["workspace_id"],
                workflow_instance_id=workflow_instance_id,
                capsule_relative_path=installed["relative_path"],
            )
        else:
            command.extend(["run", "."])
            if is_literature:
                package_identity = {
                    "package_id": manifest["package_id"],
                    "package_checksum": manifest["package_checksum"],
                    "workflow_id": manifest["workflow_id"],
                    "workflow_version": manifest["workflow_version"],
                    "workflow_checksum": manifest["workflow_checksum"],
                }
                mode_response = _validate_literature_execution_mode(
                    transport.literature_execution_mode(
                        descriptor["project_id"], package_identity
                    ),
                    package_identity,
                )
                if mode_response["mode"] == "DEMO":
                    command.extend(["--mode", "demo"])
                else:
                    confirmation = _confirm_real_provider_disclosure(consent_input)
                    consent_response = transport.grant_real_provider_consent(
                        descriptor["project_id"],
                        package_identity,
                        confirmation=confirmation,
                    )
                    _validate_real_provider_consent(
                        consent_response,
                        project_id=descriptor["project_id"],
                        package_identity=package_identity,
                    )
                if _literature_resume_required(capsule):
                    command.append("--resume")
        environment = _capsule_child_environment()
        completed = subprocess.run(
            command,
            cwd=capsule,
            env=environment,
            check=False,
        )
        if completed.returncode != 0:
            if not preflight_only and (is_idea or is_scaffold or is_real_experiment or is_real_writing or is_real_review or is_writing_revision):
                recovered = _evaluate_local_progress_readiness(
                    workspace=workspace,
                    descriptor=descriptor,
                    installed=installed,
                    capsule=capsule,
                    manifest=manifest,
                )
                if recovered.state == "INVALID":
                    raise _identity(
                        "LOCAL_PROGRESS_INVALID",
                        recovered.reason or "Local Progress cannot be safely recovered",
                    )
                recovered_reports = list(recovered.reports)
                if len(recovered_reports) > len(local_reports):
                    _recover_progress_backlog(
                        workspace=workspace,
                        descriptor=descriptor,
                        installed=installed,
                        capsule=capsule,
                        manifest=manifest,
                        reports=recovered_reports,
                        transport=transport,
                    )
                    return WorkflowRunResult(
                        status="PROGRESS_SYNCHRONIZED",
                        project_id=descriptor["project_id"],
                        workspace_id=descriptor["workspace_id"],
                        workflow_instance_id=workflow_instance_id,
                        capsule_relative_path=installed["relative_path"],
                    )
            if is_literature:
                _record_literature_harness_stop(capsule)
            raise WorkspaceCLIError(
                "WORKFLOW_RUN_PREFLIGHT_FAILED" if preflight_only else "WORKFLOW_RUN_FAILED",
                "Workflow local Harness did not complete successfully",
                EXIT_VALIDATION,
            )
        if not preflight_only and (is_real_experiment or is_real_writing or is_real_review or is_writing_revision):
            recovered = _evaluate_local_progress_readiness(
                workspace=workspace,
                descriptor=descriptor,
                installed=installed,
                capsule=capsule,
                manifest=manifest,
            )
            if recovered.state == "INVALID" or not recovered.reports:
                raise _identity(
                    "LOCAL_PROGRESS_INVALID",
                    recovered.reason or "reviewed Workflow did not finalize exact Progress",
                )
            _recover_progress_backlog(
                workspace=workspace,
                descriptor=descriptor,
                installed=installed,
                capsule=capsule,
                manifest=manifest,
                reports=list(recovered.reports),
                transport=transport,
            )
        return WorkflowRunResult(
            status="PREFLIGHT_READY" if preflight_only else "RUN_COMPLETED",
            project_id=descriptor["project_id"],
            workspace_id=descriptor["workspace_id"],
            workflow_instance_id=workflow_instance_id,
            capsule_relative_path=installed["relative_path"],
        )


def _capsule_runner_command(capsule: Path) -> list[str]:
    """Build a launcher command interpreted exactly once from its Capsule cwd."""

    runner = capsule / "reagent_local.py"
    if runner.is_symlink() or not runner.is_file():
        raise _identity("LOCAL_CAPSULE_DRIFT", "Workflow runner is unavailable")
    return [sys.executable, runner.name]


def _require_nonempty_selected_library(path: Path) -> None:
    value = _read_json(path)
    if value.get("schema") != "selected-paper-library/v1":
        raise WorkspaceCLIError(
            "MATERIALIZED_ARTIFACT_DRIFT",
            "Idea Discovery selected Literature input has an invalid schema",
            EXIT_VALIDATION,
        )
    papers = value.get("papers")
    if not isinstance(papers, list):
        raise WorkspaceCLIError(
            "MATERIALIZED_ARTIFACT_DRIFT",
            "Idea Discovery selected Literature input is invalid",
            EXIT_VALIDATION,
        )
    if not papers:
        raise WorkspaceCLIError(
            "DEPENDENCY_UNRESOLVED",
            "The selected Literature Search result contains no included papers; "
            "Idea Discovery requires at least one selected paper",
            EXIT_VALIDATION,
        )


def _capsule_child_environment() -> dict[str, str]:
    """Build the environment shared by every untrusted Capsule child."""

    environment = dict(os.environ)
    for key in (
        "REAGENT_DATABASE_URL",
        "REAGENT_ENV_FILE",
        "REAGENT_PROXY_TOKEN",
        "REAGENT_LOCAL_SESSION_TOKEN",
        *PROVIDER_CREDENTIAL_ENV_VARS,
    ):
        environment.pop(key, None)
    return environment


def _scan_capsule_for_credentials(capsule: Path) -> None:
    """Reject credential assignments in immutable or mutable Capsule files."""
    manifest = _read_package_json(capsule / "package-manifest.json")
    declared = {
        item["relative_path"]: item
        for item in manifest.get("files", [])
        if isinstance(item, dict) and isinstance(item.get("relative_path"), str)
    }
    materialized_inputs = _declared_dynamic_input_paths(capsule, declared)
    for path in capsule.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(capsule).as_posix()
        try:
            if relative in materialized_inputs or relative.startswith("outputs/artifacts/"):
                # Exact Artifact provenance may honestly contain a local execution
                # path. Artifact bytes remain local and checksum-bound; credential
                # assignments and private keys remain prohibited.
                _reject_credentials(path.read_bytes())
            else:
                _reject_secrets(path.read_bytes())
        except WorkspaceCLIError as error:
            raise _package_error(
                error.code,
                f"{error} in {relative}",
            ) from error


def _confirm_real_provider_disclosure(
    reader: Callable[[str], str],
) -> str:
    print("Real Literature Search uses OpenAlex through the ReAgent backend.")
    print("OpenAlex is a third-party service and receives your search queries")
    print("plus standard network request metadata.")
    print("ReAgent retrieves publication metadata and available abstracts only;")
    print("it does not retrieve full paper text or PDFs.")
    print("The owner-controlled ReAgent database stores query checksums/lengths,")
    print("call/cost/rate metadata, and normalized Provider records. The complete")
    print("query plan, research memory, outputs, and Artifact bytes stay local.")
    print("This is not a private or offline search.")
    try:
        confirmation = reader(
            f"Type {REAL_PROVIDER_CONFIRMATION} to continue, or anything else to cancel: "
        ).strip()
    except (EOFError, KeyboardInterrupt) as error:
        raise WorkspaceCLIError(
            "REAL_PROVIDER_CONSENT_CANCELLED",
            "Real Literature Search was cancelled before any Provider session opened",
            EXIT_VALIDATION,
        ) from error
    if confirmation != REAL_PROVIDER_CONFIRMATION:
        raise WorkspaceCLIError(
            "REAL_PROVIDER_CONSENT_CANCELLED",
            "Real Literature Search was cancelled before any Provider session opened",
            EXIT_VALIDATION,
        )
    return confirmation


def _validate_real_provider_consent(
    document: Any,
    *,
    project_id: str,
    package_identity: dict[str, str],
) -> dict[str, Any]:
    value = _object(document, "Real Provider consent response")
    expected = {
        "project_id": project_id,
        **package_identity,
        "disclosure_version": REAL_PROVIDER_DISCLOSURE_VERSION,
        "status": "CONSENT_RECORDED",
    }
    if set(value) != set(expected) | {"expires_at"}:
        raise _identity(
            "LOCAL_CAPSULE_DRIFT", "Real Provider consent response is invalid"
        )
    if any(value[field] != expected_value for field, expected_value in expected.items()):
        raise _identity(
            "LOCAL_CAPSULE_DRIFT", "Real Provider consent identity mismatch"
        )
    _timestamp(value["expires_at"], "expires_at")
    return value


def _validate_literature_execution_mode(
    document: Any, package_identity: dict[str, str]
) -> dict[str, Any]:
    value = _object(document, "Literature execution mode response")
    expected_fields = set(package_identity) | {"mode"}
    if set(value) != expected_fields:
        raise _identity(
            "LOCAL_CAPSULE_DRIFT", "Literature execution mode response is invalid"
        )
    if any(value[field] != expected for field, expected in package_identity.items()):
        raise _identity(
            "LOCAL_CAPSULE_DRIFT", "Literature execution mode identity mismatch"
        )
    if value["mode"] not in {"NORMAL", "DEMO"}:
        raise _identity(
            "LOCAL_CAPSULE_DRIFT", "Literature execution mode is unsupported"
        )
    return value


def _validated_literature_control(capsule: Path) -> dict[str, Any]:
    """Return validator-approved local Literature continuity state.

    The installed Capsule remains the state-machine authority.  The generic
    Workspace launcher only projects its already-versioned round-control
    contract after the Capsule's immutable validator has accepted the complete
    local tree.  This keeps automatic resume from becoming a weaker alternate
    validation path.
    """

    validator_path = capsule / "validate_package.py"
    control_path = capsule / "memory/round-control.json"
    try:
        validator = runpy.run_path(str(validator_path))
        result = validator["validate"](capsule, pristine=False)
        if result.get("valid") is not True:
            raise ValueError("Capsule validator did not accept local state")
        metadata = control_path.stat(follow_symlinks=False)
        if (
            control_path.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_size > MAX_CONTROL_JSON_BYTES
        ):
            raise ValueError("round-control is not a bounded regular file")
        control = _read_package_json(control_path)
        manifest = _read_package_json(capsule / "package-manifest.json")
        if (
            control.get("schema_version")
            != "literature-search-round-control/v0.1"
            or control.get("project_id")
            != manifest.get("experimental_project_identity")
            or control.get("package_id") != manifest.get("package_id")
            or control.get("package_checksum") != manifest.get("package_checksum")
            or control.get("workflow_id") != manifest.get("workflow_id")
            or control.get("workflow_version") != manifest.get("workflow_version")
            or control.get("workflow_checksum") != manifest.get("workflow_checksum")
        ):
            raise ValueError("round-control identity mismatch")
        return control
    except WorkspaceCLIError:
        raise
    except Exception as error:
        raise _identity(
            "LOCAL_CAPSULE_DRIFT",
            "Literature Search continuity state failed Capsule validation",
        ) from error


def _literature_partial_files_exist(capsule: Path) -> bool:
    outputs = capsule / "outputs"
    operations = capsule / "memory/search/operations"
    try:
        output_files = [
            path
            for path in outputs.iterdir()
            if path.is_file() and not path.is_symlink() and path.name != "README.md"
        ]
        operation_files = [
            path
            for path in operations.glob("*.json")
            if path.is_file() and not path.is_symlink()
        ]
        plan = _read_package_json(capsule / "memory/search/query_plan.json")
    except (OSError, WorkspaceCLIError) as error:
        raise _identity(
            "LOCAL_CAPSULE_DRIFT",
            "Literature Search continuity files are unavailable",
        ) from error
    return bool(
        output_files
        or operation_files
        or plan.get("status") != "PENDING"
    )


def _literature_resume_required(
    capsule: Path, control: dict[str, Any] | None = None
) -> bool:
    control = control or _validated_literature_control(capsule)
    reports = list((capsule / "memory/progress/reports").glob("prv2-*.json"))
    receipts = list((capsule / "memory/progress/receipts").glob("*.json"))
    if reports or receipts or control["state"] == "UPLOADED":
        # The Capsule's existing upload-only/already-uploaded paths do not use
        # --resume and remain authoritative.
        return False
    effective = (
        control["last_completed_state"]
        if control["state"] in {"INTERRUPTED", "FAILED"}
        else control["state"]
    )
    return effective != "NOT_STARTED" or _literature_partial_files_exist(capsule)


def _literature_continuity_projection(
    capsule: Path,
) -> tuple[str, str] | None:
    """Map verified local state to friendly Workspace readiness/next action."""

    control = _validated_literature_control(capsule)
    state = control["state"]
    effective = (
        control["last_completed_state"]
        if state in {"INTERRUPTED", "FAILED"}
        else state
    )
    if state == "UPLOADED":
        return None
    if state == "REPORT_FINALIZED":
        return "UPLOAD_PENDING", "CONTINUE"
    if state in {"INTERRUPTED", "FAILED"}:
        return "INTERRUPTED", "RESUME"
    if effective in {"SEARCH_COMPLETED", "FINALIZED"}:
        return "FINALIZATION_PENDING", "RESUME"
    if effective == "PLAN_CONFIRMED" or _literature_partial_files_exist(capsule):
        return "IN_PROGRESS", "RESUME"
    return None


def _record_literature_harness_stop(capsule: Path) -> None:
    """Persist a bounded interruption after a failed generic Harness process.

    A child exit does not prove completion or owner consent.  It does prove the
    attached execution stopped.  Preserve the last validator-approved state and
    never infer candidate review or finalization confirmation.
    """

    control = _validated_literature_control(capsule)
    state = control["state"]
    if state in {"INTERRUPTED", "FAILED", "FINALIZED", "REPORT_FINALIZED", "UPLOADED"}:
        return
    if not _literature_resume_required(capsule, control):
        return
    stage = {
        "NOT_STARTED": "SEARCH_PLAN",
        "PLAN_CONFIRMED": "PROVIDER_SEARCH_OR_SCREENING",
        "SEARCH_COMPLETED": "POST_SEARCH_INTERACTION",
    }[state]
    updated = {
        **control,
        "state": "INTERRUPTED",
        "last_completed_state": state,
        "interrupted_stage": stage,
        "failure_code": "HARNESS_SESSION_STOPPED",
        "updated_at": _utc_text(datetime.now(timezone.utc)),
    }
    _atomic_write_json(capsule / "memory/round-control.json", updated)
    _validated_literature_control(capsule)


def _prepare_idea_output_provenance(
    *, capsule: Path, artifact_id: str, checksum: str
) -> None:
    """Expose verified input provenance without requiring receipt inspection.

    The published Idea Discovery output contract requires an exact Artifact ID,
    while the immutable materialized input intentionally contains bytes only.
    The Workspace boundary has already verified the Cloud binding, receipt, and
    bytes, so it atomically establishes the empty output envelope on first run.
    Research content remains the Harness/user's responsibility.
    """

    _match(artifact_id, ARTIFACT_ID, "artifact_id")
    _checksum(checksum, "source_checksum")
    path = capsule / "outputs/candidate_ideas.json"
    expected_source = {
        "artifact_id": artifact_id,
        "artifact_type": "selected-paper-library/v1",
        "sha256": checksum,
    }
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
            raise _filesystem(
                "WORKFLOW_OUTPUT_PROVENANCE_CONFLICT",
                "Idea Discovery output provenance path is unsafe",
            )
        value = _read_json(path)
        if (
            not isinstance(value, dict)
            or value.get("schema") != "candidate-ideas/v0.1"
            or value.get("source_artifact") != expected_source
        ):
            raise _identity(
                "WORKFLOW_OUTPUT_PROVENANCE_CONFLICT",
                "Existing Idea Discovery output refers to a different selected input",
            )
        return
    _atomic_write_json(
        path,
        {
            "schema": "candidate-ideas/v0.1",
            "source_artifact": expected_source,
            "ideas": [],
        },
    )


def _prepare_scaffold_input_provenance(
    *, workspace: Path, descriptor: dict[str, Any], capsule: Path,
    workflow_instance_id: str, transport: Any, real_experiment: bool = False,
    real_writing: bool = False, real_review: bool = False,
    writing_revision: bool = False,
) -> None:
    if sum((real_experiment, real_writing, real_review, writing_revision)) > 1:
        raise _identity("LOCAL_CAPSULE_DRIFT", "reviewed Workflow descriptor is ambiguous")
    descriptor_path = (
        "workflow/real-experiment.json" if real_experiment
        else "workflow/real-writing.json" if real_writing
        else "workflow/real-review.json" if real_review
        else "workflow/writing-revision.json" if writing_revision
        else "workflow/scaffold.json"
    )
    config = _read_json(capsule / descriptor_path)
    if (
        config.get("core_capability_maturity")
        != ("REVIEWED_CORE" if (real_experiment or real_writing or real_review or writing_revision) else "SCAFFOLD_CORE")
        or config.get("workflow_id") not in {
            "writing-local-experimental", "review-local-experimental",
            "reproduction-experiment-local-experimental",
        }
    ):
        raise _identity(
            "LOCAL_CAPSULE_DRIFT", "Scaffold Workflow maturity contract is invalid"
        )
    requirements = config.get("input_requirements")
    if not isinstance(requirements, list):
        raise _identity("LOCAL_CAPSULE_DRIFT", "Scaffold requirements are invalid")
    plan = validate_materialization_plan(
        transport.materialization_plan(descriptor["project_id"], workflow_instance_id),
        descriptor,
    )
    planned = {item["requirement_key"]: item for item in plan["artifacts"]}
    expected_keys = {item.get("requirement_key") for item in requirements}
    if set(planned) - expected_keys:
        raise _identity(
            "MATERIALIZATION_PLAN_INVALID", "Scaffold plan has an unknown requirement"
        )
    records: dict[str, dict[str, str]] = {}
    for requirement in requirements:
        key = requirement.get("requirement_key")
        item = planned.get(key)
        if item is None:
            if requirement.get("required") is True:
                raise WorkspaceCLIError(
                    "DEPENDENCY_UNRESOLVED",
                    f"Required scaffold input {key} must be explicitly bound",
                    EXIT_VALIDATION,
                )
            continue
        if (
            item["artifact_type"] != requirement.get("artifact_type")
            or item["target_relative_path"] != requirement.get("target_relative_path")
        ):
            raise _identity(
                "MATERIALIZATION_PLAN_INVALID", "Scaffold requirement contract drifted"
            )
        receipt_path = workspace / MATERIALIZATION_RECEIPTS_ROOT / f"{item['binding_id']}.json"
        if receipt_path.is_symlink() or not receipt_path.is_file():
            raise WorkspaceCLIError(
                "DEPENDENCY_UNRESOLVED",
                f"Scaffold input {key} has not been explicitly materialized",
                EXIT_VALIDATION,
            )
        receipt = _validate_materialization_receipt(_read_json(receipt_path), descriptor)
        expected_target = (
            f"{item['target_capsule_relative_path']}/{item['target_relative_path']}"
        )
        expected_receipt = {
            "consumer_workflow_instance_id": workflow_instance_id,
            "binding_id": item["binding_id"],
            "artifact_id": item["artifact_id"],
            "source_checksum": item["expected_checksum"],
            "target_checksum": item["expected_checksum"],
            "target_relative_path": expected_target,
        }
        if any(receipt[field] != value for field, value in expected_receipt.items()):
            raise WorkspaceCLIError(
                "MATERIALIZED_ARTIFACT_DRIFT",
                f"Scaffold input {key} receipt differs from the exact Cloud binding",
                EXIT_VALIDATION,
            )
        target = workspace / expected_target
        checksum, size = _verified_regular_file(
            target, allowed_root=capsule,
            missing_code="ARTIFACT_BYTES_NOT_AVAILABLE",
        )
        if checksum != item["expected_checksum"] or size != item["expected_size_bytes"]:
            raise WorkspaceCLIError(
                "MATERIALIZED_ARTIFACT_DRIFT",
                f"Scaffold input {key} checksum drifted",
                EXIT_VALIDATION,
            )
        records[key] = {
            "artifact_id": item["artifact_id"],
            "artifact_type": item["artifact_type"],
            "sha256": item["expected_checksum"],
        }
        if not (real_experiment or real_writing or real_review or writing_revision):
            records[key]["relative_path"] = item["target_relative_path"]
    _atomic_write_json(capsule / "memory/input-provenance.json", {
        "schema_version": (
            "reagent.real-experiment-input-provenance/v0.1"
            if real_experiment
            else "reagent.real-writing-input-provenance/v0.1"
            if real_writing
            else "reagent.real-review-input-provenance/v0.1"
            if real_review
            else "reagent.writing-revision-input-provenance/v0.1"
            if writing_revision
            else "reagent.scaffold-input-provenance/v0.1"
        ),
        "workflow_instance_id": workflow_instance_id,
        "artifacts": records,
    })


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python reagent_local.py",
        description=(
            "Manage one ReAgent Local Workspace. Use `workflow list` to discover "
            "what is installed and what to do next."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    bootstrap = commands.add_parser("bootstrap", help="create one Project Workspace")
    bootstrap.add_argument("target", type=Path, help="new Local Workspace directory")
    bootstrap.add_argument("--descriptor", type=Path, required=True, help="downloaded Cloud Workspace setup JSON")
    bootstrap.add_argument("--json", action="store_true")
    adopt = commands.add_parser("adopt", help="copy one legacy Literature Search Package into a Workspace")
    adopt.add_argument("legacy_package", type=Path, help="verified legacy Package directory")
    adopt.add_argument("workspace", type=Path, help="Local Workspace directory")
    adopt.add_argument("--descriptor", type=Path)
    adopt.add_argument("--json", action="store_true")
    status_parser = commands.add_parser("workspace", help="inspect Local Workspace sync state")
    status_commands = status_parser.add_subparsers(dest="workspace_command", required=True)
    status_command = status_commands.add_parser("status", help="show sync and acknowledgement status")
    status_command.add_argument("workspace", type=Path, help="Local Workspace directory")
    status_command.add_argument("--json", action="store_true")
    sync = commands.add_parser("sync", help="explicitly pull and install desired Workflow Capsules")
    sync.add_argument("workspace", type=Path, help="Local Workspace directory")
    sync.add_argument("--api-url", default="http://127.0.0.1:8000")
    sync.add_argument("--dry-run", action="store_true")
    sync.add_argument("--json", action="store_true")
    workflow = commands.add_parser("workflow", help="discover installed Workflows")
    workflow_commands = workflow.add_subparsers(dest="workflow_command", required=True)
    workflow_list_command = workflow_commands.add_parser(
        "list", help="show local readiness and an exact safe run command"
    )
    workflow_list_command.add_argument("workspace", type=Path, help="Local Workspace directory")
    workflow_list_command.add_argument("--json", action="store_true")
    artifact = commands.add_parser("artifact", help="verify and materialize typed Artifacts")
    artifact_commands = artifact.add_subparsers(dest="artifact_command", required=True)
    artifact_status_command = artifact_commands.add_parser("status")
    artifact_status_command.add_argument("workspace", type=Path, help="Local Workspace directory")
    artifact_status_command.add_argument("--json", action="store_true")
    artifact_refresh_command = artifact_commands.add_parser("refresh")
    artifact_refresh_command.add_argument("workspace", type=Path, help="Local Workspace directory")
    artifact_refresh_command.add_argument("--api-url", default="http://127.0.0.1:8000")
    artifact_refresh_command.add_argument("--json", action="store_true")
    artifact_materialize_command = artifact_commands.add_parser("materialize")
    artifact_materialize_command.add_argument("workspace", type=Path, help="Local Workspace directory")
    materialize_selector = artifact_materialize_command.add_mutually_exclusive_group(required=True)
    materialize_selector.add_argument(
        "--workflow-instance", dest="workflow_instance_id", help="exact Workflow Instance ID"
    )
    materialize_selector.add_argument(
        "--workflow", dest="workflow_definition_id",
        help="stable Workflow key; accepted only when exactly one active local instance matches",
    )
    artifact_materialize_command.add_argument("--api-url", default="http://127.0.0.1:8000")
    artifact_materialize_command.add_argument("--dry-run", action="store_true")
    artifact_materialize_command.add_argument("--json", action="store_true")
    resource = commands.add_parser("resource", help="inspect and resolve exact external Resource bindings")
    resource_commands = resource.add_subparsers(dest="resource_command", required=True)
    resource_list_command = resource_commands.add_parser("list")
    resource_list_command.add_argument("workspace", type=Path)
    resource_list_selector = resource_list_command.add_mutually_exclusive_group()
    resource_list_selector.add_argument("--workflow-instance", dest="workflow_instance_id")
    resource_list_selector.add_argument("--workflow", dest="workflow_definition_id")
    resource_list_command.add_argument("--api-url", default="http://127.0.0.1:8000")
    resource_list_command.add_argument("--json", action="store_true")
    resource_status_command = resource_commands.add_parser("status")
    resource_status_command.add_argument("workspace", type=Path)
    resource_status_command.add_argument("--json", action="store_true")
    resource_resolve_command = resource_commands.add_parser("resolve")
    resource_resolve_command.add_argument("workspace", type=Path)
    resource_resolve_selector = resource_resolve_command.add_mutually_exclusive_group(required=True)
    resource_resolve_selector.add_argument("--workflow-instance", dest="workflow_instance_id")
    resource_resolve_selector.add_argument("--workflow", dest="workflow_definition_id")
    resource_resolve_command.add_argument("--api-url", default="http://127.0.0.1:8000")
    resource_resolve_command.add_argument("--local-test-fixture-root", type=Path)
    resource_resolve_command.add_argument("--json", action="store_true")
    resource_stage_command = resource_commands.add_parser(
        "stage", help="verify and copy one owner-staged Real Experiment Package"
    )
    resource_stage_command.add_argument("workspace", type=Path)
    resource_stage_command.add_argument("source", type=Path)
    resource_stage_selector = resource_stage_command.add_mutually_exclusive_group(required=True)
    resource_stage_selector.add_argument("--workflow-instance", dest="workflow_instance_id")
    resource_stage_selector.add_argument("--workflow", dest="workflow_definition_id")
    resource_stage_command.add_argument("--api-url", default="http://127.0.0.1:8000")
    resource_stage_command.add_argument("--json", action="store_true")
    run = commands.add_parser("run", help="preflight and run one exact installed Workflow Capsule")
    run.add_argument("workspace", type=Path, help="Local Workspace directory")
    run_selector = run.add_mutually_exclusive_group(required=True)
    run_selector.add_argument("--workflow-instance", dest="workflow_instance_id", help="exact Workflow Instance ID")
    run_selector.add_argument(
        "--workflow", dest="workflow_definition_id",
        help="stable Workflow key; accepted only when exactly one active local instance matches",
    )
    run.add_argument("--api-url", default="http://127.0.0.1:8000")
    run.add_argument("--preflight-only", action="store_true")
    run.add_argument("--codex-executable")
    run.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "bootstrap":
            result = bootstrap_workspace(
                target=args.target,
                descriptor=_read_external_descriptor(args.descriptor),
            )
            json_output = args.json
        elif args.command == "adopt":
            external = (
                _read_external_descriptor(args.descriptor)
                if args.descriptor is not None
                else None
            )
            result = adopt_legacy_package(
                source=args.legacy_package,
                workspace_root=args.workspace,
                bootstrap_descriptor=external,
            )
            json_output = args.json
        elif args.command == "sync":
            result = sync_workspace(
                workspace_root=args.workspace,
                transport=HTTPWorkspaceSyncTransport(args.api_url),
                dry_run=args.dry_run,
            )
            json_output = args.json
        elif args.command == "workflow":
            result = workflow_list(args.workspace)
            json_output = args.json
        elif args.command == "artifact":
            if args.artifact_command == "status":
                result = artifact_status(args.workspace)
            elif args.artifact_command == "refresh":
                result = refresh_artifact_index(
                    workspace_root=args.workspace,
                    transport=HTTPWorkspaceSyncTransport(args.api_url),
                )
            else:
                workflow_instance_id = args.workflow_instance_id or resolve_workflow_selector(
                    args.workspace, args.workflow_definition_id
                )
                result = materialize_artifacts(
                    workspace_root=args.workspace,
                    consumer_workflow_instance_id=workflow_instance_id,
                    transport=HTTPWorkspaceSyncTransport(args.api_url),
                    dry_run=args.dry_run,
                )
            json_output = args.json
        elif args.command == "resource":
            if args.resource_command == "status":
                result = resource_status(args.workspace)
            else:
                workflow_instance_id = args.workflow_instance_id
                if workflow_instance_id is None and args.workflow_definition_id is not None:
                    workflow_instance_id = resolve_workflow_selector(
                        args.workspace, args.workflow_definition_id
                    )
                transport = HTTPWorkspaceSyncTransport(args.api_url)
                if args.resource_command == "list":
                    result = resource_list(
                        workspace_root=args.workspace,
                        transport=transport,
                        workflow_instance_id=workflow_instance_id,
                    )
                elif args.resource_command == "resolve":
                    result = resolve_resources(
                        workspace_root=args.workspace,
                        workflow_instance_id=workflow_instance_id,
                        transport=transport,
                        local_test_fixture_root=args.local_test_fixture_root,
                        allow_local_test=(
                            os.environ.get("REAGENT_CONTROLLED_RESOURCE_TEST") == "1"
                        ),
                    )
                else:
                    result = stage_experiment_package(
                        workspace_root=args.workspace,
                        workflow_instance_id=workflow_instance_id,
                        source=args.source,
                        transport=transport,
                    )
            json_output = args.json
        elif args.command == "run":
            workflow_instance_id = args.workflow_instance_id or resolve_workflow_selector(
                args.workspace, args.workflow_definition_id
            )
            result = run_workflow(
                workspace_root=args.workspace,
                workflow_instance_id=workflow_instance_id,
                transport=HTTPWorkspaceSyncTransport(args.api_url),
                api_url=args.api_url,
                preflight_only=args.preflight_only,
                codex_executable=args.codex_executable,
            )
            json_output = args.json
        else:
            result = workspace_status(args.workspace)
            json_output = args.json
        _print_result(result, json_output=json_output)
        if (
            isinstance(result, WorkspaceSyncResult)
            and result.acknowledgement_status == "ACK_PENDING"
        ):
            return EXIT_ACK_PENDING
        return EXIT_SUCCESS
    except WorkspaceCLIError as error:
        _print_human_error(args.command, error)
        return error.exit_code
    except Exception:
        _print_human_error(
            args.command,
            WorkspaceCLIError(
                "INTERNAL_FAILURE",
                "No state was declared successful",
                EXIT_INTERNAL,
            ),
        )
        return EXIT_INTERNAL


def _read_external_descriptor(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise WorkspaceCLIError(
            "WORKSPACE_BOOTSTRAP_NOT_AVAILABLE",
            "Bootstrap descriptor file is unavailable",
            EXIT_CLOUD,
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Bootstrap descriptor file is invalid") from error


def workspace_status(workspace_root: str | Path) -> dict[str, Any]:
    workspace, descriptor, _ = load_workspace(workspace_root)
    lock_path = workspace / INSTALLED_LOCK
    lock = None
    if lock_path.exists() or lock_path.is_symlink():
        lock = validate_installed_lock(_read_json(lock_path), descriptor)
    pending = _pending_acknowledgements(workspace, descriptor)
    acknowledged = (
        False if lock is None else _has_acknowledged_lock(workspace, descriptor, lock)
    )
    active = 0 if lock is None else sum(
        item["lifecycle"] == "ACTIVE" for item in lock["installed_capsules"]
    )
    retained = 0 if lock is None else sum(
        item["lifecycle"] == "RETAINED_NOT_DESIRED"
        for item in lock["installed_capsules"]
    )
    if lock is None:
        state = "BOOTSTRAPPED_NO_LOCK"
    elif pending:
        state = "ACK_PENDING"
    elif acknowledged:
        state = "ACKNOWLEDGED_CURRENT"
    else:
        state = "INSTALLED_LOCK_CURRENT"
    return {
        "schema_version": "reagent.workspace-status/v0.1",
        "status": state,
        "project_id": descriptor["project_id"],
        "workspace_id": descriptor["workspace_id"],
        "bootstrap_manifest_revision": descriptor["bootstrap_manifest_revision"],
        "installed_manifest_revision": None if lock is None else lock["manifest_revision"],
        "installed_lock_checksum": None if lock is None else lock["lock_checksum"],
        "active_capsules": active,
        "retained_capsules": retained,
        "acknowledgement_status": (
            "ACK_PENDING" if pending else "ACKNOWLEDGED" if acknowledged else "NONE"
        ),
        "sync_required": lock is None or bool(pending) or not acknowledged,
    }


def _validated_workspace_progress_acknowledgement(
    path: Path,
    *,
    descriptor: dict[str, Any],
    installed: dict[str, Any],
    manifest: dict[str, Any],
    report: dict[str, Any],
) -> bool:
    if not path.exists() and not path.is_symlink():
        return False
    if path.is_symlink() or not path.is_file():
        raise _identity("LOCAL_PROGRESS_INVALID", "Progress acknowledgement path is unsafe")
    value = _read_json(path)
    expected = {
        "schema_version": PROGRESS_RECEIPT_SCHEMA,
        "project_id": descriptor["project_id"],
        "workspace_id": descriptor["workspace_id"],
        "workflow_instance_id": installed["workflow_instance_id"],
        "package_id": manifest["package_id"],
        "package_checksum": manifest["package_checksum"],
        "execution_round": report["execution_round"],
        "report_id": report["report_id"],
        "report_checksum": report["report_checksum"],
    }
    if any(value.get(field) != expected_value for field, expected_value in expected.items()):
        raise _identity("LOCAL_PROGRESS_CONFLICT", "Progress acknowledgement identity mismatch")
    payload = dict(value)
    checksum = payload.pop("acknowledgement_checksum", None)
    if not isinstance(checksum, str) or canonical_hash(payload) != checksum:
        raise _identity("LOCAL_PROGRESS_INVALID", "Progress acknowledgement checksum is invalid")
    return True


def _local_progress_acknowledged(
    workspace: Path,
    descriptor: dict[str, Any],
    installed: dict[str, Any],
    capsule: Path,
    manifest: dict[str, Any],
    report: dict[str, Any],
) -> bool:
    acknowledgement_path = _progress_receipt_path(
        workspace, installed["workflow_instance_id"], report["report_id"]
    )
    acknowledged = _validated_workspace_progress_acknowledgement(
        acknowledgement_path,
        descriptor=descriptor,
        installed=installed,
        manifest=manifest,
        report=report,
    )
    if acknowledged:
        return True
    capsule_receipt = (
        capsule / "memory/progress/receipts" / f"{report['report_id']}.json"
    )
    if not capsule_receipt.exists() and not capsule_receipt.is_symlink():
        return False
    if capsule_receipt.is_symlink() or not capsule_receipt.is_file():
        raise _identity("LOCAL_PROGRESS_INVALID", "Capsule Progress receipt path is unsafe")
    receipt = _read_json(capsule_receipt)
    legacy_fields = {
        "schema_version", "report_id", "report_checksum", "receipt_id",
        "receipt_checksum", "validation_status", "chain_state",
        "accepted_for_projection", "idempotent_replay", "projection_checksum",
        "verified_at",
    }
    if receipt.get("schema_version") != "local-progress-upload-receipt/v0.1":
        try:
            _progress_receipt_payload(
                descriptor=descriptor, installed=installed, manifest=manifest,
                report=report, receipt=receipt,
            )
        except WorkspaceCLIError as error:
            raise _identity(
                "LOCAL_PROGRESS_INVALID", f"Capsule Progress receipt is invalid: {error}"
            ) from error
        return True
    if (
        set(receipt) != legacy_fields
        or receipt.get("report_id") != report["report_id"]
        or receipt.get("report_checksum") != report["report_checksum"]
        or receipt.get("validation_status") != "ACCEPTED"
        or receipt.get("chain_state") != "VALID_CHAIN"
        or receipt.get("accepted_for_projection") is not True
        or not isinstance(receipt.get("idempotent_replay"), bool)
        or not isinstance(receipt.get("receipt_id"), str)
        or not re.fullmatch(r"progress-receipt-[0-9a-f]{64}", receipt["receipt_id"])
    ):
        raise _identity("LOCAL_PROGRESS_INVALID", "Capsule Progress receipt is invalid")
    for field in ("receipt_checksum", "projection_checksum"):
        _checksum(receipt.get(field), field)
    _timestamp(receipt.get("verified_at"), "verified_at")
    return True


def _evaluate_local_progress_readiness(
    *,
    workspace: Path,
    descriptor: dict[str, Any],
    installed: dict[str, Any],
    capsule: Path,
    manifest: dict[str, Any],
) -> LocalProgressReadiness:
    """Return the shared fail-closed readiness result used by list and run."""

    try:
        reports = _validated_local_progress_reports(capsule, manifest)
        state = "RECOVERABLE_EXACT" if reports else "NO_LOCAL_COMPLETION"
    except WorkspaceCLIError as strict_error:
        try:
            reports = _validated_local_progress_chain(
                capsule, manifest, allow_context_mismatch=True
            )
        except WorkspaceCLIError as chain_error:
            return LocalProgressReadiness("INVALID", (), str(chain_error))
        try:
            _validate_latest_progress_outputs_exact(capsule, reports)
        except WorkspaceCLIError as output_error:
            if not _legacy_experiment_v0_4_output_and_context_drift_is_exact(
                workspace=workspace,
                descriptor=descriptor,
                installed=installed,
                capsule=capsule,
                manifest=manifest,
                reports=reports,
            ):
                return LocalProgressReadiness(
                    "INVALID", tuple(reports), str(output_error)
                )
            state = (
                "RECOVERABLE_KNOWN_LEGACY_EXPERIMENT_0_4_OUTPUT_DRIFT"
            )
        else:
            if not _legacy_scaffold_context_drift_is_exact(
                workspace=workspace,
                descriptor=descriptor,
                installed=installed,
                capsule=capsule,
                manifest=manifest,
                reports=reports,
            ):
                return LocalProgressReadiness(
                    "INVALID", tuple(reports), str(strict_error)
                )
            state = "RECOVERABLE_KNOWN_LEGACY_SCAFFOLD_DRIFT"
    if not reports:
        return LocalProgressReadiness("NO_LOCAL_COMPLETION", ())
    pin = (
        installed.get("workflow_definition_id", manifest["workflow_id"]),
        installed.get("workflow_definition_version", manifest["workflow_version"]),
        installed.get("capsule_version", manifest["package_template_version"]),
    )
    provenance_exact = True
    if pin[0] in {
        "writing-local-experimental", "review-local-experimental",
        "reproduction-experiment-local-experimental",
    } and pin not in {
        ("reproduction-experiment-local-experimental", "0.4.0", "0.6.0"),
        ("reproduction-experiment-local-experimental", "0.4.0", "0.7.0"),
        ("writing-local-experimental", "0.3.0", "0.5.0"),
        ("writing-local-experimental", "0.4.0", "0.6.0"),
        ("review-local-experimental", "0.3.0", "0.5.0"),
    }:
        try:
            provenance_exact = _scaffold_provenance_is_exact(
                workspace, descriptor, installed, capsule
            )
        except (OSError, WorkspaceCLIError):
            provenance_exact = False
    if not provenance_exact:
        return LocalProgressReadiness(
            "INVALID", tuple(reports), "Scaffold input provenance is not exact"
        )
    try:
        acknowledged = _local_progress_acknowledged(
            workspace, descriptor, installed, capsule, manifest, reports[-1]
        )
    except WorkspaceCLIError as error:
        return LocalProgressReadiness("INVALID", tuple(reports), str(error))
    return LocalProgressReadiness(
        "ACKNOWLEDGED" if acknowledged else state,
        tuple(reports),
    )


def _local_progress_summary(
    workspace: Path,
    descriptor: dict[str, Any],
    installed: dict[str, Any],
    capsule: Path,
) -> tuple[int, str | None, bool]:
    manifest = _read_package_json(capsule / "package-manifest.json")
    readiness = _evaluate_local_progress_readiness(
        workspace=workspace,
        descriptor=descriptor,
        installed=installed,
        capsule=capsule,
        manifest=manifest,
    )
    reports = readiness.reports
    return (
        len(reports),
        None if not reports else reports[-1]["status"],
        readiness.state == "ACKNOWLEDGED",
    )


def _local_input_state(
    workspace: Path,
    descriptor: dict[str, Any],
    capsule: Path,
    workflow_instance_id: str,
    required_keys: set[str],
) -> str:
    receipts_root = workspace / MATERIALIZATION_RECEIPTS_ROOT
    if not receipts_root.exists():
        return "INPUT_SELECTION_OR_MATERIALIZATION_REQUIRED"
    if receipts_root.is_symlink() or not receipts_root.is_dir():
        raise _identity("MATERIALIZED_ARTIFACT_DRIFT", "Materialization receipt directory is unsafe")
    matched: set[str] = set()
    for path in sorted(receipts_root.glob("artifact-binding-*.json")):
        if path.is_symlink() or not path.is_file():
            raise _identity("MATERIALIZED_ARTIFACT_DRIFT", "Materialization receipt is unsafe")
        receipt = _validate_materialization_receipt(_read_json(path), descriptor)
        if receipt["consumer_workflow_instance_id"] != workflow_instance_id:
            continue
        requirement_key = receipt.get("requirement_key")
        if requirement_key not in required_keys:
            continue
        matched.add(requirement_key)
        target = workspace / receipt["target_relative_path"]
        try:
            checksum, _ = _verified_regular_file(
                target,
                allowed_root=capsule,
                missing_code="ARTIFACT_BYTES_NOT_AVAILABLE",
            )
        except WorkspaceCLIError:
            return "INPUT_DRIFT"
        if checksum != receipt["target_checksum"]:
            return "INPUT_DRIFT"
    return "LOCALLY_MATERIALIZED" if matched == required_keys else "INPUT_SELECTION_OR_MATERIALIZATION_REQUIRED"


def _resource_manifest(root: Path) -> tuple[str, list[dict[str, Any]]]:
    if root.is_symlink() or not root.is_dir():
        raise _identity("RESOURCE_DRIFT", "Resolved Resource root is unsafe")
    entries: list[dict[str, Any]] = []
    case_paths: dict[str, str] = {}
    for base, directories, names in os.walk(root, followlinks=False):
        base_path = Path(base)
        for name in (*directories, *names):
            candidate = base_path / name
            mode = candidate.lstat().st_mode
            if stat.S_ISLNK(mode) or (
                not stat.S_ISDIR(mode) and not stat.S_ISREG(mode)
            ):
                raise _identity("RESOURCE_UNSAFE_FILE", "Resource contains a link or special file")
            if stat.S_ISREG(mode) and candidate.stat().st_nlink != 1:
                raise _identity("RESOURCE_UNSAFE_FILE", "Resource contains a hard-linked file")
        for name in names:
            candidate = base_path / name
            relative = candidate.relative_to(root).as_posix()
            safe = PurePosixPath(relative)
            if safe.is_absolute() or any(part in {"", ".", ".."} for part in safe.parts):
                raise _identity("RESOURCE_UNSAFE_PATH", "Resource path escapes its root")
            _record_case_path(case_paths, relative)
            content = candidate.read_bytes()
            entries.append({
                "path": relative,
                "sha256": sha256_bytes(content),
                "size_bytes": len(content),
            })
    entries.sort(key=lambda item: item["path"])
    return canonical_hash(entries), entries


def _read_resource_index(workspace: Path, descriptor: dict[str, Any]) -> dict[str, Any]:
    path = workspace / RESOURCE_INDEX
    if not path.exists() and not path.is_symlink():
        return {
            "schema_version": RESOURCE_INDEX_SCHEMA,
            "project_id": descriptor["project_id"],
            "workspace_id": descriptor["workspace_id"],
            "resources": [],
            "updated_at": None,
        }
    if path.is_symlink() or not path.is_file():
        raise _identity("RESOURCE_INDEX_INVALID", "Resource Index path is unsafe")
    value = _object(_read_json(path), "Resource Index")
    required = {
        "schema_version", "project_id", "workspace_id", "resources",
        "updated_at", "index_checksum",
    }
    _exact_fields(value, required, "Resource Index")
    if value["schema_version"] != RESOURCE_INDEX_SCHEMA or (
        value["project_id"], value["workspace_id"]
    ) != (descriptor["project_id"], descriptor["workspace_id"]):
        raise _identity("RESOURCE_INDEX_INVALID", "Resource Index identity mismatch")
    entries = value["resources"]
    if not isinstance(entries, list) or len(entries) > 10_000:
        raise _identity("RESOURCE_INDEX_INVALID", "Resource Index entries are invalid")
    ids: list[str] = []
    for raw in entries:
        item = _object(raw, "Resource Index entry")
        _exact_fields(item, {
            "resource_id", "project_id", "resource_kind", "provider", "locator",
            "exact_revision", "expected_content_checksum", "verified_content_checksum",
            "local_relative_path", "resolution_status", "verified_at",
        }, "Resource Index entry")
        _match(item["resource_id"], RESOURCE_ID, "resource_id")
        if item["project_id"] != descriptor["project_id"]:
            raise _identity("RESOURCE_INDEX_INVALID", "Resource Project identity mismatch")
        _checksum(item["expected_content_checksum"], "expected_content_checksum")
        _checksum(item["verified_content_checksum"], "verified_content_checksum")
        if item["local_relative_path"] != f"{RESOURCE_ROOT}/{item['resource_id']}":
            raise _identity("RESOURCE_INDEX_INVALID", "Resource local path is non-canonical")
        if item["resolution_status"] != "RESOLVED_VERIFIED":
            raise _identity("RESOURCE_INDEX_INVALID", "Resource Index contains an unverified entry")
        _timestamp(item["verified_at"], "verified_at")
        ids.append(item["resource_id"])
    if ids != sorted(set(ids)):
        raise _identity("RESOURCE_INDEX_INVALID", "Resource Index ordering is invalid")
    payload = dict(value)
    checksum = payload.pop("index_checksum")
    if canonical_hash(payload) != checksum:
        raise _identity("RESOURCE_INDEX_INVALID", "Resource Index checksum mismatch")
    return value


def _resource_bindings(transport: Any, descriptor: dict[str, Any], instance_id: str):
    page = _object(
        transport.list_resource_bindings(descriptor["project_id"], instance_id),
        "Resource binding page",
    )
    items = page.get("items")
    if not isinstance(items, list) or page.get("total") != len(items):
        raise _identity("RESOURCE_BINDING_INVALID", "Resource binding response is invalid")
    return items


def resource_list(
    *, workspace_root: str | Path, transport: Any, workflow_instance_id: str | None = None
) -> dict[str, Any]:
    workspace, descriptor, _ = load_workspace(workspace_root)
    resources: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = _object(
            transport.list_resources(descriptor["project_id"], offset=offset, limit=100),
            "Resource page",
        )
        batch = page.get("items")
        if not isinstance(batch, list) or len(batch) > 100:
            raise _identity("RESOURCE_REFERENCE_INVALID", "Resource page is invalid")
        resources.extend(batch)
        if len(resources) >= page.get("total", 0):
            break
        if not batch:
            raise _identity("RESOURCE_REFERENCE_INVALID", "Resource pagination made no progress")
        offset += len(batch)
    bindings = (
        _resource_bindings(transport, descriptor, workflow_instance_id)
        if workflow_instance_id else []
    )
    index = _read_resource_index(workspace, descriptor)
    indexed = {item["resource_id"]: item for item in index["resources"]}
    return {
        "schema_version": "reagent.workspace-resource-list/v0.1",
        "status": "RESOURCES_LISTED",
        "project_id": descriptor["project_id"],
        "workspace_id": descriptor["workspace_id"],
        "resources": resources,
        "bindings": bindings,
        "local_resources": list(indexed.values()),
    }


def resource_status(workspace_root: str | Path) -> dict[str, Any]:
    workspace, descriptor, _ = load_workspace(workspace_root)
    index = _read_resource_index(workspace, descriptor)
    verified = 0
    drifted = 0
    entries = []
    for item in index["resources"]:
        path = workspace / item["local_relative_path"]
        try:
            checksum, _ = _resource_manifest(path)
            status = (
                "RESOLVED_VERIFIED"
                if checksum == item["verified_content_checksum"]
                else "DRIFTED"
            )
        except WorkspaceCLIError:
            status = "DRIFTED"
        verified += status == "RESOLVED_VERIFIED"
        drifted += status == "DRIFTED"
        entries.append({"resource_id": item["resource_id"], "status": status})
    return {
        "schema_version": "reagent.workspace-resource-status/v0.1",
        "status": "RESOLVED_VERIFIED" if drifted == 0 else "DRIFTED",
        "project_id": descriptor["project_id"],
        "workspace_id": descriptor["workspace_id"],
        "resource_count": len(entries),
        "verified_count": verified,
        "drift_count": drifted,
        "resources": entries,
    }


def resolve_resources(
    *, workspace_root: str | Path, workflow_instance_id: str, transport: Any,
    local_test_fixture_root: Path | None = None, allow_local_test: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    workspace, descriptor, _ = load_workspace(workspace_root)
    _match(workflow_instance_id, WORKFLOW_INSTANCE_ID, "workflow_instance_id")
    bindings = _resource_bindings(transport, descriptor, workflow_instance_id)
    timestamp = _utc_text(now or datetime.now(timezone.utc))
    with _WorkspaceWriteLock(workspace):
        index = _read_resource_index(workspace, descriptor)
        indexed = {item["resource_id"]: item for item in index["resources"]}
        for binding in bindings:
            resource = _object(binding.get("resource"), "bound Resource")
            provider = resource.get("provider")
            if provider in {"GITHUB", "HUGGING_FACE"}:
                raise WorkspaceCLIError(
                    "RESOURCE_RESOLVER_NOT_IMPLEMENTED",
                    f"{provider.replace('_', ' ').title()} resource resolution is not implemented in this scaffold version.",
                    EXIT_VALIDATION,
                )
            if provider != "LOCAL_TEST" or not allow_local_test or local_test_fixture_root is None:
                raise WorkspaceCLIError(
                    "RESOURCE_RESOLVER_NOT_IMPLEMENTED",
                    "LOCAL_TEST resolution is restricted to controlled qualification.",
                    EXIT_VALIDATION,
                )
            fixture_root = local_test_fixture_root.resolve()
            locator = resource.get("locator")
            if not isinstance(locator, str) or not locator.startswith("fixture/"):
                raise _identity("RESOURCE_REFERENCE_INVALID", "LOCAL_TEST locator is invalid")
            source = fixture_root / locator.removeprefix("fixture/")
            _assert_within(fixture_root, source)
            marker = _object(_read_json(source / ".reagent-resource.json"), "Resource fixture marker")
            if marker != {
                "schema_version": "reagent.local-test-resource/v0.1",
                "locator": locator,
                "exact_revision": resource.get("exact_revision"),
            }:
                raise _identity("RESOURCE_REVISION_MISMATCH", "LOCAL_TEST fixture revision mismatch")
            checksum, _ = _resource_manifest(source)
            if checksum != resource.get("expected_content_checksum"):
                raise _identity("RESOURCE_CHECKSUM_MISMATCH", "Resource checksum does not match Cloud metadata")
            target_root = workspace / RESOURCE_ROOT
            target_root.mkdir(parents=True, exist_ok=True)
            if target_root.is_symlink():
                raise _identity("RESOURCE_UNSAFE_PATH", "Resource root is unsafe")
            target = target_root / resource["resource_id"]
            if target.exists():
                current, _ = _resource_manifest(target)
                if current != checksum:
                    raise _identity("RESOURCE_CONFLICT", "Existing Resource bytes conflict")
            else:
                staging = Path(tempfile.mkdtemp(prefix=f".{resource['resource_id']}.", dir=target_root))
                try:
                    for base, directories, names in os.walk(source, followlinks=False):
                        relative = Path(base).relative_to(source)
                        destination = staging / relative
                        destination.mkdir(parents=True, exist_ok=True)
                        for name in names:
                            candidate = Path(base) / name
                            if candidate.is_symlink() or candidate.stat().st_nlink != 1 or not candidate.is_file():
                                raise _identity("RESOURCE_UNSAFE_FILE", "Resource fixture contains unsafe bytes")
                            shutil.copyfile(candidate, destination / name)
                    copied, _ = _resource_manifest(staging)
                    if copied != checksum:
                        raise _identity("RESOURCE_CHECKSUM_MISMATCH", "Staged Resource checksum changed")
                    os.replace(staging, target)
                finally:
                    if staging.exists():
                        shutil.rmtree(staging)
            indexed[resource["resource_id"]] = {
                "resource_id": resource["resource_id"],
                "project_id": descriptor["project_id"],
                "resource_kind": resource["resource_kind"],
                "provider": provider,
                "locator": locator,
                "exact_revision": resource["exact_revision"],
                "expected_content_checksum": checksum,
                "verified_content_checksum": checksum,
                "local_relative_path": f"{RESOURCE_ROOT}/{resource['resource_id']}",
                "resolution_status": "RESOLVED_VERIFIED",
                "verified_at": timestamp,
            }
        payload = {
            "schema_version": RESOURCE_INDEX_SCHEMA,
            "project_id": descriptor["project_id"],
            "workspace_id": descriptor["workspace_id"],
            "resources": [indexed[key] for key in sorted(indexed)],
            "updated_at": timestamp,
        }
        _atomic_write_json(
            workspace / RESOURCE_INDEX,
            {**payload, "index_checksum": canonical_hash(payload)},
        )
    return {
        "schema_version": "reagent.workspace-resource-operation/v0.1",
        "status": "RESOLVED_VERIFIED",
        "project_id": descriptor["project_id"],
        "workspace_id": descriptor["workspace_id"],
        "workflow_instance_id": workflow_instance_id,
        "resource_count": len(bindings),
    }


def _experiment_package_manifest(source: Path) -> dict[str, Any]:
    manifest_path = source / ".reagent-experiment.json"
    value = _object(_read_json(manifest_path), "Experiment Package manifest")
    _exact_fields(value, {
        "schema_version", "entrypoint", "runtime", "runtime_version", "lock_file",
    }, "Experiment Package manifest")
    if value["schema_version"] != "reagent.experiment-package/v0.1":
        raise _identity("RESOURCE_PACKAGE_INVALID", "Experiment Package schema is invalid")
    if value["runtime"] != "PYTHON" or value["runtime_version"] != (
        f"{sys.version_info.major}.{sys.version_info.minor}"
    ):
        raise _identity(
            "RESOURCE_RUNTIME_UNUSABLE",
            "Experiment Package requires a different supported Python runtime",
        )
    for field in ("entrypoint", "lock_file"):
        relative = value[field]
        if not isinstance(relative, str):
            raise _identity("RESOURCE_PACKAGE_INVALID", "Experiment Package path is invalid")
        path = PurePosixPath(relative)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise _identity("RESOURCE_PACKAGE_INVALID", "Experiment Package path is unsafe")
        target = source.joinpath(*path.parts)
        if target.is_symlink() or not target.is_file() or target.stat().st_nlink != 1:
            raise _identity("RESOURCE_RUNTIME_UNUSABLE", "Experiment Package runtime file is unavailable")
    if PurePosixPath(value["entrypoint"]).suffix != ".py":
        raise _identity("RESOURCE_RUNTIME_UNUSABLE", "E1 supports one Python entrypoint only")
    return value


def stage_experiment_package(
    *, workspace_root: str | Path, workflow_instance_id: str,
    source: Path, transport: Any, now: datetime | None = None,
) -> dict[str, Any]:
    """Verify and copy exactly one owner-staged package; never clone or install."""

    workspace, descriptor, _ = load_workspace(workspace_root)
    _match(workflow_instance_id, WORKFLOW_INSTANCE_ID, "workflow_instance_id")
    lock = _require_installed_lock(workspace, descriptor)
    installed = next((item for item in lock["installed_capsules"] if item["workflow_instance_id"] == workflow_instance_id and item["lifecycle"] == "ACTIVE"), None)
    if installed is None or (
        installed["workflow_definition_id"],
        installed["workflow_definition_version"],
        installed["capsule_version"],
    ) not in {
        ("reproduction-experiment-local-experimental", "0.4.0", "0.6.0"),
        ("reproduction-experiment-local-experimental", "0.4.0", "0.7.0"),
    }:
        raise _identity("RESOURCE_PACKAGE_UNSUPPORTED", "Owner staging is limited to Real Experiment 0.4 Capsules 0.6/0.7")
    bindings = _resource_bindings(transport, descriptor, workflow_instance_id)
    if len(bindings) != 1 or bindings[0].get("requirement_key") != "source_repository":
        raise WorkspaceCLIError("DEPENDENCY_UNRESOLVED", "Real Experiment requires one exact source_repository binding", EXIT_VALIDATION)
    binding = bindings[0]
    resource_value = _object(binding.get("resource"), "bound Resource")
    if resource_value.get("provider") != "GITHUB" or resource_value.get("resource_kind") != "SOURCE_REPOSITORY":
        raise _identity("RESOURCE_PACKAGE_UNSUPPORTED", "Real Experiment supports one exact GitHub source reference")
    source = source.resolve(strict=True)
    package = _experiment_package_manifest(source)
    content_checksum, _ = _resource_manifest(source)
    if content_checksum != resource_value.get("expected_content_checksum") or content_checksum != binding.get("expected_content_checksum"):
        raise _identity("RESOURCE_CHECKSUM_MISMATCH", "Owner-staged bytes do not match the exact Cloud Resource checksum")
    timestamp = _utc_text(now or datetime.now(timezone.utc))
    with _WorkspaceWriteLock(workspace):
        index = _read_resource_index(workspace, descriptor)
        indexed = {item["resource_id"]: item for item in index["resources"]}
        target_root = workspace / RESOURCE_ROOT
        target_root.mkdir(parents=True, exist_ok=True)
        if target_root.is_symlink():
            raise _identity("RESOURCE_UNSAFE_PATH", "Resource root is unsafe")
        target = target_root / resource_value["resource_id"]
        if target.exists() or target.is_symlink():
            existing_checksum, _ = _resource_manifest(target)
            if existing_checksum != content_checksum:
                raise _identity("RESOURCE_CONFLICT", "Existing staged Resource bytes conflict")
        else:
            staging = Path(tempfile.mkdtemp(prefix=f".{resource_value['resource_id']}.", dir=target_root))
            try:
                for base, _directories, names in os.walk(source, followlinks=False):
                    relative = Path(base).relative_to(source)
                    destination = staging / relative
                    destination.mkdir(parents=True, exist_ok=True)
                    for name in names:
                        candidate = Path(base) / name
                        shutil.copyfile(candidate, destination / name)
                copied_checksum, _ = _resource_manifest(staging)
                if copied_checksum != content_checksum:
                    raise _identity("RESOURCE_CHECKSUM_MISMATCH", "Experiment Package changed while staging")
                os.replace(staging, target)
            finally:
                if staging.exists():
                    shutil.rmtree(staging)
        indexed[resource_value["resource_id"]] = {
            "resource_id": resource_value["resource_id"],
            "project_id": descriptor["project_id"],
            "resource_kind": resource_value["resource_kind"],
            "provider": resource_value["provider"],
            "locator": resource_value["locator"],
            "exact_revision": resource_value["exact_revision"],
            "expected_content_checksum": content_checksum,
            "verified_content_checksum": content_checksum,
            "local_relative_path": f"{RESOURCE_ROOT}/{resource_value['resource_id']}",
            "resolution_status": "RESOLVED_VERIFIED",
            "verified_at": timestamp,
        }
        payload = {"schema_version": RESOURCE_INDEX_SCHEMA, "project_id": descriptor["project_id"], "workspace_id": descriptor["workspace_id"], "resources": [indexed[key] for key in sorted(indexed)], "updated_at": timestamp}
        _atomic_write_json(workspace / RESOURCE_INDEX, {**payload, "index_checksum": canonical_hash(payload)})
    return {
        "schema_version": "reagent.workspace-resource-operation/v0.1",
        "status": "OWNER_STAGED_VERIFIED",
        "project_id": descriptor["project_id"],
        "workspace_id": descriptor["workspace_id"],
        "workflow_instance_id": workflow_instance_id,
        "resource_count": 1,
        "package": {"entrypoint": package["entrypoint"], "runtime": package["runtime"], "runtime_version": package["runtime_version"]},
    }


def _experiment_resource_projection(
    *, descriptor: dict[str, Any], workflow_instance_id: str,
    bindings: list[dict[str, Any]], indexed: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    categories = (
        ("source_repository", "SOURCE_REPOSITORY"),
        ("dataset", "DATASET"),
        ("model", "MODEL"),
        ("checkpoint", "CHECKPOINT"),
    )
    by_key = {item.get("requirement_key"): item for item in bindings}
    requirements: list[dict[str, Any]] = []
    for key, kind in categories:
        binding = by_key.get(key)
        if binding is None:
            requirements.append({
                "requirement_key": key,
                "resource_kind": kind,
                "configured": False,
                "resource_id": None,
                "provider": None,
                "display_name": None,
                "exact_revision": None,
                "resolution_status": "UNCONFIGURED",
            })
            continue
        resource = _object(binding.get("resource"), "bound Resource")
        item = indexed.get(binding.get("resource_id"))
        requirements.append({
            "requirement_key": key,
            "resource_kind": kind,
            "configured": True,
            "resource_id": binding["resource_id"],
            "provider": resource.get("provider"),
            "display_name": resource.get("display_name"),
            "exact_revision": resource.get("exact_revision"),
            "resolution_status": (
                "RESOLVED_VERIFIED" if item is not None else "UNRESOLVED"
            ),
        })
    return {
        "schema_version": "reagent.experiment-resource-provenance/v0.1",
        "workflow_instance_id": workflow_instance_id,
        "requirements": requirements,
    }


def _prepare_experiment_resource_provenance(
    *, capsule: Path, workflow_instance_id: str, projection: dict[str, Any]
) -> None:
    """Persist only the bounded, credential-free Resource status for Experiment."""

    _match(workflow_instance_id, WORKFLOW_INSTANCE_ID, "workflow_instance_id")
    if (
        projection.get("schema_version")
        != "reagent.experiment-resource-provenance/v0.1"
        or projection.get("workflow_instance_id") != workflow_instance_id
    ):
        raise _identity("RESOURCE_BINDING_INVALID", "Experiment Resource projection is invalid")
    requirements = projection.get("requirements")
    expected = (
        ("source_repository", "SOURCE_REPOSITORY"),
        ("dataset", "DATASET"),
        ("model", "MODEL"),
        ("checkpoint", "CHECKPOINT"),
    )
    if not isinstance(requirements, list) or [
        (item.get("requirement_key"), item.get("resource_kind"))
        for item in requirements if isinstance(item, dict)
    ] != list(expected):
        raise _identity("RESOURCE_BINDING_INVALID", "Experiment Resource projection is invalid")
    allowed_fields = {
        "requirement_key", "resource_kind", "configured", "resource_id",
        "provider", "display_name", "exact_revision", "resolution_status",
    }
    for item in requirements:
        if set(item) != allowed_fields or item.get("configured") not in {True, False}:
            raise _identity("RESOURCE_BINDING_INVALID", "Experiment Resource projection is invalid")
        if item["configured"] is False:
            if any(item[field] is not None for field in (
                "resource_id", "provider", "display_name", "exact_revision"
            )) or item["resolution_status"] != "UNCONFIGURED":
                raise _identity("RESOURCE_BINDING_INVALID", "Unconfigured Resource projection is invalid")
        elif item["resolution_status"] != "RESOLVED_VERIFIED":
            raise _identity("RESOURCE_UNRESOLVED", "Configured Experiment Resource is not verified")
    _atomic_write_json(capsule / "memory/resource-provenance.json", projection)


def _verify_bound_resources(
    *, workspace: Path, descriptor: dict[str, Any], workflow_instance_id: str,
    transport: Any,
) -> dict[str, Any]:
    bindings = _resource_bindings(transport, descriptor, workflow_instance_id)
    index = _read_resource_index(workspace, descriptor)
    indexed = {item["resource_id"]: item for item in index["resources"]}
    for binding in bindings:
        resource = binding.get("resource", {})
        item = indexed.get(binding.get("resource_id"))
        if item is None:
            provider = resource.get("provider")
            code = (
                "RESOURCE_RESOLVER_NOT_IMPLEMENTED"
                if provider in {"GITHUB", "HUGGING_FACE"}
                else "RESOURCE_UNRESOLVED"
            )
            raise WorkspaceCLIError(
                code,
                "A configured Resource is not resolved locally. Run the Resource resolve command.",
                EXIT_VALIDATION,
            )
        checksum, _ = _resource_manifest(workspace / item["local_relative_path"])
        if checksum != binding.get("expected_content_checksum"):
            raise _identity("RESOURCE_DRIFT", "A configured Resource changed after verification")
    return _experiment_resource_projection(
        descriptor=descriptor,
        workflow_instance_id=workflow_instance_id,
        bindings=bindings,
        indexed=indexed,
    )


def _prepare_real_experiment_resource(
    *, workspace: Path, descriptor: dict[str, Any], capsule: Path,
    workflow_instance_id: str, transport: Any,
) -> None:
    bindings = _resource_bindings(transport, descriptor, workflow_instance_id)
    if len(bindings) != 1 or bindings[0].get("requirement_key") != "source_repository":
        raise WorkspaceCLIError("DEPENDENCY_UNRESOLVED", "Real Experiment requires one exact staged package", EXIT_VALIDATION)
    binding = bindings[0]
    resource_value = _object(binding.get("resource"), "bound Resource")
    index = _read_resource_index(workspace, descriptor)
    indexed = {item["resource_id"]: item for item in index["resources"]}
    item = indexed.get(binding.get("resource_id"))
    if item is None:
        raise WorkspaceCLIError("RESOURCE_UNRESOLVED", "Run `resource stage` for the exact Real Experiment Package", EXIT_VALIDATION)
    source = workspace / item["local_relative_path"]
    checksum, _ = _resource_manifest(source)
    if checksum != binding.get("expected_content_checksum") or checksum != item["verified_content_checksum"]:
        raise _identity("RESOURCE_DRIFT", "Staged Experiment Package checksum drifted")
    package = _experiment_package_manifest(source)
    target = capsule / "inputs/experiment-package"
    if target.exists() or target.is_symlink():
        current_checksum, _ = _resource_manifest(target)
        if current_checksum != checksum:
            raise _identity("RESOURCE_CONFLICT", "Capsule already contains different Experiment Package bytes")
    else:
        staging = Path(tempfile.mkdtemp(prefix=".experiment-package.", dir=capsule / "inputs"))
        try:
            for base, _directories, names in os.walk(source, followlinks=False):
                relative = Path(base).relative_to(source)
                destination = staging / relative
                destination.mkdir(parents=True, exist_ok=True)
                for name in names:
                    shutil.copyfile(Path(base) / name, destination / name)
            copied_checksum, _ = _resource_manifest(staging)
            if copied_checksum != checksum:
                raise _identity("RESOURCE_CHECKSUM_MISMATCH", "Experiment Package changed during Capsule copy")
            os.replace(staging, target)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    manifest_path = target / ".reagent-experiment.json"
    entrypoint = target / package["entrypoint"]
    lock_file = target / package["lock_file"]
    provenance = {
        "schema_version": "reagent.real-experiment-resource-provenance/v0.1",
        "workflow_instance_id": workflow_instance_id,
        "resource_id": resource_value["resource_id"],
        "resource_kind": resource_value["resource_kind"],
        "provider": resource_value["provider"],
        "locator": resource_value["locator"],
        "exact_revision": resource_value["exact_revision"],
        "content_checksum": checksum,
        "target_relative_path": "inputs/experiment-package",
        "package": {
            "manifest_checksum": sha256_bytes(manifest_path.read_bytes()),
            "entrypoint": package["entrypoint"],
            "entrypoint_checksum": sha256_bytes(entrypoint.read_bytes()),
            "lock_file": package["lock_file"],
            "lock_checksum": sha256_bytes(lock_file.read_bytes()),
            "runtime": package["runtime"],
            "runtime_version": package["runtime_version"],
        },
    }
    _atomic_write_json(capsule / "memory/resource-provenance.json", provenance)


def workflow_list(workspace_root: str | Path) -> dict[str, Any]:
    """List installed Workflow Capsules with safe, user-oriented local readiness."""

    workspace, descriptor, bootstrap = load_workspace(workspace_root)
    lock_path = workspace / INSTALLED_LOCK
    if not lock_path.exists() and not lock_path.is_symlink():
        return {
            "schema_version": WORKFLOW_LIST_SCHEMA,
            "status": "SYNC_REQUIRED",
            "project_id": descriptor["project_id"],
            "workspace_id": descriptor["workspace_id"],
            "workflows": [],
        }
    lock = _require_installed_lock(workspace, descriptor)
    _verify_locked_capsules(workspace, lock, bootstrap)
    active_counts: dict[str, int] = {}
    all_counts: dict[str, int] = {}
    for item in lock["installed_capsules"]:
        if item["lifecycle"] == "ACTIVE":
            definition_id = item["workflow_definition_id"]
            active_counts[definition_id] = active_counts.get(definition_id, 0) + 1
        definition_id = item["workflow_definition_id"]
        all_counts[definition_id] = all_counts.get(definition_id, 0) + 1
    seen_counts: dict[str, int] = {}
    workflows: list[dict[str, Any]] = []
    for item in lock["installed_capsules"]:
        capsule = workspace / item["relative_path"]
        try:
            document = json.loads((capsule / "workflow/workflow.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise _identity("LOCAL_CAPSULE_DRIFT", "Installed Workflow metadata is invalid") from error
        if (
            not isinstance(document, dict)
            or document.get("workflow_id") != item["workflow_definition_id"]
            or document.get("workflow_version") != item["workflow_definition_version"]
            or not isinstance(document.get("workflow_type"), str)
        ):
            raise _identity("LOCAL_CAPSULE_DRIFT", "Installed Workflow metadata identity is invalid")
        manifest = _read_package_json(capsule / "package-manifest.json")
        progress_readiness = _evaluate_local_progress_readiness(
            workspace=workspace,
            descriptor=descriptor,
            installed=item,
            capsule=capsule,
            manifest=manifest,
        )
        reports = progress_readiness.reports
        report_count = len(reports)
        latest_status = None if not reports else reports[-1]["status"]
        progress_acknowledged = progress_readiness.state == "ACKNOWLEDGED"
        requirements = document.get("input_requirements", [])
        if not isinstance(requirements, list):
            raise _identity("LOCAL_CAPSULE_DRIFT", "Installed Workflow input contract is invalid")
        required_keys = {
            requirement.get("requirement_key")
            for requirement in requirements
            if isinstance(requirement, dict) and requirement.get("required", True) is True
            and isinstance(requirement.get("requirement_key"), str)
        }
        definition_id = item["workflow_definition_id"]
        continuity = (
            _literature_continuity_projection(capsule)
            if definition_id == WORKFLOW_ID and item["lifecycle"] == "ACTIVE"
            else None
        )
        seen_counts[definition_id] = seen_counts.get(definition_id, 0) + 1
        friendly_label = (
            document["workflow_type"]
            if all_counts[definition_id] == 1
            else f"{document['workflow_type']} #{seen_counts[definition_id]}"
        )
        if item["lifecycle"] != "ACTIVE":
            readiness = "RETAINED"
            next_action = "REVIEW_RESULT"
        elif progress_readiness.state == "INVALID":
            readiness = "LOCAL_PROGRESS_INVALID"
            next_action = "REPAIR_REQUIRED"
        elif (
            latest_status == "COMPLETED"
            and definition_id != WORKFLOW_ID
            and progress_readiness.state in {
                "RECOVERABLE_EXACT",
                "RECOVERABLE_KNOWN_LEGACY_SCAFFOLD_DRIFT",
                "RECOVERABLE_KNOWN_LEGACY_EXPERIMENT_0_4_OUTPUT_DRIFT",
            }
        ):
            readiness = "PROGRESS_UPLOAD_PENDING"
            next_action = "CONTINUE"
        elif latest_status == "COMPLETED":
            readiness = "COMPLETED"
            next_action = "REVIEW_RESULT"
        elif continuity is not None:
            readiness, next_action = continuity
        elif report_count:
            readiness = "IN_PROGRESS"
            next_action = "CONTINUE"
        elif required_keys:
            readiness = _local_input_state(
                workspace, descriptor, capsule, item["workflow_instance_id"], required_keys
            )
            next_action = (
                "RUN" if readiness == "LOCALLY_MATERIALIZED" else "MATERIALIZE_INPUT"
            )
        else:
            readiness = "READY"
            next_action = "RUN"
        selector = (
            item["workflow_definition_id"]
            if active_counts.get(item["workflow_definition_id"]) == 1
            and item["lifecycle"] == "ACTIVE"
            else item["workflow_instance_id"]
        )
        selector_flag = "--workflow" if selector == item["workflow_definition_id"] else "--workflow-instance"
        run_command = f"python reagent_local.py run . {selector_flag} {selector}"
        next_command = None
        if next_action in {"RUN", "CONTINUE", "RESUME"}:
            next_command = run_command
        elif next_action == "MATERIALIZE_INPUT":
            next_command = (
                "python reagent_local.py artifact materialize . "
                f"{selector_flag} {selector}"
            )
        workflows.append({
            "workflow_instance_id": item["workflow_instance_id"],
            "workflow_definition_id": item["workflow_definition_id"],
            "display_name": document["workflow_type"],
            "instance_label": friendly_label,
            "core_capability_maturity": document.get("core_capability_maturity", "REVIEWED_CORE"),
            "workflow_version": item["workflow_definition_version"],
            "capsule_version": item["capsule_version"],
            "lifecycle": item["lifecycle"],
            "local_readiness": readiness,
            "progress_report_count": report_count,
            "latest_progress_status": latest_status,
            "next_action": next_action,
            "run_command": run_command,
            "next_command": next_command,
        })
    workflows.sort(key=lambda item: (item["display_name"].casefold(), item["workflow_instance_id"]))
    return {
        "schema_version": WORKFLOW_LIST_SCHEMA,
        "status": "WORKFLOWS_LISTED",
        "project_id": descriptor["project_id"],
        "workspace_id": descriptor["workspace_id"],
        "workflows": workflows,
    }


def resolve_workflow_selector(
    workspace_root: str | Path, workflow_definition_id: str
) -> str:
    """Resolve a stable Workflow key only when it names one active local instance."""

    workspace, descriptor, _ = load_workspace(workspace_root)
    _match(workflow_definition_id, STABLE_ID, "workflow_definition_id")
    lock = _require_installed_lock(workspace, descriptor)
    matches = [
        item["workflow_instance_id"]
        for item in lock["installed_capsules"]
        if item["lifecycle"] == "ACTIVE"
        and item["workflow_definition_id"] == workflow_definition_id
    ]
    if not matches:
        raise WorkspaceCLIError(
            "WORKFLOW_SELECTOR_NOT_FOUND",
            "No active installed Workflow matches that stable key",
            EXIT_VALIDATION,
        )
    if len(matches) != 1:
        raise WorkspaceCLIError(
            "WORKFLOW_SELECTOR_AMBIGUOUS",
            "More than one active installed Workflow matches that stable key",
            EXIT_VALIDATION,
        )
    return matches[0]


def _print_result(
    result: WorkspaceOperationResult | WorkspaceSyncResult | ArtifactOperationResult | WorkflowRunResult | dict[str, Any],
    *,
    json_output: bool,
) -> None:
    value = result if isinstance(result, dict) else result.as_dict()
    if json_output:
        print(canonical_json(value))
        return
    if value.get("schema_version") == WORKFLOW_LIST_SCHEMA:
        workflows = value["workflows"]
        if not workflows:
            print("No Workflow Capsules are installed yet.")
            print("Next: run `python reagent_local.py sync .` inside this Local Workspace.")
            return
        print(f"Installed Workflows ({len(workflows)})")
        for item in workflows:
            print(f"\n{item.get('instance_label', item['display_name'])} · {item['local_readiness'].replace('_', ' ').title()}")
            print(f"  Core: {item.get('core_capability_maturity', 'REVIEWED_CORE').replace('_CORE', '').title()}")
            print(f"  Next: {item['next_action'].replace('_', ' ').title()}")
            if item["next_command"] is not None:
                print(f"  Command: {item['next_command']}")
            print(
                "  Details: "
                f"version {item['workflow_version']}, "
                f"instance …{item['workflow_instance_id'][-8:]}"
            )
        return
    if value.get("schema_version") == "reagent.workspace-resource-list/v0.1":
        print(f"Project Resource References ({len(value['resources'])})")
        for item in value["resources"]:
            print(
                f"\n{item['display_name']} · {item['resource_kind'].replace('_', ' ').title()}"
            )
            print(f"  Provider: {item['provider'].replace('_', ' ').title()}")
            print(f"  Revision: {item['exact_revision']}")
            print("  Cloud stores reference metadata only; resolve bytes locally.")
        return
    if value.get("schema_version") == "reagent.workspace-resource-status/v0.1":
        print(f"Local Resources: {value['status'].replace('_', ' ').title()}")
        print(f"Verified: {value['verified_count']} · Drifted: {value['drift_count']}")
        return
    if value.get("schema_version") == "reagent.workspace-resource-operation/v0.1":
        print(f"Local Resource resolution: {value['status'].replace('_', ' ').title()}")
        print(f"Verified Resources: {value['resource_count']}")
        return
    if value.get("schema_version") == "reagent.workspace-sync-result/v0.1":
        print(f"Local Workspace sync: {value['status'].replace('_', ' ').title()}")
        print(f"Active Workflows: {value['installed_capsules']}")
        print(f"Retained Workflows: {value['retained_capsules']}")
        if value["acknowledgement_status"] == "ACK_PENDING":
            print("Cloud confirmation: pending")
            print("Next: keep the Workspace unchanged and run the same sync command again.")
        else:
            print("Cloud confirmation: complete")
            print("Next: run `python reagent_local.py workflow list .` to see what is ready.")
        return
    if value.get("schema_version") == "reagent.workspace-status/v0.1":
        print(f"Local Workspace status: {value['status'].replace('_', ' ').title()}")
        print(f"Active Workflows: {value['active_capsules']}")
        print(f"Retained Workflows: {value['retained_capsules']}")
        print(
            "Next: run `python reagent_local.py sync .`."
            if value["sync_required"]
            else "Next: run `python reagent_local.py workflow list .`."
        )
        return
    print(f"Local Workspace operation: {value['status'].replace('_', ' ').title()}")
    revision = value.get("manifest_revision", value.get("installed_manifest_revision"))
    if revision is not None:
        print(f"Cloud configuration revision: {revision}")
    if value.get("workflow_instance_id") is not None:
        print(f"Workflow: …{value['workflow_instance_id'][-8:]}")
        print(f"Local folder: {value['capsule_relative_path']}")
    if "acknowledgement_status" in value:
        print(f"Cloud confirmation: {value['acknowledgement_status'].replace('_', ' ').title()}")
    if "artifact_count" in value:
        print(f"Verified research results: {value['artifact_count']}")
    if value.get("consumer_workflow_instance_id") is not None:
        print(f"Workflow input: …{value['consumer_workflow_instance_id'][-8:]}")
        print(f"Inputs prepared: {value['materialized_count']}")
        if value["status"] == "MATERIALIZED":
            print("Next: run `python reagent_local.py workflow list .` for the safe run command.")


_ERROR_GUIDANCE: dict[str, tuple[str, str]] = {
    "WORKSPACE_BUSY": (
        "Another Local Workspace write is still running.",
        "Wait for it to finish, then retry the same command. Do not delete the lock file.",
    ),
    "WORKSPACE_SYNC_NOT_AVAILABLE": (
        "The Cloud sync service could not be reached.",
        "Keep the Workspace unchanged, check the API connection, then retry the same sync command.",
    ),
    "CAPSULE_DOWNLOAD_FAILED": (
        "A required Workflow download did not complete or did not match its Cloud identity.",
        "No Capsule was installed. Check the local API connection and retry sync; existing Workflows remain unchanged.",
    ),
    "SYNC_MANIFEST_CONFLICT": (
        "Cloud Workflow configuration changed while this sync was being prepared.",
        "Run sync again to fetch the current configuration; do not edit Workspace JSON files.",
    ),
    "MANIFEST_REVISION_CONFLICT": (
        "Cloud Workflow configuration changed elsewhere.",
        "Refresh the Workflow Board, review the current state, then repeat the explicit action.",
    ),
    "LOCAL_ARTIFACT_DRIFT": (
        "A selected research result changed after it was indexed.",
        "Idea Discovery was not prepared. Restore the original producer output or select and bind a new result, refresh the Artifact Index, then materialize again.",
    ),
    "MATERIALIZATION_CONFLICT": (
        "The Idea Discovery input path already contains different bytes.",
        "The existing file was not overwritten. Preserve or move your file, then retry explicit materialization.",
    ),
    "MATERIALIZED_ARTIFACT_DRIFT": (
        "A previously prepared Workflow input no longer matches its receipt.",
        "The Workflow was not started. Restore the verified input or choose and materialize the input again.",
    ),
    "WORKFLOW_OUTPUT_PROVENANCE_CONFLICT": (
        "The existing Idea Discovery output refers to a different selected input.",
        "Nothing was overwritten. Review the current input selection and preserve the existing output before starting a new explicitly bound round.",
    ),
    "DEPENDENCY_UNRESOLVED": (
        "This Workflow is not ready to run locally.",
        "Open the Workflow Board to select its required input, run sync if needed, then run the displayed materialization command.",
    ),
    "INSTALLED_LOCK_MISSING": (
        "This Local Workspace has not installed its desired Workflows.",
        "Run `python reagent_local.py sync .`, then retry.",
    ),
    "WORKFLOW_SELECTOR_NOT_FOUND": (
        "No active installed Workflow matches that name.",
        "Run `python reagent_local.py workflow list .`; sync first if the Workflow was just added in Cloud.",
    ),
    "WORKFLOW_SELECTOR_AMBIGUOUS": (
        "More than one active local Workflow has that name.",
        "Run `python reagent_local.py workflow list .` and use the exact `--workflow-instance` command it displays.",
    ),
    "ARTIFACT_BYTES_NOT_AVAILABLE": (
        "The selected research result is not available at its verified local path.",
        "Restore the producer Workspace output, refresh the Artifact Index, and retry. Cloud metadata cannot restore local bytes.",
    ),
    "ARTIFACT_INDEX_INVALID": (
        "The Local Workspace research-result index is missing or invalid.",
        "Run `python reagent_local.py artifact refresh .`; do not edit the Index JSON manually.",
    ),
    "ARTIFACT_REFERENCE_NOT_FOUND": (
        "The selected Workflow input is no longer available in this Project.",
        "Return to the Workflow Board, review the available Literature Search results, and explicitly select one again.",
    ),
    "MATERIALIZATION_PLAN_INVALID": (
        "Cloud and Local Workspace input identities did not agree.",
        "Nothing was copied. Refresh the Workflow Board and local Artifact Index, then retry explicit materialization.",
    ),
    "PROGRESS_UPLOAD_FAILED": (
        "Cloud Progress acknowledgement did not complete.",
        "Keep the local Workflow and Artifact unchanged, verify the loopback backend, then retry the same printed run command. ReAgent will continue from the Cloud's latest accepted execution round without starting the Agent Harness for a locally completed result.",
    ),
    "LOCAL_PROGRESS_GAP": (
        "The local append-only Progress history is missing or mislinks an execution round.",
        "Do not edit Progress JSON or rerun research. Preserve the Workspace and report code LOCAL_PROGRESS_GAP for bounded recovery review.",
    ),
    "LOCAL_PROGRESS_BRANCHED": (
        "Two local Progress reports claim the same execution round.",
        "Nothing was uploaded. Preserve both reports and report code LOCAL_PROGRESS_BRANCHED; ReAgent will not choose one silently.",
    ),
    "PROGRESS_HISTORY_CONFLICT": (
        "Cloud and local Progress histories do not identify the same exact report chain.",
        "Nothing further was uploaded. Keep the Workspace unchanged and report code PROGRESS_HISTORY_CONFLICT for integrity review.",
    ),
    "WORKFLOW_RUN_FAILED": (
        "The Workflow launcher or local Agent Harness stopped before completing the requested round.",
        "Keep the Workflow files and inspect the terminal error. If the launcher did not start or a path/file error appeared, stop and report code WORKFLOW_RUN_FAILED to the operator instead of repeatedly retrying. If the Harness started and wrote local state, run `python reagent_local.py workflow list .`; retry only when it reports Resume and use the exact displayed command.",
    ),
    "CONTROLLED_LITERATURE_PROVIDER_UNAVAILABLE": (
        "The controlled deterministic Literature provider is unavailable.",
        "Keep the Workspace unchanged and ask the operator to restore the controlled backend fixture before retrying.",
    ),
    "OPENALEX_PROXY_UNAVAILABLE": (
        "Normal Literature Search is not enabled on this backend.",
        "Keep the Workspace unchanged. Live Provider use requires separate owner authorization and backend configuration.",
    ),
    "REAL_PROVIDER_CONSENT_CANCELLED": (
        "Real Literature Search was cancelled before a Provider session opened.",
        "No OpenAlex request was made. Run the command again only when you are ready to review and explicitly accept the disclosure.",
    ),
    "REAL_PROVIDER_CONSENT_REQUIRED": (
        "The backend did not find a current one-time owner consent for this real search.",
        "Run the same command, read the OpenAlex disclosure, and type the exact confirmation when prompted.",
    ),
    "REAL_PROVIDER_CONSENT_NOT_CONFIRMED": (
        "The backend rejected the real Provider consent confirmation.",
        "No OpenAlex request was made. Keep the Workspace unchanged and repeat the normal run only when ready to confirm.",
    ),
    "WORKSPACE_DESCRIPTOR_INVALID": (
        "This directory is not a valid ReAgent Local Workspace.",
        "Open the Project Help page and bootstrap a Workspace from its downloaded setup file. Do not repair project.json manually.",
    ),
    "LOCAL_CAPSULE_DRIFT": (
        "An installed Workflow's reviewed files no longer match its immutable contract.",
        "Preserve research outputs, inspect the reported file, and restore the original Capsule. Sync will not overwrite user research state.",
    ),
    "RESOURCE_RESOLVER_NOT_IMPLEMENTED": (
        "This Resource provider has metadata support but no network resolver yet.",
        "Keep the exact reference. GitHub and Hugging Face resolution is deferred; no network request was made.",
    ),
    "RESOURCE_UNRESOLVED": (
        "A configured Resource has not been verified into this Local Workspace.",
        "Run `python reagent_local.py resource resolve .` with the exact Workflow selector.",
    ),
    "RESOURCE_DRIFT": (
        "A locally resolved Resource no longer matches its verified checksum.",
        "Do not run the Workflow. Restore the exact Resource bytes and resolve again.",
    ),
    "INTERNAL_FAILURE": (
        "The command stopped before declaring success.",
        "No state was declared successful. Keep the Workspace unchanged, inspect the command inputs, and retry.",
    ),
}


def _print_human_error(command: str, error: WorkspaceCLIError) -> None:
    what, next_step = _ERROR_GUIDANCE.get(
        error.code,
        (str(error), "Keep the Workspace unchanged, review the command and Help page, then retry."),
    )
    print(
        "Local Workspace operation stopped.\n"
        f"What happened: {what}\n"
        f"Why it matters: {error}\n"
        f"Next: {next_step}\n"
        f"Code: {error.code}\n"
        f"Command: {command}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    raise SystemExit(main())
