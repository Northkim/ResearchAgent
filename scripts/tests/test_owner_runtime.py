from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

from scripts import owner_runtime as owner_runtime_module
from scripts.owner_runtime import (
    CONFIG_SCHEMA_VERSION,
    KEYCHAIN_ACCOUNT,
    KEYCHAIN_SERVICE,
    OWNER_PROFILE,
    DatabaseInspection,
    MacOSKeychainSecretStore,
    OwnerConfigStore,
    OwnerDatabaseConfig,
    OwnerEndpointConfig,
    OwnerProviderConfig,
    OwnerRuntimeConfig,
    OwnerRuntimeError,
    _port_available,
    _process_identity,
    build_owner_environments,
    doctor_owner_runtime,
    owner_config_document,
    owner_runtime_directory,
    remove_owner_secret,
    setup_owner_runtime,
    start_owner_runtime,
    validate_owner_config,
)


SENTINEL = "owner-openalex-secret-sentinel"
HEAD = "20260806_0017"


def config(*, backend_port: int = 8000, frontend_port: int = 3000) -> OwnerRuntimeConfig:
    return OwnerRuntimeConfig(
        schema_version=CONFIG_SCHEMA_VERSION,
        profile=OWNER_PROFILE,
        database=OwnerDatabaseConfig(
            host="127.0.0.1",
            port=5432,
            database="reagent_owner_test",
            user="owner_test",
        ),
        backend=OwnerEndpointConfig("127.0.0.1", backend_port),
        frontend=OwnerEndpointConfig("127.0.0.1", frontend_port),
        providers=OwnerProviderConfig(openalex_enabled=True),
    )


def inspection(value: OwnerRuntimeConfig, _repo: Path) -> DatabaseInspection:
    return DatabaseInspection(
        reachable=True,
        database=value.database.database,
        user=value.database.user,
        current_revision=HEAD,
        head_revision=HEAD,
    )


class FakeSecretStore:
    def __init__(self, value: str | None = SENTINEL) -> None:
        self.value = value
        self.operations: list[tuple[str, bool | None]] = []

    def exists(self) -> bool:
        self.operations.append(("exists", None))
        return self.value is not None

    def store_interactively(self, *, replace: bool) -> None:
        self.operations.append(("store", replace))
        self.value = SENTINEL

    def retrieve(self) -> str:
        self.operations.append(("retrieve", None))
        if self.value is None:
            raise OwnerRuntimeError("missing")
        return self.value

    def delete(self) -> bool:
        self.operations.append(("delete", None))
        existed = self.value is not None
        self.value = None
        return existed


def store(tmp_path: Path) -> OwnerConfigStore:
    return OwnerConfigStore(
        tmp_path / "xdg" / "reagent" / "config.toml",
        repository_root=Path(__file__).resolve().parents[2],
    )


def write_config(tmp_path: Path, value: OwnerRuntimeConfig | None = None) -> OwnerConfigStore:
    target = store(tmp_path)
    target.write(value or config())
    return target


def test_owner_config_round_trip_is_atomic_owner_only_and_secret_free(tmp_path: Path) -> None:
    target = write_config(tmp_path)
    first_inode = target.path.stat().st_ino
    target.write(config(backend_port=8011, frontend_port=3011))
    assert target.load() == config(backend_port=8011, frontend_port=3011)
    assert target.path.stat().st_ino != first_inode
    assert stat.S_IMODE(target.path.stat().st_mode) == 0o600
    assert stat.S_IMODE(target.path.parent.stat().st_mode) == 0o700
    content = target.path.read_text(encoding="utf-8")
    assert SENTINEL not in content
    assert "password" not in content.casefold()
    assert not list(target.path.parent.glob(".config.toml.*"))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(schema_version="unknown/v9"),
        lambda value: value.pop("providers"),
        lambda value: value.update(password="must-not-be-supported"),
        lambda value: value["database"].update(password="must-not-be-supported"),
        lambda value: value["database"].update(host="database.example"),
        lambda value: value["database"].update(database="postgresql://owner:secret@host/db"),
    ],
)
def test_owner_config_rejects_unknown_missing_or_credential_fields(mutation) -> None:
    document = owner_config_document(config())
    mutation(document)
    with pytest.raises(OwnerRuntimeError):
        validate_owner_config(document)


def test_owner_config_rejects_corruption_and_unsafe_permissions(tmp_path: Path) -> None:
    target = store(tmp_path)
    target.path.parent.mkdir(parents=True, mode=0o700)
    target.path.write_text("not valid = [", encoding="utf-8")
    target.path.chmod(0o600)
    with pytest.raises(OwnerRuntimeError, match="invalid TOML"):
        target.load()
    target.path.write_text("schema_version = 'unknown'", encoding="utf-8")
    target.path.chmod(0o644)
    with pytest.raises(OwnerRuntimeError, match="permissions are unsafe"):
        target.load()


def test_owner_config_rejects_oversize_and_hardlinked_files(tmp_path: Path) -> None:
    target = store(tmp_path)
    target.path.parent.mkdir(parents=True, mode=0o700)
    target.path.write_bytes(b"x" * (32 * 1024 + 1))
    target.path.chmod(0o600)
    with pytest.raises(OwnerRuntimeError, match="size limit"):
        target.load()
    target.path.unlink()
    original = tmp_path / "original-config"
    original.write_text("unused", encoding="utf-8")
    os.link(original, target.path)
    with pytest.raises(OwnerRuntimeError, match="one regular unlinked file"):
        target.load()


def test_owner_config_rejects_file_and_directory_symlinks(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    file_link = tmp_path / "file-link" / "reagent"
    file_link.mkdir(parents=True)
    (real / "config.toml").write_text("unused", encoding="utf-8")
    (file_link / "config.toml").symlink_to(real / "config.toml")
    with pytest.raises(OwnerRuntimeError, match="symbolic link"):
        OwnerConfigStore(
            file_link / "config.toml", repository_root=Path("/definitely/not/here")
        ).load()

    root_link = tmp_path / "root-link"
    root_link.symlink_to(real, target_is_directory=True)
    with pytest.raises(OwnerRuntimeError, match="config root.*symlink"):
        OwnerConfigStore(
            root_link / "reagent" / "config.toml",
            repository_root=Path("/definitely/not/here"),
        ).write(config())


def test_owner_config_rejects_repository_relative_storage() -> None:
    repo = Path(__file__).resolve().parents[2]
    with pytest.raises(OwnerRuntimeError, match="outside the repository"):
        OwnerConfigStore(repo / ".owner" / "reagent" / "config.toml")


def test_keychain_write_uses_os_prompt_without_secret_in_argv() -> None:
    calls: list[list[str]] = []

    def runner(command, **_kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=b"")

    secret_store = MacOSKeychainSecretStore(runner=runner, system="Darwin")
    secret_store.store_interactively(replace=False)
    secret_store.store_interactively(replace=True)
    assert calls[0][-1] == "-w"
    assert "-U" not in calls[0]
    assert calls[1][-1] == "-w"
    assert "-U" in calls[1]
    assert SENTINEL not in repr(calls)
    assert KEYCHAIN_ACCOUNT in calls[0]
    assert KEYCHAIN_SERVICE in calls[0]


def test_keychain_detect_retrieve_delete_and_platform_gate() -> None:
    calls: list[list[str]] = []

    def runner(command, **_kwargs):
        calls.append(command)
        if command[1] == "find-generic-password" and command[-1] == "-w":
            return subprocess.CompletedProcess(command, 0, stdout=(SENTINEL + "\n").encode())
        return subprocess.CompletedProcess(command, 0, stdout=b"")

    secret_store = MacOSKeychainSecretStore(runner=runner, system="Darwin")
    assert secret_store.exists()
    assert secret_store.retrieve() == SENTINEL
    assert secret_store.delete()
    with pytest.raises(OwnerRuntimeError, match="currently supported on macOS"):
        MacOSKeychainSecretStore(runner=runner, system="Linux").exists()
    assert SENTINEL not in repr(calls)


def test_first_setup_checks_database_and_stores_keychain_secret(tmp_path: Path) -> None:
    answers = iter(["", "", "", "owner_test", "", "", ""])
    output: list[str] = []
    secrets = FakeSecretStore(value=None)
    target = store(tmp_path)
    result = setup_owner_runtime(
        config_store=target,
        secret_store=secrets,
        repo_root=Path.cwd(),
        reader=lambda _prompt: next(answers),
        writer=output.append,
        database_inspector=inspection,
    )
    assert target.load() == result
    assert ("store", False) in secrets.operations
    assert "Setup complete. Daily startup: make owner-start" in output
    assert SENTINEL not in "\n".join(output) + target.path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("answers", "operation"),
    [
        (["", "", "", "", "", "", "", ""], None),
        (["", "", "", "", "", "", "", "r", "replace-openalex"], ("store", True)),
    ],
)
def test_setup_keeps_or_replaces_existing_key(
    tmp_path: Path, answers: list[str], operation: tuple[str, bool] | None
) -> None:
    target = write_config(tmp_path)
    secrets = FakeSecretStore()
    setup_owner_runtime(
        config_store=target,
        secret_store=secrets,
        repo_root=Path.cwd(),
        reader=lambda _prompt: answers.pop(0),
        writer=lambda _message: None,
        database_inspector=inspection,
    )
    assert (operation in secrets.operations) if operation else not any(
        item[0] == "store" for item in secrets.operations
    )


def test_remove_secret_requires_exact_confirmation() -> None:
    secrets = FakeSecretStore()
    with pytest.raises(OwnerRuntimeError, match="cancelled"):
        remove_owner_secret(secret_store=secrets, reader=lambda _prompt: "yes")
    remove_owner_secret(
        secret_store=secrets,
        reader=lambda _prompt: "remove-openalex",
        writer=lambda _message: None,
    )
    assert secrets.value is None


def test_owner_start_builds_backend_only_secret_environment_and_safe_output(
    tmp_path: Path,
) -> None:
    target = write_config(tmp_path)
    captured: dict[str, object] = {}
    output: list[str] = []

    def launcher(**kwargs) -> None:
        captured.update(kwargs)
        captured["backend_environment"] = dict(kwargs["backend_environment"])
        captured["frontend_environment"] = dict(kwargs["frontend_environment"])

    start_owner_runtime(
        config_store=target,
        secret_store=FakeSecretStore(),
        repo_root=Path.cwd(),
        writer=output.append,
        database_inspector=inspection,
        port_checker=lambda _host, _port: True,
        launcher=launcher,
        environment={
            "PATH": os.environ["PATH"],
            "REAGENT_DATABASE_URL": "must-not-win",
            "REAGENT_OPENALEX_API_KEY": "parent-must-not-win",
            "OPENALEX_API_KEY": "parent-must-not-win",
            "OPENAI_API_KEY": "parent-must-not-win",
            "ANTHROPIC_API_KEY": "parent-must-not-win",
        },
    )
    backend = captured["backend_environment"]
    frontend = captured["frontend_environment"]
    assert backend["REAGENT_OPENALEX_API_KEY"] == SENTINEL
    assert backend["REAGENT_DATABASE_URL"] == config().database_url()
    assert backend["REAGENT_DEPLOYMENT_PROFILE"] == "local-development"
    assert backend["REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED"] == "1"
    assert frontend == {
        "PATH": os.environ["PATH"],
        "REAGENT_API_URL": "http://127.0.0.1:8000",
    }
    assert SENTINEL not in "\n".join(output)
    assert captured["runtime_dir"] == owner_runtime_directory(target.path)


def test_environment_scrub_is_generic_across_provider_credentials() -> None:
    backend, frontend = build_owner_environments(
        config=config(),
        secret=SENTINEL,
        runtime_dir=Path("/tmp/reagent-owner-unit"),
        environment={
            "PATH": "/usr/bin",
            "REAGENT_PROXY_TOKEN": "proxy-secret",
            "REAGENT_LOCAL_SESSION_TOKEN": "session-secret",
            "REAGENT_OPENALEX_API_KEY": "wrong-secret",
            "OPENALEX_API_KEY": "wrong-secret",
            "OPENAI_API_KEY": "wrong-secret",
            "ANTHROPIC_API_KEY": "wrong-secret",
        },
    )
    assert backend["REAGENT_OPENALEX_API_KEY"] == SENTINEL
    assert "REAGENT_PROXY_TOKEN" not in backend
    assert set(frontend) == {"PATH", "REAGENT_API_URL"}


def test_owner_start_fails_before_launch_for_missing_key_or_migration(tmp_path: Path) -> None:
    target = write_config(tmp_path)
    launched = False

    def launcher(**_kwargs) -> None:
        nonlocal launched
        launched = True

    with pytest.raises(OwnerRuntimeError, match="credential is missing"):
        start_owner_runtime(
            config_store=target,
            secret_store=FakeSecretStore(None),
            repo_root=Path.cwd(),
            database_inspector=inspection,
            port_checker=lambda _host, _port: True,
            launcher=launcher,
        )
    assert not launched

    with pytest.raises(OwnerRuntimeError, match="Backend port 8000 is occupied"):
        start_owner_runtime(
            config_store=target,
            secret_store=FakeSecretStore(),
            repo_root=Path.cwd(),
            database_inspector=inspection,
            port_checker=lambda _host, port: port != 8000,
            launcher=launcher,
        )
    assert not launched

    def behind(value: OwnerRuntimeConfig, _repo: Path) -> DatabaseInspection:
        return DatabaseInspection(True, value.database.database, value.database.user, "old", HEAD)

    with pytest.raises(OwnerRuntimeError, match="migration mismatch"):
        start_owner_runtime(
            config_store=target,
            secret_store=FakeSecretStore(),
            repo_root=Path.cwd(),
            database_inspector=behind,
            port_checker=lambda _host, _port: True,
            launcher=launcher,
        )
    assert not launched


def test_doctor_is_bounded_and_does_not_retrieve_secret(tmp_path: Path) -> None:
    target = write_config(tmp_path)
    secrets = FakeSecretStore()
    output: list[str] = []
    assert doctor_owner_runtime(
        config_store=target,
        secret_store=secrets,
        repo_root=Path.cwd(),
        writer=output.append,
        database_inspector=inspection,
        port_checker=lambda _host, _port: True,
    )
    assert ("retrieve", None) not in secrets.operations
    assert SENTINEL not in "\n".join(output)
    assert "OpenAlex credential: configured" in output


def test_makefile_preserves_three_runtime_authorities() -> None:
    repo = Path(__file__).resolve().parents[2]
    source = (repo / "Makefile").read_text(encoding="utf-8")
    assert "owner-setup:" in source and "owner_runtime.py setup" in source
    assert "owner-start:" in source and "owner_runtime.py start" in source
    assert "owner-doctor:" in source and "owner_runtime.py doctor" in source
    assert "dev:\n\t./scripts/dev-start.sh" in source
    assert "controlled-start:\n\tREAGENT_STARTUP_MODE=controlled ./scripts/dev-start.sh" in source
    assert "owner_runtime.py" not in (repo / "scripts/dev-start.sh").read_text(encoding="utf-8")
    qualification = (repo / "scripts/run_isolated_qualification.py").read_text(encoding="utf-8")
    assert "MacOSKeychainSecretStore" not in qualification
    owner_source = (repo / "scripts/owner_runtime.py").read_text(encoding="utf-8")
    assert 'os.environ.get("REAGENT_AUTOMATED_QUALIFICATION") != "1"' in owner_source


def test_direct_script_start_before_setup_is_friendly_without_traceback(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    environment = {
        **os.environ,
        "XDG_CONFIG_HOME": str(tmp_path / "xdg"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    result = subprocess.run(
        [os.sys.executable, "scripts/owner_runtime.py", "start"],
        cwd=repo,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "Run: make owner-setup" in result.stderr
    assert "Traceback" not in result.stdout + result.stderr


def test_process_identity_preserves_ps_format_used_by_existing_stop_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = " Tue Aug 11 21:31:27 2026    "
    monkeypatch.setattr(
        owner_runtime_module.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            ["ps"], 0, stdout=expected + "\n"
        ),
    )
    assert _process_identity(12345) == expected


@pytest.mark.parametrize(("connect_result", "available"), [(0, False), (61, True)])
def test_port_check_probes_for_an_actual_listener(
    monkeypatch: pytest.MonkeyPatch,
    connect_result: int,
    available: bool,
) -> None:
    class Probe:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def settimeout(self, _timeout: float) -> None:
            pass

        def connect_ex(self, endpoint: tuple[str, int]) -> int:
            assert endpoint == ("127.0.0.1", 8123)
            return connect_result

        def close(self) -> None:
            pass

    monkeypatch.setattr(owner_runtime_module.socket, "socket", Probe)
    assert _port_available("127.0.0.1", 8123) is available
