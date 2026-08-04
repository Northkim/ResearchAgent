from __future__ import annotations

import json
import logging
import secrets
import socket
import urllib.request
from dataclasses import replace
from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

import httpx
import pytest

from backend.cloud_api_proxy import (
    CloudAPIProxyService,
    DeterministicFakePaperSearchAdapter,
    InMemoryProxyDatabase,
    InMemoryProxyUnitOfWork,
)
from backend.cloud_api_proxy.contracts import (
    MAX_RESULT_BYTES,
    OPENALEX_ADAPTER_ID,
    OPENALEX_MAX_PROVIDER_COST_MICROUSD,
    OPENALEX_RESERVED_SEARCH_COST_MICROUSD,
    PaperSearchV01Request,
    ProxyOperationStatus,
    canonical_json,
    operation_to_dict,
)
from backend.cloud_api_proxy.errors import ProxyError
from backend.cloud_api_proxy.openalex_adapter import (
    OPENALEX_MAX_RESPONSE_BYTES,
    OPENALEX_SELECT,
    OPENALEX_WORKS_URL,
    EnvironmentOpenAlexCredentialSource,
    HTTPXOpenAlexTransport,
    OpenAlexPaperSearchAdapter,
    SafeTransportFailure,
    usd_decimal_to_microusd,
)
from backend.cloud_api_proxy.ports import ProviderHTTPResponse, ProxyAdapterError

from .conftest import CHECKSUM_A, CHECKSUM_B, NOW, make_request


class SyntheticCredentialSource:
    def __init__(self, value: str) -> None:
        self.value = value
        self.read_count = 0

    def get(self) -> str:
        self.read_count += 1
        return self.value


class ScriptedTransport:
    def __init__(self, responses: list[ProviderHTTPResponse | BaseException]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []
        self.lock = Lock()

    def get(self, **values) -> ProviderHTTPResponse:
        with self.lock:
            self.calls.append(values)
            if not self.responses:
                raise AssertionError("scripted transport was called more than expected")
            result = self.responses.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


def _headers(**overrides: str) -> dict[str, str]:
    value = {
        "X-RateLimit-Limit": "100000",
        "X-RateLimit-Remaining": "99999",
        "X-RateLimit-Credits-Used": "0.001",
        "X-RateLimit-Reset": "1785805200",
    }
    value.update(overrides)
    return value


def _work(index: int = 1, **overrides) -> dict:
    value = {
        "id": f"https://openalex.org/W{1000 + index}",
        "doi": f"https://doi.org/10.5555/fictional.{index}",
        "display_name": f"Fictional OpenAlex metadata {index}",
        "authorships": [
            {
                "author": {
                    "id": f"https://openalex.org/A{2000 + index}",
                    "display_name": f"Fictional Author {index}",
                    "orcid": f"https://orcid.org/0000-0000-0000-{index:04d}",
                }
            }
        ],
        "abstract_inverted_index": {"Fictional": [0], "abstract": [1]},
        "publication_year": 2040,
        "primary_location": {
            "landing_page_url": "https://provider.invalid/must-not-persist",
            "source": {
                "display_name": "Fictional Metadata Journal",
                "homepage_url": "https://provider.invalid/must-not-persist",
            },
        },
        "language": "en",
        "unknown_provider_field": "must-not-persist",
    }
    value.update(overrides)
    return value


def _response(
    *,
    status: int = 200,
    cost: object = "0.001",
    results: list | None = None,
    headers: dict[str, str] | None = None,
    raw_body: bytes | None = None,
) -> ProviderHTTPResponse:
    body = raw_body
    if body is None:
        body = json.dumps(
            {"meta": {"cost_usd": cost}, "results": results if results is not None else [_work()]},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    return ProviderHTTPResponse(
        status_code=status,
        headers=_headers() if headers is None else headers,
        body=body,
    )


def _adapter(
    transport: ScriptedTransport,
    *,
    key: str | None = None,
) -> tuple[OpenAlexPaperSearchAdapter, SyntheticCredentialSource]:
    source = SyntheticCredentialSource(key or secrets.token_urlsafe(32))
    adapter = OpenAlexPaperSearchAdapter(
        credential_source=source,
        transport=transport,
        clock=lambda: datetime(2026, 8, 5, 0, 0, tzinfo=UTC),
    )
    return adapter, source


def _service(
    adapter: OpenAlexPaperSearchAdapter,
) -> tuple[CloudAPIProxyService, InMemoryProxyDatabase, object, str]:
    database = InMemoryProxyDatabase()
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(database),
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
    return service, database, token, plaintext


def test_exact_request_mapping_normalization_and_cost_are_provider_neutral() -> None:
    transport = ScriptedTransport([_response()])
    adapter, source = _adapter(transport)
    result = adapter.search(PaperSearchV01Request("  fictional scholarly topic  ", 5))

    assert source.read_count == 1
    assert adapter.invocation_count == 1
    assert len(transport.calls) == 1
    call = transport.calls[0]
    assert call["url"] == OPENALEX_WORKS_URL
    assert call["timeout_seconds"] == 10
    assert call["maximum_response_bytes"] == 512 * 1024
    assert call["params"] == (
        ("search", "fictional scholarly topic"),
        ("per_page", "5"),
        ("select", OPENALEX_SELECT),
        ("api_key", source.value),
    )
    assert {key for key, _ in call["params"]} == {"search", "per_page", "select", "api_key"}
    assert result.reported_cost_microusd == 1_000
    assert result.provider_http_calls == 1
    assert result.provider_data["source_classification"] == "LIVE_OPENALEX_SCHOLARLY_METADATA"
    paper = result.provider_data["papers"][0]
    assert paper["provider_id"] == "W1001"
    assert paper["title"] == "Fictional OpenAlex metadata 1"
    assert paper["authors"][0]["name"] == "Fictional Author 1"
    assert paper["abstract"] == "Fictional abstract"
    assert paper["publication_venue"] == "Fictional Metadata Journal"
    assert paper["source_url"] == "https://openalex.org/W1001"
    encoded = canonical_json(result.provider_data)
    assert "provider.invalid" not in encoded
    assert "unknown_provider_field" not in encoded


def test_json_numeric_provider_cost_is_parsed_exactly_as_decimal() -> None:
    response = _response(raw_body=b'{"meta":{"cost_usd":0.001},"results":[]}')
    transport = ScriptedTransport([response])
    adapter, _ = _adapter(transport)
    result = adapter.search(PaperSearchV01Request("fictional", 1))
    assert result.reported_cost_microusd == 1_000


@pytest.mark.parametrize(
    ("value", "expected"),
    [("0.001", 1_000), ("0.05", 50_000), ("1", 1_000_000), (0, 0)],
)
def test_exact_microusd_conversion(value: object, expected: int) -> None:
    assert usd_decimal_to_microusd(value) == expected


@pytest.mark.parametrize("value", ["-0.001", "NaN", "Infinity", "0.0000001", 0.001, True, "bad"])
def test_invalid_or_inexact_cost_is_rejected(value: object) -> None:
    with pytest.raises(ValueError):
        usd_decimal_to_microusd(value)


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (300, "PROVIDER_CONTRACT_CHANGED"),
        (400, "PROVIDER_INVALID_RESPONSE"),
        (401, "PROVIDER_AUTHENTICATION_FAILED"),
        (403, "PROVIDER_AUTHORIZATION_FAILED"),
        (408, "PROVIDER_TIMEOUT"),
        (429, "PROVIDER_RATE_LIMITED"),
        (500, "PROVIDER_UNAVAILABLE"),
        (502, "PROVIDER_UNAVAILABLE"),
        (503, "PROVIDER_UNAVAILABLE"),
        (504, "PROVIDER_UNAVAILABLE"),
    ],
)
def test_http_failure_categories_are_stable_and_never_retried(status: int, code: str) -> None:
    transport = ScriptedTransport([_response(status=status, raw_body=b"<unsafe-error>secret</unsafe-error>")])
    adapter, source = _adapter(transport)
    with pytest.raises(ProxyAdapterError) as captured:
        adapter.search(PaperSearchV01Request("fictional", 1))
    assert captured.value.code == code
    assert len(transport.calls) == 1
    assert source.value not in str(captured.value)
    assert "unsafe-error" not in str(captured.value)


@pytest.mark.parametrize(
    ("failure", "code", "uncertain"),
    [
        (SafeTransportFailure(uncertain=False), "PROVIDER_UNAVAILABLE", False),
        (SafeTransportFailure(uncertain=False, timeout=True), "PROVIDER_TIMEOUT", False),
        (SafeTransportFailure(uncertain=True, timeout=True), "PROVIDER_RECONCILIATION_REQUIRED", True),
        (RuntimeError("synthetic TLS-like failure"), "PROVIDER_UNAVAILABLE", False),
    ],
)
def test_transport_failure_categories_are_safe_and_never_retried(
    failure: BaseException,
    code: str,
    uncertain: bool,
) -> None:
    transport = ScriptedTransport([failure])
    adapter, source = _adapter(transport)
    with pytest.raises(ProxyAdapterError) as captured:
        adapter.search(PaperSearchV01Request("fictional", 1))
    assert captured.value.code == code
    assert captured.value.uncertain is uncertain
    assert source.value not in str(captured.value)
    assert len(transport.calls) == 1


@pytest.mark.parametrize(
    "response",
    [
        _response(raw_body=b"{"),
        _response(raw_body=b"[]"),
        _response(raw_body=b'{"meta":{"cost_usd":"0.001"}}'),
        _response(raw_body=b'{"meta":{"cost_usd":"0.001"},"results":{}}'),
        _response(cost="bad"),
        _response(headers={}),
        _response(headers=_headers(**{"X-RateLimit-Remaining": "100001"})),
    ],
)
def test_malformed_contract_data_fails_without_retry(response: ProviderHTTPResponse) -> None:
    transport = ScriptedTransport([response])
    adapter, _ = _adapter(transport)
    with pytest.raises(ProxyAdapterError) as captured:
        adapter.search(PaperSearchV01Request("fictional", 1))
    assert captured.value.code in {"PROVIDER_INVALID_RESPONSE", "PROVIDER_CONTRACT_CHANGED"}
    assert len(transport.calls) == 1


def test_provider_result_count_cannot_exceed_requested_count() -> None:
    transport = ScriptedTransport([_response(results=[_work(1), _work(2)])])
    adapter, _ = _adapter(transport)
    with pytest.raises(ProxyAdapterError) as captured:
        adapter.search(PaperSearchV01Request("fictional", 1))
    assert captured.value.code == "PROVIDER_INVALID_RESPONSE"
    assert len(transport.calls) == 1


@pytest.mark.parametrize(
    "work",
    [
        _work(id="invalid"),
        _work(display_name="bad\u001btitle"),
        _work(authorships={}),
        _work(abstract_inverted_index={"duplicate": [0], "position": [0]}),
        _work(abstract_inverted_index={"gap": [1]}),
        _work(publication_year=True),
        _work(primary_location=[]),
    ],
)
def test_malformed_paper_fields_fail_safely(work: dict) -> None:
    transport = ScriptedTransport([_response(results=[work])])
    adapter, _ = _adapter(transport)
    with pytest.raises(ProxyAdapterError, match="Provider field") as captured:
        adapter.search(PaperSearchV01Request("fictional", 1))
    assert captured.value.code == "PROVIDER_INVALID_RESPONSE"


def test_raw_and_normalized_size_limits_do_not_truncate_or_retain_body() -> None:
    raw_transport = ScriptedTransport([_response(raw_body=b"x" * (OPENALEX_MAX_RESPONSE_BYTES + 1))])
    raw_adapter, _ = _adapter(raw_transport)
    with pytest.raises(ProxyAdapterError) as raw:
        raw_adapter.search(PaperSearchV01Request("fictional", 1))
    assert raw.value.code == "PROVIDER_RESPONSE_TOO_LARGE"

    positions = list(range(600))
    expanded = _work(abstract_inverted_index={"x" * 500: positions})
    normalized_transport = ScriptedTransport(
        [_response(results=[expanded, _work(2, abstract_inverted_index={"y" * 500: positions})])]
    )
    normalized_adapter, _ = _adapter(normalized_transport)
    with pytest.raises(ProxyAdapterError) as normalized:
        normalized_adapter.search(PaperSearchV01Request("fictional", 2))
    assert normalized.value.code == "PROVIDER_RESPONSE_TOO_LARGE"


def test_scripted_adapter_has_hard_no_network_canary(monkeypatch: pytest.MonkeyPatch) -> None:
    attempted: list[str] = []

    def forbidden(*args, **kwargs):
        attempted.append("network")
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(httpx, "Client", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    transport = ScriptedTransport([_response()])
    adapter, _ = _adapter(transport)
    adapter.search(PaperSearchV01Request("fictional", 1))
    assert attempted == []
    assert len(transport.calls) == 1


def test_live_transport_policy_suppresses_httpx_request_url_logs(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    key_marker = secrets.token_urlsafe(32)
    query_marker = "query-" + uuid4().hex

    class Response:
        status_code = 200
        headers = {}

        def __enter__(self):
            logging.getLogger("httpx").warning(
                "synthetic request %s %s", query_marker, key_marker
            )
            return self

        def __exit__(self, *args):
            return None

        def iter_bytes(self):
            yield b"{}"

    class Client:
        def __init__(self, **values):
            assert values["verify"] is True
            assert values["follow_redirects"] is False
            assert values["trust_env"] is False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def stream(self, method, url, *, params):
            assert method == "GET"
            assert url == OPENALEX_WORKS_URL
            assert ("api_key", key_marker) in params
            return Response()

    monkeypatch.setattr(httpx, "Client", Client)
    with caplog.at_level(logging.WARNING, logger="httpx"):
        response = HTTPXOpenAlexTransport().get(
            url=OPENALEX_WORKS_URL,
            params=(("search", query_marker), ("api_key", key_marker)),
            timeout_seconds=10,
            maximum_response_bytes=OPENALEX_MAX_RESPONSE_BYTES,
        )
    assert response.body == b"{}"
    assert key_marker not in caplog.text
    assert query_marker not in caplog.text


def test_openalex_service_retains_no_query_or_key_and_replay_reserves_once() -> None:
    query_marker = "query-" + uuid4().hex
    key_marker = secrets.token_urlsafe(32)
    transport = ScriptedTransport([_response()])
    adapter, _ = _adapter(transport, key=key_marker)
    service, database, token, plaintext = _service(adapter)
    request = make_request(parameters=PaperSearchV01Request(query_marker, 1))

    first = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )
    replay = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=request,
    )
    by_id = service.get_operation(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        operation_id=first["operation_id"],
    )
    by_key = service.find_operation(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        package_id=request.package_id,
        idempotency_key=request.idempotency_key,
    )

    operation = next(iter(database.operations.values()))
    persisted_shape = canonical_json(operation_to_dict(operation))
    response_shape = canonical_json(first)
    assert query_marker not in persisted_shape
    assert key_marker not in persisted_shape
    assert query_marker not in response_shape
    assert key_marker not in response_shape
    assert query_marker not in canonical_json(by_id)
    assert query_marker not in canonical_json(by_key)
    assert operation.retained_request_json is None
    assert operation.request.query_checksum.startswith("sha256:")
    assert operation.request.query_utf8_bytes == len(query_marker.encode())
    assert operation.request.query_characters == len(query_marker)
    assert operation.usage is not None
    assert operation.usage.provider_http_calls == 1
    assert operation.usage.reserved_cost_microusd == 1_000
    assert operation.usage.reported_cost_microusd == 1_000
    stored_token = database.tokens[token.scope.token_id]
    assert stored_token.admitted_operations == 1
    assert stored_token.used_provider_calls == 1
    assert stored_token.reserved_provider_cost_microusd == 1_000
    assert stored_token.reported_provider_cost_microusd == 1_000
    assert replay["operation_id"] == first["operation_id"]
    assert replay["idempotency_result"] == "REPLAYED"
    assert adapter.invocation_count == 1
    assert len(transport.calls) == 1


def test_changed_content_conflicts_before_second_provider_call() -> None:
    transport = ScriptedTransport([_response()])
    adapter, _ = _adapter(transport)
    service, database, token, plaintext = _service(adapter)
    first = make_request(parameters=PaperSearchV01Request("fictional-a", 1))
    service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=first)
    changed = make_request(
        idempotency_key=first.idempotency_key,
        parameters=PaperSearchV01Request("fictional-b", 1),
    )
    with pytest.raises(ProxyError) as captured:
        service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=changed)
    assert captured.value.code == "IDEMPOTENCY_CONFLICT"
    assert adapter.invocation_count == 1
    assert database.tokens[token.scope.token_id].used_provider_calls == 1


def test_uncertain_timeout_reconciles_and_exact_replay_never_calls_again() -> None:
    transport = ScriptedTransport([SafeTransportFailure(uncertain=True, timeout=True)])
    adapter, _ = _adapter(transport)
    service, database, _, plaintext = _service(adapter)
    request = make_request(parameters=PaperSearchV01Request("fictional-timeout", 1))
    first = service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=request)
    replay = service.submit(bearer_token=plaintext, path_project_id="fictional-project", request=request)
    operation = next(iter(database.operations.values()))
    assert first["operation_status"] == ProxyOperationStatus.RECONCILIATION_REQUIRED.value
    assert first["error_code"] == "PROVIDER_RECONCILIATION_REQUIRED"
    assert replay["operation_id"] == first["operation_id"]
    assert adapter.invocation_count == 1
    assert len(transport.calls) == 1
    assert operation.usage is not None and operation.usage.provider_http_calls == 1


def test_budget_exhaustion_fails_before_transport() -> None:
    transport = ScriptedTransport([_response()])
    adapter, _ = _adapter(transport)
    service, database, token, plaintext = _service(adapter)
    database.tokens[token.scope.token_id] = replace(
        token,
        reserved_provider_cost_microusd=OPENALEX_MAX_PROVIDER_COST_MICROUSD,
    )
    with pytest.raises(ProxyError) as captured:
        service.submit(
            bearer_token=plaintext,
            path_project_id="fictional-project",
            request=make_request(parameters=PaperSearchV01Request("fictional-budget", 1)),
        )
    assert captured.value.code == "PROVIDER_BUDGET_EXHAUSTED"
    assert adapter.invocation_count == 0
    assert transport.calls == []


def test_reported_cost_evidence_also_blocks_budget_before_transport() -> None:
    transport = ScriptedTransport([_response()])
    adapter, _ = _adapter(transport)
    service, database, token, plaintext = _service(adapter)
    database.tokens[token.scope.token_id] = replace(
        token,
        reported_provider_cost_microusd=OPENALEX_MAX_PROVIDER_COST_MICROUSD,
    )
    with pytest.raises(ProxyError) as captured:
        service.submit(
            bearer_token=plaintext,
            path_project_id="fictional-project",
            request=make_request(parameters=PaperSearchV01Request("fictional-budget", 1)),
        )
    assert captured.value.code == "PROVIDER_BUDGET_EXHAUSTED"
    assert adapter.invocation_count == 0
    assert transport.calls == []


def test_environment_credential_source_is_lazy_and_injectable() -> None:
    marker = secrets.token_urlsafe(32)
    source = EnvironmentOpenAlexCredentialSource({"REAGENT_OPENALEX_API_KEY": marker})
    assert source._environment is not None
    assert source.get() == marker


def test_missing_injected_credential_fails_closed_without_environment_read() -> None:
    source = EnvironmentOpenAlexCredentialSource({})
    with pytest.raises(RuntimeError, match="credential"):
        source.get()


def test_openalex_token_scope_freezes_exact_call_and_cost_limits() -> None:
    transport = ScriptedTransport([])
    adapter, _ = _adapter(transport)
    service, _, token, _ = _service(adapter)
    assert token.scope.adapter_id == OPENALEX_ADAPTER_ID
    assert token.scope.maximum_operations == 20
    assert token.scope.maximum_provider_calls == 20
    assert token.scope.maximum_provider_cost_microusd == 50_000
    with pytest.raises(ValueError, match="between 1 and 20"):
        service.issue_token(
            tenant_id="fictional-tenant",
            subject_id="fictional-subject",
            project_id="fictional-project",
            package_id="fictional-package",
            package_checksum=CHECKSUM_A,
            workflow_id="literature-search",
            workflow_version="1.0.0",
            workflow_checksum=CHECKSUM_B,
            adapter_id=OPENALEX_ADAPTER_ID,
            maximum_operations=21,
        )


def test_server_owned_token_scope_routes_each_adapter_without_client_switch() -> None:
    fake = DeterministicFakePaperSearchAdapter()
    transport = ScriptedTransport([_response()])
    openalex, _ = _adapter(transport)
    database = InMemoryProxyDatabase()
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(database),
        adapters={fake.adapter_id: fake, openalex.adapter_id: openalex},
        clock=lambda: NOW,
    )
    shared = {
        "tenant_id": "fictional-tenant",
        "subject_id": "fictional-subject",
        "project_id": "fictional-project",
        "package_id": "fictional-package",
        "package_checksum": CHECKSUM_A,
        "workflow_id": "literature-search",
        "workflow_version": "1.0.0",
        "workflow_checksum": CHECKSUM_B,
    }
    _, fake_plaintext = service.issue_token(**shared, adapter_id=fake.adapter_id)
    _, openalex_plaintext = service.issue_token(**shared, adapter_id=openalex.adapter_id)
    fake_request = make_request(parameters=PaperSearchV01Request("fictional-fake", 1))
    openalex_request = make_request(parameters=PaperSearchV01Request("fictional-openalex", 1))
    fake_result = service.submit(
        bearer_token=fake_plaintext,
        path_project_id="fictional-project",
        request=fake_request,
    )
    openalex_result = service.submit(
        bearer_token=openalex_plaintext,
        path_project_id="fictional-project",
        request=openalex_request,
    )
    assert fake_result["provenance"]["adapter_id"] == fake.adapter_id
    assert openalex_result["provenance"]["adapter_id"] == openalex.adapter_id
    assert fake.invocation_count == openalex.invocation_count == 1
    assert len(transport.calls) == 1
