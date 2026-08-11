"""Fail-closed identity checks for destructive PostgreSQL qualification databases."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass

from sqlalchemy import Engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

DISPOSABLE_DATABASE_PREFIX = "reagent_qualification_"
DISPOSABLE_DATABASE_NAME = re.compile(r"^reagent_qualification_[0-9a-f]{32}$")
DISPOSABLE_IDENTITY = re.compile(r"^[0-9a-f]{32}$")
DISPOSABLE_MARKER_TABLE = "reagent_disposable_database_identity"
DISPOSABLE_MARKER_SCHEMA = "reagent.disposable-database/v0.1"
PROTECTED_DATABASE_NAMES = frozenset({"projectdb", "reagent", "reagent_local_v01"})


class DisposableDatabaseError(ValueError):
    """A bounded safety failure raised before destructive test mutation."""


@dataclass(frozen=True, slots=True)
class DisposableDatabaseIdentity:
    database_name: str
    identity: str


def configured_database_name(database_url: str) -> str:
    """Return one bounded database name without exposing the rest of its URL."""

    try:
        parsed = make_url(database_url)
    except Exception as error:
        raise DisposableDatabaseError("test database URL is malformed") from error
    if parsed.get_backend_name() != "postgresql" or not parsed.database:
        raise DisposableDatabaseError("test database must be a named PostgreSQL database")
    return parsed.database


def require_disposable_database(
    engine: Engine,
    *,
    database_url: str,
    expected_identity: str | None,
) -> DisposableDatabaseIdentity:
    """Validate an exact generated marker before any destructive fixture runs."""

    configured_name = configured_database_name(database_url)
    if configured_name.casefold() in PROTECTED_DATABASE_NAMES:
        raise DisposableDatabaseError("protected persistent database is not disposable")
    if DISPOSABLE_DATABASE_NAME.fullmatch(configured_name) is None:
        raise DisposableDatabaseError(
            "destructive tests require a generated disposable database name"
        )
    if expected_identity is None or DISPOSABLE_IDENTITY.fullmatch(expected_identity) is None:
        raise DisposableDatabaseError(
            "destructive tests require an explicit generated database identity"
        )

    try:
        with engine.connect() as connection:
            actual_name = connection.scalar(text("SELECT current_database()"))
            marker = connection.execute(
                text(
                    f"SELECT schema_version, database_name, identity "
                    f"FROM {DISPOSABLE_MARKER_TABLE} WHERE singleton"
                )
            ).mappings().one_or_none()
    except SQLAlchemyError as error:
        raise DisposableDatabaseError(
            "disposable database marker is absent or unreadable"
        ) from error

    if actual_name != configured_name:
        raise DisposableDatabaseError("connected database identity does not match its URL")
    if marker is None:
        raise DisposableDatabaseError("disposable database marker is absent")
    if marker["schema_version"] != DISPOSABLE_MARKER_SCHEMA:
        raise DisposableDatabaseError("disposable database marker schema is invalid")
    if marker["database_name"] != actual_name:
        raise DisposableDatabaseError("disposable database marker names another database")
    if marker["identity"] != expected_identity:
        raise DisposableDatabaseError("disposable database identity does not match")
    return DisposableDatabaseIdentity(database_name=actual_name, identity=expected_identity)


def validate_environment() -> DisposableDatabaseIdentity:
    """CLI entry used by startup and Playwright before product mutation."""

    from backend.database import create_postgres_engine

    database_url = os.environ.get("REAGENT_TEST_DATABASE_URL", "")
    runtime_url = os.environ.get("REAGENT_DATABASE_URL", "")
    if not database_url or not runtime_url:
        raise DisposableDatabaseError(
            "automated qualification requires explicit runtime and test database URLs"
        )
    if configured_database_name(database_url) != configured_database_name(runtime_url):
        raise DisposableDatabaseError(
            "automated qualification runtime and destructive-test databases differ"
        )
    test_engine = create_postgres_engine(database_url)
    runtime_engine = create_postgres_engine(runtime_url)
    try:
        identity = require_disposable_database(
            test_engine,
            database_url=database_url,
            expected_identity=os.environ.get("REAGENT_TEST_DATABASE_IDENTITY"),
        )
        runtime_identity = require_disposable_database(
            runtime_engine,
            database_url=runtime_url,
            expected_identity=os.environ.get("REAGENT_TEST_DATABASE_IDENTITY"),
        )
        if runtime_identity != identity:
            raise DisposableDatabaseError(
                "automated qualification runtime and test identities differ"
            )
        return identity
    finally:
        test_engine.dispose()
        runtime_engine.dispose()


def main() -> int:
    try:
        identity = validate_environment()
    except DisposableDatabaseError as error:
        print(f"Automated qualification database rejected: {error}", file=sys.stderr)
        return 2
    print(f"Disposable qualification database verified: {identity.database_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
