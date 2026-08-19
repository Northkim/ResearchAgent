"""Publish Experiment 0.8 / Capsule 0.11 Generic Harness path.

Revision ID: 20260820_0038
Revises: 20260820_0037
Create Date: 2026-08-20
"""

from __future__ import annotations

from collections.abc import Sequence
import json

from alembic import op
import sqlalchemy as sa

revision: str = "20260820_0038"
down_revision: str | None = "20260820_0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WORKFLOW_ID = "reproduction-experiment-local-experimental"
VERSION = "0.8.0"
CONTRACT_CHECKSUM = (
    "sha256:16aeb60bd42a982c3e52ee4210fe7e51b5eaf8a103504e6d0e573c38be6818b8"
)
CAPSULE_ID = "capsule-aaf4d527b1aa60eed6b4bdad47da9826"
CAPSULE_VERSION = "0.11.0"
CAPSULE_CHECKSUM = (
    "sha256:aaf4d527b1aa60eed6b4bdad47da982669865c1be71d95ab80ba2dc5c9232ec1"
)
ARTIFACT_TYPE = "experiment-record/v5"
EVIDENCE_SCHEMA = "reagent.experiment-bounded-scientific-evidence/v0.1"
SKILL_ID = "sklearn-tabular-classification-preparation-local-builtin"
SKILL_VERSION = "0.1.0"
SKILL_CHECKSUM = (
    "sha256:23a0c47e2acffafe6c8f821b049e7a645f4bc4e0d844bfc754bd078c0f4173b9"
)


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _artifact_outputs() -> list[dict[str, str]]:
    return [{
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": ARTIFACT_TYPE,
        "media_type": "application/json",
        "relative_path_prefix": "outputs/artifacts/experiment-record",
        "content_addressed_filename": "sha256-<content-sha256>.json",
        "progress_artifact_kind": ARTIFACT_TYPE,
    }]


def _definition_compatibility() -> dict[str, object]:
    return {
        "package_schema_version": "workflow-package/v0.1",
        "artifact_outputs": _artifact_outputs(),
        "experiment_core": "RESEARCH_DOMAIN_AGNOSTIC",
        "capability_interface": "reagent.experiment-capability/v0.1",
        "bounded_scientific_evidence_schema": EVIDENCE_SCHEMA,
        "evidence_authority": "LOCAL_FINAL_ARTIFACT",
        "presentation_companion_authoritative": False,
        "implementation_path": (
            "EXACT_REVIEWED_FAST_PATH_OR_SYSTEM_GENERIC_HARNESS"
        ),
        "generic_harness_classification": "GENERIC_AGENT_HARNESS",
        "user_skill_authority": False,
        "network_policy": "DISABLED",
        "dependency_installation": False,
        "automatic_retry": False,
        "default_project_setup": True,
    }


def _capsule_compatibility() -> dict[str, object]:
    return {
        "package_schema_version": "workflow-package/v0.1",
        "package_template_id": (
            "reproduction-experiment-scaffold-package-experimental"
        ),
        "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
        "artifact_outputs": _artifact_outputs(),
        "core_capability_maturity": "REVIEWED_CORE",
        "capability_interface": "reagent.experiment-capability/v0.1",
        "capability_resolution": (
            "EXACT_REVIEWED_FAST_PATH_OR_SYSTEM_GENERIC_HARNESS"
        ),
        "bounded_scientific_evidence_schema": EVIDENCE_SCHEMA,
        "evidence_authority": "LOCAL_FINAL_ARTIFACT",
        "presentation_companion_authoritative": False,
        "skill_pins": [{
            "skill_id": SKILL_ID,
            "skill_version": SKILL_VERSION,
            "skill_checksum": SKILL_CHECKSUM,
            "trust": "BUILT_IN_REVIEWED",
            "classification": "REFERENCE_EXPERIMENT_CAPABILITY",
        }],
        "generic_harness_classification": "GENERIC_AGENT_HARNESS",
        "generic_harness_scientific_authority": False,
        "user_skill_authority": False,
        "managed_execution_namespace": (
            ".reagent/experiments/<workflow-instance-id>"
        ),
        "execution_boundary": "UNCHANGED_EXISTING_BOUNDED_RUNNER",
        "dependency_installation": False,
    }


def upgrade() -> None:
    connection = op.get_bind()
    _assert_preconditions(connection)
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    connection.execute(sa.text("""
        INSERT INTO local_workflow_definition_versions
          (workflow_definition_id, version, contract_checksum, input_schema_id,
           output_schema_id, compatibility, review_status, core_capability_maturity,
           published_at, created_at, updated_at)
        VALUES (:id, :version, :checksum, 'selected-research-idea/v1',
                :artifact_type, CAST(:compatibility AS jsonb), 'REVIEWED',
                'REVIEWED_CORE', :now, :now, :now)
    """), {
        "id": WORKFLOW_ID,
        "version": VERSION,
        "checksum": CONTRACT_CHECKSUM,
        "artifact_type": ARTIFACT_TYPE,
        "compatibility": _json(_definition_compatibility()),
        "now": now,
    })
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
        "capsule_id": CAPSULE_ID,
        "capsule_version": CAPSULE_VERSION,
        "id": WORKFLOW_ID,
        "version": VERSION,
        "checksum": CAPSULE_CHECKSUM,
        "mutable_roots": _json([
            "inputs", "outputs", "memory/context.md",
            "memory/input-provenance.json", "memory/research-objective.json",
            "memory/methodology-proposal.json", "memory/methodology.json",
            "memory/capability-selection.json", "memory/generic-checkpoint.json",
            "memory/design-approval.json", "memory/requirements",
            "memory/preparation", "memory/runtime", "memory/execution-plan.json",
            "memory/run-approval.json", "memory/execution", "memory/evaluation",
            "memory/result-review.json", "memory/bounded-scientific-evidence.json",
            "memory/current-artifact.json", "memory/progress",
        ]),
        "capabilities": _json([
            "progress.upload/v0.2", "artifact.materialize/v0.1",
            "artifact.publish/v0.1", "execute.local-foreground/v0.1",
            "network.no-egress/v0.1", "experiment.generic-harness/v0.1",
            "experiment.local-continuation/v0.1",
        ]),
        "compatibility": _json(_capsule_compatibility()),
        "now": now,
    })
    connection.execute(sa.text("""
        INSERT INTO workflow_definition_version_skill_pins
          (workflow_definition_id, workflow_version, pin_order, skill_id,
           skill_version, skill_checksum, purpose, created_at)
        VALUES (:id, :version, 0, :skill_id, :skill_version, :skill_checksum,
                :purpose, :now)
    """), {
        "id": WORKFLOW_ID,
        "version": VERSION,
        "skill_id": SKILL_ID,
        "skill_version": SKILL_VERSION,
        "skill_checksum": SKILL_CHECKSUM,
        "purpose": (
            "Provide an optional exact reviewed Experiment Capability fast path; "
            "the system Generic Harness remains independently available."
        ),
        "now": now,
    })
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
    connection.execute(sa.text("""
        DELETE FROM workflow_artifact_requirements
        WHERE workflow_definition_id=:id AND workflow_version=:version
    """), {"id": WORKFLOW_ID, "version": VERSION})
    connection.execute(sa.text("""
        DELETE FROM workflow_definition_version_skill_pins
        WHERE workflow_definition_id=:id AND workflow_version=:version
    """), {"id": WORKFLOW_ID, "version": VERSION})
    connection.execute(sa.text("""
        DELETE FROM local_workflow_capsule_versions
        WHERE capsule_id=:id AND capsule_version=:version
    """), {"id": CAPSULE_ID, "version": CAPSULE_VERSION})
    connection.execute(sa.text("""
        DELETE FROM local_workflow_definition_versions
        WHERE workflow_definition_id=:id AND version=:version
    """), {"id": WORKFLOW_ID, "version": VERSION})


def _assert_preconditions(connection: sa.Connection) -> None:
    frozen = connection.execute(sa.text("""
        SELECT v.contract_checksum, c.capsule_id, c.definition_checksum
        FROM local_workflow_definition_versions v
        JOIN local_workflow_capsule_versions c
          ON c.workflow_definition_id=v.workflow_definition_id
         AND c.workflow_version=v.version
        WHERE v.workflow_definition_id=:id AND v.version='0.7.0'
          AND c.capsule_version='0.10.0'
    """), {"id": WORKFLOW_ID}).one_or_none()
    if frozen != (
        "sha256:9854cf6b50d7982201a38d55649e18513f2e07d5dc0e6bdba6bd58311b5841e4",
        "capsule-cd7ff18e9857b6d20fbe9ba2ccab7ba6",
        "sha256:cd7ff18e9857b6d20fbe9ba2ccab7ba69a0883b3164627dcd12d07e6eb634ad4",
    ):
        raise RuntimeError(
            "Generic Harness publication requires exact frozen Experiment 0.7/0.10"
        )
    skill = connection.scalar(sa.text("""
        SELECT content_checksum FROM local_skill_versions
        WHERE skill_id=:skill_id AND skill_version=:skill_version
    """), {"skill_id": SKILL_ID, "skill_version": SKILL_VERSION})
    if skill != SKILL_CHECKSUM:
        raise RuntimeError(
            "Generic Harness publication requires the exact reviewed fast-path Skill"
        )
    occupied = connection.scalar(sa.text("""
        SELECT count(*) FROM local_workflow_definition_versions
        WHERE workflow_definition_id=:id AND version=:version
    """), {"id": WORKFLOW_ID, "version": VERSION})
    capsule_occupied = connection.scalar(sa.text("""
        SELECT count(*) FROM local_workflow_capsule_versions
        WHERE capsule_id=:capsule_id AND capsule_version=:version
    """), {"capsule_id": CAPSULE_ID, "version": CAPSULE_VERSION})
    if occupied or capsule_occupied:
        raise RuntimeError("Generic Harness immutable identity is already occupied")


def _assert_seed(connection: sa.Connection) -> None:
    row = connection.execute(sa.text("""
        SELECT v.contract_checksum, v.input_schema_id, v.output_schema_id,
               v.compatibility->>'default_project_setup',
               v.compatibility->>'user_skill_authority',
               c.capsule_id, c.capsule_version, c.definition_checksum,
               c.compatibility->>'managed_execution_namespace',
               c.compatibility->>'generic_harness_scientific_authority',
               (SELECT count(*) FROM workflow_artifact_requirements a
                WHERE a.workflow_definition_id=v.workflow_definition_id
                  AND a.workflow_version=v.version),
               (SELECT count(*) FROM workflow_definition_version_skill_pins s
                WHERE s.workflow_definition_id=v.workflow_definition_id
                  AND s.workflow_version=v.version)
        FROM local_workflow_definition_versions v
        JOIN local_workflow_capsule_versions c
          ON c.workflow_definition_id=v.workflow_definition_id
         AND c.workflow_version=v.version
        WHERE v.workflow_definition_id=:id AND v.version=:version
    """), {"id": WORKFLOW_ID, "version": VERSION}).one_or_none()
    expected = (
        CONTRACT_CHECKSUM,
        "selected-research-idea/v1",
        ARTIFACT_TYPE,
        "true",
        "false",
        CAPSULE_ID,
        CAPSULE_VERSION,
        CAPSULE_CHECKSUM,
        ".reagent/experiments/<workflow-instance-id>",
        "false",
        1,
        1,
    )
    if row != expected:
        raise RuntimeError("Generic Harness immutable publication conflict")
