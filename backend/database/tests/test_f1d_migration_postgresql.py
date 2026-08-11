"""Destructive F1D migration qualification on an explicitly isolated database."""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from backend.database.disposable import require_disposable_database

SCAFFOLD_IDS = (
    "writing-local-experimental",
    "review-local-experimental",
    "reproduction-experiment-local-experimental",
)


def test_f1d_skill_seed_downgrade_reupgrade_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.environ.get("REAGENT_NIGHT_F1D_MIGRATION_DATABASE_URL")
    if not database_url:
        pytest.skip("dedicated NIGHT-F1D migration database URL is required")
    monkeypatch.setenv("REAGENT_DATABASE_URL", database_url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    engine = create_engine(database_url)
    try:
        require_disposable_database(
            engine,
            database_url=database_url,
            expected_identity=os.environ.get("REAGENT_TEST_DATABASE_IDENTITY"),
        )
        command.downgrade(config, "base")
        command.upgrade(config, "20260806_0015")
        legacy = _legacy_identity(engine)
        command.upgrade(config, "20260806_0016")
        first = _f1d_identity(engine)
        assert len(first["skills"]) == 2
        assert len(first["pins"]) == 6
        assert len(first["workflow_versions"]) == 3
        assert _legacy_identity(engine) == legacy

        command.downgrade(config, "20260806_0015")
        assert _revision(engine) == "20260806_0015"
        assert _legacy_identity(engine) == legacy
        with engine.connect() as connection:
            assert not connection.dialect.has_table(
                connection, "local_builtin_skill_definitions"
            )

        command.upgrade(config, "20260806_0016")
        assert _revision(engine) == "20260806_0016"
        assert _f1d_identity(engine) == first
        assert _legacy_identity(engine) == legacy
    finally:
        engine.dispose()


def _revision(engine) -> str:
    with engine.connect() as connection:
        return str(connection.scalar(text("SELECT version_num FROM alembic_version")))


def _legacy_identity(engine) -> tuple[tuple, ...]:
    with engine.connect() as connection:
        return tuple(connection.execute(text("""
            SELECT workflow_definition_id, version, contract_checksum
            FROM local_workflow_definition_versions
            WHERE workflow_definition_id IN (
              'writing-local-experimental', 'review-local-experimental',
              'reproduction-experiment-local-experimental'
            ) AND version = '0.1.0'
            ORDER BY workflow_definition_id
        """)))


def _f1d_identity(engine) -> dict[str, tuple[tuple, ...]]:
    with engine.connect() as connection:
        skills = tuple(connection.execute(text("""
            SELECT d.skill_id, v.skill_version, v.content_checksum,
                   v.trust_tier, v.content_manifest
            FROM local_builtin_skill_definitions d
            JOIN local_skill_versions v USING (skill_id)
            ORDER BY d.skill_id, v.skill_version
        """)))
        pins = tuple(connection.execute(text("""
            SELECT workflow_definition_id, workflow_version, pin_order,
                   skill_id, skill_version, skill_checksum
            FROM workflow_definition_version_skill_pins
            ORDER BY workflow_definition_id, workflow_version, pin_order
        """)))
        versions = tuple(connection.execute(text("""
            SELECT workflow_definition_id, version, contract_checksum
            FROM local_workflow_definition_versions
            WHERE workflow_definition_id IN (
              'writing-local-experimental', 'review-local-experimental',
              'reproduction-experiment-local-experimental'
            ) AND version = '0.2.0'
            ORDER BY workflow_definition_id
        """)))
    return {"skills": skills, "pins": pins, "workflow_versions": versions}
