"""Deterministic reviewed production Workflow pins introduced by NIGHT-B7."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from backend.artifact_references.contracts import (
    CompatibilityMode,
    MaterializationMode,
    PAPER_LIBRARY_NONEMPTY_PRECONDITION_SCHEMA,
    PAPER_LIBRARY_QUALIFICATION_SCHEMA,
    WorkflowArtifactRequirement,
)
from backend.workflow_packages.contracts import PACKAGE_SCHEMA_VERSION
from backend.workflow_packages.production_workflows import (
    IDEA_DISCOVERY_CAPSULE_VERSION,
    IDEA_DISCOVERY_TEMPLATE_ID,
    IDEA_DISCOVERY_WORKFLOW_ID,
    IDEA_DISCOVERY_WORKFLOW_VERSION,
    IDEA_DISCOVERY_V0_2_CAPSULE_VERSION,
    IDEA_DISCOVERY_V0_3_CAPSULE_VERSION,
    IDEA_DISCOVERY_V0_3_WORKFLOW_VERSION,
    IDEA_DISCOVERY_V0_4_CAPSULE_VERSION,
    IDEA_DISCOVERY_V0_2_WORKFLOW_VERSION,
    IDEA_INPUT_TARGET,
    EXPERIMENT_RECORD_TYPE,
    EXPERIMENT_RECORD_V2_TYPE,
    EXPERIMENT_INTERACTIVE_CAPSULE_VERSION,
    EXPERIMENT_COMPLETION_CAPSULE_VERSION,
    EXPERIMENT_RESOURCE_CAPSULE_VERSION,
    EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
    EXPERIMENT_REQUIREMENTS,
    EXPERIMENT_TEMPLATE_ID,
    EXPERIMENT_WORKFLOW_ID,
    REAL_EXPERIMENT_CAPSULE_VERSION,
    REAL_EXPERIMENT_WORKFLOW_VERSION,
    REAL_WRITING_CAPSULE_CHECKSUM as PACKAGE_REAL_WRITING_CAPSULE_CHECKSUM,
    REAL_WRITING_CAPSULE_ID as PACKAGE_REAL_WRITING_CAPSULE_ID,
    REAL_WRITING_CAPSULE_VERSION,
    REAL_WRITING_REQUIREMENTS,
    REAL_WRITING_WORKFLOW_VERSION,
    REAL_REVIEW_CAPSULE_CHECKSUM as PACKAGE_REAL_REVIEW_CAPSULE_CHECKSUM,
    REAL_REVIEW_CAPSULE_ID as PACKAGE_REAL_REVIEW_CAPSULE_ID,
    REAL_REVIEW_CAPSULE_VERSION,
    REAL_REVIEW_REQUIREMENTS,
    REAL_REVIEW_WORKFLOW_VERSION,
    WRITING_REVISION_CAPSULE_CHECKSUM as PACKAGE_WRITING_REVISION_CAPSULE_CHECKSUM,
    WRITING_REVISION_CAPSULE_ID as PACKAGE_WRITING_REVISION_CAPSULE_ID,
    WRITING_REVISION_CAPSULE_VERSION,
    WRITING_REVISION_REQUIREMENTS,
    WRITING_REVISION_WORKFLOW_VERSION,
    LITERATURE_SEARCH_CAPSULE_VERSION,
    LITERATURE_SEARCH_TEMPLATE_ID,
    LITERATURE_SEARCH_WORKFLOW_ID,
    LITERATURE_SEARCH_WORKFLOW_VERSION,
    SELECTED_PAPER_LIBRARY_SCHEMA,
    SELECTED_PAPER_LIBRARY_TYPE,
    MANUSCRIPT_DRAFT_TYPE,
    MANUSCRIPT_DRAFT_V2_TYPE,
    MANUSCRIPT_DRAFT_V3_TYPE,
    REVIEW_REPORT_TYPE,
    REVIEW_REPORT_V2_TYPE,
    REVIEW_REQUIREMENTS,
    REVIEW_TEMPLATE_ID,
    REVIEW_WORKFLOW_ID,
    SCAFFOLD_CAPSULE_VERSION,
    SCAFFOLD_INTERACTIVE_CAPSULE_VERSION,
    SCAFFOLD_COMPLETION_CAPSULE_VERSION,
    SCAFFOLD_SKILL_BACKED_CAPSULE_VERSION,
    SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
    SCAFFOLD_INPUT_TARGETS,
    SCAFFOLD_WORKFLOW_VERSION,
    WRITING_REQUIREMENTS,
    WRITING_TEMPLATE_ID,
    WRITING_WORKFLOW_ID,
    idea_discovery_contract_checksum,
    idea_discovery_v0_2_contract_checksum,
    idea_discovery_v0_3_contract_checksum,
    literature_search_contract_checksum,
    real_experiment_contract_checksum,
    real_writing_contract_checksum,
    real_review_contract_checksum,
    writing_revision_contract_checksum,
    selected_paper_library_output_contract,
    selected_research_idea_output_contract,
    scaffold_contract_checksum,
    scaffold_output_contract,
)
from backend.workflow_packages.serialization import canonical_hash

from .skills import (
    PRODUCTION_SKILLS,
    RESEARCH_ARTIFACT_PROVENANCE_SKILL,
    production_skill_pins,
)

from .contracts import (
    CapsuleTrustClassification,
    CoreCapabilityMaturity,
    WorkflowCapsuleVersion,
    WorkflowDefinition,
    WorkflowDefinitionLifecycle,
    WorkflowDefinitionVersion,
    WorkflowReviewStatus,
)

IDEA_DISCOVERY_DEFINITION_ID = IDEA_DISCOVERY_WORKFLOW_ID

SCAFFOLD_WORKFLOWS = {
    WRITING_WORKFLOW_ID: {
        "display_name": "Writing",
        "description": (
            "Run the complete manuscript Artifact flow with an explicitly marked "
            "placeholder research core."
        ),
        "template_id": WRITING_TEMPLATE_ID,
        "requirements": WRITING_REQUIREMENTS,
        "output_type": MANUSCRIPT_DRAFT_TYPE,
    },
    REVIEW_WORKFLOW_ID: {
        "display_name": "Review",
        "description": (
            "Run the complete review Artifact flow without claiming substantive "
            "peer review."
        ),
        "template_id": REVIEW_TEMPLATE_ID,
        "requirements": REVIEW_REQUIREMENTS,
        "output_type": REVIEW_REPORT_TYPE,
    },
    EXPERIMENT_WORKFLOW_ID: {
        "display_name": "Reproduction & Experiment",
        "description": (
            "Build an Idea Experiment skeleton with no real experiment or paper "
            "reproduction execution."
        ),
        "template_id": EXPERIMENT_TEMPLATE_ID,
        "requirements": EXPERIMENT_REQUIREMENTS,
        "output_type": EXPERIMENT_RECORD_TYPE,
    },
}

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

IDEA_DISCOVERY_V0_2_CAPSULE_CHECKSUM = canonical_hash(
    {
        "generator_version": "reagent-idea-discovery-local-experimental-compiler/0.2.0",
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "package_template_id": IDEA_DISCOVERY_TEMPLATE_ID,
        "package_template_version": IDEA_DISCOVERY_V0_2_CAPSULE_VERSION,
        "workflow_checksum": idea_discovery_v0_2_contract_checksum(),
        "artifact_input": {
            "requirement_key": "paper_library",
            "artifact_type": SELECTED_PAPER_LIBRARY_TYPE,
            "artifact_schema": SELECTED_PAPER_LIBRARY_SCHEMA,
            "target_relative_path": IDEA_INPUT_TARGET,
            "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
            "materialization_mode": "VERIFIED_COPY",
        },
        "artifact_outputs": [selected_research_idea_output_contract()],
        "core_capability_maturity": CoreCapabilityMaturity.REVIEWED_CORE.value,
    }
)
IDEA_DISCOVERY_V0_2_CAPSULE_ID = (
    "capsule-" + IDEA_DISCOVERY_V0_2_CAPSULE_CHECKSUM[7:39]
)

IDEA_DISCOVERY_V0_3_CAPSULE_CHECKSUM = canonical_hash(
    {
        "generator_version": "reagent-idea-discovery-local-experimental-compiler/0.3.0",
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "package_template_id": IDEA_DISCOVERY_TEMPLATE_ID,
        "package_template_version": IDEA_DISCOVERY_V0_3_CAPSULE_VERSION,
        "workflow_checksum": idea_discovery_v0_2_contract_checksum(),
        "artifact_input": {
            "requirement_key": "paper_library",
            "artifact_type": SELECTED_PAPER_LIBRARY_TYPE,
            "artifact_schema": SELECTED_PAPER_LIBRARY_SCHEMA,
            "target_relative_path": IDEA_INPUT_TARGET,
            "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
            "materialization_mode": "VERIFIED_COPY",
        },
        "artifact_outputs": [selected_research_idea_output_contract()],
        "core_capability_maturity": CoreCapabilityMaturity.REVIEWED_CORE.value,
        "harness_integration": "BOUNDED_INTERACTIVE_INPUT_REVIEW_BOOTSTRAP",
    }
)
IDEA_DISCOVERY_V0_3_CAPSULE_ID = (
    "capsule-" + IDEA_DISCOVERY_V0_3_CAPSULE_CHECKSUM[7:39]
)

IDEA_DISCOVERY_V0_4_CAPSULE_CHECKSUM = canonical_hash(
    {
        "generator_version": (
            "reagent-idea-discovery-local-experimental-compiler/0.4.0"
        ),
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "package_template_id": IDEA_DISCOVERY_TEMPLATE_ID,
        "package_template_version": IDEA_DISCOVERY_V0_4_CAPSULE_VERSION,
        "workflow_checksum": idea_discovery_v0_3_contract_checksum(),
        "artifact_input": {
            "requirement_key": "paper_library",
            "artifact_type": SELECTED_PAPER_LIBRARY_TYPE,
            "artifact_schema": SELECTED_PAPER_LIBRARY_SCHEMA,
            "target_relative_path": IDEA_INPUT_TARGET,
            "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
            "materialization_mode": "VERIFIED_COPY",
            "content_precondition": {
                "schema": PAPER_LIBRARY_NONEMPTY_PRECONDITION_SCHEMA,
                "qualification_schema": PAPER_LIBRARY_QUALIFICATION_SCHEMA,
                "minimum_selected_count": 1,
            },
        },
        "artifact_outputs": [selected_research_idea_output_contract()],
        "core_capability_maturity": CoreCapabilityMaturity.REVIEWED_CORE.value,
        "harness_integration": "BOUNDED_INTERACTIVE_INPUT_REVIEW_BOOTSTRAP",
    }
)
IDEA_DISCOVERY_V0_4_CAPSULE_ID = (
    "capsule-" + IDEA_DISCOVERY_V0_4_CAPSULE_CHECKSUM[7:39]
)


def scaffold_capsule_checksum(workflow_id: str) -> str:
    config = SCAFFOLD_WORKFLOWS[workflow_id]
    return canonical_hash({
        "generator_version": f"reagent-{workflow_id}-compiler/0.1.0",
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "package_template_id": config["template_id"],
        "package_template_version": SCAFFOLD_CAPSULE_VERSION,
        "workflow_checksum": scaffold_contract_checksum(workflow_id),
        "artifact_requirements": list(config["requirements"]),
        "artifact_outputs": [scaffold_output_contract(config["output_type"])],
        "core_capability_maturity": CoreCapabilityMaturity.SCAFFOLD_CORE.value,
    })


SCAFFOLD_CAPSULE_CHECKSUMS = {
    workflow_id: scaffold_capsule_checksum(workflow_id)
    for workflow_id in SCAFFOLD_WORKFLOWS
}
SCAFFOLD_CAPSULE_IDS = {
    workflow_id: "capsule-" + checksum[7:39]
    for workflow_id, checksum in SCAFFOLD_CAPSULE_CHECKSUMS.items()
}


def skill_backed_scaffold_capsule_checksum(workflow_id: str) -> str:
    config = SCAFFOLD_WORKFLOWS[workflow_id]
    return canonical_hash({
        "generator_version": (
            f"reagent-{workflow_id}-compiler/"
            f"{SCAFFOLD_SKILL_BACKED_CAPSULE_VERSION}"
        ),
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "package_template_id": config["template_id"],
        "package_template_version": SCAFFOLD_SKILL_BACKED_CAPSULE_VERSION,
        "workflow_checksum": scaffold_contract_checksum(
            workflow_id,
            workflow_version=SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
        ),
        "artifact_requirements": list(config["requirements"]),
        "artifact_outputs": [scaffold_output_contract(config["output_type"])],
        "core_capability_maturity": CoreCapabilityMaturity.SCAFFOLD_CORE.value,
        "skill_pins": [
            {
                "skill_id": asset.skill_id,
                "skill_version": asset.version,
                "content_checksum": asset.content_checksum,
            }
            for asset in PRODUCTION_SKILLS
        ],
    })


SCAFFOLD_V0_2_CAPSULE_CHECKSUMS = {
    workflow_id: skill_backed_scaffold_capsule_checksum(workflow_id)
    for workflow_id in SCAFFOLD_WORKFLOWS
}
SCAFFOLD_V0_2_CAPSULE_IDS = {
    workflow_id: "capsule-" + checksum[7:39]
    for workflow_id, checksum in SCAFFOLD_V0_2_CAPSULE_CHECKSUMS.items()
}


def interactive_scaffold_capsule_checksum(workflow_id: str) -> str:
    if workflow_id not in {WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID}:
        raise ValueError("interactive scaffold Capsule supports Writing/Review only")
    config = SCAFFOLD_WORKFLOWS[workflow_id]
    return canonical_hash({
        "generator_version": (
            f"reagent-{workflow_id}-compiler/"
            f"{SCAFFOLD_INTERACTIVE_CAPSULE_VERSION}"
        ),
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "package_template_id": config["template_id"],
        "package_template_version": SCAFFOLD_INTERACTIVE_CAPSULE_VERSION,
        "workflow_checksum": scaffold_contract_checksum(
            workflow_id,
            workflow_version=SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
        ),
        "artifact_requirements": list(config["requirements"]),
        "artifact_outputs": [scaffold_output_contract(config["output_type"])],
        "core_capability_maturity": CoreCapabilityMaturity.SCAFFOLD_CORE.value,
        "skill_pins": [
            {
                "skill_id": asset.skill_id,
                "skill_version": asset.version,
                "content_checksum": asset.content_checksum,
            }
            for asset in PRODUCTION_SKILLS
        ],
        "harness_integration": "BOUNDED_INTERACTIVE_INPUT_REVIEW_BOOTSTRAP",
    })


SCAFFOLD_V0_3_CAPSULE_CHECKSUMS = {
    workflow_id: interactive_scaffold_capsule_checksum(workflow_id)
    for workflow_id in (WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID)
}
SCAFFOLD_V0_3_CAPSULE_IDS = {
    workflow_id: "capsule-" + checksum[7:39]
    for workflow_id, checksum in SCAFFOLD_V0_3_CAPSULE_CHECKSUMS.items()
}


def experiment_resource_capsule_checksum() -> str:
    config = SCAFFOLD_WORKFLOWS[EXPERIMENT_WORKFLOW_ID]
    return canonical_hash({
        "generator_version": (
            f"reagent-{EXPERIMENT_WORKFLOW_ID}-compiler/"
            f"{EXPERIMENT_RESOURCE_CAPSULE_VERSION}"
        ),
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "package_template_id": config["template_id"],
        "package_template_version": EXPERIMENT_RESOURCE_CAPSULE_VERSION,
        "workflow_checksum": scaffold_contract_checksum(
            EXPERIMENT_WORKFLOW_ID,
            workflow_version=EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
        ),
        "artifact_requirements": list(config["requirements"]),
        "artifact_outputs": [scaffold_output_contract(config["output_type"])],
        "resource_requirements": [
            ["source_repository", "SOURCE_REPOSITORY"],
            ["dataset", "DATASET"],
            ["model", "MODEL"],
            ["checkpoint", "CHECKPOINT"],
        ],
        "core_capability_maturity": CoreCapabilityMaturity.SCAFFOLD_CORE.value,
        "skill_pins": [
            {
                "skill_id": asset.skill_id,
                "skill_version": asset.version,
                "content_checksum": asset.content_checksum,
            }
            for asset in PRODUCTION_SKILLS
        ],
    })


EXPERIMENT_V0_3_CAPSULE_CHECKSUM = experiment_resource_capsule_checksum()
EXPERIMENT_V0_3_CAPSULE_ID = (
    "capsule-" + EXPERIMENT_V0_3_CAPSULE_CHECKSUM[7:39]
)


def experiment_interactive_capsule_checksum() -> str:
    config = SCAFFOLD_WORKFLOWS[EXPERIMENT_WORKFLOW_ID]
    return canonical_hash({
        "generator_version": (
            f"reagent-{EXPERIMENT_WORKFLOW_ID}-compiler/"
            f"{EXPERIMENT_INTERACTIVE_CAPSULE_VERSION}"
        ),
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "package_template_id": config["template_id"],
        "package_template_version": EXPERIMENT_INTERACTIVE_CAPSULE_VERSION,
        "workflow_checksum": scaffold_contract_checksum(
            EXPERIMENT_WORKFLOW_ID,
            workflow_version=EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
        ),
        "artifact_requirements": list(config["requirements"]),
        "artifact_outputs": [scaffold_output_contract(config["output_type"])],
        "resource_requirements": [
            ["source_repository", "SOURCE_REPOSITORY"],
            ["dataset", "DATASET"],
            ["model", "MODEL"],
            ["checkpoint", "CHECKPOINT"],
        ],
        "core_capability_maturity": CoreCapabilityMaturity.SCAFFOLD_CORE.value,
        "skill_pins": [
            {
                "skill_id": asset.skill_id,
                "skill_version": asset.version,
                "content_checksum": asset.content_checksum,
            }
            for asset in PRODUCTION_SKILLS
        ],
        "harness_integration": "BOUNDED_INTERACTIVE_INPUT_REVIEW_BOOTSTRAP",
    })


EXPERIMENT_V0_4_CAPSULE_CHECKSUM = experiment_interactive_capsule_checksum()
EXPERIMENT_V0_4_CAPSULE_ID = (
    "capsule-" + EXPERIMENT_V0_4_CAPSULE_CHECKSUM[7:39]
)


def completion_scaffold_capsule_checksum(workflow_id: str) -> str:
    if workflow_id not in {WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID}:
        raise ValueError("completion lifecycle Capsule supports Writing/Review only")
    config = SCAFFOLD_WORKFLOWS[workflow_id]
    return canonical_hash({
        "generator_version": (
            f"reagent-{workflow_id}-compiler/"
            f"{SCAFFOLD_COMPLETION_CAPSULE_VERSION}"
        ),
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "package_template_id": config["template_id"],
        "package_template_version": SCAFFOLD_COMPLETION_CAPSULE_VERSION,
        "workflow_checksum": scaffold_contract_checksum(
            workflow_id,
            workflow_version=SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
        ),
        "artifact_requirements": list(config["requirements"]),
        "artifact_outputs": [scaffold_output_contract(config["output_type"])],
        "core_capability_maturity": CoreCapabilityMaturity.SCAFFOLD_CORE.value,
        "skill_pins": [
            {
                "skill_id": asset.skill_id,
                "skill_version": asset.version,
                "content_checksum": asset.content_checksum,
            }
            for asset in PRODUCTION_SKILLS
        ],
        "harness_integration": "BOUNDED_INTERACTIVE_INPUT_REVIEW_BOOTSTRAP",
        "progress_lifecycle": "ADOPT_AGENT_FINALIZATION_OR_FINALIZE_ONCE",
    })


SCAFFOLD_V0_4_CAPSULE_CHECKSUMS = {
    workflow_id: completion_scaffold_capsule_checksum(workflow_id)
    for workflow_id in (WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID)
}
SCAFFOLD_V0_4_CAPSULE_IDS = {
    workflow_id: "capsule-" + checksum[7:39]
    for workflow_id, checksum in SCAFFOLD_V0_4_CAPSULE_CHECKSUMS.items()
}


def experiment_completion_capsule_checksum() -> str:
    config = SCAFFOLD_WORKFLOWS[EXPERIMENT_WORKFLOW_ID]
    return canonical_hash({
        "generator_version": (
            f"reagent-{EXPERIMENT_WORKFLOW_ID}-compiler/"
            f"{EXPERIMENT_COMPLETION_CAPSULE_VERSION}"
        ),
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "package_template_id": config["template_id"],
        "package_template_version": EXPERIMENT_COMPLETION_CAPSULE_VERSION,
        "workflow_checksum": scaffold_contract_checksum(
            EXPERIMENT_WORKFLOW_ID,
            workflow_version=EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
        ),
        "artifact_requirements": list(config["requirements"]),
        "artifact_outputs": [scaffold_output_contract(EXPERIMENT_RECORD_TYPE)],
        "resource_requirements": [
            ["source_repository", "SOURCE_REPOSITORY"],
            ["dataset", "DATASET"],
            ["model", "MODEL"],
            ["checkpoint", "CHECKPOINT"],
        ],
        "core_capability_maturity": CoreCapabilityMaturity.SCAFFOLD_CORE.value,
        "skill_pins": [
            {
                "skill_id": asset.skill_id,
                "skill_version": asset.version,
                "content_checksum": asset.content_checksum,
            }
            for asset in PRODUCTION_SKILLS
        ],
        "harness_integration": "BOUNDED_INTERACTIVE_INPUT_REVIEW_BOOTSTRAP",
        "progress_lifecycle": "ADOPT_AGENT_FINALIZATION_OR_FINALIZE_ONCE",
    })


EXPERIMENT_V0_5_CAPSULE_CHECKSUM = experiment_completion_capsule_checksum()
EXPERIMENT_V0_5_CAPSULE_ID = (
    "capsule-" + EXPERIMENT_V0_5_CAPSULE_CHECKSUM[7:39]
)


def real_experiment_capsule_checksum() -> str:
    asset = RESEARCH_ARTIFACT_PROVENANCE_SKILL
    return canonical_hash({
        "generator_version": (
            f"reagent-{EXPERIMENT_WORKFLOW_ID}-compiler/"
            f"{REAL_EXPERIMENT_CAPSULE_VERSION}"
        ),
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "package_template_id": EXPERIMENT_TEMPLATE_ID,
        "package_template_version": REAL_EXPERIMENT_CAPSULE_VERSION,
        "workflow_checksum": real_experiment_contract_checksum(),
        "artifact_requirements": [{
            "requirement_key": "research_idea",
            "artifact_type": "selected-research-idea/v1",
            "required": True,
        }],
        "artifact_outputs": [scaffold_output_contract(EXPERIMENT_RECORD_V2_TYPE)],
        "resource_requirements": [["source_repository", "SOURCE_REPOSITORY", "GITHUB"]],
        "core_capability_maturity": CoreCapabilityMaturity.REVIEWED_CORE.value,
        "skill_pins": [{
            "skill_id": asset.skill_id,
            "skill_version": asset.version,
            "content_checksum": asset.content_checksum,
        }],
        "execution_boundary": "ONE_APPROVED_LOCAL_NO_EGRESS_ATTEMPT",
    })


REAL_EXPERIMENT_CAPSULE_CHECKSUM = real_experiment_capsule_checksum()
REAL_EXPERIMENT_CAPSULE_ID = "capsule-" + REAL_EXPERIMENT_CAPSULE_CHECKSUM[7:39]

REAL_WRITING_CAPSULE_CHECKSUM = PACKAGE_REAL_WRITING_CAPSULE_CHECKSUM
REAL_WRITING_CAPSULE_ID = PACKAGE_REAL_WRITING_CAPSULE_ID
REAL_REVIEW_CAPSULE_CHECKSUM = PACKAGE_REAL_REVIEW_CAPSULE_CHECKSUM
REAL_REVIEW_CAPSULE_ID = PACKAGE_REAL_REVIEW_CAPSULE_ID
WRITING_REVISION_CAPSULE_CHECKSUM = PACKAGE_WRITING_REVISION_CAPSULE_CHECKSUM
WRITING_REVISION_CAPSULE_ID = PACKAGE_WRITING_REVISION_CAPSULE_ID


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
        core_capability_maturity=CoreCapabilityMaturity.REVIEWED_CORE,
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
        core_capability_maturity=CoreCapabilityMaturity.REVIEWED_CORE,
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


def idea_discovery_v0_2_definition_version(
    now: datetime,
) -> WorkflowDefinitionVersion:
    return WorkflowDefinitionVersion(
        workflow_definition_id=IDEA_DISCOVERY_DEFINITION_ID,
        version=IDEA_DISCOVERY_V0_2_WORKFLOW_VERSION,
        contract_checksum=idea_discovery_v0_2_contract_checksum(),
        input_schema_id=SELECTED_PAPER_LIBRARY_SCHEMA,
        output_schema_id="selected-research-idea/v1",
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "artifact_requirement_key": "paper_library",
            "artifact_outputs": [selected_research_idea_output_contract()],
            "explicit_selection_policy": "EXACTLY_ONE_USER_CONFIRMED",
            "novelty_claim_policy": "GLOBAL_NOVELTY_NOT_PROVEN",
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        core_capability_maturity=CoreCapabilityMaturity.REVIEWED_CORE,
        published_at=now,
        created_at=now,
        updated_at=now,
    )


def idea_discovery_v0_2_capsule(now: datetime) -> WorkflowCapsuleVersion:
    return WorkflowCapsuleVersion(
        capsule_id=IDEA_DISCOVERY_V0_2_CAPSULE_ID,
        capsule_version=IDEA_DISCOVERY_V0_2_CAPSULE_VERSION,
        workflow_definition_id=IDEA_DISCOVERY_DEFINITION_ID,
        workflow_version=IDEA_DISCOVERY_V0_2_WORKFLOW_VERSION,
        definition_checksum=IDEA_DISCOVERY_V0_2_CAPSULE_CHECKSUM,
        archive_size_bytes=0,
        archive_media_type="application/zip",
        mutable_roots=("memory/context.md", "memory/progress", "outputs", "inputs"),
        capability_requirements=(
            "progress.upload/v0.2", "artifact.materialize/v0.1",
            "artifact.publish/v0.1",
        ),
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "package_template_id": IDEA_DISCOVERY_TEMPLATE_ID,
            "trust_classification": (
                CapsuleTrustClassification.TRUSTED_BUILT_IN_UNSIGNED.value
            ),
            "artifact_requirements": [{
                "requirement_key": "paper_library",
                "artifact_type": SELECTED_PAPER_LIBRARY_TYPE,
                "artifact_schema_version": SELECTED_PAPER_LIBRARY_SCHEMA,
                "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
                "materialization_mode": "VERIFIED_COPY",
                "target_relative_path": IDEA_INPUT_TARGET,
            }],
            "artifact_outputs": [selected_research_idea_output_contract()],
            "core_capability_maturity": CoreCapabilityMaturity.REVIEWED_CORE.value,
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=False,
        created_at=now,
        updated_at=now,
    )


def idea_discovery_v0_3_capsule(now: datetime) -> WorkflowCapsuleVersion:
    """Publish a new Harness integration over the unchanged Workflow 0.2 contract."""

    previous = idea_discovery_v0_2_capsule(now)
    return replace(
        previous,
        capsule_id=IDEA_DISCOVERY_V0_3_CAPSULE_ID,
        capsule_version=IDEA_DISCOVERY_V0_3_CAPSULE_VERSION,
        definition_checksum=IDEA_DISCOVERY_V0_3_CAPSULE_CHECKSUM,
    )


def idea_discovery_v0_3_definition_version(
    now: datetime,
) -> WorkflowDefinitionVersion:
    return WorkflowDefinitionVersion(
        workflow_definition_id=IDEA_DISCOVERY_DEFINITION_ID,
        version=IDEA_DISCOVERY_V0_3_WORKFLOW_VERSION,
        contract_checksum=idea_discovery_v0_3_contract_checksum(),
        input_schema_id=SELECTED_PAPER_LIBRARY_SCHEMA,
        output_schema_id="selected-research-idea/v1",
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "artifact_requirement_key": "paper_library",
            "artifact_outputs": [selected_research_idea_output_contract()],
            "explicit_selection_policy": "EXACTLY_ONE_USER_CONFIRMED",
            "novelty_claim_policy": "GLOBAL_NOVELTY_NOT_PROVEN",
            "content_precondition": {
                "schema": PAPER_LIBRARY_NONEMPTY_PRECONDITION_SCHEMA,
                "qualification_schema": PAPER_LIBRARY_QUALIFICATION_SCHEMA,
                "minimum_selected_count": 1,
            },
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        core_capability_maturity=CoreCapabilityMaturity.REVIEWED_CORE,
        published_at=now,
        created_at=now,
        updated_at=now,
    )


def idea_discovery_v0_4_capsule(now: datetime) -> WorkflowCapsuleVersion:
    requirement = {
        "requirement_key": "paper_library",
        "artifact_type": SELECTED_PAPER_LIBRARY_TYPE,
        "artifact_schema_version": SELECTED_PAPER_LIBRARY_SCHEMA,
        "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
        "materialization_mode": "VERIFIED_COPY",
        "target_relative_path": IDEA_INPUT_TARGET,
        "content_precondition": {
            "schema": PAPER_LIBRARY_NONEMPTY_PRECONDITION_SCHEMA,
            "qualification_schema": PAPER_LIBRARY_QUALIFICATION_SCHEMA,
            "minimum_selected_count": 1,
        },
    }
    return WorkflowCapsuleVersion(
        capsule_id=IDEA_DISCOVERY_V0_4_CAPSULE_ID,
        capsule_version=IDEA_DISCOVERY_V0_4_CAPSULE_VERSION,
        workflow_definition_id=IDEA_DISCOVERY_DEFINITION_ID,
        workflow_version=IDEA_DISCOVERY_V0_3_WORKFLOW_VERSION,
        definition_checksum=IDEA_DISCOVERY_V0_4_CAPSULE_CHECKSUM,
        archive_size_bytes=0,
        archive_media_type="application/zip",
        mutable_roots=("memory/context.md", "memory/progress", "outputs", "inputs"),
        capability_requirements=(
            "progress.upload/v0.2", "artifact.materialize/v0.1",
            "artifact.publish/v0.1",
        ),
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "package_template_id": IDEA_DISCOVERY_TEMPLATE_ID,
            "trust_classification": (
                CapsuleTrustClassification.TRUSTED_BUILT_IN_UNSIGNED.value
            ),
            "artifact_requirements": [requirement],
            "artifact_outputs": [selected_research_idea_output_contract()],
            "core_capability_maturity": CoreCapabilityMaturity.REVIEWED_CORE.value,
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=False,
        created_at=now,
        updated_at=now,
    )


def idea_discovery_v0_2_requirement(now: datetime) -> WorkflowArtifactRequirement:
    return WorkflowArtifactRequirement(
        workflow_definition_id=IDEA_DISCOVERY_DEFINITION_ID,
        workflow_version=IDEA_DISCOVERY_V0_2_WORKFLOW_VERSION,
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


def idea_discovery_v0_3_requirement(now: datetime) -> WorkflowArtifactRequirement:
    return WorkflowArtifactRequirement(
        workflow_definition_id=IDEA_DISCOVERY_DEFINITION_ID,
        workflow_version=IDEA_DISCOVERY_V0_3_WORKFLOW_VERSION,
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
        content_precondition={
            "schema": PAPER_LIBRARY_NONEMPTY_PRECONDITION_SCHEMA,
            "qualification_schema": PAPER_LIBRARY_QUALIFICATION_SCHEMA,
            "minimum_selected_count": 1,
        },
    )


def scaffold_definition(workflow_id: str, now: datetime) -> WorkflowDefinition:
    config = SCAFFOLD_WORKFLOWS[workflow_id]
    return WorkflowDefinition(
        workflow_definition_id=workflow_id,
        display_name=config["display_name"],
        description=config["description"],
        lifecycle=WorkflowDefinitionLifecycle.AVAILABLE,
        allows_multiple_instances=True,
        created_at=now,
        updated_at=now,
    )


def scaffold_definition_version(
    workflow_id: str, now: datetime
) -> WorkflowDefinitionVersion:
    config = SCAFFOLD_WORKFLOWS[workflow_id]
    return WorkflowDefinitionVersion(
        workflow_definition_id=workflow_id,
        version=SCAFFOLD_WORKFLOW_VERSION,
        contract_checksum=scaffold_contract_checksum(workflow_id),
        input_schema_id="artifact-bindings/v0.1",
        output_schema_id=config["output_type"],
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "artifact_requirements": list(config["requirements"]),
            "artifact_outputs": [scaffold_output_contract(config["output_type"])],
            "scaffold_notice": (
                "Product flow is functional. Research capability is placeholder."
            ),
            "supported_mode": (
                "IDEA_EXPERIMENT"
                if workflow_id == EXPERIMENT_WORKFLOW_ID else None
            ),
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        core_capability_maturity=CoreCapabilityMaturity.SCAFFOLD_CORE,
        published_at=now,
        created_at=now,
        updated_at=now,
    )


def scaffold_capsule(workflow_id: str, now: datetime) -> WorkflowCapsuleVersion:
    config = SCAFFOLD_WORKFLOWS[workflow_id]
    return WorkflowCapsuleVersion(
        capsule_id=SCAFFOLD_CAPSULE_IDS[workflow_id],
        capsule_version=SCAFFOLD_CAPSULE_VERSION,
        workflow_definition_id=workflow_id,
        workflow_version=SCAFFOLD_WORKFLOW_VERSION,
        definition_checksum=SCAFFOLD_CAPSULE_CHECKSUMS[workflow_id],
        archive_size_bytes=0,
        archive_media_type="application/zip",
        mutable_roots=("memory/context.md", "memory/progress", "memory/input-provenance.json", "memory/current-artifact.json", "outputs", "inputs"),
        capability_requirements=(
            "progress.upload/v0.2", "artifact.materialize/v0.1",
            "artifact.publish/v0.1",
        ),
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "package_template_id": config["template_id"],
            "trust_classification": (
                CapsuleTrustClassification.TRUSTED_BUILT_IN_UNSIGNED.value
            ),
            "artifact_requirements": list(config["requirements"]),
            "artifact_outputs": [scaffold_output_contract(config["output_type"])],
            "core_capability_maturity": CoreCapabilityMaturity.SCAFFOLD_CORE.value,
            "scaffold_notice": (
                "Product flow is functional. Research capability is placeholder."
            ),
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=False,
        created_at=now,
        updated_at=now,
    )


def scaffold_requirements(
    workflow_id: str, now: datetime
) -> tuple[WorkflowArtifactRequirement, ...]:
    result = []
    for item in SCAFFOLD_WORKFLOWS[workflow_id]["requirements"]:
        result.append(WorkflowArtifactRequirement(
            workflow_definition_id=workflow_id,
            workflow_version=SCAFFOLD_WORKFLOW_VERSION,
            requirement_key=item["requirement_key"],
            artifact_type=item["artifact_type"],
            compatibility_mode=CompatibilityMode.EXACT,
            schema_constraint=item["artifact_schema"],
            cardinality_min=1 if item["required"] else 0,
            cardinality_max=1,
            required=item["required"],
            materialization_mode=MaterializationMode.VERIFIED_COPY,
            target_relative_path=item["target_relative_path"],
            created_at=now,
            updated_at=now,
        ))
    return tuple(result)


def skill_backed_scaffold_definition_version(
    workflow_id: str, now: datetime
) -> WorkflowDefinitionVersion:
    config = SCAFFOLD_WORKFLOWS[workflow_id]
    return WorkflowDefinitionVersion(
        workflow_definition_id=workflow_id,
        version=SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
        contract_checksum=scaffold_contract_checksum(
            workflow_id,
            workflow_version=SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
        ),
        input_schema_id="artifact-bindings/v0.1",
        output_schema_id=config["output_type"],
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "artifact_requirements": list(config["requirements"]),
            "artifact_outputs": [scaffold_output_contract(config["output_type"])],
            "scaffold_notice": (
                "Product flow is functional. Research capability is placeholder."
            ),
            "supported_mode": (
                "IDEA_EXPERIMENT"
                if workflow_id == EXPERIMENT_WORKFLOW_ID else None
            ),
            "skill_delivery": "EXACT_CAPSULE_BUNDLED",
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        core_capability_maturity=CoreCapabilityMaturity.SCAFFOLD_CORE,
        published_at=now,
        created_at=now,
        updated_at=now,
    )


def skill_backed_scaffold_capsule(
    workflow_id: str, now: datetime
) -> WorkflowCapsuleVersion:
    config = SCAFFOLD_WORKFLOWS[workflow_id]
    return WorkflowCapsuleVersion(
        capsule_id=SCAFFOLD_V0_2_CAPSULE_IDS[workflow_id],
        capsule_version=SCAFFOLD_SKILL_BACKED_CAPSULE_VERSION,
        workflow_definition_id=workflow_id,
        workflow_version=SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
        definition_checksum=SCAFFOLD_V0_2_CAPSULE_CHECKSUMS[workflow_id],
        archive_size_bytes=0,
        archive_media_type="application/zip",
        mutable_roots=(
            "memory/context.md", "memory/progress",
            "memory/input-provenance.json", "memory/current-artifact.json",
            "outputs", "inputs",
        ),
        capability_requirements=(
            "progress.upload/v0.2", "artifact.materialize/v0.1",
            "artifact.publish/v0.1",
        ),
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "package_template_id": config["template_id"],
            "trust_classification": (
                CapsuleTrustClassification.TRUSTED_BUILT_IN_UNSIGNED.value
            ),
            "artifact_requirements": list(config["requirements"]),
            "artifact_outputs": [scaffold_output_contract(config["output_type"])],
            "core_capability_maturity": CoreCapabilityMaturity.SCAFFOLD_CORE.value,
            "scaffold_notice": (
                "Product flow is functional. Research capability is placeholder."
            ),
            "skill_delivery": "EXACT_CAPSULE_BUNDLED",
            "skill_pins": [
                {
                    "skill_id": pin.skill_id,
                    "skill_version": pin.skill_version,
                    "skill_checksum": pin.skill_checksum,
                    "trust": "BUILT_IN_REVIEWED",
                }
                for pin in production_skill_pins(
                    workflow_id, SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION, now
                )
            ],
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=False,
        created_at=now,
        updated_at=now,
    )


def interactive_scaffold_capsule(
    workflow_id: str, now: datetime
) -> WorkflowCapsuleVersion:
    """Publish only the Writing/Review Harness integration over Definition 0.2."""

    config = SCAFFOLD_WORKFLOWS[workflow_id]
    previous = skill_backed_scaffold_capsule(workflow_id, now)
    return replace(
        previous,
        capsule_id=SCAFFOLD_V0_3_CAPSULE_IDS[workflow_id],
        capsule_version=SCAFFOLD_INTERACTIVE_CAPSULE_VERSION,
        definition_checksum=SCAFFOLD_V0_3_CAPSULE_CHECKSUMS[workflow_id],
        compatibility={
            **previous.compatibility,
            "package_template_id": config["template_id"],
            "harness_integration": (
                "BOUNDED_INTERACTIVE_INPUT_REVIEW_BOOTSTRAP"
            ),
        },
    )


def completion_scaffold_capsule(
    workflow_id: str, now: datetime
) -> WorkflowCapsuleVersion:
    """Publish the single-finalization lifecycle over unchanged Definition 0.2."""

    previous = interactive_scaffold_capsule(workflow_id, now)
    return replace(
        previous,
        capsule_id=SCAFFOLD_V0_4_CAPSULE_IDS[workflow_id],
        capsule_version=SCAFFOLD_COMPLETION_CAPSULE_VERSION,
        definition_checksum=SCAFFOLD_V0_4_CAPSULE_CHECKSUMS[workflow_id],
        compatibility={
            **previous.compatibility,
            "progress_lifecycle": "ADOPT_AGENT_FINALIZATION_OR_FINALIZE_ONCE",
        },
    )


def skill_backed_scaffold_requirements(
    workflow_id: str, now: datetime
) -> tuple[WorkflowArtifactRequirement, ...]:
    return tuple(
        WorkflowArtifactRequirement(
            workflow_definition_id=workflow_id,
            workflow_version=SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
            requirement_key=item["requirement_key"],
            artifact_type=item["artifact_type"],
            compatibility_mode=CompatibilityMode.EXACT,
            schema_constraint=item["artifact_schema"],
            cardinality_min=1 if item["required"] else 0,
            cardinality_max=1,
            required=item["required"],
            materialization_mode=MaterializationMode.VERIFIED_COPY,
            target_relative_path=item["target_relative_path"],
            created_at=now,
            updated_at=now,
        )
        for item in SCAFFOLD_WORKFLOWS[workflow_id]["requirements"]
    )


def experiment_resource_definition_version(now: datetime) -> WorkflowDefinitionVersion:
    return WorkflowDefinitionVersion(
        workflow_definition_id=EXPERIMENT_WORKFLOW_ID,
        version=EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
        contract_checksum=scaffold_contract_checksum(
            EXPERIMENT_WORKFLOW_ID,
            workflow_version=EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
        ),
        input_schema_id="artifact-and-resource-bindings/v0.1",
        output_schema_id=EXPERIMENT_RECORD_TYPE,
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "artifact_requirements": list(EXPERIMENT_REQUIREMENTS),
            "artifact_outputs": [scaffold_output_contract(EXPERIMENT_RECORD_TYPE)],
            "scaffold_notice": (
                "Product flow is functional. Research capability is placeholder."
            ),
            "supported_mode": "IDEA_EXPERIMENT",
            "paper_reproduction": "NOT_YET_ENABLED",
            "skill_delivery": "EXACT_CAPSULE_BUNDLED",
            "resource_delivery": "EXACT_PROJECT_BINDING_LOCAL_RESOLVER",
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        core_capability_maturity=CoreCapabilityMaturity.SCAFFOLD_CORE,
        published_at=now,
        created_at=now,
        updated_at=now,
    )


def experiment_resource_capsule(now: datetime) -> WorkflowCapsuleVersion:
    return WorkflowCapsuleVersion(
        capsule_id=EXPERIMENT_V0_3_CAPSULE_ID,
        capsule_version=EXPERIMENT_RESOURCE_CAPSULE_VERSION,
        workflow_definition_id=EXPERIMENT_WORKFLOW_ID,
        workflow_version=EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
        definition_checksum=EXPERIMENT_V0_3_CAPSULE_CHECKSUM,
        archive_size_bytes=0,
        archive_media_type="application/zip",
        mutable_roots=(
            "memory/context.md", "memory/progress",
            "memory/input-provenance.json", "memory/current-artifact.json",
            "outputs", "inputs",
        ),
        capability_requirements=(
            "progress.upload/v0.2", "artifact.materialize/v0.1",
            "artifact.publish/v0.1", "resource.index.verify/v0.1",
        ),
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "package_template_id": EXPERIMENT_TEMPLATE_ID,
            "trust_classification": (
                CapsuleTrustClassification.TRUSTED_BUILT_IN_UNSIGNED.value
            ),
            "artifact_requirements": list(EXPERIMENT_REQUIREMENTS),
            "artifact_outputs": [scaffold_output_contract(EXPERIMENT_RECORD_TYPE)],
            "core_capability_maturity": CoreCapabilityMaturity.SCAFFOLD_CORE.value,
            "scaffold_notice": (
                "Product flow is functional. Research capability is placeholder."
            ),
            "skill_delivery": "EXACT_CAPSULE_BUNDLED",
            "skill_pins": [
                {
                    "skill_id": pin.skill_id,
                    "skill_version": pin.skill_version,
                    "skill_checksum": pin.skill_checksum,
                    "trust": "BUILT_IN_REVIEWED",
                }
                for pin in production_skill_pins(
                    EXPERIMENT_WORKFLOW_ID,
                    EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
                    now,
                )
            ],
            "resource_delivery": "EXACT_PROJECT_BINDING_LOCAL_RESOLVER",
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=False,
        created_at=now,
        updated_at=now,
    )


def experiment_interactive_capsule(now: datetime) -> WorkflowCapsuleVersion:
    """Publish the bootstrap integration over the unchanged 0.3 definition."""

    return WorkflowCapsuleVersion(
        capsule_id=EXPERIMENT_V0_4_CAPSULE_ID,
        capsule_version=EXPERIMENT_INTERACTIVE_CAPSULE_VERSION,
        workflow_definition_id=EXPERIMENT_WORKFLOW_ID,
        workflow_version=EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
        definition_checksum=EXPERIMENT_V0_4_CAPSULE_CHECKSUM,
        archive_size_bytes=0,
        archive_media_type="application/zip",
        mutable_roots=(
            "memory/context.md", "memory/progress",
            "memory/input-provenance.json", "memory/resource-provenance.json",
            "memory/current-artifact.json", "outputs", "inputs",
        ),
        capability_requirements=(
            "progress.upload/v0.2", "artifact.materialize/v0.1",
            "artifact.publish/v0.1", "resource.index.verify/v0.1",
        ),
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "package_template_id": EXPERIMENT_TEMPLATE_ID,
            "trust_classification": (
                CapsuleTrustClassification.TRUSTED_BUILT_IN_UNSIGNED.value
            ),
            "artifact_requirements": list(EXPERIMENT_REQUIREMENTS),
            "artifact_outputs": [scaffold_output_contract(EXPERIMENT_RECORD_TYPE)],
            "core_capability_maturity": CoreCapabilityMaturity.SCAFFOLD_CORE.value,
            "scaffold_notice": (
                "Product flow is functional. Research capability is placeholder."
            ),
            "skill_delivery": "EXACT_CAPSULE_BUNDLED",
            "skill_pins": [
                {
                    "skill_id": pin.skill_id,
                    "skill_version": pin.skill_version,
                    "skill_checksum": pin.skill_checksum,
                    "trust": "BUILT_IN_REVIEWED",
                }
                for pin in production_skill_pins(
                    EXPERIMENT_WORKFLOW_ID,
                    EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
                    now,
                )
            ],
            "resource_delivery": "EXACT_PROJECT_BINDING_LOCAL_RESOLVER",
            "harness_integration": "BOUNDED_INTERACTIVE_INPUT_REVIEW_BOOTSTRAP",
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=False,
        created_at=now,
        updated_at=now,
    )


def experiment_completion_capsule(now: datetime) -> WorkflowCapsuleVersion:
    """Publish the single-finalization lifecycle over unchanged Definition 0.3."""

    previous = experiment_interactive_capsule(now)
    return replace(
        previous,
        capsule_id=EXPERIMENT_V0_5_CAPSULE_ID,
        capsule_version=EXPERIMENT_COMPLETION_CAPSULE_VERSION,
        definition_checksum=EXPERIMENT_V0_5_CAPSULE_CHECKSUM,
        compatibility={
            **previous.compatibility,
            "progress_lifecycle": "ADOPT_AGENT_FINALIZATION_OR_FINALIZE_ONCE",
        },
    )


def experiment_resource_artifact_requirements(
    now: datetime,
) -> tuple[WorkflowArtifactRequirement, ...]:
    return tuple(
        WorkflowArtifactRequirement(
            workflow_definition_id=EXPERIMENT_WORKFLOW_ID,
            workflow_version=EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
            requirement_key=item["requirement_key"],
            artifact_type=item["artifact_type"],
            compatibility_mode=CompatibilityMode.EXACT,
            schema_constraint=item["artifact_schema"],
            cardinality_min=1 if item["required"] else 0,
            cardinality_max=1,
            required=item["required"],
            materialization_mode=MaterializationMode.VERIFIED_COPY,
            target_relative_path=item["target_relative_path"],
            created_at=now,
            updated_at=now,
        )
        for item in EXPERIMENT_REQUIREMENTS
    )


def real_experiment_definition_version(now: datetime) -> WorkflowDefinitionVersion:
    return WorkflowDefinitionVersion(
        workflow_definition_id=EXPERIMENT_WORKFLOW_ID,
        version=REAL_EXPERIMENT_WORKFLOW_VERSION,
        contract_checksum=real_experiment_contract_checksum(),
        input_schema_id="selected-research-idea/v1",
        output_schema_id=EXPERIMENT_RECORD_V2_TYPE,
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "artifact_outputs": [scaffold_output_contract(EXPERIMENT_RECORD_V2_TYPE)],
            "resource_mode": "ONE_OWNER_STAGED_GITHUB_SOURCE_REPOSITORY",
            "network_policy": "DISABLED",
            "automatic_retry": False,
            "default_project_setup": False,
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        core_capability_maturity=CoreCapabilityMaturity.REVIEWED_CORE,
        published_at=now,
        created_at=now,
        updated_at=now,
    )


def real_experiment_capsule(now: datetime) -> WorkflowCapsuleVersion:
    asset = RESEARCH_ARTIFACT_PROVENANCE_SKILL
    return WorkflowCapsuleVersion(
        capsule_id=REAL_EXPERIMENT_CAPSULE_ID,
        capsule_version=REAL_EXPERIMENT_CAPSULE_VERSION,
        workflow_definition_id=EXPERIMENT_WORKFLOW_ID,
        workflow_version=REAL_EXPERIMENT_WORKFLOW_VERSION,
        definition_checksum=REAL_EXPERIMENT_CAPSULE_CHECKSUM,
        archive_size_bytes=0,
        archive_media_type="application/zip",
        mutable_roots=("memory/context.md", "memory/progress", "memory/execution", "memory/input-provenance.json", "memory/resource-provenance.json", "memory/plan-context.json", "memory/experiment-requirements.json", "memory/experiment-plan.json", "memory/experiment-approval.json", "memory/approval-consumption.json", "memory/current-artifact.json", "outputs", "inputs"),
        capability_requirements=("progress.upload/v0.2", "artifact.materialize/v0.1", "artifact.publish/v0.1", "resource.index.verify/v0.1", "execute.local-foreground/v0.1", "network.no-egress/v0.1"),
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "package_template_id": EXPERIMENT_TEMPLATE_ID,
            "trust_classification": CapsuleTrustClassification.TRUSTED_BUILT_IN_UNSIGNED.value,
            "artifact_outputs": [scaffold_output_contract(EXPERIMENT_RECORD_V2_TYPE)],
            "core_capability_maturity": CoreCapabilityMaturity.REVIEWED_CORE.value,
            "skill_pins": [{"skill_id": asset.skill_id, "skill_version": asset.version, "skill_checksum": asset.content_checksum, "trust": "BUILT_IN_REVIEWED"}],
            "execution_boundary": "ONE_APPROVED_LOCAL_NO_EGRESS_ATTEMPT",
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=False,
        created_at=now,
        updated_at=now,
    )


def real_experiment_artifact_requirement(now: datetime) -> WorkflowArtifactRequirement:
    return WorkflowArtifactRequirement(
        workflow_definition_id=EXPERIMENT_WORKFLOW_ID,
        workflow_version=REAL_EXPERIMENT_WORKFLOW_VERSION,
        requirement_key="research_idea",
        artifact_type="selected-research-idea/v1",
        compatibility_mode=CompatibilityMode.EXACT,
        schema_constraint="selected-research-idea/v1",
        cardinality_min=1,
        cardinality_max=1,
        required=True,
        materialization_mode=MaterializationMode.VERIFIED_COPY,
        target_relative_path=SCAFFOLD_INPUT_TARGETS["research_idea"],
        created_at=now,
        updated_at=now,
    )


def real_writing_definition_version(now: datetime) -> WorkflowDefinitionVersion:
    return WorkflowDefinitionVersion(
        workflow_definition_id=WRITING_WORKFLOW_ID,
        version=REAL_WRITING_WORKFLOW_VERSION,
        contract_checksum=real_writing_contract_checksum(),
        input_schema_id="artifact-bindings/v0.1",
        output_schema_id=MANUSCRIPT_DRAFT_V2_TYPE,
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "artifact_requirements": list(REAL_WRITING_REQUIREMENTS),
            "artifact_outputs": [scaffold_output_contract(MANUSCRIPT_DRAFT_V2_TYPE)],
            "supported_mode": "EVIDENCE_BOUND_INITIAL_DRAFT",
            "evidence_statuses": ["SUPPORTED", "PLANNED", "UNAVAILABLE"],
            "default_project_setup": False,
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        core_capability_maturity=CoreCapabilityMaturity.REVIEWED_CORE,
        published_at=now,
        created_at=now,
        updated_at=now,
    )


def real_writing_capsule(now: datetime) -> WorkflowCapsuleVersion:
    asset = RESEARCH_ARTIFACT_PROVENANCE_SKILL
    return WorkflowCapsuleVersion(
        capsule_id=REAL_WRITING_CAPSULE_ID,
        capsule_version=REAL_WRITING_CAPSULE_VERSION,
        workflow_definition_id=WRITING_WORKFLOW_ID,
        workflow_version=REAL_WRITING_WORKFLOW_VERSION,
        definition_checksum=REAL_WRITING_CAPSULE_CHECKSUM,
        archive_size_bytes=0,
        archive_media_type="application/zip",
        mutable_roots=(
            "memory/context.md", "memory/progress", "memory/input-provenance.json",
            "memory/writing-brief.json", "memory/evidence-map.json",
            "memory/outline.json", "memory/outline-approval.json",
            "memory/claims.json", "memory/citations.json",
            "memory/owner-review.json", "memory/current-artifact.json",
            "outputs", "inputs",
        ),
        capability_requirements=(
            "progress.upload/v0.2", "artifact.materialize/v0.1",
            "artifact.publish/v0.1",
        ),
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "package_template_id": WRITING_TEMPLATE_ID,
            "trust_classification": CapsuleTrustClassification.TRUSTED_BUILT_IN_UNSIGNED.value,
            "artifact_requirements": list(REAL_WRITING_REQUIREMENTS),
            "artifact_outputs": [scaffold_output_contract(MANUSCRIPT_DRAFT_V2_TYPE)],
            "core_capability_maturity": CoreCapabilityMaturity.REVIEWED_CORE.value,
            "skill_pins": [{
                "skill_id": asset.skill_id, "skill_version": asset.version,
                "skill_checksum": asset.content_checksum,
                "trust": "BUILT_IN_REVIEWED",
            }],
            "interaction_boundary": "TWO_EXACT_OWNER_CHECKPOINTS",
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=False,
        created_at=now,
        updated_at=now,
    )


def real_writing_artifact_requirements(now: datetime) -> tuple[WorkflowArtifactRequirement, ...]:
    return tuple(
        WorkflowArtifactRequirement(
            workflow_definition_id=WRITING_WORKFLOW_ID,
            workflow_version=REAL_WRITING_WORKFLOW_VERSION,
            requirement_key=item["requirement_key"],
            artifact_type=item["artifact_type"],
            compatibility_mode=CompatibilityMode.EXACT,
            schema_constraint=item["artifact_schema"],
            cardinality_min=1 if item["required"] else 0,
            cardinality_max=1,
            required=item["required"],
            materialization_mode=MaterializationMode.VERIFIED_COPY,
            target_relative_path=item["target_relative_path"],
            created_at=now,
            updated_at=now,
        )
        for item in REAL_WRITING_REQUIREMENTS
    )


def writing_revision_definition_version(now: datetime) -> WorkflowDefinitionVersion:
    return WorkflowDefinitionVersion(
        workflow_definition_id=WRITING_WORKFLOW_ID,
        version=WRITING_REVISION_WORKFLOW_VERSION,
        contract_checksum=writing_revision_contract_checksum(),
        input_schema_id="artifact-bindings/v0.1",
        output_schema_id=MANUSCRIPT_DRAFT_V3_TYPE,
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "artifact_requirements": list(WRITING_REVISION_REQUIREMENTS),
            "artifact_outputs": [scaffold_output_contract(MANUSCRIPT_DRAFT_V3_TYPE)],
            "supported_mode": "REVIEW_TO_WRITING_REVISION_ROUND_ONE",
            "revision_dispositions": [
                "ADDRESSED", "PARTIALLY_ADDRESSED", "NOT_ADDRESSED",
            ],
            "default_project_setup": False,
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        core_capability_maturity=CoreCapabilityMaturity.REVIEWED_CORE,
        published_at=now, created_at=now, updated_at=now,
    )


def writing_revision_capsule(now: datetime) -> WorkflowCapsuleVersion:
    asset = RESEARCH_ARTIFACT_PROVENANCE_SKILL
    return WorkflowCapsuleVersion(
        capsule_id=WRITING_REVISION_CAPSULE_ID,
        capsule_version=WRITING_REVISION_CAPSULE_VERSION,
        workflow_definition_id=WRITING_WORKFLOW_ID,
        workflow_version=WRITING_REVISION_WORKFLOW_VERSION,
        definition_checksum=WRITING_REVISION_CAPSULE_CHECKSUM,
        archive_size_bytes=0, archive_media_type="application/zip",
        mutable_roots=(
            "memory/context.md", "memory/progress", "memory/input-provenance.json",
            "memory/revision-plan.json", "memory/revision-plan-approval.json",
            "memory/claims.json", "memory/citations.json",
            "memory/issue-accounting.json", "memory/owner-review.json",
            "memory/current-artifact.json", "outputs", "inputs",
        ),
        capability_requirements=(
            "progress.upload/v0.2", "artifact.materialize/v0.1",
            "artifact.publish/v0.1",
        ),
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "package_template_id": WRITING_TEMPLATE_ID,
            "trust_classification": CapsuleTrustClassification.TRUSTED_BUILT_IN_UNSIGNED.value,
            "artifact_requirements": list(WRITING_REVISION_REQUIREMENTS),
            "artifact_outputs": [scaffold_output_contract(MANUSCRIPT_DRAFT_V3_TYPE)],
            "core_capability_maturity": CoreCapabilityMaturity.REVIEWED_CORE.value,
            "skill_pins": [{
                "skill_id": asset.skill_id, "skill_version": asset.version,
                "skill_checksum": asset.content_checksum, "trust": "BUILT_IN_REVIEWED",
            }],
            "interaction_boundary": "EXACT_REVISION_PLAN_AND_FINAL_DRAFT_CHECKPOINTS",
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=False, created_at=now, updated_at=now,
    )


def writing_revision_artifact_requirements(now: datetime) -> tuple[WorkflowArtifactRequirement, ...]:
    return tuple(
        WorkflowArtifactRequirement(
            workflow_definition_id=WRITING_WORKFLOW_ID,
            workflow_version=WRITING_REVISION_WORKFLOW_VERSION,
            requirement_key=item["requirement_key"], artifact_type=item["artifact_type"],
            compatibility_mode=CompatibilityMode.EXACT,
            schema_constraint=item["artifact_schema"],
            cardinality_min=1 if item["required"] else 0, cardinality_max=1,
            required=item["required"],
            materialization_mode=MaterializationMode.VERIFIED_COPY,
            target_relative_path=item["target_relative_path"],
            created_at=now, updated_at=now,
        )
        for item in WRITING_REVISION_REQUIREMENTS
    )


def real_review_definition_version(now: datetime) -> WorkflowDefinitionVersion:
    return WorkflowDefinitionVersion(
        workflow_definition_id=REVIEW_WORKFLOW_ID,
        version=REAL_REVIEW_WORKFLOW_VERSION,
        contract_checksum=real_review_contract_checksum(),
        input_schema_id="artifact-bindings/v0.1",
        output_schema_id=REVIEW_REPORT_V2_TYPE,
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "artifact_requirements": list(REAL_REVIEW_REQUIREMENTS),
            "artifact_outputs": [scaffold_output_contract(REVIEW_REPORT_V2_TYPE)],
            "supported_mode": "BOUNDED_EVIDENCE_AUDIT",
            "assessments": [
                "NO_BLOCKING_ISSUES", "REVISION_REQUIRED", "INSUFFICIENT_EVIDENCE",
            ],
            "default_project_setup": False,
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        core_capability_maturity=CoreCapabilityMaturity.REVIEWED_CORE,
        published_at=now,
        created_at=now,
        updated_at=now,
    )


def real_review_capsule(now: datetime) -> WorkflowCapsuleVersion:
    asset = RESEARCH_ARTIFACT_PROVENANCE_SKILL
    return WorkflowCapsuleVersion(
        capsule_id=REAL_REVIEW_CAPSULE_ID,
        capsule_version=REAL_REVIEW_CAPSULE_VERSION,
        workflow_definition_id=REVIEW_WORKFLOW_ID,
        workflow_version=REAL_REVIEW_WORKFLOW_VERSION,
        definition_checksum=REAL_REVIEW_CAPSULE_CHECKSUM,
        archive_size_bytes=0,
        archive_media_type="application/zip",
        mutable_roots=(
            "memory/context.md", "memory/progress", "memory/input-provenance.json",
            "memory/evidence-availability.json", "memory/review-scope.json",
            "memory/scope-approval.json", "memory/review-result.json",
            "memory/owner-review.json", "memory/current-artifact.json",
            "outputs", "inputs",
        ),
        capability_requirements=(
            "progress.upload/v0.2", "artifact.materialize/v0.1",
            "artifact.publish/v0.1",
        ),
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "package_template_id": REVIEW_TEMPLATE_ID,
            "trust_classification": CapsuleTrustClassification.TRUSTED_BUILT_IN_UNSIGNED.value,
            "artifact_requirements": list(REAL_REVIEW_REQUIREMENTS),
            "artifact_outputs": [scaffold_output_contract(REVIEW_REPORT_V2_TYPE)],
            "core_capability_maturity": CoreCapabilityMaturity.REVIEWED_CORE.value,
            "skill_pins": [{
                "skill_id": asset.skill_id, "skill_version": asset.version,
                "skill_checksum": asset.content_checksum,
                "trust": "BUILT_IN_REVIEWED",
            }],
            "interaction_boundary": "EXACT_SCOPE_AND_REVIEW_OWNER_CHECKPOINTS",
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=False,
        created_at=now,
        updated_at=now,
    )


def real_review_artifact_requirements(now: datetime) -> tuple[WorkflowArtifactRequirement, ...]:
    return tuple(
        WorkflowArtifactRequirement(
            workflow_definition_id=REVIEW_WORKFLOW_ID,
            workflow_version=REAL_REVIEW_WORKFLOW_VERSION,
            requirement_key=item["requirement_key"],
            artifact_type=item["artifact_type"],
            compatibility_mode=CompatibilityMode.EXACT,
            schema_constraint=item["artifact_schema"],
            cardinality_min=1 if item["required"] else 0,
            cardinality_max=1,
            required=item["required"],
            materialization_mode=MaterializationMode.VERIFIED_COPY,
            target_relative_path=item["target_relative_path"],
            created_at=now,
            updated_at=now,
        )
        for item in REAL_REVIEW_REQUIREMENTS
    )
