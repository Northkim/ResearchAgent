"""Run controlled browser qualification against one generated PostgreSQL database."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

from backend.database import create_postgres_engine
from backend.database.disposable import (
    DISPOSABLE_DATABASE_PREFIX,
    DISPOSABLE_MARKER_SCHEMA,
    DISPOSABLE_MARKER_TABLE,
    DisposableDatabaseError,
    require_disposable_database,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPECS = (
    "tests/e2e/local-v0-1.spec.ts",
    "tests/e2e/h1-product-journey.spec.ts",
    "tests/e2e/f1f-product-width.spec.ts",
)


def _admin_url() -> URL:
    raw = os.environ.get("REAGENT_TEST_ADMIN_DATABASE_URL", "")
    if not raw:
        raise DisposableDatabaseError(
            "REAGENT_TEST_ADMIN_DATABASE_URL must explicitly select loopback postgres or template1"
        )
    try:
        url = make_url(raw)
    except Exception as error:
        raise DisposableDatabaseError("test database admin URL is malformed") from error
    if url.get_backend_name() != "postgresql":
        raise DisposableDatabaseError("test database admin URL must use PostgreSQL")
    if url.host not in {None, "127.0.0.1", "localhost", "::1"}:
        raise DisposableDatabaseError("test database admin URL must be loopback-only")
    if (url.database or "").casefold() not in {"postgres", "template1"}:
        raise DisposableDatabaseError(
            "test database admin URL must select postgres or template1"
        )
    return url


def _render(url: URL) -> str:
    return url.render_as_string(hide_password=False)


@contextmanager
def _disposable_database() -> Iterator[tuple[str, str, str]]:
    admin_url = _admin_url()
    identity = uuid.uuid4().hex
    database_name = DISPOSABLE_DATABASE_PREFIX + uuid.uuid4().hex
    database_url = _render(admin_url.set(database=database_name))
    admin_engine = create_engine(_render(admin_url), isolation_level="AUTOCOMMIT")
    created = False
    try:
        with admin_engine.connect() as connection:
            connection.execute(text(f"CREATE DATABASE {database_name}"))
        created = True
        target_engine = create_postgres_engine(database_url)
        try:
            with target_engine.begin() as connection:
                connection.execute(text(f"""
                    CREATE TABLE {DISPOSABLE_MARKER_TABLE} (
                        singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
                        schema_version text NOT NULL,
                        database_name text NOT NULL,
                        identity text NOT NULL,
                        created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                connection.execute(
                    text(f"""
                        INSERT INTO {DISPOSABLE_MARKER_TABLE}
                          (singleton, schema_version, database_name, identity)
                        VALUES (true, :schema_version, :database_name, :identity)
                    """),
                    {
                        "schema_version": DISPOSABLE_MARKER_SCHEMA,
                        "database_name": database_name,
                        "identity": identity,
                    },
                )
            require_disposable_database(
                target_engine,
                database_url=database_url,
                expected_identity=identity,
            )
        finally:
            target_engine.dispose()
        print(f"QUALIFICATION_DATABASE_CREATED={database_name}", flush=True)
        yield database_url, database_name, identity
    finally:
        if created:
            target_engine = create_postgres_engine(database_url)
            try:
                require_disposable_database(
                    target_engine,
                    database_url=database_url,
                    expected_identity=identity,
                )
            finally:
                target_engine.dispose()
            with admin_engine.connect() as connection:
                connection.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname=:database_name AND pid <> pg_backend_pid()"
                    ),
                    {"database_name": database_name},
                )
                connection.execute(text(f"DROP DATABASE {database_name}"))
            print(f"QUALIFICATION_DATABASE_DROPPED={database_name}", flush=True)
        admin_engine.dispose()


def _copy_frontend(target: Path) -> None:
    source = REPO_ROOT / "frontend"
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns(
            ".next", "node_modules", "playwright-report", "test-results"
        ),
    )
    shutil.copytree(
        source / "node_modules",
        target / "node_modules",
        copy_function=os.link,
        symlinks=True,
    )


def _migrate(database_url: str, environment: dict[str, str]) -> None:
    migration_environment = {**environment, "REAGENT_DATABASE_URL": database_url}
    subprocess.run(
        ["conda", "run", "--no-capture-output", "-n", "reagent-dev", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=migration_environment,
        check=True,
    )


def _controlled_e2e(specs: tuple[str, ...]) -> int:
    with _disposable_database() as (database_url, database_name, identity):
        with tempfile.TemporaryDirectory(
            prefix="reagent-isolated-qualification-", dir=REPO_ROOT.parent
        ) as root_text:
            root = Path(root_text)
            runtime = root / "runtime"
            frontend = root / "frontend"
            _copy_frontend(frontend)
            # The published Literature Capsule currently uses the frozen
            # loopback defaults after generic mode projection. Qualification
            # therefore requires the manual instance to be stopped first;
            # dev-start fails closed if either port is occupied.
            backend_port = 8000
            frontend_port = 3000
            environment = {
                **os.environ,
                "REAGENT_AUTOMATED_QUALIFICATION": "1",
                "REAGENT_DATABASE_URL": database_url,
                "REAGENT_TEST_DATABASE_URL": database_url,
                "REAGENT_TEST_DATABASE_IDENTITY": identity,
                "REAGENT_LOCAL_RUNTIME_DIR": str(runtime),
                "REAGENT_FRONTEND_ROOT": str(frontend),
                "REAGENT_BACKEND_PORT": str(backend_port),
                "REAGENT_FRONTEND_PORT": str(frontend_port),
                "REAGENT_E2E_BACKEND_URL": f"http://127.0.0.1:{backend_port}",
                "REAGENT_E2E_BASE_URL": f"http://127.0.0.1:{frontend_port}",
                "REAGENT_E2E_QUALIFICATION_IDENTITY": identity,
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            _migrate(database_url, environment)
            started = False
            try:
                try:
                    subprocess.run(
                        ["make", "controlled-start"],
                        cwd=REPO_ROOT,
                        env=environment,
                        check=True,
                    )
                except subprocess.CalledProcessError:
                    build_log = runtime / "frontend-build.log"
                    if build_log.is_file():
                        print("--- isolated frontend build log ---", file=sys.stderr)
                        print(build_log.read_text(encoding="utf-8")[-6000:], file=sys.stderr)
                    raise
                started = True
                executable = REPO_ROOT / "frontend/node_modules/.bin/playwright"
                result = subprocess.run(
                    [str(executable), "test", *specs],
                    cwd=REPO_ROOT / "frontend",
                    env=environment,
                    check=False,
                )
                if result.returncode != 0:
                    backend_log = runtime / "backend.log"
                    if backend_log.is_file():
                        print("--- isolated backend log ---", file=sys.stderr)
                        print(backend_log.read_text(encoding="utf-8")[-8000:], file=sys.stderr)
                    return result.returncode
                target_engine = create_postgres_engine(database_url)
                try:
                    require_disposable_database(
                        target_engine,
                        database_url=database_url,
                        expected_identity=identity,
                    )
                    with target_engine.connect() as connection:
                        markers = connection.execute(
                            text(
                                "SELECT name, count(*) FROM local_projects "
                                "WHERE name IN ('H1 controlled product journey', "
                                "'F1F browser product width') GROUP BY name ORDER BY name"
                            )
                        ).all()
                    expected = {
                        "F1F browser product width": 1,
                        "H1 controlled product journey": 1,
                    }
                    if dict(markers) != expected:
                        raise RuntimeError(
                            "controlled E2E Projects were not isolated in the qualification database"
                        )
                finally:
                    target_engine.dispose()
                print(f"QUALIFICATION_PROJECT_DATABASE={database_name}", flush=True)
                return 0
            finally:
                if started:
                    subprocess.run(
                        ["make", "stop"],
                        cwd=REPO_ROOT,
                        env=environment,
                        check=True,
                    )


def _backend_tests(paths: tuple[str, ...]) -> int:
    with _disposable_database() as (database_url, database_name, identity):
        environment = {
            **os.environ,
            "REAGENT_DATABASE_URL": database_url,
            "REAGENT_TEST_DATABASE_URL": database_url,
            "REAGENT_TEST_DATABASE_IDENTITY": identity,
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        _migrate(database_url, environment)
        result = subprocess.run(
            [
                "conda", "run", "--no-capture-output", "-n", "reagent-dev",
                "pytest", "-q", *(paths or ("backend",)),
            ],
            cwd=REPO_ROOT,
            env=environment,
            check=False,
        )
        if result.returncode == 0:
            print(f"QUALIFICATION_TEST_DATABASE={database_name}", flush=True)
        return result.returncode


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    controlled = subparsers.add_parser("controlled-e2e")
    controlled.add_argument("--spec", action="append", default=[])
    backend = subparsers.add_parser("backend-tests")
    backend.add_argument("paths", nargs="*")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "controlled-e2e":
            specs = tuple(arguments.spec) or DEFAULT_SPECS
            return _controlled_e2e(specs)
        if arguments.command == "backend-tests":
            return _backend_tests(tuple(arguments.paths))
    except (DisposableDatabaseError, OSError, subprocess.SubprocessError) as error:
        print(f"Isolated qualification failed: {error}", file=sys.stderr)
        return 2
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
