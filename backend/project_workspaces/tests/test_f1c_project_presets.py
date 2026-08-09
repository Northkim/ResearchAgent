from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.local_projects.service import LocalProjectService
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces.application import ProjectWorkspaceApplicationService
from backend.project_workspaces import workspace_cli
from backend.progress_reports.aggregation import _readiness


def _client(tmp_path):
    database = InMemoryDatabase()
    return TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        local_package_root=str(tmp_path / "packages"),
    ))), database


def _create(client, setup=None, custom=()):
    payload = {
        "name": "Fictional full research setup",
        "research_topic": "Public synthetic product-flow topic",
        "selected_workflow": "LITERATURE_SEARCH",
    }
    if setup is not None:
        payload["workflow_setup"] = setup
        payload["custom_workflow_definition_ids"] = list(custom)
    return client.post("/projects", json=payload)


@pytest.mark.parametrize(("setup", "expected"), (
    (None, ("literature-search-local-experimental",)),
    ("literature-only", ("literature-search-local-experimental",)),
    ("literature-and-idea", ("literature-search-local-experimental", "idea-discovery-local-experimental")),
    ("full-research", (
        "literature-search-local-experimental", "idea-discovery-local-experimental",
        "writing-local-experimental", "review-local-experimental",
        "reproduction-experiment-local-experimental",
    )),
))
def test_server_resolved_presets_create_one_revision_atomically(tmp_path, setup, expected):
    client, _ = _client(tmp_path)
    response = _create(client, setup)
    assert response.status_code == 201
    project_id = response.json()["project_id"]
    instances = client.get(f"/projects/{project_id}/workflow-instances").json()
    manifest = client.get(f"/projects/{project_id}/manifest").json()
    assert instances["manifest_revision"] == 1
    assert {item["workflow_definition_id"] for item in instances["items"]} == set(expected)
    assert len(manifest["manifest"]["workflow_instances"]) == len(expected)
    versions = {item["workflow_definition_id"]: (item["workflow_version"], item["capsule_version"]) for item in instances["items"]}
    assert versions["literature-search-local-experimental"] == ("0.4.0", "0.6.0")
    if setup == "full-research":
        assert versions["idea-discovery-local-experimental"] == ("0.2.0", "0.2.0")
        assert versions["writing-local-experimental"] == ("0.2.0", "0.2.0")
        assert versions["review-local-experimental"] == ("0.2.0", "0.2.0")
        assert versions["reproduction-experiment-local-experimental"] == ("0.3.0", "0.3.0")


def test_custom_is_registry_validated_and_preserves_requested_independent_workflows(tmp_path):
    client, _ = _client(tmp_path)
    response = _create(client, "custom", ("writing-local-experimental", "review-local-experimental"))
    assert response.status_code == 201
    project_id = response.json()["project_id"]
    instances = client.get(f"/projects/{project_id}/workflow-instances").json()["items"]
    assert {item["workflow_definition_id"] for item in instances} == {"writing-local-experimental", "review-local-experimental"}

    invalid = _create(client, "custom", ("not-a-registry-workflow",))
    assert invalid.status_code == 404


def test_full_preset_failure_rolls_back_project_instances_and_manifest(tmp_path, monkeypatch):
    database = InMemoryDatabase()
    uow = InMemoryUnitOfWork(database)
    workspace = ProjectWorkspaceApplicationService(unit_of_work=uow, clock=lambda: datetime(2026, 8, 9, tzinfo=UTC))
    original = uow.workflow_foundation.add_workflow_instance
    count = 0

    def fail_third(instance):
        nonlocal count
        count += 1
        if count == 3:
            raise RuntimeError("injected preset instance failure")
        original(instance)

    monkeypatch.setattr(uow.workflow_foundation, "add_workflow_instance", fail_third)
    service = LocalProjectService(
        repository=uow.local_projects,
        commit_callback=uow.commit,
        rollback_callback=uow.rollback,
        project_setup_initializer=workspace.initialize_project_setup,
        package_root=tmp_path / "packages",
        project_id_factory=lambda: "project-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        clock=lambda: datetime(2026, 8, 9, tzinfo=UTC),
    )
    with pytest.raises(RuntimeError, match="injected preset"):
        service.create(name="Atomic full preset", research_topic="Public synthetic topic", selected_workflow="LITERATURE_SEARCH", workflow_setup="full-research")
    assert database.local_projects == {}
    assert database.projects == {}
    assert database.project_workflow_instances == {}
    assert database.desired_manifests == {}


class _Transport:
    def __init__(self, client):
        self.client = client
        self.downloads = 0

    def create_plan(self, project_id, payload):
        response = self.client.post(f"/projects/{project_id}/workspace/sync-plan", json=payload)
        assert response.status_code == 200
        return response.json()

    def download(self, path, expected=None):
        self.downloads += 1
        response = self.client.get(path)
        assert response.status_code == 200
        return response.content

    def acknowledge(self, project_id, payload):
        response = self.client.post(f"/projects/{project_id}/workspace/sync-ack", json=payload)
        assert response.status_code in {200, 201}
        return response.json()


def test_full_preset_bootstrap_syncs_exactly_five_capsules_then_noops(tmp_path):
    client, _ = _client(tmp_path)
    created = _create(client, "full-research")
    project_id = created.json()["project_id"]
    descriptor = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
    assert len(descriptor["workflow_capsules"]) == 5
    workspace = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=descriptor)
    transport = _Transport(client)
    first = workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    assert first.status == "SYNCED"
    assert transport.downloads == 5
    listed = workspace_cli.workflow_list(workspace)
    assert len(listed["workflows"]) == 5
    assert {item["core_capability_maturity"] for item in listed["workflows"]} == {"REVIEWED_CORE", "SCAFFOLD_CORE"}
    progress = client.get(f"/projects/{project_id}/progress").json()
    by_definition = {item["workflow_definition_id"]: item for item in progress["instances"]}
    assert by_definition["literature-search-local-experimental"]["readiness"] == "READY_TO_RUN"
    assert by_definition["literature-search-local-experimental"]["next_action"] == "RUN"
    for definition_id in (
        "idea-discovery-local-experimental", "writing-local-experimental",
        "review-local-experimental", "reproduction-experiment-local-experimental",
    ):
        assert by_definition[definition_id]["readiness"] == "WAITING_FOR_INPUT"
        assert by_definition[definition_id]["next_action"] == "WAIT_FOR_UPSTREAM"
    assert progress["recommended_workflow_instance_id"] == by_definition["literature-search-local-experimental"]["workflow_instance_id"]
    assert progress["recommended_next_action"] == "RUN"
    second = workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    assert second.status == "NO_CHANGE"
    assert transport.downloads == 5


def test_readiness_distinguishes_upstream_selection_materialization_and_review_revision():
    common = dict(lifecycle="ACTIVE", installation_state="ACKNOWLEDGED_CURRENT", report_count=0, research_status="NOT_STARTED", result_count=0, stable_key="writing-local-experimental")
    assert _readiness(missing=("research_idea",), compatible_counts={"research_idea": 0}, **common) == ("WAITING_FOR_INPUT", "WAIT_FOR_UPSTREAM")
    assert _readiness(missing=("research_idea",), compatible_counts={"research_idea": 2}, **common) == ("WAITING_FOR_INPUT", "SELECT_INPUT")
    assert _readiness(missing=(), compatible_counts={"research_idea": 2}, **common) == ("NEEDS_MATERIALIZATION", "MATERIALIZE")
    assert _readiness(missing=(), compatible_counts={}, **common) == ("READY_TO_RUN", "RUN")
    review = {**common, "stable_key": "review-local-experimental", "research_status": "COMPLETED", "result_count": 1}
    assert _readiness(missing=(), compatible_counts={"manuscript": 2}, **review) == ("RESULT_READY", "REVISE_MANUSCRIPT")
