"""PostgreSQL test composition; requires an explicitly provided test database."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, text

from backend.database import (
    SQLAlchemyUnitOfWork,
    create_postgres_engine,
    create_session_factory,
)
from backend.database.orm import Base
from backend.database.disposable import (
    DisposableDatabaseError,
    require_disposable_database,
)


@pytest.fixture(scope="session")
def repository_current_head() -> str:
    repository_root = Path(__file__).resolve().parents[3]
    configuration = Config(str(repository_root / "alembic.ini"))
    configuration.set_main_option(
        "script_location",
        str(repository_root / "backend/database/migrations"),
    )
    heads = ScriptDirectory.from_config(configuration).get_heads()
    if len(heads) != 1:
        pytest.fail(
            "PostgreSQL tests require exactly one repository Alembic head; "
            f"found {len(heads)}"
        )
    return heads[0]


@pytest.fixture(scope="session")
def postgres_engine(repository_current_head: str) -> Iterator[Engine]:
    database_url = os.environ.get("REAGENT_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("REAGENT_TEST_DATABASE_URL is required for PostgreSQL tests")
    engine = create_postgres_engine(database_url)
    try:
        require_disposable_database(
            engine,
            database_url=database_url,
            expected_identity=os.environ.get("REAGENT_TEST_DATABASE_IDENTITY"),
        )
        with engine.connect() as connection:
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    except DisposableDatabaseError as error:
        engine.dispose()
        pytest.fail(f"PostgreSQL destructive fixture rejected database: {error}")
    if revision != repository_current_head:
        engine.dispose()
        pytest.fail(
            "PostgreSQL test database must be migrated to the repository "
            f"Alembic head {repository_current_head}; found {revision}"
        )
    yield engine
    engine.dispose()


@pytest.fixture()
def sql_uow_factory(
    postgres_engine: Engine,
) -> Iterator[Callable[[], SQLAlchemyUnitOfWork]]:
    _truncate(postgres_engine)
    session_factory = create_session_factory(postgres_engine)
    yield lambda: SQLAlchemyUnitOfWork(session_factory)
    _truncate(postgres_engine)


def _truncate(engine: Engine) -> None:
    table_names = ", ".join(
        f'"{table.name}"'
        for table in reversed(Base.metadata.sorted_tables)
    )
    with engine.begin() as connection:
        connection.execute(
            text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
        )
