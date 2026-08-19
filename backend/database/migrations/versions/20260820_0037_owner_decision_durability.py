"""Publish durable Literature and Idea Owner decisions.

Revision ID: 20260820_0037
Revises: 20260820_0036
Create Date: 2026-08-20
"""

from __future__ import annotations

from collections.abc import Sequence
import json

from alembic import op
import sqlalchemy as sa

revision: str = "20260820_0037"
down_revision: str | None = "20260820_0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LITERATURE_ID = "literature-search-local-experimental"
LITERATURE_VERSION = "0.5.0"
LITERATURE_CONTRACT = "sha256:eaae7145ec0222d4d11aaf48b71c0bc281a5ea50b8f3b9aa3b61c959cbb51a84"
LITERATURE_CAPSULE_ID = "capsule-5600c6c42c85d3a2ab8beb8e112216df"
LITERATURE_CAPSULE_VERSION = "0.7.0"
LITERATURE_CAPSULE_CHECKSUM = "sha256:5600c6c42c85d3a2ab8beb8e112216df82abd942caa0473aae88f879ce0be8fb"

IDEA_ID = "idea-discovery-local-experimental"
IDEA_VERSION = "0.4.0"
IDEA_CONTRACT = "sha256:af025db540ec17c3f3134a08b96611714c26c93232c97d4aa81eddeade7c725e"
IDEA_CAPSULE_ID = "capsule-db831c40287135691c7c1c41a2a16934"
IDEA_CAPSULE_VERSION = "0.5.0"
IDEA_CAPSULE_CHECKSUM = "sha256:db831c40287135691c7c1c41a2a16934f9193464d1eaff0da3b4a2f82ee50b82"

PAPER_LIBRARY = "selected-paper-library/v1"
SELECTED_IDEA = "selected-research-idea/v1"
QUALIFICATION_SCHEMA = "reagent.artifact-qualification.selected-paper-library/v0.1"
PRECONDITION_SCHEMA = "reagent.artifact-precondition.selected-paper-library-nonempty/v0.1"


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _precondition() -> dict[str, object]:
    return {
        "schema": PRECONDITION_SCHEMA,
        "qualification_schema": QUALIFICATION_SCHEMA,
        "minimum_selected_count": 1,
    }


def _literature_output() -> dict[str, str]:
    return {
        "artifact_type": PAPER_LIBRARY,
        "artifact_schema_version": PAPER_LIBRARY,
        "media_type": "application/json",
        "relative_path_prefix": "outputs/artifacts/selected-paper-library",
        "content_addressed_filename": "sha256-<content-sha256>.json",
        "progress_artifact_kind": PAPER_LIBRARY,
    }


def _idea_output() -> dict[str, str]:
    return {
        "artifact_type": SELECTED_IDEA,
        "artifact_schema_version": SELECTED_IDEA,
        "media_type": "application/json",
        "relative_path_prefix": "outputs/artifacts/selected-research-idea",
        "content_addressed_filename": "sha256-<content-sha256>.json",
        "progress_artifact_kind": SELECTED_IDEA,
    }


def _idea_requirement() -> dict[str, object]:
    return {
        "requirement_key": "paper_library",
        "artifact_type": PAPER_LIBRARY,
        "artifact_schema_version": PAPER_LIBRARY,
        "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
        "materialization_mode": "VERIFIED_COPY",
        "target_relative_path": "inputs/selected-paper-library.json",
        "content_precondition": _precondition(),
    }


def upgrade() -> None:
    connection = op.get_bind()
    _assert_preconditions(connection)
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))

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
            },
        },
        {
            "id": IDEA_ID,
            "version": IDEA_VERSION,
            "contract": IDEA_CONTRACT,
            "input": PAPER_LIBRARY,
            "output": SELECTED_IDEA,
            "compatibility": {
                "package_schema_version": "workflow-package/v0.1",
                "artifact_requirement_key": "paper_library",
                "artifact_outputs": [_idea_output()],
                "explicit_selection_policy": "EXACTLY_ONE_USER_CONFIRMED",
                "novelty_claim_policy": "GLOBAL_NOVELTY_NOT_PROVEN",
                "content_precondition": _precondition(),
                "decision_durability": (
                    "CANDIDATE_SET_CHECKSUM_AND_EXACT_SELECTED_IDEA"
                ),
            },
        },
    )
    for value in versions:
        connection.execute(sa.text("""
            INSERT INTO local_workflow_definition_versions
              (workflow_definition_id, version, contract_checksum, input_schema_id,
               output_schema_id, compatibility, review_status,
               core_capability_maturity, published_at, created_at, updated_at)
            VALUES (:id, :version, :contract, :input, :output,
                    CAST(:compatibility AS jsonb), 'REVIEWED', 'REVIEWED_CORE',
                    :now, :now, :now)
        """), {**value, "compatibility": _json(value["compatibility"]), "now": now})

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
                "artifact_outputs": [_literature_output()],
                "decision_durability": (
                    "CANDIDATE_SET_CHECKSUM_AND_EXACT_OWNER_DISPOSITIONS"
                ),
            },
        },
        {
            "capsule_id": IDEA_CAPSULE_ID,
            "capsule_version": IDEA_CAPSULE_VERSION,
            "id": IDEA_ID,
            "version": IDEA_VERSION,
            "checksum": IDEA_CAPSULE_CHECKSUM,
            "mutable": [
                "memory/context.md", "memory/owner-decisions.json",
                "memory/progress", "outputs", "inputs",
            ],
            "capabilities": [
                "progress.upload/v0.2", "artifact.materialize/v0.1",
                "artifact.publish/v0.1",
            ],
            "compatibility": {
                "package_schema_version": "workflow-package/v0.1",
                "package_template_id": "idea-discovery-package-experimental",
                "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
                "artifact_requirements": [_idea_requirement()],
                "artifact_outputs": [_idea_output()],
                "core_capability_maturity": "REVIEWED_CORE",
                "decision_durability": (
                    "CANDIDATE_SET_CHECKSUM_AND_EXACT_SELECTED_IDEA"
                ),
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

    connection.execute(sa.text("""
        INSERT INTO workflow_artifact_requirements
          (workflow_definition_id, workflow_version, requirement_key,
           artifact_type, compatibility_mode, schema_constraint,
           cardinality_min, cardinality_max, required, materialization_mode,
           target_relative_path, content_precondition, created_at, updated_at)
        VALUES (:id, :version, 'paper_library', :artifact, 'EXACT', :artifact,
                1, 1, true, 'VERIFIED_COPY',
                'inputs/selected-paper-library.json', CAST(:precondition AS jsonb),
                :now, :now)
    """), {
        "id": IDEA_ID,
        "version": IDEA_VERSION,
        "artifact": PAPER_LIBRARY,
        "precondition": _json(_precondition()),
        "now": now,
    })
    _assert_seed(connection)


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("""
        DELETE FROM workflow_artifact_requirements
        WHERE workflow_definition_id=:id AND workflow_version=:version
    """), {"id": IDEA_ID, "version": IDEA_VERSION})
    for capsule_id, capsule_version in (
        (LITERATURE_CAPSULE_ID, LITERATURE_CAPSULE_VERSION),
        (IDEA_CAPSULE_ID, IDEA_CAPSULE_VERSION),
    ):
        connection.execute(sa.text("""
            DELETE FROM local_workflow_capsule_versions
            WHERE capsule_id=:capsule_id AND capsule_version=:capsule_version
        """), {"capsule_id": capsule_id, "capsule_version": capsule_version})
    for workflow_id, version in (
        (LITERATURE_ID, LITERATURE_VERSION),
        (IDEA_ID, IDEA_VERSION),
    ):
        connection.execute(sa.text("""
            DELETE FROM local_workflow_definition_versions
            WHERE workflow_definition_id=:id AND version=:version
        """), {"id": workflow_id, "version": version})


def _assert_preconditions(connection: sa.Connection) -> None:
    expected = {
        (LITERATURE_ID, "0.4.0"): (
            "sha256:864102b119364626b82a1644b3cfd7699746633950097ad0d5cd7bb5facf5c2c"
        ),
        (IDEA_ID, "0.3.0"): (
            "sha256:5385cfa76e7323664f1e321ad781f583edcd6f0fcbf32f36ffdbbefc4ef5e682"
        ),
    }
    for (workflow_id, version), checksum in expected.items():
        current = connection.execute(sa.text("""
            SELECT contract_checksum FROM local_workflow_definition_versions
            WHERE workflow_definition_id=:id AND version=:version
        """), {"id": workflow_id, "version": version}).scalar_one_or_none()
        if current != checksum:
            raise RuntimeError("durable Owner decisions require immutable predecessor")
    occupied = connection.execute(sa.text("""
        SELECT workflow_definition_id, version
        FROM local_workflow_definition_versions
        WHERE (workflow_definition_id=:literature AND version=:literature_version)
           OR (workflow_definition_id=:idea AND version=:idea_version)
    """), {
        "literature": LITERATURE_ID,
        "literature_version": LITERATURE_VERSION,
        "idea": IDEA_ID,
        "idea_version": IDEA_VERSION,
    }).first()
    if occupied is not None:
        raise RuntimeError("durable Owner decision publication identity is occupied")


def _assert_seed(connection: sa.Connection) -> None:
    count = connection.execute(sa.text("""
        SELECT count(*) FROM local_workflow_capsule_versions
        WHERE (capsule_id=:literature AND capsule_version=:literature_version)
           OR (capsule_id=:idea AND capsule_version=:idea_version)
    """), {
        "literature": LITERATURE_CAPSULE_ID,
        "literature_version": LITERATURE_CAPSULE_VERSION,
        "idea": IDEA_CAPSULE_ID,
        "idea_version": IDEA_CAPSULE_VERSION,
    }).scalar_one()
    if count != 2:
        raise RuntimeError("durable Owner decision publication failed")
