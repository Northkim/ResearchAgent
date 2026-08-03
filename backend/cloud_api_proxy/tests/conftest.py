from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from backend.cloud_api_proxy import (
    CAPABILITY,
    PROXY_CONTRACT_VERSION,
    CloudAPIProxyService,
    CloudProxyRequestEnvelope,
    DeterministicFakePaperSearchAdapter,
    InMemoryProxyDatabase,
    InMemoryProxyUnitOfWork,
    PaperSearchV01Request,
)

NOW = datetime(2026, 8, 4, 8, 0, tzinfo=UTC)
CHECKSUM_A = "sha256:" + "a" * 64
CHECKSUM_B = "sha256:" + "b" * 64


@pytest.fixture()
def proxy_setup():
    database = InMemoryProxyDatabase()
    adapter = DeterministicFakePaperSearchAdapter()
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(database),
        adapter=adapter,
        clock=lambda: NOW,
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
    )
    return service, database, adapter, token, plaintext


def make_request(**overrides) -> CloudProxyRequestEnvelope:
    values = {
        "proxy_contract_version": PROXY_CONTRACT_VERSION,
        "idempotency_key": str(uuid4()),
        "project_id": "fictional-project",
        "package_id": "fictional-package",
        "package_checksum": CHECKSUM_A,
        "workflow_id": "literature-search",
        "workflow_version": "1.0.0",
        "workflow_checksum": CHECKSUM_B,
        "capability": CAPABILITY,
        "parameters": PaperSearchV01Request(query="fictional continuity", max_results=2),
        "harness_type": "CODEX",
        "harness_version": None,
        "harness_session_id": "fictional-session",
        "client_timestamp": "2026-08-04T08:00:00Z",
    }
    values.update(overrides)
    return CloudProxyRequestEnvelope.create(**values)
