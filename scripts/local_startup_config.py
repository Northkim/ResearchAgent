"""Resolve local V0.1 database configuration without executing dotenv text."""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)[ \t]*=(.*)$")
_DATABASE_KEY = "REAGENT_DATABASE_URL"
_ENV_FILE_KEY = "REAGENT_ENV_FILE"


class StartupConfigurationError(ValueError):
    """A value-free local startup configuration failure."""


@dataclass(frozen=True, slots=True)
class ResolvedDatabaseConfiguration:
    value: str
    origin: str


def parse_dotenv(path: Path) -> dict[str, str]:
    """Parse a strict, non-interpolating dotenv subset without evaluating it."""

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise StartupConfigurationError(
            "the selected dotenv file cannot be read as UTF-8"
        ) from error
    if "\x00" in text:
        raise StartupConfigurationError("the selected dotenv file contains invalid data")

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _ASSIGNMENT.fullmatch(line)
        if match is None:
            raise StartupConfigurationError(
                f"dotenv line {line_number} is malformed"
            )
        key, raw_value = match.groups()
        if not _KEY.fullmatch(key):
            raise StartupConfigurationError(
                f"dotenv line {line_number} has an invalid key"
            )
        if key in values:
            raise StartupConfigurationError(
                f"dotenv line {line_number} duplicates an earlier key"
            )

        candidate = raw_value.strip()
        if candidate.startswith(("'", '"')):
            quote = candidate[0]
            if len(candidate) < 2 or candidate[-1] != quote:
                raise StartupConfigurationError(
                    f"dotenv line {line_number} has an unterminated quoted value"
                )
            candidate = candidate[1:-1]
        if any(ord(character) < 32 or ord(character) == 127 for character in candidate):
            raise StartupConfigurationError(
                f"dotenv line {line_number} contains a prohibited control character"
            )
        values[key] = candidate
    return values


def resolve_database_configuration(
    *,
    repo_root: Path,
    environment: Mapping[str, str] | None = None,
) -> ResolvedDatabaseConfiguration:
    """Resolve exported configuration before an optional custom/root dotenv."""

    environ = os.environ if environment is None else environment
    if _DATABASE_KEY in environ:
        value = environ[_DATABASE_KEY]
        if not value:
            raise StartupConfigurationError(
                "the exported REAGENT_DATABASE_URL is empty"
            )
        return ResolvedDatabaseConfiguration(value=value, origin="EXPORTED_ENVIRONMENT")

    if _ENV_FILE_KEY in environ:
        configured_path = environ[_ENV_FILE_KEY]
        if not configured_path:
            raise StartupConfigurationError("REAGENT_ENV_FILE is set but empty")
        dotenv_path = Path(configured_path).expanduser()
        origin = "CUSTOM_DOTENV"
        missing_message = "the selected REAGENT_ENV_FILE does not exist"
    else:
        dotenv_path = repo_root / ".env"
        origin = "REPOSITORY_DOTENV"
        missing_message = (
            "REAGENT_DATABASE_URL is not exported and repository .env does not exist; "
            "create .env from config/local-v0.1.example"
        )

    if not dotenv_path.exists():
        raise StartupConfigurationError(missing_message)
    if not dotenv_path.is_file():
        raise StartupConfigurationError("the selected dotenv path is not a regular file")

    values = parse_dotenv(dotenv_path)
    value = values.get(_DATABASE_KEY)
    if value is None:
        raise StartupConfigurationError(
            "the selected dotenv file does not define REAGENT_DATABASE_URL"
        )
    if not value:
        raise StartupConfigurationError(
            "the selected dotenv file defines an empty REAGENT_DATABASE_URL"
        )
    return ResolvedDatabaseConfiguration(value=value, origin=origin)


def validate_database_url(value: str) -> None:
    """Apply the existing local PostgreSQL identity restrictions safely."""

    if not value or any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise StartupConfigurationError("REAGENT_DATABASE_URL is malformed")
    try:
        from sqlalchemy.engine import make_url

        url = make_url(value)
    except Exception as error:
        raise StartupConfigurationError("REAGENT_DATABASE_URL is malformed") from error
    if url.get_backend_name() != "postgresql":
        raise StartupConfigurationError("database configuration must use PostgreSQL")
    if url.host not in {"127.0.0.1", "localhost", "::1"}:
        raise StartupConfigurationError("database configuration must be loopback-only")
    if (url.database or "").casefold() == "projectdb":
        raise StartupConfigurationError(
            "ProjectDB is not the V0.1 local product database"
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    resolve = subparsers.add_parser("resolve")
    resolve.add_argument("--repo-root", type=Path, required=True)
    subparsers.add_parser("validate")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "resolve":
            resolved = resolve_database_configuration(repo_root=arguments.repo_root)
            # The startup shell captures this output; it is never logged.
            sys.stdout.write(f"{resolved.origin}\n{resolved.value}")
        else:
            validate_database_url(os.environ.get(_DATABASE_KEY, ""))
    except StartupConfigurationError as error:
        print(f"ReAgent V0.1 startup configuration error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
