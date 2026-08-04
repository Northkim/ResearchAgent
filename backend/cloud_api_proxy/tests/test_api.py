from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.cloud_api_proxy.composition import ProxyApplicationContainer
from backend.cloud_api_proxy.contracts import MAX_REQUEST_BYTES, canonical_json, canonical_hash
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork

from .conftest import make_request


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
    with TestClient(app, base_url="http://127.0.0.1", client=("192.0.2.10", 50123)) as remote:
        nonloopback = remote.post(
            "/projects/fictional-project/proxy-operations",
            json=make_request().to_dict(),
            headers={"Authorization": f"Bearer {plaintext}"},
        )
    assert missing.status_code == 401
    assert unexpected.status_code == 422
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
