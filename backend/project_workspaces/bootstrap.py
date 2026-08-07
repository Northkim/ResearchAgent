"""Deterministic cloud descriptor for local Project Workspace bootstrap."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from backend.application.errors import ApplicationCodedConflictError
from backend.local_projects import LocalProject
from backend.workflow_packages.serialization import canonical_hash, to_json_value

from .contracts import (
    CapsuleTrustClassification,
    CloudProject,
    DesiredProjectManifest,
    LegacyPackageBootstrapReference,
    ProjectManifestEntry,
    ProjectWorkflowInstance,
    WorkflowCapsuleVersion,
    WorkflowInstanceDesiredState,
    WorkspaceBootstrapDescriptor,
    WorkspaceCapsuleBootstrap,
)
from .legacy import legacy_workflow_instance_id

BOOTSTRAP_SCHEMA_VERSION = "reagent.workspace-bootstrap/v0.1"
WORKSPACE_SCHEMA_VERSION = "reagent.project-workspace/v0.1"
CLOUD_ORIGIN_ID = "reagent-local-api"


def build_workspace_bootstrap_descriptor(
    *,
    project: CloudProject,
    local_project: LocalProject,
    manifest: DesiredProjectManifest,
    entries: tuple[ProjectManifestEntry, ...],
    instances: tuple[ProjectWorkflowInstance, ...],
    capsules: Mapping[tuple[str, str], WorkflowCapsuleVersion],
) -> WorkspaceBootstrapDescriptor:
    """Validate persisted desired state and expose a checksum-bound read model."""

    document = to_json_value(manifest.manifest_json)
    if not isinstance(document, dict):
        raise _unavailable("Desired Project Manifest document is invalid")
    if (
        project.project_id != local_project.project_id
        or manifest.project_id != project.project_id
        or manifest.workspace_id != project.workspace_id
        or manifest.manifest_revision != project.current_manifest_revision
        or document.get("project_id") != project.project_id
        or document.get("workspace_id") != project.workspace_id
        or document.get("manifest_revision") != manifest.manifest_revision
        or document.get("canonical_checksum") != manifest.canonical_checksum
    ):
        raise _unavailable("Workspace bootstrap identity is inconsistent")
    checksum_payload = dict(document)
    checksum_payload.pop("canonical_checksum", None)
    if canonical_hash(checksum_payload) != manifest.canonical_checksum:
        raise _unavailable("Desired Project Manifest checksum is invalid")

    documents = document.get("workflow_instances")
    if not isinstance(documents, list):
        raise _unavailable("Desired Project Manifest Workflow list is invalid")
    documents_by_id = {
        item.get("workflow_instance_id"): item
        for item in documents
        if isinstance(item, dict)
    }
    entries_by_id = {item.workflow_instance_id: item for item in entries}
    instances_by_id = {item.workflow_instance_id: item for item in instances}
    expected_ids = set(documents_by_id)
    if (
        None in expected_ids
        or expected_ids != set(entries_by_id)
        or expected_ids != set(instances_by_id)
    ):
        raise _unavailable("Desired Project Manifest relationships are incomplete")

    capsule_descriptors: list[WorkspaceCapsuleBootstrap] = []
    for instance_id in sorted(expected_ids):
        item = documents_by_id[instance_id]
        instance = instances_by_id[instance_id]
        entry = entries_by_id[instance_id]
        if instance.project_id != project.project_id or entry.project_id != project.project_id:
            raise _unavailable("Workflow Instance is outside the Project scope")
        if (
            item.get("workflow_definition_id") != instance.workflow_definition_id
            or item.get("workflow_definition_version") != instance.workflow_version
            or item.get("capsule_id") != instance.capsule_id
            or item.get("capsule_version") != instance.capsule_version
            or item.get("desired_state") != instance.desired_state.value
        ):
            raise _unavailable("Workflow Instance pin is inconsistent")
        if instance.capsule_id is None or instance.capsule_version is None:
            raise _unavailable("Workflow Instance lacks an exact Capsule pin")
        capsule = capsules.get((instance.capsule_id, instance.capsule_version))
        if capsule is None:
            raise _unavailable("Workflow Capsule pin is unavailable")
        if (
            capsule.workflow_definition_id != instance.workflow_definition_id
            or capsule.workflow_version != instance.workflow_version
            or item.get("capsule_definition_checksum") != capsule.definition_checksum
        ):
            raise _unavailable("Workflow Capsule pin is inconsistent")
        compatibility = to_json_value(capsule.compatibility)
        if not isinstance(compatibility, dict):
            raise _unavailable("Workflow Capsule compatibility is invalid")
        package_schema = compatibility.get("package_schema_version")
        package_template = compatibility.get("package_template_id")
        trust = compatibility.get("trust_classification")
        if not all(isinstance(value, str) for value in (package_schema, package_template, trust)):
            raise _unavailable("Workflow Capsule compatibility is incomplete")
        try:
            trust_classification = CapsuleTrustClassification(trust)
        except ValueError as error:
            raise _unavailable("Workflow Capsule trust classification is invalid") from error

        legacy_package = None
        package = local_project.current_package
        if (
            package is not None
            and capsule.legacy_package_compatible
            and instance.desired_state is WorkflowInstanceDesiredState.ACTIVE
            and instance.workflow_instance_id
            == legacy_workflow_instance_id(project.project_id)
        ):
            if (
                package.workflow_id != instance.workflow_definition_id
                or package.workflow_version != instance.workflow_version
                or package.workflow_checksum != capsule.compatibility.get("workflow_checksum", package.workflow_checksum)
                or package.package_schema_version != package_schema
            ):
                raise _unavailable("Current legacy Package is incompatible with the Capsule pin")
            legacy_package = LegacyPackageBootstrapReference(
                package_id=package.package_id,
                package_schema_version=package.package_schema_version,
                package_checksum=package.package_checksum,
                manifest_checksum=package.manifest_checksum,
                zip_checksum=package.zip_checksum,
                download_path=(
                    f"/projects/{project.project_id}/packages/{package.package_id}/download"
                ),
            )
        capsule_descriptors.append(
            WorkspaceCapsuleBootstrap(
                workflow_instance_id=instance.workflow_instance_id,
                workflow_definition_id=instance.workflow_definition_id,
                workflow_definition_version=instance.workflow_version,
                capsule_id=capsule.capsule_id,
                capsule_version=capsule.capsule_version,
                capsule_definition_checksum=capsule.definition_checksum,
                desired_state=instance.desired_state,
                legacy_package_compatible=capsule.legacy_package_compatible,
                package_schema_version=package_schema,
                package_template_id=package_template,
                trust_classification=trust_classification,
                legacy_package=legacy_package,
            )
        )

    created_at = _manifest_created_at(document, manifest.created_at)
    payload = _descriptor_payload(
        project=project,
        manifest=manifest,
        desired_manifest=document,
        workflow_capsules=tuple(capsule_descriptors),
        created_at=created_at,
    )
    checksum_payload = _descriptor_json_payload(payload)
    return WorkspaceBootstrapDescriptor(
        **payload,
        descriptor_checksum=canonical_hash(checksum_payload),
    )


def workspace_bootstrap_document(value: WorkspaceBootstrapDescriptor) -> dict[str, Any]:
    payload = {
        "schema_version": value.schema_version,
        "workspace_schema_version": value.workspace_schema_version,
        "project_id": value.project_id,
        "workspace_id": value.workspace_id,
        "cloud_origin_id": value.cloud_origin_id,
        "project_api_path": value.project_api_path,
        "workspace_lifecycle": value.workspace_lifecycle,
        "bootstrap_manifest_revision": value.bootstrap_manifest_revision,
        "desired_manifest_checksum": value.desired_manifest_checksum,
        "desired_manifest": to_json_value(value.desired_manifest),
        "workflow_capsules": [
            _capsule_document(item) for item in value.workflow_capsules
        ],
        "created_at": value.created_at.isoformat().replace("+00:00", "Z"),
    }
    return {**payload, "descriptor_checksum": value.descriptor_checksum}


def _descriptor_payload(
    *,
    project: CloudProject,
    manifest: DesiredProjectManifest,
    desired_manifest: dict[str, Any],
    workflow_capsules: tuple[WorkspaceCapsuleBootstrap, ...],
    created_at: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "workspace_schema_version": WORKSPACE_SCHEMA_VERSION,
        "project_id": project.project_id,
        "workspace_id": project.workspace_id,
        "cloud_origin_id": CLOUD_ORIGIN_ID,
        "project_api_path": f"/projects/{project.project_id}",
        "workspace_lifecycle": "ACTIVE",
        "bootstrap_manifest_revision": manifest.manifest_revision,
        "desired_manifest_checksum": manifest.canonical_checksum,
        "desired_manifest": desired_manifest,
        "workflow_capsules": tuple(workflow_capsules),
        "created_at": created_at,
    }


def _descriptor_json_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": payload["schema_version"],
        "workspace_schema_version": payload["workspace_schema_version"],
        "project_id": payload["project_id"],
        "workspace_id": payload["workspace_id"],
        "cloud_origin_id": payload["cloud_origin_id"],
        "project_api_path": payload["project_api_path"],
        "workspace_lifecycle": payload["workspace_lifecycle"],
        "bootstrap_manifest_revision": payload["bootstrap_manifest_revision"],
        "desired_manifest_checksum": payload["desired_manifest_checksum"],
        "desired_manifest": payload["desired_manifest"],
        "workflow_capsules": [
            _capsule_document(item) for item in payload["workflow_capsules"]
        ],
        "created_at": payload["created_at"].isoformat().replace("+00:00", "Z"),
    }


def _capsule_document(value: WorkspaceCapsuleBootstrap) -> dict[str, Any]:
    package = value.legacy_package
    return {
        "workflow_instance_id": value.workflow_instance_id,
        "workflow_definition_id": value.workflow_definition_id,
        "workflow_definition_version": value.workflow_definition_version,
        "capsule_id": value.capsule_id,
        "capsule_version": value.capsule_version,
        "capsule_definition_checksum": value.capsule_definition_checksum,
        "desired_state": value.desired_state.value,
        "legacy_package_compatible": value.legacy_package_compatible,
        "package_schema_version": value.package_schema_version,
        "package_template_id": value.package_template_id,
        "trust_classification": value.trust_classification.value,
        "legacy_package": (
            {
                "package_id": package.package_id,
                "package_schema_version": package.package_schema_version,
                "package_checksum": package.package_checksum,
                "manifest_checksum": package.manifest_checksum,
                "zip_checksum": package.zip_checksum,
                "download_path": package.download_path,
            }
            if package is not None
            else None
        ),
    }


def _manifest_created_at(document: dict[str, Any], fallback: datetime) -> datetime:
    value = document.get("created_at")
    if not isinstance(value, str):
        return fallback
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise _unavailable("Desired Project Manifest timestamp is invalid") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise _unavailable("Desired Project Manifest timestamp lacks a timezone")
    return parsed


def _unavailable(message: str) -> ApplicationCodedConflictError:
    return ApplicationCodedConflictError(
        message,
        code="WORKSPACE_BOOTSTRAP_NOT_AVAILABLE",
    )
