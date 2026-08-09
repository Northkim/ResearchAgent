"""Seed production Writing, Review, and Experiment scaffold Workflows.

Revision ID: 20260806_0015
Revises: 20260806_0014
Create Date: 2026-08-09
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260806_0015"
down_revision: str | None = "20260806_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VERSION = "0.1.0"
CAPSULE_VERSION = "0.1.0"
NOTICE = "Product flow is functional. Research capability is placeholder."


def _requirement(key: str, artifact_type: str, target: str, required: bool) -> dict:
    return {
        "requirement_key": key,
        "artifact_type": artifact_type,
        "artifact_schema": artifact_type,
        "cardinality": "ONE",
        "required": required,
        "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
        "materialization_mode": "VERIFIED_COPY",
        "target_relative_path": target,
    }


def _output(artifact_type: str) -> dict:
    slug = artifact_type.split("/", 1)[0]
    return {
        "artifact_type": artifact_type,
        "artifact_schema_version": artifact_type,
        "media_type": "application/json",
        "relative_path_prefix": f"outputs/artifacts/{slug}",
        "content_addressed_filename": "sha256-<content-sha256>.json",
        "progress_artifact_kind": artifact_type,
    }


WORKFLOWS = (
    {
        "id": "writing-local-experimental",
        "name": "Writing",
        "description": (
            "Run the complete manuscript Artifact flow with an explicitly marked "
            "placeholder research core."
        ),
        "contract_checksum": "sha256:637629e80170f725fd9fb7f844cfc776213c889d773fe9a1d85466f53176767c",
        "capsule_id": "capsule-072f0ceff77bac4193d13eba70df83fb",
        "capsule_checksum": "sha256:072f0ceff77bac4193d13eba70df83fbba3818f5329938d8fd441920bc84947a",
        "template_id": "writing-scaffold-package-experimental",
        "output_type": "manuscript-draft/v1",
        "supported_mode": None,
        "requirements": (
            _requirement("research_idea", "selected-research-idea/v1", "inputs/selected-research-idea.json", True),
            _requirement("literature_library", "selected-paper-library/v1", "inputs/selected-paper-library.json", True),
            _requirement("experiment_record", "experiment-record/v1", "inputs/experiment-record.json", False),
            _requirement("review_feedback", "review-report/v1", "inputs/review-report.json", False),
            _requirement("prior_manuscript", "manuscript-draft/v1", "inputs/prior-manuscript.json", False),
        ),
    },
    {
        "id": "review-local-experimental",
        "name": "Review",
        "description": (
            "Run the complete review Artifact flow without claiming substantive "
            "peer review."
        ),
        "contract_checksum": "sha256:d8e573a937382b6e8107e715790ca93f408cac14790f20227df33b2c48f6c5e9",
        "capsule_id": "capsule-a5e168388ab5af52cc087e42eba94908",
        "capsule_checksum": "sha256:a5e168388ab5af52cc087e42eba949085c574e61abe9f7d2f65cba63673467ce",
        "template_id": "review-scaffold-package-experimental",
        "output_type": "review-report/v1",
        "supported_mode": None,
        "requirements": (
            _requirement("manuscript", "manuscript-draft/v1", "inputs/manuscript-draft.json", True),
            _requirement("literature_library", "selected-paper-library/v1", "inputs/selected-paper-library.json", False),
            _requirement("experiment_record", "experiment-record/v1", "inputs/experiment-record.json", False),
        ),
    },
    {
        "id": "reproduction-experiment-local-experimental",
        "name": "Reproduction & Experiment",
        "description": (
            "Build an Idea Experiment skeleton with no real experiment or paper "
            "reproduction execution."
        ),
        "contract_checksum": "sha256:64dab0ff502488ef420319b7b9d6c250222920881f4d1397888dc30a3c487405",
        "capsule_id": "capsule-e84f06e07429c2f37db3ff884c799a2f",
        "capsule_checksum": "sha256:e84f06e07429c2f37db3ff884c799a2f74b0fa2cca96dd1c21506160599feab3",
        "template_id": "reproduction-experiment-scaffold-package-experimental",
        "output_type": "experiment-record/v1",
        "supported_mode": "IDEA_EXPERIMENT",
        "requirements": (
            _requirement("research_idea", "selected-research-idea/v1", "inputs/selected-research-idea.json", True),
            _requirement("literature_library", "selected-paper-library/v1", "inputs/selected-paper-library.json", False),
        ),
    },
)


def upgrade() -> None:
    connection = op.get_bind()
    now = connection.scalar(sa.text("SELECT CURRENT_TIMESTAMP"))
    for workflow in WORKFLOWS:
        output = _output(workflow["output_type"])
        compatibility = {
            "package_schema_version": "workflow-package/v0.1",
            "artifact_requirements": list(workflow["requirements"]),
            "artifact_outputs": [output],
            "scaffold_notice": NOTICE,
            "supported_mode": workflow["supported_mode"],
        }
        connection.execute(sa.text("""
            INSERT INTO local_workflow_definitions
              (workflow_definition_id, display_name, description, lifecycle,
               allows_multiple_instances, created_at, updated_at)
            VALUES (:id, :name, :description, 'AVAILABLE', true, :now, :now)
            ON CONFLICT (workflow_definition_id) DO NOTHING
        """), {**workflow, "now": now})
        connection.execute(sa.text("""
            INSERT INTO local_workflow_definition_versions
              (workflow_definition_id, version, contract_checksum, input_schema_id,
               output_schema_id, compatibility, review_status,
               core_capability_maturity, published_at, created_at, updated_at)
            VALUES (:id, :version, :checksum, 'artifact-bindings/v0.1',
                    :output_type, CAST(:compatibility AS jsonb), 'REVIEWED',
                    'SCAFFOLD_CORE', :now, :now, :now)
            ON CONFLICT (workflow_definition_id, version) DO NOTHING
        """), {
            "id": workflow["id"], "version": VERSION,
            "checksum": workflow["contract_checksum"],
            "output_type": workflow["output_type"],
            "compatibility": _json(compatibility), "now": now,
        })
        capsule_compatibility = {
            "package_schema_version": "workflow-package/v0.1",
            "package_template_id": workflow["template_id"],
            "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
            "artifact_requirements": list(workflow["requirements"]),
            "artifact_outputs": [output],
            "core_capability_maturity": "SCAFFOLD_CORE",
            "scaffold_notice": NOTICE,
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
            ON CONFLICT (capsule_id, capsule_version) DO NOTHING
        """), {
            "capsule_id": workflow["capsule_id"],
            "capsule_version": CAPSULE_VERSION, "id": workflow["id"],
            "version": VERSION, "checksum": workflow["capsule_checksum"],
            "mutable_roots": _json([
                "memory/context.md", "memory/progress",
                "memory/input-provenance.json", "memory/current-artifact.json",
                "outputs", "inputs",
            ]),
            "capabilities": _json([
                "progress.upload/v0.2", "artifact.materialize/v0.1",
                "artifact.publish/v0.1",
            ]),
            "compatibility": _json(capsule_compatibility), "now": now,
        })
        for requirement in workflow["requirements"]:
            connection.execute(sa.text("""
                INSERT INTO workflow_artifact_requirements
                  (workflow_definition_id, workflow_version, requirement_key,
                   artifact_type, compatibility_mode, schema_constraint,
                   cardinality_min, cardinality_max, required,
                   materialization_mode, target_relative_path, created_at, updated_at)
                VALUES (:id, :version, :key, :artifact_type, 'EXACT', :schema,
                        :minimum, 1, :required, 'VERIFIED_COPY', :target, :now, :now)
                ON CONFLICT (workflow_definition_id, workflow_version, requirement_key)
                DO NOTHING
            """), {
                "id": workflow["id"], "version": VERSION,
                "key": requirement["requirement_key"],
                "artifact_type": requirement["artifact_type"],
                "schema": requirement["artifact_schema"],
                "minimum": 1 if requirement["required"] else 0,
                "required": requirement["required"],
                "target": requirement["target_relative_path"], "now": now,
            })
    _assert_seed_content(connection)


def downgrade() -> None:
    connection = op.get_bind()
    ids = tuple(workflow["id"] for workflow in WORKFLOWS)
    connection.execute(sa.text("""
        DELETE FROM workflow_artifact_requirements
        WHERE workflow_definition_id IN :ids AND workflow_version = :version
    """).bindparams(sa.bindparam("ids", expanding=True)), {"ids": ids, "version": VERSION})
    capsule_ids = tuple(workflow["capsule_id"] for workflow in WORKFLOWS)
    connection.execute(sa.text("""
        DELETE FROM local_workflow_capsule_versions
        WHERE capsule_id IN :ids AND capsule_version = :version
    """).bindparams(sa.bindparam("ids", expanding=True)), {"ids": capsule_ids, "version": CAPSULE_VERSION})
    connection.execute(sa.text("""
        DELETE FROM local_workflow_definition_versions
        WHERE workflow_definition_id IN :ids AND version = :version
    """).bindparams(sa.bindparam("ids", expanding=True)), {"ids": ids, "version": VERSION})
    connection.execute(sa.text("""
        DELETE FROM local_workflow_definitions WHERE workflow_definition_id IN :ids
    """).bindparams(sa.bindparam("ids", expanding=True)), {"ids": ids})


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _assert_seed_content(connection: sa.Connection) -> None:
    for workflow in WORKFLOWS:
        row = connection.execute(sa.text("""
            SELECT d.display_name, d.lifecycle, d.allows_multiple_instances,
                   v.contract_checksum, v.output_schema_id, v.review_status,
                   v.core_capability_maturity
            FROM local_workflow_definitions d
            JOIN local_workflow_definition_versions v
              ON v.workflow_definition_id = d.workflow_definition_id
            WHERE d.workflow_definition_id = :id AND v.version = :version
        """), {"id": workflow["id"], "version": VERSION}).mappings().one_or_none()
        if row is None or dict(row) != {
            "display_name": workflow["name"], "lifecycle": "AVAILABLE",
            "allows_multiple_instances": True,
            "contract_checksum": workflow["contract_checksum"],
            "output_schema_id": workflow["output_type"],
            "review_status": "REVIEWED", "core_capability_maturity": "SCAFFOLD_CORE",
        }:
            raise RuntimeError(f"F1B {workflow['name']} seed conflict")
        count = connection.scalar(sa.text("""
            SELECT count(*) FROM workflow_artifact_requirements
            WHERE workflow_definition_id = :id AND workflow_version = :version
        """), {"id": workflow["id"], "version": VERSION})
        if count != len(workflow["requirements"]):
            raise RuntimeError(f"F1B {workflow['name']} requirement seed conflict")
