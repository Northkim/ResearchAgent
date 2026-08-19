"""Publish Writing Revision with optional causal-Review support.

Revision ID: 20260819_0034
Revises: 20260818_0033
Create Date: 2026-08-19
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260819_0034"
down_revision: str | None = "20260818_0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WORKFLOW_ID = "writing-local-experimental"
WORKFLOW_VERSION = "0.7.0"
CONTRACT_CHECKSUM = "sha256:07827ae2914257f9e2ab11a8a2fcce1ecbcc584eb25a8d6dcb791ad0b87cccd5"
CAPSULE_ID = "capsule-c9b068dd677efa8098f6ff4ddbdcf5e8"
CAPSULE_VERSION = "0.9.0"
CAPSULE_CHECKSUM = "sha256:c9b068dd677efa8098f6ff4ddbdcf5e8d7824348b0f2d89f79a41639593fc20d"
SKILL_ID = "research-artifact-provenance-local-builtin"
SKILL_VERSION = "0.1.0"
SKILL_CHECKSUM = "sha256:0650f150099823499d1fdcf072abd70275e87cb76e3e9d64dfb12361cc13d7c8"
OUTPUT = "manuscript-draft/v5"
MODE = "REVIEW_TO_WRITING_REVISION_V5_OPTIONAL_REVIEW_SUPPORT"


def _requirement(key: str, artifact_type: str, required: bool, target: str) -> dict[str, object]:
    return {
        "requirement_key": key,
        "artifact_type": artifact_type,
        "artifact_schema": artifact_type,
        "cardinality": "ONE",
        "required": required,
        "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
        "materialization_mode": "VERIFIED_COPY",
        "target_relative_path": target,
    }


REQUIREMENTS = (
    _requirement("prior_manuscript", "manuscript-draft/v4", True, "inputs/prior-manuscript.json"),
    _requirement("causal_review", "review-report/v3", True, "inputs/review-report.json"),
    _requirement("research_idea", "selected-research-idea/v1", True, "inputs/selected-research-idea.json"),
    _requirement("literature_library", "selected-paper-library/v1", True, "inputs/selected-paper-library.json"),
    _requirement("experiment_record", "experiment-record/v5", False, "inputs/experiment-record.json"),
)
MUTABLE_ROOTS = (
    "memory/context.md",
    "memory/progress",
    "memory/input-provenance.json",
    "memory/revision-plan.json",
    "memory/revision-plan-approval.json",
    "memory/claims.json",
    "memory/citations.json",
    "memory/issue-accounting.json",
    "memory/owner-review.json",
    "memory/current-artifact.json",
    "outputs",
    "inputs",
)


def _output() -> dict[str, str]:
    return {
        "artifact_type": OUTPUT,
        "artifact_schema_version": OUTPUT,
        "media_type": "application/json",
        "relative_path_prefix": "outputs/artifacts/manuscript-draft",
        "content_addressed_filename": "sha256-<content-sha256>.json",
        "progress_artifact_kind": OUTPUT,
    }


def upgrade() -> None:
    connection = op.get_bind()
    _assert_preconditions(connection)
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    output = _output()
    compatibility = {
        "package_schema_version": "workflow-package/v0.1",
        "artifact_requirements": REQUIREMENTS,
        "artifact_outputs": [output],
        "supported_mode": MODE,
        "experiment_evidence_authority": "experiment-record/v5",
        "presentation_companion_authoritative": False,
        "writing_role": "REVISION",
        "default_project_setup": False,
    }
    connection.execute(sa.text("""
        INSERT INTO local_workflow_definition_versions
          (workflow_definition_id, version, contract_checksum, input_schema_id,
           output_schema_id, compatibility, review_status, core_capability_maturity,
           published_at, created_at, updated_at)
        VALUES (:id, :version, :contract, 'artifact-bindings/v0.1', :output,
                CAST(:compatibility AS jsonb), 'REVIEWED', 'REVIEWED_CORE',
                :now, :now, :now)
    """), {
        "id": WORKFLOW_ID, "version": WORKFLOW_VERSION,
        "contract": CONTRACT_CHECKSUM, "output": OUTPUT,
        "compatibility": _json(compatibility), "now": now,
    })
    capsule_compatibility = {
        "package_schema_version": "workflow-package/v0.1",
        "package_template_id": "writing-scaffold-package-experimental",
        "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
        "artifact_requirements": REQUIREMENTS,
        "artifact_outputs": [output],
        "core_capability_maturity": "REVIEWED_CORE",
        "skill_pins": [{
            "skill_id": SKILL_ID, "skill_version": SKILL_VERSION,
            "skill_checksum": SKILL_CHECKSUM, "trust": "BUILT_IN_REVIEWED",
        }],
        "experiment_evidence_authority": "experiment-record/v5",
        "interaction_boundary": "TWO_EXACT_OWNER_CHECKPOINTS",
    }
    connection.execute(sa.text("""
        INSERT INTO local_workflow_capsule_versions
          (capsule_id, capsule_version, workflow_definition_id, workflow_version,
           definition_checksum, archive_size_bytes, archive_media_type,
           mutable_roots, capability_requirements, compatibility, review_status,
           legacy_package_compatible, created_at, updated_at)
        VALUES (:capsule_id, :capsule_version, :id, :version, :capsule, 0,
                'application/zip', CAST(:mutable AS jsonb), CAST(:capabilities AS jsonb),
                CAST(:compatibility AS jsonb), 'REVIEWED', false, :now, :now)
    """), {
        "capsule_id": CAPSULE_ID, "capsule_version": CAPSULE_VERSION,
        "id": WORKFLOW_ID, "version": WORKFLOW_VERSION,
        "capsule": CAPSULE_CHECKSUM, "mutable": _json(MUTABLE_ROOTS),
        "capabilities": _json([
            "progress.upload/v0.2", "artifact.materialize/v0.1", "artifact.publish/v0.1",
        ]),
        "compatibility": _json(capsule_compatibility), "now": now,
    })
    connection.execute(sa.text("""
        INSERT INTO workflow_definition_version_skill_pins
          (workflow_definition_id, workflow_version, pin_order, skill_id,
           skill_version, skill_checksum, purpose, created_at)
        VALUES (:id, :version, 0, :skill_id, :skill_version, :skill_checksum,
                'Preserve exact v5 evidence and downstream Artifact provenance.', :now)
    """), {
        "id": WORKFLOW_ID, "version": WORKFLOW_VERSION,
        "skill_id": SKILL_ID, "skill_version": SKILL_VERSION,
        "skill_checksum": SKILL_CHECKSUM, "now": now,
    })
    for requirement in REQUIREMENTS:
        connection.execute(sa.text("""
            INSERT INTO workflow_artifact_requirements
              (workflow_definition_id, workflow_version, requirement_key,
               artifact_type, compatibility_mode, schema_constraint,
               cardinality_min, cardinality_max, required, materialization_mode,
               target_relative_path, created_at, updated_at)
            VALUES (:id, :version, :key, :artifact_type, 'EXACT', :artifact_type,
                    :minimum, 1, :required, 'VERIFIED_COPY', :target, :now, :now)
        """), {
            "id": WORKFLOW_ID, "version": WORKFLOW_VERSION,
            "key": requirement["requirement_key"],
            "artifact_type": requirement["artifact_type"],
            "minimum": 1 if requirement["required"] else 0,
            "required": requirement["required"],
            "target": requirement["target_relative_path"], "now": now,
        })
    _assert_seed(connection)


def downgrade() -> None:
    connection = op.get_bind()
    params = {
        "id": WORKFLOW_ID, "version": WORKFLOW_VERSION,
        "capsule_id": CAPSULE_ID, "capsule_version": CAPSULE_VERSION,
    }
    connection.execute(sa.text(
        "DELETE FROM workflow_artifact_requirements "
        "WHERE workflow_definition_id=:id AND workflow_version=:version"
    ), params)
    connection.execute(sa.text(
        "DELETE FROM workflow_definition_version_skill_pins "
        "WHERE workflow_definition_id=:id AND workflow_version=:version"
    ), params)
    connection.execute(sa.text(
        "DELETE FROM local_workflow_capsule_versions "
        "WHERE capsule_id=:capsule_id AND capsule_version=:capsule_version"
    ), params)
    connection.execute(sa.text(
        "DELETE FROM local_workflow_definition_versions "
        "WHERE workflow_definition_id=:id AND version=:version"
    ), params)


def _assert_preconditions(connection: sa.Connection) -> None:
    historical = connection.execute(sa.text("""
        SELECT definition_checksum FROM local_workflow_capsule_versions
        WHERE workflow_definition_id=:id AND workflow_version='0.6.0'
          AND capsule_id='capsule-ff1975990022b65f0bfd83514820dd3b'
          AND capsule_version='0.8.0'
    """), {"id": WORKFLOW_ID}).scalar_one_or_none()
    if historical != "sha256:ff1975990022b65f0bfd83514820dd3b84910e783835aed2b4f65cf7749b370d":
        raise RuntimeError("optional Review support publication requires immutable Revision 0.6")
    occupied = connection.execute(sa.text("""
        SELECT 1 FROM local_workflow_definition_versions
        WHERE workflow_definition_id=:id AND version=:version
    """), {"id": WORKFLOW_ID, "version": WORKFLOW_VERSION}).scalar_one_or_none()
    if occupied is not None:
        raise RuntimeError("optional Review support Revision identity is occupied")


def _assert_seed(connection: sa.Connection) -> None:
    row = connection.execute(sa.text("""
        SELECT v.contract_checksum, v.output_schema_id, c.capsule_id,
               c.capsule_version, c.definition_checksum,
               (SELECT count(*) FROM workflow_artifact_requirements r
                WHERE r.workflow_definition_id=v.workflow_definition_id
                  AND r.workflow_version=v.version) AS requirement_count
        FROM local_workflow_definition_versions v
        JOIN local_workflow_capsule_versions c
          ON c.workflow_definition_id=v.workflow_definition_id
         AND c.workflow_version=v.version
        WHERE v.workflow_definition_id=:id AND v.version=:version
    """), {"id": WORKFLOW_ID, "version": WORKFLOW_VERSION}).mappings().one_or_none()
    expected = {
        "contract_checksum": CONTRACT_CHECKSUM,
        "output_schema_id": OUTPUT,
        "capsule_id": CAPSULE_ID,
        "capsule_version": CAPSULE_VERSION,
        "definition_checksum": CAPSULE_CHECKSUM,
        "requirement_count": len(REQUIREMENTS),
    }
    if row is None or dict(row) != expected:
        raise RuntimeError("optional Review support Revision seed conflict")


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
