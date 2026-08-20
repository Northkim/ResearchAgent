from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import workspace_cli

EXPERIMENT_WORKFLOW_ID = "reproduction-experiment-local-experimental"


def _add_resource_shell_experiment(client: TestClient, project_id: str) -> dict:
    detail = client.get(f"/workflow-definitions/{EXPERIMENT_WORKFLOW_ID}").json()
    capsule = next(
        item for item in detail["capsules"]
        if item["workflow_version"] == "0.3.0"
        and item["capsule_version"] == "0.5.0"
    )
    response = client.post(f"/projects/{project_id}/workflow-instances", json={
        "workflow_definition_id": EXPERIMENT_WORKFLOW_ID,
        "workflow_version": "0.3.0",
        "capsule_id": capsule["capsule_id"],
        "capsule_version": "0.5.0",
        "base_revision": 1,
    })
    assert response.status_code == 201, response.text
    return response.json()


def _client(tmp_path: Path):
    database = InMemoryDatabase()
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        local_package_root=str(tmp_path / "packages"),
    )))
    response = client.post("/projects", json={
        "name": "F1E synthetic project",
        "research_topic": "Synthetic external resource shell",
        "selected_workflow": "LITERATURE_SEARCH",
    })
    assert response.status_code == 201
    project_id = response.json()["project_id"]
    experiment = _add_resource_shell_experiment(client, project_id)
    return client, project_id, experiment


def _resource_payload(checksum: str, *, provider="LOCAL_TEST", locator="fixture/demo", revision="fixture-revision-0001"):
    return {
        "resource_kind": "DATASET",
        "provider": provider,
        "locator": locator,
        "exact_revision": revision,
        "expected_content_checksum": checksum,
        "display_name": "Synthetic fixture dataset",
        "metadata": {"purpose": "qualification"},
    }


def test_resource_api_is_project_scoped_exact_and_idempotent(tmp_path: Path) -> None:
    client, project_id, experiment = _client(tmp_path)
    checksum = "sha256:" + "a" * 64
    created = client.post(
        f"/projects/{project_id}/resources", json=_resource_payload(checksum)
    )
    assert created.status_code == 201
    replay = client.post(
        f"/projects/{project_id}/resources", json=_resource_payload(checksum)
    )
    assert replay.status_code == 201
    assert replay.json()["resource_id"] == created.json()["resource_id"]
    assert client.post(f"/projects/{project_id}/resources", json=_resource_payload(
        checksum, provider="GITHUB", locator="https://github.com/owner/repo", revision="main"
    )).status_code == 422
    detail = client.get(
        "/workflow-definitions/reproduction-experiment-local-experimental"
    ).json()
    assert detail["recommended_version"]["version"] == "0.8.0"
    historical = next(item for item in detail["versions"] if item["version"] == "0.3.0")
    requirements = historical["resource_requirements"]
    assert {item["requirement_key"] for item in requirements} == {
        "source_repository", "dataset", "model", "checkpoint"
    }
    assert all(item["required"] is False for item in requirements)
    bound = client.post(
        f"/projects/{project_id}/workflow-instances/"
        f"{experiment['workflow_instance_id']}/resource-bindings",
        json={
            "requirement_key": "dataset",
            "resource_id": created.json()["resource_id"],
            "idempotency_key": str(uuid4()),
        },
    )
    assert bound.status_code == 201
    assert bound.json()["resource"]["provider"] == "LOCAL_TEST"
    assert client.get(
        f"/projects/{project_id}/workflow-instances/"
        f"{experiment['workflow_instance_id']}/resource-bindings"
    ).json()["total"] == 1


def test_resource_binding_rejects_wrong_kind_provider_and_project(tmp_path: Path) -> None:
    client, project_id, experiment = _client(tmp_path)
    checksum = "sha256:" + "2" * 64
    repository = client.post(
        f"/projects/{project_id}/resources",
        json={
            **_resource_payload(checksum),
            "resource_kind": "SOURCE_REPOSITORY",
        },
    ).json()
    wrong_kind = client.post(
        f"/projects/{project_id}/workflow-instances/"
        f"{experiment['workflow_instance_id']}/resource-bindings",
        json={
            "requirement_key": "dataset",
            "resource_id": repository["resource_id"],
            "idempotency_key": str(uuid4()),
        },
    )
    assert wrong_kind.status_code == 422
    assert wrong_kind.json()["error"]["code"] == "RESOURCE_KIND_MISMATCH"

    github_dataset = client.post(
        f"/projects/{project_id}/resources",
        json={
            **_resource_payload(
                checksum,
                provider="GITHUB",
                locator="owner/dataset-repository",
                revision="3" * 40,
            ),
            "resource_kind": "DATASET",
        },
    ).json()
    wrong_provider = client.post(
        f"/projects/{project_id}/workflow-instances/"
        f"{experiment['workflow_instance_id']}/resource-bindings",
        json={
            "requirement_key": "dataset",
            "resource_id": github_dataset["resource_id"],
            "idempotency_key": str(uuid4()),
        },
    )
    assert wrong_provider.status_code == 422
    assert wrong_provider.json()["error"]["code"] == "RESOURCE_PROVIDER_MISMATCH"

    second = client.post("/projects", json={
        "name": "F1E second synthetic project",
        "research_topic": "Cross-project Resource denial",
        "selected_workflow": "LITERATURE_SEARCH",
    }).json()
    second_experiment = _add_resource_shell_experiment(client, second["project_id"])
    cross_project = client.post(
        f"/projects/{second['project_id']}/workflow-instances/"
        f"{second_experiment['workflow_instance_id']}/resource-bindings",
        json={
            "requirement_key": "source_repository",
            "resource_id": repository["resource_id"],
            "idempotency_key": str(uuid4()),
        },
    )
    assert cross_project.status_code == 403
    assert cross_project.json()["error"]["code"] == "PROJECT_SCOPE_MISMATCH"


def test_resource_list_is_stably_paginated_at_qualification_scale(tmp_path: Path) -> None:
    client, project_id, _ = _client(tmp_path)
    experiment_catalog = client.get(
        "/workflow-definitions/reproduction-experiment-local-experimental"
    ).json()
    for base_revision in range(2, 17):
        added = client.post(
            f"/projects/{project_id}/workflow-instances",
            json={
                "workflow_definition_id": (
                    "reproduction-experiment-local-experimental"
                ),
                "workflow_version": experiment_catalog["recommended_version"]["version"],
                "capsule_id": experiment_catalog["recommended_capsule"]["capsule_id"],
                "capsule_version": experiment_catalog["recommended_capsule"]["capsule_version"],
                "base_revision": base_revision,
            },
        )
        assert added.status_code == 201
    instances = client.get(f"/projects/{project_id}/workflow-instances").json()
    assert instances["total"] == 17
    for index in range(100):
        created = client.post(
            f"/projects/{project_id}/resources",
            json=_resource_payload(
                "sha256:" + f"{index:064x}",
                locator=f"fixture/scale-{index:03d}",
                revision=f"fixture-revision-{index:04d}",
            ),
        )
        assert created.status_code == 201
    first = client.get(
        f"/projects/{project_id}/resources?offset=0&limit=37"
    ).json()
    second = client.get(
        f"/projects/{project_id}/resources?offset=37&limit=63"
    ).json()
    identifiers = [item["resource_id"] for item in first["items"] + second["items"]]
    replay = client.get(
        f"/projects/{project_id}/resources?offset=0&limit=100"
    ).json()
    assert first["total"] == second["total"] == 100
    assert identifiers == [item["resource_id"] for item in replay["items"]]
    assert len(set(identifiers)) == 100
    assert client.get(f"/projects/{project_id}/progress").status_code == 200


class _Transport:
    def __init__(self, resource, binding):
        self.resource = resource
        self.binding = binding

    def list_resources(self, project_id, *, offset=0, limit=100):
        return {"items": [self.resource], "total": 1, "offset": offset, "limit": limit}

    def list_resource_bindings(self, project_id, workflow_instance_id):
        return {"items": [self.binding], "total": 1}


def test_local_test_resolver_is_gated_atomic_and_detects_drift(tmp_path: Path) -> None:
    client, project_id, experiment = _client(tmp_path)
    descriptor = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
    workspace = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=descriptor)
    fixture = tmp_path / "fixtures" / "demo"
    fixture.mkdir(parents=True)
    (fixture / "data.txt").write_text("deterministic synthetic bytes\n", encoding="utf-8")
    (fixture / ".reagent-resource.json").write_text(json.dumps({
        "schema_version": "reagent.local-test-resource/v0.1",
        "locator": "fixture/demo",
        "exact_revision": "fixture-revision-0001",
    }), encoding="utf-8")
    checksum, _ = workspace_cli._resource_manifest(fixture)
    resource_response = client.post(
        f"/projects/{project_id}/resources", json=_resource_payload(checksum)
    )
    assert resource_response.status_code == 201
    resource = resource_response.json()
    binding_response = client.post(
        f"/projects/{project_id}/workflow-instances/"
        f"{experiment['workflow_instance_id']}/resource-bindings",
        json={
            "requirement_key": "dataset",
            "resource_id": resource["resource_id"],
            "idempotency_key": str(uuid4()),
        },
    )
    binding = binding_response.json()
    transport = _Transport(resource, binding)
    workspace_path, workspace_descriptor, _ = workspace_cli.load_workspace(workspace)
    with pytest.raises(workspace_cli.WorkspaceCLIError) as unresolved:
        workspace_cli._verify_bound_resources(
            workspace=workspace_path,
            descriptor=workspace_descriptor,
            workflow_instance_id=experiment["workflow_instance_id"],
            transport=transport,
        )
    assert unresolved.value.code == "RESOURCE_UNRESOLVED"
    with pytest.raises(workspace_cli.WorkspaceCLIError) as gated:
        workspace_cli.resolve_resources(
            workspace_root=workspace,
            workflow_instance_id=experiment["workflow_instance_id"],
            transport=transport,
            local_test_fixture_root=tmp_path / "fixtures",
            allow_local_test=False,
        )
    assert gated.value.code == "RESOURCE_RESOLVER_NOT_IMPLEMENTED"
    result = workspace_cli.resolve_resources(
        workspace_root=workspace,
        workflow_instance_id=experiment["workflow_instance_id"],
        transport=transport,
        local_test_fixture_root=tmp_path / "fixtures",
        allow_local_test=True,
        now=datetime(2026, 8, 9, tzinfo=UTC),
    )
    assert result["status"] == "RESOLVED_VERIFIED"
    workspace_cli._verify_bound_resources(
        workspace=workspace_path,
        descriptor=workspace_descriptor,
        workflow_instance_id=experiment["workflow_instance_id"],
        transport=transport,
    )
    assert workspace_cli.resource_status(workspace)["drift_count"] == 0
    # A crash after atomic byte publication but before index publication is
    # recovered by re-verifying the already-published immutable target.
    (workspace / ".reagent/resource-index.json").unlink()
    replay = workspace_cli.resolve_resources(
        workspace_root=workspace,
        workflow_instance_id=experiment["workflow_instance_id"],
        transport=transport,
        local_test_fixture_root=tmp_path / "fixtures",
        allow_local_test=True,
        now=datetime(2026, 8, 9, 0, 1, tzinfo=UTC),
    )
    assert replay["status"] == "RESOLVED_VERIFIED"
    assert workspace_cli.resource_status(workspace)["verified_count"] == 1
    local = workspace / "resources" / resource["resource_id"] / "data.txt"
    local.write_text("drift\n", encoding="utf-8")
    assert workspace_cli.resource_status(workspace)["status"] == "DRIFTED"
    with pytest.raises(workspace_cli.WorkspaceCLIError) as drifted:
        workspace_cli._verify_bound_resources(
            workspace=workspace_path,
            descriptor=workspace_descriptor,
            workflow_instance_id=experiment["workflow_instance_id"],
            transport=transport,
        )
    assert drifted.value.code == "RESOURCE_DRIFT"


def test_resource_manifest_rejects_links_special_files_and_case_collisions(
    tmp_path: Path,
) -> None:
    root = tmp_path / "unsafe"
    root.mkdir()
    regular = root / "data.txt"
    regular.write_text("safe\n", encoding="utf-8")
    (root / "link.txt").symlink_to(regular)
    with pytest.raises(workspace_cli.WorkspaceCLIError) as linked:
        workspace_cli._resource_manifest(root)
    assert linked.value.code == "RESOURCE_UNSAFE_FILE"
    (root / "link.txt").unlink()

    os.link(regular, root / "hardlink.txt")
    with pytest.raises(workspace_cli.WorkspaceCLIError) as hardlinked:
        workspace_cli._resource_manifest(root)
    assert hardlinked.value.code == "RESOURCE_UNSAFE_FILE"
    (root / "hardlink.txt").unlink()

    fifo = root / "pipe"
    os.mkfifo(fifo)
    with pytest.raises(workspace_cli.WorkspaceCLIError) as special:
        workspace_cli._resource_manifest(root)
    assert special.value.code == "RESOURCE_UNSAFE_FILE"
    fifo.unlink()

    portable_paths: dict[str, str] = {}
    workspace_cli._record_case_path(portable_paths, "folder/data.txt")
    with pytest.raises(workspace_cli.WorkspaceCLIError) as collision:
        workspace_cli._record_case_path(portable_paths, "Folder/DATA.txt")
    assert collision.value.code == "UNSAFE_PACKAGE_PATH"


@pytest.mark.parametrize("provider", ("GITHUB", "HUGGING_FACE"))
def test_external_resolvers_fail_without_network(
    provider: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, project_id, experiment = _client(tmp_path)
    descriptor = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
    workspace = tmp_path / provider.lower()
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=descriptor)
    kind = "SOURCE_REPOSITORY" if provider == "GITHUB" else "DATASET"
    key = "source_repository" if provider == "GITHUB" else "dataset"
    resource = {
        **_resource_payload(
            "sha256:" + "b" * 64,
            provider=provider,
            locator="owner/repository",
            revision="c" * 40,
        ),
        "resource_id": "resource-" + "d" * 32,
        "project_id": project_id,
        "resource_kind": kind,
        "lifecycle": "ACTIVE",
        "created_at": "2026-08-09T00:00:00+00:00",
    }
    binding = {
        "binding_id": "resource-binding-" + "e" * 32,
        "project_id": project_id,
        "workflow_instance_id": experiment["workflow_instance_id"],
        "workflow_definition_id": experiment["workflow_definition_id"],
        "workflow_version": "0.3.0",
        "requirement_key": key,
        "resource_id": resource["resource_id"],
        "expected_content_checksum": resource["expected_content_checksum"],
        "state": "ACTIVE",
        "resource": resource,
    }
    network_calls = 0

    def fail_network(*_args, **_kwargs):
        nonlocal network_calls
        network_calls += 1
        raise AssertionError("external Resource resolver attempted network access")

    monkeypatch.setattr("urllib.request.urlopen", fail_network)
    with pytest.raises(workspace_cli.WorkspaceCLIError) as stopped:
        workspace_cli.resolve_resources(
            workspace_root=workspace,
            workflow_instance_id=experiment["workflow_instance_id"],
            transport=_Transport(resource, binding),
        )
    assert stopped.value.code == "RESOURCE_RESOLVER_NOT_IMPLEMENTED"
    assert network_calls == 0
