from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from backend.cloud_api_proxy.contracts import (
    ADAPTER_ID,
    PaperSearchV01Request,
    ProxyAuthorizationScope,
    build_operation_id,
    canonical_json,
)

from .conftest import CHECKSUM_A, CHECKSUM_B, make_request


def _scope() -> ProxyAuthorizationScope:
    return ProxyAuthorizationScope(
        token_id="proxytok-v1-" + "c" * 64,
        tenant_id="tenant", subject_id="subject", project_id="fictional-project",
        package_id="fictional-package", package_checksum=CHECKSUM_A,
        workflow_id="literature-search", workflow_version="1.0.0",
        workflow_checksum=CHECKSUM_B, capability="paper.search/v0.1",
        adapter_id=ADAPTER_ID, maximum_operations=50,
    )


def test_request_identity_is_stable_noncyclic_and_version_namespaced() -> None:
    request = make_request(idempotency_key="93b56851-0ddf-4a58-86e6-b82a3c2ffb98")
    assert request.request_content_checksum == request.computed_request_checksum()
    assert "idempotency_key" not in request.semantic_content()
    assert "request_content_checksum" not in request.semantic_content()
    assert "operation_id" not in request.semantic_content()
    first = build_operation_id(request, _scope())
    second = build_operation_id(request, _scope())
    assert first == second
    assert first.startswith("proxyop-v1-")


def test_changed_semantic_content_changes_checksum_and_operation_identity() -> None:
    first = make_request(idempotency_key="93b56851-0ddf-4a58-86e6-b82a3c2ffb98")
    changed = make_request(
        idempotency_key=first.idempotency_key,
        parameters=PaperSearchV01Request(query="different fictional query"),
    )
    assert first.request_content_checksum != changed.request_content_checksum
    assert build_operation_id(first, _scope()) != build_operation_id(changed, _scope())


def test_submitted_checksum_is_independently_verified() -> None:
    request = make_request()
    with pytest.raises(ValueError, match="does not match"):
        replace(request, request_content_checksum="sha256:" + "f" * 64).verify_checksum()


@pytest.mark.parametrize("parameters", [
    {"query": ""}, {"query": "x" * 501}, {"query": "ok", "max_results": True},
    {"query": "ok", "max_results": 0}, {"query": "ok", "max_results": 21},
    {"query": "ok", "url": "http://127.0.0.1"}, {"query": "bad\u001btext"},
])
def test_paper_search_schema_rejects_invalid_or_extra_fields(parameters: dict) -> None:
    with pytest.raises(ValueError):
        PaperSearchV01Request.from_dict(parameters)


def test_request_rejects_client_authorization_fields() -> None:
    value = make_request().to_dict()
    value["actor_user_id"] = "attacker"
    with pytest.raises(ValueError, match="authorization"):
        type(make_request()).from_dict(value)


def test_contract_is_frozen_and_canonical_json_is_deterministic() -> None:
    request = make_request()
    with pytest.raises(FrozenInstanceError):
        request.project_id = "changed"  # type: ignore[misc]
    assert canonical_json({"b": 1, "a": "é"}) == '{"a":"é","b":1}'
