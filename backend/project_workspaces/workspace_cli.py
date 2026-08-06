#!/usr/bin/env python3
"""Self-contained Project Workspace bootstrap and legacy Package adoption CLI.

This module intentionally uses only the Python standard library. Bootstrap
copies the same reviewed source to the Workspace root as ``reagent_local.py``;
the resulting Workspace therefore retains its identity/adoption commands
without depending on a checkout path. It does not implement sync, installation,
an Installed Lock, or acknowledgement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable

BOOTSTRAP_SCHEMA = "reagent.workspace-bootstrap/v0.1"
WORKSPACE_SCHEMA = "reagent.project-workspace/v0.1"
REGISTRY_SCHEMA = "reagent.workspace-capsule-registry/v0.1"
PACKAGE_SCHEMA = "workflow-package/v0.1"
DESIRED_MANIFEST_SCHEMA = "reagent.project-desired-manifest/v0.1"
WORKFLOW_ID = "literature-search-local-experimental"
WORKFLOW_VERSION = "0.3.0"
PACKAGE_TEMPLATE_ID = "literature-search-package-experimental"
CAPSULE_VERSION = "0.5.0"
TRUST_CLASSIFICATION = "TRUSTED_BUILT_IN_UNSIGNED"
LEGACY_NAMESPACE = uuid.UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966")

WORKSPACE_DESCRIPTOR = "project.json"
BOOTSTRAP_CACHE = ".reagent/bootstrap.json"
DESIRED_MANIFEST_CACHE = ".reagent/desired-manifest.json"
CAPSULE_REGISTRY = ".reagent/capsule-registry.json"

EXIT_SUCCESS = 0
EXIT_USAGE = 2
EXIT_IDENTITY = 10
EXIT_CLOUD = 20
EXIT_VALIDATION = 50
EXIT_FILESYSTEM = 60
EXIT_INTERNAL = 70

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
PROJECT_ID = re.compile(r"^project-[0-9a-f]{32}$")
WORKSPACE_ID = re.compile(r"^workspace-[0-9a-f]{32}$")
WORKFLOW_INSTANCE_ID = re.compile(r"^wfi-[0-9a-f]{32}$")
CAPSULE_ID = re.compile(r"^capsule-[0-9a-f]{32}$")
STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{1,127}$")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")
MAX_FILES = 5_000
MAX_PACKAGE_BYTES = 536_870_912
MAX_FILE_BYTES = 134_217_728

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
) -> tuple[dict[str, Any], str]:
    if root.is_symlink() or not root.is_dir():
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package root must be a real directory")
    manifest = _read_package_json(root / "package-manifest.json")
    if manifest.get("package_schema_version") != PACKAGE_SCHEMA:
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package schema is unsupported")
    if (
        manifest.get("workflow_id") != WORKFLOW_ID
        or manifest.get("workflow_version") != WORKFLOW_VERSION
        or manifest.get("package_template_id") != PACKAGE_TEMPLATE_ID
        or manifest.get("package_template_version") != CAPSULE_VERSION
    ):
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

    capsule = _select_capsule(bootstrap, manifest)
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
        if entry is None and relative not in output_paths and not relative.startswith(allowed_dynamic):
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
        "memory/context.md", "memory/round-control.json", "inputs/project.json",
        "inputs/research_request.json", "validate_package.py", "progress_report.py",
    }
    if not required_paths.issubset(declared):
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package execution contract is incomplete")
    try:
        workflow = json.loads((root / "workflow/workflow.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Workflow definition is invalid") from error
    if manifest.get("workflow_checksum") != canonical_hash(workflow):
        raise _package_error("LEGACY_PACKAGE_CHECKSUM_MISMATCH", "Legacy Workflow checksum is invalid")
    return manifest, _tree_checksum(root)


def _select_capsule(bootstrap: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    project_id = manifest.get("experimental_project_identity")
    expected_workspace = "workspace-" + str(project_id).removeprefix("project-")
    expected_instance = _legacy_instance_id(str(project_id))
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
        or not capsule["legacy_package_compatible"]
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
- `sync`, a general Capsule installer, Installed Lock, and cloud
  acknowledgement are not implemented in NIGHT-B3.
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
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _identity("WORKSPACE_DESCRIPTOR_INVALID", "Workspace metadata is invalid") from error


def _read_package_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise _package_error("LEGACY_PACKAGE_UNSUPPORTED", "Legacy Package manifest is missing")
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
        else:
            _, workspace, _ = load_workspace(args.workspace)
            result = WorkspaceOperationResult(
                status="VALID",
                project_id=workspace["project_id"],
                workspace_id=workspace["workspace_id"],
                manifest_revision=workspace["bootstrap_manifest_revision"],
            )
            json_output = args.json
        _print_result(result, json_output=json_output)
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


def _print_result(result: WorkspaceOperationResult, *, json_output: bool) -> None:
    if json_output:
        print(canonical_json(result.as_dict()))
        return
    print(f"Workspace operation: {result.status}")
    print(f"Project: {result.project_id}")
    print(f"Workspace: {result.workspace_id}")
    print(f"Bootstrap manifest revision: {result.manifest_revision}")
    if result.workflow_instance_id is not None:
        print(f"Workflow Instance: {result.workflow_instance_id}")
        print(f"Capsule: {result.capsule_relative_path}")


if __name__ == "__main__":
    raise SystemExit(main())
