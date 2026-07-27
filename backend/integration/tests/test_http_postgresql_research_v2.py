"""Real HTTP/PostgreSQL/filesystem acceptance for the v2 research workflow."""

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
from backend.demo.seed import (
    RESEARCH_WORKFLOW_HASH,
    seed_research_workflow,
)
from backend.research.adapters import LocalFilesystemArtifactStorage

DATABASE_URL = os.environ.get("REAGENT_9A2_DATABASE_URL")
ARTIFACT_ROOT = os.environ.get("REAGENT_9A2_ARTIFACT_ROOT")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or not ARTIFACT_ROOT,
    reason="9A-2 isolated database and artifact-root variables are required",
)


def _container(database_url: str, artifact_root: str) -> ApplicationContainer:
    engine = create_postgres_engine(database_url)
    factory = create_session_factory(engine)
    return ApplicationContainer(
        unit_of_work_factory=lambda: SQLAlchemyUnitOfWork(factory),
        artifact_storage=LocalFilesystemArtifactStorage(artifact_root),
        close_callback=engine.dispose,
    )


def test_v2_real_http_postgresql_artifacts_survive_restart() -> None:
    assert DATABASE_URL is not None
    assert ARTIFACT_ROOT is not None
    seed_research_workflow(DATABASE_URL)
    token = uuid4().hex
    run_id: str
    artifact_ids: list[str]
    event_ids: list[str]
    operation_ids: list[str]

    with TestClient(create_app(_container(DATABASE_URL, ARTIFACT_ROOT))) as client:
        catalog = client.get("/workflows").json()
        assert any(
            item["id"] == "guided-literature-review"
            and item["version"] == "2.0.0"
            for item in catalog
        )
        created = client.post(
            "/runs/from-catalog",
            json={
                "project_id": f"research-project-{token}",
                "actor_user_id": "research-owner",
                "idempotency_key": f"research-run-{token}",
                "agent_profile_ref": "deterministic-research-agent@2.0.0",
                "workflow_id": "guided-literature-review",
                "workflow_version": "2.0.0",
                "inputs": {
                    "topic": "persistent research agent auditability",
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
        assert waiting.json()["completed_steps"] == [
            "validate_query",
            "search_papers",
            "normalize_and_deduplicate",
            "rank_and_select",
        ]
        pending = [
            item
            for item in client.get(
                "/approvals", params={"status": "PENDING"}
            ).json()["approvals"]
            if item["workflow_run_id"] == run_id
        ]
        assert len(pending) == 1
        approval = pending[0]
        resolved = approval["requested_action"]["resolved_inputs"]
        assert resolved["source_scope"] == "abstract_only"
        assert len(resolved["selected_paper_ids"]) == 3
        assert len(resolved["approval_preview"]) == 3
        selected_artifact = resolved["selected_papers_artifact"]
        assert selected_artifact["logical_name"] == "selected_papers.json"
        artifacts_before = client.get(f"/runs/{run_id}/artifacts").json()
        assert {item["logical_name"] for item in artifacts_before} == {
            "papers.json",
            "selected_papers.json",
        }
        selected_metadata = client.get(
            f"/artifacts/{selected_artifact['artifact_id']}"
        )
        assert selected_metadata.status_code == 200
        assert selected_metadata.json()["checksum"] == selected_artifact["checksum"]

        approved = client.post(
            f"/approvals/{approval['id']}/approve",
            json={
                "resolved_by": "project-reviewer",
                "decision_idempotency_key": f"approval-{token}",
                "current_fingerprint": approval["request_fingerprint"],
                "reason": "Exact synthetic abstract-only paper set reviewed.",
                "metadata": {"acceptance": "phase-9a2"},
            },
        )
        assert approved.status_code == 200, approved.text
        completed = approved.json()["workflow_run"]
        assert completed["status"] == "COMPLETED", completed
        publication = completed["outputs"]["publication"]
        assert publication == {
            "publishable": True,
            "validator_version": "provenance-validator/v1",
            "paper_count": 3,
            "claim_count": 4,
            "evidence_count": 3,
            "citation_count": 3,
            "abstract_only": True,
            "all_provider_operations_settled": True,
            "estimated_cost_minor_units": 0,
        }

        artifacts = client.get(f"/runs/{run_id}/artifacts").json()
        assert {item["logical_name"] for item in artifacts} == {
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
        report_response = client.get(
            f"/artifacts/{by_name['report.md']['id']}/content"
        )
        assert report_response.status_code == 200
        report = report_response.text
        assert "abstract-only" in report
        assert all(label in report for label in ("[P1]", "[P2]", "[P3]"))
        provenance_response = client.get(
            f"/artifacts/{by_name['provenance.json']['id']}/content"
        )
        assert provenance_response.status_code == 200
        provenance = provenance_response.json()
        assert provenance["workflow_hash"] == f"sha256:{RESEARCH_WORKFLOW_HASH}"
        assert provenance["report_checksum"] == by_name["report.md"]["checksum"]
        assert len(provenance["citations"]) == 3
        assert len(provenance["evidence_units"]) == 3
        assert len(provenance["grounded_claims"]) == 4
        assert all(
            item["access_limitation"] == "abstract_only"
            for item in provenance["source_contents"]
        )

        usage = client.get(f"/runs/{run_id}/provider-usage").json()
        assert len(usage) == 9
        assert all(item["status"] == "SUCCEEDED" for item in usage)
        assert all(item["settlement_state"] == "SETTLED" for item in usage)
        assert sum(item["estimated_cost_minor_units"] or 0 for item in usage) == 0
        operation_ids = [item["id"] for item in usage]

        events = client.get(f"/runs/{run_id}/events").json()
        assert [item["sequence"] for item in events] == list(
            range(1, len(events) + 1)
        )
        assert events[-1]["type"] == "WORKFLOW_COMPLETED"
        event_ids = [item["id"] for item in events]

    with TestClient(
        create_app(_container(DATABASE_URL, ARTIFACT_ROOT))
    ) as restarted_client:
        persisted = restarted_client.get(f"/runs/{run_id}")
        assert persisted.status_code == 200
        assert persisted.json()["status"] == "COMPLETED"
        assert restarted_client.post(f"/runs/{run_id}/resume").json() == persisted.json()
        assert [
            item["id"]
            for item in restarted_client.get(f"/runs/{run_id}/artifacts").json()
        ] == artifact_ids
        assert [
            item["id"]
            for item in restarted_client.get(f"/runs/{run_id}/events").json()
        ] == event_ids
        assert [
            item["id"]
            for item in restarted_client.get(
                f"/runs/{run_id}/provider-usage"
            ).json()
        ] == operation_ids
        for artifact_id in artifact_ids:
            assert restarted_client.get(
                f"/artifacts/{artifact_id}/content"
            ).status_code == 200

    assert all(path.is_file() for path in Path(ARTIFACT_ROOT).rglob("*") if path.suffix)
