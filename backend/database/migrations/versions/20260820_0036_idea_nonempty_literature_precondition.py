"""Publish forward Idea non-empty Literature precondition.

Revision ID: 20260820_0036
Revises: 20260820_0035
Create Date: 2026-08-20
"""

from __future__ import annotations

from collections.abc import Sequence
import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260820_0036"
down_revision: str | None = "20260820_0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

IDEA_ID = "idea-discovery-local-experimental"
IDEA_VERSION = "0.3.0"
IDEA_CONTRACT = "sha256:5385cfa76e7323664f1e321ad781f583edcd6f0fcbf32f36ffdbbefc4ef5e682"
CAPSULE_ID = "capsule-717aa7729919ccef977520a3622fb44f"
CAPSULE_VERSION = "0.4.0"
CAPSULE_CHECKSUM = "sha256:717aa7729919ccef977520a3622fb44f883d827b2ba0127458fdf49417a48d0a"
LITERATURE_TYPE = "selected-paper-library/v1"
IDEA_TYPE = "selected-research-idea/v1"
QUALIFICATION_SCHEMA = "reagent.artifact-qualification.selected-paper-library/v0.1"
PRECONDITION_SCHEMA = "reagent.artifact-precondition.selected-paper-library-nonempty/v0.1"


def _precondition() -> dict[str, object]:
    return {
        "schema": PRECONDITION_SCHEMA,
        "qualification_schema": QUALIFICATION_SCHEMA,
        "minimum_selected_count": 1,
    }


def _requirement() -> dict[str, object]:
    return {
        "requirement_key": "paper_library",
        "artifact_type": LITERATURE_TYPE,
        "artifact_schema_version": LITERATURE_TYPE,
        "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
        "materialization_mode": "VERIFIED_COPY",
        "target_relative_path": "inputs/selected-paper-library.json",
        "content_precondition": _precondition(),
    }


def _output() -> dict[str, str]:
    return {
        "artifact_type": IDEA_TYPE,
        "artifact_schema_version": IDEA_TYPE,
        "media_type": "application/json",
        "relative_path_prefix": "outputs/artifacts/selected-research-idea",
        "content_addressed_filename": "sha256-<content-sha256>.json",
        "progress_artifact_kind": IDEA_TYPE,
    }


def upgrade() -> None:
    op.add_column(
        "local_artifact_references",
        sa.Column("qualification_schema_id", sa.String(length=200)),
    )
    op.add_column(
        "local_artifact_references",
        sa.Column("qualification_checksum", sa.String(length=71)),
    )
    op.add_column(
        "local_artifact_references",
        sa.Column(
            "qualification_json",
            postgresql.JSONB(astext_type=sa.Text()),
        ),
    )
    op.add_column(
        "local_artifact_references",
        sa.Column("qualification_reported_at", sa.DateTime(timezone=True)),
    )
    op.create_check_constraint(
        "local_artifact_reference_qualification_all_or_none",
        "local_artifact_references",
        "(qualification_schema_id IS NULL AND qualification_checksum IS NULL "
        "AND qualification_json IS NULL AND qualification_reported_at IS NULL) OR "
        "(qualification_schema_id IS NOT NULL AND qualification_checksum IS NOT NULL "
        "AND qualification_json IS NOT NULL AND qualification_reported_at IS NOT NULL)",
    )
    op.create_check_constraint(
        "local_artifact_reference_qualification_checksum",
        "local_artifact_references",
        "qualification_checksum IS NULL OR qualification_checksum ~ '^sha256:[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        "local_artifact_reference_qualification_size",
        "local_artifact_references",
        "qualification_json IS NULL OR octet_length(qualification_json::text) <= 4096",
    )
    op.add_column(
        "workflow_artifact_requirements",
        sa.Column(
            "content_precondition",
            postgresql.JSONB(astext_type=sa.Text()),
        ),
    )

    connection = op.get_bind()
    _assert_preconditions(connection)
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    compatibility = {
        "package_schema_version": "workflow-package/v0.1",
        "artifact_requirement_key": "paper_library",
        "artifact_outputs": [_output()],
        "explicit_selection_policy": "EXACTLY_ONE_USER_CONFIRMED",
        "novelty_claim_policy": "GLOBAL_NOVELTY_NOT_PROVEN",
        "content_precondition": _precondition(),
    }
    connection.execute(sa.text("""
        INSERT INTO local_workflow_definition_versions
          (workflow_definition_id, version, contract_checksum, input_schema_id,
           output_schema_id, compatibility, review_status, core_capability_maturity,
           published_at, created_at, updated_at)
        VALUES (:id, :version, :contract, :literature, :idea,
                CAST(:compatibility AS jsonb), 'REVIEWED', 'REVIEWED_CORE',
                :now, :now, :now)
    """), {
        "id": IDEA_ID,
        "version": IDEA_VERSION,
        "contract": IDEA_CONTRACT,
        "literature": LITERATURE_TYPE,
        "idea": IDEA_TYPE,
        "compatibility": _json(compatibility),
        "now": now,
    })
    capsule_compatibility = {
        "package_schema_version": "workflow-package/v0.1",
        "package_template_id": "idea-discovery-package-experimental",
        "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
        "artifact_requirements": [_requirement()],
        "artifact_outputs": [_output()],
        "core_capability_maturity": "REVIEWED_CORE",
    }
    connection.execute(sa.text("""
        INSERT INTO local_workflow_capsule_versions
          (capsule_id, capsule_version, workflow_definition_id, workflow_version,
           definition_checksum, archive_size_bytes, archive_media_type,
           mutable_roots, capability_requirements, compatibility, review_status,
           legacy_package_compatible, created_at, updated_at)
        VALUES (:capsule_id, :capsule_version, :id, :version, :checksum, 0,
                'application/zip', CAST(:mutable AS jsonb), CAST(:capabilities AS jsonb),
                CAST(:compatibility AS jsonb), 'REVIEWED', false, :now, :now)
    """), {
        "capsule_id": CAPSULE_ID,
        "capsule_version": CAPSULE_VERSION,
        "id": IDEA_ID,
        "version": IDEA_VERSION,
        "checksum": CAPSULE_CHECKSUM,
        "mutable": _json(["memory/context.md", "memory/progress", "outputs", "inputs"]),
        "capabilities": _json([
            "progress.upload/v0.2", "artifact.materialize/v0.1",
            "artifact.publish/v0.1",
        ]),
        "compatibility": _json(capsule_compatibility),
        "now": now,
    })
    connection.execute(sa.text("""
        INSERT INTO workflow_artifact_requirements
          (workflow_definition_id, workflow_version, requirement_key,
           artifact_type, compatibility_mode, schema_constraint,
           cardinality_min, cardinality_max, required, materialization_mode,
           target_relative_path, content_precondition, created_at, updated_at)
        VALUES (:id, :version, 'paper_library', :literature, 'EXACT', :literature,
                1, 1, true, 'VERIFIED_COPY', 'inputs/selected-paper-library.json',
                CAST(:precondition AS jsonb), :now, :now)
    """), {
        "id": IDEA_ID,
        "version": IDEA_VERSION,
        "literature": LITERATURE_TYPE,
        "precondition": _json(_precondition()),
        "now": now,
    })
    _assert_seed(connection)


def downgrade() -> None:
    connection = op.get_bind()
    params = {
        "id": IDEA_ID,
        "version": IDEA_VERSION,
        "capsule_id": CAPSULE_ID,
        "capsule_version": CAPSULE_VERSION,
    }
    connection.execute(sa.text(
        "DELETE FROM workflow_artifact_requirements "
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
    op.drop_column("workflow_artifact_requirements", "content_precondition")
    op.drop_constraint(
        "local_artifact_reference_qualification_size",
        "local_artifact_references",
        type_="check",
    )
    op.drop_constraint(
        "local_artifact_reference_qualification_checksum",
        "local_artifact_references",
        type_="check",
    )
    op.drop_constraint(
        "local_artifact_reference_qualification_all_or_none",
        "local_artifact_references",
        type_="check",
    )
    op.drop_column("local_artifact_references", "qualification_reported_at")
    op.drop_column("local_artifact_references", "qualification_json")
    op.drop_column("local_artifact_references", "qualification_checksum")
    op.drop_column("local_artifact_references", "qualification_schema_id")


def _assert_preconditions(connection: sa.Connection) -> None:
    historical = connection.execute(sa.text("""
        SELECT definition_checksum FROM local_workflow_capsule_versions
        WHERE workflow_definition_id=:id AND workflow_version='0.2.0'
          AND capsule_id='capsule-3976596c49e3df30e08774233055bcce'
          AND capsule_version='0.3.0'
    """), {"id": IDEA_ID}).scalar_one_or_none()
    if historical != "sha256:3976596c49e3df30e08774233055bcce32745034e02a78c35970242cb22c772e":
        raise RuntimeError("forward Idea precondition requires immutable Idea 0.2")
    occupied = connection.execute(sa.text("""
        SELECT 1 FROM local_workflow_definition_versions
        WHERE workflow_definition_id=:id AND version=:version
    """), {"id": IDEA_ID, "version": IDEA_VERSION}).scalar_one_or_none()
    if occupied is not None:
        raise RuntimeError("forward Idea precondition identity is occupied")


def _assert_seed(connection: sa.Connection) -> None:
    row = connection.execute(sa.text("""
        SELECT v.contract_checksum, v.output_schema_id, c.capsule_id,
               c.capsule_version, c.definition_checksum, r.content_precondition
        FROM local_workflow_definition_versions v
        JOIN local_workflow_capsule_versions c
          ON c.workflow_definition_id=v.workflow_definition_id
         AND c.workflow_version=v.version
        JOIN workflow_artifact_requirements r
          ON r.workflow_definition_id=v.workflow_definition_id
         AND r.workflow_version=v.version
        WHERE v.workflow_definition_id=:id AND v.version=:version
          AND r.requirement_key='paper_library'
    """), {"id": IDEA_ID, "version": IDEA_VERSION}).mappings().one_or_none()
    expected = {
        "contract_checksum": IDEA_CONTRACT,
        "output_schema_id": IDEA_TYPE,
        "capsule_id": CAPSULE_ID,
        "capsule_version": CAPSULE_VERSION,
        "definition_checksum": CAPSULE_CHECKSUM,
        "content_precondition": _precondition(),
    }
    if row is None or dict(row) != expected:
        raise RuntimeError("forward Idea precondition seed conflict")


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
