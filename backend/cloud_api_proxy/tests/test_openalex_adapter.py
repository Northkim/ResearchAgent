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
import backend.cloud_api_proxy.openalex_adapter as openalex_adapter_module

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
from backend.cloud_api_proxy.openalex_diagnostics import (
    STRUCTURAL_DIAGNOSTIC_CONTRACT_VERSION,
    STRUCTURAL_DIAGNOSTIC_EVENT_NAME,
    FailureStage,
    ObservedKind,
    OpenAlexStructuralDiagnosticEmitter,
    ValidatorCode,
    provider_structural_shape_checksum,
)
from backend.cloud_api_proxy.ports import (
    ProviderHTTPResponse,
    ProxyAdapterError,
    ProxyAdapterResult,
)

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
    *,
    diagnostics_enabled: bool = False,
) -> tuple[CloudAPIProxyService, InMemoryProxyDatabase, object, str]:
    database = InMemoryProxyDatabase()
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(database),
        adapters={adapter.adapter_id: adapter},
        clock=lambda: NOW,
        openalex_structural_diagnostics=OpenAlexStructuralDiagnosticEmitter(
            enabled=diagnostics_enabled
        ),
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


def test_uncertain_timeout_reconciles_and_exact_replay_never_calls_again(
    caplog: pytest.LogCaptureFixture,
) -> None:
    transport = ScriptedTransport([SafeTransportFailure(uncertain=True, timeout=True)])
    adapter, _ = _adapter(transport)
    service, database, _, plaintext = _service(adapter, diagnostics_enabled=True)
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
    assert _diagnostic_events(caplog) == []


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


def _per_work_failure_case(case: str) -> tuple[object, FailureStage, str, ObservedKind, ValidatorCode]:
    work = _work()
    stage = FailureStage.WORK_NORMALIZATION
    path = "/results/*"
    kind = ObservedKind.WRONG_TYPE
    code = ValidatorCode.WORK_OBJECT_REQUIRED
    if case == "work_object":
        return None, stage, path, ObservedKind.NULL, code
    if case == "id_missing":
        del work["id"]
        return work, stage, "/results/*/id", ObservedKind.MISSING, ValidatorCode.WORK_ID_REQUIRED_STRING
    if case == "id_null":
        work["id"] = None
        return work, stage, "/results/*/id", ObservedKind.NULL, ValidatorCode.WORK_ID_REQUIRED_STRING
    if case == "id_format":
        work["id"] = "fictional-invalid-id"
        return work, stage, "/results/*/id", ObservedKind.INVALID_VALUE, ValidatorCode.WORK_ID_FORMAT
    if case == "doi_type":
        work["doi"] = []
        return work, stage, "/results/*/doi", kind, ValidatorCode.DOI_STRING_OR_NULL
    if case.startswith("title_"):
        path = "/results/*/display_name"
        mapping = {
            "title_missing": (None, ObservedKind.MISSING, ValidatorCode.DISPLAY_NAME_REQUIRED_TEXT),
            "title_null": (None, ObservedKind.NULL, ValidatorCode.DISPLAY_NAME_REQUIRED_TEXT),
            "title_empty": (" ", ObservedKind.EMPTY, ValidatorCode.DISPLAY_NAME_REQUIRED_TEXT),
            "title_length": ("x" * 2_001, ObservedKind.LIMIT_EXCEEDED, ValidatorCode.DISPLAY_NAME_LENGTH),
            "title_control": ("fictional\u001btitle", ObservedKind.CONTROL_CHARACTER, ValidatorCode.DISPLAY_NAME_CONTROL),
        }
        value, kind, code = mapping[case]
        if case == "title_missing":
            del work["display_name"]
        else:
            work["display_name"] = value
        return work, stage, path, kind, code
    stage = FailureStage.AUTHORSHIP_NORMALIZATION
    if case == "authorships_missing":
        del work["authorships"]
        return work, stage, "/results/*/authorships", ObservedKind.MISSING, ValidatorCode.AUTHORSHIPS_ARRAY_REQUIRED
    if case == "authorships_type":
        work["authorships"] = {}
        return work, stage, "/results/*/authorships", kind, ValidatorCode.AUTHORSHIPS_ARRAY_REQUIRED
    if case == "authorships_count":
        work["authorships"] = work["authorships"] * 101
        return work, stage, "/results/*/authorships", ObservedKind.LIMIT_EXCEEDED, ValidatorCode.AUTHORSHIPS_COUNT_LIMIT
    if case == "authorship_object":
        work["authorships"] = [None]
        return work, stage, "/results/*/authorships/*", kind, ValidatorCode.AUTHORSHIP_OBJECT_REQUIRED
    if case in {"author_missing", "author_null"}:
        work["authorships"] = [{}] if case == "author_missing" else [{"author": None}]
        return (
            work,
            stage,
            "/results/*/authorships/*/author",
            ObservedKind.MISSING if case == "author_missing" else ObservedKind.NULL,
            ValidatorCode.AUTHOR_OBJECT_REQUIRED,
        )
    author = work["authorships"][0]["author"]
    if case.startswith("author_name_"):
        path = "/results/*/authorships/*/author/display_name"
        mapping = {
            "author_name_missing": (None, ObservedKind.MISSING, ValidatorCode.AUTHOR_DISPLAY_NAME_REQUIRED_TEXT),
            "author_name_null": (None, ObservedKind.NULL, ValidatorCode.AUTHOR_DISPLAY_NAME_REQUIRED_TEXT),
            "author_name_empty": (" ", ObservedKind.EMPTY, ValidatorCode.AUTHOR_DISPLAY_NAME_REQUIRED_TEXT),
            "author_name_length": ("x" * 501, ObservedKind.LIMIT_EXCEEDED, ValidatorCode.AUTHOR_DISPLAY_NAME_LENGTH),
            "author_name_control": ("fictional\u001bauthor", ObservedKind.CONTROL_CHARACTER, ValidatorCode.AUTHOR_DISPLAY_NAME_CONTROL),
        }
        value, kind, code = mapping[case]
        if case == "author_name_missing":
            del author["display_name"]
        else:
            author["display_name"] = value
        return work, stage, path, kind, code
    if case in {"author_id_type", "author_id_format"}:
        author["id"] = [] if case == "author_id_type" else "fictional-invalid-author-id"
        return (
            work,
            stage,
            "/results/*/authorships/*/author/id",
            kind if case == "author_id_type" else ObservedKind.INVALID_VALUE,
            ValidatorCode.AUTHOR_ID_FORMAT,
        )
    if case.startswith("orcid_"):
        path = "/results/*/authorships/*/author/orcid"
        mapping = {
            "orcid_type": ([], kind, ValidatorCode.AUTHOR_ORCID_REQUIRED_TEXT),
            "orcid_empty": (" ", ObservedKind.EMPTY, ValidatorCode.AUTHOR_ORCID_REQUIRED_TEXT),
            "orcid_length": ("x" * 65, ObservedKind.LIMIT_EXCEEDED, ValidatorCode.AUTHOR_ORCID_LENGTH),
            "orcid_control": ("fictional\u001borcid", ObservedKind.CONTROL_CHARACTER, ValidatorCode.AUTHOR_ORCID_CONTROL),
        }
        author["orcid"], kind, code = mapping[case]
        return work, stage, path, kind, code
    stage = FailureStage.ABSTRACT_RECONSTRUCTION
    path = "/results/*/abstract_inverted_index"
    if case == "abstract_type":
        work["abstract_inverted_index"] = []
        return work, stage, path, kind, ValidatorCode.ABSTRACT_OBJECT_OR_NULL
    if case == "abstract_token_count":
        work["abstract_inverted_index"] = {f"t{index}": [] for index in range(20_001)}
        return work, stage, path, ObservedKind.LIMIT_EXCEEDED, ValidatorCode.ABSTRACT_TOKEN_COUNT_LIMIT
    abstract_mapping = {
        "abstract_token_empty": ({" ": [0]}, ObservedKind.EMPTY, ValidatorCode.ABSTRACT_TOKEN_REQUIRED_TEXT),
        "abstract_token_length": ({"x" * 501: [0]}, ObservedKind.LIMIT_EXCEEDED, ValidatorCode.ABSTRACT_TOKEN_LENGTH),
        "abstract_token_control": ({"fictional\u001btoken": [0]}, ObservedKind.CONTROL_CHARACTER, ValidatorCode.ABSTRACT_TOKEN_CONTROL),
        "abstract_positions_type": ({"fictional": {}}, kind, ValidatorCode.ABSTRACT_POSITIONS_ARRAY),
        "abstract_positions_count": ({"fictional": [0] * 20_001}, ObservedKind.LIMIT_EXCEEDED, ValidatorCode.ABSTRACT_POSITIONS_COUNT_LIMIT),
        "abstract_position_type": ({"fictional": [False]}, kind, ValidatorCode.ABSTRACT_POSITION_INTEGER),
        "abstract_position_range": ({"fictional": [100_001]}, ObservedKind.INVALID_POSITION, ValidatorCode.ABSTRACT_POSITION_RANGE),
        "abstract_position_duplicate": ({"fictional": [0], "metadata": [0]}, ObservedKind.INVALID_POSITION, ValidatorCode.ABSTRACT_POSITION_UNIQUE),
        "abstract_position_gap": ({"fictional": [1]}, ObservedKind.INVALID_POSITION, ValidatorCode.ABSTRACT_POSITIONS_CONTIGUOUS),
        "abstract_result_size": ({"x" * 500: list(range(20_000))}, ObservedKind.LIMIT_EXCEEDED, ValidatorCode.ABSTRACT_RESULT_SIZE),
    }
    if case in abstract_mapping:
        work["abstract_inverted_index"], kind, code = abstract_mapping[case]
        return work, stage, path, kind, code
    stage = FailureStage.WORK_NORMALIZATION
    if case in {"year_type", "year_range"}:
        work["publication_year"] = True if case == "year_type" else 999
        return (
            work,
            stage,
            "/results/*/publication_year",
            kind if case == "year_type" else ObservedKind.INVALID_VALUE,
            ValidatorCode.PUBLICATION_YEAR_INTEGER if case == "year_type" else ValidatorCode.PUBLICATION_YEAR_RANGE,
        )
    if case == "location_type":
        work["primary_location"] = []
        return work, stage, "/results/*/primary_location", kind, ValidatorCode.PRIMARY_LOCATION_OBJECT_OR_NULL
    if case == "source_type":
        work["primary_location"] = {"source": []}
        return work, stage, "/results/*/primary_location/source", kind, ValidatorCode.PRIMARY_SOURCE_OBJECT_OR_NULL
    if case.startswith("venue_"):
        mapping = {
            "venue_type": ([], kind, ValidatorCode.VENUE_REQUIRED_TEXT),
            "venue_empty": (" ", ObservedKind.EMPTY, ValidatorCode.VENUE_REQUIRED_TEXT),
            "venue_length": ("x" * 1_001, ObservedKind.LIMIT_EXCEEDED, ValidatorCode.VENUE_LENGTH),
            "venue_control": ("fictional\u001bvenue", ObservedKind.CONTROL_CHARACTER, ValidatorCode.VENUE_CONTROL),
        }
        value, kind, code = mapping[case]
        work["primary_location"] = {"source": {"display_name": value}}
        return work, stage, "/results/*/primary_location/source/display_name", kind, code
    if case.startswith("language_"):
        mapping = {
            "language_type": ([], kind, ValidatorCode.LANGUAGE_REQUIRED_TEXT),
            "language_empty": (" ", ObservedKind.EMPTY, ValidatorCode.LANGUAGE_REQUIRED_TEXT),
            "language_length": ("x" * 33, ObservedKind.LIMIT_EXCEEDED, ValidatorCode.LANGUAGE_LENGTH),
            "language_control": ("en\u001b", ObservedKind.CONTROL_CHARACTER, ValidatorCode.LANGUAGE_CONTROL),
        }
        work["language"], kind, code = mapping[case]
        return work, stage, "/results/*/language", kind, code
    if case == "paper_model":
        work["doi"] = "fictional-invalid-doi"
        return work, FailureStage.PAPER_MODEL_VALIDATION, "/results/*", ObservedKind.MODEL_VALIDATION, ValidatorCode.PAPER_RECORD_MODEL
    raise AssertionError(f"unknown synthetic case: {case}")


_PER_WORK_FAILURE_CASES = (
    "work_object",
    "id_missing",
    "id_null",
    "id_format",
    "doi_type",
    "title_missing",
    "title_null",
    "title_empty",
    "title_length",
    "title_control",
    "authorships_missing",
    "authorships_type",
    "authorships_count",
    "authorship_object",
    "author_missing",
    "author_null",
    "author_name_missing",
    "author_name_null",
    "author_name_empty",
    "author_name_length",
    "author_name_control",
    "author_id_type",
    "author_id_format",
    "orcid_type",
    "orcid_empty",
    "orcid_length",
    "orcid_control",
    "abstract_type",
    "abstract_token_count",
    "abstract_token_empty",
    "abstract_token_length",
    "abstract_token_control",
    "abstract_positions_type",
    "abstract_positions_count",
    "abstract_position_type",
    "abstract_position_range",
    "abstract_position_duplicate",
    "abstract_position_gap",
    "abstract_result_size",
    "year_type",
    "year_range",
    "location_type",
    "source_type",
    "venue_type",
    "venue_empty",
    "venue_length",
    "venue_control",
    "language_type",
    "language_empty",
    "language_length",
    "language_control",
    "paper_model",
)


@pytest.mark.parametrize("case", _PER_WORK_FAILURE_CASES)
def test_every_per_work_rejection_has_a_closed_structural_diagnostic(case: str) -> None:
    work, stage, path, kind, code = _per_work_failure_case(case)
    transport = ScriptedTransport([_response(results=[work])])
    adapter, _ = _adapter(transport)
    with pytest.raises(ProxyAdapterError) as captured:
        adapter.search(PaperSearchV01Request("fictional structural probe", 1))
    diagnostic = captured.value.structural_failure
    assert diagnostic is not None
    assert diagnostic.failure_stage is stage
    assert diagnostic.approved_json_path == path
    assert diagnostic.observed_kind is kind
    assert diagnostic.validator_code is code
    assert diagnostic.record_index == 0
    assert diagnostic.normalized_records_before_failure == 0
    assert diagnostic.structural_shape_checksum.startswith("sha256:")
    if stage in {FailureStage.AUTHORSHIP_NORMALIZATION, FailureStage.ABSTRACT_RECONSTRUCTION}:
        assert diagnostic.nested_element_index in {None, 0}
    assert len(transport.calls) == 1


def test_approved_sparse_shapes_remain_accepted() -> None:
    sparse = _work(
        doi=None,
        authorships=[],
        abstract_inverted_index=None,
        publication_year=None,
        primary_location=None,
        language=None,
    )
    transport = ScriptedTransport([_response(results=[sparse])])
    adapter, _ = _adapter(transport)
    result = adapter.search(PaperSearchV01Request("fictional sparse shape", 1))
    assert len(result.provider_data["papers"]) == 1
    assert result.reported_cost_microusd == 1_000


def test_structural_shape_checksum_is_deterministic_and_value_independent() -> None:
    first = {"meta": {"cost_usd": "0.001"}, "results": [_work(1)]}
    same_shape = {"meta": {"cost_usd": "999"}, "results": [_work(9)]}
    different_shape = {"meta": {"cost_usd": "0.001"}, "results": [_work(1)]}
    del different_shape["results"][0]["doi"]
    assert provider_structural_shape_checksum(first) == provider_structural_shape_checksum(first)
    assert provider_structural_shape_checksum(first) == provider_structural_shape_checksum(same_shape)
    assert provider_structural_shape_checksum(first) != provider_structural_shape_checksum(different_shape)


def _pipeline_failure_case(
    case: str,
) -> tuple[ProviderHTTPResponse, int, FailureStage, str, ObservedKind, ValidatorCode]:
    maximum = 1
    if case == "response_bytes":
        response = _response(raw_body=b"x" * (OPENALEX_MAX_RESPONSE_BYTES + 1))
        return response, maximum, FailureStage.RESPONSE_BYTES, "/", ObservedKind.LIMIT_EXCEEDED, ValidatorCode.RESPONSE_BYTES_LIMIT
    if case == "http_status":
        return _response(status=400), maximum, FailureStage.RESPONSE_BYTES, "/", ObservedKind.INVALID_VALUE, ValidatorCode.HTTP_STATUS_REJECTED
    if case == "json_decode":
        return _response(raw_body=b"{"), maximum, FailureStage.JSON_ROOT, "/", ObservedKind.INVALID_VALUE, ValidatorCode.JSON_DECODE
    if case == "json_root":
        return _response(raw_body=b"[]"), maximum, FailureStage.JSON_ROOT, "/", ObservedKind.WRONG_TYPE, ValidatorCode.JSON_ROOT_OBJECT
    if case == "meta_missing":
        response = _response(raw_body=b'{"results":[]}')
        return response, maximum, FailureStage.COST_USAGE, "/meta", ObservedKind.MISSING, ValidatorCode.META_OBJECT
    if case == "meta_type":
        response = _response(raw_body=b'{"meta":[],"results":[]}')
        return response, maximum, FailureStage.COST_USAGE, "/meta", ObservedKind.WRONG_TYPE, ValidatorCode.META_OBJECT
    if case == "cost_missing":
        response = _response(raw_body=b'{"meta":{},"results":[]}')
        return response, maximum, FailureStage.COST_USAGE, "/meta/cost_usd", ObservedKind.MISSING, ValidatorCode.COST_REQUIRED
    if case == "cost_invalid":
        return _response(cost="invalid"), maximum, FailureStage.COST_USAGE, "/meta/cost_usd", ObservedKind.INVALID_VALUE, ValidatorCode.COST_EXACT_DECIMAL
    if case == "headers_missing":
        return _response(headers={}), maximum, FailureStage.COST_USAGE, "/meta", ObservedKind.MISSING, ValidatorCode.RATE_HEADERS_REQUIRED
    if case == "headers_bounded":
        headers = _headers(**{"X-RateLimit-Limit": "not-an-integer"})
        return _response(headers=headers), maximum, FailureStage.COST_USAGE, "/meta", ObservedKind.INVALID_VALUE, ValidatorCode.RATE_HEADERS_BOUNDED
    if case == "headers_inconsistent":
        headers = _headers(**{"X-RateLimit-Remaining": "100001"})
        return _response(headers=headers), maximum, FailureStage.COST_USAGE, "/meta", ObservedKind.INVALID_VALUE, ValidatorCode.RATE_HEADERS_CONSISTENT
    if case == "cost_qualified":
        return _response(cost="0.002"), maximum, FailureStage.COST_USAGE, "/meta/cost_usd", ObservedKind.INVALID_VALUE, ValidatorCode.COST_QUALIFIED_PRICE
    if case == "results_missing":
        response = _response(raw_body=b'{"meta":{"cost_usd":"0.001"}}')
        return response, maximum, FailureStage.RESULTS_ARRAY, "/results", ObservedKind.MISSING, ValidatorCode.RESULTS_ARRAY_REQUIRED
    if case == "results_type":
        response = _response(raw_body=b'{"meta":{"cost_usd":"0.001"},"results":{}}')
        return response, maximum, FailureStage.RESULTS_ARRAY, "/results", ObservedKind.WRONG_TYPE, ValidatorCode.RESULTS_ARRAY_REQUIRED
    if case == "result_count":
        return _response(results=[_work(1), _work(2)]), maximum, FailureStage.RESULTS_ARRAY, "/results", ObservedKind.LIMIT_EXCEEDED, ValidatorCode.RESULT_COUNT_LIMIT
    if case == "normalized_size":
        positions = list(range(600))
        response = _response(
            results=[
                _work(1, abstract_inverted_index={"x" * 500: positions}),
                _work(2, abstract_inverted_index={"y" * 500: positions}),
            ]
        )
        return response, 2, FailureStage.RESULT_SIZE, "/normalized_results", ObservedKind.LIMIT_EXCEEDED, ValidatorCode.NORMALIZED_RESULT_SIZE
    raise AssertionError(f"unknown pipeline case: {case}")


@pytest.mark.parametrize(
    "case",
    (
        "response_bytes",
        "http_status",
        "json_decode",
        "json_root",
        "meta_missing",
        "meta_type",
        "cost_missing",
        "cost_invalid",
        "headers_missing",
        "headers_bounded",
        "headers_inconsistent",
        "cost_qualified",
        "results_missing",
        "results_type",
        "result_count",
        "normalized_size",
    ),
)
def test_response_pipeline_rejections_have_closed_structural_diagnostics(case: str) -> None:
    response, maximum, stage, path, kind, code = _pipeline_failure_case(case)
    transport = ScriptedTransport([response])
    adapter, _ = _adapter(transport)
    with pytest.raises(ProxyAdapterError) as captured:
        adapter.search(PaperSearchV01Request("fictional pipeline probe", maximum))
    diagnostic = captured.value.structural_failure
    assert diagnostic is not None
    assert diagnostic.failure_stage is stage
    assert diagnostic.approved_json_path == path
    assert diagnostic.observed_kind is kind
    assert diagnostic.validator_code is code
    assert diagnostic.record_index is None
    assert diagnostic.normalized_records_before_failure in {0, 2}
    assert len(transport.calls) == 1


def _diagnostic_events(caplog: pytest.LogCaptureFixture) -> list[dict]:
    return [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "reagent.openalex_structural_diagnostic"
    ]


def test_disabled_structural_diagnostics_emit_nothing_and_keep_generic_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    transport = ScriptedTransport([_response(results=[_work(id="fictional-invalid")])])
    adapter, _ = _adapter(transport)
    service, _, _, plaintext = _service(adapter, diagnostics_enabled=False)
    result = service.submit(
        bearer_token=plaintext,
        path_project_id="fictional-project",
        request=make_request(parameters=PaperSearchV01Request("fictional disabled", 1)),
    )
    assert result["error_code"] == "PROVIDER_INVALID_RESPONSE"
    assert _diagnostic_events(caplog) == []
    assert "structural" not in canonical_json(result)


def test_enabled_structural_diagnostics_emit_one_value_free_event_and_same_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    query_marker = "query-" + uuid4().hex
    key_marker = "key-" + secrets.token_urlsafe(32)
    work = _work(id="malformed-" + uuid4().hex, display_name="value-" + uuid4().hex)
    transport = ScriptedTransport([_response(results=[work])])
    adapter, _ = _adapter(transport, key=key_marker)
    service, database, _, plaintext = _service(adapter, diagnostics_enabled=True)
    with caplog.at_level(logging.WARNING, logger="reagent.openalex_structural_diagnostic"):
        result = service.submit(
            bearer_token=plaintext,
            path_project_id="fictional-project",
            request=make_request(parameters=PaperSearchV01Request(query_marker, 1)),
        )
    events = _diagnostic_events(caplog)
    assert result["error_code"] == "PROVIDER_INVALID_RESPONSE"
    assert len(events) == 1
    event = events[0]
    assert event["event"] == STRUCTURAL_DIAGNOSTIC_EVENT_NAME
    assert event["diagnostic_contract_version"] == STRUCTURAL_DIAGNOSTIC_CONTRACT_VERSION
    assert event["failure_stage"] == "WORK_NORMALIZATION"
    assert event["approved_json_path"] == "/results/*/id"
    assert event["record_index"] == 0
    assert event["validator_code"] == "WORK_ID_FORMAT"
    persisted = canonical_json(operation_to_dict(next(iter(database.operations.values()))))
    exposed = canonical_json(result) + caplog.text + persisted
    for prohibited in (
        query_marker,
        key_marker,
        plaintext,
        work["id"],
        work["display_name"],
        OPENALEX_WORKS_URL,
    ):
        assert prohibited not in exposed
    assert "structural" not in canonical_json(result)
    assert "diagnostic" not in persisted


def test_mixed_records_fail_completely_settle_cost_once_and_replay_without_an_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    results = [_work(1), _work(2, id="fictional-invalid"), _work(3)]
    transport = ScriptedTransport([_response(results=results)])
    adapter, _ = _adapter(transport)
    service, database, token, plaintext = _service(adapter, diagnostics_enabled=True)
    request = make_request(parameters=PaperSearchV01Request("fictional mixed records", 3))
    with caplog.at_level(logging.WARNING, logger="reagent.openalex_structural_diagnostic"):
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
        status = service.get_operation(
            bearer_token=plaintext,
            path_project_id="fictional-project",
            operation_id=first["operation_id"],
        )
    events = _diagnostic_events(caplog)
    operation = next(iter(database.operations.values()))
    persisted = canonical_json(operation_to_dict(operation))
    assert first["operation_status"] == "FAILED"
    assert first["error_code"] == "PROVIDER_INVALID_RESPONSE"
    assert first.get("provider_data") is None
    assert replay["operation_id"] == first["operation_id"]
    assert replay["idempotency_result"] == "REPLAYED"
    assert "diagnostic" not in canonical_json(status)
    assert "structural" not in canonical_json(status)
    assert len(events) == 1
    assert events[0]["record_index"] == 1
    assert events[0]["normalized_records_before_failure"] == 1
    assert events[0]["validator_code"] == "WORK_ID_FORMAT"
    assert "Fictional OpenAlex metadata" not in canonical_json(events[0])
    assert "papers" not in persisted
    assert operation.usage is not None
    assert operation.usage.provider_http_calls == 1
    assert operation.usage.reported_cost_microusd == 1_000
    stored_token = database.tokens[token.scope.token_id]
    assert stored_token.used_provider_calls == 1
    assert stored_token.reported_provider_cost_microusd == 1_000
    assert adapter.invocation_count == 1
    assert len(transport.calls) == 1


def test_service_safety_diagnostic_is_distinct_and_never_logs_the_match(
    caplog: pytest.LogCaptureFixture,
) -> None:
    matched_marker = "OPENAI_API_KEY=synthetic_" + uuid4().hex
    transport = ScriptedTransport([_response(results=[_work(display_name=matched_marker)])])
    adapter, _ = _adapter(transport)
    service, database, _, plaintext = _service(adapter, diagnostics_enabled=True)
    with caplog.at_level(logging.WARNING, logger="reagent.openalex_structural_diagnostic"):
        result = service.submit(
            bearer_token=plaintext,
            path_project_id="fictional-project",
            request=make_request(parameters=PaperSearchV01Request("fictional safety", 1)),
        )
    event = _diagnostic_events(caplog)[0]
    assert result["error_code"] == "PROVIDER_INVALID_RESPONSE"
    assert event["failure_stage"] == "SERVICE_SAFETY"
    assert event["approved_json_path"] == "/service_safety"
    assert event["observed_kind"] == "SENSITIVE_CONTENT"
    assert event["validator_code"] == "SERVICE_SENSITIVE_CONTENT"
    assert matched_marker not in caplog.text
    assert matched_marker not in canonical_json(result)
    operation = next(iter(database.operations.values()))
    assert operation.provider_data is None


class SyntheticOpenAlexResultAdapter:
    adapter_id = OPENALEX_ADAPTER_ID
    adapter_version = "v0.1"

    def __init__(self, result: ProxyAdapterResult) -> None:
        self.result = result
        self.invocation_count = 0

    def search(self, request: PaperSearchV01Request) -> ProxyAdapterResult:
        del request
        self.invocation_count += 1
        return self.result


@pytest.mark.parametrize(
    ("provider_data", "error_code", "stage", "kind", "code", "reported_cost"),
    [
        (
            {"papers": [], "synthetic": object()},
            "PROVIDER_UNAVAILABLE",
            "NORMALIZED_SERIALIZATION",
            "UNKNOWN",
            "NORMALIZED_CANONICAL_SERIALIZATION",
            0,
        ),
        (
            {"papers": [], "synthetic": "x" * (MAX_RESULT_BYTES + 1)},
            "PROVIDER_RESPONSE_TOO_LARGE",
            "RESULT_SIZE",
            "LIMIT_EXCEEDED",
            "NORMALIZED_RESULT_SIZE",
            1_000,
        ),
    ],
)
def test_service_serialization_and_size_failures_have_distinct_safe_diagnostics(
    provider_data: dict,
    error_code: str,
    stage: str,
    kind: str,
    code: str,
    reported_cost: int,
    caplog: pytest.LogCaptureFixture,
) -> None:
    adapter = SyntheticOpenAlexResultAdapter(
        ProxyAdapterResult(
            provider_data=provider_data,
            provider_http_calls=1,
            reported_cost_microusd=1_000,
        )
    )
    service, database, _, plaintext = _service(adapter, diagnostics_enabled=True)
    with caplog.at_level(logging.WARNING, logger="reagent.openalex_structural_diagnostic"):
        result = service.submit(
            bearer_token=plaintext,
            path_project_id="fictional-project",
            request=make_request(parameters=PaperSearchV01Request("fictional service", 1)),
        )
    event = _diagnostic_events(caplog)[0]
    assert result["error_code"] == error_code
    assert event["failure_stage"] == stage
    assert event["approved_json_path"] == "/normalized_results"
    assert event["observed_kind"] == kind
    assert event["validator_code"] == code
    operation = next(iter(database.operations.values()))
    assert operation.provider_data is None
    assert operation.usage is not None
    assert operation.usage.reported_cost_microusd == reported_cost


def test_unexpected_adapter_exception_emits_closed_unclassified_diagnostic_without_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    private_marker = "private-exception-" + uuid4().hex
    transport = ScriptedTransport([RuntimeError(private_marker)])
    adapter, _ = _adapter(transport)
    service, _, _, plaintext = _service(adapter, diagnostics_enabled=True)
    with caplog.at_level(logging.WARNING, logger="reagent.openalex_structural_diagnostic"):
        result = service.submit(
            bearer_token=plaintext,
            path_project_id="fictional-project",
            request=make_request(parameters=PaperSearchV01Request("fictional internal", 1)),
        )
    event = _diagnostic_events(caplog)[0]
    assert result["error_code"] == "PROVIDER_UNAVAILABLE"
    assert event["failure_stage"] == "UNCLASSIFIED_INTERNAL"
    assert event["validator_code"] == "UNCLASSIFIED_INTERNAL"
    assert private_marker not in caplog.text
    assert private_marker not in canonical_json(result)


def test_domain_model_failure_is_typed_without_raw_validation_text(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    private_marker = "private-model-error-" + uuid4().hex

    def rejecting_author(**values):
        del values
        raise ValueError(private_marker)

    monkeypatch.setattr(openalex_adapter_module, "PaperAuthor", rejecting_author)
    transport = ScriptedTransport([_response()])
    adapter, _ = _adapter(transport)
    service, _, _, plaintext = _service(adapter, diagnostics_enabled=True)
    with caplog.at_level(logging.WARNING, logger="reagent.openalex_structural_diagnostic"):
        result = service.submit(
            bearer_token=plaintext,
            path_project_id="fictional-project",
            request=make_request(parameters=PaperSearchV01Request("fictional model", 1)),
        )
    event = _diagnostic_events(caplog)[0]
    assert result["error_code"] == "PROVIDER_UNAVAILABLE"
    assert event["failure_stage"] == "PAPER_MODEL_VALIDATION"
    assert event["approved_json_path"] == "/results/*/authorships/*/author"
    assert event["observed_kind"] == "MODEL_VALIDATION"
    assert event["validator_code"] == "PAPER_AUTHOR_MODEL"
    assert event["record_index"] == 0
    assert event["nested_element_index"] == 0
    assert private_marker not in caplog.text
    assert private_marker not in canonical_json(result)


def test_fake_adapter_never_emits_openalex_diagnostics(
    caplog: pytest.LogCaptureFixture,
) -> None:
    database = InMemoryProxyDatabase()
    fake = DeterministicFakePaperSearchAdapter()
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(database),
        adapters={fake.adapter_id: fake},
        clock=lambda: NOW,
        openalex_structural_diagnostics=OpenAlexStructuralDiagnosticEmitter(enabled=True),
    )
    _, plaintext = service.issue_token(
        tenant_id="fictional-tenant",
        subject_id="fictional-subject",
        project_id="fictional-project",
        package_id="fictional-package",
        package_checksum=CHECKSUM_A,
        workflow_id="literature-search",
        workflow_version="1.0.0",
        workflow_checksum=CHECKSUM_B,
        adapter_id=fake.adapter_id,
    )
    with caplog.at_level(logging.WARNING, logger="reagent.openalex_structural_diagnostic"):
        result = service.submit(
            bearer_token=plaintext,
            path_project_id="fictional-project",
            request=make_request(parameters=PaperSearchV01Request("fictional fake", 1)),
        )
    assert result["operation_status"] == "SUCCEEDED"
    assert _diagnostic_events(caplog) == []
