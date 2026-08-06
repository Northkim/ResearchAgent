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
    ProjectWorkflowInstance,
    WorkflowCapsuleVersion,
    WorkflowDefinition,
    WorkflowDefinitionLifecycle,
    WorkflowDefinitionVersion,
    WorkflowInstanceDesiredState,
    WorkflowReviewStatus,
)
from .errors import WorkflowFoundationConflictError
from .legacy import legacy_workflow_instance_id
from .literature_search import (
    LITERATURE_SEARCH_CAPSULE_ID,
    literature_search_capsule_definition_checksum,
    literature_search_contract_checksum,
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
    repository = uow.workflow_foundation
    repository.add_definition(_definition(timestamp))
    repository.add_definition_version(_definition_version(timestamp))
    repository.add_capsule_version(_capsule_version(timestamp))

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
            capsule_id=LITERATURE_SEARCH_CAPSULE_ID if package else None,
            capsule_version=TEMPLATE_VERSION if package else None,
            desired_state=WorkflowInstanceDesiredState.ACTIVE,
            display_name="Literature Search",
            created_manifest_revision=0,
            retired_manifest_revision=None,
            legacy_package_id=package.package_id if package else None,
            created_at=_parse_time(project.created_at),
            updated_at=_parse_time(project.updated_at),
        )
        repository.add_workflow_instance(instance)
        instances.append(instance)
    return tuple(instances)


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
