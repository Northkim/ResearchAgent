from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.controlled_local_run_approvals import (
    ControlledLocalRunApproval,
    ControlledLocalRunSummary,
)
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.tests.test_generic_experiment_public_workspace import (
    WORKFLOW_ID,
    _seed_publication,
)
from backend.workflow_packages.generic_experiment_publication import (
    GENERIC_EXPERIMENT_CAPSULE_ID,
)

NOW = datetime(2026, 8, 17, 12, tzinfo=timezone.utc)
SHA = tuple("sha256:" + character * 64 for character in "123456789abcdef")


def _summary(**changes) -> ControlledLocalRunSummary:
    values = {
        "what_will_run": "A bounded local categorical comparison.",
        "research_objective": "Compare two deterministic text transformations.",
        "preparation_method": "Reviewed synthetic textual preparation.",
        "research_resources": (),
        "execution_environment": "Controlled non-Python text runtime.",
        "network_policy": "DISABLED",
        "compute_limits": ("At most 60 seconds.", "At most 64 MiB output."),
        "expected_outputs": ("One bounded categorical result.",),
        "evaluation_approach": "Compare the declared categories for exact equality.",
        "important_assumptions": ("Input text is already verified.",),
        "important_limitations": ("This does not generalize beyond the fixture.",),
    }
    return ControlledLocalRunSummary(**{**values, **changes})


def _request(project_id: str, instance_id: str, *, at=NOW, plan=SHA[1]):
    return ControlledLocalRunApproval.create(
        project_id=project_id,
        workflow_instance_id=instance_id,
        research_objective_checksum=SHA[0],
        execution_plan_checksum=plan,
        validated_package_checksum=SHA[2],
        runtime_compatibility_checksum=SHA[3],
        capability_checksum=SHA[4],
        summary=_summary(),
        created_at=at,
    )


def _setup(tmp_path):
    database = InMemoryDatabase()
    factory = lambda: InMemoryUnitOfWork(database)
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=factory,
        local_package_root=str(tmp_path / "packages"),
        clock=lambda: NOW,
    )))
    project = client.post("/projects", json={
        "name": "Controlled-local approval fixture",
        "research_topic": "Exact local authorization",
        "selected_workflow": "LITERATURE_SEARCH",
    }).json()
    _seed_publication(database)
    instance = client.post(
        f"/projects/{project['project_id']}/workflow-instances",
        json={
            "workflow_definition_id": WORKFLOW_ID,
            "workflow_version": "0.6.0",
            "capsule_id": GENERIC_EXPERIMENT_CAPSULE_ID,
            "capsule_version": "0.9.0",
            "base_revision": 1,
        },
    )
    assert instance.status_code == 201, instance.text
    return database, client, project["project_id"], instance.json()["workflow_instance_id"]


def _path(project_id: str, instance_id: str) -> str:
    return f"/projects/{project_id}/workflow-instances/{instance_id}/run-approvals"


def _decision(request, key="owner-decision-1"):
    return {
        "execution_plan_checksum": request.execution_plan_checksum,
        "request_checksum": request.request_checksum,
        "idempotency_key": key,
    }


def test_contract_is_exact_bounded_and_rejects_private_payloads() -> None:
    summary = _summary()
    request = _request("project-" + "a" * 32, "wfi-" + "b" * 32)
    assert summary.summary_checksum.startswith("sha256:")
    assert request.request_id == "clra-" + request.request_checksum[7:39]
    assert request.to_dict()["summary"]["summary_checksum"] == summary.summary_checksum

    for unsafe in (
        "/Users/owner/private/result.txt",
        "path=/tmp/private-result.txt",
        "API_KEY=fictional-secret",
        "Traceback (most recent call last): failure",
        "[INFO] raw process log",
        "Bearer fictional-token",
        "print('source code')",
        "```python",
        "<script>alert('x')</script>",
    ):
        with pytest.raises(ValueError):
            _summary(what_will_run=unsafe)
    with pytest.raises(ValueError, match="byte bound"):
        _summary(important_limitations=tuple("x" * 900 for _ in range(20)))


def test_api_create_approve_consume_and_retry_are_exact(tmp_path) -> None:
    database, client, project_id, instance_id = _setup(tmp_path)
    path = _path(project_id, instance_id)
    empty = client.get(path.removesuffix("s"))
    assert empty.status_code == 200
    assert empty.json() == {
        "request": None, "next_action": "REPORT_EXACT_RUN_APPROVAL_REQUEST"
    }

    request = _request(project_id, instance_id)
    changed = request.request_dict()
    changed["summary"]["what_will_run"] = "A different unapproved operation."
    rejected_change = client.post(path, json=changed)
    assert rejected_change.status_code == 422
    assert rejected_change.json()["error"]["code"] == "RUN_APPROVAL_REQUEST_INVALID"
    created = client.post(path, json=request.request_dict())
    replay = client.post(path, json=request.request_dict())
    assert created.status_code == replay.status_code == 201
    assert created.json() == replay.json()
    assert created.json()["schema"] == "reagent.controlled-local-run-approval/v0.1"
    assert "schema_id" not in created.json()
    assert created.json()["status"] == "REQUESTED"

    wrong = client.post(
        f"{path}/{request.request_id}/approve",
        json={**_decision(request), "execution_plan_checksum": SHA[9]},
    )
    assert wrong.status_code == 409
    assert wrong.json()["error"]["code"] == "APPROVAL_IDENTITY_MISMATCH"

    approved = client.post(
        f"{path}/{request.request_id}/approve", json=_decision(request)
    )
    approved_replay = client.post(
        f"{path}/{request.request_id}/approve", json=_decision(request)
    )
    assert approved.status_code == approved_replay.status_code == 200
    assert approved.json() == approved_replay.json()
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["approval_checksum"].startswith("sha256:")

    consume = {
        "execution_plan_checksum": request.execution_plan_checksum,
        "attempt_id": "attempt-" + "c" * 32,
    }
    first = client.post(f"{path}/{request.request_id}/consume", json=consume)
    retry = client.post(f"{path}/{request.request_id}/consume", json=consume)
    assert first.status_code == retry.status_code == 200
    assert first.json() == retry.json()
    assert first.json()["approval"]["status"] == "CONSUMED"
    assert first.json()["receipt"]["consumption_checksum"].startswith("sha256:")
    second = client.post(
        f"{path}/{request.request_id}/consume",
        json={**consume, "attempt_id": "attempt-" + "d" * 32},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ALREADY_CONSUMED"
    assert database.executions == {}
    assert database.approvals == {}


def test_non_experiment_scope_and_unsafe_api_summary_fail_closed(tmp_path) -> None:
    _, client, project_id, instance_id = _setup(tmp_path)
    instances = client.get(f"/projects/{project_id}/workflow-instances").json()["items"]
    literature_id = next(
        item["workflow_instance_id"] for item in instances
        if item["workflow_definition_id"] == "literature-search-local-experimental"
    )
    wrong_workflow = _request(project_id, literature_id)
    denied = client.post(
        _path(project_id, literature_id), json=wrong_workflow.request_dict()
    )
    assert denied.status_code == 422
    assert denied.json()["error"]["code"] == "RUN_APPROVAL_WORKFLOW_UNSUPPORTED"

    request = _request(project_id, instance_id)
    unsafe = request.request_dict()
    unsafe["summary"]["execution_environment"] = "path=/private/tmp/launcher"
    denied = client.post(_path(project_id, instance_id), json=unsafe)
    assert denied.status_code == 422
    assert denied.json()["error"]["code"] == "RUN_APPROVAL_REQUEST_INVALID"


def test_workspace_http_transport_uses_only_scoped_approval_routes(monkeypatch) -> None:
    project_id = "project-" + "a" * 32
    instance_id = "wfi-" + "b" * 32
    request = _request(project_id, instance_id)
    transport = workspace_cli.HTTPWorkspaceSyncTransport("http://127.0.0.1:8123")
    calls = []
    monkeypatch.setattr(
        transport,
        "_json_request",
        lambda method, route, payload: calls.append((method, route, payload)) or payload,
    )
    monkeypatch.setattr(
        transport,
        "_json_get",
        lambda route: calls.append(("GET", route, None)) or {"request": None},
    )

    assert transport.report_run_approval(
        project_id, instance_id, request.request_dict()
    )["request_id"] == request.request_id
    assert transport.observe_run_approval(project_id, instance_id) == {"request": None}
    transport.consume_run_approval(
        project_id, instance_id, request.request_id,
        {"execution_plan_checksum": request.execution_plan_checksum,
         "attempt_id": "attempt-" + "c" * 32},
    )
    assert [item[0] for item in calls] == ["POST", "GET", "POST"]
    assert all(route.startswith(f"/projects/{project_id}/workflow-instances/{instance_id}/") for _, route, _ in calls)


def test_supersession_rejection_and_scope_fail_closed(tmp_path) -> None:
    _, client, project_id, instance_id = _setup(tmp_path)
    path = _path(project_id, instance_id)
    first = _request(project_id, instance_id)
    second = _request(
        project_id, instance_id, at=NOW + timedelta(seconds=1), plan=SHA[5]
    )
    assert client.post(path, json=first.request_dict()).status_code == 201
    approved_first = client.post(
        f"{path}/{first.request_id}/approve", json=_decision(first)
    )
    assert approved_first.status_code == 200
    assert client.post(path, json=second.request_dict()).status_code == 201
    stale = client.post(f"{path}/{first.request_id}/approve", json=_decision(first))
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "APPROVAL_SUPERSEDED"
    stale_consume = client.post(
        f"{path}/{first.request_id}/consume",
        json={
            "execution_plan_checksum": first.execution_plan_checksum,
            "attempt_id": "attempt-" + "9" * 32,
        },
    )
    assert stale_consume.status_code == 409
    assert stale_consume.json()["error"]["code"] == "APPROVAL_SUPERSEDED"

    rejected = client.post(
        f"{path}/{second.request_id}/reject",
        json={**_decision(second, "reject-1"), "reason": "Scientific design needs revision."},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"
    rejected_replay = client.post(
        f"{path}/{second.request_id}/reject",
        json={**_decision(second, "reject-1"), "reason": "Scientific design needs revision."},
    )
    assert rejected_replay.status_code == 200
    assert rejected_replay.json() == rejected.json()
    denied = client.post(
        f"{path}/{second.request_id}/consume",
        json={
            "execution_plan_checksum": second.execution_plan_checksum,
            "attempt_id": "attempt-" + "e" * 32,
        },
    )
    assert denied.status_code == 409
    assert denied.json()["error"]["code"] == "APPROVAL_REJECTED"

    cross = client.post(
        f"/projects/project-{'f' * 32}/workflow-instances/{instance_id}/"
        f"run-approvals/{second.request_id}/approve",
        json=_decision(second, "cross-project"),
    )
    assert cross.status_code == 404


class _ApprovalTransport:
    def __init__(self, client: TestClient):
        self.client = client

    def observe_run_approval(self, project_id, workflow_instance_id):
        response = self.client.get(
            f"/projects/{project_id}/workflow-instances/{workflow_instance_id}/run-approval"
        )
        assert response.status_code == 200, response.text
        return response.json()

    def consume_run_approval(self, project_id, workflow_instance_id, request_id, payload):
        response = self.client.post(
            f"/projects/{project_id}/workflow-instances/{workflow_instance_id}/"
            f"run-approvals/{request_id}/consume",
            json=payload,
        )
        if response.status_code != 200:
            body = response.json()["error"]
            raise workspace_cli.WorkspaceCLIError(
                body["code"], body["message"], workspace_cli.EXIT_CLOUD
            )
        return response.json()


def test_local_revalidation_gates_only_the_injected_bounded_runner_handoff(tmp_path) -> None:
    _, client, project_id, instance_id = _setup(tmp_path)
    request = _request(project_id, instance_id)
    path = _path(project_id, instance_id)
    client.post(path, json=request.request_dict())
    client.post(f"{path}/{request.request_id}/approve", json=_decision(request))
    calls = []

    result = workspace_cli.controlled_local_run_approval_handoff(
        transport=_ApprovalTransport(client), project_id=project_id,
        workflow_instance_id=instance_id, request_id=request.request_id,
        attempt_id="attempt-" + "a" * 32,
        current_plan_checksum=lambda: request.execution_plan_checksum,
        bounded_runner_handoff=lambda approval, receipt: calls.append(
            (approval, receipt)
        ) or "RUNNER_HANDOFF",
    )
    assert result == "RUNNER_HANDOFF"
    assert len(calls) == 1
    assert calls[0][1]["execution_plan_checksum"] == request.execution_plan_checksum


def test_post_consumption_plan_drift_never_invokes_runner(tmp_path) -> None:
    _, client, project_id, instance_id = _setup(tmp_path)
    request = _request(project_id, instance_id)
    path = _path(project_id, instance_id)
    client.post(path, json=request.request_dict())
    client.post(f"{path}/{request.request_id}/approve", json=_decision(request))
    checksums = iter((request.execution_plan_checksum, SHA[8]))
    calls = []
    with pytest.raises(workspace_cli.WorkspaceCLIError) as drift:
        workspace_cli.controlled_local_run_approval_handoff(
            transport=_ApprovalTransport(client), project_id=project_id,
            workflow_instance_id=instance_id, request_id=request.request_id,
            attempt_id="attempt-" + "b" * 32,
            current_plan_checksum=lambda: next(checksums),
            bounded_runner_handoff=lambda *_: calls.append(True),
        )
    assert drift.value.code == "APPROVAL_INVALIDATED"
    assert calls == []
    observed = client.get(path.removesuffix("s")).json()["request"]
    assert observed["status"] == "CONSUMED"


def test_pre_consumption_drift_and_launch_failure_do_not_recycle_approval(tmp_path) -> None:
    _, client, project_id, instance_id = _setup(tmp_path)
    request = _request(project_id, instance_id)
    path = _path(project_id, instance_id)
    client.post(path, json=request.request_dict())
    client.post(f"{path}/{request.request_id}/approve", json=_decision(request))
    transport = _ApprovalTransport(client)

    with pytest.raises(workspace_cli.WorkspaceCLIError) as drift:
        workspace_cli.controlled_local_run_approval_handoff(
            transport=transport, project_id=project_id,
            workflow_instance_id=instance_id, request_id=request.request_id,
            attempt_id="attempt-" + "3" * 32,
            current_plan_checksum=lambda: SHA[9],
            bounded_runner_handoff=lambda *_: pytest.fail("runner must not be invoked"),
        )
    assert drift.value.code == "APPROVAL_INVALIDATED"
    assert client.get(path.removesuffix("s")).json()["request"]["status"] == "APPROVED"

    def launch_failure(*_):
        raise RuntimeError("synthetic process launch failure")

    with pytest.raises(RuntimeError, match="synthetic process launch failure"):
        workspace_cli.controlled_local_run_approval_handoff(
            transport=transport, project_id=project_id,
            workflow_instance_id=instance_id, request_id=request.request_id,
            attempt_id="attempt-" + "4" * 32,
            current_plan_checksum=lambda: request.execution_plan_checksum,
            bounded_runner_handoff=launch_failure,
        )
    assert client.get(path.removesuffix("s")).json()["request"]["status"] == "CONSUMED"


def test_local_handoff_rejects_mismatched_cloud_consumption_receipt(tmp_path) -> None:
    _, client, project_id, instance_id = _setup(tmp_path)
    request = _request(project_id, instance_id)
    path = _path(project_id, instance_id)
    client.post(path, json=request.request_dict())
    client.post(f"{path}/{request.request_id}/approve", json=_decision(request))

    class TamperedTransport(_ApprovalTransport):
        def consume_run_approval(self, *args):
            value = super().consume_run_approval(*args)
            value["approval"]["workflow_instance_id"] = "wfi-" + "f" * 32
            return value

    with pytest.raises(workspace_cli.WorkspaceCLIError) as error:
        workspace_cli.controlled_local_run_approval_handoff(
            transport=TamperedTransport(client), project_id=project_id,
            workflow_instance_id=instance_id, request_id=request.request_id,
            attempt_id="attempt-" + "5" * 32,
            current_plan_checksum=lambda: request.execution_plan_checksum,
            bounded_runner_handoff=lambda *_: pytest.fail("runner must not be invoked"),
        )
    assert error.value.code == "RUN_APPROVAL_INVALID"
