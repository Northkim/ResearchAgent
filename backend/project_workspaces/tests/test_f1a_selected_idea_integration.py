from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.progress_reports.contracts import ProgressReportUploadEnvelope
from backend.research.adapters.local_artifact_storage import (
    LocalFilesystemArtifactStorage,
)
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.tests.test_b7_multi_workflow import (
    _Transport,
    _finalize_progress,
    _literature_outputs,
    _post_production_literature_progress,
)
from backend.workflow_packages.serialization import canonical_json


def test_selected_idea_progress_promotes_one_canonical_artifact_and_retries(
    tmp_path,
) -> None:
    database = InMemoryDatabase()
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        local_package_root=str(tmp_path / "packages"),
        artifact_storage=LocalFilesystemArtifactStorage(tmp_path / "progress-artifacts"),
    )))
    project_id = client.post("/projects", json={
        "name": "F1A promotion fixture",
        "research_topic": "Synthetic selected idea provenance",
        "selected_workflow": "LITERATURE_SEARCH",
    }).json()["project_id"]
    bootstrap = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
    workspace = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=bootstrap)
    transport = _Transport(client)
    workspace_cli.sync_workspace(
        workspace_root=workspace,
        transport=transport,
        now=datetime(2026, 8, 7, tzinfo=UTC),
    )
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    literature = lock["installed_capsules"][0]
    literature_root = workspace / literature["relative_path"]
    _literature_outputs(literature_root)
    literature_report = _finalize_progress(literature_root, state="COMPLETED")
    _post_production_literature_progress(
        client, literature_root, literature["workflow_instance_id"], literature_report
    )
    source_artifact = client.get(
        f"/projects/{project_id}/artifacts",
        params={"artifact_type": "selected-paper-library/v1"},
    ).json()["artifacts"][0]

    catalog = client.get(
        "/workflow-definitions/idea-discovery-local-experimental"
    ).json()
    idea_response = client.post(
        f"/projects/{project_id}/workflow-instances",
        json={
            "workflow_definition_id": "idea-discovery-local-experimental",
            "workflow_version": catalog["recommended_version"]["version"],
            "capsule_id": catalog["recommended_capsule"]["capsule_id"],
            "capsule_version": catalog["recommended_capsule"]["capsule_version"],
            "base_revision": 1,
        },
    )
    assert idea_response.status_code == 201, idea_response.text
    idea = idea_response.json()
    workspace_cli.sync_workspace(
        workspace_root=workspace,
        transport=transport,
        now=datetime(2026, 8, 7, 0, 10, tzinfo=UTC),
    )
    binding = client.post(
        f"/projects/{project_id}/workflow-instances/"
        f"{idea['workflow_instance_id']}/artifact-dependencies",
        json={
            "requirement_key": "paper_library",
            "artifact_id": source_artifact["artifact_id"],
            "idempotency_key": "00000000-0000-4000-8000-000000000141",
        },
    )
    assert binding.status_code == 201, binding.text
    workspace_cli.refresh_artifact_index(
        workspace_root=workspace,
        transport=transport,
        now=datetime(2026, 8, 7, 0, 11, tzinfo=UTC),
    )
    workspace_cli.materialize_artifacts(
        workspace_root=workspace,
        consumer_workflow_instance_id=idea["workflow_instance_id"],
        transport=transport,
        now=datetime(2026, 8, 7, 0, 12, tzinfo=UTC),
    )
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    idea_entry = next(
        item for item in lock["installed_capsules"]
        if item["workflow_instance_id"] == idea["workflow_instance_id"]
    )
    idea_root = workspace / idea_entry["relative_path"]
    workspace_cli._prepare_idea_output_provenance(
        capsule=idea_root,
        artifact_id=source_artifact["artifact_id"],
        checksum=source_artifact["content_checksum"],
    )
    candidates = json.loads((idea_root / "outputs/candidate_ideas.json").read_text())
    library = json.loads((idea_root / "inputs/selected-paper-library.json").read_text())
    candidates["ideas"] = [{
        "idea_id": "idea-001",
        "title": "Explicitly selected synthetic direction",
        "research_question": "How should explicit provenance be evaluated?",
        "motivation": "The supplied records expose a bounded concern.",
        "literature_basis": [library["papers"][0]["candidate_id"]],
        "observed_gap": "The bounded set leaves one question unresolved.",
        "proposed_direction": "Evaluate exact Artifact provenance.",
        "assumptions": ["The selected set is relevant."],
        "risks": ["Global novelty is not established."],
        "validation_needed": ["Broader validation."],
        "status": "selected",
    }]
    (idea_root / "outputs/candidate_ideas.json").write_text(
        canonical_json(candidates) + "\n", encoding="utf-8"
    )
    (idea_root / "outputs/idea_discovery_report.md").write_text(
        "# Report\n## Literature landscape\nBounded.\n"
        "## Observed patterns\nPattern.\n## Gaps\nPotential gap.\n"
        "## Candidate research directions\nOne candidate.\n"
        "## User choices\nThe user explicitly selected idea-001.\n"
        "## Uncertainties\nGlobal novelty is not proven.\n"
        "## Next validation needs\nBroader validation.\n",
        encoding="utf-8",
    )
    report_path = _finalize_progress(idea_root, state="COMPLETED")
    manifest = json.loads((idea_root / "package-manifest.json").read_text())
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
        uploaded_at="2026-08-07T00:20:00Z",
        uploader_type="local-cli",
        client_version="f1a-test/0.1.0",
        source_path_hint=report_path.relative_to(idea_root).as_posix(),
        context_snapshot_metadata=None,
    ).to_dict()
    envelope["workflow_instance_id"] = idea["workflow_instance_id"]
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
    first = client.post(f"/projects/{project_id}/progress-reports", json=envelope)
    replay = client.post(f"/projects/{project_id}/progress-reports", json=envelope)
    assert first.status_code == 201, first.text
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotent_replay"] is True
    mutated_retry = json.loads(json.dumps(envelope))
    mutated_retry["artifact_declarations"][0]["artifact_id"] = (
        "artifact-" + "f" * 32
    )
    conflict = client.post(
        f"/projects/{project_id}/progress-reports", json=mutated_retry
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["error"]["code"] == "PROGRESS_IDEMPOTENCY_CONFLICT"
    artifacts = client.get(
        f"/projects/{project_id}/artifacts",
        params={"artifact_type": "selected-research-idea/v1"},
    ).json()["artifacts"]
    assert len(artifacts) == 1
    assert artifacts[0]["artifact_id"] == artifact_id
    assert artifacts[0]["producer_workflow_instance_id"] == idea["workflow_instance_id"]
    assert artifacts[0]["producer_progress_report_id"] == report["report_id"]
