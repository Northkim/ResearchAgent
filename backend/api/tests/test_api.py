"""HTTP contract tests using only deterministic in-memory adapters."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.application.execution import ExecutionDispatcher, ExecutionRequest
from backend.agent_runtime import AgentRuntime
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork


@pytest.fixture
def api_client() -> Iterator[tuple[TestClient, InMemoryDatabase]]:
    database = InMemoryDatabase()
    container = ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database)
    )
    with TestClient(create_app(container)) as client:
        yield client, database


def _linear_run_payload(*, idempotency_key: str = "request-1") -> dict:
    return {
        "project_id": "project-1",
        "actor_user_id": "user-1",
        "idempotency_key": idempotency_key,
        "agent_profile_ref": "researcher-v1",
        "inputs": {"query": "persistent research agents"},
        "workflow": {
            "id": "literature-review",
            "version": "1.0.0",
            "name": "Literature review",
            "input_schema": {"query": {"type": "string", "required": True}},
            "outputs": {
                "summary": "${nodes.summarize.outputs.summary}",
            },
            "steps": [
                {
                    "id": "search",
                    "kind": "skill",
                    "uses": "mock_paper_search@1.0.0",
                    "input_mapping": {"query": "${inputs.query}"},
                },
                {
                    "id": "summarize",
                    "kind": "skill",
                    "needs": ["search"],
                    "uses": "mock_summary@1.0.0",
                    "input_mapping": {
                        "papers": "${nodes.search.outputs.papers}",
                    },
                },
            ],
        },
    }


def _approval_run_payload() -> dict:
    return {
        "project_id": "project-approval",
        "actor_user_id": "user-1",
        "idempotency_key": "approval-run-1",
        "agent_profile_ref": "researcher-v1",
        "inputs": {"query": "human oversight"},
        "workflow": {
            "id": "approval-gated-search",
            "version": "1.0.0",
            "name": "Approval gated search",
            "input_schema": {"query": {"type": "string", "required": True}},
            "outputs": {"papers": "${nodes.search.outputs.papers}"},
            "steps": [
                {
                    "id": "approve_search",
                    "kind": "approval",
                    "approval_policy": "research.search.v1",
                },
                {
                    "id": "search",
                    "kind": "skill",
                    "needs": ["approve_search"],
                    "uses": "mock_paper_search@1.0.0",
                    "input_mapping": {"query": "${inputs.query}"},
                },
            ],
        },
    }


def test_health_does_not_require_persistence_configuration() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_creates_and_retrieves_workflow_run(api_client) -> None:
    client, _ = api_client

    created = client.post("/runs", json=_linear_run_payload())

    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "CREATED"
    assert body["checkpoint_count"] == 1
    assert [step["step_id"] for step in body["steps"]] == ["search", "summarize"]

    fetched = client.get(f"/runs/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_resume_endpoint_completes_deterministic_workflow(api_client) -> None:
    client, _ = api_client
    created = client.post("/runs", json=_linear_run_payload()).json()

    resumed = client.post(f"/runs/{created['id']}/resume")

    assert resumed.status_code == 200
    body = resumed.json()
    assert body["status"] == "COMPLETED"
    assert body["completed_steps"] == ["search", "summarize"]
    assert body["outputs"]["summary"].startswith("Mock summary:")


def test_create_idempotency_replays_exact_request_and_rejects_drift(api_client) -> None:
    client, _ = api_client
    payload = _linear_run_payload()
    first = client.post("/runs", json=payload)

    replay = client.post("/runs", json=payload)
    changed = _linear_run_payload()
    changed["workflow"]["name"] = "Changed definition"
    conflict = client.post("/runs", json=changed)

    assert replay.status_code == 201
    assert replay.json() == first.json()
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "CONFLICT"


def test_resume_endpoint_is_idempotent_after_completion(api_client) -> None:
    client, _ = api_client
    run_id = client.post("/runs", json=_linear_run_payload()).json()["id"]
    first = client.post(f"/runs/{run_id}/resume")

    second = client.post(f"/runs/{run_id}/resume")

    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()


def test_approval_endpoint_resolves_request_and_resumes_run(api_client) -> None:
    client, database = api_client
    run_id = client.post("/runs", json=_approval_run_payload()).json()["id"]
    waiting = client.post(f"/runs/{run_id}/resume")
    assert waiting.status_code == 200
    assert waiting.json()["status"] == "WAITING_FOR_APPROVAL"

    approvals = list(database.approvals.values())
    assert len(approvals) == 1
    approval = approvals[0]

    response = client.post(
        f"/approvals/{approval.id}/approve",
        json={
            "resolved_by": "user-1",
            "decision_idempotency_key": "approval-decision-1",
            "current_fingerprint": approval.request_fingerprint,
            "reason": "Search is in scope",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["approval"]["status"] == "APPROVED"
    assert body["workflow_run"]["status"] == "COMPLETED"


def test_rejecting_runtime_approval_cancels_run(api_client) -> None:
    client, database = api_client
    run_id = client.post("/runs", json=_approval_run_payload()).json()["id"]
    client.post(f"/runs/{run_id}/resume")
    approval = next(iter(database.approvals.values()))

    response = client.post(
        f"/approvals/{approval.id}/reject",
        json={
            "resolved_by": "user-1",
            "decision_idempotency_key": "reject-1",
            "reason": "Out of scope",
        },
    )

    assert response.status_code == 200
    assert response.json()["approval"]["status"] == "REJECTED"
    assert response.json()["workflow_run"]["status"] == "CANCELLED"


def test_expired_approval_is_persisted_and_cancels_run() -> None:
    class MutableClock:
        def __init__(self) -> None:
            self.now = datetime(2026, 7, 21, 8, 0, tzinfo=UTC)

        def __call__(self) -> datetime:
            return self.now

    database = InMemoryDatabase()
    clock = MutableClock()
    container = ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        clock=clock,
        approval_ttl=timedelta(minutes=5),
    )
    with TestClient(create_app(container)) as client:
        run_id = client.post("/runs", json=_approval_run_payload()).json()["id"]
        client.post(f"/runs/{run_id}/resume")
        approval = next(iter(database.approvals.values()))
        clock.now += timedelta(minutes=6)

        response = client.post(
            f"/approvals/{approval.id}/approve",
            json={
                "resolved_by": "user-1",
                "decision_idempotency_key": "too-late-1",
                "current_fingerprint": approval.request_fingerprint,
            },
        )

    assert response.status_code == 200
    assert response.json()["approval"]["status"] == "EXPIRED"
    assert response.json()["workflow_run"]["status"] == "CANCELLED"


def test_run_list_supports_pagination_and_status_filter(api_client) -> None:
    client, _ = api_client
    completed_id = client.post("/runs", json=_linear_run_payload()).json()["id"]
    client.post(f"/runs/{completed_id}/resume")
    client.post(
        "/runs",
        json=_linear_run_payload(idempotency_key="request-2"),
    )

    all_runs = client.get("/runs", params={"offset": 0, "limit": 1})
    completed = client.get(
        "/runs",
        params={"status": "COMPLETED", "offset": 0, "limit": 10},
    )

    assert all_runs.status_code == 200
    assert all_runs.json()["total"] == 2
    assert len(all_runs.json()["runs"]) == 1
    assert completed.status_code == 200
    assert completed.json()["total"] == 1
    assert completed.json()["runs"][0]["id"] == completed_id


def test_event_timeline_returns_ordered_runtime_events(api_client) -> None:
    client, _ = api_client
    run_id = client.post("/runs", json=_linear_run_payload()).json()["id"]
    client.post(f"/runs/{run_id}/resume")

    response = client.get(f"/runs/{run_id}/events")

    assert response.status_code == 200
    events = response.json()
    assert [event["sequence"] for event in events] == list(
        range(1, len(events) + 1)
    )
    assert events[0]["type"] == "WORKFLOW_STARTED"
    assert events[-1]["type"] == "WORKFLOW_COMPLETED"
    assert {event["type"] for event in events} >= {
        "STEP_STARTED",
        "SKILL_EXECUTED",
        "CHECKPOINT_CREATED",
    }


def test_approval_list_supports_pending_status_filter(api_client) -> None:
    client, _ = api_client
    run_id = client.post("/runs", json=_approval_run_payload()).json()["id"]
    client.post(f"/runs/{run_id}/resume")

    response = client.get("/approvals", params={"status": "PENDING"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["approvals"][0]["workflow_run_id"] == run_id
    assert body["approvals"][0]["request_fingerprint"].startswith("sha256:")


def test_workflow_catalog_returns_known_definitions(api_client) -> None:
    client, _ = api_client
    client.post("/runs", json=_linear_run_payload())
    client.post("/runs", json=_approval_run_payload())

    response = client.get("/workflows")

    assert response.status_code == 200
    assert [workflow["id"] for workflow in response.json()] == [
        "approval-gated-search",
        "literature-review",
    ]


def test_resume_api_submits_execution_request_to_dispatcher() -> None:
    requests: list[ExecutionRequest] = []

    class RecordingDispatcher(ExecutionDispatcher):
        def __init__(self, runtime: AgentRuntime) -> None:
            self.runtime = runtime

        async def submit(self, request: ExecutionRequest):
            requests.append(request)
            return await self.runtime.run(
                request.workflow_run_id,
                approval_outcome=request.approval_outcome,
            )

    database = InMemoryDatabase()
    container = ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        dispatcher_factory=RecordingDispatcher,
    )
    with TestClient(create_app(container)) as client:
        run_id = client.post("/runs", json=_linear_run_payload()).json()["id"]
        response = client.post(f"/runs/{run_id}/resume")

    assert response.status_code == 200
    assert requests == [ExecutionRequest(workflow_run_id=run_id)]


def test_cancel_endpoint_uses_domain_terminal_state(api_client) -> None:
    client, _ = api_client
    run_id = client.post("/runs", json=_linear_run_payload()).json()["id"]

    response = client.post(f"/runs/{run_id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert {step["status"] for step in response.json()["steps"]} == {"CANCELLED"}


def test_invalid_workflow_is_a_stable_422_response(api_client) -> None:
    client, _ = api_client
    payload = _linear_run_payload()
    payload["workflow"]["steps"][0]["uses"] = None

    response = client.post("/runs", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_unknown_run_is_a_stable_404_response(api_client) -> None:
    client, _ = api_client

    response = client.get("/runs/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
