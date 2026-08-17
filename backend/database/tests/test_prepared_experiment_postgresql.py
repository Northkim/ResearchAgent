"""Publication identity and Registry shape for Experiment 0.5 Path A."""

from __future__ import annotations

from importlib import import_module

from sqlalchemy import text

from backend.workflow_packages.production_workflows import (
    PREPARED_EXPERIMENT_CAPSULE_CHECKSUM, PREPARED_EXPERIMENT_CAPSULE_ID,
    PREPARED_EXPERIMENT_CONTRACT_CHECKSUM,
)


def test_prepared_experiment_migration_matches_runtime_authority() -> None:
    migration = import_module(
        "backend.database.migrations.versions.20260817_0027_prepared_experiment_path"
    )
    assert migration.down_revision == "20260815_0026"
    assert migration.VERSION == "0.5.0"
    assert migration.CONTRACT_CHECKSUM == PREPARED_EXPERIMENT_CONTRACT_CHECKSUM
    assert migration.CAPSULE_ID == PREPARED_EXPERIMENT_CAPSULE_ID
    assert migration.CAPSULE_VERSION == "0.8.0"
    assert migration.CAPSULE_CHECKSUM == PREPARED_EXPERIMENT_CAPSULE_CHECKSUM


def test_prepared_experiment_registry_is_provider_neutral_and_exact(postgres_engine) -> None:
    with postgres_engine.connect() as connection:
        definition = connection.execute(text("""
            SELECT output_schema_id, compatibility, core_capability_maturity
            FROM local_workflow_definition_versions
            WHERE workflow_definition_id='reproduction-experiment-local-experimental'
              AND version='0.5.0'
        """)).mappings().one()
        capsule = connection.execute(text("""
            SELECT capsule_id, capsule_version, definition_checksum
            FROM local_workflow_capsule_versions
            WHERE workflow_definition_id='reproduction-experiment-local-experimental'
              AND workflow_version='0.5.0'
        """)).mappings().one()
        artifact = connection.execute(text("""
            SELECT requirement_key, artifact_type, required, cardinality_min,
                   cardinality_max, materialization_mode, target_relative_path
            FROM workflow_artifact_requirements
            WHERE workflow_definition_id='reproduction-experiment-local-experimental'
              AND workflow_version='0.5.0'
        """)).mappings().one()
        resources = connection.scalar(text("""
            SELECT count(*) FROM workflow_resource_requirements
            WHERE workflow_definition_id='reproduction-experiment-local-experimental'
              AND workflow_version='0.5.0'
        """))
    assert definition["output_schema_id"] == "experiment-record/v3"
    assert definition["core_capability_maturity"] == "REVIEWED_CORE"
    assert definition["compatibility"]["resource_mode"] == "PREPARE_WITH_REAGENT"
    assert dict(capsule) == {"capsule_id": PREPARED_EXPERIMENT_CAPSULE_ID, "capsule_version": "0.8.0", "definition_checksum": PREPARED_EXPERIMENT_CAPSULE_CHECKSUM}
    assert dict(artifact) == {"requirement_key": "research_idea", "artifact_type": "selected-research-idea/v1", "required": True, "cardinality_min": 1, "cardinality_max": 1, "materialization_mode": "VERIFIED_COPY", "target_relative_path": "inputs/selected-research-idea.json"}
    assert resources == 0
