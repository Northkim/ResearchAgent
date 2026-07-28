"""Opt-in real OpenAlex -> fake downstream full-stack backend acceptance.

This module is excluded unless every 9B-1 safety variable is supplied.  It
never uses ProjectDB or prior phase acceptance databases.
"""

from __future__ import annotations

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
    OpenAlexPaperSearchProvider,
)
from backend.research.services import ProviderExecutionPolicy

DATABASE_URL = os.environ.get("REAGENT_9B1_DATABASE_URL")
ARTIFACT_ROOT = os.environ.get("REAGENT_9B1_ARTIFACT_ROOT")
LIVE_ENABLED = os.environ.get("REAGENT_9B1_LIVE", "").lower() in {
    "1",
    "true",
    "yes",
}
QUERY = os.environ.get("REAGENT_9B1_QUERY")
API_KEY = os.environ.get("REAGENT_OPENALEX_API_KEY")

pytestmark = pytest.mark.skipif(
    not LIVE_ENABLED or not DATABASE_URL or not ARTIFACT_ROOT or not QUERY or not API_KEY,
    reason=(
        "Explicit REAGENT_9B1_LIVE, isolated database/artifact root, and narrow "
        "query are required"
    ),
)


def _assert_isolated_database(database_url: str) -> None:
    lowered = database_url.lower()
    assert "reagent_9b1" in lowered
    assert "projectdb" not in lowered
    assert "reagent_9a1" not in lowered
    assert "reagent_9a2" not in lowered


def _container(database_url: str, artifact_root: str) -> ApplicationContainer:
    engine = create_postgres_engine(database_url)
    factory = create_session_factory(engine)
    provider = OpenAlexPaperSearchProvider(
        OpenAlexConfiguration(
            api_key=API_KEY,
        )
    )
    return ApplicationContainer(
        unit_of_work_factory=lambda: SQLAlchemyUnitOfWork(factory),
        artifact_storage=LocalFilesystemArtifactStorage(artifact_root),
        paper_search_provider=provider,
        provider_execution_policy=ProviderExecutionPolicy.supervised_openalex(),
        close_callback=engine.dispose,
    )


def test_supervised_openalex_discovery_completes_with_fake_downstream_and_reloads() -> None:
    assert DATABASE_URL is not None
    assert ARTIFACT_ROOT is not None
    assert QUERY is not None
    _assert_isolated_database(DATABASE_URL)
    seed_research_workflow(DATABASE_URL)
    token = uuid4().hex

    with TestClient(create_app(_container(DATABASE_URL, ARTIFACT_ROOT))) as client:
        created = client.post(
            "/runs/from-catalog",
            json={
                "project_id": f"openalex-project-{token}",
                "actor_user_id": "supervised-owner",
                "idempotency_key": f"openalex-run-{token}",
                "agent_profile_ref": "supervised-openalex-fake-downstream@1.0.0",
                "workflow_id": "guided-literature-review",
                "workflow_version": "2.0.0",
                "inputs": {
                    "topic": QUERY,
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

        pending = [
            item
            for item in client.get("/approvals", params={"status": "PENDING"}).json()[
                "approvals"
            ]
            if item["workflow_run_id"] == run_id
        ]
        assert len(pending) == 1
        approval = pending[0]
        resolved = approval["requested_action"]["resolved_inputs"]
        assert 3 <= len(resolved["selected_paper_ids"]) <= 5
        assert all(
            item["source_provider"].startswith("openalex@")
            for item in resolved["approval_preview"]
        )
        assert all(item["abstract_only"] is True for item in resolved["approval_preview"])

        preapproval = client.get(f"/runs/{run_id}/artifacts").json()
        assert {
            item["logical_name"] for item in preapproval
        } == {
            "search_plan.json",
            "search_execution.json",
            "search_statistics.json",
            "papers.json",
            "selected_papers.json",
        }
        approved = client.post(
            f"/approvals/{approval['id']}/approve",
            json={
                "resolved_by": "supervised-reviewer",
                "decision_idempotency_key": f"openalex-approval-{token}",
                "current_fingerprint": approval["request_fingerprint"],
                "reason": "Exact OpenAlex discovery-only paper set reviewed.",
                "metadata": {"acceptance": "phase-9b1-live"},
            },
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["workflow_run"]["status"] == "COMPLETED"

        artifacts = client.get(f"/runs/{run_id}/artifacts").json()
        assert {
            item["logical_name"] for item in artifacts
        } == {
            "search_plan.json",
            "search_execution.json",
            "search_statistics.json",
            "papers.json",
            "selected_papers.json",
            "source_content.json",
            "paper_summaries.json",
            "evidence.json",
            "report.md",
            "provenance.json",
            "usage.json",
        }
        artifact_ids = [item["id"] for item in artifacts]
        by_name = {item["logical_name"]: item for item in artifacts}
        report = client.get(f"/artifacts/{by_name['report.md']['id']}/content")
        assert report.status_code == 200
        assert "OpenAlex" in report.text
        assert "SourceContent and LLM providers remain deterministic fakes" in report.text
        provenance = client.get(
            f"/artifacts/{by_name['provenance.json']['id']}/content"
        ).json()
        assert any(
            item["provider"] == "openalex"
            for item in provenance["provider_versions"]
        )
        assert all(
            item["access_limitation"] == "abstract_only"
            for item in provenance["source_contents"]
        )
        usage = client.get(f"/runs/{run_id}/provider-usage").json()
        openalex = [item for item in usage if item["provider_identity"] == "openalex"]
        assert len(openalex) == 1
        assert openalex[0]["status"] == "SUCCEEDED"
        assert openalex[0]["settlement_state"] == "SETTLED"
        assert openalex[0]["estimated_cost_minor_units"] == 0
        operation_ids = [item["id"] for item in usage]
        event_ids = [
            item["id"] for item in client.get(f"/runs/{run_id}/events").json()
        ]

    with TestClient(create_app(_container(DATABASE_URL, ARTIFACT_ROOT))) as client:
        persisted = client.get(f"/runs/{run_id}")
        assert persisted.status_code == 200
        assert persisted.json()["status"] == "COMPLETED"
        assert client.post(f"/runs/{run_id}/resume").json() == persisted.json()
        assert [
            item["id"] for item in client.get(f"/runs/{run_id}/artifacts").json()
        ] == artifact_ids
        assert [
            item["id"] for item in client.get(f"/runs/{run_id}/provider-usage").json()
        ] == operation_ids
        assert [
            item["id"] for item in client.get(f"/runs/{run_id}/events").json()
        ] == event_ids

    assert all(
        path.is_file()
        for path in Path(ARTIFACT_ROOT).rglob("*")
        if path.suffix
    )
