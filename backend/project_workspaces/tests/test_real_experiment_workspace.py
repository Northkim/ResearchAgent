from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.artifact_references.tests.test_research_flow_contracts import _selected
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.tests.e1_q1_public_workspace_qualification import (
    _qualification_app,
)
from backend.project_workspaces.tests.test_f1b_full_scaffold_flow import _seed_upstream
from backend.project_workspaces.tests.test_sync import _ClientTransport


class _Transport(_ClientTransport):
    def list_artifacts(self, project_id, *, offset=0, limit=100):
        response = self.client.get(
            f"/projects/{project_id}/artifacts",
            params={"offset": offset, "limit": limit},
        )
        assert response.status_code == 200, response.text
        return response.json()

    def materialization_plan(self, project_id, consumer_workflow_instance_id):
        response = self.client.get(
            f"/projects/{project_id}/workflow-instances/"
            f"{consumer_workflow_instance_id}/artifact-materialization-plan"
        )
        assert response.status_code == 200, response.text
        return response.json()

    def list_resource_bindings(self, project_id, workflow_instance_id):
        response = self.client.get(
            f"/projects/{project_id}/workflow-instances/{workflow_instance_id}/resource-bindings"
        )
        assert response.status_code == 200, response.text
        return response.json()


def test_e1_qualification_app_composes_upload_only_local_sessions(
    tmp_path: Path,
) -> None:
    database = InMemoryDatabase()
    app = _qualification_app(root=tmp_path, database=database)
    with TestClient(
        app,
        base_url="http://127.0.0.1",
        client=("127.0.0.1", 50000),
    ) as client:
        project = client.post(
            "/projects",
            json={
                "name": "Controlled upload-only session",
                "research_topic": "Deterministic local projection",
                "selected_workflow": "LITERATURE_SEARCH",
            },
        ).json()
        package = client.post(
            f"/projects/{project['project_id']}/packages"
        ).json()
        session = client.post(
            f"/projects/{project['project_id']}/local-sessions",
            json={
                "package_id": package["package_id"],
                "package_checksum": package["package_checksum"],
                "workflow_id": package["workflow_id"],
                "workflow_version": package["workflow_version"],
                "workflow_checksum": package["workflow_checksum"],
                "mode": "UPLOAD_ONLY",
                "execution_round": 1,
                "report_id": "prv2-" + "a" * 64,
                "report_content_checksum": "sha256:" + "b" * 64,
            },
        )

    assert session.status_code == 201, session.text
    assert session.json()["mode"] == "UPLOAD_ONLY"
    assert session.json()["maximum_provider_calls"] == 0


def _setup(tmp_path: Path):
    database = InMemoryDatabase()
    uow_factory = lambda: InMemoryUnitOfWork(database)
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=uow_factory,
        local_package_root=str(tmp_path / "packages"),
    )))
    project = client.post("/projects", json={
        "name": "Real Experiment controlled Project",
        "research_topic": "Deterministic local computation",
        "selected_workflow": "LITERATURE_SEARCH",
        "workflow_setup": "full-research",
    }).json()
    instances = client.get(f"/projects/{project['project_id']}/workflow-instances").json()["items"]
    experiment = next(
        item for item in instances
        if item["workflow_definition_id"]
        == "reproduction-experiment-local-experimental"
    )
    assert (experiment["workflow_version"], experiment["capsule_version"]) == (
        "0.4.0", "0.7.0"
    )
    descriptor = client.get(f"/projects/{project['project_id']}/workspace-bootstrap").json()
    workspace = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=descriptor)
    transport = _Transport(client)
    workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    return (
        client,
        project["project_id"],
        experiment,
        workspace,
        transport,
        uow_factory,
    )


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "owner-package"
    source.mkdir()
    (source / ".reagent-experiment.json").write_text(json.dumps({
        "schema_version": "reagent.experiment-package/v0.1",
        "entrypoint": "run.py",
        "runtime": "PYTHON",
        "runtime_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "lock_file": "requirements.lock",
    }), encoding="utf-8")
    (source / "requirements.lock").write_text("# owner-staged; no installation\n", encoding="utf-8")
    (source / "run.py").write_text("print('{}')\n", encoding="utf-8")
    return source


def _bind(client: TestClient, project_id: str, experiment: dict, checksum: str):
    resource = client.post(f"/projects/{project_id}/resources", json={
        "resource_kind": "SOURCE_REPOSITORY",
        "provider": "GITHUB",
        "locator": "owner/controlled-experiment",
        "exact_revision": "a" * 40,
        "expected_content_checksum": checksum,
        "display_name": "Owner-staged controlled package",
        "metadata": {"staging": "owner"},
    })
    assert resource.status_code == 201, resource.text
    binding = client.post(
        f"/projects/{project_id}/workflow-instances/{experiment['workflow_instance_id']}/resource-bindings",
        json={"requirement_key": "source_repository", "resource_id": resource.json()["resource_id"], "idempotency_key": str(uuid4())},
    )
    assert binding.status_code == 201, binding.text
    return resource.json()


def test_metadata_only_mismatch_missing_bytes_and_valid_owner_stage(tmp_path: Path) -> None:
    client, project_id, experiment, workspace, transport, _ = _setup(tmp_path)
    source = _source(tmp_path)
    checksum, _ = workspace_cli._resource_manifest(source)
    resource = _bind(client, project_id, experiment, checksum)
    workspace_path, descriptor, _ = workspace_cli.load_workspace(workspace)
    capsule = workspace / next(
        item["relative_path"] for item in workspace_cli._require_installed_lock(workspace_path, descriptor)["installed_capsules"]
        if item["workflow_instance_id"] == experiment["workflow_instance_id"]
    )
    with pytest.raises(workspace_cli.WorkspaceCLIError, match="resource stage"):
        workspace_cli._prepare_real_experiment_resource(
            workspace=workspace_path, descriptor=descriptor, capsule=capsule,
            workflow_instance_id=experiment["workflow_instance_id"], transport=transport,
        )
    (source / "run.py").write_text("print('drift')\n", encoding="utf-8")
    with pytest.raises(workspace_cli.WorkspaceCLIError) as mismatch:
        workspace_cli.stage_experiment_package(
            workspace_root=workspace, workflow_instance_id=experiment["workflow_instance_id"],
            source=source, transport=transport,
        )
    assert mismatch.value.code == "RESOURCE_CHECKSUM_MISMATCH"
    (source / "run.py").write_text("print('{}')\n", encoding="utf-8")
    result = workspace_cli.stage_experiment_package(
        workspace_root=workspace, workflow_instance_id=experiment["workflow_instance_id"],
        source=source, transport=transport,
    )
    assert result["status"] == "OWNER_STAGED_VERIFIED"
    workspace_cli._prepare_real_experiment_resource(
        workspace=workspace_path, descriptor=descriptor, capsule=capsule,
        workflow_instance_id=experiment["workflow_instance_id"], transport=transport,
    )
    provenance = json.loads((capsule / "memory/resource-provenance.json").read_text())
    assert provenance["content_checksum"] == checksum
    assert provenance["resource_id"] == resource["resource_id"]
    assert provenance["package"]["runtime"] == "PYTHON"
    staged = workspace / "resources" / resource["resource_id"]
    (staged / "run.py").unlink()
    assert workspace_cli.resource_status(workspace)["status"] == "DRIFTED"
    with pytest.raises(workspace_cli.WorkspaceCLIError) as missing:
        workspace_cli._prepare_real_experiment_resource(
            workspace=workspace_path, descriptor=descriptor, capsule=capsule,
            workflow_instance_id=experiment["workflow_instance_id"], transport=transport,
        )
    assert missing.value.code == "RESOURCE_DRIFT"


def test_real_experiment_declared_materialized_input_is_the_only_dynamic_input(
    tmp_path: Path,
) -> None:
    client, project_id, experiment, workspace, transport, uow_factory = _setup(
        tmp_path
    )
    instances = client.get(
        f"/projects/{project_id}/workflow-instances"
    ).json()["items"]
    idea = next(
        item
        for item in instances
        if item["workflow_definition_id"] == "idea-discovery-local-experimental"
    )
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    roots = {
        item["workflow_instance_id"]: workspace / item["relative_path"]
        for item in lock["installed_capsules"]
    }
    selected_idea, _ = _selected()
    idea_artifact = _seed_upstream(
        uow_factory=uow_factory,
        project_id=project_id,
        instance=idea,
        root=roots[idea["workflow_instance_id"]],
        artifact_type="selected-research-idea/v1",
        content=selected_idea,
        character="f",
    )
    bound = client.post(
        f"/projects/{project_id}/workflow-instances/"
        f"{experiment['workflow_instance_id']}/artifact-dependencies",
        json={
            "requirement_key": "research_idea",
            "artifact_id": idea_artifact["artifact_id"],
            "idempotency_key": str(uuid4()),
        },
    )
    assert bound.status_code == 201, bound.text
    workspace_cli.refresh_artifact_index(
        workspace_root=workspace, transport=transport
    )
    materialized = workspace_cli.materialize_artifacts(
        workspace_root=workspace,
        consumer_workflow_instance_id=experiment["workflow_instance_id"],
        transport=transport,
    )
    assert materialized.materialized_count == 1

    capsule = roots[experiment["workflow_instance_id"]]
    real_contract = json.loads(
        (capsule / "workflow/real-experiment.json").read_text()
    )
    artifact_contract = json.loads(
        (capsule / "workflow/artifact-inputs.json").read_text()
    )
    expected_target = "inputs/selected-research-idea.json"
    assert real_contract["input_requirements"][0]["target_relative_path"] == (
        expected_target
    )
    assert artifact_contract["requirements"] == real_contract["input_requirements"]
    assert (capsule / expected_target).is_file()

    workspace_path, descriptor, bootstrap = workspace_cli.load_workspace(workspace)
    installed = workspace_cli._require_installed_lock(workspace_path, descriptor)
    workspace_cli._verify_locked_capsules(workspace_path, installed, bootstrap)

    (capsule / "inputs/undeclared-e1-c1.json").write_text(
        "{}\n", encoding="utf-8"
    )
    with pytest.raises(workspace_cli.WorkspaceCLIError) as undeclared:
        workspace_cli._verify_locked_capsules(workspace_path, installed, bootstrap)
    assert undeclared.value.code == "LEGACY_PACKAGE_UNSUPPORTED"
