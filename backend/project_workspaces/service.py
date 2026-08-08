"""Deterministic built-in seed and legacy Project reconciliation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from backend.local_projects.contracts import LITERATURE_SEARCH_WORKFLOW
from backend.workflow_packages.contracts import PACKAGE_SCHEMA_VERSION
from backend.workflow_packages.template import (
    TEMPLATE_ID,
    TEMPLATE_VERSION,
    WORKFLOW_ID,
    WORKFLOW_VERSION,
)

from .contracts import (
    CapsuleTrustClassification,
    CloudProject,
    CloudProjectStatus,
    CoreCapabilityMaturity,
    ProjectWorkflowInstance,
    WorkflowCapsuleVersion,
    WorkflowDefinition,
    WorkflowDefinitionLifecycle,
    WorkflowDefinitionVersion,
    WorkflowInstanceDesiredState,
    WorkflowReviewStatus,
)
from .errors import WorkflowFoundationConflictError
from .legacy import (
    initial_manifest_idempotency_key,
    legacy_workflow_instance_id,
    workspace_id_for_project,
)
from .manifest import build_desired_manifest
from .literature_search import (
    LITERATURE_SEARCH_CAPSULE_ID,
    literature_search_capsule_definition_checksum,
    literature_search_contract_checksum,
)
from .production_workflows import (
    idea_discovery_capsule,
    idea_discovery_definition,
    idea_discovery_definition_version,
    idea_discovery_requirement,
    idea_discovery_v0_2_capsule,
    idea_discovery_v0_2_definition_version,
    idea_discovery_v0_2_requirement,
    literature_search_capsule as production_literature_search_capsule,
    literature_search_definition_version as production_literature_search_version,
)

if TYPE_CHECKING:
    from backend.persistence.ports.unit_of_work import UnitOfWork

_MUTABLE_ROOTS = (
    "memory/context.md",
    "memory/progress",
    "memory/round-control.json",
    "memory/search",
    "outputs",
)
_CAPABILITIES = (
    "paper.search/v0.1",
    "progress.read/v0.1",
    "progress.upload/v0.2",
)


def reconcile_legacy_workflow_foundation(
    uow: UnitOfWork, *, now: datetime | None = None
) -> tuple[ProjectWorkflowInstance, ...]:
    """Seed accepted LS metadata and add one identity per legacy Project.

    The caller owns the transaction and decides whether to commit. Existing
    equivalent identities are idempotent; immutable conflicts fail closed.
    """

    timestamp = now or datetime.now(timezone.utc)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    ensure_literature_search_foundation(uow, now=timestamp)
    repository = uow.workflow_foundation

    instances: list[ProjectWorkflowInstance] = []
    for project in uow.local_projects.list_all():
        if project.selected_workflow != LITERATURE_SEARCH_WORKFLOW:
            raise WorkflowFoundationConflictError(
                "unsupported legacy selected_workflow during workspace backfill"
            )
        package = project.current_package
        instance = ProjectWorkflowInstance(
            workflow_instance_id=legacy_workflow_instance_id(project.project_id),
            project_id=project.project_id,
            workflow_definition_id=WORKFLOW_ID,
            workflow_version=WORKFLOW_VERSION,
            capsule_id=LITERATURE_SEARCH_CAPSULE_ID,
            capsule_version=TEMPLATE_VERSION,
            desired_state=WorkflowInstanceDesiredState.ACTIVE,
            display_name="Literature Search",
            created_manifest_revision=0,
            retired_manifest_revision=None,
            legacy_package_id=package.package_id if package else None,
            created_at=_parse_time(project.created_at),
            updated_at=_parse_time(project.updated_at),
        )
        repository.add_workflow_instance(instance)
        canonical = uow.project_manifests.get_project(project.project_id)
        if canonical is None:
            canonical = CloudProject(
                project_id=project.project_id,
                workspace_id=workspace_id_for_project(project.project_id),
                name=project.name,
                research_topic=project.research_topic,
                status=CloudProjectStatus.ACTIVE,
                current_manifest_revision=1,
                legacy_local_project_id=project.project_id,
                created_at=_parse_time(project.created_at),
                updated_at=_parse_time(project.updated_at),
            )
            manifest, entries = build_desired_manifest(
                project=canonical,
                instances=(instance,),
                capsules={
                    (LITERATURE_SEARCH_CAPSULE_ID, TEMPLATE_VERSION):
                    _capsule_version(timestamp)
                },
                revision=1,
                base_revision=0,
                idempotency_key=initial_manifest_idempotency_key(project.project_id),
                now=_parse_time(project.created_at),
            )
            uow.project_manifests.add_project(canonical)
            uow.project_manifests.add_manifest(manifest)
            uow.project_manifests.add_manifest_entries(entries)
        instances.append(instance)
    return tuple(instances)


def ensure_literature_search_foundation(
    uow: UnitOfWork, *, now: datetime | None = None
) -> tuple[WorkflowDefinition, WorkflowDefinitionVersion, WorkflowCapsuleVersion]:
    timestamp = now or datetime.now(timezone.utc)
    definition = _definition(timestamp)
    version = _definition_version(timestamp)
    capsule = _capsule_version(timestamp)
    repository = uow.workflow_foundation
    repository.add_definition(definition)
    repository.add_definition_version(version)
    repository.add_capsule_version(capsule)
    return definition, version, capsule


def ensure_production_workflow_foundation(
    uow: UnitOfWork, *, now: datetime | None = None
) -> tuple[
    WorkflowDefinition,
    WorkflowDefinitionVersion,
    WorkflowCapsuleVersion,
    WorkflowDefinition,
    WorkflowDefinitionVersion,
    WorkflowCapsuleVersion,
]:
    """Seed both reviewed production Workflows without mutating legacy pins."""

    timestamp = now or datetime.now(timezone.utc)
    literature_definition, _, _ = ensure_literature_search_foundation(
        uow, now=timestamp
    )
    literature_version = production_literature_search_version(timestamp)
    literature_capsule = production_literature_search_capsule(timestamp)
    idea_definition = idea_discovery_definition(timestamp)
    legacy_idea_version = idea_discovery_definition_version(timestamp)
    legacy_idea_capsule = idea_discovery_capsule(timestamp)
    idea_version = idea_discovery_v0_2_definition_version(timestamp)
    idea_capsule = idea_discovery_v0_2_capsule(timestamp)
    repository = uow.workflow_foundation
    repository.add_definition_version(literature_version)
    repository.add_capsule_version(literature_capsule)
    repository.add_definition(idea_definition)
    repository.add_definition_version(legacy_idea_version)
    repository.add_capsule_version(legacy_idea_capsule)
    repository.add_definition_version(idea_version)
    repository.add_capsule_version(idea_capsule)
    for requirement in (
        idea_discovery_requirement(timestamp),
        idea_discovery_v0_2_requirement(timestamp),
    ):
        existing_requirement = uow.artifact_references.get_requirement(
            requirement.workflow_definition_id,
            requirement.workflow_version,
            requirement.requirement_key,
        )
        if existing_requirement is None:
            uow.artifact_references.add_requirement(requirement)
        elif (
            existing_requirement.workflow_definition_id,
            existing_requirement.workflow_version,
            existing_requirement.requirement_key,
            existing_requirement.artifact_type,
            existing_requirement.compatibility_mode,
            existing_requirement.schema_constraint,
            existing_requirement.cardinality_min,
            existing_requirement.cardinality_max,
            existing_requirement.required,
            existing_requirement.materialization_mode,
            existing_requirement.target_relative_path,
        ) != (
            requirement.workflow_definition_id,
            requirement.workflow_version,
            requirement.requirement_key,
            requirement.artifact_type,
            requirement.compatibility_mode,
            requirement.schema_constraint,
            requirement.cardinality_min,
            requirement.cardinality_max,
            requirement.required,
            requirement.materialization_mode,
            requirement.target_relative_path,
        ):
            raise WorkflowFoundationConflictError(
                "Idea Discovery Artifact requirement immutable-content conflict"
            )
    return (
        literature_definition,
        literature_version,
        literature_capsule,
        idea_definition,
        idea_version,
        idea_capsule,
    )


def _definition(now: datetime) -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_definition_id=WORKFLOW_ID,
        display_name="Literature Search",
        description="",
        lifecycle=WorkflowDefinitionLifecycle.AVAILABLE,
        allows_multiple_instances=True,
        created_at=now,
        updated_at=now,
    )


def _definition_version(now: datetime) -> WorkflowDefinitionVersion:
    return WorkflowDefinitionVersion(
        workflow_definition_id=WORKFLOW_ID,
        version=WORKFLOW_VERSION,
        contract_checksum=literature_search_contract_checksum(),
        input_schema_id="research-request/v0.2",
        output_schema_id="literature-search-report/v0.2",
        compatibility={"package_schema_version": PACKAGE_SCHEMA_VERSION},
        review_status=WorkflowReviewStatus.REVIEWED,
        core_capability_maturity=CoreCapabilityMaturity.REVIEWED_CORE,
        published_at=now,
        created_at=now,
        updated_at=now,
    )


def _capsule_version(now: datetime) -> WorkflowCapsuleVersion:
    return WorkflowCapsuleVersion(
        capsule_id=LITERATURE_SEARCH_CAPSULE_ID,
        capsule_version=TEMPLATE_VERSION,
        workflow_definition_id=WORKFLOW_ID,
        workflow_version=WORKFLOW_VERSION,
        definition_checksum=literature_search_capsule_definition_checksum(),
        archive_size_bytes=0,
        archive_media_type="application/zip",
        mutable_roots=_MUTABLE_ROOTS,
        capability_requirements=_CAPABILITIES,
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "package_template_id": TEMPLATE_ID,
            "trust_classification": CapsuleTrustClassification.TRUSTED_BUILT_IN_UNSIGNED.value,
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=True,
        created_at=now,
        updated_at=now,
    )


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("legacy timestamp must be timezone-aware")
    return parsed
