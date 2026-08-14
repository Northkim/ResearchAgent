"""Run controlled browser qualification against one generated PostgreSQL database."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
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
B0_SPEC = "tests/e2e/b0-controlled-runtime.spec.ts"


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
def _disposable_database(
    *, database_prefix: str = DISPOSABLE_DATABASE_PREFIX,
    identity: str | None = None,
) -> Iterator[tuple[str, str, str]]:
    admin_url = _admin_url()
    identity = identity or uuid.uuid4().hex
    if not database_prefix.startswith(DISPOSABLE_DATABASE_PREFIX):
        raise DisposableDatabaseError("disposable database prefix is not approved")
    database_name = database_prefix + identity
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
                exists = connection.scalar(
                    text("SELECT EXISTS (SELECT 1 FROM pg_database WHERE datname=:database_name)"),
                    {"database_name": database_name},
                )
                if exists:
                    raise DisposableDatabaseError(
                        "disposable database still exists after DROP DATABASE"
                    )
            print(f"QUALIFICATION_DATABASE_DROPPED={database_name}", flush=True)
        admin_engine.dispose()


def _copy_frontend(target: Path) -> None:
    def link_or_copy(source: str, destination: str) -> str | None:
        try:
            return os.link(source, destination)
        except OSError as error:
            if error.errno != errno.EXDEV:
                raise
            return shutil.copy2(source, destination)

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
        copy_function=link_or_copy,
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


def _b0_child_environment() -> dict[str, str]:
    sensitive = ("API_KEY", "CREDENTIAL", "DATABASE_URL", "PASSWORD", "SECRET", "TOKEN")
    sensitive_prefixes = ("AWS_", "AZURE_", "GH_", "GITHUB_", "GOOGLE_", "HF_", "PG")
    return {
        key: value for key, value in os.environ.items()
        if not key.startswith("REAGENT_")
        and not key.startswith(sensitive_prefixes)
        and not any(fragment in key.upper() for fragment in sensitive)
        and key not in {"GPG_AGENT_INFO", "SSH_AUTH_SOCK"}
    }


def _loopback_reachable(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.25):
            return True
    except OSError:
        return False


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def _b0_process_pids(runtime: Path) -> dict[str, int]:
    result = {}
    for name in ("backend", "frontend"):
        pid_path, identity_path = runtime / f"{name}.pid", runtime / f"{name}.identity"
        if not pid_path.exists() and not identity_path.exists():
            continue
        if not pid_path.is_file() or not identity_path.is_file():
            raise RuntimeError(f"B0 {name} process identity is incomplete")
        raw = pid_path.read_text(encoding="utf-8").strip()
        if not raw.isdigit(): raise RuntimeError(f"B0 {name} PID is invalid")
        pid = int(raw)
        if not _process_alive(pid): raise RuntimeError(f"B0 {name} process is not alive")
        actual = subprocess.run(["ps", "-p", str(pid), "-o", "lstart="],
            capture_output=True, text=True, check=False).stdout.strip()
        if actual != identity_path.read_text(encoding="utf-8").strip():
            raise RuntimeError(f"B0 {name} process identity does not match")
        result[name] = pid
    return result


_B0_CHECKS = {
    "PLAYWRIGHT_PACKAGE_PRESENT": "repository Playwright executable is present",
    "BROWSER_BINARY_PRESENT": "repository-declared Playwright browser launches its test body",
    "CONTROLLED_BACKEND_REACHABLE": "GET dynamic loopback Backend /ready returns 200",
    "CONTROLLED_FRONTEND_REACHABLE": "GET dynamic loopback Frontend /projects returns 200",
    "DATASET_VERIFIED_DISPOSABLE": "B0 database guard, run identity, Project, and Workspace marker agree",
    "SCREENSHOT_CAPTURE_PASS": "three PNG files are readable, non-empty, and match viewport dimensions",
    "TEARDOWN_PASS": "B0 processes, ports, database, Workspace, screenshots, and root are absent",
}
_B0_SCREENSHOTS = {
    "projects-workflows__1440x900__controlled-states__fold.png": (1440, 900),
    "projects-workflows__1280x800__controlled-states__fold.png": (1280, 800),
    "projects-workflows__390x844__controlled-states__fold.png": (390, 844),
}


def _workspace_summary(workspace: Path) -> tuple[tuple[str, int, str], ...]:
    summary = []
    for path in sorted(workspace.rglob("*")):
        if path.is_symlink() or not path.is_file():
            if path.is_dir() and not path.is_symlink():
                summary.append((path.relative_to(workspace).as_posix() + "/", 0, "DIRECTORY"))
                continue
            raise RuntimeError(f"unsupported entry in B0 Workspace: {path}")
        body = path.read_bytes()
        summary.append((path.relative_to(workspace).as_posix(), len(body),
                        hashlib.sha256(body).hexdigest()))
    return tuple(summary)


def _screenshot_evidence(root: Path) -> str:
    if {item.name for item in root.iterdir()} != set(_B0_SCREENSHOTS):
        raise RuntimeError("B0 screenshot set does not exactly match the three viewports")
    evidence = []
    for name, expected_dimensions in _B0_SCREENSHOTS.items():
        body = (root / name).read_bytes()
        if len(body) < 24 or body[:8] != b"\x89PNG\r\n\x1a\n" or body[12:16] != b"IHDR":
            raise RuntimeError(f"B0 screenshot is not a readable PNG: {name}")
        dimensions = struct.unpack(">II", body[16:24])
        if dimensions != expected_dimensions:
            raise RuntimeError(f"B0 screenshot dimensions mismatch: {name}: {dimensions}")
        evidence.append(f"{name}:size={len(body)}:dimensions={dimensions}")
    return ";".join(evidence)


def _b0_browser_qualification() -> int:
    states = {name: {"status": "FAIL", "evidence": "none", "check": check,
                     "limitation": "not reached"} for name, check in _B0_CHECKS.items()}

    def passed(name: str, evidence: str) -> None:
        states[name].update(status="PASS", evidence=evidence, limitation="none")
    run_id = uuid.uuid4().hex
    repository_playwright = REPO_ROOT / "frontend/node_modules/.bin/playwright"
    failure: Exception | None = None
    database_absent = runtime_clean = False
    root: Path | None = None
    try:
        if not repository_playwright.is_file() or not os.access(repository_playwright, os.X_OK):
            raise RuntimeError("repository Playwright package executable is unavailable")
        passed("PLAYWRIGHT_PACKAGE_PRESENT", str(repository_playwright))
        with _disposable_database(identity=run_id) as (
            database_url, database_name, identity,
        ):
            qualification = tempfile.TemporaryDirectory(prefix=f"reagent-b0-{run_id}-")
            root = Path(qualification.name)
            runtime, frontend = root / "runtime", root / "frontend"
            workspace, audit = root / "workspace", root / "audit"
            screenshots = root / "screenshots"
            fixture_manifest = audit / "fixtures.json"
            launch_marker = audit / "playwright-launched"
            marker = workspace / "B0_DISPOSABLE_WORKSPACE"
            backend_port = frontend_port = 0
            environment: dict[str, str] | None = None
            started = False
            workspace_before: tuple[tuple[str, int, str], ...] | None = None
            cleanup_errors: list[str] = []
            try:
                if root.resolve().is_relative_to(REPO_ROOT.resolve()):
                    raise RuntimeError("B0 qualification root must be outside the repository")
                for directory in (audit, screenshots, workspace, root / "home", root / "xdg"):
                    directory.mkdir(mode=0o700)
                marker.write_text(f"B0_DISPOSABLE_WORKSPACE\nrun_id={run_id}\n", encoding="utf-8")
                _copy_frontend(frontend)
                playwright = frontend / "node_modules/.bin/playwright"
                playwright_test = frontend / "node_modules/@playwright/test"
                config = frontend / "playwright.config.ts"
                spec = frontend / B0_SPEC
                frontend_root = frontend.resolve()
                if any(not path.resolve().is_relative_to(frontend_root)
                       for path in (playwright, playwright_test, config, spec)):
                    raise RuntimeError("B0 Playwright runtime identity escaped the temporary frontend")
                if (not playwright.is_file() or not os.access(playwright, os.X_OK)
                        or not playwright_test.is_dir() or not config.is_file() or not spec.is_file()):
                    raise RuntimeError("B0 temporary Playwright runtime identity is incomplete")
                backend_port = _available_loopback_port()
                frontend_port = _available_loopback_port()
                while frontend_port == backend_port:
                    frontend_port = _available_loopback_port()
                backend_url = f"http://127.0.0.1:{backend_port}"
                frontend_url = f"http://127.0.0.1:{frontend_port}"
                environment = {
                    **_b0_child_environment(),
                    "REAGENT_AUTOMATED_QUALIFICATION": "1",
                    "REAGENT_DATABASE_URL": database_url,
                    "REAGENT_TEST_DATABASE_URL": database_url,
                    "REAGENT_TEST_DATABASE_IDENTITY": identity,
                    "REAGENT_E2E_QUALIFICATION_IDENTITY": run_id,
                    "REAGENT_LOCAL_RUNTIME_DIR": str(runtime),
                    "REAGENT_FRONTEND_ROOT": str(frontend),
                    "REAGENT_BACKEND_PORT": str(backend_port),
                    "REAGENT_FRONTEND_PORT": str(frontend_port),
                    "REAGENT_E2E_BACKEND_URL": backend_url,
                    "REAGENT_E2E_BASE_URL": frontend_url,
                    "REAGENT_LOCAL_BASE_URL": backend_url,
                    "REAGENT_B0_FIXTURE_MANIFEST": str(fixture_manifest),
                    "REAGENT_B0_BROWSER_LAUNCH_MARKER": str(launch_marker),
                    "REAGENT_B0_SCREENSHOT_DIR": str(screenshots),
                    "HOME": str(root / "home"),
                    "XDG_CONFIG_HOME": str(root / "xdg"),
                    "NPM_CONFIG_CACHE": str(root / "npm-cache"),
                    "PYTHONDONTWRITEBYTECODE": "1",
                }
                _migrate(database_url, environment)
                subprocess.run(
                    ["make", "controlled-start"], cwd=REPO_ROOT,
                    env=environment, check=True,
                )
                started = True
                with urllib.request.urlopen(backend_url + "/ready", timeout=3) as response:
                    if response.status != 200:
                        raise RuntimeError("controlled Backend readiness failed")
                passed("CONTROLLED_BACKEND_REACHABLE", backend_url + "/ready")
                with urllib.request.urlopen(frontend_url + "/projects", timeout=3) as response:
                    if response.status != 200:
                        raise RuntimeError("controlled Frontend readiness failed")
                passed("CONTROLLED_FRONTEND_REACHABLE", frontend_url + "/projects")
                subprocess.run([
                    "conda", "run", "--no-capture-output", "-n", "reagent-dev", "python",
                    "-m", "scripts.b0_controlled_fixtures", "--api-url", backend_url,
                    "--run-id", run_id, "--manifest", str(fixture_manifest),
                ], cwd=REPO_ROOT, env=environment, check=True)
                fixture = json.loads(fixture_manifest.read_text(encoding="utf-8"))
                target_engine = create_postgres_engine(database_url)
                try:
                    require_disposable_database(target_engine, database_url=database_url,
                                                expected_identity=run_id)
                    with target_engine.connect() as connection:
                        project_count = connection.scalar(text(
                            "SELECT count(*) FROM local_projects WHERE project_id=:project_id"
                        ), {"project_id": fixture["project_id"]})
                finally:
                    target_engine.dispose()
                if (fixture.get("run_id") != run_id or project_count != 1 or
                        marker.read_text(encoding="utf-8") !=
                        f"B0_DISPOSABLE_WORKSPACE\nrun_id={run_id}\n"):
                    raise RuntimeError("B0 disposable dataset identities do not agree")
                workspace_before = _workspace_summary(workspace)
                passed(
                    "DATASET_VERIFIED_DISPOSABLE",
                    f"database={database_name};run_id={run_id};workspace={workspace_before}",
                )
                result = subprocess.run([str(playwright), "test", B0_SPEC], cwd=frontend,
                                        env=environment, check=False)
                if _workspace_summary(workspace) != workspace_before:
                    raise RuntimeError("BLOCKED_BROWSER_WORKSPACE_WRITE: "
                                       "WORKSPACE_BROWSER_MUTATION is not NONE")
                print("WORKSPACE_BROWSER_MUTATION=NONE", flush=True)
                if launch_marker.read_text(encoding="utf-8") != f"run_id={run_id}\n":
                    raise RuntimeError("repository-declared Playwright browser did not launch")
                passed("BROWSER_BINARY_PRESENT",
                       "repository-declared Chrome channel entered the Playwright test body")
                if result.returncode != 0:
                    raise RuntimeError(f"B0 Playwright qualification failed: {result.returncode}")
                passed("SCREENSHOT_CAPTURE_PASS", _screenshot_evidence(screenshots))
            except Exception as error:
                failure = error
            finally:
                captured_pids: dict[str, int] = {}
                if environment is not None:
                    try:
                        captured_pids = _b0_process_pids(runtime)
                        if started and set(captured_pids) != {"backend", "frontend"}:
                            cleanup_errors.append("B0 process identities were not both captured")
                    except RuntimeError as error:
                        cleanup_errors.append(str(error))
                    stopped = subprocess.run([str(REPO_ROOT / "scripts/dev-stop.sh")], cwd=REPO_ROOT,
                                             env=environment, check=False)
                    if stopped.returncode != 0:
                        cleanup_errors.append("exact B0 process shutdown failed")
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if (not any(_process_alive(pid) for pid in captured_pids.values())
                            and not any(port and _loopback_reachable(port)
                                        for port in (backend_port, frontend_port))):
                        break
                    time.sleep(0.1)
                surviving = [name for name, pid in captured_pids.items() if _process_alive(pid)]
                if surviving:
                    cleanup_errors.append("B0 processes survived shutdown: " + ",".join(surviving))
                if runtime.exists() and any(
                    (runtime / name).exists() for name in
                    ("backend.pid", "backend.identity", "frontend.pid", "frontend.identity")
                ):
                    cleanup_errors.append("B0 process identity files remain")
                for port, label in ((backend_port, "Backend"), (frontend_port, "Frontend")):
                    if port and _loopback_reachable(port):
                        cleanup_errors.append(f"B0 {label} port remains served")
                for path, label in ((screenshots, "screenshot directory"), (workspace, "Workspace")):
                    if path.exists():
                        shutil.rmtree(path)
                    if path.exists():
                        cleanup_errors.append(f"B0 {label} remains")
                qualification.cleanup()
                if root.exists():
                    cleanup_errors.append("B0 qualification root remains")
                runtime_clean = not cleanup_errors
                if cleanup_errors:
                    cleanup_error = RuntimeError("; ".join(cleanup_errors))
                    failure = cleanup_error if failure is None else RuntimeError(
                        f"{failure}; teardown: {cleanup_error}"
                    )
        database_absent = True
    except Exception as error:
        failure = error if failure is None else failure

    if database_absent and runtime_clean and root is not None and not root.exists():
        passed("TEARDOWN_PASS", "processes stopped; ports closed; database, Workspace, "
               "screenshots, and root absent")
    for state in states.values():
        if state["status"] == "FAIL" and state["limitation"] == "not reached":
            state["limitation"] = "not reached because " + str(
                failure or "an earlier qualification check did not pass"
            )
    for name, state in states.items():
        print(f"{name}={json.dumps(state, sort_keys=True)}", flush=True)
    if failure is not None:
        raise failure
    if any(state["status"] != "PASS" for state in states.values()):
        raise RuntimeError("B0 qualification did not pass all seven states")
    print("B0_CONTROLLED_BROWSER_QUALIFICATION=PASS", flush=True)
    return 0


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
        subprocess.run(
            [
                "conda", "run", "--no-capture-output", "-n", "reagent-dev",
                "alembic", "check",
            ],
            cwd=REPO_ROOT,
            env=environment,
            check=True,
        )
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
            shadow_repo = root / "repository"
            shadow_repo.mkdir(mode=0o700)
            shutil.copy2(REPO_ROOT / "Makefile", shadow_repo / "Makefile")
            shutil.copy2(REPO_ROOT / "alembic.ini", shadow_repo / "alembic.ini")
            os.symlink(REPO_ROOT / "backend", shadow_repo / "backend")
            shadow_scripts = shadow_repo / "scripts"
            shadow_scripts.mkdir()
            for script_name in ("owner_runtime.py", "dev-stop.sh"):
                shutil.copy2(
                    REPO_ROOT / "scripts" / script_name,
                    shadow_scripts / script_name,
                )
            _copy_frontend(shadow_repo / "frontend")
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
            OwnerConfigStore(config_path, repository_root=shadow_repo).write(config)
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
                    cwd=shadow_repo,
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
                    for log_name in ("backend.log", "frontend.log"):
                        log_path = runtime / log_name
                        if log_path.is_file():
                            print(
                                f"--- {log_name} ---\n"
                                + log_path.read_text(
                                    encoding="utf-8", errors="replace"
                                )[-8000:],
                                file=sys.stderr,
                            )
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
    subparsers.add_parser("b0-browser")
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
        if arguments.command == "b0-browser":
            return _b0_browser_qualification()
    except (
        DisposableDatabaseError, OSError, RuntimeError, subprocess.SubprocessError
    ) as error:
        print(f"Isolated qualification failed: {error}", file=sys.stderr)
        return 2
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
