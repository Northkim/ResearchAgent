from __future__ import annotations

import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.cloud_api_proxy.composition import (
    ProxyApplicationContainer,
    feature_enabled,
    openalex_structural_diagnostics_enabled,
)
from backend.cloud_api_proxy.openalex_diagnostics import STRUCTURAL_DIAGNOSTIC_FEATURE_FLAG
from backend.cloud_api_proxy.contracts import MAX_REQUEST_BYTES, canonical_json, canonical_hash
from backend.cloud_api_proxy import (
    CloudAPIProxyService,
    DeterministicFakePaperSearchAdapter,
    InMemoryProxyDatabase,
    InMemoryProxyUnitOfWork,
)
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork

from .conftest import CHECKSUM_A, CHECKSUM_B, NOW, make_request


def _client(proxy_setup):
    service, _, _, _, plaintext = proxy_setup
    hosted_database = InMemoryDatabase()
    hosted = ApplicationContainer(unit_of_work_factory=lambda: InMemoryUnitOfWork(hosted_database))
    proxy = ProxyApplicationContainer(service=service)
    client = TestClient(
        create_app(hosted, proxy_container=proxy, enable_experimental_proxy=True),
        base_url="http://127.0.0.1",
        client=("127.0.0.1", 50123),
    )
    return client, hosted_database, plaintext


def _mutable_client():
    current = [NOW]
    database = InMemoryProxyDatabase()
    adapter = DeterministicFakePaperSearchAdapter()
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(database),
        adapter=adapter,
        clock=lambda: current[0],
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
    )
    hosted_database = InMemoryDatabase()
    hosted = ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(hosted_database),
    )
    client = TestClient(
        create_app(
            hosted,
            proxy_container=ProxyApplicationContainer(service=service),
            enable_experimental_proxy=True,
        ),
        base_url="http://127.0.0.1",
        client=("127.0.0.1", 50123),
    )
    return client, database, adapter, hosted_database, plaintext, current


def test_proxy_is_not_mounted_by_default() -> None:
    hosted = ApplicationContainer(unit_of_work_factory=lambda: InMemoryUnitOfWork(InMemoryDatabase()))
    with TestClient(create_app(hosted), base_url="http://127.0.0.1", client=("127.0.0.1", 50123)) as client:
        response = client.post("/projects/fictional-project/proxy-operations", json={})
    assert response.status_code == 404


def test_default_startup_does_not_construct_openalex_credential_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.cloud_api_proxy import openalex_adapter

    def forbidden_source():
        raise AssertionError("default startup attempted to construct the OpenAlex credential source")

    monkeypatch.delenv("REAGENT_EXPERIMENTAL_FAKE_PROXY_ENABLED", raising=False)
    monkeypatch.delenv("REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED", raising=False)
    monkeypatch.setattr(openalex_adapter, "EnvironmentOpenAlexCredentialSource", forbidden_source)
    hosted = ApplicationContainer(unit_of_work_factory=lambda: InMemoryUnitOfWork(InMemoryDatabase()))
    with TestClient(create_app(hosted), base_url="http://127.0.0.1") as client:
        assert client.get("/health").status_code == 200


def test_diagnostic_flag_alone_does_not_mount_proxy_or_read_openalex_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.cloud_api_proxy import openalex_adapter

    def forbidden_source():
        raise AssertionError("diagnostic flag attempted to construct a credential source")

    monkeypatch.delenv("REAGENT_EXPERIMENTAL_FAKE_PROXY_ENABLED", raising=False)
    monkeypatch.delenv("REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED", raising=False)
    monkeypatch.setenv(STRUCTURAL_DIAGNOSTIC_FEATURE_FLAG, "1")
    monkeypatch.setattr(openalex_adapter, "EnvironmentOpenAlexCredentialSource", forbidden_source)
    assert openalex_structural_diagnostics_enabled() is True
    assert feature_enabled() is False
    hosted = ApplicationContainer(unit_of_work_factory=lambda: InMemoryUnitOfWork(InMemoryDatabase()))
    with TestClient(create_app(hosted), base_url="http://127.0.0.1") as client:
        assert client.get("/health").status_code == 200
        assert client.post("/projects/fictional-project/proxy-operations", json={}).status_code == 404


@pytest.mark.parametrize(
    ("value", "enabled"),
    [("1", True), ("0", False), ("true", False), ("TRUE", False), ("", False)],
)
def test_structural_diagnostic_flag_requires_exact_one(value: str, enabled: bool) -> None:
    assert openalex_structural_diagnostics_enabled(value) is enabled


def test_openalex_enabled_composition_without_credential_fails_closed_before_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.cloud_api_proxy import composition, openalex_adapter

    class Engine:
        disposed = False

        def dispose(self) -> None:
            self.disposed = True

    class MissingCredential:
        def get(self) -> str:
            raise RuntimeError("Experimental OpenAlex Proxy requires its server credential")

    engine = Engine()
    monkeypatch.setenv("REAGENT_DATABASE_URL", "postgresql://127.0.0.1:1/isolated-invalid")
    monkeypatch.setenv("REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED", "1")
    monkeypatch.delenv("REAGENT_EXPERIMENTAL_FAKE_PROXY_ENABLED", raising=False)
    monkeypatch.setattr(composition, "create_postgres_engine", lambda _: engine)
    monkeypatch.setattr(composition, "create_session_factory", lambda _: object())
    monkeypatch.setattr(
        openalex_adapter,
        "EnvironmentOpenAlexCredentialSource",
        MissingCredential,
    )
    with pytest.raises(RuntimeError, match="credential"):
        ProxyApplicationContainer.from_environment()
    assert engine.disposed is True


def test_enabled_without_persistence_configuration_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REAGENT_DATABASE_URL", raising=False)
    hosted = ApplicationContainer(unit_of_work_factory=lambda: InMemoryUnitOfWork(InMemoryDatabase()))
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        create_app(hosted, enable_experimental_proxy=True)


def test_submit_get_and_reconcile_read_use_strict_envelopes(proxy_setup) -> None:
    client, hosted_database, plaintext = _client(proxy_setup)
    request = make_request()
    headers = {"Authorization": f"Bearer {plaintext}", "Content-Type": "application/json"}
    with client:
        created = client.post(
            "/projects/fictional-project/proxy-operations",
            content=canonical_json(request.to_dict()).encode(),
            headers=headers,
        )
        by_id = client.get(
            f"/projects/fictional-project/proxy-operations/{created.json()['operation_id']}",
            headers={"Authorization": f"Bearer {plaintext}"},
        )
        by_key = client.get(
            "/projects/fictional-project/proxy-operations",
            params={"package_id": request.package_id, "idempotency_key": request.idempotency_key},
            headers={"Authorization": f"Bearer {plaintext}"},
        )
    assert created.status_code == 201
    assert by_id.status_code == by_key.status_code == 200
    assert by_id.json()["operation_id"] == by_key.json()["operation_id"]
    assert plaintext not in json.dumps(created.json())
    assert not hosted_database.executions
    assert not hosted_database.execution_events
    assert not hosted_database.checkpoint_records
    assert not hosted_database.memory_revisions
    assert not hosted_database.provider_operations


def test_api_delayed_replay_conflict_and_stale_new_admission_keep_existing_contract() -> None:
    client, database, adapter, hosted_database, plaintext, current = _mutable_client()
    request = make_request()
    headers = {
        "Authorization": f"Bearer {plaintext}",
        "Content-Type": "application/json",
    }
    request_bytes = canonical_json(request.to_dict()).encode()

    with client:
        created = client.post(
            "/projects/fictional-project/proxy-operations",
            content=request_bytes,
            headers=headers,
        )
        current[0] = NOW + timedelta(minutes=6)
        replay = client.post(
            "/projects/fictional-project/proxy-operations",
            content=request_bytes,
            headers=headers,
        )
        changed = make_request(
            idempotency_key=request.idempotency_key,
            client_timestamp="2026-08-04T08:00:01Z",
        )
        conflict = client.post(
            "/projects/fictional-project/proxy-operations",
            content=canonical_json(changed.to_dict()).encode(),
            headers=headers,
        )
        stale_new = client.post(
            "/projects/fictional-project/proxy-operations",
            content=canonical_json(make_request().to_dict()).encode(),
            headers=headers,
        )
        malformed_payload = make_request().to_dict()
        malformed_payload["client_timestamp"] = "not-a-timestamp"
        malformed = client.post(
            "/projects/fictional-project/proxy-operations",
            content=canonical_json(malformed_payload).encode(),
            headers=headers,
        )
        by_id = client.get(
            f"/projects/fictional-project/proxy-operations/{created.json()['operation_id']}",
            headers={"Authorization": f"Bearer {plaintext}"},
        )
        by_key = client.get(
            "/projects/fictional-project/proxy-operations",
            params={
                "package_id": request.package_id,
                "idempotency_key": request.idempotency_key,
            },
            headers={"Authorization": f"Bearer {plaintext}"},
        )

    assert created.status_code == 201
    assert replay.status_code == 200
    assert replay.json()["idempotency_result"] == "REPLAYED"
    assert replay.json()["operation_id"] == created.json()["operation_id"]
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert stale_new.status_code == 422
    assert stale_new.json()["error"]["code"] == "CLIENT_TIMESTAMP_OUT_OF_RANGE"
    assert malformed.status_code == 422
    assert by_id.status_code == by_key.status_code == 200
    assert by_id.json()["operation_id"] == by_key.json()["operation_id"]
    assert len(database.operations) == 1
    assert adapter.invocation_count == 1
    exposed = "\n".join(
        json.dumps(item.json(), sort_keys=True)
        for item in (created, replay, conflict, stale_new, malformed, by_id, by_key)
    )
    assert plaintext not in exposed
    error_exposed = "\n".join(
        json.dumps(item.json(), sort_keys=True)
        for item in (conflict, stale_new, malformed)
    )
    assert request.parameters.query not in error_exposed
    assert not hosted_database.executions
    assert not hosted_database.provider_operations


def test_malformed_timestamp_rejects_before_service_or_repository_identity_lookup() -> None:
    class GuardedService:
        called = False

        def submit(self, **kwargs):
            self.called = True
            raise AssertionError("malformed timestamp reached the Proxy service")

    guarded = GuardedService()
    hosted = ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(InMemoryDatabase()),
    )
    app = create_app(
        hosted,
        proxy_container=ProxyApplicationContainer(service=guarded),
        enable_experimental_proxy=True,
    )
    payload = make_request().to_dict()
    payload["client_timestamp"] = "not-a-timestamp"

    with TestClient(
        app,
        base_url="http://127.0.0.1",
        client=("127.0.0.1", 50123),
    ) as client:
        response = client.post(
            "/projects/fictional-project/proxy-operations",
            content=canonical_json(payload).encode(),
            headers={
                "Authorization": "Bearer " + "x" * 43,
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 422
    assert guarded.called is False


def test_missing_token_nonloopback_and_unknown_fields_reject(proxy_setup) -> None:
    service, _, adapter, _, plaintext = proxy_setup
    hosted = ApplicationContainer(unit_of_work_factory=lambda: InMemoryUnitOfWork(InMemoryDatabase()))
    app = create_app(hosted, proxy_container=ProxyApplicationContainer(service=service), enable_experimental_proxy=True)
    payload = make_request().to_dict()
    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50123)) as client:
        missing = client.post("/projects/fictional-project/proxy-operations", json=payload)
        payload["tenant_id"] = "attacker"
        unexpected = client.post(
            "/projects/fictional-project/proxy-operations",
            json=payload,
            headers={"Authorization": f"Bearer {plaintext}"},
        )
        diagnostic_payload = make_request().to_dict()
        diagnostic_payload["structural_diagnostics"] = True
        diagnostic_request = client.post(
            "/projects/fictional-project/proxy-operations",
            json=diagnostic_payload,
            headers={"Authorization": f"Bearer {plaintext}"},
        )
    with TestClient(app, base_url="http://127.0.0.1", client=("192.0.2.10", 50123)) as remote:
        nonloopback = remote.post(
            "/projects/fictional-project/proxy-operations",
            json=make_request().to_dict(),
            headers={"Authorization": f"Bearer {plaintext}"},
        )
    assert missing.status_code == 401
    assert unexpected.status_code == 422
    assert diagnostic_request.status_code == 422
    assert nonloopback.status_code == 403
    assert adapter.invocation_count == 0


def test_forwarded_peer_and_arbitrary_host_are_not_trusted(proxy_setup) -> None:
    client, _, plaintext = _client(proxy_setup)
    payload = make_request().to_dict()
    with client:
        forwarded = client.post(
            "/projects/fictional-project/proxy-operations",
            json=payload,
            headers={
                "Authorization": f"Bearer {plaintext}",
                "X-Forwarded-For": "203.0.113.8",
            },
        )
        hostile_host = client.post(
            "/projects/fictional-project/proxy-operations",
            json=make_request().to_dict(),
            headers={"Authorization": f"Bearer {plaintext}", "Host": "example.invalid"},
        )
    assert forwarded.status_code == 201
    assert hostile_host.status_code == 403


def test_actual_body_size_bound_ignores_content_length_claim(proxy_setup) -> None:
    client, _, plaintext = _client(proxy_setup)
    request_bytes = canonical_json(make_request().to_dict()).encode()
    exact = request_bytes + b" " * (MAX_REQUEST_BYTES - len(request_bytes))
    over = exact + b" "
    headers = {
        "Authorization": f"Bearer {plaintext}",
        "Content-Type": "application/json",
        "Content-Length": "1",
    }
    with client:
        accepted = client.post("/projects/fictional-project/proxy-operations", content=exact, headers=headers)
        rejected = client.post("/projects/fictional-project/proxy-operations", content=over, headers=headers)
        missing_length = client.post(
            "/projects/fictional-project/proxy-operations",
            content=(chunk for chunk in (canonical_json(make_request().to_dict()).encode(),)),
            headers={
                "Authorization": f"Bearer {plaintext}",
                "Content-Type": "application/json",
            },
        )
    assert accepted.status_code == 201
    assert rejected.status_code == 413
    assert missing_length.status_code == 201


def test_malformed_duplicate_and_unsupported_media_type_reject(proxy_setup) -> None:
    client, _, plaintext = _client(proxy_setup)
    auth = {"Authorization": f"Bearer {plaintext}"}
    with client:
        malformed = client.post("/projects/fictional-project/proxy-operations", content=b"{", headers={**auth, "Content-Type": "application/json"})
        duplicate = client.post("/projects/fictional-project/proxy-operations", content=b'{"a":1,"a":2}', headers={**auth, "Content-Type": "application/json"})
        media = client.post("/projects/fictional-project/proxy-operations", content=b"{}", headers={**auth, "Content-Type": "text/plain"})
        encoding = client.post("/projects/fictional-project/proxy-operations", content=b"{}", headers={**auth, "Content-Type": "application/json; charset=latin-1"})
    assert malformed.status_code == duplicate.status_code == 422
    assert media.status_code == encoding.status_code == 415


def test_delivery_response_checksum_excludes_only_itself(proxy_setup) -> None:
    client, _, plaintext = _client(proxy_setup)
    with client:
        response = client.post(
            "/projects/fictional-project/proxy-operations",
            json=make_request().to_dict(),
            headers={"Authorization": f"Bearer {plaintext}"},
        )
    body = response.json()
    checksum = body.pop("response_checksum")
    assert checksum == canonical_hash(body)
