"""Seed the reviewed literature Artifact producer and Idea Discovery consumer.

Revision ID: 20260806_0013
Revises: 20260806_0012
Create Date: 2026-08-07
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260806_0013"
down_revision: str | None = "20260806_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LS_ID = "literature-search-local-experimental"
LS_VERSION = "0.4.0"
LS_CHECKSUM = "sha256:864102b119364626b82a1644b3cfd7699746633950097ad0d5cd7bb5facf5c2c"
LS_CAPSULE_ID = "capsule-e9e6a2e0aa46146818fb6123e03877f3"
LS_CAPSULE_VERSION = "0.6.0"
LS_CAPSULE_CHECKSUM = "sha256:e9e6a2e0aa46146818fb6123e03877f32abaa8745f9c0b3139572530ccd1b80d"

IDEA_ID = "idea-discovery-local-experimental"
IDEA_VERSION = "0.1.0"
IDEA_CHECKSUM = "sha256:b9468ed938f4dce3fb856a06fe7c1c054456f361a0c3fb3b393234f9ac448491"
IDEA_CAPSULE_ID = "capsule-f07330db6f0d87f3fd482b698223ea75"
IDEA_CAPSULE_VERSION = "0.1.0"
IDEA_CAPSULE_CHECKSUM = "sha256:f07330db6f0d87f3fd482b698223ea75414ce087fac193de80f8e8522e9e6452"

ARTIFACT_TYPE = "selected-paper-library/v1"
ARTIFACT_SCHEMA = "selected-paper-library/v1"

LS_OUTPUT_CONTRACT = {
    "artifact_type": ARTIFACT_TYPE,
    "artifact_schema_version": ARTIFACT_SCHEMA,
    "media_type": "application/json",
    "relative_path_prefix": "outputs/artifacts/selected-paper-library",
    "content_addressed_filename": "sha256-<content-sha256>.json",
    "progress_artifact_kind": ARTIFACT_TYPE,
}


def upgrade() -> None:
    connection = op.get_bind()
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    connection.execute(
        sa.text("""
            INSERT INTO local_workflow_definition_versions
              (workflow_definition_id, version, contract_checksum, input_schema_id,
               output_schema_id, compatibility, review_status, published_at,
               created_at, updated_at)
            VALUES (:definition_id, :version, :checksum, 'research-request/v0.2',
                    'literature-search-report/v0.2', CAST(:compatibility AS jsonb),
                    'REVIEWED', :now, :now, :now)
            ON CONFLICT (workflow_definition_id, version) DO NOTHING
        """),
        {
            "definition_id": LS_ID,
            "version": LS_VERSION,
            "checksum": LS_CHECKSUM,
            "compatibility": _json({
                "package_schema_version": "workflow-package/v0.1",
                "production_artifact_type": ARTIFACT_TYPE,
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
            "capsule_id": LS_CAPSULE_ID,
            "capsule_version": LS_CAPSULE_VERSION,
            "definition_id": LS_ID,
            "workflow_version": LS_VERSION,
            "checksum": LS_CAPSULE_CHECKSUM,
            "mutable_roots": _json([
                "memory/context.md", "memory/progress", "memory/round-control.json",
                "memory/search", "outputs",
            ]),
            "capabilities": _json([
                "paper.search/v0.1", "progress.read/v0.1", "progress.upload/v0.2",
            ]),
            "compatibility": _json({
                "package_schema_version": "workflow-package/v0.1",
                "package_template_id": "literature-search-package-experimental",
                "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
                "artifact_outputs": [LS_OUTPUT_CONTRACT],
            }),
            "now": now,
        },
    )
    connection.execute(
        sa.text("""
            INSERT INTO local_workflow_definitions
              (workflow_definition_id, display_name, description, lifecycle,
               allows_multiple_instances, created_at, updated_at)
            VALUES (:definition_id, 'Idea Discovery', :description, 'AVAILABLE',
                    true, :now, :now)
            ON CONFLICT (workflow_definition_id) DO NOTHING
        """),
        {
            "definition_id": IDEA_ID,
            "description": (
                "Interactively develop evidence-grounded candidate research directions "
                "from an explicitly selected literature Artifact."
            ),
            "now": now,
        },
    )
    connection.execute(
        sa.text("""
            INSERT INTO local_workflow_definition_versions
              (workflow_definition_id, version, contract_checksum, input_schema_id,
               output_schema_id, compatibility, review_status, published_at,
               created_at, updated_at)
            VALUES (:definition_id, :version, :checksum, :input_schema,
                    'candidate-ideas/v0.1', CAST(:compatibility AS jsonb),
                    'REVIEWED', :now, :now, :now)
            ON CONFLICT (workflow_definition_id, version) DO NOTHING
        """),
        {
            "definition_id": IDEA_ID,
            "version": IDEA_VERSION,
            "checksum": IDEA_CHECKSUM,
            "input_schema": ARTIFACT_SCHEMA,
            "compatibility": _json({
                "package_schema_version": "workflow-package/v0.1",
                "artifact_requirement_key": "paper_library",
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
            "mutable_roots": _json(["memory/context.md", "memory/progress", "outputs", "inputs"]),
            "capabilities": _json(["progress.upload/v0.2", "artifact.materialize/v0.1"]),
            "compatibility": _json({
                "package_schema_version": "workflow-package/v0.1",
                "package_template_id": "idea-discovery-package-experimental",
                "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
                "artifact_requirements": [{
                    "requirement_key": "paper_library",
                    "artifact_type": ARTIFACT_TYPE,
                    "artifact_schema_version": ARTIFACT_SCHEMA,
                    "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
                    "materialization_mode": "VERIFIED_COPY",
                    "target_relative_path": "inputs/selected-paper-library.json",
                }],
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
            "artifact_type": ARTIFACT_TYPE,
            "artifact_schema": ARTIFACT_SCHEMA,
            "now": now,
        },
    )
    _assert_seed_content(connection)


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("""
        DELETE FROM workflow_artifact_requirements
        WHERE workflow_definition_id = :id AND workflow_version = :version
          AND requirement_key = 'paper_library'
    """), {"id": IDEA_ID, "version": IDEA_VERSION})
    connection.execute(sa.text("""
        DELETE FROM local_workflow_capsule_versions
        WHERE (capsule_id, capsule_version) IN (
          (:idea_capsule, :idea_version), (:ls_capsule, :ls_version)
        )
    """), {
        "idea_capsule": IDEA_CAPSULE_ID, "idea_version": IDEA_CAPSULE_VERSION,
        "ls_capsule": LS_CAPSULE_ID, "ls_version": LS_CAPSULE_VERSION,
    })
    connection.execute(sa.text("""
        DELETE FROM local_workflow_definition_versions
        WHERE (workflow_definition_id, version) IN (
          (:idea_id, :idea_version), (:ls_id, :ls_version)
        )
    """), {
        "idea_id": IDEA_ID, "idea_version": IDEA_VERSION,
        "ls_id": LS_ID, "ls_version": LS_VERSION,
    })
    connection.execute(sa.text("""
        DELETE FROM local_workflow_definitions WHERE workflow_definition_id = :id
    """), {"id": IDEA_ID})


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _assert_seed_content(connection: sa.Connection) -> None:
    definition = connection.execute(sa.text("""
        SELECT display_name, description, lifecycle, allows_multiple_instances
        FROM local_workflow_definitions WHERE workflow_definition_id = :id
    """), {"id": IDEA_ID}).mappings().one_or_none()
    if definition is None or dict(definition) != {
        "display_name": "Idea Discovery",
        "description": (
            "Interactively develop evidence-grounded candidate research directions "
            "from an explicitly selected literature Artifact."
        ),
        "lifecycle": "AVAILABLE",
        "allows_multiple_instances": True,
    }:
        raise RuntimeError("B7 Idea Discovery Workflow Definition seed conflict")
    rows = connection.execute(sa.text("""
        SELECT workflow_definition_id, version, contract_checksum
        FROM local_workflow_definition_versions
        WHERE (workflow_definition_id, version) IN (
          (:ls_id, :ls_version), (:idea_id, :idea_version)
        ) ORDER BY workflow_definition_id
    """), {
        "ls_id": LS_ID, "ls_version": LS_VERSION,
        "idea_id": IDEA_ID, "idea_version": IDEA_VERSION,
    }).mappings().all()
    expected = {
        (LS_ID, LS_VERSION): LS_CHECKSUM,
        (IDEA_ID, IDEA_VERSION): IDEA_CHECKSUM,
    }
    if {(row["workflow_definition_id"], row["version"]): row["contract_checksum"] for row in rows} != expected:
        raise RuntimeError("B7 Workflow Definition Version seed conflict")
    capsules = connection.execute(sa.text("""
        SELECT capsule_id, capsule_version, definition_checksum
        FROM local_workflow_capsule_versions
        WHERE (capsule_id, capsule_version) IN (
          (:ls_id, :ls_version), (:idea_id, :idea_version)
        )
    """), {
        "ls_id": LS_CAPSULE_ID, "ls_version": LS_CAPSULE_VERSION,
        "idea_id": IDEA_CAPSULE_ID, "idea_version": IDEA_CAPSULE_VERSION,
    }).mappings().all()
    expected_capsules = {
        (LS_CAPSULE_ID, LS_CAPSULE_VERSION): LS_CAPSULE_CHECKSUM,
        (IDEA_CAPSULE_ID, IDEA_CAPSULE_VERSION): IDEA_CAPSULE_CHECKSUM,
    }
    if {(row["capsule_id"], row["capsule_version"]): row["definition_checksum"] for row in capsules} != expected_capsules:
        raise RuntimeError("B7 Workflow Capsule seed conflict")
    requirement = connection.execute(sa.text("""
        SELECT artifact_type, compatibility_mode, schema_constraint,
               cardinality_min, cardinality_max, required,
               materialization_mode, target_relative_path
        FROM workflow_artifact_requirements
        WHERE workflow_definition_id = :id AND workflow_version = :version
          AND requirement_key = 'paper_library'
    """), {"id": IDEA_ID, "version": IDEA_VERSION}).mappings().one_or_none()
    if requirement is None or dict(requirement) != {
        "artifact_type": ARTIFACT_TYPE,
        "compatibility_mode": "EXACT",
        "schema_constraint": ARTIFACT_SCHEMA,
        "cardinality_min": 1,
        "cardinality_max": 1,
        "required": True,
        "materialization_mode": "VERIFIED_COPY",
        "target_relative_path": "inputs/selected-paper-library.json",
    }:
        raise RuntimeError("B7 Idea Discovery Artifact requirement seed conflict")
