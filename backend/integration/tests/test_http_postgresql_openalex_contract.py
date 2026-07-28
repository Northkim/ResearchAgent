"""Network-free OpenAlex-shaped HTTP/PostgreSQL vertical-slice acceptance."""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.database import (
    SQLAlchemyUnitOfWork,
    create_postgres_engine,
    create_session_factory,
)
from backend.demo.seed import seed_research_workflow
from backend.research.adapters import (
    LocalFilesystemArtifactStorage,
    OpenAlexConfiguration,
    OpenAlexHttpResponse,
    OpenAlexPaperSearchProvider,
)
from backend.research.services import ProviderExecutionPolicy

DATABASE_URL = os.environ.get("REAGENT_9B1_DATABASE_URL")
ARTIFACT_ROOT = os.environ.get("REAGENT_9B1_ARTIFACT_ROOT")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or not ARTIFACT_ROOT,
    reason="9B-1 isolated database and artifact root are required",
)


class _OpenAlexContractTransport:
    def __init__(self, *, allow_calls: bool = True) -> None:
        self.allow_calls = allow_calls
        self.calls = 0

    async def get(self, path, *, params, timeout_seconds, headers):
        del params, timeout_seconds, headers
        assert self.allow_calls, "recovery must not call the provider"
        self.calls += 1
        if path == "/rate-limit":
            value = {
                "rate_limit": {
                    "daily_remaining_usd": 1,
                    "endpoint_costs_usd": {"search": 0.001},
                }
            }
        else:
            value = {
                "meta": {
                    "count": 3,
                    "per_page": 3,
                    "next_cursor": None,
                    "cost_usd": 0.001,
                },
                "results": [
                    {
                        "id": f"https://openalex.org/W900{index}",
                        "doi": f"https://doi.org/10.9999/reagent.synthetic.{index}",
                        "display_name": f"Synthetic Contract Paper {index}",
                        "authorships": [
                            {
                                "author": {
                                    "id": f"https://openalex.org/A900{index}",
                                    "display_name": f"Synthetic Contract Author {index}",
                                }
                            }
                        ],
                        "abstract_inverted_index": {
                            "Synthetic": [0],
                            "contract": [1],
                            "abstract": [2],
                            str(index): [3],
                        },
                        "publication_year": 2020 + index,
                        "primary_location": {
                            "source": {"display_name": "Synthetic Contract Venue"}
                        },
                    }
                    for index in range(1, 4)
                ],
            }
        return OpenAlexHttpResponse(
            status_code=200,
            body=json.dumps(value).encode(),
            headers={"x-request-id": f"synthetic-contract-{self.calls}"},
        )


def _container(
    database_url: str,
    artifact_root: str,
    transport: _OpenAlexContractTransport,
) -> ApplicationContainer:
    engine = create_postgres_engine(database_url)
    factory = create_session_factory(engine)
    provider = OpenAlexPaperSearchProvider(
        OpenAlexConfiguration(api_key="synthetic-test-only"),
        transport=transport,
    )
    return ApplicationContainer(
        unit_of_work_factory=lambda: SQLAlchemyUnitOfWork(factory),
        artifact_storage=LocalFilesystemArtifactStorage(artifact_root),
        paper_search_provider=provider,
        provider_execution_policy=ProviderExecutionPolicy.supervised_openalex(),
        close_callback=engine.dispose,
    )


def test_openalex_contract_path_persists_evidence_approval_report_and_reloads() -> None:
    assert DATABASE_URL is not None
    assert ARTIFACT_ROOT is not None
    assert "reagent_9b1" in DATABASE_URL.lower()
    seed_research_workflow(DATABASE_URL)
    transport = _OpenAlexContractTransport()
    token = uuid4().hex

    with TestClient(
        create_app(_container(DATABASE_URL, ARTIFACT_ROOT, transport))
    ) as client:
        created = client.post(
            "/runs/from-catalog",
            json={
                "project_id": f"openalex-contract-project-{token}",
                "actor_user_id": "supervised-owner",
                "idempotency_key": f"openalex-contract-run-{token}",
                "agent_profile_ref": "openalex-contract-fake-downstream@1.0.0",
                "workflow_id": "guided-literature-review",
                "workflow_version": "2.0.0",
                "inputs": {
                    "topic": "supervised research provenance",
                    "year_from": 2020,
                    "year_to": 2026,
                    "max_papers": 3,
                },
            },
        )
        assert created.status_code == 201, created.text
        run_id = created.json()["id"]
        waiting = client.post(f"/runs/{run_id}/resume")
        assert waiting.status_code == 200, waiting.text
        assert waiting.json()["status"] == "WAITING_FOR_APPROVAL"
        assert transport.calls == 2

        artifacts = client.get(f"/runs/{run_id}/artifacts").json()
        assert {
            item["logical_name"] for item in artifacts
        } == {
            "search_plan.json",
            "search_execution.json",
            "search_statistics.json",
            "papers.json",
            "selected_papers.json",
        }
        by_name = {item["logical_name"]: item for item in artifacts}
        execution = client.get(
            f"/artifacts/{by_name['search_execution.json']['id']}/content"
        ).json()
        assert execution["identity_status"] == "discovery_only_unverified"
        assert execution["request_count"] == 2
        assert "api_key" not in json.dumps(execution)

        approval = next(
            item
            for item in client.get("/approvals", params={"status": "PENDING"}).json()[
                "approvals"
            ]
            if item["workflow_run_id"] == run_id
        )
        assert all(
            item["source_provider"] == "openalex@1.0.0"
            for item in approval["requested_action"]["resolved_inputs"][
                "approval_preview"
            ]
        )
        approved = client.post(
            f"/approvals/{approval['id']}/approve",
            json={
                "resolved_by": "supervised-reviewer",
                "decision_idempotency_key": f"openalex-contract-approval-{token}",
                "current_fingerprint": approval["request_fingerprint"],
                "reason": "Exact discovery-only contract paper set reviewed.",
                "metadata": {"acceptance": "phase-9b1-contract"},
            },
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["workflow_run"]["status"] == "COMPLETED"

        artifacts = client.get(f"/runs/{run_id}/artifacts").json()
        assert len(artifacts) == 11
        artifact_ids = [item["id"] for item in artifacts]
        by_name = {item["logical_name"]: item for item in artifacts}
        report = client.get(f"/artifacts/{by_name['report.md']['id']}/content")
        assert report.status_code == 200
        assert "Discovery metadata supplied by [OpenAlex]" in report.text
        assert "deterministic fakes" in report.text
        provenance = client.get(
            f"/artifacts/{by_name['provenance.json']['id']}/content"
        ).json()
        assert any(
            item["provider"] == "openalex"
            for item in provenance["provider_versions"]
        )
        usage = client.get(f"/runs/{run_id}/provider-usage").json()
        assert len(usage) == 9
        openalex = next(
            item for item in usage if item["provider_identity"] == "openalex"
        )
        assert openalex["status"] == "SUCCEEDED"
        assert openalex["settlement_state"] == "SETTLED"
        assert openalex["request_count"] == 2
        assert openalex["estimated_cost_minor_units"] == 0
        operation_ids = [item["id"] for item in usage]

    recovery_transport = _OpenAlexContractTransport(allow_calls=False)
    with TestClient(
        create_app(_container(DATABASE_URL, ARTIFACT_ROOT, recovery_transport))
    ) as client:
        persisted = client.get(f"/runs/{run_id}")
        assert persisted.status_code == 200
        assert persisted.json()["status"] == "COMPLETED"
        assert client.post(f"/runs/{run_id}/resume").json() == persisted.json()
        assert recovery_transport.calls == 0
        assert [
            item["id"] for item in client.get(f"/runs/{run_id}/artifacts").json()
        ] == artifact_ids
        assert [
            item["id"] for item in client.get(f"/runs/{run_id}/provider-usage").json()
        ] == operation_ids

    assert all(
        path.is_file()
        for path in Path(ARTIFACT_ROOT).rglob("*")
        if path.suffix
    )
