"""Real PostgreSQL qualification for R3B Proxy identity and concurrency."""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event

import pytest
from sqlalchemy import inspect, text

from backend.cloud_api_proxy import CloudAPIProxyService, DeterministicFakePaperSearchAdapter
from backend.cloud_api_proxy.contracts import (
    ADAPTER_ID,
    LOCAL_PROGRESS_ADAPTER_ID,
    LOCAL_PROGRESS_SESSION_CAPABILITY,
    LOCAL_PROGRESS_READ_CAPABILITY,
    LOCAL_PROGRESS_UPLOAD_CAPABILITY,
    LocalProgressReportScope,
)
from backend.cloud_api_proxy.errors import ProxyError
from backend.cloud_api_proxy.sql import SQLProxyUnitOfWork
from backend.database import create_postgres_engine, create_session_factory
from backend.database.orm import Base

from backend.cloud_api_proxy.tests.conftest import CHECKSUM_A, CHECKSUM_B, NOW, make_request
from backend.cloud_api_proxy.contracts import PaperSearchV01Request, format_timestamp


@pytest.fixture(scope="module")
def r3b_engine():
    database_url = os.environ.get("REAGENT_TEST_DATABASE_URL")
    if not database_url:
        pytest.fail("R3B PostgreSQL tests require REAGENT_TEST_DATABASE_URL and may not skip")
    engine = create_postgres_engine(database_url)
    with engine.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    if revision != "20260806_0014":
        engine.dispose()
        pytest.fail("Proxy PostgreSQL database must be at 20260806_0014")
    yield engine
    engine.dispose()


@pytest.fixture()
def sql_proxy_setup(r3b_engine):
    table_names = ", ".join(f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables))
    with r3b_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
    session_factory = create_session_factory(r3b_engine)
    adapter = DeterministicFakePaperSearchAdapter()
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: SQLProxyUnitOfWork(session_factory),
        adapter=adapter,
        clock=lambda: NOW,
    )
    token, plaintext = service.issue_token(
        tenant_id="fictional-tenant", subject_id="fictional-subject",
        project_id="fictional-project", package_id="fictional-package",
        package_checksum=CHECKSUM_A, workflow_id="literature-search",
        workflow_version="1.0.0", workflow_checksum=CHECKSUM_B,
    )
    return service, adapter, token, plaintext, session_factory


def test_proxy_schema_is_independent_and_digest_only(r3b_engine) -> None:
    inspector = inspect(r3b_engine)
    assert {"proxy_capability_tokens", "proxy_operations"} <= set(inspector.get_table_names())
    token_columns = {column["name"] for column in inspector.get_columns("proxy_capability_tokens")}
    assert "token_digest_sha256" in token_columns
    assert "local_session_capabilities_json" in token_columns
    assert not {"token", "plaintext_token", "authorization_header"} & token_columns
    operation_fks = inspector.get_foreign_keys("proxy_operations")
    assert {fk["referred_table"] for fk in operation_fks} == {"proxy_capability_tokens"}
    unique_names = {item["name"] for item in inspector.get_unique_constraints("proxy_operations")}
    assert "uq_proxy_operations_scoped_idempotency" in unique_names


def test_local_session_scope_persists_and_authorizes_after_reload(
    sql_proxy_setup,
) -> None:
    service, adapter, _, _, session_factory = sql_proxy_setup
    token, plaintext = service.issue_token(
        tenant_id="local-v0-1",
        subject_id="fictional-owner",
        project_id="fictional-project",
        package_id="fictional-package",
        package_checksum=CHECKSUM_A,
        workflow_id="literature-search",
        workflow_version="1.0.0",
        workflow_checksum=CHECKSUM_B,
        maximum_operations=0,
        adapter_id=LOCAL_PROGRESS_ADAPTER_ID,
        local_session_capabilities=(
            LOCAL_PROGRESS_UPLOAD_CAPABILITY,
            LOCAL_PROGRESS_READ_CAPABILITY,
        ),
        local_progress_report_scope=LocalProgressReportScope(
            execution_round=1,
            report_id="prv2-" + "a" * 64,
            report_content_checksum=CHECKSUM_A,
        ),
        capability=LOCAL_PROGRESS_SESSION_CAPABILITY,
    )
    reloaded = CloudAPIProxyService(
        unit_of_work_factory=lambda: SQLProxyUnitOfWork(session_factory),
        adapter=adapter,
        clock=lambda: NOW,
    )
    authorized = reloaded.authorize_local_session_capability(
        bearer_token=plaintext,
        token_id=token.scope.token_id,
        project_id="fictional-project",
        package_id="fictional-package",
        package_checksum=CHECKSUM_A,
        workflow_id="literature-search",
        workflow_version="1.0.0",
        workflow_checksum=CHECKSUM_B,
        capability=LOCAL_PROGRESS_READ_CAPABILITY,
    )
    assert authorized.scope.maximum_operations == 0
    assert authorized.scope.local_session_capabilities == (
        LOCAL_PROGRESS_READ_CAPABILITY,
        LOCAL_PROGRESS_UPLOAD_CAPABILITY,
    )
    assert authorized.scope.adapter_id == LOCAL_PROGRESS_ADAPTER_ID
    assert authorized.scope.local_progress_report_scope == LocalProgressReportScope(
        execution_round=1,
        report_id="prv2-" + "a" * 64,
        report_content_checksum=CHECKSUM_A,
    )
    with session_factory() as session:
        assert session.scalar(text("SELECT count(*) FROM proxy_operations")) == 0


def test_sql_roundtrip_reload_and_exact_replay(sql_proxy_setup) -> None:
    service, adapter, token, plaintext, session_factory = sql_proxy_setup
    request = make_request()
    first = service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=request)
    reloaded_adapter = DeterministicFakePaperSearchAdapter()
    reloaded = CloudAPIProxyService(
        unit_of_work_factory=lambda: SQLProxyUnitOfWork(session_factory),
        adapter=reloaded_adapter,
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
    replay = reloaded.submit(bearer_token=plaintext, path_project_id="fictional-project", request=request)
    assert by_id["operation_id"] == by_key["operation_id"] == first["operation_id"]
    assert replay["operation_id"] == first["operation_id"]
    assert replay["idempotency_result"] == "REPLAYED"
    assert adapter.invocation_count == 1
    assert reloaded_adapter.invocation_count == 0
    with session_factory() as session:
        assert session.scalar(text("SELECT count(*) FROM proxy_operations")) == 1
        assert session.scalar(text("SELECT admitted_operations FROM proxy_capability_tokens WHERE token_id=:token_id"), {"token_id": token.scope.token_id}) == 1
        stored = session.scalar(text("SELECT token_digest_sha256 FROM proxy_capability_tokens WHERE token_id=:token_id"), {"token_id": token.scope.token_id})
        assert stored != plaintext


def test_sql_delayed_conflict_and_stale_new_admission_preserve_existing_row(
    sql_proxy_setup,
) -> None:
    service, adapter, token, plaintext, session_factory = sql_proxy_setup
    request = make_request()
    first = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )
    reloaded_adapter = DeterministicFakePaperSearchAdapter()
    reloaded = CloudAPIProxyService(
        unit_of_work_factory=lambda: SQLProxyUnitOfWork(session_factory),
        adapter=reloaded_adapter,
        clock=lambda: NOW + timedelta(minutes=6),
    )
    changed = make_request(
        idempotency_key=request.idempotency_key,
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
            request=make_request(),
        )

    assert conflict_error.value.code == "IDEMPOTENCY_CONFLICT"
    assert stale_error.value.code == "CLIENT_TIMESTAMP_OUT_OF_RANGE"
    assert adapter.invocation_count == 1
    assert reloaded_adapter.invocation_count == 0
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
        "used_provider_calls": 0,
        "reserved_provider_cost_microusd": 0,
        "reported_provider_cost_microusd": 0,
    }
    assert first["operation_status"] == "SUCCEEDED"


def test_sql_concurrent_delayed_replays_and_conflicts_are_stable(sql_proxy_setup) -> None:
    service, adapter, token, plaintext, session_factory = sql_proxy_setup
    request = make_request()
    first = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )
    reloaded_adapter = DeterministicFakePaperSearchAdapter()
    reloaded = CloudAPIProxyService(
        unit_of_work_factory=lambda: SQLProxyUnitOfWork(session_factory),
        adapter=reloaded_adapter,
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
        parameters=PaperSearchV01Request(query="delayed conflicting fictional content"),
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
    assert reloaded_adapter.invocation_count == 0
    with session_factory() as session:
        assert session.scalar(text("SELECT count(*) FROM proxy_operations")) == 1
        assert session.scalar(
            text(
                "SELECT admitted_operations FROM proxy_capability_tokens "
                "WHERE token_id=:token_id"
            ),
            {"token_id": token.scope.token_id},
        ) == 1


def test_concurrent_exact_replay_creates_one_effective_operation(sql_proxy_setup) -> None:
    service, adapter, _, plaintext, session_factory = sql_proxy_setup
    request = make_request()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(
            lambda _: service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=request),
            range(2),
        ))
    assert {item["operation_id"] for item in results} == {results[0]["operation_id"]}
    assert adapter.invocation_count == 1
    with session_factory() as session:
        assert session.scalar(text("SELECT count(*) FROM proxy_operations")) == 1
        assert session.scalar(text("SELECT max(admitted_operations) FROM proxy_capability_tokens")) == 1


def test_concurrent_changed_content_conflicts_before_second_adapter_call(sql_proxy_setup) -> None:
    service, adapter, _, plaintext, session_factory = sql_proxy_setup
    first = make_request()
    changed = make_request(
        idempotency_key=first.idempotency_key,
        parameters=PaperSearchV01Request(query="changed fictional content"),
    )

    def invoke(request):
        try:
            return service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=request)
        except ProxyError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(invoke, (first, changed)))
    assert "IDEMPOTENCY_CONFLICT" in results
    assert sum(isinstance(item, dict) for item in results) == 1
    assert adapter.invocation_count == 1
    with session_factory() as session:
        assert session.scalar(text("SELECT count(*) FROM proxy_operations")) == 1
        assert session.scalar(text("SELECT max(admitted_operations) FROM proxy_capability_tokens")) == 1


def test_sql_operation_count_race_admits_only_one_when_limit_is_one(sql_proxy_setup) -> None:
    service, adapter, _, _, session_factory = sql_proxy_setup
    _, plaintext = service.issue_token(
        tenant_id="limited-tenant", subject_id="limited-subject",
        project_id="fictional-project", package_id="fictional-package",
        package_checksum=CHECKSUM_A, workflow_id="literature-search",
        workflow_version="1.0.0", workflow_checksum=CHECKSUM_B,
        maximum_operations=1,
    )

    def invoke(request):
        try:
            return service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=request)
        except ProxyError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(invoke, (make_request(), make_request())))
    assert "OPERATION_LIMIT_EXHAUSTED" in results
    assert sum(isinstance(item, dict) for item in results) == 1
    with session_factory() as session:
        assert session.scalar(text("SELECT max(admitted_operations) FROM proxy_capability_tokens")) == 1


class SQLInterruptingAdapter:
    adapter_id = ADAPTER_ID
    invocation_count = 0

    def search(self, request):
        self.invocation_count += 1
        raise KeyboardInterrupt()


def test_running_reload_becomes_reconciliation_required_without_reinvoke(sql_proxy_setup) -> None:
    _, _, _, plaintext, session_factory = sql_proxy_setup
    adapter = SQLInterruptingAdapter()
    interrupted = CloudAPIProxyService(
        unit_of_work_factory=lambda: SQLProxyUnitOfWork(session_factory),
        adapter=adapter,
        clock=lambda: NOW,
    )
    request = make_request()
    with pytest.raises(KeyboardInterrupt):
        interrupted.submit(bearer_token=plaintext, path_project_id="fictional-project", request=request)
    assert interrupted.reconcile_interrupted() == 1
    replay = interrupted.submit(bearer_token=plaintext, path_project_id="fictional-project", request=request)
    assert replay["operation_status"] == "RECONCILIATION_REQUIRED"
    assert adapter.invocation_count == 1


class SQLBlockingAdapter(DeterministicFakePaperSearchAdapter):
    def __init__(self, entered: Event, release: Event) -> None:
        super().__init__()
        self.entered = entered
        self.release = release

    def search(self, request):
        self.entered.set()
        self.release.wait(timeout=3)
        return super().search(request)


def test_sql_concurrent_active_limit_is_transactionally_enforced(sql_proxy_setup) -> None:
    _, _, _, plaintext, session_factory = sql_proxy_setup
    entered = Event()
    release = Event()
    adapter = SQLBlockingAdapter(entered, release)
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: SQLProxyUnitOfWork(session_factory),
        adapter=adapter,
        clock=lambda: NOW,
    )
    requests = (make_request(), make_request())
    executor = ThreadPoolExecutor(max_workers=2)
    futures = [executor.submit(service.submit, bearer_token=plaintext, path_project_id="fictional-project", request=item) for item in requests]
    entered.wait(timeout=2)
    deadline = time.monotonic() + 3
    active = 0
    while time.monotonic() < deadline:
        with session_factory() as session:
            active = int(session.scalar(text("SELECT count(*) FROM proxy_operations WHERE status IN ('RECEIVED', 'RUNNING')")) or 0)
        if active == 2:
            break
        time.sleep(0.01)
    assert active == 2
    with pytest.raises(ProxyError) as captured:
        service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=make_request())
    release.set()
    for future in futures:
        future.result(timeout=4)
    executor.shutdown()
    assert captured.value.code == "CONCURRENCY_LIMIT_EXCEEDED"
