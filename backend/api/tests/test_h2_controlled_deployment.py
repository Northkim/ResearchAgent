"""H2 controlled-deployment boundaries and operator diagnostics."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.api.deployment import (
    DeploymentConfigurationError,
    DeploymentProfile,
    DeploymentSettings,
)
from backend.api.readiness import check_postgres_readiness
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.progress_reports.aggregation import _project_attention, _workflow_action


def _container() -> ApplicationContainer:
    database = InMemoryDatabase()
    return ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database)
    )


def _controlled_environment(**overrides: str) -> dict[str, str]:
    values = {
        "REAGENT_DEPLOYMENT_PROFILE": "isolated-controlled-test",
        "REAGENT_DATABASE_URL": "postgresql://127.0.0.1:5432/reagent_h2_test",
        "REAGENT_PAPER_SEARCH_PROVIDER": "fake",
        "REAGENT_V0_1_LOCAL_MODE_ENABLED": "1",
        "REAGENT_EXPERIMENTAL_FAKE_PROXY_ENABLED": "1",
        "REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED": "0",
        "REAGENT_ARTIFACT_ROOT": "/private/tmp/reagent-h2-artifacts",
        "REAGENT_LOCAL_PACKAGE_ROOT": "/private/tmp/reagent-h2-packages",
    }
    values.update(overrides)
    return values


def test_controlled_profile_fails_closed_on_unsafe_configuration() -> None:
    valid = DeploymentSettings.from_environment(_controlled_environment())
    assert valid.profile is DeploymentProfile.ISOLATED_CONTROLLED_TEST
    assert not valid.expose_api_docs
    assert not valid.expose_legacy_hosted_routes

    with pytest.raises(DeploymentConfigurationError, match="same-origin"):
        DeploymentSettings.from_environment(
            _controlled_environment(
                REAGENT_CORS_ALLOWED_ORIGINS="https://controlled.example"
            )
        )
    with pytest.raises(DeploymentConfigurationError, match="wildcard"):
        DeploymentSettings.from_environment(
            {"REAGENT_CORS_ALLOWED_ORIGINS": "*"}
        )
    with pytest.raises(DeploymentConfigurationError, match="fake provider"):
        DeploymentSettings.from_environment(
            _controlled_environment(REAGENT_PAPER_SEARCH_PROVIDER="openalex")
        )
    with pytest.raises(DeploymentConfigurationError, match="bounded fake Proxy"):
        DeploymentSettings.from_environment(
            _controlled_environment(REAGENT_EXPERIMENTAL_FAKE_PROXY_ENABLED="0")
        )
    with pytest.raises(DeploymentConfigurationError, match="must not receive"):
        DeploymentSettings.from_environment(
            _controlled_environment(REAGENT_OPENALEX_API_KEY="forbidden-test-value")
        )
    with pytest.raises(DeploymentConfigurationError, match="absolute path"):
        DeploymentSettings.from_environment(
            _controlled_environment(REAGENT_ARTIFACT_ROOT="runtime_data/artifacts")
        )


def test_controlled_app_hides_hosted_surface_and_adds_security_diagnostics() -> None:
    app = create_app(
        _container(),
        deployment_settings=DeploymentSettings.isolated_test_defaults(),
        enable_experimental_proxy=False,
        enable_local_workflow_sessions=False,
    )
    with TestClient(app) as client:
        health = client.get("/health", headers={"X-Request-ID": "tester-request-1"})
        ready = client.get("/ready")
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        assert client.get("/runs").status_code == 404
        assert client.get("/approvals").status_code == 404
        assert client.get("/workflows").status_code == 404
        assert client.get("/projects").status_code == 200

    assert health.status_code == 200
    assert health.headers["x-request-id"] == "tester-request-1"
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert health.headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in health.headers["content-security-policy"]
    assert ready.json() == {
        "status": "ready",
        "checks": {"persistence": "injected"},
    }


def test_optional_development_cors_is_exact_and_never_credentialed() -> None:
    settings = DeploymentSettings.from_environment(
        {"REAGENT_CORS_ALLOWED_ORIGINS": "http://127.0.0.1:3000"}
    )
    with TestClient(create_app(_container(), deployment_settings=settings)) as client:
        response = client.options(
            "/projects",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        rejected = client.options(
            "/projects",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    assert "access-control-allow-credentials" not in response.headers
    assert "access-control-allow-origin" not in rejected.headers


def test_request_limit_and_invalid_request_do_not_echo_research_payload() -> None:
    settings = DeploymentSettings(
        profile=DeploymentProfile.ISOLATED_CONTROLLED_TEST,
        maximum_request_bytes=64 * 1024,
        cors_allowed_origins=(),
        expose_api_docs=False,
        expose_legacy_hosted_routes=False,
    )
    with TestClient(create_app(_container(), deployment_settings=settings)) as client:
        oversized = client.post(
            "/projects",
            content=b"x" * (64 * 1024 + 1),
            headers={"Content-Type": "application/json"},
        )
        invalid = client.post(
            "/projects",
            json={
                "name": "safe",
                "research_topic": "private-research-value",
                "selected_workflow": "INVALID",
            },
        )

    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "REQUEST_BODY_TOO_LARGE"
    assert oversized.headers["x-request-id"] == oversized.json()["error"]["request_id"]
    assert invalid.status_code == 422
    assert "private-research-value" not in invalid.text
    assert "request_id" not in invalid.json()["error"]
    assert invalid.headers["x-request-id"]


def test_unhandled_error_is_safe_and_log_contains_only_correlation_metadata(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(
        _container(), deployment_settings=DeploymentSettings.isolated_test_defaults()
    )

    @app.get("/_h2_failure_probe")
    async def failure_probe() -> None:
        raise RuntimeError("secret-provider-token-and-research-content")

    caplog.set_level(logging.INFO)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/_h2_failure_probe")

    assert response.status_code == 500
    body = response.json()["error"]
    assert body["code"] == "INTERNAL_SERVER_ERROR"
    assert body["request_id"] == response.headers["x-request-id"]
    assert "secret-provider-token" not in response.text
    combined = "\n".join(item.getMessage() for item in caplog.records)
    assert "secret-provider-token" not in combined
    assert body["request_id"] in combined
    request_events = [
        json.loads(item.getMessage())
        for item in caplog.records
        if item.name == "uvicorn.error"
        and json.loads(item.getMessage()).get("event") == "http_request"
    ]
    assert request_events[-1]["status"] == 500
    assert "duration_ms" in request_events[-1]


def test_local_client_download_is_fixed_self_contained_source(tmp_path: Path) -> None:
    with TestClient(
        create_app(
            _container(), deployment_settings=DeploymentSettings.isolated_test_defaults()
        )
    ) as client:
        response = client.get("/local-client/reagent_local.py")

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="reagent_local.py"'
    assert response.headers["x-reagent-cli-sha256"].startswith("sha256:")
    path = tmp_path / "reagent_local.py"
    path.write_bytes(response.content)
    compile(response.content, str(path), "exec")
    assert b"Self-contained Project Workspace lifecycle CLI" in response.content


class _UnavailableEngine:
    def connect(self):
        raise RuntimeError("database URL and password must never be exposed")


class _Result:
    def __init__(self, values: tuple[object, ...]) -> None:
        self.values = values

    def scalars(self):
        return iter(self.values)

    def one(self):
        return self.values


class _Connection:
    def __init__(self, revision: str) -> None:
        self.revision = revision
        self.calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def scalar(self, _statement):
        return 1

    def execute(self, _statement):
        self.calls += 1
        if self.calls == 1:
            return _Result((self.revision,))
        return _Result((True, True, True))


class _ReadyEngine:
    def __init__(self, revision: str = "20260820_0035") -> None:
        self.connection = _Connection(revision)

    def connect(self):
        return self.connection


def test_readiness_reports_database_unavailable_without_exception_details() -> None:
    result = check_postgres_readiness(_UnavailableEngine())  # type: ignore[arg-type]
    assert not result.ready
    assert result.checks == {"database": "unavailable"}


def test_readiness_requires_exact_migration_and_production_registry() -> None:
    ready = check_postgres_readiness(_ReadyEngine())  # type: ignore[arg-type]
    mismatch = check_postgres_readiness(  # type: ignore[arg-type]
        _ReadyEngine("20260806_0012")
    )

    assert ready.ready
    assert ready.checks == {
        "database": "ok",
        "migration": "20260820_0035",
        "production_registry": "ok",
    }
    assert not mismatch.ready
    assert mismatch.checks == {"database": "ok", "migration": "mismatch"}


@pytest.mark.parametrize(
    ("research_status", "installation_state", "readiness", "next_action", "summary", "attention", "actor"),
    [
        ("COMPLETED", "ACKNOWLEDGED_CURRENT", "RESULT_READY", "REVIEW_RESULT", "Done", "COMPLETED", "NONE"),
        ("BLOCKED", "ACKNOWLEDGED_CURRENT", "IN_PROGRESS", "CONTINUE", "Awaiting owner action before drafting.", "OWNER_ACTION_REQUIRED", "OWNER"),
        ("BLOCKED", "ACKNOWLEDGED_CURRENT", "IN_PROGRESS", "CONTINUE", "Resource unavailable", "BLOCKED", "OWNER"),
        ("IN_PROGRESS", "ACKNOWLEDGED_CURRENT", "IN_PROGRESS", "CONTINUE", "ISSUE_RECONCILIATION", "NORMAL", "AGENT"),
        ("NOT_STARTED", "ACKNOWLEDGED_STALE", "NOT_INSTALLED", "SYNC", None, "ATTENTION_REQUIRED", "OWNER"),
        ("FAILED", "ACKNOWLEDGED_CURRENT", "IN_PROGRESS", "CONTINUE", "Evaluation failed", "ATTENTION_REQUIRED", "OWNER"),
    ],
)
def test_task_first_projection_covers_authoritative_workflow_states(
    research_status, installation_state, readiness, next_action, summary, attention, actor,
) -> None:
    action = _workflow_action(
        project_id="project-projection-test",
        workflow_definition_id="writing-local-experimental",
        output_schema_id="manuscript-draft/v3",
        lifecycle="ACTIVE",
        research_status=research_status,
        latest_summary=summary,
        continuation_reason=None,
        installation_state=installation_state,
        readiness=readiness,
        next_action=next_action,
        missing=(),
        latest_artifact=None,
    )
    assert action.attention_state == attention
    assert action.actor == actor
    assert action.expected_output is not None
    assert action.expected_output.label == "Revised manuscript draft"
    if summary == "ISSUE_RECONCILIATION":
        assert action.stage.label == "Issue reconciliation"


def test_task_first_projection_has_an_honest_no_workflow_state() -> None:
    projection = _project_attention(
        recommended=None, latest_activity=None, latest_output=None
    )
    assert projection.action.stage.code == "NO_ACTIVE_WORKFLOW"
    assert projection.action.next_action.surface == "NONE"
