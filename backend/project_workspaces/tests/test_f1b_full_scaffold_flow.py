from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.artifact_references.contracts import ArtifactReference, ArtifactState
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.progress_reports.contracts import ProgressReportUploadEnvelope
from backend.project_workspaces import workspace_cli
from backend.workflow_packages import scaffold_runtime
from backend.workflow_packages.production_workflows import (
    EXPERIMENT_WORKFLOW_ID,
    REVIEW_WORKFLOW_ID,
    WRITING_WORKFLOW_ID,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes

from backend.project_workspaces.tests.test_b7_multi_workflow import _Transport


def test_full_scaffold_chain_preserves_exact_provenance_and_history(tmp_path: Path) -> None:
    database = InMemoryDatabase()
    uow_factory = lambda: InMemoryUnitOfWork(database)
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=uow_factory,
        local_package_root=str(tmp_path / "cloud-packages"),
    )))
    qualify_full_scaffold_chain(client, tmp_path, uow_factory)


def qualify_full_scaffold_chain(
    client: TestClient, tmp_path: Path, uow_factory, *, seed_progress_parent=None,
) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    project = client.post("/projects", json={
        "name": "F1B synthetic full chain",
        "research_topic": "Synthetic exact provenance",
        "selected_workflow": "LITERATURE_SEARCH",
    }).json()
    project_id = project["project_id"]
    revision = 1
    idea = _add(client, project_id, "idea-discovery-local-experimental", revision)
    revision += 1
    writing_a = _add(client, project_id, WRITING_WORKFLOW_ID, revision)
    revision += 1
    review_a = _add(client, project_id, REVIEW_WORKFLOW_ID, revision)
    revision += 1
    experiment = _add(client, project_id, EXPERIMENT_WORKFLOW_ID, revision)
    revision += 1
    writing_b = _add(client, project_id, WRITING_WORKFLOW_ID, revision)
    revision += 1
    review_b = _add(client, project_id, REVIEW_WORKFLOW_ID, revision)
    revision += 1

    bootstrap = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
    workspace = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=bootstrap)
    transport = _Transport(client)
    now = datetime(2026, 8, 9, tzinfo=UTC)
    workspace_cli.sync_workspace(workspace_root=workspace, transport=transport, now=now)
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    roots = {
        item["workflow_instance_id"]: workspace / item["relative_path"]
        for item in lock["installed_capsules"]
    }
    literature = next(
        item for item in lock["installed_capsules"]
        if item["workflow_definition_id"] == "literature-search-local-experimental"
    )
    library = _seed_upstream(
        uow_factory=uow_factory, project_id=project_id, instance=literature,
        root=workspace / literature["relative_path"], artifact_type="selected-paper-library/v1",
        content={"schema": "selected-paper-library/v1", "papers": []}, character="a",
        seed_progress_parent=seed_progress_parent,
    )
    idea_artifact = _seed_upstream(
        uow_factory=uow_factory, project_id=project_id, instance={
            **idea, "capsule_id": idea["capsule_id"], "capsule_version": idea["capsule_version"]
        }, root=roots[idea["workflow_instance_id"]],
        artifact_type="selected-research-idea/v1",
        content={
            "schema": "selected-research-idea/v1",
            "selected_idea": {
                "title": "Synthetic bounded direction",
                "research_question": "How can exact provenance be qualified?",
            },
        }, character="b", seed_progress_parent=seed_progress_parent,
    )
    workspace_cli.refresh_artifact_index(
        workspace_root=workspace, transport=transport, now=now + timedelta(minutes=1)
    )

    _bind(client, project_id, writing_a, "research_idea", idea_artifact, 1)
    _bind(client, project_id, writing_a, "literature_library", library, 2)
    draft_a = _materialize_finalize(
        client, transport, workspace, roots[writing_a["workflow_instance_id"]], writing_a,
        now + timedelta(minutes=2),
    )
    assert draft_a["producer_core_capability_maturity"] == "SCAFFOLD_CORE"
    draft_a_path = roots[writing_a["workflow_instance_id"]] / draft_a["relative_path"]
    draft_a_bytes = draft_a_path.read_bytes()
    assert b"SCAFFOLD PLACEHOLDER" in draft_a_bytes

    workspace_cli.refresh_artifact_index(
        workspace_root=workspace, transport=transport, now=now + timedelta(minutes=3)
    )
    _bind(client, project_id, review_a, "manuscript", draft_a, 3)
    review_report = _materialize_finalize(
        client, transport, workspace, roots[review_a["workflow_instance_id"]], review_a,
        now + timedelta(minutes=4),
    )
    review_value = json.loads(
        (roots[review_a["workflow_instance_id"]] / review_report["relative_path"]).read_text()
    )
    assert review_value["recommendation"] == "INSUFFICIENT_EVIDENCE"
    assert review_value["source_manuscript"]["artifact_id"] == draft_a["artifact_id"]

    workspace_cli.refresh_artifact_index(
        workspace_root=workspace, transport=transport, now=now + timedelta(minutes=5)
    )
    _bind(client, project_id, experiment, "research_idea", idea_artifact, 4)
    experiment_record = _materialize_finalize(
        client, transport, workspace, roots[experiment["workflow_instance_id"]], experiment,
        now + timedelta(minutes=6),
    )
    experiment_value = json.loads(
        (roots[experiment["workflow_instance_id"]] / experiment_record["relative_path"]).read_text()
    )
    assert (experiment_value["mode"], experiment_value["execution_status"], experiment_value["actual_results"]) == (
        "IDEA_EXPERIMENT", "PLACEHOLDER_NOT_EXECUTED", None
    )

    workspace_cli.refresh_artifact_index(
        workspace_root=workspace, transport=transport, now=now + timedelta(minutes=7)
    )
    for index, (key, artifact) in enumerate((
        ("research_idea", idea_artifact), ("literature_library", library),
        ("prior_manuscript", draft_a), ("review_feedback", review_report),
    ), start=5):
        _bind(client, project_id, writing_b, key, artifact, index)
    draft_b = _materialize_finalize(
        client, transport, workspace, roots[writing_b["workflow_instance_id"]], writing_b,
        now + timedelta(minutes=8),
    )
    draft_b_value = json.loads(
        (roots[writing_b["workflow_instance_id"]] / draft_b["relative_path"]).read_text()
    )
    assert draft_b_value["source_artifacts"]["prior_manuscript"]["artifact_id"] == draft_a["artifact_id"]
    assert draft_b_value["source_artifacts"]["review_feedback"]["artifact_id"] == review_report["artifact_id"]
    assert draft_a_path.read_bytes() == draft_a_bytes

    manuscripts = client.get(
        f"/projects/{project_id}/artifacts",
        params={"artifact_type": "manuscript-draft/v1"},
    ).json()["artifacts"]
    assert {item["artifact_id"] for item in manuscripts} == {
        draft_a["artifact_id"], draft_b["artifact_id"]
    }
    progress_response = client.get(f"/projects/{project_id}/progress")
    assert progress_response.status_code == 200, progress_response.text
    assert review_b["workflow_instance_id"] not in {
        item["consumer_workflow_instance_id"]
        for item in progress_response.json()["dependency_edges"]
    }

    retired = client.post(
        f"/projects/{project_id}/workflow-instances/{writing_a['workflow_instance_id']}/retire",
        json={"base_revision": revision},
    )
    assert retired.status_code == 200, retired.text
    assert draft_a_path.read_bytes() == draft_a_bytes
    assert any(
        item["artifact_id"] == draft_a["artifact_id"]
        for item in client.get(f"/projects/{project_id}/artifacts").json()["artifacts"]
    )
    context = (roots[writing_b["workflow_instance_id"]] / "memory/context.md").read_text()
    assert '"completed_rounds":1' in context
    # A fresh module invocation reconstructs readiness solely from local files.
    assert scaffold_runtime.preflight(roots[writing_b["workflow_instance_id"]])["ready"]
    progress_response = client.get(f"/projects/{project_id}/progress")
    assert progress_response.status_code == 200, progress_response.text
    progress = progress_response.json()
    assert {item["core_capability_maturity"] for item in progress["instances"]} == {
        "REVIEWED_CORE", "SCAFFOLD_CORE"
    }
    assert len(progress["instances"]) == 7


def _add(client: TestClient, project_id: str, workflow_id: str, revision: int) -> dict:
    detail = client.get(f"/workflow-definitions/{workflow_id}").json()
    historical = {
        "idea-discovery-local-experimental": ("0.2.0", "0.3.0"),
        WRITING_WORKFLOW_ID: ("0.2.0", "0.4.0"),
        REVIEW_WORKFLOW_ID: ("0.2.0", "0.4.0"),
        EXPERIMENT_WORKFLOW_ID: ("0.3.0", "0.5.0"),
    }
    workflow_version, capsule_version = historical[workflow_id]
    capsule = next(
        item for item in detail["capsules"]
        if item["workflow_version"] == workflow_version
        and item["capsule_version"] == capsule_version
    )
    response = client.post(f"/projects/{project_id}/workflow-instances", json={
        "workflow_definition_id": workflow_id,
        "workflow_version": workflow_version,
        "capsule_id": capsule["capsule_id"],
        "capsule_version": capsule_version,
        "base_revision": revision,
    })
    assert response.status_code == 201, response.text
    return response.json()


def _seed_upstream(
    *, uow_factory, project_id: str, instance: dict, root: Path,
    artifact_type: str, content: dict, character: str, seed_progress_parent=None,
) -> dict:
    payload = canonical_json(content).encode()
    checksum = sha256_bytes(payload)
    slug = artifact_type.split("/", 1)[0]
    relative = f"outputs/artifacts/{slug}/sha256-{checksum[7:]}.json"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    now = datetime(2026, 8, 9, tzinfo=UTC)
    artifact = ArtifactReference(
        artifact_id="artifact-" + character * 32, project_id=project_id,
        producer_workflow_instance_id=instance["workflow_instance_id"],
        producer_progress_receipt_id=f"f1b-upstream-{character}",
        producer_progress_report_id=f"f1b-upstream-report-{character}",
        producer_execution_round=1, producer_capsule_id=instance["capsule_id"],
        producer_capsule_version=instance["capsule_version"],
        artifact_type=artifact_type, artifact_schema_version=artifact_type,
        media_type="application/json", state=ArtifactState.LOCAL_AVAILABLE,
        relative_path=relative, content_checksum=checksum, size_bytes=len(payload),
        cloud_metadata_available=True, produced_at=now, retired_at=None,
        created_at=now, updated_at=now,
    )
    if seed_progress_parent is not None:
        seed_progress_parent(artifact)
    scope = uow_factory()
    try:
        scope.artifact_references.add_artifact(artifact)
        scope.commit()
    finally:
        close = getattr(scope, "close", None)
        if close is not None:
            close()
    return {"artifact_id": artifact.artifact_id, "content_checksum": checksum}


def _bind(
    client: TestClient, project_id: str, consumer: dict, key: str,
    artifact: dict, number: int,
) -> None:
    response = client.post(
        f"/projects/{project_id}/workflow-instances/{consumer['workflow_instance_id']}/artifact-dependencies",
        json={
            "requirement_key": key, "artifact_id": artifact["artifact_id"],
            "idempotency_key": f"00000000-0000-4000-8000-{number:012d}",
        },
    )
    assert response.status_code == 201, response.text


def _materialize_finalize(
    client: TestClient, transport: _Transport, workspace: Path, root: Path,
    instance: dict, now: datetime,
) -> dict:
    workspace_cli.refresh_artifact_index(
        workspace_root=workspace, transport=transport, now=now
    )
    setup = client.get(
        f"/projects/{instance['project_id']}/workflow-instances/"
        f"{instance['workflow_instance_id']}/input-setup"
    )
    assert setup.status_code == 200, setup.text
    omitted = setup.json()["omitted_optional_requirement_keys"]
    if omitted:
        decision = client.post(
            f"/projects/{instance['project_id']}/workflow-instances/"
            f"{instance['workflow_instance_id']}/input-setup-decisions",
            json={
                "omitted_optional_requirement_keys": omitted,
                "idempotency_key": str(uuid.uuid4()),
            },
        )
        assert decision.status_code == 201, decision.text
        confirmed = client.get(
            f"/projects/{instance['project_id']}/workflow-instances/"
            f"{instance['workflow_instance_id']}/input-setup"
        )
        assert confirmed.status_code == 200, confirmed.text
        assert confirmed.json()["current_decision"] is not None, confirmed.text
    workspace_cli.materialize_artifacts(
        workspace_root=workspace,
        consumer_workflow_instance_id=instance["workflow_instance_id"],
        transport=transport, now=now,
    )
    descriptor = json.loads((workspace / workspace_cli.WORKSPACE_DESCRIPTOR).read_text())
    workspace_cli._prepare_scaffold_input_provenance(
        workspace=workspace, descriptor=descriptor, capsule=root,
        workflow_instance_id=instance["workflow_instance_id"], transport=transport,
    )
    assert scaffold_runtime.preflight(root)["ready"]
    config = json.loads((root / "workflow/scaffold.json").read_text())
    before = scaffold_runtime._prepare_draft(root, config)
    artifact_output = scaffold_runtime._publish(root, config)
    scaffold_runtime._update_context(root, config, artifact_output)
    report_path = scaffold_runtime._finalize(root, before)
    manifest = json.loads((root / "package-manifest.json").read_text())
    report = json.loads(report_path.read_text())
    envelope = ProgressReportUploadEnvelope.create(
        original_report_bytes=report_path.read_bytes(), project_id=manifest["experimental_project_identity"],
        package_id=manifest["package_id"], package_checksum=manifest["package_checksum"],
        report_schema_version=report["schema_version"], report_id=report["report_id"],
        report_checksum=report["report_checksum"], original_report_media_type="application/json",
        uploaded_at=report["completed_at"], uploader_type="f1b-test",
        client_version="f1b-test/0.1.0", source_path_hint=report_path.relative_to(root).as_posix(),
        context_snapshot_metadata=None,
    )
    artifact_id = "artifact-" + uuid.uuid5(
        uuid.UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966"),
        "production-artifact/v1|package=" + manifest["package_id"]
        + "|report=" + report["report_id"] + "|path=" + artifact_output["relative_path"]
        + "|checksum=" + artifact_output["checksum"],
    ).hex
    payload = envelope.to_dict()
    payload["workflow_instance_id"] = instance["workflow_instance_id"]
    payload["artifact_declarations"] = [{
        "artifact_id": artifact_id,
        "artifact_type": artifact_output["artifact_kind"],
        "artifact_schema_version": artifact_output["artifact_kind"],
        "media_type": artifact_output["media_type"],
        "relative_path": artifact_output["relative_path"],
        "content_checksum": artifact_output["checksum"],
        "size_bytes": artifact_output["size"],
        "produced_at": report["completed_at"],
    }]
    response = client.post(
        f"/projects/{manifest['experimental_project_identity']}/progress-reports",
        json=payload,
    )
    assert response.status_code == 201, response.text
    artifacts = client.get(
        f"/projects/{manifest['experimental_project_identity']}/artifacts",
        params={"workflow_instance_id": instance["workflow_instance_id"]},
    ).json()["artifacts"]
    return next(item for item in artifacts if item["artifact_id"] == artifact_id)
