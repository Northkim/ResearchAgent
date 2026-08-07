"""Deployment-profile validation for local and isolated controlled use."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

from sqlalchemy.engine import make_url


class DeploymentConfigurationError(RuntimeError):
    """A safe startup failure caused by invalid deployment configuration."""


class DeploymentProfile(str, Enum):
    LOCAL_DEVELOPMENT = "local-development"
    ISOLATED_CONTROLLED_TEST = "isolated-controlled-test"


@dataclass(frozen=True, slots=True)
class DeploymentSettings:
    profile: DeploymentProfile
    maximum_request_bytes: int
    cors_allowed_origins: tuple[str, ...]
    expose_api_docs: bool
    expose_legacy_hosted_routes: bool

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> "DeploymentSettings":
        values = os.environ if environment is None else environment
        raw_profile = values.get(
            "REAGENT_DEPLOYMENT_PROFILE",
            DeploymentProfile.LOCAL_DEVELOPMENT.value,
        )
        try:
            profile = DeploymentProfile(raw_profile)
        except ValueError as error:
            raise DeploymentConfigurationError(
                "REAGENT_DEPLOYMENT_PROFILE must be 'local-development' or "
                "'isolated-controlled-test'"
            ) from error

        maximum_request_bytes = _bounded_integer(
            values.get("REAGENT_MAX_REQUEST_BYTES", str(1024 * 1024)),
            name="REAGENT_MAX_REQUEST_BYTES",
            minimum=64 * 1024,
            maximum=8 * 1024 * 1024,
        )
        origins = _origins(values.get("REAGENT_CORS_ALLOWED_ORIGINS", ""))

        if profile is DeploymentProfile.ISOLATED_CONTROLLED_TEST:
            _validate_controlled_environment(values, origins=origins)
            return cls(
                profile=profile,
                maximum_request_bytes=maximum_request_bytes,
                cors_allowed_origins=(),
                expose_api_docs=False,
                expose_legacy_hosted_routes=False,
            )
        return cls(
            profile=profile,
            maximum_request_bytes=maximum_request_bytes,
            cors_allowed_origins=origins,
            expose_api_docs=True,
            expose_legacy_hosted_routes=True,
        )

    @classmethod
    def isolated_test_defaults(cls) -> "DeploymentSettings":
        """Return controlled settings for an explicitly injected test container."""

        return cls(
            profile=DeploymentProfile.ISOLATED_CONTROLLED_TEST,
            maximum_request_bytes=1024 * 1024,
            cors_allowed_origins=(),
            expose_api_docs=False,
            expose_legacy_hosted_routes=False,
        )


def _bounded_integer(value: str, *, name: str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise DeploymentConfigurationError(f"{name} must be an integer") from error
    if not minimum <= parsed <= maximum:
        raise DeploymentConfigurationError(
            f"{name} must be between {minimum} and {maximum}"
        )
    return parsed


def _origins(value: str) -> tuple[str, ...]:
    if not value.strip():
        return ()
    result: list[str] = []
    for item in value.split(","):
        candidate = item.strip()
        if candidate == "*":
            raise DeploymentConfigurationError("wildcard CORS origins are prohibited")
        try:
            parsed = urlsplit(candidate)
            port = parsed.port
        except ValueError as error:
            raise DeploymentConfigurationError("CORS origin is malformed") from error
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise DeploymentConfigurationError(
                "CORS origins must be exact http(s) origins without path or credentials"
            )
        normalized = f"{parsed.scheme}://{parsed.hostname}"
        if port is not None:
            normalized += f":{port}"
        if normalized not in result:
            result.append(normalized)
    return tuple(result)


def _enabled(values: Mapping[str, str], name: str) -> bool:
    return values.get(name, "").strip().lower() in {"1", "true", "yes"}


def _validate_controlled_environment(
    values: Mapping[str, str],
    *,
    origins: tuple[str, ...],
) -> None:
    if origins:
        raise DeploymentConfigurationError(
            "isolated controlled testing uses the same-origin Next.js proxy; "
            "REAGENT_CORS_ALLOWED_ORIGINS must be empty"
        )
    database_url = values.get("REAGENT_DATABASE_URL", "")
    if not database_url:
        raise DeploymentConfigurationError(
            "isolated controlled testing requires REAGENT_DATABASE_URL"
        )
    try:
        url = make_url(database_url)
    except Exception as error:
        raise DeploymentConfigurationError("REAGENT_DATABASE_URL is malformed") from error
    if url.get_backend_name() != "postgresql":
        raise DeploymentConfigurationError("controlled testing requires PostgreSQL")
    if url.host not in {"127.0.0.1", "localhost", "::1"}:
        raise DeploymentConfigurationError(
            "controlled testing requires a loopback PostgreSQL endpoint"
        )
    if not url.database or url.database.casefold() == "projectdb":
        raise DeploymentConfigurationError(
            "controlled testing requires a named isolated database other than ProjectDB"
        )
    if values.get("REAGENT_PAPER_SEARCH_PROVIDER", "fake").strip().lower() != "fake":
        raise DeploymentConfigurationError(
            "controlled testing without separate Provider authorization must use the fake provider"
        )
    prohibited_flags = (
        "REAGENT_OPENALEX_LIVE_ENABLED",
        "REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED",
        "REAGENT_EXPERIMENTAL_OPENALEX_STRUCTURAL_DIAGNOSTICS_ENABLED",
    )
    if any(_enabled(values, name) for name in prohibited_flags):
        raise DeploymentConfigurationError(
            "live OpenAlex and structural diagnostics are prohibited in the isolated profile"
        )
    if values.get("REAGENT_OPENALEX_API_KEY", ""):
        raise DeploymentConfigurationError(
            "controlled fake-provider startup must not receive an OpenAlex credential"
        )
    if values.get("REAGENT_V0_1_LOCAL_MODE_ENABLED") != "1":
        raise DeploymentConfigurationError(
            "isolated controlled testing requires REAGENT_V0_1_LOCAL_MODE_ENABLED=1"
        )
    if values.get("REAGENT_EXPERIMENTAL_FAKE_PROXY_ENABLED") != "1":
        raise DeploymentConfigurationError(
            "isolated controlled testing requires the bounded fake Proxy"
        )
    for name in ("REAGENT_ARTIFACT_ROOT", "REAGENT_LOCAL_PACKAGE_ROOT"):
        value = values.get(name, "")
        if not value or not Path(value).is_absolute():
            raise DeploymentConfigurationError(
                f"{name} must be an explicit absolute path in controlled testing"
            )
