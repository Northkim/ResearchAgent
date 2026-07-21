"""PostgreSQL engine and session factories kept at the adapter boundary."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import Session, sessionmaker


def normalize_postgres_url(database_url: str) -> str:
    """Pin PostgreSQL URLs to the psycopg 3 SQLAlchemy dialect."""

    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )
    if database_url.startswith("postgres://"):
        return database_url.replace(
            "postgres://",
            "postgresql+psycopg://",
            1,
        )
    raise ValueError("ReAgent database URL must use PostgreSQL")


def create_postgres_engine(
    database_url: str,
    *,
    echo: bool = False,
    pool_pre_ping: bool = True,
) -> Engine:
    return create_engine(
        normalize_postgres_url(database_url),
        echo=echo,
        pool_pre_ping=pool_pre_ping,
    )


def create_async_postgres_engine(
    database_url: str,
    *,
    echo: bool = False,
    pool_pre_ping: bool = True,
) -> AsyncEngine:
    """Create the future API/worker async engine using the same psycopg driver."""

    return create_async_engine(
        normalize_postgres_url(database_url),
        echo=echo,
        pool_pre_ping=pool_pre_ping,
    )


def create_session_factory(engine: Engine) -> Callable[[], Session]:
    """Return sync sessions matching the frozen synchronous repository ports."""

    return sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )
