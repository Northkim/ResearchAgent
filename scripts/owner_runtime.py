#!/usr/bin/env python3
"""Secure single-owner configuration and local real-research startup."""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# Direct execution (the Makefile contract) otherwise places only scripts/ on
# sys.path. Add the immutable repository root before importing application code.
_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import URL

from backend.database import create_postgres_engine


CONFIG_SCHEMA_VERSION = "reagent.owner-runtime/v0.1"
OWNER_PROFILE = "owner-local-real"
CONFIG_FILENAME = "config.toml"
CONFIG_MAX_BYTES = 32 * 1024
KEYCHAIN_SERVICE = "com.reagent.owner-local-real.openalex"
KEYCHAIN_ACCOUNT = "openalex-api-key"
KEYCHAIN_LABEL = "ReAgent Owner Local Real Research - OpenAlex"
DEFAULT_DATABASE_HOST = "127.0.0.1"
DEFAULT_DATABASE_PORT = 5432
DEFAULT_DATABASE_NAME = "reagent_local_v01"
DEFAULT_BACKEND_HOST = "127.0.0.1"
DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_HOST = "127.0.0.1"
DEFAULT_FRONTEND_PORT = 3000
SAFE_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}$")


class OwnerRuntimeError(RuntimeError):
    """A value-free owner startup failure suitable for terminal display."""


class OwnerSecretStore(Protocol):
    def exists(self) -> bool: ...

    def store_interactively(self, *, replace: bool) -> None: ...

    def retrieve(self) -> str: ...

    def delete(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class OwnerDatabaseConfig:
    host: str
    port: int
    database: str
    user: str


@dataclass(frozen=True, slots=True)
class OwnerEndpointConfig:
    host: str
    port: int


@dataclass(frozen=True, slots=True)
class OwnerProviderConfig:
    openalex_enabled: bool


@dataclass(frozen=True, slots=True)
class OwnerRuntimeConfig:
    schema_version: str
    profile: str
    database: OwnerDatabaseConfig
    backend: OwnerEndpointConfig
    frontend: OwnerEndpointConfig
    providers: OwnerProviderConfig

    def database_url(self) -> str:
        return URL.create(
            "postgresql+psycopg",
            username=self.database.user,
            host=self.database.host,
            port=self.database.port,
            database=self.database.database,
        ).render_as_string(hide_password=False)


@dataclass(frozen=True, slots=True)
class DatabaseInspection:
    reachable: bool
    database: str
    user: str
    current_revision: str
    head_revision: str

    @property
    def migration_current(self) -> bool:
        return self.current_revision == self.head_revision


def _repository_root() -> Path:
    return _REPOSITORY_ROOT


def canonical_config_path(environment: Mapping[str, str] | None = None) -> Path:
    values = os.environ if environment is None else environment
    configured = values.get("XDG_CONFIG_HOME")
    if configured:
        base = Path(configured).expanduser()
        if not base.is_absolute():
            raise OwnerRuntimeError("XDG_CONFIG_HOME must be an absolute path")
    else:
        base = Path.home() / ".config"
    return base / "reagent" / CONFIG_FILENAME


def _is_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=True))
    except (OSError, ValueError):
        return False
    return True


def _require_unlinked_regular_file(path: Path, *, label: str) -> os.stat_result:
    if path.is_symlink():
        raise OwnerRuntimeError(f"{label} must not be a symbolic link")
    try:
        value = path.stat(follow_symlinks=False)
    except OSError as error:
        raise OwnerRuntimeError(f"{label} cannot be inspected") from error
    if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
        raise OwnerRuntimeError(f"{label} must be one regular unlinked file")
    if hasattr(os, "getuid") and value.st_uid != os.getuid():
        raise OwnerRuntimeError(f"{label} must be owned by the current user")
    return value


def _require_safe_directory(path: Path, *, create: bool) -> None:
    if path.is_symlink():
        raise OwnerRuntimeError("ReAgent owner config directory must not be a symlink")
    if not path.exists():
        if not create:
            raise OwnerRuntimeError("ReAgent owner setup has not been completed")
        try:
            path.mkdir(mode=0o700)
        except OSError as error:
            raise OwnerRuntimeError("ReAgent owner config directory could not be created") from error
    try:
        value = path.stat(follow_symlinks=False)
    except OSError as error:
        raise OwnerRuntimeError("ReAgent owner config directory cannot be inspected") from error
    if not stat.S_ISDIR(value.st_mode):
        raise OwnerRuntimeError("ReAgent owner config directory is not a directory")
    if hasattr(os, "getuid") and value.st_uid != os.getuid():
        raise OwnerRuntimeError("ReAgent owner config directory must be owned by the current user")
    try:
        os.chmod(path, 0o700)
    except OSError as error:
        raise OwnerRuntimeError("ReAgent owner config directory permissions could not be secured") from error


class OwnerConfigStore:
    """Atomic, versioned, user-level owner runtime configuration."""

    def __init__(
        self,
        path: Path | None = None,
        *,
        repository_root: Path | None = None,
        enforce_user_location: bool = True,
    ) -> None:
        self.path = canonical_config_path() if path is None else path
        if not self.path.is_absolute():
            raise OwnerRuntimeError("ReAgent owner config path must be absolute")
        if self.path.name != CONFIG_FILENAME:
            raise OwnerRuntimeError("ReAgent owner config filename is invalid")
        root = repository_root or _repository_root()
        if enforce_user_location and _is_within(root, self.path):
            raise OwnerRuntimeError("ReAgent owner config must remain outside the repository")

    def exists(self) -> bool:
        return self.path.exists() and not self.path.is_symlink()

    def load(self) -> OwnerRuntimeConfig:
        if not self.path.exists() and not self.path.is_symlink():
            raise OwnerRuntimeError(
                "ReAgent owner setup has not been completed. Run: make owner-setup"
            )
        if self.path.parent.parent.is_symlink():
            raise OwnerRuntimeError("ReAgent user config root must not be a symlink")
        _require_safe_directory(self.path.parent, create=False)
        value = _require_unlinked_regular_file(self.path, label="ReAgent owner config")
        if value.st_size > CONFIG_MAX_BYTES:
            raise OwnerRuntimeError("ReAgent owner config exceeds its size limit")
        if stat.S_IMODE(value.st_mode) & 0o077:
            raise OwnerRuntimeError(
                "ReAgent owner config permissions are unsafe; expected owner-only access"
            )
        try:
            content = self.path.read_bytes()
            document = tomllib.loads(content.decode("utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
            raise OwnerRuntimeError("ReAgent owner config is invalid TOML") from error
        return validate_owner_config(document)

    def write(self, config: OwnerRuntimeConfig) -> None:
        config = validate_owner_config(owner_config_document(config))
        base = self.path.parent.parent
        if base.is_symlink():
            raise OwnerRuntimeError("ReAgent user config root must not be a symlink")
        if not base.exists():
            try:
                base.mkdir(mode=0o700, parents=True)
            except OSError as error:
                raise OwnerRuntimeError("ReAgent user config root could not be created") from error
        if not base.is_dir():
            raise OwnerRuntimeError("ReAgent user config root is invalid")
        _require_safe_directory(self.path.parent, create=True)
        if self.path.exists() or self.path.is_symlink():
            _require_unlinked_regular_file(self.path, label="ReAgent owner config")
        payload = render_owner_config(config).encode("utf-8")
        if len(payload) > CONFIG_MAX_BYTES:
            raise OwnerRuntimeError("ReAgent owner config exceeds its size limit")
        descriptor, name = tempfile.mkstemp(
            prefix=".config.toml.", dir=self.path.parent
        )
        temporary = Path(name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb", closefd=True) as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            if self.path.is_symlink():
                raise OwnerRuntimeError("ReAgent owner config target became unsafe")
            os.replace(temporary, self.path)
            os.chmod(self.path, 0o600)
            directory = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            temporary.unlink(missing_ok=True)
            raise


def owner_config_document(config: OwnerRuntimeConfig) -> dict[str, object]:
    return {
        "schema_version": config.schema_version,
        "profile": config.profile,
        "database": {
            "host": config.database.host,
            "port": config.database.port,
            "database": config.database.database,
            "user": config.database.user,
        },
        "backend": {"host": config.backend.host, "port": config.backend.port},
        "frontend": {"host": config.frontend.host, "port": config.frontend.port},
        "providers": {"openalex_enabled": config.providers.openalex_enabled},
    }


def _object(value: object, *, name: str, fields: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != fields:
        raise OwnerRuntimeError(f"ReAgent owner config {name} fields are invalid")
    if any(not isinstance(key, str) for key in value):
        raise OwnerRuntimeError(f"ReAgent owner config {name} is invalid")
    return value


def _port(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1024 <= value <= 65535:
        raise OwnerRuntimeError(f"ReAgent owner config {name} port is invalid")
    return value


def _name(value: object, *, name: str) -> str:
    if not isinstance(value, str) or SAFE_NAME.fullmatch(value) is None:
        raise OwnerRuntimeError(f"ReAgent owner config {name} is invalid")
    return value


def validate_owner_config(document: object) -> OwnerRuntimeConfig:
    root = _object(
        document,
        name="root",
        fields={"schema_version", "profile", "database", "backend", "frontend", "providers"},
    )
    if root["schema_version"] != CONFIG_SCHEMA_VERSION:
        raise OwnerRuntimeError("ReAgent owner config schema version is unsupported")
    if root["profile"] != OWNER_PROFILE:
        raise OwnerRuntimeError("ReAgent owner config profile is unsupported")
    database = _object(
        root["database"],
        name="database",
        fields={"host", "port", "database", "user"},
    )
    backend = _object(root["backend"], name="backend", fields={"host", "port"})
    frontend = _object(root["frontend"], name="frontend", fields={"host", "port"})
    providers = _object(
        root["providers"], name="providers", fields={"openalex_enabled"}
    )
    if database["host"] != DEFAULT_DATABASE_HOST:
        raise OwnerRuntimeError("Owner PostgreSQL must use literal loopback 127.0.0.1")
    if backend["host"] != DEFAULT_BACKEND_HOST or frontend["host"] != DEFAULT_FRONTEND_HOST:
        raise OwnerRuntimeError("Owner Backend and Frontend must use literal loopback 127.0.0.1")
    openalex_enabled = providers["openalex_enabled"]
    if not isinstance(openalex_enabled, bool):
        raise OwnerRuntimeError("ReAgent owner config OpenAlex setting is invalid")
    backend_port = _port(backend["port"], name="Backend")
    frontend_port = _port(frontend["port"], name="Frontend")
    if backend_port == frontend_port:
        raise OwnerRuntimeError("Owner Backend and Frontend ports must differ")
    return OwnerRuntimeConfig(
        schema_version=CONFIG_SCHEMA_VERSION,
        profile=OWNER_PROFILE,
        database=OwnerDatabaseConfig(
            host=DEFAULT_DATABASE_HOST,
            port=_port(database["port"], name="database"),
            database=_name(database["database"], name="database name"),
            user=_name(database["user"], name="database user"),
        ),
        backend=OwnerEndpointConfig(DEFAULT_BACKEND_HOST, backend_port),
        frontend=OwnerEndpointConfig(DEFAULT_FRONTEND_HOST, frontend_port),
        providers=OwnerProviderConfig(openalex_enabled),
    )


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_owner_config(config: OwnerRuntimeConfig) -> str:
    value = validate_owner_config(owner_config_document(config))
    return (
        f"schema_version = {_toml_string(value.schema_version)}\n"
        f"profile = {_toml_string(value.profile)}\n\n"
        "[database]\n"
        f"host = {_toml_string(value.database.host)}\n"
        f"port = {value.database.port}\n"
        f"database = {_toml_string(value.database.database)}\n"
        f"user = {_toml_string(value.database.user)}\n\n"
        "[backend]\n"
        f"host = {_toml_string(value.backend.host)}\n"
        f"port = {value.backend.port}\n\n"
        "[frontend]\n"
        f"host = {_toml_string(value.frontend.host)}\n"
        f"port = {value.frontend.port}\n\n"
        "[providers]\n"
        f"openalex_enabled = {'true' if value.providers.openalex_enabled else 'false'}\n"
    )


class MacOSKeychainSecretStore:
    """Minimal Keychain adapter whose write path lets `security` prompt."""

    def __init__(
        self,
        *,
        runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
        system: str | None = None,
    ) -> None:
        self._runner = runner
        self._system = platform.system() if system is None else system

    def _require_platform(self) -> None:
        if self._system != "Darwin":
            raise OwnerRuntimeError(
                "Owner secure local startup is currently supported on macOS"
            )
        if shutil.which("security") is None and self._runner is subprocess.run:
            raise OwnerRuntimeError("macOS Keychain command is unavailable")

    def exists(self) -> bool:
        self._require_platform()
        result = self._runner(
            [
                "security", "find-generic-password",
                "-a", KEYCHAIN_ACCOUNT,
                "-s", KEYCHAIN_SERVICE,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            return True
        if result.returncode == 44:
            return False
        raise OwnerRuntimeError("macOS Keychain credential status could not be determined")

    def store_interactively(self, *, replace: bool) -> None:
        self._require_platform()
        command = [
            "security", "add-generic-password",
            "-a", KEYCHAIN_ACCOUNT,
            "-s", KEYCHAIN_SERVICE,
            "-l", KEYCHAIN_LABEL,
        ]
        if replace:
            command.append("-U")
        # `security help add-generic-password` documents that a final bare -w
        # securely prompts instead of accepting the value in argv.
        command.append("-w")
        result = self._runner(
            command,
            stdout=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            raise OwnerRuntimeError("OpenAlex credential was not stored in macOS Keychain")

    def retrieve(self) -> str:
        self._require_platform()
        result = self._runner(
            [
                "security", "find-generic-password",
                "-a", KEYCHAIN_ACCOUNT,
                "-s", KEYCHAIN_SERVICE,
                "-w",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            raise OwnerRuntimeError(
                "OpenAlex credential is missing. Run: make owner-setup"
            )
        raw = result.stdout
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        try:
            value = raw.decode("utf-8").rstrip("\r\n")
        except UnicodeError as error:
            raise OwnerRuntimeError("OpenAlex credential in Keychain is invalid") from error
        if (
            not value
            or len(value.encode("utf-8")) > 4096
            or any(ord(character) < 32 or ord(character) == 127 for character in value)
        ):
            raise OwnerRuntimeError("OpenAlex credential in Keychain is invalid")
        return value

    def delete(self) -> bool:
        self._require_platform()
        result = self._runner(
            [
                "security", "delete-generic-password",
                "-a", KEYCHAIN_ACCOUNT,
                "-s", KEYCHAIN_SERVICE,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            return True
        if result.returncode == 44:
            return False
        raise OwnerRuntimeError("OpenAlex credential could not be removed from Keychain")


def repository_migration_head(repo_root: Path) -> str:
    configuration = AlembicConfig(str(repo_root / "alembic.ini"))
    configuration.set_main_option("script_location", str(repo_root / "backend/database/migrations"))
    heads = ScriptDirectory.from_config(configuration).get_heads()
    if len(heads) != 1:
        raise OwnerRuntimeError("Repository migration history does not have one head")
    return heads[0]


def inspect_database(config: OwnerRuntimeConfig, repo_root: Path) -> DatabaseInspection:
    engine = create_postgres_engine(config.database_url())
    try:
        with engine.connect() as connection:
            if connection.scalar(text("SELECT 1")) != 1:
                raise OwnerRuntimeError("Owner PostgreSQL readiness check failed")
            database = connection.scalar(text("SELECT current_database()"))
            user = connection.scalar(text("SELECT current_user"))
            revisions = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
    except OwnerRuntimeError:
        raise
    except Exception as error:
        raise OwnerRuntimeError(
            "Owner PostgreSQL database is unavailable; start PostgreSQL and rerun make owner-doctor"
        ) from error
    finally:
        engine.dispose()
    if database != config.database.database or user != config.database.user:
        raise OwnerRuntimeError("Owner PostgreSQL identity does not match owner config")
    if len(revisions) != 1 or not isinstance(revisions[0], str):
        raise OwnerRuntimeError("Owner PostgreSQL migration state is invalid")
    return DatabaseInspection(
        reachable=True,
        database=database,
        user=user,
        current_revision=revisions[0],
        head_revision=repository_migration_head(repo_root),
    )


def _prompt_default(reader: Callable[[str], str], label: str, default: str) -> str:
    value = reader(f"{label} [{default}]: ").strip()
    return value or default


def default_owner_config(existing: OwnerRuntimeConfig | None = None) -> OwnerRuntimeConfig:
    if existing is not None:
        return existing
    return OwnerRuntimeConfig(
        schema_version=CONFIG_SCHEMA_VERSION,
        profile=OWNER_PROFILE,
        database=OwnerDatabaseConfig(
            DEFAULT_DATABASE_HOST,
            DEFAULT_DATABASE_PORT,
            DEFAULT_DATABASE_NAME,
            getpass.getuser(),
        ),
        backend=OwnerEndpointConfig(DEFAULT_BACKEND_HOST, DEFAULT_BACKEND_PORT),
        frontend=OwnerEndpointConfig(DEFAULT_FRONTEND_HOST, DEFAULT_FRONTEND_PORT),
        providers=OwnerProviderConfig(True),
    )


def setup_owner_runtime(
    *,
    config_store: OwnerConfigStore,
    secret_store: OwnerSecretStore,
    repo_root: Path,
    reader: Callable[[str], str] = input,
    writer: Callable[[str], None] = print,
    database_inspector: Callable[[OwnerRuntimeConfig, Path], DatabaseInspection] = inspect_database,
) -> OwnerRuntimeConfig:
    writer("ReAgent Owner Setup")
    existing = config_store.load() if config_store.exists() else None
    defaults = default_owner_config(existing)
    database_name = _prompt_default(reader, "Database", defaults.database.database)
    database_host = _prompt_default(reader, "Database host", defaults.database.host)
    database_port_text = _prompt_default(reader, "Database port", str(defaults.database.port))
    database_user = _prompt_default(reader, "Database user", defaults.database.user)
    backend_port_text = _prompt_default(reader, "Backend port", str(defaults.backend.port))
    frontend_port_text = _prompt_default(reader, "Frontend port", str(defaults.frontend.port))
    try:
        database_port = int(database_port_text)
        backend_port = int(backend_port_text)
        frontend_port = int(frontend_port_text)
    except ValueError as error:
        raise OwnerRuntimeError("Owner setup ports must be integers") from error
    config = validate_owner_config({
        "schema_version": CONFIG_SCHEMA_VERSION,
        "profile": OWNER_PROFILE,
        "database": {
            "host": database_host,
            "port": database_port,
            "database": database_name,
            "user": database_user,
        },
        "backend": {"host": DEFAULT_BACKEND_HOST, "port": backend_port},
        "frontend": {"host": DEFAULT_FRONTEND_HOST, "port": frontend_port},
        "providers": {"openalex_enabled": True},
    })
    inspection = database_inspector(config, repo_root)
    writer(f"Database: {inspection.database} - reachable")
    writer(f"Migration: {inspection.current_revision} - " + (
        "current" if inspection.migration_current else f"mismatch (head {inspection.head_revision})"
    ))
    if not inspection.migration_current:
        raise OwnerRuntimeError(
            "Owner database migration is not current. owner-setup made no changes; "
            "review the approved migration procedure before retrying"
        )
    answer = reader("Configure real Literature Search with OpenAlex? [Y/n]: ").strip().casefold()
    if answer not in {"", "y", "yes"}:
        raise OwnerRuntimeError("Owner real-research setup was cancelled")
    if secret_store.exists():
        action = reader(
            "OpenAlex credential is configured. Keep [K], replace [R], or remove [D]: "
        ).strip().casefold()
        if action in {"", "k", "keep"}:
            writer("OpenAlex: existing Keychain credential retained")
        elif action in {"r", "replace"}:
            confirmation = reader("Type replace-openalex to confirm replacement: ").strip()
            if confirmation != "replace-openalex":
                raise OwnerRuntimeError("OpenAlex credential replacement was cancelled")
            secret_store.store_interactively(replace=True)
            writer("OpenAlex: credential replaced in macOS Keychain")
        elif action in {"d", "delete", "remove"}:
            confirmation = reader("Type remove-openalex to confirm removal: ").strip()
            if confirmation != "remove-openalex":
                raise OwnerRuntimeError("OpenAlex credential removal was cancelled")
            secret_store.delete()
            raise OwnerRuntimeError(
                "OpenAlex credential removed. Setup is incomplete; rerun make owner-setup"
            )
        else:
            raise OwnerRuntimeError("OpenAlex credential action was not recognized")
    else:
        writer("OpenAlex: macOS Keychain will securely prompt for the credential")
        secret_store.store_interactively(replace=False)
        writer("OpenAlex: credential stored in macOS Keychain")
    config_store.write(config)
    writer(f"Config: {config_store.path}")
    writer("Setup complete. Daily startup: make owner-start")
    return config


def remove_owner_secret(
    *,
    secret_store: OwnerSecretStore,
    reader: Callable[[str], str] = input,
    writer: Callable[[str], None] = print,
) -> None:
    confirmation = reader("Type remove-openalex to remove the Keychain credential: ").strip()
    if confirmation != "remove-openalex":
        raise OwnerRuntimeError("OpenAlex credential removal was cancelled")
    removed = secret_store.delete()
    writer("OpenAlex credential removed." if removed else "OpenAlex credential was not configured.")


def _port_available(host: str, port: int) -> bool:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.settimeout(0.25)
        return probe.connect_ex((host, port)) != 0
    finally:
        probe.close()
    return True


def owner_runtime_directory(config_path: Path | None = None) -> Path:
    """Stable per-config records let stop work even when config is damaged."""

    path = canonical_config_path() if config_path is None else config_path
    identity = hashlib.sha256(str(path.absolute()).encode("utf-8")).hexdigest()[:12]
    return Path(f"/tmp/reagent-owner-{os.getuid()}-{identity}")


def build_owner_environments(
    *,
    config: OwnerRuntimeConfig,
    secret: str,
    runtime_dir: Path,
    environment: Mapping[str, str] | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    source = os.environ if environment is None else environment
    clean = {
        key: value
        for key, value in source.items()
        if not key.startswith("REAGENT_")
        and key not in {"OPENALEX_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"}
    }
    backend = {
        **clean,
        "REAGENT_DEPLOYMENT_PROFILE": "local-development",
        "REAGENT_DATABASE_URL": config.database_url(),
        "REAGENT_ARTIFACT_ROOT": str(runtime_dir / "artifacts"),
        "REAGENT_LOCAL_PACKAGE_ROOT": str(runtime_dir / "local-packages"),
        "REAGENT_PAPER_SEARCH_PROVIDER": "fake",
        "REAGENT_V0_1_LOCAL_MODE_ENABLED": "1",
        "REAGENT_EXPERIMENTAL_FAKE_PROXY_ENABLED": "0",
        "REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED": "1",
        "REAGENT_OPENALEX_API_KEY": secret,
        "REAGENT_EXPERIMENTAL_OPENALEX_STRUCTURAL_DIAGNOSTICS_ENABLED": "0",
    }
    frontend = {
        **clean,
        "REAGENT_API_URL": f"http://{config.backend.host}:{config.backend.port}",
    }
    return backend, frontend


def _process_identity(pid: int) -> str:
    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "lstart="],
        capture_output=True,
        text=True,
        check=False,
    )
    value = result.stdout.rstrip("\r\n")
    if result.returncode != 0 or not value.strip():
        raise OwnerRuntimeError("Owner runtime process identity could not be recorded")
    return value


def _write_runtime_record(path: Path, value: str) -> None:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", closefd=True) as handle:
            handle.write(value + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _wait_url(url: str, process: subprocess.Popen, *, attempts: int) -> None:
    for _ in range(attempts):
        if process.poll() is not None:
            raise OwnerRuntimeError("Owner runtime process exited before readiness")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError, urllib.error.HTTPError):
            pass
        time.sleep(0.25)
    raise OwnerRuntimeError("Owner runtime did not become ready")


def _stop_runtime_dir(runtime_dir: Path, repo_root: Path, *, quiet: bool = False) -> None:
    environment = {
        **os.environ,
        "REAGENT_LOCAL_RUNTIME_DIR": str(runtime_dir),
    }
    result = subprocess.run(
        [str(repo_root / "scripts/dev-stop.sh")],
        cwd=repo_root,
        env=environment,
        stdout=subprocess.DEVNULL if quiet else None,
        check=False,
    )
    if result.returncode != 0:
        raise OwnerRuntimeError("Owner runtime could not be stopped safely")


def _terminate_started_process(process: subprocess.Popen | None) -> None:
    """Reap an exact child if startup failed before safe records existed."""

    if process is None or process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        return
    try:
        process.wait(timeout=4)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
        process.wait(timeout=4)


def launch_owner_processes(
    *,
    config: OwnerRuntimeConfig,
    backend_environment: dict[str, str],
    frontend_environment: dict[str, str],
    repo_root: Path,
    runtime_dir: Path,
) -> None:
    for command in ("npm", "curl", "ps", "pgrep"):
        if shutil.which(command) is None:
            raise OwnerRuntimeError(f"Owner runtime requirement is missing: {command}")
    if _is_within(repo_root, runtime_dir):
        raise OwnerRuntimeError("Owner runtime files must remain outside the repository")
    runtime_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(runtime_dir, 0o700)
    records = [
        runtime_dir / f"{name}.{suffix}"
        for name in ("backend", "frontend")
        for suffix in ("pid", "identity")
    ]
    if any(path.exists() or path.is_symlink() for path in records):
        raise OwnerRuntimeError("Stale owner runtime records exist. Run: make stop")
    backend_log_path = runtime_dir / "backend.log"
    frontend_log_path = runtime_dir / "frontend.log"
    backend: subprocess.Popen | None = None
    frontend: subprocess.Popen | None = None
    try:
        with backend_log_path.open("wb") as backend_log:
            os.chmod(backend_log_path, 0o600)
            backend = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "backend.api.app:app",
                    "--host",
                    config.backend.host,
                    "--port",
                    str(config.backend.port),
                    "--no-proxy-headers",
                ],
                cwd=repo_root,
                env=backend_environment,
                stdin=subprocess.DEVNULL,
                stdout=backend_log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        _write_runtime_record(runtime_dir / "backend.pid", str(backend.pid))
        _write_runtime_record(runtime_dir / "backend.identity", _process_identity(backend.pid))
        _wait_url(
            f"http://{config.backend.host}:{config.backend.port}/ready",
            backend,
            attempts=120,
        )
        with frontend_log_path.open("wb") as frontend_log:
            os.chmod(frontend_log_path, 0o600)
            frontend = subprocess.Popen(
                [
                    "npm", "run", "dev", "--",
                    "--hostname", config.frontend.host,
                    "--port", str(config.frontend.port),
                ],
                cwd=repo_root / "frontend",
                env=frontend_environment,
                stdin=subprocess.DEVNULL,
                stdout=frontend_log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        _write_runtime_record(runtime_dir / "frontend.pid", str(frontend.pid))
        _write_runtime_record(runtime_dir / "frontend.identity", _process_identity(frontend.pid))
        _wait_url(
            f"http://{config.frontend.host}:{config.frontend.port}/projects",
            frontend,
            attempts=160,
        )
    except Exception:
        # Startup may fail before a complete pid+identity pair is durable, so
        # clean up only the exact children created by this invocation.
        _terminate_started_process(frontend)
        _terminate_started_process(backend)
        for path in records:
            path.unlink(missing_ok=True)
        raise


def start_owner_runtime(
    *,
    config_store: OwnerConfigStore,
    secret_store: OwnerSecretStore,
    repo_root: Path,
    writer: Callable[[str], None] = print,
    database_inspector: Callable[[OwnerRuntimeConfig, Path], DatabaseInspection] = inspect_database,
    port_checker: Callable[[str, int], bool] = _port_available,
    launcher: Callable[..., None] = launch_owner_processes,
    environment: Mapping[str, str] | None = None,
) -> OwnerRuntimeConfig:
    config = config_store.load()
    if not config.providers.openalex_enabled:
        raise OwnerRuntimeError("OpenAlex is not enabled. Run: make owner-setup")
    inspection = database_inspector(config, repo_root)
    if not inspection.migration_current:
        raise OwnerRuntimeError(
            f"Owner database migration mismatch: current {inspection.current_revision}, "
            f"repository head {inspection.head_revision}. owner-start made no changes"
        )
    if not secret_store.exists():
        raise OwnerRuntimeError("OpenAlex credential is missing. Run: make owner-setup")
    occupied = [
        f"{name} port {endpoint.port}"
        for name, endpoint in (("Backend", config.backend), ("Frontend", config.frontend))
        if not port_checker(endpoint.host, endpoint.port)
    ]
    if occupied:
        raise OwnerRuntimeError(
            ", ".join(occupied) + " is occupied. Stop the existing service or run: make stop"
        )
    secret = secret_store.retrieve()
    runtime_dir = owner_runtime_directory(config_store.path)
    backend_environment, frontend_environment = build_owner_environments(
        config=config,
        secret=secret,
        runtime_dir=runtime_dir,
        environment=environment,
    )
    try:
        launcher(
            config=config,
            backend_environment=backend_environment,
            frontend_environment=frontend_environment,
            repo_root=repo_root,
            runtime_dir=runtime_dir,
        )
    finally:
        backend_environment["REAGENT_OPENALEX_API_KEY"] = ""
        secret = ""
    writer("ReAgent Owner Runtime")
    writer(f"Database: {inspection.database} - ready")
    writer(f"Migration: {inspection.current_revision} - current")
    writer("OpenAlex: configured")
    writer(f"Backend: http://{config.backend.host}:{config.backend.port}")
    writer(f"Frontend: http://{config.frontend.host}:{config.frontend.port}")
    writer("Mode: owner-local real research")
    return config


def doctor_owner_runtime(
    *,
    config_store: OwnerConfigStore,
    secret_store: OwnerSecretStore,
    repo_root: Path,
    writer: Callable[[str], None] = print,
    database_inspector: Callable[[OwnerRuntimeConfig, Path], DatabaseInspection] = inspect_database,
    port_checker: Callable[[str, int], bool] = _port_available,
) -> bool:
    writer("ReAgent Owner Doctor")
    try:
        config = config_store.load()
    except OwnerRuntimeError as error:
        writer(f"Config: missing or invalid - {error}")
        writer("Run: make owner-setup")
        return False
    writer("Config: OK")
    healthy = True
    try:
        inspection = database_inspector(config, repo_root)
        writer(f"Database: {inspection.database} - reachable")
        writer(
            f"Migration: {inspection.current_revision} - "
            + ("current" if inspection.migration_current else f"mismatch; head {inspection.head_revision}")
        )
        healthy = healthy and inspection.migration_current
    except OwnerRuntimeError as error:
        writer(f"Database: unavailable - {error}")
        writer("Migration: unknown")
        healthy = False
    try:
        configured = secret_store.exists()
    except OwnerRuntimeError as error:
        writer(f"OpenAlex credential: unavailable - {error}")
        healthy = False
    else:
        writer("OpenAlex credential: " + ("configured" if configured else "missing"))
        healthy = healthy and configured
    for name, endpoint in (("Backend", config.backend), ("Frontend", config.frontend)):
        available = port_checker(endpoint.host, endpoint.port)
        writer(f"{name} port {endpoint.port}: " + ("available" if available else "occupied"))
        healthy = healthy and available
    writer("PostgreSQL: reachable" if healthy else "Owner runtime: action required")
    return healthy


def stop_owner_runtime(
    *,
    config_store: OwnerConfigStore,
    repo_root: Path,
    writer: Callable[[str], None] = print,
) -> None:
    runtime_dir = owner_runtime_directory(config_store.path)
    _stop_runtime_dir(runtime_dir, repo_root, quiet=True)
    writer("Stopped ReAgent owner Backend/Frontend. Config, Keychain and PostgreSQL were unchanged.")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("setup", "start", "doctor", "stop", "remove-secret")
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    repo_root = _repository_root()
    config_store = OwnerConfigStore(repository_root=repo_root)
    secret_store = MacOSKeychainSecretStore()
    try:
        if arguments.command == "setup":
            setup_owner_runtime(
                config_store=config_store,
                secret_store=secret_store,
                repo_root=repo_root,
            )
        elif arguments.command == "start":
            start_owner_runtime(
                config_store=config_store,
                secret_store=secret_store,
                repo_root=repo_root,
            )
        elif arguments.command == "doctor":
            if not doctor_owner_runtime(
                config_store=config_store,
                secret_store=secret_store,
                repo_root=repo_root,
            ):
                return 2
        elif arguments.command == "stop":
            # Controlled E2E already supplies its own runtime directory. Never
            # let its shared `make stop` touch a separately running owner
            # runtime derived from the real user-config authority.
            if os.environ.get("REAGENT_AUTOMATED_QUALIFICATION") != "1":
                stop_owner_runtime(config_store=config_store, repo_root=repo_root)
        else:
            remove_owner_secret(secret_store=secret_store)
    except OwnerRuntimeError as error:
        print(f"ReAgent owner runtime: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
