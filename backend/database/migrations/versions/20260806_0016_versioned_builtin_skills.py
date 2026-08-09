"""Add versioned built-in Skills and skill-backed scaffold Capsules.

Revision ID: 20260806_0016
Revises: 20260806_0015
Create Date: 2026-08-09
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260806_0016"
down_revision: str | None = "20260806_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_VERSION = "0.1.0"
VERSION = "0.2.0"
SKILL_VERSION = "0.1.0"

SKILLS = (
    {
        "id": "research-artifact-provenance-local-builtin",
        "name": "Research Artifact Provenance",
        "description": (
            "Preserve exact Artifact identity and checksum provenance while using "
            "materialized Workflow inputs."
        ),
        "checksum": "sha256:0650f150099823499d1fdcf072abd70275e87cb76e3e9d64dfb12361cc13d7c8",
        "source": "reagent-f1d-research-artifact-provenance",
        "purpose": "Use exact materialized inputs and preserve Artifact provenance.",
        "manifest": {
            "schema_version": "local-skill/v0.1",
            "files": [
                {"path": "SKILL.md", "media_type": "text/markdown", "sha256": "sha256:94dd8acb5320676ee459fbf66e81a6e2b0d2f5ad6674a1b93a36ca3e96c39f93", "byte_size": 574},
                {"path": "skill.json", "media_type": "application/json", "sha256": "sha256:d1bcea793c21b5cce5aedcd320d8704aae7f67364126ee3657b9475d9a120b5c", "byte_size": 360},
            ],
        },
    },
    {
        "id": "scaffold-core-safety-local-builtin",
        "name": "Scaffold Core Safety",
        "description": (
            "Keep scaffold outputs visibly provisional and prevent fabricated "
            "scientific evidence or conclusions."
        ),
        "checksum": "sha256:0f9fb8471de4114bb8e54ee0a2c9f4ba0b03264c70ddd410e5955d17fedc8c78",
        "source": "reagent-f1d-scaffold-core-safety",
        "purpose": "Preserve scaffold markers and prohibit fabricated research claims.",
        "manifest": {
            "schema_version": "local-skill/v0.1",
            "files": [
                {"path": "SKILL.md", "media_type": "text/markdown", "sha256": "sha256:e87dc50671ed24e0705756216181e3a71a4b4add5e82eeb7505bc307b45f276d", "byte_size": 684},
                {"path": "skill.json", "media_type": "application/json", "sha256": "sha256:6febaea87afb86dc81e30cd1ae889fa3511e3b78162cdc3dd3da5ce5bcabf050", "byte_size": 361},
            ],
        },
    },
)

WORKFLOWS = (
    {
        "id": "writing-local-experimental",
        "contract": "sha256:8e6c8c2ffdc0b10d9d40bc168704c66993e13092300e85c02814cb30a51257e9",
        "capsule_id": "capsule-84896829db7ee1cb6b24a5e10bf6705b",
        "capsule_checksum": "sha256:84896829db7ee1cb6b24a5e10bf6705beac93fa42857d0dc08d4916e0243ee0c",
    },
    {
        "id": "review-local-experimental",
        "contract": "sha256:632941e0ae8646398c07515ade09e694753a9f4bb44724ef53b07553e6d9681a",
        "capsule_id": "capsule-9c3e4e8f065914393f5dc786b36d07bb",
        "capsule_checksum": "sha256:9c3e4e8f065914393f5dc786b36d07bbbdc962f381ea70f125353429c48089f1",
    },
    {
        "id": "reproduction-experiment-local-experimental",
        "contract": "sha256:2f73685a3b7ff28a1adbe3d04e427a4cbe32f889524b0a987fcc7179a679eb93",
        "capsule_id": "capsule-299a1f6ca3ef91537426ac2ff5d868ad",
        "capsule_checksum": "sha256:299a1f6ca3ef91537426ac2ff5d868ad09469082941fb71bd8d1cc373acd6b1f",
    },
)


def upgrade() -> None:
    op.create_table(
        "local_builtin_skill_definitions",
        sa.Column("skill_id", sa.String(length=128), primary_key=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("lifecycle", sa.String(length=20), nullable=False),
        sa.Column("source_class", sa.String(length=32), nullable=False),
        sa.Column("trust_tier", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("lifecycle IN ('AVAILABLE','RETIRED')", name="local_builtin_skill_definition_lifecycle"),
        sa.CheckConstraint("source_class = 'PLATFORM_BUILT_IN'", name="local_builtin_skill_definition_source_class"),
        sa.CheckConstraint("trust_tier = 'BUILT_IN_REVIEWED'", name="local_builtin_skill_definition_trust"),
    )
    op.create_index(
        "ix_local_builtin_skill_definitions_lifecycle",
        "local_builtin_skill_definitions", ["lifecycle", "skill_id"],
    )
    op.create_table(
        "local_skill_versions",
        sa.Column("skill_id", sa.String(length=128), nullable=False),
        sa.Column("skill_version", sa.String(length=100), nullable=False),
        sa.Column("content_checksum", sa.String(length=71), nullable=False, unique=True),
        sa.Column("manifest_schema_version", sa.String(length=100), nullable=False),
        sa.Column("content_manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("trust_tier", sa.String(length=32), nullable=False),
        sa.Column("review_status", sa.String(length=20), nullable=False),
        sa.Column("content_source_identity", sa.String(length=255), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["skill_id"], ["local_builtin_skill_definitions.skill_id"]),
        sa.PrimaryKeyConstraint("skill_id", "skill_version"),
        sa.CheckConstraint("trust_tier IN ('BUILT_IN_REVIEWED','PRIVATE_DISABLED','IMPORTED_QUARANTINED')", name="local_skill_version_trust"),
        sa.CheckConstraint("review_status IN ('REVIEWED','RETIRED','QUARANTINED')", name="local_skill_version_review_status"),
    )
    op.create_index(
        "ix_local_skill_versions_skill_review", "local_skill_versions",
        ["skill_id", "review_status"],
    )
    op.create_table(
        "workflow_definition_version_skill_pins",
        sa.Column("workflow_definition_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_version", sa.String(length=100), nullable=False),
        sa.Column("pin_order", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.String(length=128), nullable=False),
        sa.Column("skill_version", sa.String(length=100), nullable=False),
        sa.Column("skill_checksum", sa.String(length=71), nullable=False),
        sa.Column("purpose", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workflow_definition_id", "workflow_version"],
            ["local_workflow_definition_versions.workflow_definition_id", "local_workflow_definition_versions.version"],
            name="fk_workflow_skill_pins_workflow_version",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id", "skill_version"],
            ["local_skill_versions.skill_id", "local_skill_versions.skill_version"],
            name="fk_workflow_skill_pins_skill_version",
        ),
        sa.PrimaryKeyConstraint("workflow_definition_id", "workflow_version", "pin_order"),
        sa.UniqueConstraint("workflow_definition_id", "workflow_version", "skill_id", name="uq_workflow_skill_pins_exact_skill"),
        sa.CheckConstraint("pin_order BETWEEN 0 AND 99", name="workflow_skill_pin_order"),
    )
    op.create_index(
        "ix_workflow_skill_pins_workflow",
        "workflow_definition_version_skill_pins",
        ["workflow_definition_id", "workflow_version", "pin_order"],
    )

    connection = op.get_bind()
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    _assert_f1b_preconditions(connection)
    for skill in SKILLS:
        connection.execute(sa.text("""
            INSERT INTO local_builtin_skill_definitions
              (skill_id, display_name, description, lifecycle, source_class,
               trust_tier, created_at, updated_at)
            VALUES (:id, :name, :description, 'AVAILABLE', 'PLATFORM_BUILT_IN',
                    'BUILT_IN_REVIEWED', :now, :now)
        """), {**skill, "now": now})
        connection.execute(sa.text("""
            INSERT INTO local_skill_versions
              (skill_id, skill_version, content_checksum, manifest_schema_version,
               content_manifest, trust_tier, review_status,
               content_source_identity, published_at, created_at, updated_at)
            VALUES (:id, :version, :checksum, 'local-skill/v0.1',
                    CAST(:manifest AS jsonb), 'BUILT_IN_REVIEWED', 'REVIEWED',
                    :source, :now, :now, :now)
        """), {
            **skill, "version": SKILL_VERSION,
            "manifest": _json(skill["manifest"]), "now": now,
        })

    skill_pins = [
        {
            "skill_id": skill["id"], "skill_version": SKILL_VERSION,
            "skill_checksum": skill["checksum"], "trust": "BUILT_IN_REVIEWED",
        }
        for skill in SKILLS
    ]
    for workflow in WORKFLOWS:
        connection.execute(sa.text("""
            INSERT INTO local_workflow_definition_versions
              (workflow_definition_id, version, contract_checksum, input_schema_id,
               output_schema_id, compatibility, review_status,
               core_capability_maturity, published_at, created_at, updated_at)
            SELECT workflow_definition_id, :version, :contract, input_schema_id,
                   output_schema_id,
                   compatibility || jsonb_build_object(
                     'skill_delivery', 'EXACT_CAPSULE_BUNDLED'),
                   'REVIEWED', 'SCAFFOLD_CORE', :now, :now, :now
            FROM local_workflow_definition_versions
            WHERE workflow_definition_id = :id AND version = :old_version
        """), {**workflow, "version": VERSION, "old_version": OLD_VERSION, "now": now})
        connection.execute(sa.text("""
            INSERT INTO local_workflow_capsule_versions
              (capsule_id, capsule_version, workflow_definition_id, workflow_version,
               definition_checksum, archive_size_bytes, archive_media_type,
               mutable_roots, capability_requirements, compatibility, review_status,
               legacy_package_compatible, created_at, updated_at)
            SELECT :capsule_id, :version, workflow_definition_id, :version,
                   :capsule_checksum, 0, archive_media_type, mutable_roots,
                   capability_requirements,
                   compatibility || jsonb_build_object(
                     'skill_pins', CAST(:skill_pins AS jsonb),
                     'skill_delivery', 'EXACT_CAPSULE_BUNDLED'),
                   'REVIEWED', false, :now, :now
            FROM local_workflow_capsule_versions
            WHERE workflow_definition_id = :id AND workflow_version = :old_version
              AND capsule_version = :old_version
        """), {
            **workflow, "version": VERSION, "old_version": OLD_VERSION,
            "skill_pins": _json(skill_pins), "now": now,
        })
        connection.execute(sa.text("""
            INSERT INTO workflow_artifact_requirements
              (workflow_definition_id, workflow_version, requirement_key,
               artifact_type, compatibility_mode, schema_constraint,
               cardinality_min, cardinality_max, required,
               materialization_mode, target_relative_path, created_at, updated_at)
            SELECT workflow_definition_id, :version, requirement_key,
                   artifact_type, compatibility_mode, schema_constraint,
                   cardinality_min, cardinality_max, required,
                   materialization_mode, target_relative_path, :now, :now
            FROM workflow_artifact_requirements
            WHERE workflow_definition_id = :id AND workflow_version = :old_version
        """), {**workflow, "version": VERSION, "old_version": OLD_VERSION, "now": now})
        for order, skill in enumerate(SKILLS):
            connection.execute(sa.text("""
                INSERT INTO workflow_definition_version_skill_pins
                  (workflow_definition_id, workflow_version, pin_order, skill_id,
                   skill_version, skill_checksum, purpose, created_at)
                VALUES (:workflow_id, :workflow_version, :pin_order, :skill_id,
                        :skill_version, :skill_checksum, :purpose, :now)
            """), {
                "workflow_id": workflow["id"], "workflow_version": VERSION,
                "pin_order": order, "skill_id": skill["id"],
                "skill_version": SKILL_VERSION,
                "skill_checksum": skill["checksum"], "purpose": skill["purpose"],
                "now": now,
            })
    _assert_seed_content(connection)


def downgrade() -> None:
    connection = op.get_bind()
    workflow_ids = tuple(item["id"] for item in WORKFLOWS)
    connection.execute(sa.text("""
        DELETE FROM workflow_definition_version_skill_pins
        WHERE workflow_definition_id IN :ids AND workflow_version = :version
    """).bindparams(sa.bindparam("ids", expanding=True)), {"ids": workflow_ids, "version": VERSION})
    connection.execute(sa.text("""
        DELETE FROM workflow_artifact_requirements
        WHERE workflow_definition_id IN :ids AND workflow_version = :version
    """).bindparams(sa.bindparam("ids", expanding=True)), {"ids": workflow_ids, "version": VERSION})
    capsule_ids = tuple(item["capsule_id"] for item in WORKFLOWS)
    connection.execute(sa.text("""
        DELETE FROM local_workflow_capsule_versions
        WHERE capsule_id IN :ids AND capsule_version = :version
    """).bindparams(sa.bindparam("ids", expanding=True)), {"ids": capsule_ids, "version": VERSION})
    connection.execute(sa.text("""
        DELETE FROM local_workflow_definition_versions
        WHERE workflow_definition_id IN :ids AND version = :version
    """).bindparams(sa.bindparam("ids", expanding=True)), {"ids": workflow_ids, "version": VERSION})
    op.drop_table("workflow_definition_version_skill_pins")
    op.drop_table("local_skill_versions")
    op.drop_table("local_builtin_skill_definitions")


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _assert_f1b_preconditions(connection: sa.Connection) -> None:
    workflow_ids = tuple(item["id"] for item in WORKFLOWS)
    versions = connection.scalar(sa.text("""
        SELECT count(*) FROM local_workflow_definition_versions
        WHERE workflow_definition_id IN :ids AND version = :version
    """).bindparams(sa.bindparam("ids", expanding=True)), {
        "ids": workflow_ids, "version": OLD_VERSION,
    })
    capsules = connection.scalar(sa.text("""
        SELECT count(*) FROM local_workflow_capsule_versions
        WHERE workflow_definition_id IN :ids
          AND workflow_version = :version AND capsule_version = :version
    """).bindparams(sa.bindparam("ids", expanding=True)), {
        "ids": workflow_ids, "version": OLD_VERSION,
    })
    if versions != 3 or capsules != 3:
        raise RuntimeError("F1D requires the complete immutable F1B scaffold seed")


def _assert_seed_content(connection: sa.Connection) -> None:
    if connection.scalar(sa.text("SELECT count(*) FROM local_builtin_skill_definitions")) != 2:
        raise RuntimeError("F1D Skill Definition seed conflict")
    if connection.scalar(sa.text("SELECT count(*) FROM local_skill_versions")) != 2:
        raise RuntimeError("F1D Skill Version seed conflict")
    for workflow in WORKFLOWS:
        row = connection.execute(sa.text("""
            SELECT v.contract_checksum, v.core_capability_maturity,
                   c.capsule_id, c.definition_checksum,
                   (SELECT count(*) FROM workflow_definition_version_skill_pins p
                    WHERE p.workflow_definition_id = v.workflow_definition_id
                      AND p.workflow_version = v.version) AS pin_count
            FROM local_workflow_definition_versions v
            JOIN local_workflow_capsule_versions c
              ON c.workflow_definition_id = v.workflow_definition_id
             AND c.workflow_version = v.version
            WHERE v.workflow_definition_id = :id AND v.version = :version
        """), {"id": workflow["id"], "version": VERSION}).mappings().one_or_none()
        if row is None or dict(row) != {
            "contract_checksum": workflow["contract"],
            "core_capability_maturity": "SCAFFOLD_CORE",
            "capsule_id": workflow["capsule_id"],
            "definition_checksum": workflow["capsule_checksum"],
            "pin_count": 2,
        }:
            raise RuntimeError(f"F1D {workflow['id']} seed conflict")
