"""Publish immutable Real Experiment Capsule 0.7 validator bugfix.

Revision ID: 20260815_0023
Revises: 20260814_0022
Create Date: 2026-08-15
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260815_0023"
down_revision: str | None = "20260814_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WORKFLOW_ID = "reproduction-experiment-local-experimental"
WORKFLOW_VERSION = "0.4.0"
CAPSULE_ID = "capsule-a01688245334eb95a7733a746e6357c1"
CAPSULE_VERSION = "0.7.0"
CAPSULE_CHECKSUM = "sha256:a01688245334eb95a7733a746e6357c1876daf09139492477b7186ebaea34fa3"
HISTORICAL_CAPSULE_ID = "capsule-c262ef5522f9967641e28cf1b605bdc1"
HISTORICAL_CAPSULE_CHECKSUM = "sha256:c262ef5522f9967641e28cf1b605bdc1a4f3c44ab7c00ffdfa1e5de6ef7db2c7"


def upgrade() -> None:
    connection = op.get_bind()
    _assert_preconditions(connection)
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    compatibility = {
        "package_schema_version": "workflow-package/v0.1",
        "package_template_id": "reproduction-experiment-scaffold-package-experimental",
        "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
        "artifact_outputs": [{
            "artifact_type": "experiment-record/v2",
            "artifact_schema_version": "experiment-record/v2",
            "media_type": "application/json",
            "relative_path_prefix": "outputs/artifacts/experiment-record",
            "content_addressed_filename": "sha256-<content-sha256>.json",
            "progress_artifact_kind": "experiment-record/v2",
        }],
        "core_capability_maturity": "REVIEWED_CORE",
        "skill_pins": [{
            "skill_id": "research-artifact-provenance-local-builtin",
            "skill_version": "0.1.0",
            "skill_checksum": "sha256:0650f150099823499d1fdcf072abd70275e87cb76e3e9d64dfb12361cc13d7c8",
            "trust": "BUILT_IN_REVIEWED",
        }],
        "execution_boundary": "ONE_APPROVED_LOCAL_NO_EGRESS_ATTEMPT",
    }
    connection.execute(sa.text("""
        INSERT INTO local_workflow_capsule_versions
          (capsule_id, capsule_version, workflow_definition_id, workflow_version,
           definition_checksum, archive_size_bytes, archive_media_type,
           mutable_roots, capability_requirements, compatibility, review_status,
           legacy_package_compatible, created_at, updated_at)
        VALUES (:capsule_id, :capsule_version, :workflow_id, :workflow_version,
                :checksum, 0, 'application/zip', CAST(:mutable_roots AS jsonb),
                CAST(:capabilities AS jsonb), CAST(:compatibility AS jsonb),
                'REVIEWED', false, :now, :now)
    """), {
        "capsule_id": CAPSULE_ID,
        "capsule_version": CAPSULE_VERSION,
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "checksum": CAPSULE_CHECKSUM,
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
        "compatibility": _json(compatibility),
        "now": now,
    })


def downgrade() -> None:
    op.get_bind().execute(sa.text("""
        DELETE FROM local_workflow_capsule_versions
        WHERE capsule_id = :capsule_id AND capsule_version = :capsule_version
    """), {"capsule_id": CAPSULE_ID, "capsule_version": CAPSULE_VERSION})


def _assert_preconditions(connection) -> None:
    definition = connection.execute(sa.text("""
        SELECT output_schema_id
        FROM local_workflow_definition_versions
        WHERE workflow_definition_id = :workflow_id AND version = :workflow_version
    """), {
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
    }).mappings().one_or_none()
    if definition is None or definition["output_schema_id"] != "experiment-record/v2":
        raise RuntimeError("Real Experiment Definition 0.4 authority is missing")
    historical = connection.execute(sa.text("""
        SELECT definition_checksum
        FROM local_workflow_capsule_versions
        WHERE capsule_id = :capsule_id AND capsule_version = '0.6.0'
    """), {"capsule_id": HISTORICAL_CAPSULE_ID}).scalar_one_or_none()
    if historical != HISTORICAL_CAPSULE_CHECKSUM:
        raise RuntimeError("historical Real Experiment Capsule 0.6 identity drifted")
    existing = connection.execute(sa.text("""
        SELECT definition_checksum
        FROM local_workflow_capsule_versions
        WHERE capsule_id = :capsule_id AND capsule_version = :capsule_version
    """), {
        "capsule_id": CAPSULE_ID,
        "capsule_version": CAPSULE_VERSION,
    }).scalar_one_or_none()
    if existing is not None:
        raise RuntimeError("Real Experiment Capsule 0.7 is already published")


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
