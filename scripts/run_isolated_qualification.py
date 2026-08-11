"""Run controlled browser qualification against one generated PostgreSQL database."""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import urllib.request
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

# This file is an executable script; make repository imports deterministic
# before importing backend modules.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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
from scripts.owner_runtime import (
    CONFIG_SCHEMA_VERSION,
    OWNER_PROFILE,
    OwnerConfigStore,
    OwnerDatabaseConfig,
    OwnerEndpointConfig,
    OwnerProviderConfig,
    OwnerRuntimeConfig,
    owner_runtime_directory,
)

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


def _available_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _controlled_e2e(specs: tuple[str, ...]) -> int:
    with _disposable_database() as (database_url, database_name, identity):
        with tempfile.TemporaryDirectory(
            prefix="reagent-isolated-qualification-", dir=REPO_ROOT.parent
        ) as root_text:
            root = Path(root_text)
            runtime = root / "runtime"
            frontend = root / "frontend"
            _copy_frontend(frontend)
            # The generic launcher projects this exact loopback origin into
            # the Capsule environment. Automated qualification therefore does
            # not stop or share ports with an owner's manual local runtime.
            backend_port = _available_loopback_port()
            frontend_port = _available_loopback_port()
            while frontend_port == backend_port:
                frontend_port = _available_loopback_port()
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
                "REAGENT_LOCAL_BASE_URL": f"http://127.0.0.1:{backend_port}",
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


def _read_process_environment(pid: int) -> str:
    result = subprocess.run(
        ["ps", "eww", "-p", str(pid)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _owner_runtime_smoke() -> int:
    """Exercise the literal fresh-shell Make contract with isolated authorities."""

    sentinel = "owner-openalex-secret-sentinel"
    with _disposable_database() as (database_url, database_name, identity):
        with tempfile.TemporaryDirectory(
            prefix="reagent-owner-runtime-qualification-", dir=REPO_ROOT.parent
        ) as root_text:
            root = Path(root_text)
            xdg_root = root / "xdg"
            fake_bin = root / "bin"
            fake_bin.mkdir(mode=0o700)
            fake_security = fake_bin / "security"
            fake_security.write_text(
                "#!/bin/sh\n"
                "if [ \"$1\" = find-generic-password ]; then\n"
                "  case \" $* \" in *\" -w \"*) "
                f"printf '%s\\n' '{sentinel}' ;; esac\n"
                "  exit 0\n"
                "fi\n"
                "exit 1\n",
                encoding="utf-8",
            )
            fake_security.chmod(0o700)
            backend_port = _available_loopback_port()
            frontend_port = _available_loopback_port()
            while frontend_port == backend_port:
                frontend_port = _available_loopback_port()
            parsed = make_url(database_url)
            config = OwnerRuntimeConfig(
                schema_version=CONFIG_SCHEMA_VERSION,
                profile=OWNER_PROFILE,
                database=OwnerDatabaseConfig(
                    host="127.0.0.1",
                    port=parsed.port or 5432,
                    database=database_name,
                    user=parsed.username or "",
                ),
                backend=OwnerEndpointConfig("127.0.0.1", backend_port),
                frontend=OwnerEndpointConfig("127.0.0.1", frontend_port),
                providers=OwnerProviderConfig(openalex_enabled=True),
            )
            config_path = xdg_root / "reagent" / "config.toml"
            OwnerConfigStore(config_path, repository_root=REPO_ROOT).write(config)
            runtime = owner_runtime_directory(config_path)
            environment = {
                key: value
                for key, value in os.environ.items()
                if not key.startswith("REAGENT_")
                and key not in {
                    "OPENALEX_API_KEY",
                    "OPENAI_API_KEY",
                    "ANTHROPIC_API_KEY",
                }
            }
            environment.update(
                {
                    "PATH": str(fake_bin) + os.pathsep + environment.get("PATH", ""),
                    "XDG_CONFIG_HOME": str(xdg_root),
                    "PYTHONDONTWRITEBYTECODE": "1",
                    # Prevent this qualification's `make stop` from touching a
                    # separately running developer/controlled runtime.
                    "REAGENT_LOCAL_RUNTIME_DIR": str(root / "unused-dev-runtime"),
                }
            )
            _migrate(database_url, environment)
            target_engine = create_postgres_engine(database_url)
            try:
                require_disposable_database(
                    target_engine,
                    database_url=database_url,
                    expected_identity=identity,
                )
                with target_engine.connect() as connection:
                    project_count_before = connection.scalar(text("SELECT count(*) FROM local_projects"))
            finally:
                target_engine.dispose()

            def invoke(target: str) -> subprocess.CompletedProcess[str]:
                result = subprocess.run(
                    ["make", target],
                    cwd=REPO_ROOT,
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if sentinel in result.stdout + result.stderr:
                    raise RuntimeError("owner runtime secret appeared in command output")
                if result.returncode != 0:
                    print(result.stdout, file=sys.stderr)
                    print(result.stderr, file=sys.stderr)
                    raise subprocess.CalledProcessError(result.returncode, result.args)
                return result

            started = False
            try:
                for attempt in range(2):
                    result = invoke("owner-start")
                    started = True
                    if "Mode: owner-local real research" not in result.stdout:
                        raise RuntimeError("owner-start did not report owner real mode")
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{backend_port}/ready", timeout=3
                    ) as response:
                        if response.status != 200:
                            raise RuntimeError("owner Backend was not ready")
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{frontend_port}/projects", timeout=3
                    ) as response:
                        if response.status != 200:
                            raise RuntimeError("owner Frontend was not ready")
                    backend_pid = int((runtime / "backend.pid").read_text().strip())
                    frontend_pid = int((runtime / "frontend.pid").read_text().strip())
                    if sentinel not in _read_process_environment(backend_pid):
                        raise RuntimeError("owner Backend did not receive the Keychain credential")
                    if sentinel in _read_process_environment(frontend_pid):
                        raise RuntimeError("owner Frontend inherited the Provider credential")
                    for path in (config_path, runtime / "backend.log", runtime / "frontend.log"):
                        if path.is_file() and sentinel in path.read_text(
                            encoding="utf-8", errors="replace"
                        ):
                            raise RuntimeError(f"owner credential leaked into {path.name}")
                    invoke("stop")
                    started = False
                    if attempt == 0:
                        print("OWNER_RUNTIME_RESTART_PHASE=READY", flush=True)
            finally:
                if started:
                    invoke("stop")
                shutil.rmtree(runtime, ignore_errors=True)

            target_engine = create_postgres_engine(database_url)
            try:
                require_disposable_database(
                    target_engine,
                    database_url=database_url,
                    expected_identity=identity,
                )
                with target_engine.connect() as connection:
                    project_count_after = connection.scalar(text("SELECT count(*) FROM local_projects"))
            finally:
                target_engine.dispose()
            if project_count_after != project_count_before:
                raise RuntimeError("owner runtime smoke changed qualification Project count")
            print(f"OWNER_RUNTIME_DATABASE={database_name}", flush=True)
            print("OWNER_RUNTIME_FRESH_SHELL_EXPORTS=NONE", flush=True)
            print("OWNER_RUNTIME_RESTART=PASS", flush=True)
            print("OWNER_RUNTIME_SECRET_ISOLATION=PASS", flush=True)
            return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    controlled = subparsers.add_parser("controlled-e2e")
    controlled.add_argument("--spec", action="append", default=[])
    backend = subparsers.add_parser("backend-tests")
    backend.add_argument("paths", nargs="*")
    subparsers.add_parser("owner-runtime-smoke")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "controlled-e2e":
            specs = tuple(arguments.spec) or DEFAULT_SPECS
            return _controlled_e2e(specs)
        if arguments.command == "backend-tests":
            return _backend_tests(tuple(arguments.paths))
        if arguments.command == "owner-runtime-smoke":
            return _owner_runtime_smoke()
    except (DisposableDatabaseError, OSError, subprocess.SubprocessError) as error:
        print(f"Isolated qualification failed: {error}", file=sys.stderr)
        return 2
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
