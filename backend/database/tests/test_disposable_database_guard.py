"""Fail-closed tests for destructive PostgreSQL qualification identity."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from backend.database.disposable import (
    DISPOSABLE_MARKER_SCHEMA,
    DisposableDatabaseError,
    require_disposable_database,
)


@dataclass
class _Mappings:
    marker: dict[str, str] | None

    def one_or_none(self):
        return self.marker


@dataclass
class _Result:
    marker: dict[str, str] | None

    def mappings(self):
        return _Mappings(self.marker)


class _Connection:
    def __init__(self, database_name: str, marker: dict[str, str] | None) -> None:
        self.database_name = database_name
        self.marker = marker

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def scalar(self, _statement):
        return self.database_name

    def execute(self, _statement):
        return _Result(self.marker)


class _Engine:
    def __init__(self, database_name: str, marker: dict[str, str] | None = None) -> None:
        self.database_name = database_name
        self.marker = marker
        self.connect_calls = 0

    def connect(self):
        self.connect_calls += 1
        return _Connection(self.database_name, self.marker)


@pytest.mark.parametrize("database_name", ["reagent_local_v01", "ProjectDB", "reagent"])
def test_protected_persistent_databases_fail_before_connection(database_name: str) -> None:
    engine = _Engine(database_name)
    with pytest.raises(DisposableDatabaseError, match="protected persistent"):
        require_disposable_database(
            engine,  # type: ignore[arg-type]
            database_url=f"postgresql://127.0.0.1:5432/{database_name}",
            expected_identity="a" * 32,
        )
    assert engine.connect_calls == 0


def test_name_that_merely_contains_test_is_not_disposable() -> None:
    engine = _Engine("important_test_database")
    with pytest.raises(DisposableDatabaseError, match="generated disposable"):
        require_disposable_database(
            engine,  # type: ignore[arg-type]
            database_url="postgresql://127.0.0.1:5432/important_test_database",
            expected_identity="a" * 32,
        )
    assert engine.connect_calls == 0


def test_generated_database_requires_exact_persisted_marker_identity() -> None:
    database_name = "reagent_qualification_" + "b" * 32
    identity = "c" * 32
    engine = _Engine(
        database_name,
        {
            "schema_version": DISPOSABLE_MARKER_SCHEMA,
            "database_name": database_name,
            "identity": identity,
        },
    )

    result = require_disposable_database(
        engine,  # type: ignore[arg-type]
        database_url=f"postgresql+psycopg://127.0.0.1:5432/{database_name}",
        expected_identity=identity,
    )

    assert result.database_name == database_name
    assert result.identity == identity
    assert engine.connect_calls == 1


def test_generated_database_rejects_mismatched_marker() -> None:
    database_name = "reagent_qualification_" + "d" * 32
    engine = _Engine(
        database_name,
        {
            "schema_version": DISPOSABLE_MARKER_SCHEMA,
            "database_name": database_name,
            "identity": "e" * 32,
        },
    )
    with pytest.raises(DisposableDatabaseError, match="identity does not match"):
        require_disposable_database(
            engine,  # type: ignore[arg-type]
            database_url=f"postgresql://127.0.0.1:5432/{database_name}",
            expected_identity="f" * 32,
        )
