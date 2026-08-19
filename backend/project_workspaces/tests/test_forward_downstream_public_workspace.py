from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.artifact_references.tests.test_forward_downstream_v5_contracts import _manuscript, _review, _v5
from backend.artifact_references.tests.test_research_flow_contracts import _library, _selected
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.tests.test_f1b_full_scaffold_flow import _seed_upstream
from backend.project_workspaces.tests.test_generic_experiment_v5_workspace import _seed_forward
from backend.project_workspaces.tests.test_owner_real_research_gate import _loopback_server
from backend.project_workspaces.tests.test_real_experiment_workspace import _Transport
from backend.workflow_packages.forward_downstream_publication import (
    INITIAL_WRITING_CAPSULE_ID, REVIEW_CAPSULE_ID,
)
from backend.workflow_packages.revision_optional_support_publication import (
    WRITING_REVISION_CAPSULE_ID,
)


def test_public_workspace_sync_bind_materialize_preflight_and_role_selection(tmp_path: Path) -> None:
    database = InMemoryDatabase(); factory = lambda: InMemoryUnitOfWork(database)
    app = create_app(ApplicationContainer(unit_of_work_factory=factory, local_package_root=str(tmp_path / "packages")))
    client = TestClient(app)
    project = client.post("/projects", json={"name":"EP-D1 disposable","research_topic":"Exact v5 downstream","selected_workflow":"LITERATURE_SEARCH"}).json()
    project_id = project["project_id"]; _seed_forward(database)
    assert client.get("/workflow-definitions/writing-local-experimental").json()["recommended_version"]["version"] == "0.5.0"
    assert client.get("/workflow-definitions/review-local-experimental").json()["recommended_version"]["version"] == "0.4.0"

    revision = 1; created = {}
    for role, workflow_id, version, capsule_id, capsule_version in (
        ("experiment", "reproduction-experiment-local-experimental", "0.8.0", next(key[0] for key in database.workflow_capsule_versions if key[1] == "0.11.0"), "0.11.0"),
        ("writing", "writing-local-experimental", "0.5.0", INITIAL_WRITING_CAPSULE_ID, "0.7.0"),
        ("writing_fixture", "writing-local-experimental", "0.5.0", INITIAL_WRITING_CAPSULE_ID, "0.7.0"),
        ("review", "review-local-experimental", "0.4.0", REVIEW_CAPSULE_ID, "0.6.0"),
        ("review_fixture", "review-local-experimental", "0.4.0", REVIEW_CAPSULE_ID, "0.6.0"),
        ("revision", "writing-local-experimental", "0.7.0", WRITING_REVISION_CAPSULE_ID, "0.9.0"),
    ):
        response = client.post(f"/projects/{project_id}/workflow-instances", json={"workflow_definition_id":workflow_id,"workflow_version":version,"capsule_id":capsule_id,"capsule_version":capsule_version,"base_revision":revision})
        assert response.status_code == 201, response.text
        created[role] = response.json(); revision += 1

    workspace = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=client.get(f"/projects/{project_id}/workspace-bootstrap").json())
    transport = _Transport(client)
    assert workspace_cli.sync_workspace(workspace_root=workspace, transport=transport).status == "SYNCED"
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text()); installed = {item["workflow_instance_id"]:item for item in lock["installed_capsules"]}
    assert [(installed[created[role]["workflow_instance_id"]]["workflow_definition_version"], installed[created[role]["workflow_instance_id"]]["capsule_version"]) for role in ("writing","review","revision")] == [("0.5.0","0.7.0"),("0.4.0","0.6.0"),("0.7.0","0.9.0")]
    producer = next(item for item in lock["installed_capsules"] if item["workflow_definition_id"] == "literature-search-local-experimental")
    idea, _ = _selected(); library = _library(); v5, block = _v5()
    idea_art = _seed_upstream(uow_factory=factory, project_id=project_id, instance=producer, root=workspace/producer["relative_path"], artifact_type="selected-research-idea/v1", content=idea, character="a")
    library_art = _seed_upstream(uow_factory=factory, project_id=project_id, instance=producer, root=workspace/producer["relative_path"], artifact_type="selected-paper-library/v1", content=library, character="b")
    exp_pin = installed[created["experiment"]["workflow_instance_id"]]
    exp_art = _seed_upstream(uow_factory=factory, project_id=project_id, instance=exp_pin, root=workspace/exp_pin["relative_path"], artifact_type="experiment-record/v5", content=v5, character="e")
    exact_sources = {
        "research_idea": {"artifact_id":idea_art["artifact_id"],"artifact_type":"selected-research-idea/v1","sha256":idea_art["content_checksum"]},
        "literature_library": {"artifact_id":library_art["artifact_id"],"artifact_type":"selected-paper-library/v1","sha256":library_art["content_checksum"]},
        "experiment_record": {"artifact_id":exp_art["artifact_id"],"artifact_type":"experiment-record/v5","sha256":exp_art["content_checksum"]},
    }
    manuscript, _ = _manuscript(v5, block, inputs=exact_sources); manuscript = deepcopy(manuscript)
    writing_pin = installed[created["writing_fixture"]["workflow_instance_id"]]
    manuscript_art = _seed_upstream(uow_factory=factory, project_id=project_id, instance=writing_pin, root=workspace/writing_pin["relative_path"], artifact_type="manuscript-draft/v4", content=manuscript, character="c")
    manuscript_exact = {"artifact_id":manuscript_art["artifact_id"],"artifact_type":"manuscript-draft/v4","sha256":manuscript_art["content_checksum"]}
    review_value, _ = _review(manuscript, exact_sources, v5, manuscript_ref=manuscript_exact); review_value = deepcopy(review_value)
    review_pin = installed[created["review_fixture"]["workflow_instance_id"]]
    review_art = _seed_upstream(uow_factory=factory, project_id=project_id, instance=review_pin, root=workspace/review_pin["relative_path"], artifact_type="review-report/v3", content=review_value, character="d")

    bindings = {
        "writing": (("research_idea",idea_art),("literature_library",library_art),("experiment_record",exp_art)),
        "review": (("manuscript",manuscript_art),("research_idea",idea_art),("literature_library",library_art),("experiment_record",exp_art)),
        "revision": (("prior_manuscript",manuscript_art),("causal_review",review_art),("research_idea",idea_art),("literature_library",library_art),("experiment_record",exp_art)),
    }
    for role, items in bindings.items():
        instance_id = created[role]["workflow_instance_id"]
        for key, artifact in items:
            response = client.post(f"/projects/{project_id}/workflow-instances/{instance_id}/artifact-dependencies", json={"requirement_key":key,"artifact_id":artifact["artifact_id"],"idempotency_key":str(uuid4())})
            assert response.status_code == 201, response.text
    workspace_cli.refresh_artifact_index(workspace_root=workspace, transport=transport)
    for role in bindings:
        assert workspace_cli.materialize_artifacts(workspace_root=workspace, consumer_workflow_instance_id=created[role]["workflow_instance_id"], transport=transport).materialized_count == len(bindings[role])

    with _loopback_server(app) as api_url:
        root_cli = workspace / "reagent_local.py"
        for role in bindings:
            result = subprocess.run([sys.executable,str(root_cli),"run",".","--workflow-instance",created[role]["workflow_instance_id"],"--api-url",api_url,"--preflight-only","--json"],cwd=workspace,capture_output=True,text=True,check=False)
            assert result.returncode == 0, result.stderr
            messages = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
            assert messages[0]["status"] == "PREFLIGHT_READY"
            assert messages[-1]["status"] == "PREFLIGHT_READY"
    assert workspace_cli.sync_workspace(workspace_root=workspace, transport=transport).status == "NO_CHANGE"
