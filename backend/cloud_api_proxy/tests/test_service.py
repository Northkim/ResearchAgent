from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Event, Thread
import time
from uuid import uuid4

import pytest

from backend.cloud_api_proxy import CloudAPIProxyService, InMemoryProxyDatabase, InMemoryProxyUnitOfWork
from backend.cloud_api_proxy.contracts import ADAPTER_ID, PaperSearchV01Request, ProxyOperationStatus, canonical_json, format_timestamp
from backend.cloud_api_proxy.errors import ProxyError
from backend.cloud_api_proxy.fake_adapter import DeterministicFakePaperSearchAdapter

from .conftest import CHECKSUM_A, CHECKSUM_B, NOW, make_request


def _mutable_proxy_setup(*, adapter=None, maximum_operations: int | None = None):
    database = InMemoryProxyDatabase()
    selected_adapter = adapter or DeterministicFakePaperSearchAdapter()
    current = [NOW]
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(database),
        adapter=selected_adapter,
        clock=lambda: current[0],
    )
    token, plaintext = service.issue_token(
        tenant_id="fictional-tenant",
        subject_id="fictional-operator",
        project_id="fictional-project",
        package_id="fictional-package",
        package_checksum=CHECKSUM_A,
        workflow_id="literature-search",
        workflow_version="1.0.0",
        workflow_checksum=CHECKSUM_B,
        maximum_operations=maximum_operations,
    )
    return service, database, selected_adapter, token, plaintext, current


def test_token_generation_has_256_random_bits_and_enforces_ratified_bounds() -> None:
    database = InMemoryProxyDatabase()
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(database),
        adapter=DeterministicFakePaperSearchAdapter(),
        clock=lambda: NOW,
    )
    common = {
        "tenant_id": "tenant", "subject_id": "subject", "project_id": "fictional-project",
        "package_id": "fictional-package", "package_checksum": CHECKSUM_A,
        "workflow_id": "literature-search", "workflow_version": "1.0.0",
        "workflow_checksum": CHECKSUM_B,
    }
    _, plaintext = service.issue_token(**common)
    decoded = base64.urlsafe_b64decode(plaintext + "=" * (-len(plaintext) % 4))
    assert len(decoded) == 32
    for overrides in (
        {"lifetime_minutes": 0}, {"lifetime_minutes": 121},
        {"lifetime_minutes": True}, {"maximum_operations": 51},
    ):
        with pytest.raises(ValueError):
            service.issue_token(**common, **overrides)


def test_submit_and_sequential_exact_replay_are_idempotent(proxy_setup) -> None:
    service, database, adapter, token, plaintext = proxy_setup
    request = make_request()
    first = service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=request)
    replay = service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=request)
    assert first["operation_status"] == "SUCCEEDED"
    assert replay["idempotency_result"] == "REPLAYED"
    assert replay["operation_id"] == first["operation_id"]
    assert adapter.invocation_count == 1
    assert len(database.operations) == 1
    assert database.tokens[token.scope.token_id].admitted_operations == 1


def test_delayed_exact_replay_of_succeeded_precedes_timestamp_freshness() -> None:
    service, database, adapter, token, plaintext, current = _mutable_proxy_setup()
    request = make_request()
    first = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )
    current[0] = NOW + timedelta(minutes=6)

    replay = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )

    assert replay["operation_status"] == "SUCCEEDED"
    assert replay["operation_id"] == first["operation_id"]
    assert replay["request_content_checksum"] == first["request_content_checksum"]
    assert replay["response_content_checksum"] == first["response_content_checksum"]
    assert replay["idempotency_result"] == "REPLAYED"
    assert adapter.invocation_count == 1
    assert len(database.operations) == 1
    assert database.tokens[token.scope.token_id].admitted_operations == 1


def test_same_key_changed_content_conflicts_before_adapter(proxy_setup) -> None:
    service, _, adapter, _, plaintext = proxy_setup
    first = make_request()
    service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=first)
    changed = make_request(
        idempotency_key=first.idempotency_key,
        parameters=PaperSearchV01Request(query="changed"),
    )
    with pytest.raises(ProxyError) as captured:
        service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=changed)
    assert captured.value.code == "IDEMPOTENCY_CONFLICT"
    assert adapter.invocation_count == 1


def test_stale_changed_content_conflicts_before_timestamp_freshness() -> None:
    service, database, adapter, token, plaintext, current = _mutable_proxy_setup()
    first = make_request()
    accepted = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=first,
    )
    current[0] = NOW + timedelta(minutes=6)
    changed = make_request(
        idempotency_key=first.idempotency_key,
        parameters=PaperSearchV01Request(query="changed stale fictional content"),
    )

    with pytest.raises(ProxyError) as captured:
        service.submit(
            bearer_token=plaintext,
            path_project_id="fictional-project",
            request=changed,
        )

    assert captured.value.code == "IDEMPOTENCY_CONFLICT"
    assert next(iter(database.operations.values())).operation_id == accepted["operation_id"]
    assert database.tokens[token.scope.token_id].admitted_operations == 1
    assert adapter.invocation_count == 1


def test_existing_key_request_differing_only_in_timestamp_conflicts() -> None:
    service, database, adapter, _, plaintext, current = _mutable_proxy_setup()
    first = make_request()
    accepted = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=first,
    )
    current[0] = NOW + timedelta(minutes=6)
    timestamp_only_change = make_request(
        idempotency_key=first.idempotency_key,
        client_timestamp=format_timestamp(NOW + timedelta(seconds=1)),
    )

    with pytest.raises(ProxyError) as captured:
        service.submit(
            bearer_token=plaintext,
            path_project_id="fictional-project",
            request=timestamp_only_change,
        )

    assert captured.value.code == "IDEMPOTENCY_CONFLICT"
    assert next(iter(database.operations.values())).operation_id == accepted["operation_id"]
    assert adapter.invocation_count == 1


@pytest.mark.parametrize("token", ["", "short", "x" * 43])
def test_missing_malformed_and_unknown_tokens_fail(proxy_setup, token: str) -> None:
    service, _, adapter, _, _ = proxy_setup
    with pytest.raises(ProxyError) as captured:
        service.submit(bearer_token=token, path_project_id="fictional-project", request=make_request())
    assert captured.value.code == "UNAUTHORIZED"
    assert adapter.invocation_count == 0


def test_revoked_and_expired_tokens_fail_before_adapter(proxy_setup) -> None:
    service, database, adapter, token, plaintext = proxy_setup
    service.revoke_token(token.scope.token_id)
    with pytest.raises(ProxyError, match="revoked"):
        service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=make_request())
    assert adapter.invocation_count == 0
    database.tokens[token.scope.token_id] = replace(
        token,
        issued_at=format_timestamp(NOW - timedelta(hours=2)),
        expires_at=format_timestamp(NOW - timedelta(seconds=1)),
        revoked=False,
        revoked_at=None,
    )
    with pytest.raises(ProxyError, match="expired"):
        service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=make_request())


def test_revoked_and_expired_tokens_cannot_delayed_replay_existing_operation() -> None:
    revoked_service, _, revoked_adapter, revoked_token, revoked_plaintext, revoked_now = _mutable_proxy_setup()
    revoked_request = make_request()
    revoked_service.submit(
        bearer_token=revoked_plaintext,
        path_project_id="fictional-project",
        request=revoked_request,
    )
    revoked_now[0] = NOW + timedelta(minutes=6)
    revoked_service.revoke_token(revoked_token.scope.token_id)
    with pytest.raises(ProxyError) as revoked:
        revoked_service.submit(
            bearer_token=revoked_plaintext,
            path_project_id="fictional-project",
            request=revoked_request,
        )
    assert revoked.value.code == "UNAUTHORIZED"
    assert revoked_adapter.invocation_count == 1

    expired_service, expired_database, expired_adapter, expired_token, expired_plaintext, expired_now = _mutable_proxy_setup()
    expired_request = make_request()
    expired_service.submit(
        bearer_token=expired_plaintext,
        path_project_id="fictional-project",
        request=expired_request,
    )
    expired_now[0] = NOW + timedelta(minutes=6)
    expired_database.tokens[expired_token.scope.token_id] = replace(
        expired_database.tokens[expired_token.scope.token_id],
        expires_at=format_timestamp(NOW + timedelta(minutes=5)),
    )
    with pytest.raises(ProxyError) as expired:
        expired_service.submit(
            bearer_token=expired_plaintext,
            path_project_id="fictional-project",
            request=expired_request,
        )
    assert expired.value.code == "UNAUTHORIZED"
    assert expired_adapter.invocation_count == 1


@pytest.mark.parametrize("field,value", [
    ("package_id", "wrong"), ("package_checksum", "sha256:" + "d" * 64),
    ("workflow_id", "wrong"), ("workflow_version", "2.0.0"),
    ("workflow_checksum", "sha256:" + "e" * 64), ("project_id", "wrong"),
])
def test_scope_mismatch_fails_before_adapter(proxy_setup, field: str, value: str) -> None:
    service, _, adapter, _, plaintext = proxy_setup
    request = make_request(**{field: value})
    with pytest.raises(ProxyError) as captured:
        service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=request)
    assert captured.value.code == "AUTHORIZATION_SCOPE_MISMATCH"
    assert adapter.invocation_count == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("project_id", "wrong-project"),
        ("package_id", "wrong-package"),
        ("workflow_id", "wrong-workflow"),
    ],
)
def test_wrong_scope_cannot_probe_delayed_existing_key(field: str, value: str) -> None:
    service, database, adapter, _, plaintext, current = _mutable_proxy_setup()
    first = make_request()
    service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=first,
    )
    current[0] = NOW + timedelta(minutes=6)
    wrong_scope = make_request(idempotency_key=first.idempotency_key, **{field: value})

    with pytest.raises(ProxyError) as captured:
        service.submit(
            bearer_token=plaintext,
            path_project_id="fictional-project",
            request=wrong_scope,
        )

    assert captured.value.code == "AUTHORIZATION_SCOPE_MISMATCH"
    assert len(database.operations) == 1
    assert adapter.invocation_count == 1


def test_stale_and_future_timestamp_fail_before_adapter(proxy_setup) -> None:
    service, _, adapter, _, plaintext = proxy_setup
    for timestamp in (NOW - timedelta(minutes=6), NOW + timedelta(minutes=6)):
        with pytest.raises(ProxyError) as captured:
            service.submit(
                bearer_token=plaintext,
                path_project_id="fictional-project",
                request=make_request(client_timestamp=format_timestamp(timestamp)),
            )
        assert captured.value.code == "CLIENT_TIMESTAMP_OUT_OF_RANGE"
    assert adapter.invocation_count == 0


def test_fresh_new_admission_remains_unchanged() -> None:
    service, database, adapter, _, plaintext, current = _mutable_proxy_setup()
    current[0] = NOW + timedelta(minutes=4)
    request = make_request(client_timestamp=format_timestamp(current[0]))

    result = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )

    assert result["operation_status"] == "SUCCEEDED"
    assert result["idempotency_result"] == "CREATED"
    assert len(database.operations) == 1
    assert adapter.invocation_count == 1


def test_token_operation_limit_counts_admitted_terminal_operations() -> None:
    database = InMemoryProxyDatabase()
    adapter = DeterministicFakePaperSearchAdapter()
    service = CloudAPIProxyService(unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(database), adapter=adapter, clock=lambda: NOW)
    _, plaintext = service.issue_token(
        tenant_id="tenant", subject_id="subject", project_id="fictional-project",
        package_id="fictional-package", package_checksum=CHECKSUM_A,
        workflow_id="literature-search", workflow_version="1.0.0",
        workflow_checksum=CHECKSUM_B, maximum_operations=1,
    )
    service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=make_request())
    with pytest.raises(ProxyError) as captured:
        service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=make_request())
    assert captured.value.code == "OPERATION_LIMIT_EXHAUSTED"


class OversizedAdapter(DeterministicFakePaperSearchAdapter):
    def search(self, request):
        self.invocation_count += 1
        return {"untrusted_provider_data": True, "oversized": "x" * (512 * 1024)}


def test_oversized_result_is_not_persisted_or_delivered() -> None:
    database = InMemoryProxyDatabase()
    adapter = OversizedAdapter()
    service = CloudAPIProxyService(unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(database), adapter=adapter, clock=lambda: NOW)
    _, plaintext = service.issue_token(
        tenant_id="tenant", subject_id="subject", project_id="fictional-project",
        package_id="fictional-package", package_checksum=CHECKSUM_A,
        workflow_id="literature-search", workflow_version="1.0.0", workflow_checksum=CHECKSUM_B,
    )
    result = service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=make_request())
    stored = next(iter(database.operations.values()))
    assert result["operation_status"] == "FAILED"
    assert result["error_code"] == "RESPONSE_LIMIT_EXCEEDED"
    assert stored.provider_data is None
    assert stored.provider_data_checksum is None


def test_delayed_exact_replay_of_failed_operation_never_reinvokes_adapter() -> None:
    service, database, adapter, token, plaintext, current = _mutable_proxy_setup(
        adapter=OversizedAdapter(),
    )
    request = make_request()
    first = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )
    current[0] = NOW + timedelta(minutes=6)

    replay = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )

    assert first["operation_status"] == replay["operation_status"] == "FAILED"
    assert replay["operation_id"] == first["operation_id"]
    assert replay["idempotency_result"] == "REPLAYED"
    assert adapter.invocation_count == 1
    assert len(database.operations) == 1
    assert database.tokens[token.scope.token_id].admitted_operations == 1


def test_operation_timeout_is_terminal_and_has_no_retry() -> None:
    database = InMemoryProxyDatabase()
    adapter = DeterministicFakePaperSearchAdapter()
    ticks = iter((0.0, 10.001))
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(database),
        adapter=adapter,
        clock=lambda: NOW,
        monotonic=lambda: next(ticks),
    )
    _, plaintext = service.issue_token(
        tenant_id="tenant", subject_id="subject", project_id="fictional-project",
        package_id="fictional-package", package_checksum=CHECKSUM_A,
        workflow_id="literature-search", workflow_version="1.0.0", workflow_checksum=CHECKSUM_B,
    )
    result = service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=make_request())
    assert result["operation_status"] == "FAILED"
    assert result["error_code"] == "OPERATION_TIMEOUT"
    assert adapter.invocation_count == 1


class UnsafeResultAdapter(DeterministicFakePaperSearchAdapter):
    def search(self, request):
        self.invocation_count += 1
        return {"untrusted_provider_data": True, "text": "OPENAI_API_KEY=fake_canary_value"}


def test_sensitive_canaries_are_rejected_before_request_or_result_retention() -> None:
    database = InMemoryProxyDatabase()
    adapter = UnsafeResultAdapter()
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(database),
        adapter=adapter,
        clock=lambda: NOW,
    )
    _, plaintext = service.issue_token(
        tenant_id="tenant", subject_id="subject", project_id="fictional-project",
        package_id="fictional-package", package_checksum=CHECKSUM_A,
        workflow_id="literature-search", workflow_version="1.0.0", workflow_checksum=CHECKSUM_B,
    )
    unsafe_request = make_request(parameters=PaperSearchV01Request("OPENAI_API_KEY=fake_canary_value"))
    with pytest.raises(ProxyError) as captured:
        service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=unsafe_request)
    assert captured.value.code == "UNSAFE_REQUEST_CONTENT"
    assert not database.operations
    assert adapter.invocation_count == 0

    result = service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=make_request())
    stored = next(iter(database.operations.values()))
    assert result["error_code"] == "UNSAFE_PROVIDER_DATA"
    assert stored.provider_data is None
    assert "fake_canary_value" not in canonical_json(result)


class InterruptingAdapter:
    adapter_id = ADAPTER_ID
    invocation_count = 0

    def search(self, request):
        self.invocation_count += 1
        raise KeyboardInterrupt()


def test_interrupted_running_operation_reconciles_without_second_invocation() -> None:
    database = InMemoryProxyDatabase()
    adapter = InterruptingAdapter()
    current = [NOW]
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(database),
        adapter=adapter,
        clock=lambda: current[0],
    )
    _, plaintext = service.issue_token(
        tenant_id="tenant", subject_id="subject", project_id="fictional-project",
        package_id="fictional-package", package_checksum=CHECKSUM_A,
        workflow_id="literature-search", workflow_version="1.0.0", workflow_checksum=CHECKSUM_B,
    )
    request = make_request()
    with pytest.raises(KeyboardInterrupt):
        service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=request)
    assert next(iter(database.operations.values())).status is ProxyOperationStatus.RUNNING
    current[0] = NOW + timedelta(minutes=6)
    running_replay = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )
    assert running_replay["operation_status"] == "RUNNING"
    assert running_replay["idempotency_result"] == "REPLAYED"
    assert adapter.invocation_count == 1
    assert service.reconcile_interrupted() == 1
    replay = service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=request)
    assert replay["operation_status"] == "RECONCILIATION_REQUIRED"
    assert replay["idempotency_result"] == "REPLAYED"
    assert adapter.invocation_count == 1


def test_exhausted_operation_budget_does_not_block_delayed_exact_replay() -> None:
    service, database, adapter, token, plaintext, current = _mutable_proxy_setup()
    request = make_request()
    first = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )
    database.tokens[token.scope.token_id] = replace(
        database.tokens[token.scope.token_id],
        admitted_operations=token.scope.maximum_operations,
    )
    current[0] = NOW + timedelta(minutes=6)

    replay = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )

    assert replay["operation_id"] == first["operation_id"]
    assert replay["idempotency_result"] == "REPLAYED"
    assert database.tokens[token.scope.token_id].admitted_operations == token.scope.maximum_operations
    assert adapter.invocation_count == 1


def test_concurrent_delayed_replay_and_stale_conflict_keep_stable_ledger() -> None:
    service, database, adapter, token, plaintext, current = _mutable_proxy_setup()
    request = make_request()
    first = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )
    current[0] = NOW + timedelta(minutes=6)

    with ThreadPoolExecutor(max_workers=4) as executor:
        replays = list(
            executor.map(
                lambda _: service.submit(
                    bearer_token=plaintext,
                    path_project_id="fictional-project",
                    request=request,
                ),
                range(4),
            )
        )
    changed = make_request(
        idempotency_key=request.idempotency_key,
        parameters=PaperSearchV01Request(query="stale concurrent changed content"),
    )

    def conflict_code(_: int) -> str:
        try:
            service.submit(
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
    assert len(database.operations) == 1
    assert database.tokens[token.scope.token_id].admitted_operations == 1
    assert adapter.invocation_count == 1


class BlockingAdapter(DeterministicFakePaperSearchAdapter):
    def __init__(self, entered: Event, release: Event) -> None:
        super().__init__()
        self.entered = entered
        self.release = release

    def search(self, request):
        self.entered.set()
        self.release.wait(timeout=2)
        return super().search(request)


def test_concurrency_limit_rejects_third_active_operation() -> None:
    database = InMemoryProxyDatabase()
    entered = Event()
    release = Event()
    adapter = BlockingAdapter(entered, release)
    service = CloudAPIProxyService(unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(database), adapter=adapter, clock=lambda: NOW)
    _, plaintext = service.issue_token(
        tenant_id="tenant", subject_id="subject", project_id="fictional-project",
        package_id="fictional-package", package_checksum=CHECKSUM_A,
        workflow_id="literature-search", workflow_version="1.0.0", workflow_checksum=CHECKSUM_B,
    )
    errors: list[BaseException] = []
    threads = [
        Thread(target=lambda request=request: _submit_thread(service, plaintext, request, errors))
        for request in (make_request(), make_request())
    ]
    for thread in threads:
        thread.start()
    entered.wait(timeout=1)
    deadline = time.monotonic() + 2
    while len([item for item in database.operations.values() if item.status is ProxyOperationStatus.RUNNING]) < 2 and time.monotonic() < deadline:
        time.sleep(0.001)
    assert len([item for item in database.operations.values() if item.status is ProxyOperationStatus.RUNNING]) == 2
    with pytest.raises(ProxyError) as captured:
        service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=make_request())
    release.set()
    for thread in threads:
        thread.join(timeout=2)
    assert captured.value.code == "CONCURRENCY_LIMIT_EXCEEDED"
    assert not errors


def _submit_thread(service, plaintext: str, request, errors: list[BaseException]) -> None:
    try:
        service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=request)
    except BaseException as error:
        errors.append(error)
