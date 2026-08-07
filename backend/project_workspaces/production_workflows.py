"""Deterministic reviewed production Workflow pins introduced by NIGHT-B7."""

from __future__ import annotations

from datetime import datetime

from backend.artifact_references.contracts import (
    CompatibilityMode,
    MaterializationMode,
    WorkflowArtifactRequirement,
)
from backend.workflow_packages.contracts import PACKAGE_SCHEMA_VERSION
from backend.workflow_packages.production_workflows import (
    IDEA_DISCOVERY_CAPSULE_VERSION,
    IDEA_DISCOVERY_TEMPLATE_ID,
    IDEA_DISCOVERY_WORKFLOW_ID,
    IDEA_DISCOVERY_WORKFLOW_VERSION,
    IDEA_INPUT_TARGET,
    LITERATURE_SEARCH_CAPSULE_VERSION,
    LITERATURE_SEARCH_TEMPLATE_ID,
    LITERATURE_SEARCH_WORKFLOW_ID,
    LITERATURE_SEARCH_WORKFLOW_VERSION,
    SELECTED_PAPER_LIBRARY_SCHEMA,
    SELECTED_PAPER_LIBRARY_TYPE,
    idea_discovery_contract_checksum,
    literature_search_contract_checksum,
    selected_paper_library_output_contract,
)
from backend.workflow_packages.serialization import canonical_hash

from .contracts import (
    CapsuleTrustClassification,
    WorkflowCapsuleVersion,
    WorkflowDefinition,
    WorkflowDefinitionLifecycle,
    WorkflowDefinitionVersion,
    WorkflowReviewStatus,
)

IDEA_DISCOVERY_DEFINITION_ID = IDEA_DISCOVERY_WORKFLOW_ID

LITERATURE_SEARCH_V0_6_CAPSULE_CHECKSUM = canonical_hash(
    {
        "generator_version": "reagent-literature-search-local-experimental-compiler/0.6.0",
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "package_template_id": LITERATURE_SEARCH_TEMPLATE_ID,
        "package_template_version": LITERATURE_SEARCH_CAPSULE_VERSION,
        "workflow_checksum": literature_search_contract_checksum(),
        "artifact_outputs": [selected_paper_library_output_contract()],
    }
)
LITERATURE_SEARCH_V0_6_CAPSULE_ID = (
    "capsule-" + LITERATURE_SEARCH_V0_6_CAPSULE_CHECKSUM[7:39]
)

IDEA_DISCOVERY_CAPSULE_CHECKSUM = canonical_hash(
    {
        "generator_version": "reagent-idea-discovery-local-experimental-compiler/0.1.0",
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "package_template_id": IDEA_DISCOVERY_TEMPLATE_ID,
        "package_template_version": IDEA_DISCOVERY_CAPSULE_VERSION,
        "workflow_checksum": idea_discovery_contract_checksum(),
        "artifact_input": {
            "requirement_key": "paper_library",
            "artifact_type": SELECTED_PAPER_LIBRARY_TYPE,
            "artifact_schema": SELECTED_PAPER_LIBRARY_SCHEMA,
            "target_relative_path": IDEA_INPUT_TARGET,
            "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
            "materialization_mode": "VERIFIED_COPY",
        },
    }
)
IDEA_DISCOVERY_CAPSULE_ID = "capsule-" + IDEA_DISCOVERY_CAPSULE_CHECKSUM[7:39]


def literature_search_definition_version(now: datetime) -> WorkflowDefinitionVersion:
    return WorkflowDefinitionVersion(
        workflow_definition_id=LITERATURE_SEARCH_WORKFLOW_ID,
        version=LITERATURE_SEARCH_WORKFLOW_VERSION,
        contract_checksum=literature_search_contract_checksum(),
        input_schema_id="research-request/v0.2",
        output_schema_id="literature-search-report/v0.2",
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "production_artifact_type": SELECTED_PAPER_LIBRARY_TYPE,
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        published_at=now,
        created_at=now,
        updated_at=now,
    )


def literature_search_capsule(now: datetime) -> WorkflowCapsuleVersion:
    return WorkflowCapsuleVersion(
        capsule_id=LITERATURE_SEARCH_V0_6_CAPSULE_ID,
        capsule_version=LITERATURE_SEARCH_CAPSULE_VERSION,
        workflow_definition_id=LITERATURE_SEARCH_WORKFLOW_ID,
        workflow_version=LITERATURE_SEARCH_WORKFLOW_VERSION,
        definition_checksum=LITERATURE_SEARCH_V0_6_CAPSULE_CHECKSUM,
        archive_size_bytes=0,
        archive_media_type="application/zip",
        mutable_roots=(
            "memory/context.md", "memory/progress", "memory/round-control.json",
            "memory/search", "outputs",
        ),
        capability_requirements=(
            "paper.search/v0.1", "progress.read/v0.1", "progress.upload/v0.2",
        ),
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "package_template_id": LITERATURE_SEARCH_TEMPLATE_ID,
            "trust_classification": CapsuleTrustClassification.TRUSTED_BUILT_IN_UNSIGNED.value,
            "artifact_outputs": [selected_paper_library_output_contract()],
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=False,
        created_at=now,
        updated_at=now,
    )


def idea_discovery_definition(now: datetime) -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_definition_id=IDEA_DISCOVERY_DEFINITION_ID,
        display_name="Idea Discovery",
        description=(
            "Interactively develop evidence-grounded candidate research directions "
            "from an explicitly selected literature Artifact."
        ),
        lifecycle=WorkflowDefinitionLifecycle.AVAILABLE,
        allows_multiple_instances=True,
        created_at=now,
        updated_at=now,
    )


def idea_discovery_definition_version(now: datetime) -> WorkflowDefinitionVersion:
    return WorkflowDefinitionVersion(
        workflow_definition_id=IDEA_DISCOVERY_DEFINITION_ID,
        version=IDEA_DISCOVERY_WORKFLOW_VERSION,
        contract_checksum=idea_discovery_contract_checksum(),
        input_schema_id=SELECTED_PAPER_LIBRARY_SCHEMA,
        output_schema_id="candidate-ideas/v0.1",
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "artifact_requirement_key": "paper_library",
            "novelty_claim_policy": "GLOBAL_NOVELTY_NOT_PROVEN",
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        published_at=now,
        created_at=now,
        updated_at=now,
    )


def idea_discovery_capsule(now: datetime) -> WorkflowCapsuleVersion:
    return WorkflowCapsuleVersion(
        capsule_id=IDEA_DISCOVERY_CAPSULE_ID,
        capsule_version=IDEA_DISCOVERY_CAPSULE_VERSION,
        workflow_definition_id=IDEA_DISCOVERY_DEFINITION_ID,
        workflow_version=IDEA_DISCOVERY_WORKFLOW_VERSION,
        definition_checksum=IDEA_DISCOVERY_CAPSULE_CHECKSUM,
        archive_size_bytes=0,
        archive_media_type="application/zip",
        mutable_roots=("memory/context.md", "memory/progress", "outputs", "inputs"),
        capability_requirements=("progress.upload/v0.2", "artifact.materialize/v0.1"),
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "package_template_id": IDEA_DISCOVERY_TEMPLATE_ID,
            "trust_classification": CapsuleTrustClassification.TRUSTED_BUILT_IN_UNSIGNED.value,
            "artifact_requirements": [{
                "requirement_key": "paper_library",
                "artifact_type": SELECTED_PAPER_LIBRARY_TYPE,
                "artifact_schema_version": SELECTED_PAPER_LIBRARY_SCHEMA,
                "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
                "materialization_mode": "VERIFIED_COPY",
                "target_relative_path": IDEA_INPUT_TARGET,
            }],
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=False,
        created_at=now,
        updated_at=now,
    )


def idea_discovery_requirement(now: datetime) -> WorkflowArtifactRequirement:
    return WorkflowArtifactRequirement(
        workflow_definition_id=IDEA_DISCOVERY_DEFINITION_ID,
        workflow_version=IDEA_DISCOVERY_WORKFLOW_VERSION,
        requirement_key="paper_library",
        artifact_type=SELECTED_PAPER_LIBRARY_TYPE,
        compatibility_mode=CompatibilityMode.EXACT,
        schema_constraint=SELECTED_PAPER_LIBRARY_SCHEMA,
        cardinality_min=1,
        cardinality_max=1,
        required=True,
        materialization_mode=MaterializationMode.VERIFIED_COPY,
        target_relative_path=IDEA_INPUT_TARGET,
        created_at=now,
        updated_at=now,
    )
