"""Real HTTP -> application -> Runtime -> SQL Unit of Work -> PostgreSQL proof."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.api import ApplicationContainer, create_app
from backend.database import (
    SQLAlchemyUnitOfWork,
    create_postgres_engine,
    create_session_factory,
)
from backend.database.engine import normalize_postgres_url
from backend.database.orm import WorkflowDefinitionORM
from backend.demo.seed import (
    DEMO_WORKFLOW_HASH,
    DEMO_WORKFLOW_ID,
    DEMO_WORKFLOW_VERSION,
    seed_demo_workflow,
)

DATABASE_URL = os.environ.get("REAGENT_E2E_DATABASE_URL")
ALLOW_RESET = os.environ.get("REAGENT_ALLOW_DATABASE_RESET") == "1"

pytestmark = pytest.mark.skipif(
    not DATABASE_URL or not ALLOW_RESET,
    reason=(
        "REAGENT_E2E_DATABASE_URL and REAGENT_ALLOW_DATABASE_RESET=1 are required "
        "for the destructive isolated PostgreSQL integration test"
    ),
)

QUERY = "persistent research agents"
EXPECTED_SUMMARY = (
    "Mock summary: Mock Foundations of persistent research agents; "
    "Mock Advances in persistent research agents"
)


def _migrate_from_clean_database(database_url: str) -> None:
    configuration = Config("alembic.ini")
    configuration.set_main_option(
        "sqlalchemy.url",
        normalize_postgres_url(database_url).replace("%", "%%"),
    )
    with patch.dict(os.environ, {"REAGENT_DATABASE_URL": database_url}):
        command.downgrade(configuration, "base")
        command.upgrade(configuration, "head")


def _container(database_url: str) -> ApplicationContainer:
    engine = create_postgres_engine(database_url)
    session_factory = create_session_factory(engine)
    return ApplicationContainer(
        unit_of_work_factory=lambda: SQLAlchemyUnitOfWork(session_factory),
        close_callback=engine.dispose,
    )


def _assert_semantic_event_order(events: list[dict]) -> None:
    semantic = [
        (event["type"], event["payload"].get("step_id"))
        for event in events
        if event["type"] != "CHECKPOINT_CREATED"
    ]
    assert semantic == [
        ("WORKFLOW_STARTED", None),
        ("STEP_STARTED", "search"),
        ("SKILL_EXECUTED", "search"),
        ("APPROVAL_REQUESTED", "approve_sources"),
        ("STEP_STARTED", "summarize"),
        ("SKILL_EXECUTED", "summarize"),
        ("WORKFLOW_COMPLETED", None),
    ]


def test_real_http_postgresql_demo_survives_application_restart() -> None:
    assert DATABASE_URL is not None
    _migrate_from_clean_database(DATABASE_URL)

    first_seed = seed_demo_workflow(DATABASE_URL)
    repeated_seed = seed_demo_workflow(DATABASE_URL)
    assert first_seed.created is True
    assert repeated_seed.created is False
    assert repeated_seed.canonical_hash == DEMO_WORKFLOW_HASH

    inspection_engine = create_postgres_engine(DATABASE_URL)
    inspection_factory = create_session_factory(inspection_engine)
    with inspection_factory() as session:
        assert session.scalar(select(func.count()).select_from(WorkflowDefinitionORM)) == 1
    inspection_engine.dispose()

    with TestClient(create_app(_container(DATABASE_URL))) as client:
        catalog_response = client.get("/workflows")
        assert catalog_response.status_code == 200
        catalog = catalog_response.json()
        assert [(item["id"], item["version"]) for item in catalog] == [
            (DEMO_WORKFLOW_ID, DEMO_WORKFLOW_VERSION)
        ]

        create_response = client.post(
            "/runs",
            json={
                "project_id": "e2e-project",
                "actor_user_id": "e2e-user",
                "idempotency_key": "e2e-http-postgresql-run-1",
                "agent_profile_ref": "deterministic-agent@1.0.0",
                "workflow": catalog[0],
                "inputs": {"query": QUERY},
            },
        )
        assert create_response.status_code == 201
        run_id = create_response.json()["id"]

        waiting_response = client.post(f"/runs/{run_id}/resume")
        assert waiting_response.status_code == 200
        assert waiting_response.json()["status"] == "WAITING_FOR_APPROVAL"
        assert waiting_response.json()["completed_steps"] == ["search"]

        approvals_response = client.get(
            "/approvals",
            params={"status": "PENDING"},
        )
        assert approvals_response.status_code == 200
        approvals = approvals_response.json()["approvals"]
        assert len(approvals) == 1
        approval = approvals[0]
        assert approval["workflow_run_id"] == run_id

        approved_response = client.post(
            f"/approvals/{approval['id']}/approve",
            json={
                "resolved_by": "e2e-reviewer",
                "decision_idempotency_key": "e2e-approval-decision-1",
                "current_fingerprint": approval["request_fingerprint"],
                "reason": "Deterministic sources reviewed for the demo.",
                "metadata": {"source": "http_postgresql_integration"},
            },
        )
        assert approved_response.status_code == 200
        completed = approved_response.json()["workflow_run"]
        assert completed["status"] == "COMPLETED"
        assert completed["outputs"] == {"summary": EXPECTED_SUMMARY}

        events_response = client.get(f"/runs/{run_id}/events")
        assert events_response.status_code == 200
        events = events_response.json()
        assert [event["sequence"] for event in events] == list(
            range(1, len(events) + 1)
        )
        assert events[-1]["type"] == "WORKFLOW_COMPLETED"
        _assert_semantic_event_order(events)
        original_event_ids = [event["id"] for event in events]

    with TestClient(create_app(_container(DATABASE_URL))) as restarted_client:
        persisted_response = restarted_client.get(f"/runs/{run_id}")
        assert persisted_response.status_code == 200
        assert persisted_response.json()["status"] == "COMPLETED"
        assert persisted_response.json()["outputs"]["summary"] == EXPECTED_SUMMARY

        replay_response = restarted_client.post(f"/runs/{run_id}/resume")
        assert replay_response.status_code == 200
        assert replay_response.json() == persisted_response.json()

        persisted_events = restarted_client.get(f"/runs/{run_id}/events").json()
        assert [event["id"] for event in persisted_events] == original_event_ids
