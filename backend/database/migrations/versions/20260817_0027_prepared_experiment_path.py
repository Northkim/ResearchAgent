"""Publish immutable Experiment 0.5 and prepared Capsule 0.8.

Revision ID: 20260817_0027
Revises: 20260815_0026
Create Date: 2026-08-17
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260817_0027"
down_revision: str | None = "20260815_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WORKFLOW_ID = "reproduction-experiment-local-experimental"
VERSION = "0.5.0"
CONTRACT_CHECKSUM = "sha256:23b6e3cae5746c8589927d2380595df61d01c6fb3f487cf47e09753f3ef8b600"
CAPSULE_ID = "capsule-5e02c832357355b6036b7e21cfbae306"
CAPSULE_VERSION = "0.8.0"
CAPSULE_CHECKSUM = "sha256:5e02c832357355b6036b7e21cfbae3061306b16268d04ee75c764c56c759bd98"
SKILL_ID = "research-artifact-provenance-local-builtin"
SKILL_VERSION = "0.1.0"
SKILL_CHECKSUM = "sha256:0650f150099823499d1fdcf072abd70275e87cb76e3e9d64dfb12361cc13d7c8"


def upgrade() -> None:
    connection = op.get_bind()
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    _assert_preconditions(connection)
    outputs = [{
        "artifact_type": "experiment-record/v3",
        "artifact_schema_version": "experiment-record/v3",
        "media_type": "application/json",
        "relative_path_prefix": "outputs/artifacts/experiment-record",
        "content_addressed_filename": "sha256-<content-sha256>.json",
        "progress_artifact_kind": "experiment-record/v3",
    }]
    compatibility = {
        "package_schema_version": "workflow-package/v0.1",
        "artifact_outputs": outputs,
        "resource_mode": "PREPARE_WITH_REAGENT",
        "builder_family": "SKLEARN_TABULAR_CLASSIFICATION_V1",
        "network_policy": "DISABLED", "dependency_installation": False,
        "automatic_retry": False, "default_project_setup": False,
    }
    connection.execute(sa.text("""
        INSERT INTO local_workflow_definition_versions
          (workflow_definition_id, version, contract_checksum, input_schema_id,
           output_schema_id, compatibility, review_status, core_capability_maturity,
           published_at, created_at, updated_at)
        VALUES (:id, :version, :checksum, 'selected-research-idea/v1',
                'experiment-record/v3', CAST(:compatibility AS jsonb),
                'REVIEWED', 'REVIEWED_CORE', :now, :now, :now)
    """), {"id": WORKFLOW_ID, "version": VERSION, "checksum": CONTRACT_CHECKSUM,
             "compatibility": _json(compatibility), "now": now})
    capsule_compatibility = {
        "package_schema_version": "workflow-package/v0.1",
        "package_template_id": "reproduction-experiment-scaffold-package-experimental",
        "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
        "artifact_outputs": outputs, "core_capability_maturity": "REVIEWED_CORE",
        "builder_family": "SKLEARN_TABULAR_CLASSIFICATION_V1",
        "execution_boundary": "ONE_APPROVED_LOCAL_NO_EGRESS_ATTEMPT",
        "skill_pins": [{"skill_id": SKILL_ID, "skill_version": SKILL_VERSION,
                        "skill_checksum": SKILL_CHECKSUM, "trust": "BUILT_IN_REVIEWED"}],
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
            "inputs", "outputs", "memory/context.md", "memory/progress",
            "memory/input-provenance.json", "memory/methodology-proposal.json",
            "memory/methodology.json", "memory/design-approval.json",
            "memory/implementation-specification.json", "memory/preparation",
            "memory/prepared-package-receipt.json",
            "memory/validated-experiment-package.json", "memory/execution-plan.json",
            "memory/run-approval.json", "memory/run-approval-consumption.json",
            "memory/execution", "memory/execution-evidence.json",
            "memory/evaluation-evidence.json", "memory/current-artifact.json",
        ]),
        "capabilities": _json([
            "progress.upload/v0.2", "artifact.materialize/v0.1",
            "artifact.publish/v0.1", "execute.local-foreground/v0.1",
            "network.no-egress/v0.1", "experiment.prepare.reviewed/v0.1",
        ]),
        "compatibility": _json(capsule_compatibility), "now": now,
    })
    connection.execute(sa.text("""
        INSERT INTO workflow_definition_version_skill_pins
          (workflow_definition_id, workflow_version, pin_order, skill_id,
           skill_version, skill_checksum, purpose, created_at)
        VALUES (:id, :version, 0, :skill_id, :skill_version, :skill_checksum,
                'Preserve exact selected Idea and prepared-package provenance.', :now)
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
    _assert_seed(connection)


def downgrade() -> None:
    connection = op.get_bind()
    for table in ("workflow_artifact_requirements", "workflow_definition_version_skill_pins"):
        connection.execute(sa.text(f"DELETE FROM {table} WHERE workflow_definition_id = :id AND workflow_version = :version"), {"id": WORKFLOW_ID, "version": VERSION})
    connection.execute(sa.text("DELETE FROM local_workflow_capsule_versions WHERE capsule_id = :id AND capsule_version = :version"), {"id": CAPSULE_ID, "version": CAPSULE_VERSION})
    connection.execute(sa.text("DELETE FROM local_workflow_definition_versions WHERE workflow_definition_id = :id AND version = :version"), {"id": WORKFLOW_ID, "version": VERSION})


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _assert_preconditions(connection: sa.Connection) -> None:
    row = connection.execute(sa.text("""
        SELECT definition_checksum FROM local_workflow_capsule_versions
        WHERE workflow_definition_id = :id AND workflow_version = '0.4.0'
          AND capsule_version = '0.7.0'
    """), {"id": WORKFLOW_ID}).scalar_one_or_none()
    if row != "sha256:a01688245334eb95a7733a746e6357c1876daf09139492477b7186ebaea34fa3":
        raise RuntimeError("Prepared Experiment requires immutable Experiment 0.4/0.7")


def _assert_seed(connection: sa.Connection) -> None:
    row = connection.execute(sa.text("""
        SELECT v.contract_checksum, v.output_schema_id, v.core_capability_maturity,
               c.capsule_id, c.capsule_version, c.definition_checksum,
               (SELECT count(*) FROM workflow_artifact_requirements a WHERE a.workflow_definition_id=v.workflow_definition_id AND a.workflow_version=v.version) AS artifact_count,
               (SELECT count(*) FROM workflow_resource_requirements r WHERE r.workflow_definition_id=v.workflow_definition_id AND r.workflow_version=v.version) AS resource_count
        FROM local_workflow_definition_versions v
        JOIN local_workflow_capsule_versions c ON c.workflow_definition_id=v.workflow_definition_id AND c.workflow_version=v.version
        WHERE v.workflow_definition_id=:id AND v.version=:version
    """), {"id": WORKFLOW_ID, "version": VERSION}).mappings().one_or_none()
    expected = {"contract_checksum": CONTRACT_CHECKSUM, "output_schema_id": "experiment-record/v3", "core_capability_maturity": "REVIEWED_CORE", "capsule_id": CAPSULE_ID, "capsule_version": CAPSULE_VERSION, "definition_checksum": CAPSULE_CHECKSUM, "artifact_count": 1, "resource_count": 0}
    if row is None or dict(row) != expected:
        raise RuntimeError("Prepared Experiment immutable seed conflict")
