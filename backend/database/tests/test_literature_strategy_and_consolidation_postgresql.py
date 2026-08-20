"""R4 PostgreSQL publication and immutable source-equivalence evidence."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module
import os

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from backend.database import SQLAlchemyUnitOfWork, create_session_factory
from backend.database.disposable import require_disposable_database
from backend.database.repositories.workflow_foundation import (
    _capsule_content,
    _definition_version_content,
)
from backend.project_workspaces.production_workflows import (
    LITERATURE_SEARCH_V0_8_CAPSULE_CHECKSUM,
    LITERATURE_SEARCH_V0_8_CAPSULE_ID,
    literature_consolidation_capsule,
    literature_consolidation_definition_version,
    literature_consolidation_requirements,
    literature_search_v0_6_definition_version,
    literature_search_v0_8_capsule,
)
from backend.project_workspaces.service import (
    _requirement_content,
    ensure_production_workflow_foundation,
)
from backend.workflow_packages.literature_consolidation import (
    CAPSULE_CHECKSUM,
    CAPSULE_ID,
    WORKFLOW_ID,
    WORKFLOW_VERSION,
    contract_checksum,
)
from backend.workflow_packages.production_workflows import (
    LITERATURE_SEARCH_V0_6_WORKFLOW_VERSION,
    LITERATURE_SEARCH_V0_8_CAPSULE_VERSION,
    literature_search_v0_6_contract_checksum,
)

MIGRATION = (
    "backend.database.migrations.versions."
    "20260820_0039_literature_strategy_and_consolidation"
)


def _head(engine) -> str:
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


def _counts(engine) -> tuple[int, int, int, int, int]:
    with engine.connect() as connection:
        return (
            connection.scalar(text("""
                SELECT count(*) FROM local_workflow_definitions
                WHERE workflow_definition_id=:id
            """), {"id": WORKFLOW_ID}),
            connection.scalar(text("""
                SELECT count(*) FROM local_workflow_definition_versions
                WHERE (workflow_definition_id='literature-search-local-experimental'
                       AND version='0.6.0')
                   OR (workflow_definition_id=:id AND version=:version)
            """), {"id": WORKFLOW_ID, "version": WORKFLOW_VERSION}),
            connection.scalar(text("""
                SELECT count(*) FROM local_workflow_capsule_versions
                WHERE (capsule_id=:literature AND capsule_version='0.8.0')
                   OR (capsule_id=:consolidation AND capsule_version='0.1.0')
            """), {
                "literature": LITERATURE_SEARCH_V0_8_CAPSULE_ID,
                "consolidation": CAPSULE_ID,
            }),
            connection.scalar(text("""
                SELECT count(*) FROM workflow_artifact_requirements
                WHERE workflow_definition_id=:id AND workflow_version=:version
            """), {"id": WORKFLOW_ID, "version": WORKFLOW_VERSION}),
            connection.scalar(text("""
                SELECT count(*) FROM project_workflow_instances
                WHERE workflow_definition_id=:id
            """), {"id": WORKFLOW_ID}),
        )


def test_migration_identity_matches_r4_source_authority() -> None:
    migration = import_module(MIGRATION)
    assert migration.down_revision == "20260820_0038"
    assert (
        migration.LITERATURE_VERSION,
        migration.LITERATURE_CONTRACT,
        migration.LITERATURE_CAPSULE_ID,
        migration.LITERATURE_CAPSULE_VERSION,
        migration.LITERATURE_CAPSULE_CHECKSUM,
    ) == (
        LITERATURE_SEARCH_V0_6_WORKFLOW_VERSION,
        literature_search_v0_6_contract_checksum(),
        LITERATURE_SEARCH_V0_8_CAPSULE_ID,
        LITERATURE_SEARCH_V0_8_CAPSULE_VERSION,
        LITERATURE_SEARCH_V0_8_CAPSULE_CHECKSUM,
    )
    assert (
        migration.CONSOLIDATION_VERSION,
        migration.CONSOLIDATION_CONTRACT,
        migration.CONSOLIDATION_CAPSULE_ID,
        migration.CONSOLIDATION_CAPSULE_VERSION,
        migration.CONSOLIDATION_CAPSULE_CHECKSUM,
    ) == (
        WORKFLOW_VERSION,
        contract_checksum(),
        CAPSULE_ID,
        "0.1.0",
        CAPSULE_CHECKSUM,
    )


def test_r4_publication_is_exact_idempotent_and_reversible(postgres_engine) -> None:
    database_url = os.environ["REAGENT_TEST_DATABASE_URL"]
    require_disposable_database(
        postgres_engine,
        database_url=database_url,
        expected_identity=os.environ.get("REAGENT_TEST_DATABASE_IDENTITY"),
    )
    assert _head(postgres_engine) == "20260820_0039"
    assert _counts(postgres_engine) == (1, 2, 2, 2, 0)

    now = datetime(2026, 8, 20, tzinfo=UTC)
    uow = SQLAlchemyUnitOfWork(create_session_factory(postgres_engine))
    try:
        published_literature_version = (
            uow.workflow_foundation.get_definition_version(
                "literature-search-local-experimental", "0.6.0"
            )
        )
        published_literature_capsule = uow.workflow_foundation.get_capsule_version(
            LITERATURE_SEARCH_V0_8_CAPSULE_ID, "0.8.0"
        )
        published_consolidation_version = (
            uow.workflow_foundation.get_definition_version(
                WORKFLOW_ID, WORKFLOW_VERSION
            )
        )
        published_consolidation_capsule = (
            uow.workflow_foundation.get_capsule_version(CAPSULE_ID, "0.1.0")
        )
        assert published_literature_version is not None
        assert published_literature_capsule is not None
        assert published_consolidation_version is not None
        assert published_consolidation_capsule is not None
        assert _definition_version_content(published_literature_version) == (
            _definition_version_content(literature_search_v0_6_definition_version(now))
        )
        assert _capsule_content(published_literature_capsule) == _capsule_content(
            literature_search_v0_8_capsule(now)
        )
        assert _definition_version_content(published_consolidation_version) == (
            _definition_version_content(literature_consolidation_definition_version(now))
        )
        assert _capsule_content(published_consolidation_capsule) == _capsule_content(
            literature_consolidation_capsule(now)
        )
        for expected in literature_consolidation_requirements(now):
            published = uow.artifact_references.get_requirement(
                expected.workflow_definition_id,
                expected.workflow_version,
                expected.requirement_key,
            )
            assert published is not None
            assert _requirement_content(published) == _requirement_content(expected)
        ensure_production_workflow_foundation(uow, now=now)
        ensure_production_workflow_foundation(uow, now=now)
        uow.commit()
    finally:
        uow.close()
    assert _counts(postgres_engine) == (1, 2, 2, 2, 0)

    configuration = Config("alembic.ini")
    configuration.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(configuration, "20260820_0038")
    try:
        assert _head(postgres_engine) == "20260820_0038"
        assert _counts(postgres_engine) == (0, 0, 0, 0, 0)
    finally:
        command.upgrade(configuration, "20260820_0039")
    assert _head(postgres_engine) == "20260820_0039"
    assert _counts(postgres_engine) == (1, 2, 2, 2, 0)
