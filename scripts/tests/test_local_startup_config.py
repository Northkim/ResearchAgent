from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.local_startup_config import (
    StartupConfigurationError,
    parse_dotenv,
    resolve_database_configuration,
    validate_database_url,
)

_LOOPBACK_URL = "postgresql+psycopg://fictional@127.0.0.1:5432/reagent_local_v01"


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_repository_dotenv_resolves_database_url(tmp_path: Path) -> None:
    _write(tmp_path / ".env", f"REAGENT_DATABASE_URL={_LOOPBACK_URL}\n")
    environment = {"UNRELATED_EXPORTED_VALUE": "must-remain"}
    resolved = resolve_database_configuration(
        repo_root=tmp_path,
        environment=environment,
    )
    assert resolved.value == _LOOPBACK_URL
    assert resolved.origin == "REPOSITORY_DOTENV"
    assert environment == {"UNRELATED_EXPORTED_VALUE": "must-remain"}


def test_exported_database_url_precedes_dotenv_without_reading_it(tmp_path: Path) -> None:
    _write(tmp_path / ".env", "this malformed file must not be read\n")
    exported = "postgresql://exported@localhost:5432/reagent_exported"
    resolved = resolve_database_configuration(
        repo_root=tmp_path,
        environment={"REAGENT_DATABASE_URL": exported},
    )
    assert resolved.value == exported
    assert resolved.origin == "EXPORTED_ENVIRONMENT"


def test_custom_env_file_replaces_repository_default(tmp_path: Path) -> None:
    _write(tmp_path / ".env", "repository file must not be parsed\n")
    custom = _write(
        tmp_path / "custom.env",
        f"REAGENT_DATABASE_URL='{_LOOPBACK_URL}'\n",
    )
    resolved = resolve_database_configuration(
        repo_root=tmp_path,
        environment={"REAGENT_ENV_FILE": str(custom)},
    )
    assert resolved.value == _LOOPBACK_URL
    assert resolved.origin == "CUSTOM_DOTENV"


def test_missing_configuration_fails_with_setup_instructions(tmp_path: Path) -> None:
    with pytest.raises(StartupConfigurationError) as captured:
        resolve_database_configuration(repo_root=tmp_path, environment={})
    assert "create .env from config/local-v0.1.example" in str(captured.value)


def test_malformed_dotenv_fails_without_value_disclosure(tmp_path: Path) -> None:
    secret_canary = "fictional-secret-canary"
    malformed = _write(tmp_path / "malformed.env", f"BROKEN {secret_canary}\n")
    environment = os.environ.copy()
    environment.pop("REAGENT_DATABASE_URL", None)
    environment["REAGENT_ENV_FILE"] = str(malformed)
    result = subprocess.run(
        [
            sys.executable,
            "scripts/local_startup_config.py",
            "resolve",
            "--repo-root",
            str(tmp_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "dotenv line 1 is malformed" in result.stderr
    assert secret_canary not in result.stdout + result.stderr


def test_duplicate_dotenv_key_fails_closed(tmp_path: Path) -> None:
    dotenv = _write(
        tmp_path / ".env",
        f"REAGENT_DATABASE_URL={_LOOPBACK_URL}\n"
        f"REAGENT_DATABASE_URL={_LOOPBACK_URL}\n",
    )
    with pytest.raises(StartupConfigurationError, match="duplicates an earlier key"):
        parse_dotenv(dotenv)


@pytest.mark.parametrize(
    "literal",
    ["$(touch {marker})", "`touch {marker}`"],
)
def test_dotenv_command_syntax_is_literal_and_never_executed(
    tmp_path: Path,
    literal: str,
) -> None:
    marker = tmp_path / "must-not-exist"
    value = literal.format(marker=marker)
    _write(tmp_path / ".env", f"REAGENT_DATABASE_URL={value}\n")
    resolved = resolve_database_configuration(repo_root=tmp_path, environment={})
    assert resolved.value == value
    assert not marker.exists()
    with pytest.raises(StartupConfigurationError):
        validate_database_url(resolved.value)


def test_blank_lines_comments_and_unrelated_values_are_safe(tmp_path: Path) -> None:
    dotenv = _write(
        tmp_path / ".env",
        "\n  # local comment\nUNRELATED_VALUE=preserved punctuation:/?#[]@!$&'()*+,;=\n"
        f"REAGENT_DATABASE_URL={_LOOPBACK_URL}\n\n",
    )
    parsed = parse_dotenv(dotenv)
    assert parsed["REAGENT_DATABASE_URL"] == _LOOPBACK_URL
    assert parsed["UNRELATED_VALUE"].startswith("preserved punctuation")


@pytest.mark.parametrize("quote", ["'", '"'])
def test_quoted_postgresql_url_is_supported(tmp_path: Path, quote: str) -> None:
    _write(
        tmp_path / ".env",
        f"REAGENT_DATABASE_URL={quote}{_LOOPBACK_URL}{quote}\n",
    )
    resolved = resolve_database_configuration(repo_root=tmp_path, environment={})
    assert resolved.value == _LOOPBACK_URL
    validate_database_url(resolved.value)


@pytest.mark.parametrize(
    ("url", "safe_error"),
    [
        (
            "postgresql://fictional@database.example:5432/reagent_local_v01",
            "loopback-only",
        ),
        (
            "postgresql://fictional@127.0.0.1:5432/ProjectDB",
            "ProjectDB",
        ),
    ],
)
def test_database_safety_checks_remain_after_dotenv_resolution(
    tmp_path: Path,
    url: str,
    safe_error: str,
) -> None:
    _write(tmp_path / ".env", f"REAGENT_DATABASE_URL={url}\n")
    resolved = resolve_database_configuration(repo_root=tmp_path, environment={})
    with pytest.raises(StartupConfigurationError, match=safe_error):
        validate_database_url(resolved.value)


def test_repository_env_remains_ignored() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", ".env"],
        cwd=repo_root,
        check=False,
    )
    assert result.returncode == 0
    assert subprocess.run(
        ["git", "ls-files", "--error-unmatch", ".env"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    ).returncode != 0
