"""Cloud publication records for the forward Experiment-v5 downstream chain."""

from __future__ import annotations

from datetime import datetime

from backend.artifact_references.contracts import (
    CompatibilityMode, MaterializationMode, WorkflowArtifactRequirement,
)
from backend.workflow_packages.contracts import PACKAGE_SCHEMA_VERSION
from backend.workflow_packages.forward_downstream_publication import (
    INITIAL_WRITING_CAPSULE_CHECKSUM, INITIAL_WRITING_CAPSULE_ID,
    INITIAL_WRITING_CAPSULE_VERSION, INITIAL_WRITING_REQUIREMENTS,
    INITIAL_WRITING_VERSION, MANUSCRIPT_V4, MANUSCRIPT_V5,
    REVIEW_CAPSULE_CHECKSUM, REVIEW_CAPSULE_ID, REVIEW_CAPSULE_VERSION,
    REVIEW_REQUIREMENTS, REVIEW_V3, REVIEW_VERSION,
    REVISION_REQUIREMENTS, WRITING_REVISION_CAPSULE_CHECKSUM,
    WRITING_REVISION_CAPSULE_ID, WRITING_REVISION_CAPSULE_VERSION,
    WRITING_REVISION_VERSION, workflow_checksum,
)
from backend.workflow_packages.production_workflows import (
    REVIEW_TEMPLATE_ID, REVIEW_WORKFLOW_ID, WRITING_TEMPLATE_ID, WRITING_WORKFLOW_ID,
    scaffold_output_contract,
)

from .contracts import (
    CapsuleTrustClassification, CoreCapabilityMaturity, WorkflowCapsuleVersion,
    WorkflowDefinitionVersion, WorkflowReviewStatus,
)
from .skills import RESEARCH_ARTIFACT_PROVENANCE_SKILL


def _identity(role: str):
    return {
        "initial-writing": (WRITING_WORKFLOW_ID, INITIAL_WRITING_VERSION, INITIAL_WRITING_CAPSULE_ID, INITIAL_WRITING_CAPSULE_VERSION, INITIAL_WRITING_CAPSULE_CHECKSUM, INITIAL_WRITING_REQUIREMENTS, MANUSCRIPT_V4, WRITING_TEMPLATE_ID, True),
        "review": (REVIEW_WORKFLOW_ID, REVIEW_VERSION, REVIEW_CAPSULE_ID, REVIEW_CAPSULE_VERSION, REVIEW_CAPSULE_CHECKSUM, REVIEW_REQUIREMENTS, REVIEW_V3, REVIEW_TEMPLATE_ID, True),
        "revision": (WRITING_WORKFLOW_ID, WRITING_REVISION_VERSION, WRITING_REVISION_CAPSULE_ID, WRITING_REVISION_CAPSULE_VERSION, WRITING_REVISION_CAPSULE_CHECKSUM, REVISION_REQUIREMENTS, MANUSCRIPT_V5, WRITING_TEMPLATE_ID, False),
    }[role]


def definition_version(role: str, now: datetime) -> WorkflowDefinitionVersion:
    workflow_id, version, _capsule_id, _capsule_version, _capsule_checksum, requirements, output, _template, recommended = _identity(role)
    return WorkflowDefinitionVersion(
        workflow_definition_id=workflow_id, version=version,
        contract_checksum=workflow_checksum(role), input_schema_id="artifact-bindings/v0.1",
        output_schema_id=output,
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "artifact_requirements": list(requirements),
            "artifact_outputs": [scaffold_output_contract(output)],
            "supported_mode": {
                "initial-writing": "EVIDENCE_BOUND_INITIAL_DRAFT_V5",
                "review": "BOUNDED_EVIDENCE_AUDIT_V5",
                "revision": "REVIEW_TO_WRITING_REVISION_V5_ROUND_ONE",
            }[role],
            "experiment_evidence_authority": "experiment-record/v5",
            "presentation_companion_authoritative": False,
            "writing_role": "REVISION" if role == "revision" else "INITIAL" if role == "initial-writing" else None,
            "default_project_setup": recommended,
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        core_capability_maturity=CoreCapabilityMaturity.REVIEWED_CORE,
        published_at=now, created_at=now, updated_at=now,
    )


def capsule_version(role: str, now: datetime) -> WorkflowCapsuleVersion:
    workflow_id, version, capsule_id, version_capsule, checksum, requirements, output, template, _recommended = _identity(role)
    asset = RESEARCH_ARTIFACT_PROVENANCE_SKILL
    role_mutable = {
        "initial-writing": ("memory/writing-brief.json", "memory/evidence-map.json", "memory/outline.json", "memory/outline-approval.json", "memory/claims.json", "memory/citations.json"),
        "review": ("memory/evidence-availability.json", "memory/review-scope.json", "memory/scope-approval.json", "memory/review-result.json"),
        "revision": ("memory/revision-plan.json", "memory/revision-plan-approval.json", "memory/claims.json", "memory/citations.json", "memory/issue-accounting.json"),
    }[role]
    mutable = (
        "memory/context.md", "memory/progress", "memory/input-provenance.json",
        *role_mutable, "memory/current-artifact.json", "memory/owner-review.json",
        "outputs", "inputs",
    )
    return WorkflowCapsuleVersion(
        capsule_id=capsule_id, capsule_version=version_capsule,
        workflow_definition_id=workflow_id, workflow_version=version,
        definition_checksum=checksum, archive_size_bytes=0,
        archive_media_type="application/zip", mutable_roots=mutable,
        capability_requirements=("progress.upload/v0.2", "artifact.materialize/v0.1", "artifact.publish/v0.1"),
        compatibility={
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "package_template_id": template,
            "trust_classification": CapsuleTrustClassification.TRUSTED_BUILT_IN_UNSIGNED.value,
            "artifact_requirements": list(requirements),
            "artifact_outputs": [scaffold_output_contract(output)],
            "core_capability_maturity": CoreCapabilityMaturity.REVIEWED_CORE.value,
            "skill_pins": [{
                "skill_id": asset.skill_id, "skill_version": asset.version,
                "skill_checksum": asset.content_checksum, "trust": "BUILT_IN_REVIEWED",
            }],
            "experiment_evidence_authority": "experiment-record/v5",
            "interaction_boundary": "TWO_EXACT_OWNER_CHECKPOINTS",
        },
        review_status=WorkflowReviewStatus.REVIEWED,
        legacy_package_compatible=False, created_at=now, updated_at=now,
    )


def artifact_requirements(role: str, now: datetime) -> tuple[WorkflowArtifactRequirement, ...]:
    workflow_id, version, _capsule_id, _capsule_version, _checksum, requirements, _output, _template, _recommended = _identity(role)
    return tuple(WorkflowArtifactRequirement(
        workflow_definition_id=workflow_id, workflow_version=version,
        requirement_key=item["requirement_key"], artifact_type=item["artifact_type"],
        compatibility_mode=CompatibilityMode.EXACT,
        schema_constraint=item["artifact_schema"],
        cardinality_min=1 if item["required"] else 0, cardinality_max=1,
        required=item["required"], materialization_mode=MaterializationMode.VERIFIED_COPY,
        target_relative_path=item["target_relative_path"], created_at=now, updated_at=now,
    ) for item in requirements)
