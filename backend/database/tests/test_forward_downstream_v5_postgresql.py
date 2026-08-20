"""E4 publication evidence for the exact Experiment-v5 downstream chain."""

from __future__ import annotations

from importlib import import_module
import os
from datetime import datetime, timezone

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import text

from backend.api import ApplicationContainer, create_app
from backend.database import SQLAlchemyUnitOfWork, create_session_factory
from backend.database.disposable import require_disposable_database
from backend.project_workspaces.application import _FULL_RESEARCH_INITIAL_PINS
from backend.project_workspaces.forward_downstream import capsule_version
from backend.project_workspaces.service import ensure_production_workflow_foundation
from backend.database.repositories.workflow_foundation import _capsule_content
from backend.workflow_packages.forward_downstream_publication import (
    INITIAL_WRITING_CAPSULE_CHECKSUM, INITIAL_WRITING_CAPSULE_ID,
    INITIAL_WRITING_CAPSULE_VERSION, INITIAL_WRITING_VERSION,
    REVIEW_CAPSULE_CHECKSUM, REVIEW_CAPSULE_ID,
    REVIEW_CAPSULE_VERSION, REVIEW_VERSION,
    WRITING_REVISION_CAPSULE_CHECKSUM as HISTORICAL_REVISION_CAPSULE_CHECKSUM,
    WRITING_REVISION_CAPSULE_ID as HISTORICAL_REVISION_CAPSULE_ID,
    WRITING_REVISION_CAPSULE_VERSION as HISTORICAL_REVISION_CAPSULE_VERSION,
    WRITING_REVISION_VERSION as HISTORICAL_REVISION_VERSION,
    workflow_checksum,
)
from backend.workflow_packages.revision_optional_support_publication import (
    WRITING_REVISION_CAPSULE_CHECKSUM,
    WRITING_REVISION_CAPSULE_ID,
    WRITING_REVISION_CAPSULE_VERSION,
    WRITING_REVISION_VERSION,
    workflow_checksum as revision_workflow_checksum,
)

MIGRATION = "backend.database.migrations.versions.20260818_0032_forward_downstream_v5_chain"
OPTIONAL_SUPPORT_MIGRATION = (
    "backend.database.migrations.versions.20260819_0034_revision_optional_review_support"
)


def test_migration_identity_matches_forward_compiler_authority() -> None:
    migration = import_module(MIGRATION)
    assert migration.down_revision == "20260818_0031"
    assert (
        HISTORICAL_REVISION_VERSION,
        HISTORICAL_REVISION_CAPSULE_ID,
        HISTORICAL_REVISION_CAPSULE_VERSION,
        HISTORICAL_REVISION_CAPSULE_CHECKSUM,
    ) == (
        "0.6.0",
        "capsule-ff1975990022b65f0bfd83514820dd3b",
        "0.8.0",
        "sha256:ff1975990022b65f0bfd83514820dd3b84910e783835aed2b4f65cf7749b370d",
    )
    expected = (
        ("initial-writing", "0.5.0", INITIAL_WRITING_CAPSULE_ID, INITIAL_WRITING_CAPSULE_CHECKSUM),
        ("review", "0.4.0", REVIEW_CAPSULE_ID, REVIEW_CAPSULE_CHECKSUM),
        ("revision", "0.6.0", HISTORICAL_REVISION_CAPSULE_ID, HISTORICAL_REVISION_CAPSULE_CHECKSUM),
    )
    assert [(item["role"], item["version"], item["capsule_id"], item["capsule"]) for item in migration.PUBLICATIONS] == list(expected)
    assert [item["contract"] for item in migration.PUBLICATIONS] == [workflow_checksum(role) for role, *_ in expected]


def test_optional_review_support_migration_matches_additive_source_authority() -> None:
    migration = import_module(OPTIONAL_SUPPORT_MIGRATION)
    assert migration.down_revision == "20260818_0033"
    assert (
        migration.WORKFLOW_VERSION,
        migration.CONTRACT_CHECKSUM,
        migration.CAPSULE_ID,
        migration.CAPSULE_VERSION,
        migration.CAPSULE_CHECKSUM,
    ) == (
        WRITING_REVISION_VERSION,
        revision_workflow_checksum(),
        WRITING_REVISION_CAPSULE_ID,
        WRITING_REVISION_CAPSULE_VERSION,
        WRITING_REVISION_CAPSULE_CHECKSUM,
    )


def test_optional_review_support_publication_is_additive_and_reversible(
    postgres_engine,
) -> None:
    database_url = os.environ["REAGENT_TEST_DATABASE_URL"]
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    migration = import_module(OPTIONAL_SUPPORT_MIGRATION)
    with postgres_engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260820_0039"
        new_row = connection.execute(text("""
            SELECT v.contract_checksum, v.output_schema_id,
                   v.compatibility->>'writing_role' AS writing_role,
                   v.compatibility->>'default_project_setup' AS is_default,
                   c.capsule_id, c.capsule_version, c.definition_checksum
            FROM local_workflow_definition_versions v
            JOIN local_workflow_capsule_versions c
              ON c.workflow_definition_id=v.workflow_definition_id
             AND c.workflow_version=v.version
            WHERE v.workflow_definition_id=:id AND v.version=:version
        """), {"id": migration.WORKFLOW_ID, "version": migration.WORKFLOW_VERSION}).mappings().one()
        old_checksum = connection.scalar(text("""
            SELECT definition_checksum FROM local_workflow_capsule_versions
            WHERE workflow_definition_id=:id AND workflow_version='0.6.0'
              AND capsule_version='0.8.0'
        """), {"id": migration.WORKFLOW_ID})
    assert dict(new_row) == {
        "contract_checksum": migration.CONTRACT_CHECKSUM,
        "output_schema_id": "manuscript-draft/v5",
        "writing_role": "REVISION",
        "is_default": "false",
        "capsule_id": migration.CAPSULE_ID,
        "capsule_version": migration.CAPSULE_VERSION,
        "definition_checksum": migration.CAPSULE_CHECKSUM,
    }
    assert old_checksum == HISTORICAL_REVISION_CAPSULE_CHECKSUM
    command.downgrade(config, "20260818_0033")
    try:
        with postgres_engine.connect() as connection:
            assert connection.scalar(text("""
                SELECT count(*) FROM local_workflow_definition_versions
                WHERE workflow_definition_id=:id AND version='0.7.0'
            """), {"id": migration.WORKFLOW_ID}) == 0
            assert connection.scalar(text("""
                SELECT definition_checksum FROM local_workflow_capsule_versions
                WHERE workflow_definition_id=:id AND workflow_version='0.6.0'
                  AND capsule_version='0.8.0'
            """), {"id": migration.WORKFLOW_ID}) == HISTORICAL_REVISION_CAPSULE_CHECKSUM
    finally:
        command.upgrade(config, "20260820_0039")


def test_forward_publication_is_exact_role_aware_and_reversible(postgres_engine) -> None:
    database_url = os.environ["REAGENT_TEST_DATABASE_URL"]
    require_disposable_database(postgres_engine, database_url=database_url, expected_identity=os.environ.get("REAGENT_TEST_DATABASE_IDENTITY"))
    config = Config("alembic.ini"); config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, "20260818_0032")
    try:
        with postgres_engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260818_0032"
            rows = connection.execute(text("""
            SELECT workflow_definition_id, version, output_schema_id,
                   compatibility->>'writing_role' AS writing_role,
                   compatibility->>'default_project_setup' AS is_default
            FROM local_workflow_definition_versions
            WHERE (workflow_definition_id='writing-local-experimental' AND version IN ('0.5.0','0.6.0'))
               OR (workflow_definition_id='review-local-experimental' AND version='0.4.0')
            ORDER BY workflow_definition_id, version
        """)).mappings().all()
            requirements = connection.execute(text("""
            SELECT workflow_definition_id, workflow_version, requirement_key,
                   artifact_type, compatibility_mode, materialization_mode, required
            FROM workflow_artifact_requirements
            WHERE workflow_version IN ('0.5.0','0.6.0','0.4.0')
              AND artifact_type IN ('experiment-record/v5','manuscript-draft/v4','review-report/v3')
            ORDER BY workflow_definition_id, workflow_version, requirement_key
            """)).mappings().all()
        assert [dict(row) for row in rows] == [
            {"workflow_definition_id":"review-local-experimental","version":"0.4.0","output_schema_id":"review-report/v3","writing_role":None,"is_default":"true"},
            {"workflow_definition_id":"writing-local-experimental","version":"0.5.0","output_schema_id":"manuscript-draft/v4","writing_role":"INITIAL","is_default":"true"},
            {"workflow_definition_id":"writing-local-experimental","version":"0.6.0","output_schema_id":"manuscript-draft/v5","writing_role":"REVISION","is_default":"false"},
        ]
        assert all(row["compatibility_mode"] == "EXACT" and row["materialization_mode"] == "VERIFIED_COPY" for row in requirements)
        assert {(row["workflow_version"], row["artifact_type"], row["required"]) for row in requirements} >= {
            ("0.5.0", "experiment-record/v5", False), ("0.4.0", "manuscript-draft/v4", True),
            ("0.4.0", "experiment-record/v5", False), ("0.6.0", "manuscript-draft/v4", True),
            ("0.6.0", "review-report/v3", True), ("0.6.0", "experiment-record/v5", False),
        }
        command.downgrade(config, "20260818_0031")
        with postgres_engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM local_workflow_definition_versions WHERE (workflow_definition_id='writing-local-experimental' AND version IN ('0.5.0','0.6.0')) OR (workflow_definition_id='review-local-experimental' AND version='0.4.0')")) == 0
        command.upgrade(config, "20260818_0032")
        with postgres_engine.connect() as connection:
            with pytest.raises(RuntimeError, match="already occupied"):
                import_module(MIGRATION)._assert_preconditions(connection)
    finally:
        command.upgrade(config, "head")


def test_published_capsules_match_source_and_foundation_replay_is_idempotent(
    postgres_engine,
) -> None:
    session_factory = create_session_factory(postgres_engine)
    uow = SQLAlchemyUnitOfWork(session_factory)
    now = datetime(2026, 8, 18, tzinfo=timezone.utc)
    identities = (
        ("initial-writing", INITIAL_WRITING_CAPSULE_ID, INITIAL_WRITING_CAPSULE_VERSION),
        ("review", REVIEW_CAPSULE_ID, REVIEW_CAPSULE_VERSION),
        ("revision", WRITING_REVISION_CAPSULE_ID, WRITING_REVISION_CAPSULE_VERSION),
    )
    before = _foundation_counts(postgres_engine)
    try:
        for role, capsule_id, version in identities:
            published = uow.workflow_foundation.get_capsule_version(capsule_id, version)
            assert published is not None
            assert _capsule_content(published) == _capsule_content(
                capsule_version(role, now)
            )
        ensure_production_workflow_foundation(uow, now=now)
        uow.commit()
        assert _foundation_counts(postgres_engine) == before
        ensure_production_workflow_foundation(uow, now=now)
        uow.commit()
        assert _foundation_counts(postgres_engine) == before
    finally:
        uow.close()


def test_postgresql_project_creation_preserves_current_roles_and_presets(
    postgres_engine, tmp_path,
) -> None:
    session_factory = create_session_factory(postgres_engine)
    container = ApplicationContainer(
        unit_of_work_factory=lambda: SQLAlchemyUnitOfWork(session_factory),
        local_package_root=str(tmp_path / "packages"),
    )
    payload = {
        "research_topic": "Foundation replay qualification",
        "selected_workflow": "LITERATURE_SEARCH",
    }
    with TestClient(create_app(container)) as client:
        literature = client.post("/projects", json={
            **payload, "name": "F1 Literature", "workflow_setup": "literature-only",
        })
        assert literature.status_code == 201, literature.text
        custom = client.post("/projects", json={
            **payload,
            "name": "F1 U1 custom",
            "workflow_setup": "custom",
            "custom_workflow_definition_ids": [
                "literature-search-local-experimental",
                "idea-discovery-local-experimental",
                "writing-local-experimental",
                "review-local-experimental",
            ],
        })
        assert custom.status_code == 201, custom.text
        full = client.post("/projects", json={
            **payload, "name": "F1 Full Research", "workflow_setup": "full-research",
        })
        assert full.status_code == 201, full.text

        literature_instances = _instances(client, literature.json()["project_id"])
        custom_instances = _instances(client, custom.json()["project_id"])
        full_instances = _instances(client, full.json()["project_id"])
        assert len(literature_instances) == 1
        assert {(item["workflow_definition_id"], item["workflow_version"], item["capsule_version"])
                for item in custom_instances} == {
            ("literature-search-local-experimental", "0.6.0", "0.8.0"),
            ("idea-discovery-local-experimental", "0.4.0", "0.5.0"),
            ("writing-local-experimental", INITIAL_WRITING_VERSION,
             INITIAL_WRITING_CAPSULE_VERSION),
            ("review-local-experimental", REVIEW_VERSION, REVIEW_CAPSULE_VERSION),
        }
        assert {(item["workflow_definition_id"], item["workflow_version"],
                 item["capsule_id"], item["capsule_version"])
                for item in full_instances} == set(_FULL_RESEARCH_INITIAL_PINS)
        assert all(
            not (
                item["workflow_definition_id"] == "writing-local-experimental"
                and item["workflow_version"] == WRITING_REVISION_VERSION
            )
            for item in (*custom_instances, *full_instances)
        )

        writing = client.get(
            "/workflow-definitions/writing-local-experimental"
        ).json()
        review = client.get(
            "/workflow-definitions/review-local-experimental"
        ).json()
        experiment = client.get(
            "/workflow-definitions/reproduction-experiment-local-experimental"
        ).json()
        assert writing["recommended_version"]["version"] == INITIAL_WRITING_VERSION
        assert review["recommended_version"]["version"] == REVIEW_VERSION
        assert experiment["recommended_version"]["version"] == "0.8.0"
    role_uow = SQLAlchemyUnitOfWork(session_factory)
    try:
        revision = role_uow.workflow_foundation.get_definition_version(
            "writing-local-experimental", WRITING_REVISION_VERSION
        )
        experiment_v5 = role_uow.workflow_foundation.get_definition_version(
            "reproduction-experiment-local-experimental", "0.7.0"
        )
        assert revision is not None and experiment_v5 is not None
        assert revision.compatibility["writing_role"] == "REVISION"
        assert revision.compatibility["default_project_setup"] is False
        assert experiment_v5.compatibility["default_project_setup"] is False
    finally:
        role_uow.close()


def _foundation_counts(engine) -> tuple[int, int, int, int, int]:
    with engine.connect() as connection:
        return tuple(connection.scalar(text(f"SELECT count(*) FROM {table}")) for table in (
            "local_workflow_definitions",
            "local_workflow_definition_versions",
            "local_workflow_capsule_versions",
            "workflow_definition_version_skill_pins",
            "workflow_artifact_requirements",
        ))


def _instances(client: TestClient, project_id: str) -> list[dict[str, object]]:
    response = client.get(f"/projects/{project_id}/workflow-instances")
    assert response.status_code == 200, response.text
    return response.json()["items"]
