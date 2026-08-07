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
MATERIALIZATION_RECEIPTS_ROOT = ".reagent/receipts/materializations"

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
STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{1,127}$")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")
MAX_FILES = 5_000
MAX_PACKAGE_BYTES = 536_870_912
MAX_FILE_BYTES = 134_217_728
MAX_CONTROL_JSON_BYTES = 2_097_152

_SECRET_PATTERNS = (
    re.compile(b"sk-" + rb"ant-[A-Za-z0-9_-]{8,}"),
    re.compile(b"sk-" + rb"proj-[A-Za-z0-9_-]{8,}"),
    re.compile(b"-----BEGIN " + rb"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"(?:ANTHROPIC|OPENAI)_API_KEY\s*=[^\s<]+"),
    re.compile(b"postgres" + rb"(?:ql)?://[^\s/:]+:[^\s/@]+@"),
    re.compile(b"/" + b"Users/"),
    re.compile(b"/" + b"Volumes/"),
    re.compile(rb"[A-Za-z]:\\\\"),
)

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
    allowed_dynamic = (
        "memory/progress/reports/",
        "memory/progress/receipts/",
        "memory/search/operations/",
        "outputs/artifacts/selected-paper-library/",
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
        _reject_secrets(content)
        if path.name == ".DS_Store":
            if len(content) > 1_048_576:
                raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "macOS metadata exceeds the safe bound")
            continue
        entry = declared.get(relative)
        if (
            entry is None
            and relative not in output_paths
            and relative != "inputs/selected-paper-library.json"
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
        manifest, _ = _validate_legacy_package(
            destination,
            synthetic,
            expected_instance_id=item["workflow_instance_id"],
            require_legacy_compatibility=False,
        )
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


def run_workflow(
    *,
    workspace_root: str | Path,
    workflow_instance_id: str,
    transport: Any,
    api_url: str,
    preflight_only: bool = False,
    codex_executable: str | None = None,
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
        runner = capsule / "reagent_local.py"
        if runner.is_symlink() or not runner.is_file():
            raise _identity("LOCAL_CAPSULE_DRIFT", "Workflow runner is unavailable")
        pin = (
            installed["workflow_definition_id"],
            installed["workflow_definition_version"],
            installed["capsule_version"],
        )
        is_idea = pin == (
            "idea-discovery-local-experimental",
            "0.1.0",
            "0.1.0",
        )
        command = [sys.executable, str(runner)]
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
        environment = dict(os.environ)
        environment.pop("REAGENT_DATABASE_URL", None)
        completed = subprocess.run(
            command,
            cwd=capsule,
            env=environment,
            check=False,
        )
        if completed.returncode != 0:
            raise WorkspaceCLIError(
                "WORKFLOW_RUN_PREFLIGHT_FAILED" if preflight_only else "WORKFLOW_RUN_FAILED",
                "Workflow local Harness did not complete successfully",
                EXIT_VALIDATION,
            )
        return WorkflowRunResult(
            status="PREFLIGHT_READY" if preflight_only else "RUN_COMPLETED",
            project_id=descriptor["project_id"],
            workspace_id=descriptor["workspace_id"],
            workflow_instance_id=workflow_instance_id,
            capsule_relative_path=installed["relative_path"],
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python reagent_local.py",
        description="Bootstrap a Project Workspace or adopt one verified legacy Package.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    bootstrap = commands.add_parser("bootstrap", help="create one Project Workspace")
    bootstrap.add_argument("target", type=Path)
    bootstrap.add_argument("--descriptor", type=Path, required=True)
    bootstrap.add_argument("--json", action="store_true")
    adopt = commands.add_parser("adopt", help="copy one legacy Literature Search Package into a Workspace")
    adopt.add_argument("legacy_package", type=Path)
    adopt.add_argument("workspace", type=Path)
    adopt.add_argument("--descriptor", type=Path)
    adopt.add_argument("--json", action="store_true")
    status_parser = commands.add_parser("workspace", help="inspect Workspace identity")
    status_commands = status_parser.add_subparsers(dest="workspace_command", required=True)
    status_command = status_commands.add_parser("status")
    status_command.add_argument("workspace", type=Path)
    status_command.add_argument("--json", action="store_true")
    sync = commands.add_parser("sync", help="explicitly pull and install desired Workflow Capsules")
    sync.add_argument("workspace", type=Path)
    sync.add_argument("--api-url", default="http://127.0.0.1:8000")
    sync.add_argument("--dry-run", action="store_true")
    sync.add_argument("--json", action="store_true")
    artifact = commands.add_parser("artifact", help="verify and materialize typed Artifacts")
    artifact_commands = artifact.add_subparsers(dest="artifact_command", required=True)
    artifact_status_command = artifact_commands.add_parser("status")
    artifact_status_command.add_argument("workspace", type=Path)
    artifact_status_command.add_argument("--json", action="store_true")
    artifact_refresh_command = artifact_commands.add_parser("refresh")
    artifact_refresh_command.add_argument("workspace", type=Path)
    artifact_refresh_command.add_argument("--api-url", default="http://127.0.0.1:8000")
    artifact_refresh_command.add_argument("--json", action="store_true")
    artifact_materialize_command = artifact_commands.add_parser("materialize")
    artifact_materialize_command.add_argument("workspace", type=Path)
    artifact_materialize_command.add_argument(
        "--workflow-instance", required=True, dest="workflow_instance_id"
    )
    artifact_materialize_command.add_argument("--api-url", default="http://127.0.0.1:8000")
    artifact_materialize_command.add_argument("--dry-run", action="store_true")
    artifact_materialize_command.add_argument("--json", action="store_true")
    run = commands.add_parser("run", help="preflight and run one exact installed Workflow Capsule")
    run.add_argument("workspace", type=Path)
    run.add_argument("--workflow-instance", required=True, dest="workflow_instance_id")
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
        elif args.command == "artifact":
            if args.artifact_command == "status":
                result = artifact_status(args.workspace)
            elif args.artifact_command == "refresh":
                result = refresh_artifact_index(
                    workspace_root=args.workspace,
                    transport=HTTPWorkspaceSyncTransport(args.api_url),
                )
            else:
                result = materialize_artifacts(
                    workspace_root=args.workspace,
                    consumer_workflow_instance_id=args.workflow_instance_id,
                    transport=HTTPWorkspaceSyncTransport(args.api_url),
                    dry_run=args.dry_run,
                )
            json_output = args.json
        elif args.command == "run":
            result = run_workflow(
                workspace_root=args.workspace,
                workflow_instance_id=args.workflow_instance_id,
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
        print(
            f"Workspace operation failed\nstage = {args.command.upper()}\n"
            f"code = {error.code}\naction = {error}",
            file=sys.stderr,
        )
        return error.exit_code
    except Exception:
        print(
            f"Workspace operation failed\nstage = {args.command.upper()}\n"
            "code = INTERNAL_FAILURE\naction = no state was declared successful; inspect inputs and retry",
            file=sys.stderr,
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


def _print_result(
    result: WorkspaceOperationResult | WorkspaceSyncResult | ArtifactOperationResult | WorkflowRunResult | dict[str, Any],
    *,
    json_output: bool,
) -> None:
    value = result if isinstance(result, dict) else result.as_dict()
    if json_output:
        print(canonical_json(value))
        return
    print(f"Workspace operation: {value['status']}")
    print(f"Project: {value['project_id']}")
    print(f"Workspace: {value['workspace_id']}")
    revision = value.get("manifest_revision", value.get("installed_manifest_revision"))
    print(f"Manifest revision: {revision if revision is not None else 'not installed'}")
    if value.get("workflow_instance_id") is not None:
        print(f"Workflow Instance: {value['workflow_instance_id']}")
        print(f"Capsule: {value['capsule_relative_path']}")
    if "acknowledgement_status" in value:
        print(f"Acknowledgement: {value['acknowledgement_status']}")
    if "artifact_count" in value:
        print(f"Artifacts: {value['artifact_count']}")
    if value.get("consumer_workflow_instance_id") is not None:
        print(f"Consumer Workflow Instance: {value['consumer_workflow_instance_id']}")
        print(f"Materialized: {value['materialized_count']}")


if __name__ == "__main__":
    raise SystemExit(main())
