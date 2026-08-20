"""Publish Literature 0.6 / 0.8 and Literature Consolidation 0.1.

Revision ID: 20260820_0039
Revises: 20260820_0038
Create Date: 2026-08-20
"""

from __future__ import annotations

from collections.abc import Sequence
import json

from alembic import op
import sqlalchemy as sa

revision: str = "20260820_0039"
down_revision: str | None = "20260820_0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LITERATURE_ID = "literature-search-local-experimental"
LITERATURE_VERSION = "0.6.0"
LITERATURE_CONTRACT = (
    "sha256:d1f2cee4cd570826276977854e2ab178e925e0f10b3331f9fc5fac1bd9038afc"
)
LITERATURE_CAPSULE_ID = "capsule-5d6056c7c5e6a9d8df6bbdab161c2fb0"
LITERATURE_CAPSULE_VERSION = "0.8.0"
LITERATURE_CAPSULE_CHECKSUM = (
    "sha256:5d6056c7c5e6a9d8df6bbdab161c2fb055bfcf9dcd76ff8cbefcefcb06b71325"
)

CONSOLIDATION_ID = "literature-consolidation-local-experimental"
CONSOLIDATION_VERSION = "0.1.0"
CONSOLIDATION_CONTRACT = (
    "sha256:e5a9c0b39b0334142df047ea88fffcdff80f7fc0cd82667413db6ba6c58898f1"
)
CONSOLIDATION_CAPSULE_ID = "capsule-8b7d8665c2ede6b050995c4e196c9a2f"
CONSOLIDATION_CAPSULE_VERSION = "0.1.0"
CONSOLIDATION_CAPSULE_CHECKSUM = (
    "sha256:8b7d8665c2ede6b050995c4e196c9a2fb29c0d2b83807a58008454dcfb514a9e"
)

PAPER_LIBRARY = "selected-paper-library/v1"


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _output() -> dict[str, str]:
    return {
        "artifact_type": PAPER_LIBRARY,
        "artifact_schema_version": PAPER_LIBRARY,
        "media_type": "application/json",
        "relative_path_prefix": "outputs/artifacts/selected-paper-library",
        "content_addressed_filename": "sha256-<content-sha256>.json",
        "progress_artifact_kind": PAPER_LIBRARY,
    }


def _requirement(key: str, target: str) -> dict[str, object]:
    return {
        "requirement_key": key,
        "artifact_type": PAPER_LIBRARY,
        "artifact_schema": PAPER_LIBRARY,
        "cardinality": "ONE",
        "required": True,
        "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
        "materialization_mode": "VERIFIED_COPY",
        "target_relative_path": target,
    }


CONSOLIDATION_REQUIREMENTS = (
    _requirement("base_library", "inputs/base-paper-library.json"),
    _requirement("additional_library", "inputs/additional-paper-library.json"),
)


def upgrade() -> None:
    connection = op.get_bind()
    _assert_preconditions(connection)
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))

    connection.execute(sa.text("""
        INSERT INTO local_workflow_definitions
          (workflow_definition_id, display_name, description, lifecycle,
           allows_multiple_instances, created_at, updated_at)
        VALUES (:id, 'Literature Consolidation', :description, 'AVAILABLE',
                true, :now, :now)
    """), {
        "id": CONSOLIDATION_ID,
        "description": (
            "Explicitly combine two exact paper-library Artifacts into one "
            "Owner-reviewed downstream library."
        ),
        "now": now,
    })

    versions = (
        {
            "id": LITERATURE_ID,
            "version": LITERATURE_VERSION,
            "contract": LITERATURE_CONTRACT,
            "input": "research-request/v0.2",
            "output": "literature-search-report/v0.2",
            "compatibility": {
                "package_schema_version": "workflow-package/v0.1",
                "production_artifact_type": PAPER_LIBRARY,
                "decision_durability": (
                    "CANDIDATE_SET_CHECKSUM_AND_EXACT_OWNER_DISPOSITIONS"
                ),
                "query_strategy": "DIRECT_SUPPORTING_CONTEXTUAL_BACKGROUND",
                "user_skill_scientific_authority": False,
            },
        },
        {
            "id": CONSOLIDATION_ID,
            "version": CONSOLIDATION_VERSION,
            "contract": CONSOLIDATION_CONTRACT,
            "input": "artifact-bindings/v0.1",
            "output": PAPER_LIBRARY,
            "compatibility": {
                "package_schema_version": "workflow-package/v0.1",
                "artifact_requirements": list(CONSOLIDATION_REQUIREMENTS),
                "artifact_outputs": [_output()],
                "composition_policy": "EXPLICIT_TWO_SOURCE_RECURSIVE",
                "implicit_latest": False,
                "default_project_setup": True,
            },
        },
    )
    for value in versions:
        connection.execute(sa.text("""
            INSERT INTO local_workflow_definition_versions
              (workflow_definition_id, version, contract_checksum,
               input_schema_id, output_schema_id, compatibility, review_status,
               core_capability_maturity, published_at, created_at, updated_at)
            VALUES (:id, :version, :contract, :input, :output,
                    CAST(:compatibility AS jsonb), 'REVIEWED', 'REVIEWED_CORE',
                    :now, :now, :now)
        """), {
            **value,
            "compatibility": _json(value["compatibility"]),
            "now": now,
        })

    capsules = (
        {
            "capsule_id": LITERATURE_CAPSULE_ID,
            "capsule_version": LITERATURE_CAPSULE_VERSION,
            "id": LITERATURE_ID,
            "version": LITERATURE_VERSION,
            "checksum": LITERATURE_CAPSULE_CHECKSUM,
            "mutable": [
                "memory/context.md", "memory/owner-decisions.json",
                "memory/progress", "memory/round-control.json", "memory/search",
                "outputs",
            ],
            "capabilities": [
                "paper.search/v0.1", "progress.read/v0.1", "progress.upload/v0.2",
            ],
            "compatibility": {
                "package_schema_version": "workflow-package/v0.1",
                "package_template_id": "literature-search-package-experimental",
                "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
                "artifact_outputs": [_output()],
                "decision_durability": (
                    "CANDIDATE_SET_CHECKSUM_AND_EXACT_OWNER_DISPOSITIONS"
                ),
                "query_strategy": "DIRECT_SUPPORTING_CONTEXTUAL_BACKGROUND",
                "user_skill_scientific_authority": False,
            },
        },
        {
            "capsule_id": CONSOLIDATION_CAPSULE_ID,
            "capsule_version": CONSOLIDATION_CAPSULE_VERSION,
            "id": CONSOLIDATION_ID,
            "version": CONSOLIDATION_VERSION,
            "checksum": CONSOLIDATION_CAPSULE_CHECKSUM,
            "mutable": [
                "memory/context.md", "memory/input-provenance.json",
                "memory/owner-decisions.json", "memory/current-artifact.json",
                "memory/progress", "outputs", "inputs",
            ],
            "capabilities": [
                "artifact.materialize/v0.1", "artifact.publish/v0.1",
                "progress.upload/v0.2",
            ],
            "compatibility": {
                "package_schema_version": "workflow-package/v0.1",
                "package_template_id": "literature-consolidation-package",
                "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
                "artifact_requirements": list(CONSOLIDATION_REQUIREMENTS),
                "artifact_outputs": [_output()],
                "core_capability_maturity": "REVIEWED_CORE",
            },
        },
    )
    for value in capsules:
        connection.execute(sa.text("""
            INSERT INTO local_workflow_capsule_versions
              (capsule_id, capsule_version, workflow_definition_id,
               workflow_version, definition_checksum, archive_size_bytes,
               archive_media_type, mutable_roots, capability_requirements,
               compatibility, review_status, legacy_package_compatible,
               created_at, updated_at)
            VALUES (:capsule_id, :capsule_version, :id, :version, :checksum, 0,
                    'application/zip', CAST(:mutable AS jsonb),
                    CAST(:capabilities AS jsonb), CAST(:compatibility AS jsonb),
                    'REVIEWED', false, :now, :now)
        """), {
            **value,
            "mutable": _json(value["mutable"]),
            "capabilities": _json(value["capabilities"]),
            "compatibility": _json(value["compatibility"]),
            "now": now,
        })

    for requirement in CONSOLIDATION_REQUIREMENTS:
        connection.execute(sa.text("""
            INSERT INTO workflow_artifact_requirements
              (workflow_definition_id, workflow_version, requirement_key,
               artifact_type, compatibility_mode, schema_constraint,
               cardinality_min, cardinality_max, required,
               materialization_mode, target_relative_path, created_at, updated_at)
            VALUES (:id, :version, :key, :artifact, 'EXACT', :artifact,
                    1, 1, true, 'VERIFIED_COPY', :target, :now, :now)
        """), {
            "id": CONSOLIDATION_ID,
            "version": CONSOLIDATION_VERSION,
            "key": requirement["requirement_key"],
            "artifact": PAPER_LIBRARY,
            "target": requirement["target_relative_path"],
            "now": now,
        })
    _assert_seed(connection)


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("""
        DELETE FROM workflow_artifact_requirements
        WHERE workflow_definition_id=:id AND workflow_version=:version
    """), {"id": CONSOLIDATION_ID, "version": CONSOLIDATION_VERSION})
    for capsule_id, capsule_version in (
        (CONSOLIDATION_CAPSULE_ID, CONSOLIDATION_CAPSULE_VERSION),
        (LITERATURE_CAPSULE_ID, LITERATURE_CAPSULE_VERSION),
    ):
        connection.execute(sa.text("""
            DELETE FROM local_workflow_capsule_versions
            WHERE capsule_id=:capsule_id AND capsule_version=:capsule_version
        """), {
            "capsule_id": capsule_id,
            "capsule_version": capsule_version,
        })
    for workflow_id, version in (
        (CONSOLIDATION_ID, CONSOLIDATION_VERSION),
        (LITERATURE_ID, LITERATURE_VERSION),
    ):
        connection.execute(sa.text("""
            DELETE FROM local_workflow_definition_versions
            WHERE workflow_definition_id=:id AND version=:version
        """), {"id": workflow_id, "version": version})
    connection.execute(sa.text("""
        DELETE FROM local_workflow_definitions
        WHERE workflow_definition_id=:id
    """), {"id": CONSOLIDATION_ID})


def _assert_preconditions(connection: sa.Connection) -> None:
    predecessor = connection.execute(sa.text("""
        SELECT v.contract_checksum, c.capsule_id, c.definition_checksum
        FROM local_workflow_definition_versions v
        JOIN local_workflow_capsule_versions c
          ON c.workflow_definition_id=v.workflow_definition_id
         AND c.workflow_version=v.version
        WHERE v.workflow_definition_id=:id AND v.version='0.5.0'
          AND c.capsule_version='0.7.0'
    """), {"id": LITERATURE_ID}).one_or_none()
    if predecessor != (
        "sha256:eaae7145ec0222d4d11aaf48b71c0bc281a5ea50b8f3b9aa3b61c959cbb51a84",
        "capsule-5600c6c42c85d3a2ab8beb8e112216df",
        "sha256:5600c6c42c85d3a2ab8beb8e112216df82abd942caa0473aae88f879ce0be8fb",
    ):
        raise RuntimeError("R4 publication requires exact frozen Literature 0.5/0.7")
    occupied = connection.scalar(sa.text("""
        SELECT count(*) FROM local_workflow_definition_versions
        WHERE (workflow_definition_id=:literature AND version=:literature_version)
           OR (workflow_definition_id=:consolidation AND version=:consolidation_version)
    """), {
        "literature": LITERATURE_ID,
        "literature_version": LITERATURE_VERSION,
        "consolidation": CONSOLIDATION_ID,
        "consolidation_version": CONSOLIDATION_VERSION,
    })
    family = connection.scalar(sa.text("""
        SELECT count(*) FROM local_workflow_definitions
        WHERE workflow_definition_id=:id
    """), {"id": CONSOLIDATION_ID})
    if occupied or family:
        raise RuntimeError("R4 immutable publication identity is already occupied")


def _assert_seed(connection: sa.Connection) -> None:
    rows = connection.execute(sa.text("""
        SELECT v.workflow_definition_id, v.version, v.contract_checksum,
               c.capsule_id, c.capsule_version, c.definition_checksum,
               (SELECT count(*) FROM workflow_artifact_requirements r
                WHERE r.workflow_definition_id=v.workflow_definition_id
                  AND r.workflow_version=v.version)
        FROM local_workflow_definition_versions v
        JOIN local_workflow_capsule_versions c
          ON c.workflow_definition_id=v.workflow_definition_id
         AND c.workflow_version=v.version
        WHERE (v.workflow_definition_id=:literature
               AND v.version=:literature_version)
           OR (v.workflow_definition_id=:consolidation
               AND v.version=:consolidation_version)
        ORDER BY v.workflow_definition_id
    """), {
        "literature": LITERATURE_ID,
        "literature_version": LITERATURE_VERSION,
        "consolidation": CONSOLIDATION_ID,
        "consolidation_version": CONSOLIDATION_VERSION,
    }).all()
    if rows != [
        (
            CONSOLIDATION_ID, CONSOLIDATION_VERSION, CONSOLIDATION_CONTRACT,
            CONSOLIDATION_CAPSULE_ID, CONSOLIDATION_CAPSULE_VERSION,
            CONSOLIDATION_CAPSULE_CHECKSUM, 2,
        ),
        (
            LITERATURE_ID, LITERATURE_VERSION, LITERATURE_CONTRACT,
            LITERATURE_CAPSULE_ID, LITERATURE_CAPSULE_VERSION,
            LITERATURE_CAPSULE_CHECKSUM, 0,
        ),
    ]:
        raise RuntimeError("R4 immutable publication conflict")
