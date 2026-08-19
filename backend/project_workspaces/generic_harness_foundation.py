"""Cloud publication records for the forward Generic Harness Experiment."""

from __future__ import annotations

from datetime import datetime

from backend.artifact_references.contracts import (
    CompatibilityMode,
    MaterializationMode,
    WorkflowArtifactRequirement,
)
from backend.workflow_packages.contracts import PACKAGE_SCHEMA_VERSION
from backend.workflow_packages.generic_experiment_publication import (
    REFERENCE_CAPABILITY_SKILL,
)
from backend.workflow_packages.generic_harness_contracts import (
    GENERIC_HARNESS_CLASSIFICATION,
)
from backend.workflow_packages.generic_harness_publication import (
    GENERIC_HARNESS_ARTIFACT_TYPE,
    GENERIC_HARNESS_CAPSULE_CHECKSUM,
    GENERIC_HARNESS_CAPSULE_ID,
    GENERIC_HARNESS_CAPSULE_VERSION,
    GENERIC_HARNESS_CONTRACT_CHECKSUM,
    GENERIC_HARNESS_WORKFLOW_VERSION,
)
from backend.workflow_packages.generic_experiment_v5_publication import (
    BOUNDED_EVIDENCE_SCHEMA,
)
from backend.workflow_packages.production_workflows import (
    EXPERIMENT_TEMPLATE_ID,
    EXPERIMENT_WORKFLOW_ID,
    scaffold_output_contract,
)

from .contracts import (
    CapsuleTrustClassification,
    CoreCapabilityMaturity,
    WorkflowCapsuleVersion,
    WorkflowDefinitionVersion,
    WorkflowDefinitionVersionSkillPin,
    WorkflowReviewStatus,
)

GENERIC_HARNESS_MUTABLE_ROOTS = (
    "inputs",
    "outputs",
    "memory/context.md",
    "memory/input-provenance.json",
    "memory/research-objective.json",
    "memory/methodology-proposal.json",
    "memory/methodology.json",
    "memory/capability-selection.json",
    "memory/generic-checkpoint.json",
    "memory/design-approval.json",
    "memory/requirements",
    "memory/preparation",
    "memory/runtime",
    "memory/execution-plan.json",
    "memory/run-approval.json",
    "memory/execution",
    "memory/evaluation",
    "memory/result-review.json",
    "memory/bounded-scientific-evidence.json",
    "memory/current-artifact.json",
    "memory/progress",
)

GENERIC_HARNESS_CAPABILITY_REQUIREMENTS = (
    "progress.upload/v0.2",
    "artifact.materialize/v0.1",
    "artifact.publish/v0.1",
    "execute.local-foreground/v0.1",
    "network.no-egress/v0.1",
    "experiment.generic-harness/v0.1",
    "experiment.local-continuation/v0.1",
)


def _artifact_outputs() -> list[dict[str, str]]:
    return [scaffold_output_contract(GENERIC_HARNESS_ARTIFACT_TYPE)]


def definition_version(now: datetime) -> WorkflowDefinitionVersion:
    return WorkflowDefinitionVersion(
        workflow_definition_id=EXPERIMENT_WORKFLOW_ID,
        version=GENERIC_HARNESS_WORKFLOW_VERSION,
        contract_checksum=GENERIC_HARNESS_CONTRACT_CHECKSUM,
        input_schema_id="selected-research-idea/v1",
        output_schema_id=GENERIC_HARNESS_ARTIFACT_TYPE,
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "artifact_outputs": _artifact_outputs(),
            "experiment_core": "RESEARCH_DOMAIN_AGNOSTIC",
            "capability_interface": "reagent.experiment-capability/v0.1",
            "bounded_scientific_evidence_schema": BOUNDED_EVIDENCE_SCHEMA,
            "evidence_authority": "LOCAL_FINAL_ARTIFACT",
            "presentation_companion_authoritative": False,
            "implementation_path": (
                "EXACT_REVIEWED_FAST_PATH_OR_SYSTEM_GENERIC_HARNESS"
            ),
            "generic_harness_classification": GENERIC_HARNESS_CLASSIFICATION,
            "user_skill_authority": False,
            "network_policy": "DISABLED",
            "dependency_installation": False,
            "automatic_retry": False,
            "default_project_setup": True,
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        core_capability_maturity=CoreCapabilityMaturity.REVIEWED_CORE,
        published_at=now,
        created_at=now,
        updated_at=now,
    )


def capsule_version(now: datetime) -> WorkflowCapsuleVersion:
    asset = REFERENCE_CAPABILITY_SKILL
    return WorkflowCapsuleVersion(
        capsule_id=GENERIC_HARNESS_CAPSULE_ID,
        capsule_version=GENERIC_HARNESS_CAPSULE_VERSION,
        workflow_definition_id=EXPERIMENT_WORKFLOW_ID,
        workflow_version=GENERIC_HARNESS_WORKFLOW_VERSION,
        definition_checksum=GENERIC_HARNESS_CAPSULE_CHECKSUM,
        archive_size_bytes=0,
        archive_media_type="application/zip",
        mutable_roots=GENERIC_HARNESS_MUTABLE_ROOTS,
        capability_requirements=GENERIC_HARNESS_CAPABILITY_REQUIREMENTS,
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "package_template_id": EXPERIMENT_TEMPLATE_ID,
            "trust_classification": (
                CapsuleTrustClassification.TRUSTED_BUILT_IN_UNSIGNED.value
            ),
            "artifact_outputs": _artifact_outputs(),
            "core_capability_maturity": CoreCapabilityMaturity.REVIEWED_CORE.value,
            "capability_interface": "reagent.experiment-capability/v0.1",
            "capability_resolution": (
                "EXACT_REVIEWED_FAST_PATH_OR_SYSTEM_GENERIC_HARNESS"
            ),
            "bounded_scientific_evidence_schema": BOUNDED_EVIDENCE_SCHEMA,
            "evidence_authority": "LOCAL_FINAL_ARTIFACT",
            "presentation_companion_authoritative": False,
            "skill_pins": [{
                "skill_id": asset.skill_id,
                "skill_version": asset.version,
                "skill_checksum": asset.content_checksum,
                "trust": "BUILT_IN_REVIEWED",
                "classification": "REFERENCE_EXPERIMENT_CAPABILITY",
            }],
            "generic_harness_classification": GENERIC_HARNESS_CLASSIFICATION,
            "generic_harness_scientific_authority": False,
            "user_skill_authority": False,
            "managed_execution_namespace": (
                ".reagent/experiments/<workflow-instance-id>"
            ),
            "execution_boundary": "UNCHANGED_EXISTING_BOUNDED_RUNNER",
            "dependency_installation": False,
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=False,
        created_at=now,
        updated_at=now,
    )


def skill_pin(now: datetime) -> WorkflowDefinitionVersionSkillPin:
    asset = REFERENCE_CAPABILITY_SKILL
    return WorkflowDefinitionVersionSkillPin(
        workflow_definition_id=EXPERIMENT_WORKFLOW_ID,
        workflow_version=GENERIC_HARNESS_WORKFLOW_VERSION,
        pin_order=0,
        skill_id=asset.skill_id,
        skill_version=asset.version,
        skill_checksum=asset.content_checksum,
        purpose=(
            "Provide an optional exact reviewed Experiment Capability fast path; "
            "the system Generic Harness remains independently available."
        ),
        created_at=now,
    )


def artifact_requirement(now: datetime) -> WorkflowArtifactRequirement:
    return WorkflowArtifactRequirement(
        workflow_definition_id=EXPERIMENT_WORKFLOW_ID,
        workflow_version=GENERIC_HARNESS_WORKFLOW_VERSION,
        requirement_key="research_idea",
        artifact_type="selected-research-idea/v1",
        compatibility_mode=CompatibilityMode.EXACT,
        schema_constraint="selected-research-idea/v1",
        cardinality_min=1,
        cardinality_max=1,
        required=True,
        materialization_mode=MaterializationMode.VERIFIED_COPY,
        target_relative_path="inputs/selected-research-idea.json",
        created_at=now,
        updated_at=now,
    )
