"""Publish the exact Experiment-v5 downstream Writing/Review/Revision chain.

Revision ID: 20260818_0032
Revises: 20260818_0031
Create Date: 2026-08-18
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260818_0032"
down_revision: str | None = "20260818_0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SKILL_ID = "research-artifact-provenance-local-builtin"
SKILL_VERSION = "0.1.0"
SKILL_CHECKSUM = "sha256:0650f150099823499d1fdcf072abd70275e87cb76e3e9d64dfb12361cc13d7c8"
EXPERIMENT_V5_CAPSULE = "sha256:cd7ff18e9857b6d20fbe9ba2ccab7ba69a0883b3164627dcd12d07e6eb634ad4"


def _requirement(key: str, artifact_type: str, required: bool, target: str) -> dict[str, object]:
    return {
        "requirement_key": key, "artifact_type": artifact_type,
        "artifact_schema": artifact_type, "cardinality": "ONE",
        "required": required, "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
        "materialization_mode": "VERIFIED_COPY", "target_relative_path": target,
    }


PUBLICATIONS = (
    {
        "role": "initial-writing", "workflow_id": "writing-local-experimental",
        "version": "0.5.0", "contract": "sha256:90900094d0d7c1192b2568d0eebad260cee5b84485e366494cc54ddc6f984eac",
        "capsule_id": "capsule-2abb078c2c2112b284f9a7dae8ea2854", "capsule_version": "0.7.0",
        "capsule": "sha256:2abb078c2c2112b284f9a7dae8ea2854a36243a787f9d54c5febf649e0389a77",
        "output": "manuscript-draft/v4", "template": "writing-scaffold-package-experimental",
        "mode": "EVIDENCE_BOUND_INITIAL_DRAFT_V5", "default": True,
        "requirements": (
            _requirement("research_idea", "selected-research-idea/v1", True, "inputs/selected-research-idea.json"),
            _requirement("literature_library", "selected-paper-library/v1", True, "inputs/selected-paper-library.json"),
            _requirement("experiment_record", "experiment-record/v5", False, "inputs/experiment-record.json"),
        ),
        "mutable": ("memory/context.md", "memory/progress", "memory/input-provenance.json", "memory/writing-brief.json", "memory/evidence-map.json", "memory/outline.json", "memory/outline-approval.json", "memory/claims.json", "memory/citations.json", "memory/owner-review.json", "memory/current-artifact.json", "outputs", "inputs"),
    },
    {
        "role": "review", "workflow_id": "review-local-experimental",
        "version": "0.4.0", "contract": "sha256:d7966ee1e23b1e9e7b30b34c5422d0218625ffda12d85044463046643e482d14",
        "capsule_id": "capsule-133692a783abb9a5061ebd315159a90e", "capsule_version": "0.6.0",
        "capsule": "sha256:133692a783abb9a5061ebd315159a90e0c6e1b9b85bb6d5453b67ac6d25093af",
        "output": "review-report/v3", "template": "review-scaffold-package-experimental",
        "mode": "BOUNDED_EVIDENCE_AUDIT_V5", "default": True,
        "requirements": (
            _requirement("manuscript", "manuscript-draft/v4", True, "inputs/manuscript-draft.json"),
            _requirement("research_idea", "selected-research-idea/v1", False, "inputs/selected-research-idea.json"),
            _requirement("literature_library", "selected-paper-library/v1", False, "inputs/selected-paper-library.json"),
            _requirement("experiment_record", "experiment-record/v5", False, "inputs/experiment-record.json"),
        ),
        "mutable": ("memory/context.md", "memory/progress", "memory/input-provenance.json", "memory/evidence-availability.json", "memory/review-scope.json", "memory/scope-approval.json", "memory/review-result.json", "memory/owner-review.json", "memory/current-artifact.json", "outputs", "inputs"),
    },
    {
        "role": "revision", "workflow_id": "writing-local-experimental",
        "version": "0.6.0", "contract": "sha256:7cf0986a7d09f3cc9854931b74fa26e068c3077712d722cf3ca0971745d47429",
        "capsule_id": "capsule-ff1975990022b65f0bfd83514820dd3b", "capsule_version": "0.8.0",
        "capsule": "sha256:ff1975990022b65f0bfd83514820dd3b84910e783835aed2b4f65cf7749b370d",
        "output": "manuscript-draft/v5", "template": "writing-scaffold-package-experimental",
        "mode": "REVIEW_TO_WRITING_REVISION_V5_ROUND_ONE", "default": False,
        "requirements": (
            _requirement("prior_manuscript", "manuscript-draft/v4", True, "inputs/prior-manuscript.json"),
            _requirement("causal_review", "review-report/v3", True, "inputs/review-report.json"),
            _requirement("research_idea", "selected-research-idea/v1", True, "inputs/selected-research-idea.json"),
            _requirement("literature_library", "selected-paper-library/v1", True, "inputs/selected-paper-library.json"),
            _requirement("experiment_record", "experiment-record/v5", False, "inputs/experiment-record.json"),
        ),
        "mutable": ("memory/context.md", "memory/progress", "memory/input-provenance.json", "memory/revision-plan.json", "memory/revision-plan-approval.json", "memory/claims.json", "memory/citations.json", "memory/issue-accounting.json", "memory/owner-review.json", "memory/current-artifact.json", "outputs", "inputs"),
    },
)


def _output(artifact_type: str) -> dict[str, str]:
    slug = artifact_type.split("/", 1)[0]
    return {
        "artifact_type": artifact_type, "artifact_schema_version": artifact_type,
        "media_type": "application/json", "relative_path_prefix": f"outputs/artifacts/{slug}",
        "content_addressed_filename": "sha256-<content-sha256>.json",
        "progress_artifact_kind": artifact_type,
    }


def upgrade() -> None:
    connection = op.get_bind()
    _assert_preconditions(connection)
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    for item in PUBLICATIONS:
        output = _output(item["output"])
        compatibility = {
            "package_schema_version": "workflow-package/v0.1",
            "artifact_requirements": item["requirements"], "artifact_outputs": [output],
            "supported_mode": item["mode"],
            "experiment_evidence_authority": "experiment-record/v5",
            "presentation_companion_authoritative": False,
            "writing_role": "REVISION" if item["role"] == "revision" else "INITIAL" if item["role"] == "initial-writing" else None,
            "default_project_setup": item["default"],
        }
        connection.execute(sa.text("""
            INSERT INTO local_workflow_definition_versions
              (workflow_definition_id, version, contract_checksum, input_schema_id,
               output_schema_id, compatibility, review_status, core_capability_maturity,
               published_at, created_at, updated_at)
            VALUES (:id, :version, :contract, 'artifact-bindings/v0.1', :output,
                    CAST(:compatibility AS jsonb), 'REVIEWED', 'REVIEWED_CORE',
                    :now, :now, :now)
        """), {**item, "id": item["workflow_id"], "compatibility": _json(compatibility), "now": now})
        capsule_compatibility = {
            "package_schema_version": "workflow-package/v0.1", "package_template_id": item["template"],
            "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
            "artifact_requirements": item["requirements"], "artifact_outputs": [output],
            "core_capability_maturity": "REVIEWED_CORE",
            "skill_pins": [{"skill_id": SKILL_ID, "skill_version": SKILL_VERSION, "skill_checksum": SKILL_CHECKSUM, "trust": "BUILT_IN_REVIEWED"}],
            "experiment_evidence_authority": "experiment-record/v5",
            "interaction_boundary": "TWO_EXACT_OWNER_CHECKPOINTS",
        }
        connection.execute(sa.text("""
            INSERT INTO local_workflow_capsule_versions
              (capsule_id, capsule_version, workflow_definition_id, workflow_version,
               definition_checksum, archive_size_bytes, archive_media_type,
               mutable_roots, capability_requirements, compatibility, review_status,
               legacy_package_compatible, created_at, updated_at)
            VALUES (:capsule_id, :capsule_version, :id, :version, :capsule, 0,
                    'application/zip', CAST(:mutable AS jsonb), CAST(:capabilities AS jsonb),
                    CAST(:compatibility AS jsonb), 'REVIEWED', false, :now, :now)
        """), {**item, "id": item["workflow_id"], "mutable": _json(item["mutable"]),
                 "capabilities": _json(["progress.upload/v0.2", "artifact.materialize/v0.1", "artifact.publish/v0.1"]),
                 "compatibility": _json(capsule_compatibility), "now": now})
        connection.execute(sa.text("""
            INSERT INTO workflow_definition_version_skill_pins
              (workflow_definition_id, workflow_version, pin_order, skill_id,
               skill_version, skill_checksum, purpose, created_at)
            VALUES (:id, :version, 0, :skill_id, :skill_version, :skill_checksum,
                    'Preserve exact v5 evidence and downstream Artifact provenance.', :now)
        """), {"id": item["workflow_id"], "version": item["version"], "skill_id": SKILL_ID,
                 "skill_version": SKILL_VERSION, "skill_checksum": SKILL_CHECKSUM, "now": now})
        for requirement in item["requirements"]:
            connection.execute(sa.text("""
                INSERT INTO workflow_artifact_requirements
                  (workflow_definition_id, workflow_version, requirement_key,
                   artifact_type, compatibility_mode, schema_constraint,
                   cardinality_min, cardinality_max, required, materialization_mode,
                   target_relative_path, created_at, updated_at)
                VALUES (:id, :version, :key, :artifact_type, 'EXACT', :artifact_type,
                        :minimum, 1, :required, 'VERIFIED_COPY', :target, :now, :now)
            """), {"id": item["workflow_id"], "version": item["version"],
                     "key": requirement["requirement_key"], "artifact_type": requirement["artifact_type"],
                     "minimum": 1 if requirement["required"] else 0,
                     "required": requirement["required"], "target": requirement["target_relative_path"], "now": now})
    _assert_seed(connection)


def downgrade() -> None:
    connection = op.get_bind()
    for item in reversed(PUBLICATIONS):
        params = {"id": item["workflow_id"], "version": item["version"], "capsule_id": item["capsule_id"], "capsule_version": item["capsule_version"]}
        connection.execute(sa.text("DELETE FROM workflow_artifact_requirements WHERE workflow_definition_id=:id AND workflow_version=:version"), params)
        connection.execute(sa.text("DELETE FROM workflow_definition_version_skill_pins WHERE workflow_definition_id=:id AND workflow_version=:version"), params)
        connection.execute(sa.text("DELETE FROM local_workflow_capsule_versions WHERE capsule_id=:capsule_id AND capsule_version=:capsule_version"), params)
        connection.execute(sa.text("DELETE FROM local_workflow_definition_versions WHERE workflow_definition_id=:id AND version=:version"), params)


def _assert_preconditions(connection: sa.Connection) -> None:
    value = connection.execute(sa.text("""
        SELECT definition_checksum FROM local_workflow_capsule_versions
        WHERE workflow_definition_id='reproduction-experiment-local-experimental'
          AND workflow_version='0.7.0' AND capsule_version='0.10.0'
    """)).scalar_one_or_none()
    if value != EXPERIMENT_V5_CAPSULE:
        raise RuntimeError("forward downstream publication requires immutable Experiment v5")
    for item in PUBLICATIONS:
        occupied = connection.execute(sa.text("SELECT 1 FROM local_workflow_definition_versions WHERE workflow_definition_id=:id AND version=:version"), {"id": item["workflow_id"], "version": item["version"]}).scalar_one_or_none()
        if occupied is not None:
            raise RuntimeError("forward downstream identity is already occupied")


def _assert_seed(connection: sa.Connection) -> None:
    for item in PUBLICATIONS:
        row = connection.execute(sa.text("""
            SELECT v.contract_checksum, v.output_schema_id, c.capsule_id,
                   c.capsule_version, c.definition_checksum,
                   (SELECT count(*) FROM workflow_artifact_requirements r
                    WHERE r.workflow_definition_id=v.workflow_definition_id
                      AND r.workflow_version=v.version) AS requirement_count
            FROM local_workflow_definition_versions v
            JOIN local_workflow_capsule_versions c
              ON c.workflow_definition_id=v.workflow_definition_id AND c.workflow_version=v.version
            WHERE v.workflow_definition_id=:id AND v.version=:version
        """), {"id": item["workflow_id"], "version": item["version"]}).mappings().one_or_none()
        expected = {"contract_checksum": item["contract"], "output_schema_id": item["output"],
                    "capsule_id": item["capsule_id"], "capsule_version": item["capsule_version"],
                    "definition_checksum": item["capsule"], "requirement_count": len(item["requirements"])}
        if row is None or dict(row) != expected:
            raise RuntimeError("forward downstream immutable seed conflict")


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
