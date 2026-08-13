from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.progress_reports.contracts import ProgressReportUploadEnvelope
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.tests.test_b7_multi_workflow import (
    _Transport,
    _finalize_progress,
    _literature_outputs,
    _post_production_literature_progress,
)
from backend.project_workspaces.tests.test_f1b_full_scaffold_flow import (
    _add,
    _bind,
    _materialize_finalize,
)
from backend.workflow_packages import scaffold_runtime
from backend.workflow_packages.production_workflows import (
    EXPERIMENT_WORKFLOW_ID,
    IDEA_DISCOVERY_WORKFLOW_ID,
    LITERATURE_SEARCH_WORKFLOW_ID,
    REVIEW_WORKFLOW_ID,
    WRITING_WORKFLOW_ID,
)
from backend.workflow_packages.serialization import canonical_json


class _ProductTransport(_Transport):
    def list_resources(self, project_id, *, offset=0, limit=100):
        response = self.client.get(
            f"/projects/{project_id}/resources",
            params={"offset": offset, "limit": limit},
        )
        assert response.status_code == 200, response.text
        return response.json()

    def list_resource_bindings(self, project_id, workflow_instance_id):
        response = self.client.get(
            f"/projects/{project_id}/workflow-instances/"
            f"{workflow_instance_id}/resource-bindings"
        )
        assert response.status_code == 200, response.text
        return response.json()


def _root_by_instance(workspace: Path) -> tuple[dict, dict[str, Path]]:
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    return lock, {
        item["workflow_instance_id"]: workspace / item["relative_path"]
        for item in lock["installed_capsules"]
    }


def _artifact(client: TestClient, project_id: str, artifact_type: str) -> dict:
    response = client.get(
        f"/projects/{project_id}/artifacts", params={"artifact_type": artifact_type}
    )
    assert response.status_code == 200, response.text
    values = response.json()["artifacts"]
    assert len(values) == 1
    return values[0]


def _publish_selected_idea(
    client: TestClient,
    project_id: str,
    instance: dict,
    root: Path,
    source_artifact: dict,
) -> dict:
    workspace_cli._prepare_idea_output_provenance(
        capsule=root,
        artifact_id=source_artifact["artifact_id"],
        checksum=source_artifact["content_checksum"],
    )
    candidates = json.loads((root / "outputs/candidate_ideas.json").read_text())
    library = json.loads((root / "inputs/selected-paper-library.json").read_text())
    candidates["ideas"] = [{
        "idea_id": "idea-001",
        "title": "Explicit product-width qualification direction",
        "research_question": "How can exact cross-workflow continuity be qualified?",
        "motivation": "The supplied bounded records expose a continuity concern.",
        "literature_basis": [library["papers"][0]["candidate_id"]],
        "observed_gap": "The bounded set leaves continuity validation unresolved.",
        "proposed_direction": "Qualify explicit immutable handoffs.",
        "assumptions": ["The synthetic selected set is relevant to this qualification."],
        "risks": ["The bounded set cannot establish global novelty."],
        "validation_needed": ["Broader real-world validation remains necessary."],
        "status": "selected",
    }]
    (root / "outputs/candidate_ideas.json").write_text(
        canonical_json(candidates) + "\n", encoding="utf-8"
    )
    (root / "outputs/idea_discovery_report.md").write_text(
        "# Idea Discovery report\n\n"
        "## Literature landscape\nBounded synthetic evidence.\n"
        "## Observed patterns\nExplicit handoffs recur.\n"
        "## Gaps\nContinuity validation remains bounded.\n"
        "## Candidate research directions\nOne qualification direction.\n"
        "## User choices\nThe user explicitly selected idea-001.\n"
        "## Uncertainties\nGlobal novelty is not proven.\n"
        "## Next validation needs\nBroader validation.\n",
        encoding="utf-8",
    )
    report_path = _finalize_progress(root, state="COMPLETED")
    manifest = json.loads((root / "package-manifest.json").read_text())
    report = json.loads(report_path.read_text())
    output = next(
        item for item in report["output_artifacts"]
        if item["artifact_kind"] == "selected-research-idea/v1"
    )
    artifact_id = "artifact-" + uuid.uuid5(
        uuid.UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966"),
        "production-artifact/v1|package=" + manifest["package_id"]
        + "|report=" + report["report_id"]
        + "|path=" + output["relative_path"]
        + "|checksum=" + output["checksum"],
    ).hex
    envelope = ProgressReportUploadEnvelope.create(
        original_report_bytes=report_path.read_bytes(),
        project_id=project_id,
        package_id=manifest["package_id"],
        package_checksum=manifest["package_checksum"],
        report_schema_version=report["schema_version"],
        report_id=report["report_id"],
        report_checksum=report["report_checksum"],
        original_report_media_type="application/json",
        uploaded_at=report["completed_at"],
        uploader_type="f1f-qualification",
        client_version="f1f-qualification/0.1.0",
        source_path_hint=report_path.relative_to(root).as_posix(),
        context_snapshot_metadata=None,
    ).to_dict()
    envelope["workflow_instance_id"] = instance["workflow_instance_id"]
    envelope["artifact_declarations"] = [{
        "artifact_id": artifact_id,
        "artifact_type": "selected-research-idea/v1",
        "artifact_schema_version": "selected-research-idea/v1",
        "media_type": "application/json",
        "relative_path": output["relative_path"],
        "content_checksum": output["checksum"],
        "size_bytes": output["size"],
        "produced_at": report["completed_at"],
    }]
    response = client.post(f"/projects/{project_id}/progress-reports", json=envelope)
    assert response.status_code == 201, response.text
    return _artifact(client, project_id, "selected-research-idea/v1")


def _resource_payload(
    checksum: str, *, provider: str, locator: str, revision: str,
    kind: str = "DATASET",
) -> dict:
    return {
        "resource_kind": kind,
        "provider": provider,
        "locator": locator,
        "exact_revision": revision,
        "expected_content_checksum": checksum,
        "display_name": f"F1F {provider} qualification reference",
        "metadata": {"purpose": "complete-product-width qualification"},
    }


def test_complete_product_width_e2e_uses_only_product_paths(tmp_path: Path) -> None:
    database = InMemoryDatabase()
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        local_package_root=str(tmp_path / "cloud-packages"),
    )))
    qualify_complete_product_width(client, tmp_path)


def qualify_complete_product_width(client: TestClient, tmp_path: Path) -> dict:
    """Qualify F1F without direct persistence writes or synthetic local receipts."""
    created = client.post("/projects", json={
        "name": "F1F complete product-width qualification",
        "research_topic": "Synthetic immutable research-flow continuity",
        "selected_workflow": "LITERATURE_SEARCH",
        "workflow_setup": "full-research",
    })
    assert created.status_code == 201, created.text
    project_id = created.json()["project_id"]
    instance_page = client.get(f"/projects/{project_id}/workflow-instances").json()
    assert instance_page["manifest_revision"] == 1
    assert instance_page["total"] == 5
    instances = {item["workflow_definition_id"]: item for item in instance_page["items"]}
    assert set(instances) == {
        LITERATURE_SEARCH_WORKFLOW_ID, IDEA_DISCOVERY_WORKFLOW_ID,
        WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID, EXPERIMENT_WORKFLOW_ID,
    }
    assert {
        key: (value["workflow_version"], value["capsule_version"])
        for key, value in instances.items()
    } == {
        LITERATURE_SEARCH_WORKFLOW_ID: ("0.4.0", "0.6.0"),
        IDEA_DISCOVERY_WORKFLOW_ID: ("0.2.0", "0.3.0"),
        WRITING_WORKFLOW_ID: ("0.2.0", "0.4.0"),
        REVIEW_WORKFLOW_ID: ("0.2.0", "0.4.0"),
        EXPERIMENT_WORKFLOW_ID: ("0.3.0", "0.5.0"),
    }

    workspace = tmp_path / "workspace"
    descriptor = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=descriptor)
    transport = _ProductTransport(client)
    now = datetime(2026, 8, 9, tzinfo=UTC)
    first_sync = workspace_cli.sync_workspace(
        workspace_root=workspace, transport=transport, now=now
    )
    second_sync = workspace_cli.sync_workspace(
        workspace_root=workspace, transport=transport, now=now + timedelta(seconds=1)
    )
    assert first_sync.status == "SYNCED"
    assert second_sync.status == "NO_CHANGE"
    lock, roots = _root_by_instance(workspace)
    assert len(lock["installed_capsules"]) == 5

    for workflow_id in (WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID, EXPERIMENT_WORKFLOW_ID):
        root = roots[instances[workflow_id]["workflow_instance_id"]]
        manifest = json.loads((root / "package-manifest.json").read_text())
        skills = [
            item for item in manifest["files"]
            if item["relative_path"].startswith("workflow/skills/")
        ]
        assert any(item["relative_path"].endswith("/SKILL.md") for item in skills)
        assert any("research-artifact-provenance" in item["relative_path"] for item in skills)
        assert any("scaffold-core-safety" in item["relative_path"] for item in skills)

    # Literature: deterministic fixture bytes, real finalization, API promotion.
    literature = instances[LITERATURE_SEARCH_WORKFLOW_ID]
    literature_root = roots[literature["workflow_instance_id"]]
    _literature_outputs(literature_root)
    literature_report = _finalize_progress(literature_root, state="COMPLETED")
    _post_production_literature_progress(
        client, literature_root, literature["workflow_instance_id"], literature_report
    )
    library = _artifact(client, project_id, "selected-paper-library/v1")

    # Idea: exact binding and materialization, then explicit selection and promotion.
    idea = instances[IDEA_DISCOVERY_WORKFLOW_ID]
    _bind(client, project_id, idea, "paper_library", library, 1)
    workspace_cli.refresh_artifact_index(
        workspace_root=workspace, transport=transport, now=now + timedelta(minutes=1)
    )
    workspace_cli.materialize_artifacts(
        workspace_root=workspace,
        consumer_workflow_instance_id=idea["workflow_instance_id"],
        transport=transport,
        now=now + timedelta(minutes=2),
    )
    idea_root = roots[idea["workflow_instance_id"]]
    selected_idea = _publish_selected_idea(
        client, project_id, idea, idea_root, library
    )

    # Resource shell: real metadata/binding APIs and deterministic local resolution.
    fixture = tmp_path / "resource-fixtures" / "demo"
    fixture.mkdir(parents=True)
    (fixture / "data.txt").write_text("deterministic F1F resource bytes\n", encoding="utf-8")
    (fixture / ".reagent-resource.json").write_text(canonical_json({
        "schema_version": "reagent.local-test-resource/v0.1",
        "locator": "fixture/demo",
        "exact_revision": "fixture-revision-f1f-0001",
    }), encoding="utf-8")
    resource_checksum, _ = workspace_cli._resource_manifest(fixture)
    local_resource_response = client.post(
        f"/projects/{project_id}/resources",
        json=_resource_payload(
            resource_checksum, provider="LOCAL_TEST", locator="fixture/demo",
            revision="fixture-revision-f1f-0001",
        ),
    )
    assert local_resource_response.status_code == 201, local_resource_response.text
    local_resource = local_resource_response.json()
    experiment = instances[EXPERIMENT_WORKFLOW_ID]
    resource_binding = client.post(
        f"/projects/{project_id}/workflow-instances/"
        f"{experiment['workflow_instance_id']}/resource-bindings",
        json={
            "requirement_key": "dataset",
            "resource_id": local_resource["resource_id"],
            "idempotency_key": "00000000-0000-4000-8000-000000000051",
        },
    )
    assert resource_binding.status_code == 201, resource_binding.text
    resolved = workspace_cli.resolve_resources(
        workspace_root=workspace,
        workflow_instance_id=experiment["workflow_instance_id"],
        transport=transport,
        local_test_fixture_root=tmp_path / "resource-fixtures",
        allow_local_test=True,
        now=now + timedelta(minutes=3),
    )
    assert resolved["status"] == "RESOLVED_VERIFIED"

    for provider, locator, revision, kind in (
        ("GITHUB", "owner/repository", "a" * 40, "SOURCE_REPOSITORY"),
        ("HUGGING_FACE", "owner/dataset", "b" * 40, "DATASET"),
    ):
        response = client.post(
            f"/projects/{project_id}/resources",
            json=_resource_payload(
                "sha256:" + "c" * 64, provider=provider, locator=locator,
                revision=revision, kind=kind,
            ),
        )
        assert response.status_code == 201, response.text

    # Experiment: bound Resource must verify; Artifact inputs remain explicit.
    _bind(client, project_id, experiment, "research_idea", selected_idea, 2)
    _bind(client, project_id, experiment, "literature_library", library, 3)
    resource_projection = workspace_cli._verify_bound_resources(
        workspace=workspace,
        descriptor=json.loads((workspace / workspace_cli.WORKSPACE_DESCRIPTOR).read_text()),
        workflow_instance_id=experiment["workflow_instance_id"],
        transport=transport,
    )
    projected = {
        item["requirement_key"]: item
        for item in resource_projection["requirements"]
    }
    assert projected["dataset"]["configured"] is True
    assert projected["dataset"]["resolution_status"] == "RESOLVED_VERIFIED"
    assert all(
        projected[key]["resolution_status"] == "UNCONFIGURED"
        for key in ("source_repository", "model", "checkpoint")
    )
    experiment_record = _materialize_finalize(
        client, transport, workspace, roots[experiment["workflow_instance_id"]],
        experiment, now + timedelta(minutes=4),
    )
    experiment_value = json.loads(
        (roots[experiment["workflow_instance_id"]] / experiment_record["relative_path"]).read_text()
    )
    assert experiment_value["execution_status"] == "PLACEHOLDER_NOT_EXECUTED"
    assert experiment_value["actual_results"] is None

    # Writing A includes the optional Experiment result by exact Artifact identity.
    writing_a = instances[WRITING_WORKFLOW_ID]
    for number, (key, value) in enumerate((
        ("research_idea", selected_idea),
        ("literature_library", library),
        ("experiment_record", experiment_record),
    ), start=4):
        _bind(client, project_id, writing_a, key, value, number)
    draft_a = _materialize_finalize(
        client, transport, workspace, roots[writing_a["workflow_instance_id"]],
        writing_a, now + timedelta(minutes=5),
    )
    draft_a_path = roots[writing_a["workflow_instance_id"]] / draft_a["relative_path"]
    draft_a_bytes = draft_a_path.read_bytes()
    assert b"SCAFFOLD PLACEHOLDER" in draft_a_bytes
    draft_a_value = json.loads(draft_a_bytes)
    assert (
        draft_a_value["source_artifacts"]["experiment_record"]["artifact_id"]
        == experiment_record["artifact_id"]
    )

    review = instances[REVIEW_WORKFLOW_ID]
    _bind(client, project_id, review, "manuscript", draft_a, 7)
    review_report = _materialize_finalize(
        client, transport, workspace, roots[review["workflow_instance_id"]],
        review, now + timedelta(minutes=6),
    )
    review_value = json.loads(
        (roots[review["workflow_instance_id"]] / review_report["relative_path"]).read_text()
    )
    assert review_value["recommendation"] == "INSUFFICIENT_EVIDENCE"

    # The reviewed product model preserves Draft A by creating Writing #2.
    writing_b = _add(client, project_id, WRITING_WORKFLOW_ID, revision=1)
    third_sync = workspace_cli.sync_workspace(
        workspace_root=workspace, transport=transport, now=now + timedelta(minutes=7)
    )
    assert third_sync.status == "SYNCED"
    _, roots = _root_by_instance(workspace)
    for number, (key, value) in enumerate((
        ("research_idea", selected_idea),
        ("literature_library", library),
        ("experiment_record", experiment_record),
        ("prior_manuscript", draft_a),
        ("review_feedback", review_report),
    ), start=8):
        _bind(client, project_id, writing_b, key, value, number)
    draft_b = _materialize_finalize(
        client, transport, workspace, roots[writing_b["workflow_instance_id"]],
        writing_b, now + timedelta(minutes=8),
    )
    draft_b_value = json.loads(
        (roots[writing_b["workflow_instance_id"]] / draft_b["relative_path"]).read_text()
    )
    assert (
        draft_b_value["source_artifacts"]["prior_manuscript"]["artifact_id"]
        == draft_a["artifact_id"]
    )
    assert (
        draft_b_value["source_artifacts"]["review_feedback"]["artifact_id"]
        == review_report["artifact_id"]
    )
    assert draft_a_path.read_bytes() == draft_a_bytes

    manuscripts = client.get(
        f"/projects/{project_id}/artifacts",
        params={"artifact_type": "manuscript-draft/v1"},
    ).json()["artifacts"]
    assert {item["artifact_id"] for item in manuscripts} == {
        draft_a["artifact_id"], draft_b["artifact_id"]
    }
    progress = client.get(f"/projects/{project_id}/progress").json()
    assert len(progress["instances"]) == 6
    labels = {item["friendly_instance_label"] for item in progress["instances"]}
    assert {"Writing #1", "Writing #2"}.issubset(labels)
    assert progress["total_progress_report_count"] == 6

    # Three independent fail-closed drills, restored without editing internal JSON.
    writing_b_root = roots[writing_b["workflow_instance_id"]]
    skill_path = next(writing_b_root.glob("workflow/skills/*/SKILL.md"))
    skill_bytes = skill_path.read_bytes()
    skill_path.write_bytes(skill_bytes + b"\ntamper\n")
    with pytest.raises(workspace_cli.WorkspaceCLIError) as skill_drift:
        workspace_cli.workflow_list(workspace)
    assert skill_drift.value.code == "LOCAL_CAPSULE_DRIFT"
    skill_path.write_bytes(skill_bytes)
    assert scaffold_runtime.preflight(writing_b_root)["ready"]

    local_resource_path = workspace / "resources" / local_resource["resource_id"] / "data.txt"
    resource_bytes = local_resource_path.read_bytes()
    local_resource_path.write_bytes(b"drift\n")
    with pytest.raises(workspace_cli.WorkspaceCLIError) as resource_drift:
        workspace_cli._verify_bound_resources(
            workspace=workspace,
            descriptor=json.loads((workspace / workspace_cli.WORKSPACE_DESCRIPTOR).read_text()),
            workflow_instance_id=experiment["workflow_instance_id"],
            transport=transport,
        )
    assert resource_drift.value.code == "RESOURCE_DRIFT"
    local_resource_path.write_bytes(resource_bytes)
    workspace_cli._verify_bound_resources(
        workspace=workspace,
        descriptor=json.loads((workspace / workspace_cli.WORKSPACE_DESCRIPTOR).read_text()),
        workflow_instance_id=experiment["workflow_instance_id"],
        transport=transport,
    )

    prior_input = writing_b_root / "inputs/prior-manuscript.json"
    prior_bytes = prior_input.read_bytes()
    prior_input.write_bytes(prior_bytes + b"\n")
    with pytest.raises(
        scaffold_runtime.ScaffoldRuntimeError,
        match="materialized input checksum drift",
    ):
        scaffold_runtime.preflight(writing_b_root)
    prior_input.write_bytes(prior_bytes)
    assert scaffold_runtime.preflight(writing_b_root)["ready"]

    # Fresh invocations reconstruct continuity from immutable local files.
    assert (idea_root / "memory/context.md").is_file()
    assert (writing_b_root / "memory/context.md").is_file()
    listing = workspace_cli.workflow_list(workspace)
    assert len(listing["workflows"]) == 6
    assert {item["instance_label"] for item in listing["workflows"]}.issuperset(
        {"Writing #1", "Writing #2"}
    )
    return {
        "project_id": project_id,
        "workspace": workspace,
        "artifact_ids": {
            "literature": library["artifact_id"],
            "idea": selected_idea["artifact_id"],
            "experiment": experiment_record["artifact_id"],
            "draft_a": draft_a["artifact_id"],
            "review": review_report["artifact_id"],
            "draft_b": draft_b["artifact_id"],
        },
    }
