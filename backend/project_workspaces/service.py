"""Deterministic built-in seed and legacy Project reconciliation."""

from __future__ import annotations

from dataclasses import replace
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
from backend.resource_references.contracts import (
    ResourceKind,
    ResourceProvider,
    WorkflowResourceRequirement,
)

from .contracts import (
    CapsuleTrustClassification,
    CloudProject,
    CloudProjectStatus,
    CoreCapabilityMaturity,
    ProjectWorkflowInstance,
    SkillReviewStatus,
    SkillTrustTier,
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
    idea_discovery_v0_3_capsule,
    idea_discovery_v0_3_definition_version,
    idea_discovery_v0_3_requirement,
    idea_discovery_v0_4_capsule,
    idea_discovery_v0_4_definition_version,
    idea_discovery_v0_4_requirement,
    idea_discovery_v0_5_capsule,
    literature_search_capsule as production_literature_search_capsule,
    literature_search_definition_version as production_literature_search_version,
    literature_search_v0_5_definition_version,
    literature_search_v0_7_capsule,
    SCAFFOLD_WORKFLOWS,
    scaffold_capsule,
    scaffold_definition,
    scaffold_definition_version,
    scaffold_requirements,
    skill_backed_scaffold_capsule,
    skill_backed_scaffold_definition_version,
    skill_backed_scaffold_requirements,
    interactive_scaffold_capsule,
    completion_scaffold_capsule,
    experiment_resource_artifact_requirements,
    experiment_resource_capsule,
    experiment_resource_definition_version,
    experiment_interactive_capsule,
    experiment_completion_capsule,
    real_experiment_artifact_requirement,
    real_experiment_capsule,
    real_experiment_definition_version,
    real_writing_artifact_requirements,
    real_writing_capsule,
    real_writing_definition_version,
    real_review_artifact_requirements,
    real_review_capsule,
    real_review_definition_version,
    writing_revision_artifact_requirements,
    writing_revision_capsule,
    writing_revision_definition_version,
)
from backend.workflow_packages.production_workflows import (
    EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
    EXPERIMENT_WORKFLOW_ID,
    REAL_EXPERIMENT_BUGFIX_CAPSULE_VERSION,
    REAL_EXPERIMENT_V0_7_CAPSULE_CHECKSUM,
    REAL_EXPERIMENT_V0_7_CAPSULE_ID,
    REAL_EXPERIMENT_WORKFLOW_VERSION,
    REAL_WRITING_WORKFLOW_VERSION,
    REAL_REVIEW_WORKFLOW_VERSION,
    WRITING_REVISION_WORKFLOW_VERSION,
    REVIEW_WORKFLOW_ID,
    WRITING_WORKFLOW_ID,
)
from .skills import (
    PRODUCTION_SKILLS,
    RESEARCH_ARTIFACT_PROVENANCE_SKILL_ID,
    production_skill_pins,
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
    current_idea_capsule = idea_discovery_v0_3_capsule(timestamp)
    forward_idea_version = idea_discovery_v0_3_definition_version(timestamp)
    forward_idea_capsule = idea_discovery_v0_4_capsule(timestamp)
    durable_literature_version = literature_search_v0_5_definition_version(timestamp)
    durable_literature_capsule = literature_search_v0_7_capsule(timestamp)
    durable_idea_version = idea_discovery_v0_4_definition_version(timestamp)
    durable_idea_capsule = idea_discovery_v0_5_capsule(timestamp)
    repository = uow.workflow_foundation
    repository.add_definition_version(literature_version)
    repository.add_capsule_version(literature_capsule)
    repository.add_definition(idea_definition)
    repository.add_definition_version(legacy_idea_version)
    repository.add_capsule_version(legacy_idea_capsule)
    repository.add_definition_version(idea_version)
    repository.add_capsule_version(idea_capsule)
    repository.add_capsule_version(current_idea_capsule)
    repository.add_definition_version(forward_idea_version)
    repository.add_capsule_version(forward_idea_capsule)
    repository.add_definition_version(durable_literature_version)
    repository.add_capsule_version(durable_literature_capsule)
    repository.add_definition_version(durable_idea_version)
    repository.add_capsule_version(durable_idea_capsule)
    for requirement in (
        idea_discovery_requirement(timestamp),
        idea_discovery_v0_2_requirement(timestamp),
        idea_discovery_v0_3_requirement(timestamp),
        idea_discovery_v0_4_requirement(timestamp),
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
            existing_requirement.content_precondition,
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
            requirement.content_precondition,
        ):
            raise WorkflowFoundationConflictError(
                "Idea Discovery Artifact requirement immutable-content conflict"
            )
    for workflow_id in SCAFFOLD_WORKFLOWS:
        repository.add_definition(scaffold_definition(workflow_id, timestamp))
        repository.add_definition_version(
            scaffold_definition_version(workflow_id, timestamp)
        )
        repository.add_capsule_version(scaffold_capsule(workflow_id, timestamp))
        repository.add_definition_version(
            skill_backed_scaffold_definition_version(workflow_id, timestamp)
        )
        repository.add_capsule_version(
            skill_backed_scaffold_capsule(workflow_id, timestamp)
        )
        if workflow_id in {
            "writing-local-experimental", "review-local-experimental",
        }:
            repository.add_capsule_version(
                interactive_scaffold_capsule(workflow_id, timestamp)
            )
            repository.add_capsule_version(
                completion_scaffold_capsule(workflow_id, timestamp)
            )
        for asset in PRODUCTION_SKILLS:
            definition = asset.definition(timestamp)
            version = asset.skill_version(timestamp)
            if (
                definition.trust_tier is not SkillTrustTier.BUILT_IN_REVIEWED
                or version.trust_tier is not SkillTrustTier.BUILT_IN_REVIEWED
                or version.review_status is not SkillReviewStatus.REVIEWED
            ):
                raise WorkflowFoundationConflictError(
                    "Only reviewed built-in Skills may be seeded"
                )
            repository.add_skill_definition(definition)
            repository.add_skill_version(version)
        for pin in production_skill_pins(
            workflow_id, "0.2.0", timestamp
        ):
            version = repository.get_skill_version(
                pin.skill_id, pin.skill_version
            )
            if version is None or version.content_checksum != pin.skill_checksum:
                raise WorkflowFoundationConflictError(
                    "Workflow Skill pin checksum does not match Skill Version authority"
                )
            repository.add_workflow_skill_pin(pin)
        for requirement in (
            *scaffold_requirements(workflow_id, timestamp),
            *skill_backed_scaffold_requirements(workflow_id, timestamp),
        ):
            existing_requirement = uow.artifact_references.get_requirement(
                requirement.workflow_definition_id,
                requirement.workflow_version,
                requirement.requirement_key,
            )
            if existing_requirement is None:
                uow.artifact_references.add_requirement(requirement)
            elif _requirement_content(existing_requirement) != _requirement_content(
                requirement
            ):
                raise WorkflowFoundationConflictError(
                    "Scaffold Workflow Artifact requirement immutable-content conflict"
                )
    repository.add_definition_version(
        experiment_resource_definition_version(timestamp)
    )
    repository.add_capsule_version(experiment_resource_capsule(timestamp))
    repository.add_capsule_version(experiment_interactive_capsule(timestamp))
    repository.add_capsule_version(experiment_completion_capsule(timestamp))
    for pin in production_skill_pins(
        EXPERIMENT_WORKFLOW_ID, EXPERIMENT_RESOURCE_WORKFLOW_VERSION, timestamp
    ):
        repository.add_workflow_skill_pin(pin)
    for requirement in experiment_resource_artifact_requirements(timestamp):
        existing_requirement = uow.artifact_references.get_requirement(
            requirement.workflow_definition_id,
            requirement.workflow_version,
            requirement.requirement_key,
        )
        if existing_requirement is None:
            uow.artifact_references.add_requirement(requirement)
        elif _requirement_content(existing_requirement) != _requirement_content(
            requirement
        ):
            raise WorkflowFoundationConflictError(
                "Experiment 0.3 Artifact requirement immutable-content conflict"
            )
    resource_requirements = (
        ("source_repository", ResourceKind.SOURCE_REPOSITORY,
         (ResourceProvider.GITHUB, ResourceProvider.LOCAL_TEST)),
        ("dataset", ResourceKind.DATASET,
         (ResourceProvider.HUGGING_FACE, ResourceProvider.LOCAL_TEST)),
        ("model", ResourceKind.MODEL,
         (ResourceProvider.HUGGING_FACE, ResourceProvider.LOCAL_TEST)),
        ("checkpoint", ResourceKind.CHECKPOINT,
         (ResourceProvider.HUGGING_FACE, ResourceProvider.LOCAL_TEST)),
    )
    for key, kind, providers in resource_requirements:
        requirement = WorkflowResourceRequirement(
            workflow_definition_id=EXPERIMENT_WORKFLOW_ID,
            workflow_version=EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
            requirement_key=key,
            resource_kind=kind,
            cardinality_min=0,
            cardinality_max=1,
            required=False,
            allowed_providers=providers,
            usage_description=(
                "Optional external asset reference for the non-executing "
                "Idea Experiment scaffold."
            ),
            created_at=timestamp,
            updated_at=timestamp,
        )
        existing = uow.resource_references.get_requirement(
            requirement.workflow_definition_id,
            requirement.workflow_version,
            requirement.requirement_key,
        )
        if existing is None:
            uow.resource_references.add_requirement(requirement)
        elif (
            existing.workflow_definition_id,
            existing.workflow_version,
            existing.requirement_key,
            existing.resource_kind,
            existing.cardinality_min,
            existing.cardinality_max,
            existing.required,
            existing.allowed_providers,
            existing.usage_description,
        ) != (
            requirement.workflow_definition_id,
            requirement.workflow_version,
            requirement.requirement_key,
            requirement.resource_kind,
            requirement.cardinality_min,
            requirement.cardinality_max,
            requirement.required,
            requirement.allowed_providers,
            requirement.usage_description,
        ):
            raise WorkflowFoundationConflictError(
                "Experiment Resource requirement immutable-content conflict"
            )
    repository.add_definition_version(real_experiment_definition_version(timestamp))
    historical_real_experiment = real_experiment_capsule(timestamp)
    repository.add_capsule_version(historical_real_experiment)
    repository.add_capsule_version(replace(
        historical_real_experiment,
        capsule_id=REAL_EXPERIMENT_V0_7_CAPSULE_ID,
        capsule_version=REAL_EXPERIMENT_BUGFIX_CAPSULE_VERSION,
        definition_checksum=REAL_EXPERIMENT_V0_7_CAPSULE_CHECKSUM,
    ))
    for pin in production_skill_pins(
        EXPERIMENT_WORKFLOW_ID, REAL_EXPERIMENT_WORKFLOW_VERSION, timestamp
    ):
        if pin.skill_id == RESEARCH_ARTIFACT_PROVENANCE_SKILL_ID:
            repository.add_workflow_skill_pin(pin)
    real_artifact_requirement = real_experiment_artifact_requirement(timestamp)
    existing_artifact_requirement = uow.artifact_references.get_requirement(
        real_artifact_requirement.workflow_definition_id,
        real_artifact_requirement.workflow_version,
        real_artifact_requirement.requirement_key,
    )
    if existing_artifact_requirement is None:
        uow.artifact_references.add_requirement(real_artifact_requirement)
    elif _requirement_content(existing_artifact_requirement) != _requirement_content(
        real_artifact_requirement
    ):
        raise WorkflowFoundationConflictError(
            "Real Experiment Artifact requirement immutable-content conflict"
        )
    real_resource_requirement = WorkflowResourceRequirement(
        workflow_definition_id=EXPERIMENT_WORKFLOW_ID,
        workflow_version=REAL_EXPERIMENT_WORKFLOW_VERSION,
        requirement_key="source_repository",
        resource_kind=ResourceKind.SOURCE_REPOSITORY,
        cardinality_min=1,
        cardinality_max=1,
        required=True,
        allowed_providers=(ResourceProvider.GITHUB,),
        usage_description=(
            "One exact owner-staged local Experiment Package; Cloud metadata alone "
            "is not execution readiness."
        ),
        created_at=timestamp,
        updated_at=timestamp,
    )
    existing_resource_requirement = uow.resource_references.get_requirement(
        real_resource_requirement.workflow_definition_id,
        real_resource_requirement.workflow_version,
        real_resource_requirement.requirement_key,
    )
    if existing_resource_requirement is None:
        uow.resource_references.add_requirement(real_resource_requirement)
    elif _resource_requirement_content(existing_resource_requirement) != _resource_requirement_content(
        real_resource_requirement
    ):
        raise WorkflowFoundationConflictError(
            "Real Experiment Resource requirement immutable-content conflict"
        )
    repository.add_definition_version(real_writing_definition_version(timestamp))
    repository.add_capsule_version(real_writing_capsule(timestamp))
    for pin in production_skill_pins(
        WRITING_WORKFLOW_ID, REAL_WRITING_WORKFLOW_VERSION, timestamp
    ):
        if pin.skill_id == RESEARCH_ARTIFACT_PROVENANCE_SKILL_ID:
            repository.add_workflow_skill_pin(replace(
                pin,
                purpose="Use exact bound evidence and preserve Artifact provenance.",
            ))
    for requirement in real_writing_artifact_requirements(timestamp):
        existing = uow.artifact_references.get_requirement(
            requirement.workflow_definition_id,
            requirement.workflow_version,
            requirement.requirement_key,
        )
        if existing is None:
            uow.artifact_references.add_requirement(requirement)
        elif _requirement_content(existing) != _requirement_content(requirement):
            raise WorkflowFoundationConflictError(
                "Real Writing Artifact requirement immutable-content conflict"
            )
    repository.add_definition_version(writing_revision_definition_version(timestamp))
    repository.add_capsule_version(writing_revision_capsule(timestamp))
    for pin in production_skill_pins(
        WRITING_WORKFLOW_ID, WRITING_REVISION_WORKFLOW_VERSION, timestamp
    ):
        if pin.skill_id == RESEARCH_ARTIFACT_PROVENANCE_SKILL_ID:
            repository.add_workflow_skill_pin(replace(
                pin,
                purpose="Revise exact claims while preserving Artifact provenance.",
            ))
    for requirement in writing_revision_artifact_requirements(timestamp):
        existing = uow.artifact_references.get_requirement(
            requirement.workflow_definition_id,
            requirement.workflow_version,
            requirement.requirement_key,
        )
        if existing is None:
            uow.artifact_references.add_requirement(requirement)
        elif _requirement_content(existing) != _requirement_content(requirement):
            raise WorkflowFoundationConflictError(
                "Writing Revision Artifact requirement immutable-content conflict"
            )
    repository.add_definition_version(real_review_definition_version(timestamp))
    repository.add_capsule_version(real_review_capsule(timestamp))
    for pin in production_skill_pins(
        REVIEW_WORKFLOW_ID, REAL_REVIEW_WORKFLOW_VERSION, timestamp
    ):
        if pin.skill_id == RESEARCH_ARTIFACT_PROVENANCE_SKILL_ID:
            repository.add_workflow_skill_pin(replace(
                pin,
                purpose="Audit exact bound evidence and preserve Artifact provenance.",
            ))
    for requirement in real_review_artifact_requirements(timestamp):
        existing = uow.artifact_references.get_requirement(
            requirement.workflow_definition_id,
            requirement.workflow_version,
            requirement.requirement_key,
        )
        if existing is None:
            uow.artifact_references.add_requirement(requirement)
        elif _requirement_content(existing) != _requirement_content(requirement):
            raise WorkflowFoundationConflictError(
                "Real Review Artifact requirement immutable-content conflict"
            )
    from .forward_downstream import (
        artifact_requirements as forward_artifact_requirements,
        capsule_version as forward_capsule_version,
        definition_version as forward_definition_version,
    )
    from backend.workflow_packages.forward_downstream_publication import (
        INITIAL_WRITING_VERSION, REVIEW_VERSION as FORWARD_REVIEW_VERSION,
    )
    from backend.workflow_packages.revision_optional_support_publication import (
        WRITING_REVISION_VERSION as FORWARD_REVISION_VERSION,
    )
    for role, workflow_id, workflow_version in (
        ("initial-writing", WRITING_WORKFLOW_ID, INITIAL_WRITING_VERSION),
        ("review", REVIEW_WORKFLOW_ID, FORWARD_REVIEW_VERSION),
        ("revision", WRITING_WORKFLOW_ID, FORWARD_REVISION_VERSION),
    ):
        repository.add_definition_version(forward_definition_version(role, timestamp))
        repository.add_capsule_version(forward_capsule_version(role, timestamp))
        for pin in production_skill_pins(workflow_id, workflow_version, timestamp):
            if pin.skill_id == RESEARCH_ARTIFACT_PROVENANCE_SKILL_ID:
                repository.add_workflow_skill_pin(replace(
                    pin,
                    purpose="Preserve exact v5 evidence and downstream Artifact provenance.",
                ))
        for requirement in forward_artifact_requirements(role, timestamp):
            existing = uow.artifact_references.get_requirement(
                requirement.workflow_definition_id, requirement.workflow_version,
                requirement.requirement_key,
            )
            if existing is None:
                uow.artifact_references.add_requirement(requirement)
            elif _requirement_content(existing) != _requirement_content(requirement):
                raise WorkflowFoundationConflictError(
                    "Forward downstream Artifact requirement immutable-content conflict"
                )
    from .generic_harness_foundation import (
        artifact_requirement as generic_harness_artifact_requirement,
        capsule_version as generic_harness_capsule_version,
        definition_version as generic_harness_definition_version,
        skill_pin as generic_harness_skill_pin,
    )
    from backend.workflow_packages.generic_experiment_publication import (
        REFERENCE_CAPABILITY_SKILL,
    )

    reference_asset = REFERENCE_CAPABILITY_SKILL
    repository.add_skill_definition(reference_asset.definition(timestamp))
    repository.add_skill_version(reference_asset.skill_version(timestamp))
    repository.add_definition_version(generic_harness_definition_version(timestamp))
    repository.add_capsule_version(generic_harness_capsule_version(timestamp))
    reference_pin = generic_harness_skill_pin(timestamp)
    reference_version = repository.get_skill_version(
        reference_pin.skill_id, reference_pin.skill_version
    )
    if (
        reference_version is None
        or reference_version.content_checksum != reference_pin.skill_checksum
    ):
        raise WorkflowFoundationConflictError(
            "Generic Harness reference Capability Skill checksum conflict"
        )
    repository.add_workflow_skill_pin(reference_pin)
    generic_requirement = generic_harness_artifact_requirement(timestamp)
    existing = uow.artifact_references.get_requirement(
        generic_requirement.workflow_definition_id,
        generic_requirement.workflow_version,
        generic_requirement.requirement_key,
    )
    if existing is None:
        uow.artifact_references.add_requirement(generic_requirement)
    elif _requirement_content(existing) != _requirement_content(generic_requirement):
        raise WorkflowFoundationConflictError(
            "Generic Harness Artifact requirement immutable-content conflict"
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


def _requirement_content(value):
    return (
        value.workflow_definition_id,
        value.workflow_version,
        value.requirement_key,
        value.artifact_type,
        value.compatibility_mode,
        value.schema_constraint,
        value.cardinality_min,
        value.cardinality_max,
        value.required,
        value.materialization_mode,
        value.target_relative_path,
        value.content_precondition,
    )


def _resource_requirement_content(value):
    return (
        value.workflow_definition_id,
        value.workflow_version,
        value.requirement_key,
        value.resource_kind,
        value.cardinality_min,
        value.cardinality_max,
        value.required,
        value.allowed_providers,
        value.usage_description,
    )
