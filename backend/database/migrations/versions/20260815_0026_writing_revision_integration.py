"""Publish immutable Writing Revision Definition 0.4 and Capsule 0.6.

Revision ID: 20260815_0026
Revises: 20260815_0025
Create Date: 2026-08-15
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260815_0026"
down_revision: str | None = "20260815_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WORKFLOW_ID = "writing-local-experimental"
VERSION = "0.4.0"
CONTRACT_CHECKSUM = "sha256:53e910ac525f4fe6f69e2c75631d0d1f8ff82ad7620a9c1f879c3198e45828ea"
CAPSULE_ID = "capsule-d10eeb323d17944c6ef8b4ed9bfb1497"
CAPSULE_VERSION = "0.6.0"
CAPSULE_CHECKSUM = "sha256:d10eeb323d17944c6ef8b4ed9bfb149751ee96bbf6cac6b6bd41b45629c327c3"
SKILL_ID = "research-artifact-provenance-local-builtin"
SKILL_VERSION = "0.1.0"
SKILL_CHECKSUM = "sha256:0650f150099823499d1fdcf072abd70275e87cb76e3e9d64dfb12361cc13d7c8"
HISTORICAL_CAPSULE_CHECKSUM = "sha256:3f94b97702190efed2a4fcd2c0e5f770eaf64020a56ec5f14eaf41412314e8ad"


def upgrade() -> None:
    connection = op.get_bind(); _assert_preconditions(connection)
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    requirements = [
        _requirement("prior_manuscript", "manuscript-draft/v2", True, "inputs/prior-manuscript.json"),
        _requirement("causal_review", "review-report/v2", True, "inputs/review-report.json"),
        _requirement("research_idea", "selected-research-idea/v1", True, "inputs/selected-research-idea.json"),
        _requirement("literature_library", "selected-paper-library/v1", True, "inputs/selected-paper-library.json"),
        _requirement("experiment_record", "experiment-record/v2", False, "inputs/experiment-record.json"),
    ]
    output = {
        "artifact_type": "manuscript-draft/v3", "artifact_schema_version": "manuscript-draft/v3",
        "media_type": "application/json", "relative_path_prefix": "outputs/artifacts/manuscript-draft",
        "content_addressed_filename": "sha256-<content-sha256>.json",
        "progress_artifact_kind": "manuscript-draft/v3",
    }
    compatibility = {
        "package_schema_version": "workflow-package/v0.1",
        "artifact_requirements": requirements, "artifact_outputs": [output],
        "supported_mode": "REVIEW_TO_WRITING_REVISION_ROUND_ONE",
        "revision_dispositions": ["ADDRESSED", "PARTIALLY_ADDRESSED", "NOT_ADDRESSED"],
        "default_project_setup": False,
    }
    connection.execute(sa.text("""
        INSERT INTO local_workflow_definition_versions
          (workflow_definition_id, version, contract_checksum, input_schema_id,
           output_schema_id, compatibility, review_status, core_capability_maturity,
           published_at, created_at, updated_at)
        VALUES (:id, :version, :checksum, 'artifact-bindings/v0.1',
                'manuscript-draft/v3', CAST(:compatibility AS jsonb),
                'REVIEWED', 'REVIEWED_CORE', :now, :now, :now)
    """), {"id": WORKFLOW_ID, "version": VERSION, "checksum": CONTRACT_CHECKSUM,
             "compatibility": _json(compatibility), "now": now})
    capsule_compatibility = {
        "package_schema_version": "workflow-package/v0.1",
        "package_template_id": "writing-scaffold-package-experimental",
        "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
        "artifact_requirements": requirements, "artifact_outputs": [output],
        "core_capability_maturity": "REVIEWED_CORE",
        "skill_pins": [{"skill_id": SKILL_ID, "skill_version": SKILL_VERSION,
                        "skill_checksum": SKILL_CHECKSUM, "trust": "BUILT_IN_REVIEWED"}],
        "interaction_boundary": "EXACT_REVISION_PLAN_AND_FINAL_DRAFT_CHECKPOINTS",
    }
    connection.execute(sa.text("""
        INSERT INTO local_workflow_capsule_versions
          (capsule_id, capsule_version, workflow_definition_id, workflow_version,
           definition_checksum, archive_size_bytes, archive_media_type,
           mutable_roots, capability_requirements, compatibility, review_status,
           legacy_package_compatible, created_at, updated_at)
        VALUES (:capsule_id, :capsule_version, :id, :version, :checksum, 0,
                'application/zip', CAST(:mutable_roots AS jsonb),
                CAST(:capabilities AS jsonb), CAST(:compatibility AS jsonb),
                'REVIEWED', false, :now, :now)
    """), {
        "capsule_id": CAPSULE_ID, "capsule_version": CAPSULE_VERSION,
        "id": WORKFLOW_ID, "version": VERSION, "checksum": CAPSULE_CHECKSUM,
        "mutable_roots": _json([
            "memory/context.md", "memory/progress", "memory/input-provenance.json",
            "memory/revision-plan.json", "memory/revision-plan-approval.json",
            "memory/claims.json", "memory/citations.json", "memory/issue-accounting.json",
            "memory/owner-review.json", "memory/current-artifact.json", "outputs", "inputs",
        ]),
        "capabilities": _json(["progress.upload/v0.2", "artifact.materialize/v0.1", "artifact.publish/v0.1"]),
        "compatibility": _json(capsule_compatibility), "now": now,
    })
    connection.execute(sa.text("""
        INSERT INTO workflow_definition_version_skill_pins
          (workflow_definition_id, workflow_version, pin_order, skill_id,
           skill_version, skill_checksum, purpose, created_at)
        VALUES (:id, :version, 0, :skill_id, :skill_version, :skill_checksum,
                'Revise exact claims while preserving Artifact provenance.', :now)
    """), {"id": WORKFLOW_ID, "version": VERSION, "skill_id": SKILL_ID,
             "skill_version": SKILL_VERSION, "skill_checksum": SKILL_CHECKSUM, "now": now})
    for requirement in requirements:
        connection.execute(sa.text("""
            INSERT INTO workflow_artifact_requirements
              (workflow_definition_id, workflow_version, requirement_key,
               artifact_type, compatibility_mode, schema_constraint,
               cardinality_min, cardinality_max, required, materialization_mode,
               target_relative_path, created_at, updated_at)
            VALUES (:id, :version, :key, :artifact_type, 'EXACT', :schema,
                    :minimum, 1, :required, 'VERIFIED_COPY', :target, :now, :now)
        """), {"id": WORKFLOW_ID, "version": VERSION,
                 "key": requirement["requirement_key"], "artifact_type": requirement["artifact_type"],
                 "schema": requirement["artifact_schema"], "minimum": 1 if requirement["required"] else 0,
                 "required": requirement["required"], "target": requirement["target_relative_path"], "now": now})
    _assert_seed(connection)


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("DELETE FROM workflow_artifact_requirements WHERE workflow_definition_id = :id AND workflow_version = :version"), {"id": WORKFLOW_ID, "version": VERSION})
    connection.execute(sa.text("DELETE FROM workflow_definition_version_skill_pins WHERE workflow_definition_id = :id AND workflow_version = :version"), {"id": WORKFLOW_ID, "version": VERSION})
    connection.execute(sa.text("DELETE FROM local_workflow_capsule_versions WHERE capsule_id = :id AND capsule_version = :capsule_version"), {"id": CAPSULE_ID, "capsule_version": CAPSULE_VERSION})
    connection.execute(sa.text("DELETE FROM local_workflow_definition_versions WHERE workflow_definition_id = :id AND version = :version"), {"id": WORKFLOW_ID, "version": VERSION})


def _requirement(key: str, artifact_type: str, required: bool, target: str) -> dict[str, object]:
    return {"requirement_key": key, "artifact_type": artifact_type, "artifact_schema": artifact_type,
            "cardinality": "ONE", "required": required,
            "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
            "materialization_mode": "VERIFIED_COPY", "target_relative_path": target}


def _assert_preconditions(connection: sa.Connection) -> None:
    historical = connection.execute(sa.text("""
        SELECT definition_checksum FROM local_workflow_capsule_versions
        WHERE workflow_definition_id = :id AND workflow_version = '0.3.0'
          AND capsule_version = '0.5.0'
    """), {"id": WORKFLOW_ID}).scalar_one_or_none()
    if historical != HISTORICAL_CAPSULE_CHECKSUM:
        raise RuntimeError("Writing Revision requires immutable Real Writing 0.3/0.5")


def _assert_seed(connection: sa.Connection) -> None:
    row = connection.execute(sa.text("""
        SELECT v.contract_checksum, v.output_schema_id, v.core_capability_maturity,
               c.capsule_id, c.capsule_version, c.definition_checksum,
               (SELECT count(*) FROM workflow_artifact_requirements a
                WHERE a.workflow_definition_id = v.workflow_definition_id
                  AND a.workflow_version = v.version) AS artifact_count
        FROM local_workflow_definition_versions v
        JOIN local_workflow_capsule_versions c
          ON c.workflow_definition_id = v.workflow_definition_id
         AND c.workflow_version = v.version
        WHERE v.workflow_definition_id = :id AND v.version = :version
    """), {"id": WORKFLOW_ID, "version": VERSION}).mappings().one_or_none()
    expected = {"contract_checksum": CONTRACT_CHECKSUM, "output_schema_id": "manuscript-draft/v3",
                "core_capability_maturity": "REVIEWED_CORE", "capsule_id": CAPSULE_ID,
                "capsule_version": CAPSULE_VERSION, "definition_checksum": CAPSULE_CHECKSUM,
                "artifact_count": 5}
    if row is None or dict(row) != expected:
        raise RuntimeError("Writing Revision immutable seed conflict")


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
