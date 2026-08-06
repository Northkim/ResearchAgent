"""Canonical Desired Project Manifest construction shared by migration/runtime."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid5

from backend.workflow_packages.serialization import canonical_hash

from .contracts import (
    CloudProject,
    DesiredProjectManifest,
    ManifestDesiredAction,
    ManifestEntryKind,
    ProjectManifestEntry,
    ProjectWorkflowInstance,
    WorkflowCapsuleVersion,
)
from .legacy import LEGACY_WORKFLOW_INSTANCE_NAMESPACE

SCHEMA_VERSION = "reagent.project-desired-manifest/v0.1"
_CREATED_BY = "reagent-system"


def mutation_idempotency_key(
    *, project_id: str, revision: int, operation_key: str
) -> str:
    name = (
        "project-manifest-mutation/v1|"
        f"project={project_id}|revision={revision}|operation={operation_key}"
    )
    return str(uuid5(LEGACY_WORKFLOW_INSTANCE_NAMESPACE, name))


def build_desired_manifest(
    *,
    project: CloudProject,
    instances: tuple[ProjectWorkflowInstance, ...],
    capsules: dict[tuple[str, str], WorkflowCapsuleVersion],
    revision: int,
    base_revision: int,
    idempotency_key: str,
    now: datetime,
) -> tuple[DesiredProjectManifest, tuple[ProjectManifestEntry, ...]]:
    """Build one full, immutable desired-state snapshot and its typed index."""

    timestamp = _utc(now)
    instance_documents: list[dict[str, object]] = []
    entries: list[ProjectManifestEntry] = []
    for instance in sorted(instances, key=lambda value: value.workflow_instance_id):
        capsule_checksum = None
        if instance.capsule_id is not None and instance.capsule_version is not None:
            capsule = capsules.get((instance.capsule_id, instance.capsule_version))
            if capsule is None:
                raise ValueError("Workflow Instance references an unavailable Capsule Version")
            capsule_checksum = capsule.definition_checksum
        document = {
            "workflow_instance_id": instance.workflow_instance_id,
            "workflow_definition_id": instance.workflow_definition_id,
            "workflow_definition_version": instance.workflow_version,
            "capsule_id": instance.capsule_id,
            "capsule_version": instance.capsule_version,
            "capsule_definition_checksum": capsule_checksum,
            "desired_state": instance.desired_state.value,
        }
        instance_documents.append(document)
        action = (
            ManifestDesiredAction.ENSURE_PRESENT
            if instance.desired_state.value == "ACTIVE"
            else ManifestDesiredAction.RETIRE
        )
        entry_payload = {
            "schema_version": "reagent.project-manifest-entry/v0.1",
            "project_id": project.project_id,
            "manifest_revision": revision,
            "entry_kind": ManifestEntryKind.WORKFLOW_INSTANCE.value,
            "workflow_instance_id": instance.workflow_instance_id,
            "desired_action": action.value,
            "workflow_definition_id": instance.workflow_definition_id,
            "workflow_definition_version": instance.workflow_version,
            "capsule_id": instance.capsule_id,
            "capsule_version": instance.capsule_version,
            "capsule_definition_checksum": capsule_checksum,
        }
        entry_uuid = uuid5(
            UUID(idempotency_key),
            f"workflow-instance-entry/v1|instance={instance.workflow_instance_id}",
        )
        entries.append(
            ProjectManifestEntry(
                entry_id="entry-" + entry_uuid.hex,
                project_id=project.project_id,
                manifest_revision=revision,
                entry_kind=ManifestEntryKind.WORKFLOW_INSTANCE,
                workflow_instance_id=instance.workflow_instance_id,
                desired_action=action,
                entry_checksum=canonical_hash(entry_payload),
                created_at=timestamp,
            )
        )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project.project_id,
        "workspace_id": project.workspace_id,
        "manifest_revision": revision,
        "base_revision": base_revision,
        "workflow_instances": instance_documents,
        "skill_pins": [],
        "artifact_requirements": [],
        "resource_bindings": [],
        "compatibility": {
            "workspace_schema": "reagent.project-workspace/v0.1",
            "minimum_cli_version": "0.1.0",
        },
        "created_at": timestamp.isoformat().replace("+00:00", "Z"),
    }
    checksum = canonical_hash(payload)
    stored = {**payload, "canonical_checksum": checksum}
    return (
        DesiredProjectManifest(
            project_id=project.project_id,
            manifest_revision=revision,
            workspace_id=project.workspace_id,
            base_revision=base_revision,
            schema_version=SCHEMA_VERSION,
            canonical_checksum=checksum,
            manifest_json=stored,
            created_by_subject_id=_CREATED_BY,
            idempotency_key=idempotency_key,
            created_at=timestamp,
            updated_at=timestamp,
        ),
        tuple(entries),
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("manifest timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)
