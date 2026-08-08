"""Real PostgreSQL qualification for privacy-safe OpenAlex Proxy metadata."""

from __future__ import annotations

import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import inspect, text

from backend.cloud_api_proxy import CloudAPIProxyService
from backend.cloud_api_proxy.contracts import (
    OPENALEX_ADAPTER_ID,
    PaperSearchV01Request,
    canonical_json,
    format_timestamp,
)
from backend.cloud_api_proxy.errors import ProxyError
from backend.cloud_api_proxy.sql import SQLProxyUnitOfWork
from backend.cloud_api_proxy.tests.conftest import CHECKSUM_A, CHECKSUM_B, NOW, make_request
from backend.cloud_api_proxy.tests.test_openalex_adapter import (
    ScriptedTransport,
    _adapter,
    _response,
)
from backend.database import create_postgres_engine, create_session_factory
from backend.database.orm import Base


@pytest.fixture(scope="module")
def r3ci_engine():
    database_url = os.environ.get("REAGENT_TEST_DATABASE_URL")
    if not database_url:
        pytest.fail("R3C-I PostgreSQL tests require REAGENT_TEST_DATABASE_URL and may not skip")
    engine = create_postgres_engine(database_url)
    with engine.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    if revision != "20260806_0014":
        engine.dispose()
        pytest.fail("R3C-I PostgreSQL database must be at 20260806_0014")
    yield engine
    engine.dispose()


@pytest.fixture()
def sql_openalex_setup(r3ci_engine):
    table_names = ", ".join(f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables))
    with r3ci_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
    session_factory = create_session_factory(r3ci_engine)
    transport = ScriptedTransport([_response()])
    key_marker = secrets.token_urlsafe(32)
    adapter, _ = _adapter(transport, key=key_marker)
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: SQLProxyUnitOfWork(session_factory),
        adapters={adapter.adapter_id: adapter},
        clock=lambda: NOW,
    )
    token, plaintext = service.issue_token(
        tenant_id="fictional-tenant",
        subject_id="fictional-subject",
        project_id="fictional-project",
        package_id="fictional-package",
        package_checksum=CHECKSUM_A,
        workflow_id="literature-search",
        workflow_version="1.0.0",
        workflow_checksum=CHECKSUM_B,
        adapter_id=OPENALEX_ADAPTER_ID,
    )
    return service, adapter, transport, token, plaintext, key_marker, session_factory


def test_openalex_schema_is_exact_cost_privacy_safe_and_hosted_independent(r3ci_engine) -> None:
    inspector = inspect(r3ci_engine)
    token_columns = {item["name"] for item in inspector.get_columns("proxy_capability_tokens")}
    operation_columns = {item["name"] for item in inspector.get_columns("proxy_operations")}
    assert {
        "maximum_provider_calls",
        "used_provider_calls",
        "maximum_provider_cost_microusd",
        "reserved_provider_cost_microusd",
        "reported_provider_cost_microusd",
    } <= token_columns
    assert {
        "request_retention_mode",
        "query_checksum",
        "query_utf8_bytes",
        "query_characters",
        "provider_http_calls",
        "reserved_cost_microusd",
        "reported_cost_microusd",
        "provider_response_checksum",
        "provider_http_status",
        "provider_adapter_version",
        "provider_rate_limit_json",
    } <= operation_columns
    prohibited = {
        "api_key",
        "credential",
        "plaintext_key",
        "query_text",
        "raw_response_body",
        "credentialed_url",
        "workflow_run_id",
        "workflow_step_run_id",
        "hosted_provider_operation_id",
    }
    assert not prohibited & (token_columns | operation_columns)
    assert {item["referred_table"] for item in inspector.get_foreign_keys("proxy_operations")} == {
        "proxy_capability_tokens"
    }
    indexes = {item["name"] for item in inspector.get_indexes("proxy_operations")}
    assert "ix_proxy_operations_adapter_status" in indexes


def test_sql_roundtrip_retains_exact_cost_but_no_query_or_key(sql_openalex_setup) -> None:
    service, adapter, transport, token, plaintext, key_marker, session_factory = sql_openalex_setup
    query_marker = "query-" + uuid4().hex
    request = make_request(parameters=PaperSearchV01Request(query_marker, 1))
    result = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )

    with session_factory() as session:
        operation = session.execute(
            text(
                "SELECT request_json, request_retention_mode, query_checksum, query_utf8_bytes, "
                "query_characters, provider_http_calls, reserved_cost_microusd, "
                "reported_cost_microusd, provider_rate_limit_json, provider_data_json "
                "FROM proxy_operations"
            )
        ).mappings().one()
        stored_token = session.execute(
            text(
                "SELECT admitted_operations, used_provider_calls, maximum_provider_calls, "
                "maximum_provider_cost_microusd, reserved_provider_cost_microusd, "
                "reported_provider_cost_microusd FROM proxy_capability_tokens "
                "WHERE token_id=:token_id"
            ),
            {"token_id": token.scope.token_id},
        ).mappings().one()
        operation_text = session.scalar(text("SELECT row_to_json(t)::text FROM proxy_operations AS t"))
        token_text = session.scalar(text("SELECT row_to_json(t)::text FROM proxy_capability_tokens AS t"))

    assert operation["request_retention_mode"] == "CHECKSUM_ONLY"
    assert "parameters" not in operation["request_json"]
    assert "query" not in operation["request_json"]
    assert operation["query_checksum"].startswith("sha256:")
    assert operation["query_utf8_bytes"] == len(query_marker.encode())
    assert operation["query_characters"] == len(query_marker)
    assert operation["provider_http_calls"] == 1
    assert operation["reserved_cost_microusd"] == 1_000
    assert operation["reported_cost_microusd"] == 1_000
    assert operation["provider_rate_limit_json"]["provider_credits_used"] == "0.001"
    assert stored_token == {
        "admitted_operations": 1,
        "used_provider_calls": 1,
        "maximum_provider_calls": 20,
        "maximum_provider_cost_microusd": 50_000,
        "reserved_provider_cost_microusd": 1_000,
        "reported_provider_cost_microusd": 1_000,
    }
    combined = "\n".join((operation_text, token_text, canonical_json(result)))
    assert query_marker not in combined
    assert key_marker not in combined
    assert plaintext not in combined
    assert adapter.invocation_count == 1
    assert len(transport.calls) == 1


def test_sql_reload_exact_replay_has_zero_second_provider_call(sql_openalex_setup) -> None:
    service, adapter, _, token, plaintext, _, session_factory = sql_openalex_setup
    request = make_request(parameters=PaperSearchV01Request("fictional-reload", 1))
    first = service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=request)
    reloaded_transport = ScriptedTransport([])
    reloaded_adapter, _ = _adapter(reloaded_transport)
    reloaded = CloudAPIProxyService(
        unit_of_work_factory=lambda: SQLProxyUnitOfWork(session_factory),
        adapters={reloaded_adapter.adapter_id: reloaded_adapter},
        clock=lambda: NOW + timedelta(minutes=6),
    )
    by_id = reloaded.get_operation(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        operation_id=first["operation_id"],
    )
    by_key = reloaded.find_operation(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        package_id=request.package_id,
        idempotency_key=request.idempotency_key,
    )
    replay = reloaded.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )
    assert by_id["operation_id"] == by_key["operation_id"] == first["operation_id"]
    assert replay["operation_id"] == first["operation_id"]
    assert replay["idempotency_result"] == "REPLAYED"
    assert adapter.invocation_count == 1
    assert reloaded_adapter.invocation_count == 0
    assert reloaded_transport.calls == []
    with session_factory() as session:
        values = session.execute(
            text(
                "SELECT admitted_operations, used_provider_calls, "
                "reserved_provider_cost_microusd, reported_provider_cost_microusd "
                "FROM proxy_capability_tokens WHERE token_id=:token_id"
            ),
            {"token_id": token.scope.token_id},
        ).mappings().one()
        assert session.scalar(text("SELECT count(*) FROM proxy_operations")) == 1
    assert values == {
        "admitted_operations": 1,
        "used_provider_calls": 1,
        "reserved_provider_cost_microusd": 1_000,
        "reported_provider_cost_microusd": 1_000,
    }


def test_sql_delayed_openalex_conflict_and_stale_new_admission_are_zero_call(
    sql_openalex_setup,
) -> None:
    service, adapter, transport, token, plaintext, _, session_factory = sql_openalex_setup
    request = make_request(parameters=PaperSearchV01Request("fictional-delayed-conflict", 1))
    first = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )
    reloaded_transport = ScriptedTransport([])
    reloaded_adapter, _ = _adapter(reloaded_transport)
    reloaded = CloudAPIProxyService(
        unit_of_work_factory=lambda: SQLProxyUnitOfWork(session_factory),
        adapters={reloaded_adapter.adapter_id: reloaded_adapter},
        clock=lambda: NOW + timedelta(minutes=6),
    )
    changed = make_request(
        idempotency_key=request.idempotency_key,
        parameters=request.parameters,
        client_timestamp=format_timestamp(NOW + timedelta(seconds=1)),
    )
    with pytest.raises(ProxyError) as conflict_error:
        reloaded.submit(
            bearer_token=plaintext,
            path_project_id="fictional-project",
            request=changed,
        )
    with pytest.raises(ProxyError) as stale_error:
        reloaded.submit(
            bearer_token=plaintext,
            path_project_id="fictional-project",
            request=make_request(
                parameters=PaperSearchV01Request("fictional-stale-new", 1),
            ),
        )

    assert conflict_error.value.code == "IDEMPOTENCY_CONFLICT"
    assert stale_error.value.code == "CLIENT_TIMESTAMP_OUT_OF_RANGE"
    assert first["operation_status"] == "SUCCEEDED"
    assert adapter.invocation_count == 1
    assert len(transport.calls) == 1
    assert reloaded_adapter.invocation_count == 0
    assert reloaded_transport.calls == []
    with session_factory() as session:
        assert session.scalar(text("SELECT count(*) FROM proxy_operations")) == 1
        values = session.execute(
            text(
                "SELECT admitted_operations, used_provider_calls, "
                "reserved_provider_cost_microusd, reported_provider_cost_microusd "
                "FROM proxy_capability_tokens WHERE token_id=:token_id"
            ),
            {"token_id": token.scope.token_id},
        ).mappings().one()
    assert values == {
        "admitted_operations": 1,
        "used_provider_calls": 1,
        "reserved_provider_cost_microusd": 1_000,
        "reported_provider_cost_microusd": 1_000,
    }


def test_sql_concurrent_delayed_openalex_replay_and_conflict_keep_exact_cost(
    sql_openalex_setup,
) -> None:
    service, adapter, transport, token, plaintext, _, session_factory = sql_openalex_setup
    request = make_request(parameters=PaperSearchV01Request("fictional-delayed-concurrency", 1))
    first = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )
    reloaded_transport = ScriptedTransport([])
    reloaded_adapter, _ = _adapter(reloaded_transport)
    reloaded = CloudAPIProxyService(
        unit_of_work_factory=lambda: SQLProxyUnitOfWork(session_factory),
        adapters={reloaded_adapter.adapter_id: reloaded_adapter},
        clock=lambda: NOW + timedelta(minutes=6),
    )
    with ThreadPoolExecutor(max_workers=4) as executor:
        replays = list(
            executor.map(
                lambda _: reloaded.submit(
                    bearer_token=plaintext,
                    path_project_id="fictional-project",
                    request=request,
                ),
                range(4),
            )
        )
    changed = make_request(
        idempotency_key=request.idempotency_key,
        parameters=PaperSearchV01Request("fictional-delayed-concurrency-changed", 1),
    )

    def conflict_code(_: int) -> str:
        try:
            reloaded.submit(
                bearer_token=plaintext,
                path_project_id="fictional-project",
                request=changed,
            )
        except ProxyError as error:
            return error.code
        raise AssertionError("changed content was not rejected")

    with ThreadPoolExecutor(max_workers=4) as executor:
        conflicts = list(executor.map(conflict_code, range(4)))

    assert {item["operation_id"] for item in replays} == {first["operation_id"]}
    assert {item["idempotency_result"] for item in replays} == {"REPLAYED"}
    assert conflicts == ["IDEMPOTENCY_CONFLICT"] * 4
    assert adapter.invocation_count == 1
    assert len(transport.calls) == 1
    assert reloaded_adapter.invocation_count == 0
    assert reloaded_transport.calls == []
    with session_factory() as session:
        assert session.scalar(text("SELECT count(*) FROM proxy_operations")) == 1
        values = session.execute(
            text(
                "SELECT admitted_operations, used_provider_calls, "
                "reserved_provider_cost_microusd, reported_provider_cost_microusd "
                "FROM proxy_capability_tokens WHERE token_id=:token_id"
            ),
            {"token_id": token.scope.token_id},
        ).mappings().one()
    assert values == {
        "admitted_operations": 1,
        "used_provider_calls": 1,
        "reserved_provider_cost_microusd": 1_000,
        "reported_provider_cost_microusd": 1_000,
    }


def test_sql_concurrent_exact_replay_reserves_one_call_and_cost(sql_openalex_setup) -> None:
    service, adapter, transport, token, plaintext, _, session_factory = sql_openalex_setup
    request = make_request(parameters=PaperSearchV01Request("fictional-concurrent", 1))
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: service.submit(
                    bearer_token=plaintext,
                    path_project_id="fictional-project",
                    request=request,
                ),
                range(2),
            )
        )
    assert {item["operation_id"] for item in results} == {results[0]["operation_id"]}
    assert adapter.invocation_count == 1
    assert len(transport.calls) == 1
    with session_factory() as session:
        counts = session.execute(
            text(
                "SELECT admitted_operations, used_provider_calls, reserved_provider_cost_microusd, "
                "reported_provider_cost_microusd FROM proxy_capability_tokens WHERE token_id=:token_id"
            ),
            {"token_id": token.scope.token_id},
        ).mappings().one()
        assert counts == {
            "admitted_operations": 1,
            "used_provider_calls": 1,
            "reserved_provider_cost_microusd": 1_000,
            "reported_provider_cost_microusd": 1_000,
        }
        assert session.scalar(text("SELECT count(*) FROM proxy_operations")) == 1


def test_sql_provider_budget_race_admits_only_one_final_operation(sql_openalex_setup) -> None:
    service, adapter, transport, token, plaintext, _, session_factory = sql_openalex_setup
    with session_factory.begin() as session:
        session.execute(
            text(
                "UPDATE proxy_capability_tokens SET admitted_operations=19, used_provider_calls=19, "
                "reserved_provider_cost_microusd=49000 WHERE token_id=:token_id"
            ),
            {"token_id": token.scope.token_id},
        )

    def invoke(request):
        try:
            return service.submit(
                bearer_token=plaintext,
                path_project_id="fictional-project",
                request=request,
            )
        except ProxyError as error:
            return error.code

    requests = (
        make_request(parameters=PaperSearchV01Request("fictional-budget-a", 1)),
        make_request(parameters=PaperSearchV01Request("fictional-budget-b", 1)),
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(invoke, requests))
    assert "PROVIDER_BUDGET_EXHAUSTED" in results
    assert sum(isinstance(item, dict) for item in results) == 1
    assert adapter.invocation_count == 1
    assert len(transport.calls) == 1
    with session_factory() as session:
        values = session.execute(
            text(
                "SELECT admitted_operations, used_provider_calls, reserved_provider_cost_microusd "
                "FROM proxy_capability_tokens WHERE token_id=:token_id"
            ),
            {"token_id": token.scope.token_id},
        ).mappings().one()
    assert values == {
        "admitted_operations": 20,
        "used_provider_calls": 20,
        "reserved_provider_cost_microusd": 50_000,
    }


def test_sql_uncertain_transport_reloads_as_reconciliation_without_reinvoke(r3ci_engine) -> None:
    table_names = ", ".join(f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables))
    with r3ci_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
    session_factory = create_session_factory(r3ci_engine)
    transport = ScriptedTransport([RuntimeError("synthetic uncertain transport")])
    adapter, _ = _adapter(transport)
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: SQLProxyUnitOfWork(session_factory),
        adapters={adapter.adapter_id: adapter},
        clock=lambda: NOW,
    )
    _, plaintext = service.issue_token(
        tenant_id="tenant",
        subject_id="subject",
        project_id="fictional-project",
        package_id="fictional-package",
        package_checksum=CHECKSUM_A,
        workflow_id="literature-search",
        workflow_version="1.0.0",
        workflow_checksum=CHECKSUM_B,
        adapter_id=OPENALEX_ADAPTER_ID,
    )
    request = make_request(parameters=PaperSearchV01Request("fictional-uncertain", 1))
    result = service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=request)
    assert result["operation_status"] == "FAILED"

    with session_factory.begin() as session:
        session.execute(
            text(
                "UPDATE proxy_operations SET status='RUNNING', error_code=NULL, "
                "reconciliation_evidence=NULL WHERE operation_id=:operation_id"
            ),
            {"operation_id": result["operation_id"]},
        )
    reloaded_transport = ScriptedTransport([])
    reloaded_adapter, _ = _adapter(reloaded_transport)
    reloaded = CloudAPIProxyService(
        unit_of_work_factory=lambda: SQLProxyUnitOfWork(session_factory),
        adapters={reloaded_adapter.adapter_id: reloaded_adapter},
        clock=lambda: NOW,
    )
    assert reloaded.reconcile_interrupted() == 1
    replay = reloaded.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )
    assert replay["operation_status"] == "RECONCILIATION_REQUIRED"
    assert reloaded_adapter.invocation_count == 0
    assert reloaded_transport.calls == []
