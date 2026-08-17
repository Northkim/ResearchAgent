"""E4 publication identity for generic Experiment 0.6 / Capsule 0.9."""

from __future__ import annotations

from importlib import import_module

import pytest
from sqlalchemy import text

from backend.workflow_packages.generic_experiment_publication import (
    GENERIC_EXPERIMENT_CAPSULE_CHECKSUM, GENERIC_EXPERIMENT_CAPSULE_ID,
    GENERIC_EXPERIMENT_CONTRACT_CHECKSUM, REFERENCE_CAPABILITY_SKILL,
)


def test_generic_experiment_migration_matches_compiler_authority() -> None:
    migration = import_module(
        "backend.database.migrations.versions.20260817_0028_generic_experiment_publication"
    )
    assert migration.down_revision == "20260817_0027"
    assert migration.VERSION == "0.6.0"
    assert migration.CONTRACT_CHECKSUM == GENERIC_EXPERIMENT_CONTRACT_CHECKSUM
    assert migration.CAPSULE_ID == GENERIC_EXPERIMENT_CAPSULE_ID
    assert migration.CAPSULE_VERSION == "0.9.0"
    assert migration.CAPSULE_CHECKSUM == GENERIC_EXPERIMENT_CAPSULE_CHECKSUM
    assert migration.SKILL_ID == REFERENCE_CAPABILITY_SKILL.skill_id
    assert migration.SKILL_CHECKSUM == REFERENCE_CAPABILITY_SKILL.content_checksum


def test_generic_experiment_registry_is_exact_and_preserves_reference_slice(
    postgres_engine,
) -> None:
    with postgres_engine.connect() as connection:
        versions = connection.execute(text("""
            SELECT version, contract_checksum, output_schema_id, compatibility
            FROM local_workflow_definition_versions
            WHERE workflow_definition_id='reproduction-experiment-local-experimental'
              AND version IN ('0.5.0','0.6.0') ORDER BY version
        """)).mappings().all()
        capsule = connection.execute(text("""
            SELECT capsule_id, capsule_version, definition_checksum, compatibility
            FROM local_workflow_capsule_versions
            WHERE workflow_definition_id='reproduction-experiment-local-experimental'
              AND workflow_version='0.6.0'
        """)).mappings().one()
        skill = connection.execute(text("""
            SELECT d.lifecycle, d.source_class, d.trust_tier, v.content_checksum,
                   v.review_status, v.content_source_identity
            FROM local_builtin_skill_definitions d
            JOIN local_skill_versions v ON v.skill_id=d.skill_id
            WHERE d.skill_id=:skill AND v.skill_version='0.1.0'
        """), {"skill": REFERENCE_CAPABILITY_SKILL.skill_id}).mappings().one()
        requirement = connection.execute(text("""
            SELECT requirement_key, artifact_type, required, target_relative_path
            FROM workflow_artifact_requirements
            WHERE workflow_definition_id='reproduction-experiment-local-experimental'
              AND workflow_version='0.6.0'
        """)).mappings().one()
        resources = connection.scalar(text("""
            SELECT count(*) FROM workflow_resource_requirements
            WHERE workflow_definition_id='reproduction-experiment-local-experimental'
              AND workflow_version='0.6.0'
        """))
    assert versions[0]["contract_checksum"] == "sha256:23b6e3cae5746c8589927d2380595df61d01c6fb3f487cf47e09753f3ef8b600"
    assert versions[0]["output_schema_id"] == "experiment-record/v3"
    assert versions[1]["contract_checksum"] == GENERIC_EXPERIMENT_CONTRACT_CHECKSUM
    assert versions[1]["output_schema_id"] == "experiment-record/v4"
    assert versions[1]["compatibility"]["experiment_core"] == "RESEARCH_DOMAIN_AGNOSTIC"
    assert dict(capsule)["capsule_id"] == GENERIC_EXPERIMENT_CAPSULE_ID
    assert capsule["definition_checksum"] == GENERIC_EXPERIMENT_CAPSULE_CHECKSUM
    assert capsule["compatibility"]["synthetic_capability_published"] is False
    assert capsule["compatibility"]["skill_pins"][0]["classification"] == "REFERENCE_EXPERIMENT_CAPABILITY"
    assert dict(skill) == {
        "lifecycle": "AVAILABLE", "source_class": "PLATFORM_BUILT_IN",
        "trust_tier": "BUILT_IN_REVIEWED",
        "content_checksum": REFERENCE_CAPABILITY_SKILL.content_checksum,
        "review_status": "REVIEWED",
        "content_source_identity": REFERENCE_CAPABILITY_SKILL.content_source_identity,
    }
    assert dict(requirement) == {
        "requirement_key": "research_idea",
        "artifact_type": "selected-research-idea/v1", "required": True,
        "target_relative_path": "inputs/selected-research-idea.json",
    }
    assert resources == 0


def test_generic_experiment_conflicting_identity_is_rejected(postgres_engine) -> None:
    migration = import_module(
        "backend.database.migrations.versions.20260817_0028_generic_experiment_publication"
    )
    with postgres_engine.connect() as connection:
        with pytest.raises(RuntimeError, match="already occupied"):
            migration._assert_preconditions(connection)
