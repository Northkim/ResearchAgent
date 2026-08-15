"""Publish immutable Real Experiment Definition 0.4 and Capsule 0.6.

Revision ID: 20260814_0022
Revises: 20260813_0021
Create Date: 2026-08-14
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260814_0022"
down_revision: str | None = "20260813_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WORKFLOW_ID = "reproduction-experiment-local-experimental"
VERSION = "0.4.0"
CONTRACT_CHECKSUM = "sha256:809029bd63ac101a49abbcbe253550284c369b1024ca774e61f49fa88fcb8193"
CAPSULE_ID = "capsule-c262ef5522f9967641e28cf1b605bdc1"
CAPSULE_VERSION = "0.6.0"
CAPSULE_CHECKSUM = "sha256:c262ef5522f9967641e28cf1b605bdc1a4f3c44ab7c00ffdfa1e5de6ef7db2c7"
SKILL_ID = "research-artifact-provenance-local-builtin"
SKILL_VERSION = "0.1.0"
SKILL_CHECKSUM = "sha256:0650f150099823499d1fdcf072abd70275e87cb76e3e9d64dfb12361cc13d7c8"


def upgrade() -> None:
    connection = op.get_bind()
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    _assert_preconditions(connection)
    compatibility = {
        "package_schema_version": "workflow-package/v0.1",
        "artifact_outputs": [{
            "artifact_type": "experiment-record/v2",
            "artifact_schema_version": "experiment-record/v2",
            "media_type": "application/json",
            "relative_path_prefix": "outputs/artifacts/experiment-record",
            "content_addressed_filename": "sha256-<content-sha256>.json",
            "progress_artifact_kind": "experiment-record/v2",
        }],
        "resource_mode": "ONE_OWNER_STAGED_GITHUB_SOURCE_REPOSITORY",
        "network_policy": "DISABLED",
        "automatic_retry": False,
        "default_project_setup": False,
    }
    connection.execute(sa.text("""
        INSERT INTO local_workflow_definition_versions
          (workflow_definition_id, version, contract_checksum, input_schema_id,
           output_schema_id, compatibility, review_status, core_capability_maturity,
           published_at, created_at, updated_at)
        VALUES (:id, :version, :checksum, 'selected-research-idea/v1',
                'experiment-record/v2', CAST(:compatibility AS jsonb),
                'REVIEWED', 'REVIEWED_CORE', :now, :now, :now)
    """), {"id": WORKFLOW_ID, "version": VERSION, "checksum": CONTRACT_CHECKSUM,
             "compatibility": _json(compatibility), "now": now})
    capsule_compatibility = {
        "package_schema_version": "workflow-package/v0.1",
        "package_template_id": "reproduction-experiment-scaffold-package-experimental",
        "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
        "artifact_outputs": compatibility["artifact_outputs"],
        "core_capability_maturity": "REVIEWED_CORE",
        "skill_pins": [{
            "skill_id": SKILL_ID, "skill_version": SKILL_VERSION,
            "skill_checksum": SKILL_CHECKSUM, "trust": "BUILT_IN_REVIEWED",
        }],
        "execution_boundary": "ONE_APPROVED_LOCAL_NO_EGRESS_ATTEMPT",
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
            "memory/context.md", "memory/progress", "memory/execution",
            "memory/input-provenance.json", "memory/resource-provenance.json",
            "memory/plan-context.json", "memory/experiment-requirements.json",
            "memory/experiment-plan.json", "memory/experiment-approval.json",
            "memory/approval-consumption.json", "memory/current-artifact.json",
            "outputs", "inputs",
        ]),
        "capabilities": _json([
            "progress.upload/v0.2", "artifact.materialize/v0.1",
            "artifact.publish/v0.1", "resource.index.verify/v0.1",
            "execute.local-foreground/v0.1", "network.no-egress/v0.1",
        ]),
        "compatibility": _json(capsule_compatibility), "now": now,
    })
    connection.execute(sa.text("""
        INSERT INTO workflow_definition_version_skill_pins
          (workflow_definition_id, workflow_version, pin_order, skill_id,
           skill_version, skill_checksum, purpose, created_at)
        VALUES (:id, :version, 0, :skill_id, :skill_version, :skill_checksum,
                'Use exact materialized inputs and preserve Artifact provenance.', :now)
    """), {"id": WORKFLOW_ID, "version": VERSION, "skill_id": SKILL_ID,
             "skill_version": SKILL_VERSION, "skill_checksum": SKILL_CHECKSUM,
             "now": now})
    connection.execute(sa.text("""
        INSERT INTO workflow_artifact_requirements
          (workflow_definition_id, workflow_version, requirement_key,
           artifact_type, compatibility_mode, schema_constraint, cardinality_min,
           cardinality_max, required, materialization_mode, target_relative_path,
           created_at, updated_at)
        VALUES (:id, :version, 'research_idea', 'selected-research-idea/v1',
                'EXACT', 'selected-research-idea/v1', 1, 1, true,
                'VERIFIED_COPY', 'inputs/selected-research-idea.json', :now, :now)
    """), {"id": WORKFLOW_ID, "version": VERSION, "now": now})
    connection.execute(sa.text("""
        INSERT INTO workflow_resource_requirements
          (workflow_definition_id, workflow_version, requirement_key,
           resource_kind, cardinality_min, cardinality_max, required,
           allowed_providers_json, usage_description, created_at, updated_at)
        VALUES (:id, :version, 'source_repository', 'SOURCE_REPOSITORY', 1, 1,
                true, CAST(:providers AS jsonb), :description, :now, :now)
    """), {"id": WORKFLOW_ID, "version": VERSION,
             "providers": _json(["GITHUB"]),
             "description": "One exact owner-staged local Experiment Package; Cloud metadata alone is not execution readiness.",
             "now": now})
    _assert_seed(connection)


def downgrade() -> None:
    connection = op.get_bind()
    for table in (
        "workflow_resource_requirements", "workflow_artifact_requirements",
        "workflow_definition_version_skill_pins",
    ):
        connection.execute(sa.text(
            f"DELETE FROM {table} WHERE workflow_definition_id = :id AND workflow_version = :version"
        ), {"id": WORKFLOW_ID, "version": VERSION})
    connection.execute(sa.text("DELETE FROM local_workflow_capsule_versions WHERE capsule_id = :id AND capsule_version = :capsule_version"), {"id": CAPSULE_ID, "capsule_version": CAPSULE_VERSION})
    connection.execute(sa.text("DELETE FROM local_workflow_definition_versions WHERE workflow_definition_id = :id AND version = :version"), {"id": WORKFLOW_ID, "version": VERSION})


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _assert_preconditions(connection: sa.Connection) -> None:
    historical = connection.execute(sa.text("""
        SELECT definition_checksum FROM local_workflow_capsule_versions
        WHERE workflow_definition_id = :id AND workflow_version = '0.3.0'
          AND capsule_version = '0.5.0'
    """), {"id": WORKFLOW_ID}).scalar_one_or_none()
    if historical != "sha256:396f09bf03486ce53113611e2c9614dd6a86166f44415f9350fd02803ac04b3f":
        raise RuntimeError("Real Experiment requires the accepted immutable 0.3/0.5 Capsule")


def _assert_seed(connection: sa.Connection) -> None:
    row = connection.execute(sa.text("""
        SELECT v.contract_checksum, v.core_capability_maturity,
               c.capsule_id, c.capsule_version, c.definition_checksum,
               (SELECT count(*) FROM workflow_artifact_requirements a
                WHERE a.workflow_definition_id = v.workflow_definition_id AND a.workflow_version = v.version) AS artifact_count,
               (SELECT count(*) FROM workflow_resource_requirements r
                WHERE r.workflow_definition_id = v.workflow_definition_id AND r.workflow_version = v.version) AS resource_count,
               (SELECT count(*) FROM workflow_definition_version_skill_pins s
                WHERE s.workflow_definition_id = v.workflow_definition_id AND s.workflow_version = v.version) AS skill_count
        FROM local_workflow_definition_versions v
        JOIN local_workflow_capsule_versions c
          ON c.workflow_definition_id = v.workflow_definition_id AND c.workflow_version = v.version
        WHERE v.workflow_definition_id = :id AND v.version = :version
    """), {"id": WORKFLOW_ID, "version": VERSION}).mappings().one_or_none()
    expected = {
        "contract_checksum": CONTRACT_CHECKSUM,
        "core_capability_maturity": "REVIEWED_CORE",
        "capsule_id": CAPSULE_ID,
        "capsule_version": CAPSULE_VERSION,
        "definition_checksum": CAPSULE_CHECKSUM,
        "artifact_count": 1,
        "resource_count": 1,
        "skill_count": 1,
    }
    if row is None or dict(row) != expected:
        raise RuntimeError("Real Experiment immutable seed conflict")
