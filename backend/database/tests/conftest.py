"""PostgreSQL test composition; requires an explicitly provided test database."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import Engine, text

from backend.database import (
    SQLAlchemyUnitOfWork,
    create_postgres_engine,
    create_session_factory,
)
from backend.database.orm import Base


@pytest.fixture(scope="session")
def postgres_engine() -> Iterator[Engine]:
    database_url = os.environ.get("REAGENT_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("REAGENT_TEST_DATABASE_URL is required for PostgreSQL tests")
    engine = create_postgres_engine(database_url)
    with engine.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    if revision != "20260806_0015":
        engine.dispose()
        pytest.fail(
            "PostgreSQL test database must be migrated to revision 20260806_0015"
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
