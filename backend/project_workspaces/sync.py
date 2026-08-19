"""Cloud-side Capsule acquisition, sync planning, and installation reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID, uuid5

from backend.application.errors import (
    ApplicationCodedConflictError,
    ApplicationCodedNotFoundError,
    ApplicationCodedUnavailableError,
    ApplicationCodedValidationError,
)
from backend.local_projects import LocalProject
from backend.persistence.ports import DuplicateEntityError, UnitOfWork
from backend.workflow_packages import build_literature_search_package
from backend.workflow_packages.production_workflows import (
    IDEA_DISCOVERY_WORKFLOW_ID,
    IDEA_DISCOVERY_WORKFLOW_VERSION,
    IDEA_DISCOVERY_V0_2_WORKFLOW_VERSION,
    IDEA_DISCOVERY_V0_3_CAPSULE_VERSION,
    IDEA_DISCOVERY_V0_3_WORKFLOW_VERSION,
    IDEA_DISCOVERY_V0_4_CAPSULE_VERSION,
    IDEA_DISCOVERY_V0_4_WORKFLOW_VERSION,
    IDEA_DISCOVERY_V0_5_CAPSULE_VERSION,
    EXPERIMENT_WORKFLOW_ID,
    EXPERIMENT_INTERACTIVE_CAPSULE_VERSION,
    EXPERIMENT_COMPLETION_CAPSULE_VERSION,
    EXPERIMENT_RESOURCE_CAPSULE_VERSION,
    EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
    REAL_EXPERIMENT_BUGFIX_CAPSULE_VERSION,
    PREPARED_EXPERIMENT_CAPSULE_VERSION,
    PREPARED_EXPERIMENT_WORKFLOW_VERSION,
    REAL_EXPERIMENT_CAPSULE_VERSION,
    REAL_EXPERIMENT_WORKFLOW_VERSION,
    REAL_WRITING_CAPSULE_VERSION,
    REAL_WRITING_WORKFLOW_VERSION,
    REAL_REVIEW_CAPSULE_VERSION,
    REAL_REVIEW_WORKFLOW_VERSION,
    WRITING_REVISION_CAPSULE_VERSION,
    WRITING_REVISION_WORKFLOW_VERSION,
    REVIEW_WORKFLOW_ID,
    SCAFFOLD_CAPSULE_VERSION,
    SCAFFOLD_INTERACTIVE_CAPSULE_VERSION,
    SCAFFOLD_COMPLETION_CAPSULE_VERSION,
    SCAFFOLD_WORKFLOW_VERSION,
    SCAFFOLD_SKILL_BACKED_CAPSULE_VERSION,
    SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
    WRITING_WORKFLOW_ID,
    LITERATURE_SEARCH_WORKFLOW_VERSION as PRODUCTION_LITERATURE_SEARCH_VERSION,
    LITERATURE_SEARCH_V0_5_WORKFLOW_VERSION,
    LITERATURE_SEARCH_V0_7_CAPSULE_VERSION,
    build_idea_discovery_package,
    build_idea_discovery_v0_2_package,
    build_idea_discovery_v0_3_package,
    build_idea_discovery_v0_4_package,
    build_idea_discovery_v0_5_package,
    build_literature_search_v0_6_package,
    build_literature_search_v0_7_package,
    build_writing_scaffold_package,
    build_review_scaffold_package,
    build_experiment_scaffold_package,
    build_writing_scaffold_v0_2_package,
    build_review_scaffold_v0_2_package,
    build_writing_scaffold_v0_3_package,
    build_review_scaffold_v0_3_package,
    build_writing_scaffold_v0_4_package,
    build_review_scaffold_v0_4_package,
    build_experiment_scaffold_v0_2_package,
    build_experiment_scaffold_v0_3_package,
    build_experiment_scaffold_v0_4_package,
    build_experiment_scaffold_v0_5_package,
    build_real_experiment_v0_6_package,
    build_real_experiment_v0_7_package,
    build_prepared_experiment_v0_8_package,
    build_real_writing_v0_5_package,
    build_real_review_v0_5_package,
    build_writing_revision_v0_6_package,
)
from backend.workflow_packages.serialization import canonical_hash, sha256_bytes, to_json_value
from backend.workflow_packages.generic_experiment_publication import (
    GENERIC_EXPERIMENT_CAPSULE_VERSION,
    GENERIC_EXPERIMENT_WORKFLOW_VERSION,
    build_generic_experiment_v0_9_package,
)
from backend.workflow_packages.generic_experiment_v5_publication import (
    GENERIC_EXPERIMENT_V5_CAPSULE_VERSION,
    GENERIC_EXPERIMENT_V5_WORKFLOW_VERSION,
    build_generic_experiment_v0_10_package,
)
from backend.workflow_packages.generic_harness_publication import (
    GENERIC_HARNESS_CAPSULE_VERSION,
    GENERIC_HARNESS_WORKFLOW_VERSION,
    build_generic_harness_v0_11_package,
)
from backend.workflow_packages.forward_downstream_publication import (
    INITIAL_WRITING_CAPSULE_VERSION as FORWARD_WRITING_CAPSULE_VERSION,
    INITIAL_WRITING_VERSION as FORWARD_WRITING_VERSION,
    REVIEW_CAPSULE_VERSION as FORWARD_REVIEW_CAPSULE_VERSION,
    REVIEW_VERSION as FORWARD_REVIEW_VERSION,
    WRITING_REVISION_CAPSULE_VERSION as FORWARD_REVISION_V0_8_CAPSULE_VERSION,
    WRITING_REVISION_VERSION as FORWARD_REVISION_V0_8_VERSION,
    build_initial_writing_v0_7_package,
    build_review_v0_6_package,
    build_writing_revision_v0_8_package,
)
from backend.workflow_packages.revision_optional_support_publication import (
    WRITING_REVISION_CAPSULE_VERSION as FORWARD_REVISION_CAPSULE_VERSION,
    WRITING_REVISION_VERSION as FORWARD_REVISION_VERSION,
    build_writing_revision_v0_9_package,
)

from .contracts import (
    CapsuleArtifactStatus,
    CapsuleTrustClassification,
    DesiredProjectManifest,
    InstallationAcknowledgementStatus,
    ProjectWorkflowInstance,
    SkillLifecycle,
    SkillReviewStatus,
    SkillSourceClass,
    SkillTrustTier,
    WorkflowCapsuleArtifact,
    WorkflowInstanceDesiredState,
    WorkspaceInstallationAcknowledgement,
)
from .literature_search import LITERATURE_SEARCH_DEFINITION_ID
from .legacy import legacy_workflow_instance_id

SYNC_PLAN_SCHEMA = "reagent.workspace-sync-plan/v0.1"
SYNC_ACK_SCHEMA = "reagent.capsule-installation-ack/v0.1"
SYNC_ACK_RECEIPT_SCHEMA = "reagent.workspace-sync-ack-receipt/v0.1"
LOCK_SCHEMA = "reagent.workspace-installed-lock/v0.1"
_NAMESPACE = UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966")


@dataclass(frozen=True, slots=True)
class WorkspaceSyncPlan:
    installation_id: str
    project_id: str
    workspace_id: str
    base_manifest_revision: int
    target_manifest_revision: int
    target_manifest_checksum: str
    installed_lock_checksum: str | None
    plan_checksum: str
    state: str
    actions: tuple[Mapping[str, Any], ...]
    created_at: datetime
    expires_at: datetime


def capsule_artifact_id(project_id: str, workflow_instance_id: str, package_id: str) -> str:
    value = uuid5(
        _NAMESPACE,
        "capsule-artifact/v1|"
        f"project={project_id}|instance={workflow_instance_id}|package={package_id}",
    )
    return "capsule-artifact-" + value.hex


def installation_id(idempotency_key: str, project_id: str, workspace_id: str) -> str:
    value = uuid5(
        UUID(idempotency_key),
        f"workspace-sync/v1|project={project_id}|workspace={workspace_id}",
    )
    return "install-" + value.hex


class WorkspaceSyncApplicationService:
    def __init__(
        self,
        *,
        unit_of_work: UnitOfWork,
        package_root: str | Path,
        clock,
    ) -> None:
        self._uow = unit_of_work
        self._package_root = Path(package_root)
        self._clock = clock

    def standalone_literature_package_pin(
        self, project_id: str
    ) -> tuple[str, str, str] | None:
        """Resolve one exact desired Literature instance for Package delivery."""

        matches = tuple(
            instance
            for instance in self._uow.workflow_foundation.list_workflow_instances(
                project_id
            )
            if instance.workflow_definition_id == LITERATURE_SEARCH_DEFINITION_ID
            and instance.desired_state is WorkflowInstanceDesiredState.ACTIVE
            and instance.capsule_version is not None
        )
        if not matches:
            return None
        if len(matches) != 1:
            raise ApplicationCodedConflictError(
                "Standalone Package delivery requires one exact desired Literature Search Instance",
                code="PACKAGE_WORKFLOW_INSTANCE_AMBIGUOUS",
            )
        instance = matches[0]
        return (
            instance.workflow_instance_id,
            instance.workflow_version,
            instance.capsule_version or "",
        )

    def register_standalone_package_artifact(
        self, project: LocalProject, workflow_instance_id: str
    ) -> None:
        """Bind a generated standalone Package to its exact Workflow Instance."""

        package = project.current_package
        instance = self._uow.workflow_foundation.get_workflow_instance(
            workflow_instance_id
        )
        if (
            package is None
            or instance is None
            or instance.project_id != project.project_id
            or instance.workflow_definition_id != LITERATURE_SEARCH_DEFINITION_ID
            or package.workflow_id != instance.workflow_definition_id
            or package.workflow_version != instance.workflow_version
            or instance.capsule_id is None
            or instance.capsule_version is None
        ):
            raise ApplicationCodedConflictError(
                "Standalone Package identity does not match the Workflow Instance",
                code="PACKAGE_WORKFLOW_INSTANCE_CONFLICT",
            )
        existing = self._uow.workspace_sync.get_capsule_artifact(
            project.project_id, workflow_instance_id
        )
        if existing is not None:
            if (
                existing.package_id != package.package_id
                or existing.package_checksum != package.package_checksum
                or existing.manifest_checksum != package.manifest_checksum
                or existing.archive_checksum != package.zip_checksum
            ):
                raise ApplicationCodedConflictError(
                    "Workflow Instance already has another immutable Package artifact",
                    code="CAPSULE_ARTIFACT_CONFLICT",
                )
            return
        timestamp = _parse_time(package.generated_at)
        self._uow.workspace_sync.add_capsule_artifact(WorkflowCapsuleArtifact(
            capsule_artifact_id=capsule_artifact_id(
                project.project_id, workflow_instance_id, package.package_id
            ),
            project_id=project.project_id,
            workflow_instance_id=workflow_instance_id,
            capsule_id=instance.capsule_id,
            capsule_version=instance.capsule_version,
            package_id=package.package_id,
            package_schema_version=package.package_schema_version,
            package_checksum=package.package_checksum,
            manifest_checksum=package.manifest_checksum,
            archive_checksum=package.zip_checksum,
            archive_size_bytes=package.package_size_bytes,
            file_count=package.file_count,
            archive_storage_key=package.archive_storage_key,
            status=CapsuleArtifactStatus.AVAILABLE,
            created_at=timestamp,
            updated_at=timestamp,
        ))

    def create_plan(
        self,
        *,
        project_id: str,
        workspace_id: str,
        installed_manifest_revision: int,
        installed_lock_checksum: str | None,
        installed_capsules: tuple[Mapping[str, Any], ...],
        idempotency_key: str,
        dry_run: bool,
    ) -> WorkspaceSyncPlan:
        project, manifest = self._require_project_manifest(project_id, workspace_id)
        del project
        _canonical_uuid(idempotency_key)
        if installed_manifest_revision < 0:
            raise ApplicationCodedValidationError(
                "Installed Manifest revision must be non-negative",
                code="INSTALLED_LOCK_INVALID",
            )
        installed_by_instance = _installed_index(installed_capsules)
        desired = _manifest_instances(manifest)
        instances = {
            item.workflow_instance_id: item
            for item in self._uow.workflow_foundation.list_workflow_instances(project_id)
        }
        pending_actions: list[Mapping[str, Any]] = []
        for instance_id in sorted(desired):
            pin = desired[instance_id]
            instance = instances.get(instance_id)
            if instance is None or instance.project_id != project_id:
                raise _unavailable("Desired Workflow Instance relation is incomplete")
            _validate_instance_pin(instance, pin)
            artifact = self._ensure_artifact(instance, manifest)
            installed = installed_by_instance.get(instance_id)
            if installed is not None and _installed_matches(installed, pin, artifact):
                action_type = "NOOP"
            elif installed is not None:
                action_type = "CONFLICT"
            elif artifact is None or artifact.status is not CapsuleArtifactStatus.AVAILABLE:
                action_type = "UNAVAILABLE"
            else:
                action_type = "INSTALL_CAPSULE"
            pending_actions.append(_action_document(
                sequence=0,
                action_type=action_type,
                instance=instance,
                pin=pin,
                artifact=artifact,
            ))
        for instance_id in sorted(set(installed_by_instance) - set(desired)):
            installed = installed_by_instance[instance_id]
            pending_actions.append(MappingProxyType({
                "sequence": 0,
                "action_type": "RETAINED_NOT_DESIRED",
                "workflow_instance_id": instance_id,
                "workflow_definition_id": installed["workflow_definition_id"],
                "workflow_definition_version": installed["workflow_definition_version"],
                "capsule_id": installed["capsule_id"],
                "capsule_version": installed["capsule_version"],
                "capsule_definition_checksum": installed["capsule_definition_checksum"],
                "trust_classification": CapsuleTrustClassification.TRUSTED_BUILT_IN_UNSIGNED.value,
                "destination_relative_path": installed["relative_path"],
                "artifact": None,
            }))
        ordered_actions = sorted(
            pending_actions,
            key=lambda item: (item["workflow_instance_id"], item["action_type"]),
        )
        actions = [
            MappingProxyType({**dict(item), "sequence": sequence})
            for sequence, item in enumerate(ordered_actions, 1)
        ]
        created_at = _aware(self._clock())
        base_payload = {
            "schema_version": SYNC_PLAN_SCHEMA,
            "installation_id": installation_id(idempotency_key, project_id, workspace_id),
            "project_id": project_id,
            "workspace_id": workspace_id,
            "base_manifest_revision": installed_manifest_revision,
            "target_manifest_revision": manifest.manifest_revision,
            "target_manifest_checksum": manifest.canonical_checksum,
            "installed_lock_checksum": installed_lock_checksum,
            "state": "NO_CHANGE" if actions and all(item["action_type"] == "NOOP" for item in actions) else "PLAN_CREATED",
            "actions": [to_json_value(item) for item in actions],
            "created_at": created_at.isoformat().replace("+00:00", "Z"),
            "expires_at": (created_at + timedelta(minutes=15)).isoformat().replace("+00:00", "Z"),
        }
        plan_checksum = canonical_hash(base_payload)
        # Artifact materialization is canonical cloud state even for a dry-run
        # plan.  It must never leave archive bytes without their binding row.
        self._uow.commit()
        return WorkspaceSyncPlan(
            installation_id=base_payload["installation_id"],
            project_id=project_id,
            workspace_id=workspace_id,
            base_manifest_revision=installed_manifest_revision,
            target_manifest_revision=manifest.manifest_revision,
            target_manifest_checksum=manifest.canonical_checksum,
            installed_lock_checksum=installed_lock_checksum,
            plan_checksum=plan_checksum,
            state=base_payload["state"],
            actions=tuple(actions),
            created_at=created_at,
            expires_at=created_at + timedelta(minutes=15),
        )

    def read_artifact(
        self, *, project_id: str, workflow_instance_id: str, capsule_artifact_id: str
    ) -> tuple[bytes, WorkflowCapsuleArtifact]:
        artifact = self._uow.workspace_sync.get_capsule_artifact_by_id(capsule_artifact_id)
        if artifact is None or artifact.project_id != project_id or artifact.workflow_instance_id != workflow_instance_id:
            raise ApplicationCodedNotFoundError(
                "Workflow Capsule artifact not found", code="CAPSULE_ARTIFACT_UNAVAILABLE"
            )
        path = self._artifact_path(artifact.archive_storage_key, project_id)
        if not path.is_file() or path.is_symlink():
            raise _unavailable("Workflow Capsule artifact archive is unavailable")
        content = path.read_bytes()
        if sha256_bytes(content) != artifact.archive_checksum:
            raise ApplicationCodedUnavailableError(
                "Workflow Capsule artifact failed integrity verification",
                code="CAPSULE_CHECKSUM_MISMATCH",
            )
        return content, artifact

    def acknowledge(
        self,
        *,
        project_id: str,
        document: Mapping[str, Any],
    ) -> WorkspaceInstallationAcknowledgement:
        required = {
            "schema_version", "installation_id", "project_id", "workspace_id",
            "manifest_revision", "manifest_checksum", "plan_checksum",
            "installed_lock_schema", "installed_lock_checksum", "idempotency_key",
            "installed_capsules", "installed_at",
        }
        if set(document) != required or document.get("schema_version") != SYNC_ACK_SCHEMA:
            raise ApplicationCodedValidationError(
                "Installation acknowledgement schema is invalid",
                code="ACKNOWLEDGEMENT_REJECTED",
            )
        if document["project_id"] != project_id:
            raise ApplicationCodedConflictError(
                "Installation acknowledgement Project identity mismatch",
                code="ACKNOWLEDGEMENT_CONFLICT",
            )
        project, current = self._require_project_manifest(project_id, document["workspace_id"])
        del project
        if document["manifest_revision"] != current.manifest_revision:
            raise ApplicationCodedConflictError(
                "Installation acknowledgement targets a stale Manifest revision",
                code="ACKNOWLEDGEMENT_STALE",
                details={"current_revision": current.manifest_revision},
            )
        if document["manifest_checksum"] != current.canonical_checksum:
            raise ApplicationCodedConflictError(
                "Installation acknowledgement Manifest checksum mismatch",
                code="ACKNOWLEDGEMENT_CONFLICT",
            )
        if document["installed_lock_schema"] != LOCK_SCHEMA:
            raise ApplicationCodedValidationError(
                "Installed Workspace Lock schema is unsupported",
                code="INSTALLED_LOCK_INVALID",
            )
        _canonical_uuid(document["idempotency_key"])
        desired = _manifest_instances(current)
        capsules = _ack_capsule_index(document["installed_capsules"])
        if set(capsules) != set(desired):
            raise ApplicationCodedConflictError(
                "Installation acknowledgement active Capsule set is incomplete",
                code="ACKNOWLEDGEMENT_CONFLICT",
            )
        for instance_id, pin in desired.items():
            item = capsules[instance_id]
            for field in (
                "workflow_definition_id", "workflow_definition_version",
                "capsule_id", "capsule_version", "capsule_definition_checksum",
            ):
                if item.get(field) != pin.get(field):
                    raise ApplicationCodedConflictError(
                        "Installation acknowledgement Capsule pin mismatch",
                        code="ACKNOWLEDGEMENT_CONFLICT",
                    )
        existing = self._uow.workspace_sync.get_acknowledgement_by_idempotency(
            document["workspace_id"], document["idempotency_key"]
        )
        installed_at = _parse_time(document["installed_at"])
        now = _aware(self._clock())
        candidate = WorkspaceInstallationAcknowledgement(
            installation_id=document["installation_id"],
            project_id=project_id,
            workspace_id=document["workspace_id"],
            manifest_revision=current.manifest_revision,
            manifest_checksum=current.canonical_checksum,
            installed_lock_schema=document["installed_lock_schema"],
            installed_lock_checksum=document["installed_lock_checksum"],
            plan_checksum=document["plan_checksum"],
            idempotency_key=document["idempotency_key"],
            status=InstallationAcknowledgementStatus.ACKNOWLEDGED,
            installed_capsules=tuple(document["installed_capsules"]),
            installed_at=installed_at,
            acknowledged_at=now,
            created_at=now,
            updated_at=now,
        )
        if existing is not None:
            if _ack_identity(existing) != _ack_identity(candidate):
                raise ApplicationCodedConflictError(
                    "Idempotency key was reused with different acknowledgement content",
                    code="IDEMPOTENCY_CONFLICT",
                )
            return existing
        try:
            self._uow.workspace_sync.add_acknowledgement(candidate)
            self._uow.commit()
        except DuplicateEntityError as error:
            self._uow.rollback()
            raise ApplicationCodedConflictError(
                "Concurrent installation acknowledgement requires exact retry",
                code="ACKNOWLEDGEMENT_CONFLICT",
            ) from error
        return candidate

    def _require_project_manifest(self, project_id: str, workspace_id: str):
        project = self._uow.project_manifests.get_project(project_id)
        if project is None:
            raise ApplicationCodedNotFoundError("Project not found", code="PROJECT_NOT_FOUND")
        if project.workspace_id != workspace_id:
            raise ApplicationCodedConflictError(
                "Workspace identity does not belong to the Project",
                code="WORKSPACE_IDENTITY_CONFLICT",
            )
        manifest = self._uow.project_manifests.get_current_manifest(project_id)
        if manifest is None:
            raise _unavailable("Current Desired Project Manifest is unavailable")
        return project, manifest

    def _ensure_artifact(
        self, instance: ProjectWorkflowInstance, manifest: DesiredProjectManifest
    ) -> WorkflowCapsuleArtifact | None:
        existing = self._uow.workspace_sync.get_capsule_artifact(
            instance.project_id, instance.workflow_instance_id
        )
        if existing is not None:
            if existing.capsule_id != instance.capsule_id or existing.capsule_version != instance.capsule_version:
                raise _unavailable("Workflow Capsule artifact pin conflicts with the Instance")
            return existing
        local_project: LocalProject | None = self._uow.local_projects.get(instance.project_id)
        if local_project is None:
            return None
        if instance.capsule_id is None or instance.capsule_version is None:
            return None
        package = local_project.current_package
        if (
            instance.workflow_definition_id == LITERATURE_SEARCH_DEFINITION_ID
            and instance.workflow_version == "0.3.0"
            and instance.capsule_version == "0.5.0"
            and package is not None
            and instance.workflow_instance_id == legacy_workflow_instance_id(instance.project_id)
        ):
            artifact = WorkflowCapsuleArtifact(
                capsule_artifact_id=capsule_artifact_id(instance.project_id, instance.workflow_instance_id, package.package_id),
                project_id=instance.project_id,
                workflow_instance_id=instance.workflow_instance_id,
                capsule_id=instance.capsule_id,
                capsule_version=instance.capsule_version,
                package_id=package.package_id,
                package_schema_version=package.package_schema_version,
                package_checksum=package.package_checksum,
                manifest_checksum=package.manifest_checksum,
                archive_checksum=package.zip_checksum,
                archive_size_bytes=package.package_size_bytes,
                file_count=package.file_count,
                archive_storage_key=package.archive_storage_key,
                status=CapsuleArtifactStatus.AVAILABLE,
                created_at=_parse_time(package.generated_at),
                updated_at=_parse_time(package.generated_at),
            )
        else:
            artifact = self._build_instance_artifact(instance, local_project, manifest)
        self._uow.workspace_sync.add_capsule_artifact(artifact)
        return artifact

    def _build_instance_artifact(
        self,
        instance: ProjectWorkflowInstance,
        project: LocalProject,
        manifest: DesiredProjectManifest,
    ) -> WorkflowCapsuleArtifact:
        if (
            instance.workflow_definition_id == LITERATURE_SEARCH_DEFINITION_ID
            and instance.workflow_version == "0.3.0"
            and instance.capsule_version == "0.5.0"
        ):
            package_id = (
                f"literature-search-{project.project_id}-{instance.workflow_instance_id}-v0.5"
            )
            builder = build_literature_search_package
        elif (
            instance.workflow_definition_id == LITERATURE_SEARCH_DEFINITION_ID
            and instance.workflow_version == PRODUCTION_LITERATURE_SEARCH_VERSION
            and instance.capsule_version == "0.6.0"
        ):
            package_id = (
                f"literature-search-{project.project_id}-{instance.workflow_instance_id}-v0.6"
            )
            builder = build_literature_search_v0_6_package
        elif (
            instance.workflow_definition_id == LITERATURE_SEARCH_DEFINITION_ID
            and instance.workflow_version == LITERATURE_SEARCH_V0_5_WORKFLOW_VERSION
            and instance.capsule_version == LITERATURE_SEARCH_V0_7_CAPSULE_VERSION
        ):
            package_id = (
                f"literature-search-{project.project_id}-"
                f"{instance.workflow_instance_id}-v0.7"
            )
            builder = build_literature_search_v0_7_package
        elif (
            instance.workflow_definition_id == IDEA_DISCOVERY_WORKFLOW_ID
            and instance.workflow_version == IDEA_DISCOVERY_WORKFLOW_VERSION
            and instance.capsule_version == "0.1.0"
        ):
            package_id = (
                f"idea-discovery-{project.project_id}-{instance.workflow_instance_id}-v0.1"
            )
            builder = build_idea_discovery_package
        elif (
            instance.workflow_definition_id == IDEA_DISCOVERY_WORKFLOW_ID
            and instance.workflow_version == IDEA_DISCOVERY_V0_2_WORKFLOW_VERSION
            and instance.capsule_version == "0.2.0"
        ):
            package_id = (
                f"idea-discovery-{project.project_id}-{instance.workflow_instance_id}-v0.2"
            )
            builder = build_idea_discovery_v0_2_package
        elif (
            instance.workflow_definition_id == IDEA_DISCOVERY_WORKFLOW_ID
            and instance.workflow_version == IDEA_DISCOVERY_V0_2_WORKFLOW_VERSION
            and instance.capsule_version == IDEA_DISCOVERY_V0_3_CAPSULE_VERSION
        ):
            package_id = (
                f"idea-discovery-{project.project_id}-{instance.workflow_instance_id}-v0.3"
            )
            builder = build_idea_discovery_v0_3_package
        elif (
            instance.workflow_definition_id == IDEA_DISCOVERY_WORKFLOW_ID
            and instance.workflow_version == IDEA_DISCOVERY_V0_3_WORKFLOW_VERSION
            and instance.capsule_version == IDEA_DISCOVERY_V0_4_CAPSULE_VERSION
        ):
            package_id = (
                f"idea-discovery-{project.project_id}-"
                f"{instance.workflow_instance_id}-v0.4"
            )
            builder = build_idea_discovery_v0_4_package
        elif (
            instance.workflow_definition_id == IDEA_DISCOVERY_WORKFLOW_ID
            and instance.workflow_version == IDEA_DISCOVERY_V0_4_WORKFLOW_VERSION
            and instance.capsule_version == IDEA_DISCOVERY_V0_5_CAPSULE_VERSION
        ):
            package_id = (
                f"idea-discovery-{project.project_id}-"
                f"{instance.workflow_instance_id}-v0.5"
            )
            builder = build_idea_discovery_v0_5_package
        elif (
            instance.workflow_definition_id in {
                WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID, EXPERIMENT_WORKFLOW_ID,
            }
            and instance.workflow_version == SCAFFOLD_WORKFLOW_VERSION
            and instance.capsule_version == SCAFFOLD_CAPSULE_VERSION
        ):
            slug, builder = {
                WRITING_WORKFLOW_ID: ("writing", build_writing_scaffold_package),
                REVIEW_WORKFLOW_ID: ("review", build_review_scaffold_package),
                EXPERIMENT_WORKFLOW_ID: (
                    "reproduction-experiment", build_experiment_scaffold_package,
                ),
            }[instance.workflow_definition_id]
            package_id = (
                f"{slug}-{project.project_id}-{instance.workflow_instance_id}-v0.1"
            )
        elif (
            instance.workflow_definition_id in {
                WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID, EXPERIMENT_WORKFLOW_ID,
            }
            and instance.workflow_version == SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION
            and instance.capsule_version == SCAFFOLD_SKILL_BACKED_CAPSULE_VERSION
        ):
            slug, builder = {
                WRITING_WORKFLOW_ID: (
                    "writing", build_writing_scaffold_v0_2_package
                ),
                REVIEW_WORKFLOW_ID: (
                    "review", build_review_scaffold_v0_2_package
                ),
                EXPERIMENT_WORKFLOW_ID: (
                    "reproduction-experiment",
                    build_experiment_scaffold_v0_2_package,
                ),
            }[instance.workflow_definition_id]
            package_id = (
                f"{slug}-{project.project_id}-{instance.workflow_instance_id}-v0.2"
            )
        elif (
            instance.workflow_definition_id in {
                WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID,
            }
            and instance.workflow_version == SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION
            and instance.capsule_version == SCAFFOLD_INTERACTIVE_CAPSULE_VERSION
        ):
            slug, builder = {
                WRITING_WORKFLOW_ID: (
                    "writing", build_writing_scaffold_v0_3_package
                ),
                REVIEW_WORKFLOW_ID: (
                    "review", build_review_scaffold_v0_3_package
                ),
            }[instance.workflow_definition_id]
            package_id = (
                f"{slug}-{project.project_id}-{instance.workflow_instance_id}-v0.3"
            )
        elif (
            instance.workflow_definition_id in {
                WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID,
            }
            and instance.workflow_version == SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION
            and instance.capsule_version == SCAFFOLD_COMPLETION_CAPSULE_VERSION
        ):
            slug, builder = {
                WRITING_WORKFLOW_ID: (
                    "writing", build_writing_scaffold_v0_4_package
                ),
                REVIEW_WORKFLOW_ID: (
                    "review", build_review_scaffold_v0_4_package
                ),
            }[instance.workflow_definition_id]
            package_id = (
                f"{slug}-{project.project_id}-{instance.workflow_instance_id}-v0.4"
            )
        elif (
            instance.workflow_definition_id == WRITING_WORKFLOW_ID
            and instance.workflow_version == WRITING_REVISION_WORKFLOW_VERSION
            and instance.capsule_version == WRITING_REVISION_CAPSULE_VERSION
        ):
            builder = build_writing_revision_v0_6_package
            package_id = (
                f"writing-revision-{project.project_id}-"
                f"{instance.workflow_instance_id}-v0.6"
            )
        elif (
            instance.workflow_definition_id == WRITING_WORKFLOW_ID
            and instance.workflow_version == FORWARD_REVISION_V0_8_VERSION
            and instance.capsule_version == FORWARD_REVISION_V0_8_CAPSULE_VERSION
        ):
            builder = build_writing_revision_v0_8_package
            package_id = f"forward-writing-revision-{project.project_id}-{instance.workflow_instance_id}-v0.8"
        elif (
            instance.workflow_definition_id == WRITING_WORKFLOW_ID
            and instance.workflow_version == FORWARD_REVISION_VERSION
            and instance.capsule_version == FORWARD_REVISION_CAPSULE_VERSION
        ):
            builder = build_writing_revision_v0_9_package
            package_id = f"forward-writing-revision-{project.project_id}-{instance.workflow_instance_id}-v0.9"
        elif (
            instance.workflow_definition_id == WRITING_WORKFLOW_ID
            and instance.workflow_version == REAL_WRITING_WORKFLOW_VERSION
            and instance.capsule_version == REAL_WRITING_CAPSULE_VERSION
        ):
            builder = build_real_writing_v0_5_package
            package_id = (
                f"real-writing-{project.project_id}-"
                f"{instance.workflow_instance_id}-v0.5"
            )
        elif (
            instance.workflow_definition_id == WRITING_WORKFLOW_ID
            and instance.workflow_version == FORWARD_WRITING_VERSION
            and instance.capsule_version == FORWARD_WRITING_CAPSULE_VERSION
        ):
            builder = build_initial_writing_v0_7_package
            package_id = f"forward-writing-{project.project_id}-{instance.workflow_instance_id}-v0.7"
        elif (
            instance.workflow_definition_id == REVIEW_WORKFLOW_ID
            and instance.workflow_version == REAL_REVIEW_WORKFLOW_VERSION
            and instance.capsule_version == REAL_REVIEW_CAPSULE_VERSION
        ):
            builder = build_real_review_v0_5_package
            package_id = (
                f"real-review-{project.project_id}-"
                f"{instance.workflow_instance_id}-v0.5"
            )
        elif (
            instance.workflow_definition_id == REVIEW_WORKFLOW_ID
            and instance.workflow_version == FORWARD_REVIEW_VERSION
            and instance.capsule_version == FORWARD_REVIEW_CAPSULE_VERSION
        ):
            builder = build_review_v0_6_package
            package_id = f"forward-review-{project.project_id}-{instance.workflow_instance_id}-v0.6"
        elif (
            instance.workflow_definition_id == EXPERIMENT_WORKFLOW_ID
            and instance.workflow_version == EXPERIMENT_RESOURCE_WORKFLOW_VERSION
            and instance.capsule_version == EXPERIMENT_RESOURCE_CAPSULE_VERSION
        ):
            slug = "reproduction-experiment"
            builder = build_experiment_scaffold_v0_3_package
            package_id = (
                f"{slug}-{project.project_id}-{instance.workflow_instance_id}-v0.3"
            )
        elif (
            instance.workflow_definition_id == EXPERIMENT_WORKFLOW_ID
            and instance.workflow_version == EXPERIMENT_RESOURCE_WORKFLOW_VERSION
            and instance.capsule_version == EXPERIMENT_INTERACTIVE_CAPSULE_VERSION
        ):
            slug = "reproduction-experiment"
            builder = build_experiment_scaffold_v0_4_package
            package_id = (
                f"{slug}-{project.project_id}-{instance.workflow_instance_id}-v0.4"
            )
        elif (
            instance.workflow_definition_id == EXPERIMENT_WORKFLOW_ID
            and instance.workflow_version == EXPERIMENT_RESOURCE_WORKFLOW_VERSION
            and instance.capsule_version == EXPERIMENT_COMPLETION_CAPSULE_VERSION
        ):
            slug = "reproduction-experiment"
            builder = build_experiment_scaffold_v0_5_package
            package_id = (
                f"{slug}-{project.project_id}-{instance.workflow_instance_id}-v0.5"
            )
        elif (
            instance.workflow_definition_id == EXPERIMENT_WORKFLOW_ID
            and instance.workflow_version == REAL_EXPERIMENT_WORKFLOW_VERSION
            and instance.capsule_version in {
                REAL_EXPERIMENT_CAPSULE_VERSION,
                REAL_EXPERIMENT_BUGFIX_CAPSULE_VERSION,
            }
        ):
            builder = {
                REAL_EXPERIMENT_CAPSULE_VERSION: build_real_experiment_v0_6_package,
                REAL_EXPERIMENT_BUGFIX_CAPSULE_VERSION: build_real_experiment_v0_7_package,
            }[instance.capsule_version]
            package_id = (
                f"real-experiment-{project.project_id}-"
                f"{instance.workflow_instance_id}-v"
                f"{instance.capsule_version.removesuffix('.0')}"
            )
        elif (
            instance.workflow_definition_id == EXPERIMENT_WORKFLOW_ID
            and instance.workflow_version == PREPARED_EXPERIMENT_WORKFLOW_VERSION
            and instance.capsule_version == PREPARED_EXPERIMENT_CAPSULE_VERSION
        ):
            builder = build_prepared_experiment_v0_8_package
            package_id = (
                f"prepared-experiment-{project.project_id}-"
                f"{instance.workflow_instance_id}-v0.8"
            )
        elif (
            instance.workflow_definition_id == EXPERIMENT_WORKFLOW_ID
            and instance.workflow_version == GENERIC_EXPERIMENT_WORKFLOW_VERSION
            and instance.capsule_version == GENERIC_EXPERIMENT_CAPSULE_VERSION
        ):
            builder = build_generic_experiment_v0_9_package
            package_id = (
                f"generic-experiment-{project.project_id}-"
                f"{instance.workflow_instance_id}-v0.9"
            )
        elif (
            instance.workflow_definition_id == EXPERIMENT_WORKFLOW_ID
            and instance.workflow_version == GENERIC_EXPERIMENT_V5_WORKFLOW_VERSION
            and instance.capsule_version == GENERIC_EXPERIMENT_V5_CAPSULE_VERSION
        ):
            builder = build_generic_experiment_v0_10_package
            package_id = (
                f"generic-experiment-{project.project_id}-"
                f"{instance.workflow_instance_id}-v0.10"
            )
        elif (
            instance.workflow_definition_id == EXPERIMENT_WORKFLOW_ID
            and instance.workflow_version == GENERIC_HARNESS_WORKFLOW_VERSION
            and instance.capsule_version == GENERIC_HARNESS_CAPSULE_VERSION
        ):
            builder = build_generic_harness_v0_11_package
            package_id = (
                f"generic-harness-{project.project_id}-"
                f"{instance.workflow_instance_id}-v0.11"
            )
        else:
            raise _unavailable("Workflow Capsule artifact pin has no reviewed compiler")
        output = (
            self._resolved_package_root()
            / project.project_id
            / "workspace-capsules"
            / instance.workflow_instance_id
            / instance.capsule_version
        )
        try:
            build_options = dict(
                project_id=project.project_id,
                project_name=project.name,
                research_topic=project.research_topic,
                output_root=output,
                package_id=package_id,
            )
            if builder is build_literature_search_package:
                build_options["allow_absolute_output_root"] = True
            built = builder(**build_options)
        except (FileExistsError, OSError, ValueError) as error:
            raise ApplicationCodedUnavailableError(
                "Workflow Capsule artifact materialization failed closed",
                code="CAPSULE_ARTIFACT_UNAVAILABLE",
            ) from error
        if not built.validation.valid or not built.archive_validation.valid:
            raise _unavailable("Workflow Capsule artifact validation failed")
        if (
            instance.workflow_definition_id in {
                WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID, EXPERIMENT_WORKFLOW_ID,
            }
            and instance.workflow_version in {
                SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
                EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
                REAL_EXPERIMENT_WORKFLOW_VERSION,
                REAL_WRITING_WORKFLOW_VERSION,
                WRITING_REVISION_WORKFLOW_VERSION,
                FORWARD_WRITING_VERSION,
                FORWARD_REVIEW_VERSION,
                FORWARD_REVISION_VERSION,
                GENERIC_EXPERIMENT_WORKFLOW_VERSION,
                GENERIC_EXPERIMENT_V5_WORKFLOW_VERSION,
                GENERIC_HARNESS_WORKFLOW_VERSION,
            }
        ):
            self._verify_compiled_skill_authority(instance, built.package_root)
        timestamp = manifest.created_at.astimezone(timezone.utc)
        return WorkflowCapsuleArtifact(
            capsule_artifact_id=capsule_artifact_id(project.project_id, instance.workflow_instance_id, built.package_id),
            project_id=project.project_id,
            workflow_instance_id=instance.workflow_instance_id,
            capsule_id=instance.capsule_id or "",
            capsule_version=instance.capsule_version or "",
            package_id=built.package_id,
            package_schema_version=built.package_schema_version,
            package_checksum=built.package_checksum,
            manifest_checksum=built.manifest_checksum,
            archive_checksum=built.zip_checksum,
            archive_size_bytes=built.archive_path.stat().st_size,
            file_count=built.file_count,
            archive_storage_key=built.archive_path.relative_to(self._resolved_package_root()).as_posix(),
            status=CapsuleArtifactStatus.AVAILABLE,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def _verify_compiled_skill_authority(
        self, instance: ProjectWorkflowInstance, package_root: Path
    ) -> None:
        """Bind compiler output to Registry pins; never trust static bytes alone."""

        pins = self._uow.workflow_foundation.list_workflow_skill_pins(
            instance.workflow_definition_id, instance.workflow_version
        )
        try:
            manifest = json.loads(
                (package_root / "package-manifest.json").read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise _unavailable("Skill-backed Capsule manifest is unavailable") from error
        compiled = manifest.get("skill_pins")
        if not isinstance(compiled, list) or len(compiled) != len(pins) or not pins:
            raise _unavailable("Skill-backed Capsule pin set conflicts with Registry")
        for pin, package_pin in zip(pins, compiled, strict=True):
            definition = self._uow.workflow_foundation.get_skill_definition(
                pin.skill_id
            )
            version = self._uow.workflow_foundation.get_skill_version(
                pin.skill_id, pin.skill_version
            )
            if (
                definition is None
                or version is None
                or definition.lifecycle is not SkillLifecycle.AVAILABLE
                or definition.source_class is not SkillSourceClass.PLATFORM_BUILT_IN
                or definition.trust_tier is not SkillTrustTier.BUILT_IN_REVIEWED
                or version.trust_tier is not SkillTrustTier.BUILT_IN_REVIEWED
                or version.review_status is not SkillReviewStatus.REVIEWED
                or version.published_at is None
                or version.content_checksum != pin.skill_checksum
                or package_pin.get("name") != pin.skill_id
                or package_pin.get("semantic_version") != pin.skill_version
                or package_pin.get("checksum") != pin.skill_checksum
                or package_pin.get("source_identity")
                != version.content_source_identity
            ):
                raise _unavailable(
                    "Skill-backed Capsule requires exact reviewed Registry authority"
                )

    def _resolved_package_root(self) -> Path:
        root = self._package_root.expanduser().resolve()
        if root.is_symlink():
            raise _unavailable("Capsule artifact root must not be a symbolic link")
        root.mkdir(parents=True, exist_ok=True)
        return root

    def local_session_package_identity(
        self, project_id: str, package_id: str
    ) -> tuple[str, str, str, str, str] | None:
        """Return a trusted B4 artifact identity for local-session issuance."""

        matches = tuple(
            artifact
            for artifact in self._uow.workspace_sync.list_capsule_artifacts(project_id)
            if artifact.package_id == package_id
            and artifact.status is CapsuleArtifactStatus.AVAILABLE
        )
        if len(matches) != 1:
            return None
        artifact = matches[0]
        instance = self._uow.workflow_foundation.get_workflow_instance(
            artifact.workflow_instance_id
        )
        if instance is None or instance.project_id != project_id:
            return None
        version = self._uow.workflow_foundation.get_definition_version(
            instance.workflow_definition_id,
            instance.workflow_version,
        )
        if version is None:
            return None
        return (
            artifact.package_id,
            artifact.package_checksum,
            instance.workflow_definition_id,
            instance.workflow_version,
            version.contract_checksum,
        )

    def _artifact_path(self, storage_key: str, project_id: str) -> Path:
        root = self._resolved_package_root()
        path = (root / storage_key).resolve()
        try:
            path.relative_to((root / project_id).resolve())
        except ValueError as error:
            raise _unavailable("Capsule artifact storage identity is invalid") from error
        return path


def sync_plan_document(value: WorkspaceSyncPlan) -> dict[str, Any]:
    return {
        "schema_version": SYNC_PLAN_SCHEMA,
        "installation_id": value.installation_id,
        "project_id": value.project_id,
        "workspace_id": value.workspace_id,
        "base_manifest_revision": value.base_manifest_revision,
        "target_manifest_revision": value.target_manifest_revision,
        "target_manifest_checksum": value.target_manifest_checksum,
        "installed_lock_checksum": value.installed_lock_checksum,
        "plan_checksum": value.plan_checksum,
        "state": value.state,
        "actions": [to_json_value(item) for item in value.actions],
        "created_at": value.created_at.isoformat().replace("+00:00", "Z"),
        "expires_at": value.expires_at.isoformat().replace("+00:00", "Z"),
    }


def acknowledgement_document(value: WorkspaceInstallationAcknowledgement) -> dict[str, Any]:
    return {
        "schema_version": SYNC_ACK_RECEIPT_SCHEMA,
        "installation_id": value.installation_id,
        "project_id": value.project_id,
        "workspace_id": value.workspace_id,
        "manifest_revision": value.manifest_revision,
        "installed_lock_checksum": value.installed_lock_checksum,
        "status": value.status.value,
        "idempotency_key": value.idempotency_key,
        "acknowledged_at": value.acknowledged_at.isoformat().replace("+00:00", "Z"),
    }


def _manifest_instances(manifest: DesiredProjectManifest) -> dict[str, Mapping[str, Any]]:
    document = to_json_value(manifest.manifest_json)
    if not isinstance(document, dict) or document.get("canonical_checksum") != manifest.canonical_checksum:
        raise _unavailable("Desired Project Manifest checksum envelope is invalid")
    payload = dict(document)
    payload.pop("canonical_checksum", None)
    if canonical_hash(payload) != manifest.canonical_checksum:
        raise _unavailable("Desired Project Manifest checksum is invalid")
    raw = document.get("workflow_instances")
    if not isinstance(raw, list) or len(raw) > 100:
        raise _unavailable("Desired Project Manifest Workflow list is invalid")
    result: dict[str, Mapping[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict) or item.get("desired_state") != "ACTIVE":
            continue
        instance_id = item.get("workflow_instance_id")
        if not isinstance(instance_id, str) or instance_id in result:
            raise _unavailable("Desired Project Manifest contains duplicate Workflow Instances")
        result[instance_id] = MappingProxyType(dict(item))
    return result


def _validate_instance_pin(instance: ProjectWorkflowInstance, pin: Mapping[str, Any]) -> None:
    expected = {
        "workflow_instance_id": instance.workflow_instance_id,
        "workflow_definition_id": instance.workflow_definition_id,
        "workflow_definition_version": instance.workflow_version,
        "capsule_id": instance.capsule_id,
        "capsule_version": instance.capsule_version,
        "desired_state": "ACTIVE",
    }
    if any(pin.get(key) != value for key, value in expected.items()):
        raise _unavailable("Desired Project Manifest pin conflicts with Workflow Instance")


def _installed_index(values: tuple[Mapping[str, Any], ...]) -> dict[str, Mapping[str, Any]]:
    if len(values) > 100:
        raise ApplicationCodedValidationError("Installed Capsule list is too large", code="INSTALLED_LOCK_INVALID")
    result: dict[str, Mapping[str, Any]] = {}
    for value in values:
        if not isinstance(value, Mapping):
            raise ApplicationCodedValidationError("Installed Capsule entry is invalid", code="INSTALLED_LOCK_INVALID")
        instance_id = value.get("workflow_instance_id")
        if not isinstance(instance_id, str) or instance_id in result:
            raise ApplicationCodedValidationError("Installed Capsule identity is invalid", code="INSTALLED_LOCK_INVALID")
        result[instance_id] = MappingProxyType(dict(value))
    return result


def _installed_matches(installed, pin, artifact) -> bool:
    if artifact is None:
        return False
    expected = {
        "workflow_definition_id": pin["workflow_definition_id"],
        "workflow_definition_version": pin["workflow_definition_version"],
        "capsule_id": pin["capsule_id"],
        "capsule_version": pin["capsule_version"],
        "capsule_definition_checksum": pin["capsule_definition_checksum"],
        "package_checksum": artifact.package_checksum,
    }
    return all(installed.get(key) == value for key, value in expected.items())


def _action_document(*, sequence, action_type, instance, pin, artifact):
    return MappingProxyType({
        "sequence": sequence,
        "action_type": action_type,
        "workflow_instance_id": instance.workflow_instance_id,
        "workflow_definition_id": instance.workflow_definition_id,
        "workflow_definition_version": instance.workflow_version,
        "capsule_id": instance.capsule_id,
        "capsule_version": instance.capsule_version,
        "capsule_definition_checksum": pin["capsule_definition_checksum"],
        "trust_classification": CapsuleTrustClassification.TRUSTED_BUILT_IN_UNSIGNED.value,
        "destination_relative_path": (
            f"capsules/{instance.workflow_definition_id}/"
            f"{instance.workflow_instance_id}/{instance.capsule_version}"
        ),
        "artifact": None if artifact is None else {
            "capsule_artifact_id": artifact.capsule_artifact_id,
            "package_id": artifact.package_id,
            "package_schema_version": artifact.package_schema_version,
            "package_checksum": artifact.package_checksum,
            "manifest_checksum": artifact.manifest_checksum,
            "archive_checksum": artifact.archive_checksum,
            "archive_size_bytes": artifact.archive_size_bytes,
            "file_count": artifact.file_count,
            "media_type": "application/zip",
            "download_path": (
                f"/projects/{instance.project_id}/workflow-instances/"
                f"{instance.workflow_instance_id}/capsule-artifacts/"
                f"{artifact.capsule_artifact_id}/download"
            ),
        },
    })


def _ack_capsule_index(values) -> dict[str, Mapping[str, Any]]:
    if not isinstance(values, list) or len(values) > 100:
        raise ApplicationCodedValidationError("Acknowledged Capsule list is invalid", code="ACKNOWLEDGEMENT_REJECTED")
    result = {}
    required = {
        "workflow_instance_id", "workflow_definition_id",
        "workflow_definition_version", "capsule_id", "capsule_version",
        "capsule_definition_checksum",
    }
    for item in values:
        if (
            not isinstance(item, dict)
            or set(item) != required
            or not isinstance(item.get("workflow_instance_id"), str)
        ):
            raise ApplicationCodedValidationError("Acknowledged Capsule identity is invalid", code="ACKNOWLEDGEMENT_REJECTED")
        if item["workflow_instance_id"] in result:
            raise ApplicationCodedValidationError("Acknowledged Capsule identity is duplicated", code="ACKNOWLEDGEMENT_REJECTED")
        result[item["workflow_instance_id"]] = item
    return result


def _ack_identity(value: WorkspaceInstallationAcknowledgement):
    return (
        value.installation_id, value.project_id, value.workspace_id,
        value.manifest_revision, value.manifest_checksum,
        value.installed_lock_schema, value.installed_lock_checksum,
        value.plan_checksum, value.idempotency_key,
        tuple(to_json_value(item) for item in value.installed_capsules),
        value.installed_at,
    )


def _canonical_uuid(value: str) -> None:
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as error:
        raise ApplicationCodedValidationError("Idempotency key must be a UUID", code="INVALID_REQUEST") from error
    if str(parsed) != value:
        raise ApplicationCodedValidationError("Idempotency key must use canonical UUID text", code="INVALID_REQUEST")


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as error:
        raise ApplicationCodedValidationError("Timestamp is invalid", code="ACKNOWLEDGEMENT_REJECTED") from error
    return _aware(parsed)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("clock must be timezone-aware")
    return value.astimezone(timezone.utc)


def _unavailable(message: str) -> ApplicationCodedUnavailableError:
    return ApplicationCodedUnavailableError(message, code="WORKSPACE_SYNC_NOT_AVAILABLE")
