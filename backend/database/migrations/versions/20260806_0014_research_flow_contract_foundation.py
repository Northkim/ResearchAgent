"""Publish Idea Discovery 0.2 and canonical Core Capability Maturity.

Revision ID: 20260806_0014
Revises: 20260806_0013
Create Date: 2026-08-07
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260806_0014"
down_revision: str | None = "20260806_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

IDEA_ID = "idea-discovery-local-experimental"
IDEA_VERSION = "0.2.0"
IDEA_CHECKSUM = "sha256:6ddc73c6bbe61a425a338f0b6d1c7c1cf50608ce87b5333a83c101a93cb519d5"
IDEA_CAPSULE_ID = "capsule-6b66289a38895ce0eba2f76cd7725176"
IDEA_CAPSULE_VERSION = "0.2.0"
IDEA_CAPSULE_CHECKSUM = "sha256:6b66289a38895ce0eba2f76cd77251766711a6ec8ebf416cdd368695b5c727f5"

LITERATURE_TYPE = "selected-paper-library/v1"
SELECTED_IDEA_TYPE = "selected-research-idea/v1"

SELECTED_IDEA_OUTPUT = {
    "artifact_type": SELECTED_IDEA_TYPE,
    "artifact_schema_version": SELECTED_IDEA_TYPE,
    "media_type": "application/json",
    "relative_path_prefix": "outputs/artifacts/selected-research-idea",
    "content_addressed_filename": "sha256-<content-sha256>.json",
    "progress_artifact_kind": SELECTED_IDEA_TYPE,
}


def upgrade() -> None:
    op.add_column(
        "local_workflow_definition_versions",
        sa.Column(
            "core_capability_maturity",
            sa.String(length=24),
            nullable=False,
            server_default="REVIEWED_CORE",
        ),
    )
    op.create_check_constraint(
        "ck_local_workflow_definition_versions_local_workflow_definition_version_core_maturity",
        "local_workflow_definition_versions",
        "core_capability_maturity IN ('REVIEWED_CORE', 'SCAFFOLD_CORE')",
    )
    op.alter_column(
        "local_workflow_definition_versions",
        "core_capability_maturity",
        server_default=None,
    )

    connection = op.get_bind()
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    connection.execute(
        sa.text("""
            INSERT INTO local_workflow_definition_versions
              (workflow_definition_id, version, contract_checksum, input_schema_id,
               output_schema_id, compatibility, review_status,
               core_capability_maturity, published_at, created_at, updated_at)
            VALUES (:definition_id, :version, :checksum, :input_schema,
                    :output_schema, CAST(:compatibility AS jsonb), 'REVIEWED',
                    'REVIEWED_CORE', :now, :now, :now)
            ON CONFLICT (workflow_definition_id, version) DO NOTHING
        """),
        {
            "definition_id": IDEA_ID,
            "version": IDEA_VERSION,
            "checksum": IDEA_CHECKSUM,
            "input_schema": LITERATURE_TYPE,
            "output_schema": SELECTED_IDEA_TYPE,
            "compatibility": _json({
                "package_schema_version": "workflow-package/v0.1",
                "artifact_requirement_key": "paper_library",
                "artifact_outputs": [SELECTED_IDEA_OUTPUT],
                "explicit_selection_policy": "EXACTLY_ONE_USER_CONFIRMED",
                "novelty_claim_policy": "GLOBAL_NOVELTY_NOT_PROVEN",
            }),
            "now": now,
        },
    )
    connection.execute(
        sa.text("""
            INSERT INTO local_workflow_capsule_versions
              (capsule_id, capsule_version, workflow_definition_id, workflow_version,
               definition_checksum, archive_size_bytes, archive_media_type,
               mutable_roots, capability_requirements, compatibility, review_status,
               legacy_package_compatible, created_at, updated_at)
            VALUES (:capsule_id, :capsule_version, :definition_id, :workflow_version,
                    :checksum, 0, 'application/zip', CAST(:mutable_roots AS jsonb),
                    CAST(:capabilities AS jsonb), CAST(:compatibility AS jsonb),
                    'REVIEWED', false, :now, :now)
            ON CONFLICT (capsule_id, capsule_version) DO NOTHING
        """),
        {
            "capsule_id": IDEA_CAPSULE_ID,
            "capsule_version": IDEA_CAPSULE_VERSION,
            "definition_id": IDEA_ID,
            "workflow_version": IDEA_VERSION,
            "checksum": IDEA_CAPSULE_CHECKSUM,
            "mutable_roots": _json([
                "memory/context.md", "memory/progress", "outputs", "inputs",
            ]),
            "capabilities": _json([
                "progress.upload/v0.2", "artifact.materialize/v0.1",
                "artifact.publish/v0.1",
            ]),
            "compatibility": _json({
                "package_schema_version": "workflow-package/v0.1",
                "package_template_id": "idea-discovery-package-experimental",
                "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
                "artifact_requirements": [{
                    "requirement_key": "paper_library",
                    "artifact_type": LITERATURE_TYPE,
                    "artifact_schema_version": LITERATURE_TYPE,
                    "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
                    "materialization_mode": "VERIFIED_COPY",
                    "target_relative_path": "inputs/selected-paper-library.json",
                }],
                "artifact_outputs": [SELECTED_IDEA_OUTPUT],
                "core_capability_maturity": "REVIEWED_CORE",
            }),
            "now": now,
        },
    )
    connection.execute(
        sa.text("""
            INSERT INTO workflow_artifact_requirements
              (workflow_definition_id, workflow_version, requirement_key,
               artifact_type, compatibility_mode, schema_constraint,
               cardinality_min, cardinality_max, required, materialization_mode,
               target_relative_path, created_at, updated_at)
            VALUES (:definition_id, :version, 'paper_library', :artifact_type,
                    'EXACT', :artifact_schema, 1, 1, true, 'VERIFIED_COPY',
                    'inputs/selected-paper-library.json', :now, :now)
            ON CONFLICT (workflow_definition_id, workflow_version, requirement_key)
            DO NOTHING
        """),
        {
            "definition_id": IDEA_ID,
            "version": IDEA_VERSION,
            "artifact_type": LITERATURE_TYPE,
            "artifact_schema": LITERATURE_TYPE,
            "now": now,
        },
    )
    _assert_seed_content(connection)


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("""
            DELETE FROM workflow_artifact_requirements
            WHERE workflow_definition_id = :id AND workflow_version = :version
              AND requirement_key = 'paper_library'
        """),
        {"id": IDEA_ID, "version": IDEA_VERSION},
    )
    connection.execute(
        sa.text("""
            DELETE FROM local_workflow_capsule_versions
            WHERE capsule_id = :id AND capsule_version = :version
        """),
        {"id": IDEA_CAPSULE_ID, "version": IDEA_CAPSULE_VERSION},
    )
    connection.execute(
        sa.text("""
            DELETE FROM local_workflow_definition_versions
            WHERE workflow_definition_id = :id AND version = :version
        """),
        {"id": IDEA_ID, "version": IDEA_VERSION},
    )
    op.drop_constraint(
        "ck_local_workflow_definition_versions_local_workflow_definition_version_core_maturity",
        "local_workflow_definition_versions",
        type_="check",
    )
    op.drop_column(
        "local_workflow_definition_versions", "core_capability_maturity"
    )


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _assert_seed_content(connection: sa.Connection) -> None:
    version = connection.execute(
        sa.text("""
            SELECT contract_checksum, input_schema_id, output_schema_id,
                   compatibility, review_status, core_capability_maturity
            FROM local_workflow_definition_versions
            WHERE workflow_definition_id = :id AND version = :version
        """),
        {"id": IDEA_ID, "version": IDEA_VERSION},
    ).mappings().one_or_none()
    expected_version = {
        "contract_checksum": IDEA_CHECKSUM,
        "input_schema_id": LITERATURE_TYPE,
        "output_schema_id": SELECTED_IDEA_TYPE,
        "compatibility": {
            "package_schema_version": "workflow-package/v0.1",
            "artifact_requirement_key": "paper_library",
            "artifact_outputs": [SELECTED_IDEA_OUTPUT],
            "explicit_selection_policy": "EXACTLY_ONE_USER_CONFIRMED",
            "novelty_claim_policy": "GLOBAL_NOVELTY_NOT_PROVEN",
        },
        "review_status": "REVIEWED",
        "core_capability_maturity": "REVIEWED_CORE",
    }
    if version is None or dict(version) != expected_version:
        raise RuntimeError("F1A Idea Discovery Definition Version seed conflict")
    capsule = connection.execute(
        sa.text("""
            SELECT definition_checksum, workflow_definition_id, workflow_version
            FROM local_workflow_capsule_versions
            WHERE capsule_id = :id AND capsule_version = :version
        """),
        {"id": IDEA_CAPSULE_ID, "version": IDEA_CAPSULE_VERSION},
    ).mappings().one_or_none()
    if capsule is None or dict(capsule) != {
        "definition_checksum": IDEA_CAPSULE_CHECKSUM,
        "workflow_definition_id": IDEA_ID,
        "workflow_version": IDEA_VERSION,
    }:
        raise RuntimeError("F1A Idea Discovery Capsule seed conflict")
    requirement = connection.execute(
        sa.text("""
            SELECT artifact_type, compatibility_mode, schema_constraint,
                   cardinality_min, cardinality_max, required,
                   materialization_mode, target_relative_path
            FROM workflow_artifact_requirements
            WHERE workflow_definition_id = :id AND workflow_version = :version
              AND requirement_key = 'paper_library'
        """),
        {"id": IDEA_ID, "version": IDEA_VERSION},
    ).mappings().one_or_none()
    if requirement is None or dict(requirement) != {
        "artifact_type": LITERATURE_TYPE,
        "compatibility_mode": "EXACT",
        "schema_constraint": LITERATURE_TYPE,
        "cardinality_min": 1,
        "cardinality_max": 1,
        "required": True,
        "materialization_mode": "VERIFIED_COPY",
        "target_relative_path": "inputs/selected-paper-library.json",
    }:
        raise RuntimeError("F1A Idea Discovery dependency seed conflict")
    non_reviewed = connection.scalar(sa.text("""
        SELECT COUNT(*) FROM local_workflow_definition_versions
        WHERE core_capability_maturity <> 'REVIEWED_CORE'
    """))
    if non_reviewed != 0:
        raise RuntimeError("F1A existing real Workflow maturity backfill conflict")
