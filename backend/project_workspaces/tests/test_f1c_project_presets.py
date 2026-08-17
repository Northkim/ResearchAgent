from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.local_projects.service import LocalProjectService
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces.application import ProjectWorkspaceApplicationService
from backend.project_workspaces import workspace_cli
from backend.progress_reports.aggregation import _readiness, _workflow_action


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
        assert versions["idea-discovery-local-experimental"] == ("0.2.0", "0.3.0")
        assert versions["reproduction-experiment-local-experimental"] == ("0.4.0", "0.7.0")
        assert versions["writing-local-experimental"] == ("0.3.0", "0.5.0")
        assert versions["review-local-experimental"] == ("0.3.0", "0.5.0")


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
    expected_pins = {
        "literature-search-local-experimental": (
            "0.4.0", "0.6.0", "capsule-e9e6a2e0aa46146818fb6123e03877f3"
        ),
        "idea-discovery-local-experimental": (
            "0.2.0", "0.3.0", "capsule-3976596c49e3df30e08774233055bcce"
        ),
        "reproduction-experiment-local-experimental": (
            "0.4.0", "0.7.0", "capsule-a01688245334eb95a7733a746e6357c1"
        ),
        "writing-local-experimental": (
            "0.3.0", "0.5.0", "capsule-3f94b97702190efed2a4fcd2c0e5f770"
        ),
        "review-local-experimental": (
            "0.3.0", "0.5.0", "capsule-d8565c18f6d0c5d540d4d0ff63b90d7e"
        ),
    }
    assert {
        item["workflow_definition_id"]: (
            item["workflow_definition_version"], item["capsule_version"],
            item["capsule_id"],
        )
        for item in descriptor["workflow_capsules"]
    } == expected_pins
    assert {
        item["workflow_definition_id"]: (
            item["workflow_definition_version"], item["capsule_version"],
            item["capsule_id"],
        )
        for item in descriptor["desired_manifest"]["workflow_instances"]
    } == expected_pins
    workspace = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=descriptor)
    transport = _Transport(client)
    first = workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    assert first.status == "SYNCED"
    assert transport.downloads == 5
    listed = workspace_cli.workflow_list(workspace)
    assert len(listed["workflows"]) == 5
    assert {item["core_capability_maturity"] for item in listed["workflows"]} == {"REVIEWED_CORE"}
    expected_versions = {
        definition_id: pin[:2] for definition_id, pin in expected_pins.items()
    }
    assert {
        item["workflow_definition_id"]: (
            item["workflow_version"], item["capsule_version"]
        )
        for item in listed["workflows"]
    } == expected_versions
    installed_lock = json.loads(
        (workspace / workspace_cli.INSTALLED_LOCK).read_text(encoding="utf-8")
    )
    assert {
        item["workflow_definition_id"]: (
            item["workflow_definition_version"], item["capsule_version"],
            item["capsule_id"],
        )
        for item in installed_lock["installed_capsules"]
    } == expected_pins
    repository = Path(__file__).resolve().parents[3]
    public_list = subprocess.run(
        [
            sys.executable,
            str(repository / "reagent_local.py"),
            "workflow",
            "list",
            ".",
            "--json",
        ],
        cwd=workspace,
        check=False,
        capture_output=True,
        text=True,
    )
    assert public_list.returncode == 0, public_list.stderr
    public_result = json.loads(public_list.stdout)
    assert {
        item["workflow_definition_id"]: (
            item["workflow_version"], item["capsule_version"]
        )
        for item in public_result["workflows"]
    } == expected_versions
    human_list = subprocess.run(
        [
            sys.executable,
            str(repository / "reagent_local.py"),
            "workflow",
            "list",
            ".",
        ],
        cwd=workspace,
        check=False,
        capture_output=True,
        text=True,
    )
    assert human_list.returncode == 0, human_list.stderr
    assert "Installed Workflows (5)" in human_list.stdout
    assert human_list.stdout.count("Core: Reviewed") == 5
    assert "Core: Scaffold" not in human_list.stdout
    for display_name, version in (
        ("Literature Search", "0.4.0"),
        ("Idea Discovery", "0.2.0"),
        ("Reproduction & Experiment", "0.4.0"),
        ("Writing", "0.3.0"),
        ("Review", "0.3.0"),
    ):
        assert display_name in human_list.stdout
        assert f"version {version}" in human_list.stdout
    progress = client.get(f"/projects/{project_id}/progress").json()
    by_definition = {item["workflow_definition_id"]: item for item in progress["instances"]}
    assert {item["installation_state"] for item in progress["instances"]} == {"ACKNOWLEDGED_CURRENT"}
    assert by_definition["literature-search-local-experimental"]["readiness"] == "READY_TO_RUN"
    assert by_definition["literature-search-local-experimental"]["next_action"] == "RUN"
    assert by_definition["literature-search-local-experimental"]["action"]["stage"]["code"] == "READY"
    assert by_definition["literature-search-local-experimental"]["action"]["next_action"]["code"] == "RUN"
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

    literature = by_definition["literature-search-local-experimental"]
    added = client.post(f"/projects/{project_id}/workflow-instances", json={
        "workflow_definition_id": literature["workflow_definition_id"],
        "workflow_version": literature["workflow_definition_version"],
        "capsule_id": literature["capsule_id"],
        "capsule_version": literature["capsule_version"],
        "base_revision": 1,
    })
    assert added.status_code == 201
    stale_progress = client.get(f"/projects/{project_id}/progress").json()
    assert {item["installation_state"] for item in stale_progress["instances"]} == {"ACKNOWLEDGED_STALE"}
    assert {item["action"]["next_action"]["code"] for item in stale_progress["instances"]} == {"SYNC"}
    assert stale_progress["attention"]["action"]["next_action"]["code"] == "SYNC"


def test_installation_projection_distinguishes_first_setup_from_stale_sync(tmp_path):
    client, _ = _client(tmp_path)
    created = _create(client, "full-research")
    project_id = created.json()["project_id"]

    progress = client.get(f"/projects/{project_id}/progress").json()
    assert {item["installation_state"] for item in progress["instances"]} == {"UNKNOWN"}
    assert {item["readiness"] for item in progress["instances"]} == {"NOT_INSTALLED"}
    assert {item["next_action"] for item in progress["instances"]} == {"SETUP"}
    for item in progress["instances"]:
        assert item["action"]["stage"]["code"] == "LOCAL_SETUP"
        assert item["action"]["blocker"]["code"] == "LOCAL_SETUP_REQUIRED"
        assert item["action"]["next_action"] == {
            "surface": "BROWSER",
            "code": "SETUP",
            "label": "Set up Local Workspace",
            "description": "Open the supported Project setup instructions before creating and syncing the Local Workspace.",
        }
    assert progress["attention"]["recommended_workflow_label"] == "Literature Search"
    assert progress["attention"]["action"]["next_action"]["code"] == "SETUP"
    assert progress["attention"]["action"]["next_action"]["surface"] == "BROWSER"
    assert progress["attention"]["action"]["expected_output"]["label"] == "Selected paper library"

    stale = _workflow_action(
        project_id=project_id,
        workflow_definition_id="literature-search-local-experimental",
        output_schema_id="selected-paper-library/v1",
        lifecycle="ACTIVE",
        research_status="NOT_STARTED",
        latest_summary=None,
        continuation_reason=None,
        installation_state="ACKNOWLEDGED_STALE",
        readiness="NOT_INSTALLED",
        next_action="SYNC",
        missing=(),
        latest_artifact=None,
    )
    assert stale.stage.code == "LOCAL_SYNC"
    assert stale.blocker is not None and stale.blocker.code == "LOCAL_SYNC_REQUIRED"
    assert stale.next_action.code == "SYNC"
    assert stale.next_action.surface == "LOCAL"


def test_readiness_distinguishes_upstream_selection_materialization_and_review_revision():
    common = dict(lifecycle="ACTIVE", installation_state="ACKNOWLEDGED_CURRENT", report_count=0, research_status="NOT_STARTED", result_count=0, stable_key="writing-local-experimental")
    assert _readiness(missing=("research_idea",), compatible_counts={"research_idea": 0}, **common) == ("WAITING_FOR_INPUT", "WAIT_FOR_UPSTREAM")
    assert _readiness(missing=("research_idea",), compatible_counts={"research_idea": 2}, **common) == ("WAITING_FOR_INPUT", "SELECT_INPUT")
    assert _readiness(missing=(), compatible_counts={"research_idea": 2}, **common) == ("NEEDS_MATERIALIZATION", "MATERIALIZE")
    assert _readiness(missing=(), compatible_counts={}, **common) == ("READY_TO_RUN", "RUN")
    review = {**common, "stable_key": "review-local-experimental", "research_status": "COMPLETED", "result_count": 1}
    assert _readiness(missing=(), compatible_counts={"manuscript": 2}, **review) == ("RESULT_READY", "REVISE_MANUSCRIPT")


def test_required_resource_blocks_cloud_run_without_changing_resource_authority():
    common = dict(
        lifecycle="ACTIVE",
        installation_state="ACKNOWLEDGED_CURRENT",
        missing=(),
        compatible_counts={"research_idea": 1},
        report_count=0,
        research_status="NOT_STARTED",
        result_count=0,
        stable_key="reproduction-experiment-local-experimental",
        required_resource_count=1,
    )
    missing = _readiness(
        missing_resources=("source_repository",),
        **common,
    )
    assert missing == ("WAITING_FOR_RESOURCE", "SELECT_RESOURCE")
    missing_action = _workflow_action(
        project_id="project-resource-projection",
        workflow_definition_id="reproduction-experiment-local-experimental",
        output_schema_id="experiment-record/v2",
        lifecycle="ACTIVE",
        research_status="NOT_STARTED",
        latest_summary=None,
        continuation_reason=None,
        installation_state="ACKNOWLEDGED_CURRENT",
        readiness=missing[0],
        next_action=missing[1],
        missing=(),
        missing_resources=("source_repository",),
        latest_artifact=None,
    )
    assert missing_action.stage.code == "RESOURCE_BINDING"
    assert missing_action.blocker is not None
    assert missing_action.blocker.code == "REQUIRED_RESOURCE_NOT_BOUND"
    assert missing_action.next_action.code == "SELECT_RESOURCE"
    assert missing_action.next_action.code != "RUN"

    bound = _readiness(missing_resources=(), **common)
    assert bound == ("NEEDS_RESOURCE_STAGING", "STAGE_RESOURCE")
    bound_action = _workflow_action(
        project_id="project-resource-projection",
        workflow_definition_id="reproduction-experiment-local-experimental",
        output_schema_id="experiment-record/v2",
        lifecycle="ACTIVE",
        research_status="NOT_STARTED",
        latest_summary=None,
        continuation_reason=None,
        installation_state="ACKNOWLEDGED_CURRENT",
        readiness=bound[0],
        next_action=bound[1],
        missing=(),
        latest_artifact=None,
    )
    assert bound_action.stage.code == "RESOURCE_STAGING"
    assert bound_action.blocker is not None
    assert bound_action.blocker.code == "LOCAL_RESOURCE_READINESS_REQUIRED"
    assert bound_action.next_action.code == "STAGE_RESOURCE"
    assert bound_action.next_action.code != "RUN"

    no_resources = _readiness(
        missing_resources=(),
        required_resource_count=0,
        **{key: value for key, value in common.items() if key != "required_resource_count"},
    )
    assert no_resources == ("NEEDS_MATERIALIZATION", "MATERIALIZE")
