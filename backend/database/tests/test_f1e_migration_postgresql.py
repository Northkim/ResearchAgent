"""Destructive F1E migration cycle qualification on an isolated database."""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def test_f1e_resource_seed_downgrade_reupgrade_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.environ.get("REAGENT_NIGHT_F1E_MIGRATION_DATABASE_URL")
    if not database_url:
        pytest.skip("dedicated NIGHT-F1E migration database URL is required")
    if "reagent_night_f1e" not in database_url:
        pytest.fail("migration qualification refuses a non-NIGHT-F1E database")
    monkeypatch.setenv("REAGENT_DATABASE_URL", database_url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    engine = create_engine(database_url)
    try:
        command.downgrade(config, "base")
        command.upgrade(config, "20260806_0016")
        f1d = _f1d_identity(engine)
        command.upgrade(config, "20260806_0017")
        first = _f1e_identity(engine)
        assert len(first["requirements"]) == 4
        assert len(first["pins"]) == 2
        assert _f1d_identity(engine) == f1d
        command.downgrade(config, "20260806_0016")
        assert _revision(engine) == "20260806_0016"
        assert _f1d_identity(engine) == f1d
        with engine.connect() as connection:
            assert not connection.dialect.has_table(connection, "project_resource_references")
        command.upgrade(config, "20260806_0017")
        assert _f1e_identity(engine) == first
        assert _f1d_identity(engine) == f1d
    finally:
        engine.dispose()


def _revision(engine) -> str:
    with engine.connect() as connection:
        return str(connection.scalar(text("SELECT version_num FROM alembic_version")))


def _f1d_identity(engine):
    with engine.connect() as connection:
        return tuple(connection.execute(text("""
            SELECT workflow_definition_id, version, contract_checksum
            FROM local_workflow_definition_versions
            WHERE version IN ('0.1.0','0.2.0')
            ORDER BY workflow_definition_id, version
        """)))


def _f1e_identity(engine):
    with engine.connect() as connection:
        version = tuple(connection.execute(text("""
            SELECT workflow_definition_id, version, contract_checksum
            FROM local_workflow_definition_versions
            WHERE workflow_definition_id = 'reproduction-experiment-local-experimental'
              AND version = '0.3.0'
        """)))
        requirements = tuple(connection.execute(text("""
            SELECT requirement_key, resource_kind, cardinality_min, cardinality_max,
                   required, allowed_providers_json
            FROM workflow_resource_requirements
            ORDER BY requirement_key
        """)))
        pins = tuple(connection.execute(text("""
            SELECT pin_order, skill_id, skill_version, skill_checksum
            FROM workflow_definition_version_skill_pins
            WHERE workflow_definition_id = 'reproduction-experiment-local-experimental'
              AND workflow_version = '0.3.0'
            ORDER BY pin_order
        """)))
    return {"version": version, "requirements": requirements, "pins": pins}
