from __future__ import annotations

import hashlib
import json
import runpy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.progress_reports.contracts import ProgressReportUploadEnvelope
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.production_workflows import (
    IDEA_DISCOVERY_CAPSULE_ID,
    LITERATURE_SEARCH_V0_8_CAPSULE_ID,
)
from backend.workflow_packages.production_workflows import (
    IDEA_DISCOVERY_WORKFLOW_ID,
    IDEA_DISCOVERY_WORKFLOW_VERSION,
    LITERATURE_SEARCH_WORKFLOW_ID,
    LITERATURE_SEARCH_V0_6_WORKFLOW_VERSION,
)
from backend.workflow_packages.serialization import canonical_json


class _Transport:
    def __init__(self, client: TestClient) -> None:
        self.client = client
        self.downloads: list[str] = []

    def create_plan(self, project_id, payload):
        response = self.client.post(
            f"/projects/{project_id}/workspace/sync-plan", json=payload
        )
        assert response.status_code == 200, response.text
        return response.json()

    def download(self, path, expected=None):
        del expected
        self.downloads.append(path)
        response = self.client.get(path)
        assert response.status_code == 200, response.text
        return response.content

    def acknowledge(self, project_id, payload):
        response = self.client.post(
            f"/projects/{project_id}/workspace/sync-ack", json=payload
        )
        assert response.status_code in {200, 201}, response.text
        return response.json()

    def list_artifacts(self, project_id, *, offset=0, limit=100):
        response = self.client.get(
            f"/projects/{project_id}/artifacts",
            params={"offset": offset, "limit": limit},
        )
        assert response.status_code == 200, response.text
        return response.json()

    def report_artifact_content_qualification(
        self, project_id, artifact_id, payload
    ):
        response = self.client.put(
            f"/projects/{project_id}/artifacts/{artifact_id}/content-qualification",
            json=payload,
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


def _literature_outputs(root: Path) -> None:
    (root / "outputs/search_plan.md").write_text(
        """# Search plan
## Interpreted topic
Fictional continuity.
## Concepts and synonyms
continuity; handoff
## Query variants
query-1, query-2
## Search bounds
Two calls.
## Screening rules
Direct relevance.
## Evidence limitations
Metadata and abstracts only; no full text.
""",
        encoding="utf-8",
    )
    candidates = {
        "schema_version": "candidate-papers/v0.2",
        "mode": "DEMO",
        "candidates": [
            {
                "candidate_id": f"candidate-{index:016x}",
                "provider_id": f"fictional-provider-{index}",
                "openalex_id": None,
                "title": f"Fictional paper {index}",
                "authors": [f"Fictional Author {index}"],
                "publication_year": 2026,
                "doi": None,
                "source": "Fictional venue",
                "language": "en",
                "abstract": "Fictional abstract evidence.",
                "source_query_ids": ["query-1"],
                "provenance_checksum": "sha256:" + f"{index:064x}",
                "deduplication_status": "UNIQUE",
            }
            for index in range(1, 4)
        ],
    }
    selected = {
        "schema_version": "selected-papers/v0.2",
        "mode": "DEMO",
        "selection_status": "SUFFICIENT",
        "selected": [
            {
                "candidate_id": item["candidate_id"],
                "relevance_decision": "INCLUDE",
                "inclusion_reason": "Direct fictional evidence.",
                "evidence_availability": "METADATA_AND_ABSTRACT",
            }
            for item in candidates["candidates"]
        ],
        "exclusions": [],
        "exclusion_summary": "No exclusions.",
    }
    candidate_path = root / "outputs/candidate_papers.json"
    candidate_path.write_text(json.dumps(candidates), encoding="utf-8")
    (root / "outputs/selected_papers.json").write_text(
        json.dumps(selected), encoding="utf-8"
    )
    (root / "outputs/literature_search_report.md").write_text(
        """FICTIONAL DEMO EVIDENCE.
# Literature search report
## Executive summary
Bounded synthesis.
## Search coverage
Two bounded queries.
## Main research themes
Continuity.
## Common methods
Metadata comparison.
## Representative works
Three records.
## Trends
Transparent handoffs.
## Limitations
Metadata and abstract-only evidence; full text was not read.
## Potential research gaps
Longitudinal validation.
## Recommended next research action
Review the local evidence.
## Selected-paper references
Candidates 1-3.
""",
        encoding="utf-8",
    )
    owner_decisions = root / "memory/owner-decisions.json"
    if owner_decisions.exists():
        owner_decisions.write_text(canonical_json({
            "schema_version": "reagent.owner-decision-snapshot.literature/v0.1",
            "candidate_set_checksum": (
                "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest()
            ),
            "decision_revision": 1,
            "decisions": [{
                "candidate_id": item["candidate_id"],
                "disposition": "SELECTED",
                "reason": "Direct fictional evidence.",
            } for item in candidates["candidates"]],
        }) + "\n", encoding="utf-8")


def _finalize_progress(root: Path, *, state: str, status: str = "COMPLETED") -> Path:
    progress = runpy.run_path(str(root / "progress_report.py"))
    before = progress["snapshot"](root)["context_before_checksum"]
    existing = sorted((root / "memory/progress/reports").glob("prv2-*.json"))
    previous = json.loads(existing[-1].read_text()) if existing else None
    round_number = 1 if previous is None else previous["execution_round"] + 1
    draft = {
        "execution_round": round_number,
        "harness_type": "codex",
        "harness_version": None,
        "harness_session_id": f"b7-round-{round_number}",
        "previous_report_id": None if previous is None else previous["report_id"],
        "previous_report_checksum": None if previous is None else previous["report_checksum"],
        "started_at": "2026-08-07T00:00:00Z",
        "completed_at": f"2026-08-07T00:0{round_number}:00Z",
        "status": status,
        "completed_work": [state],
        "current_state": state,
        "next_recommended_action": "Review the next explicit decision",
        "continuation_reason": None,
        "warnings": [],
        "errors": [],
        "unresolved_questions": [],
        "continuation_instructions": ["Read local memory before continuing"],
    }
    if previous is not None and previous["status"] == "COMPLETED":
        draft["continuation_reason"] = "Owner requested a refinement round"
    (root / "memory/progress/report-draft.json").write_text(
        canonical_json(draft) + "\n", encoding="utf-8"
    )
    result = progress["finalize"](
        package_root=root,
        draft_path="memory/progress/report-draft.json",
        context_before_checksum=before,
    )
    return root / result["created"]


def _post_progress(
    client: TestClient, root: Path, instance_id: str, report_path: Path,
    *, with_declarations: bool,
) -> dict:
    manifest = json.loads((root / "package-manifest.json").read_text())
    report = json.loads(report_path.read_text())
    envelope = ProgressReportUploadEnvelope.create(
        original_report_bytes=report_path.read_bytes(),
        project_id=manifest["experimental_project_identity"],
        package_id=manifest["package_id"],
        package_checksum=manifest["package_checksum"],
        report_schema_version=report["schema_version"],
        report_id=report["report_id"],
        report_checksum=report["report_checksum"],
        original_report_media_type="application/json",
        uploaded_at="2026-08-07T00:10:00Z",
        uploader_type="local-cli",
        client_version="b7-test/0.1.0",
        source_path_hint=report_path.relative_to(root).as_posix(),
        context_snapshot_metadata=None,
    )
    payload = envelope.to_dict()
    payload["workflow_instance_id"] = instance_id
    payload["artifact_declarations"] = []
    if with_declarations:
        artifact_output = next(
            item
            for item in report["output_artifacts"]
            if item["artifact_kind"] == "selected-paper-library/v1"
        )
        import uuid

        identifier = uuid.uuid5(
            uuid.UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966"),
            "production-artifact/v1|package=" + manifest["package_id"]
            + "|report=" + report["report_id"]
            + "|path=" + artifact_output["relative_path"]
            + "|checksum=" + artifact_output["checksum"],
        )
        payload["artifact_declarations"] = [{
            "artifact_id": "artifact-" + identifier.hex,
            "artifact_type": "selected-paper-library/v1",
            "artifact_schema_version": "selected-paper-library/v1",
            "media_type": "application/json",
            "relative_path": artifact_output["relative_path"],
            "content_checksum": artifact_output["checksum"],
            "size_bytes": artifact_output["size"],
            "produced_at": report["completed_at"],
        }]
    response = client.post(
        f"/projects/{manifest['experimental_project_identity']}/progress-reports",
        json=payload,
    )
    if response.status_code != 201:
        detail = client.get(
            f"/projects/{manifest['experimental_project_identity']}"
            f"/progress-reports/{report['report_id']}"
        )
        raise AssertionError(
            response.text + ("; stored=" + detail.text if detail.status_code == 200 else "")
        )
    return response.json()


def _post_production_literature_progress(
    client: TestClient,
    root: Path,
    instance_id: str,
    report_path: Path,
) -> dict:
    manifest = json.loads((root / "package-manifest.json").read_text())
    runner = runpy.run_path(str(root / "reagent_local.py"))
    payload = runner["_upload_envelope"](
        root=root,
        manifest=manifest,
        report_path=report_path,
    )
    # The immutable 0.6.0 local-session adapter omitted this redundant list.
    # Cloud must recover it only from the exact reviewed Capsule/Progress
    # contract, preserving the already-published Capsule bytes.
    payload["artifact_declarations"] = []
    payload["workflow_instance_id"] = instance_id
    response = client.post(
        f"/projects/{manifest['experimental_project_identity']}/progress-reports",
        json=payload,
    )
    assert response.status_code in {200, 201}, response.text
    return {"http_status": response.status_code, **response.json()}


def qualify_real_multi_workflow_artifact_handoff(
    client: TestClient,
    tmp_path: Path,
    *,
    database: InMemoryDatabase | None = None,
) -> str:
    project = client.post("/projects", json={
        "name": "B7 fictional architecture qualification",
        "research_topic": "Fictional cross-Workflow provenance",
        "selected_workflow": "LITERATURE_SEARCH",
    })
    assert project.status_code == 201
    project_id = project.json()["project_id"]
    bootstrap = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
    literature = bootstrap["workflow_capsules"][0]
    assert literature["workflow_definition_version"] == LITERATURE_SEARCH_V0_6_WORKFLOW_VERSION
    assert literature["capsule_id"] == LITERATURE_SEARCH_V0_8_CAPSULE_ID
    assert literature["legacy_package_compatible"] is False
    workspace = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=bootstrap)
    transport = _Transport(client)
    first_sync = workspace_cli.sync_workspace(
        workspace_root=workspace,
        transport=transport,
        now=datetime(2026, 8, 7, tzinfo=UTC),
    )
    assert first_sync.status == "SYNCED"
    assert len(transport.downloads) == 1
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    literature_entry = lock["installed_capsules"][0]
    literature_root = workspace / literature_entry["relative_path"]
    immutable_before = workspace_cli._immutable_contract_checksum(
        literature_root,
        json.loads((literature_root / "package-manifest.json").read_text()),
    )

    _literature_outputs(literature_root)
    literature_report = _finalize_progress(
        literature_root, state="COMPLETED", status="COMPLETED"
    )
    first_upload = _post_production_literature_progress(
        client,
        literature_root,
        literature["workflow_instance_id"],
        literature_report,
    )
    replay_upload = _post_production_literature_progress(
        client,
        literature_root,
        literature["workflow_instance_id"],
        literature_report,
    )
    assert first_upload["http_status"] == 201
    assert replay_upload["http_status"] == 200
    assert replay_upload["idempotent_replay"] is True
    if database is not None:
        # Model an accepted B7 Progress row whose immutable local-session
        # adapter omitted canonical Artifact promotion. An exact retry repairs
        # only that derived metadata and never creates another Progress row.
        assert len(database.local_artifact_references) == 1
        database.local_artifact_references.clear()
        repaired_upload = _post_production_literature_progress(
            client,
            literature_root,
            literature["workflow_instance_id"],
            literature_report,
        )
        assert repaired_upload["http_status"] == 200
        assert repaired_upload["idempotent_replay"] is True
        assert len(database.local_artifact_references) == 1
    artifacts = client.get(
        f"/projects/{project_id}/artifacts",
        params={"artifact_type": "selected-paper-library/v1"},
    ).json()["artifacts"]
    assert len(artifacts) == 1
    artifact = artifacts[0]

    created = client.post(
        f"/projects/{project_id}/workflow-instances",
        json={
            "workflow_definition_id": IDEA_DISCOVERY_WORKFLOW_ID,
            "workflow_version": IDEA_DISCOVERY_WORKFLOW_VERSION,
            "capsule_id": IDEA_DISCOVERY_CAPSULE_ID,
            "capsule_version": "0.1.0",
            "base_revision": 1,
        },
    )
    assert created.status_code == 201, created.text
    idea = created.json()
    second_sync = workspace_cli.sync_workspace(
        workspace_root=workspace,
        transport=transport,
        now=datetime(2026, 8, 7, 0, 20, tzinfo=UTC),
    )
    assert second_sync.status == "SYNCED"
    assert len(transport.downloads) == 2
    assert workspace_cli._immutable_contract_checksum(
        literature_root,
        json.loads((literature_root / "package-manifest.json").read_text()),
    ) == immutable_before

    binding = client.post(
        f"/projects/{project_id}/workflow-instances/"
        f"{idea['workflow_instance_id']}/artifact-dependencies",
        json={
            "requirement_key": "paper_library",
            "artifact_id": artifact["artifact_id"],
            "idempotency_key": "00000000-0000-4000-8000-000000000071",
        },
    )
    assert binding.status_code == 201, binding.text
    with pytest.raises(workspace_cli.WorkspaceCLIError) as missing_input:
        workspace_cli.run_workflow(
            workspace_root=workspace,
            workflow_instance_id=idea["workflow_instance_id"],
            transport=transport,
            api_url="http://127.0.0.1:8000",
            preflight_only=True,
        )
    assert missing_input.value.code == "DEPENDENCY_UNRESOLVED"
    workspace_cli.refresh_artifact_index(
        workspace_root=workspace, transport=transport,
        now=datetime(2026, 8, 7, 0, 21, tzinfo=UTC),
    )
    materialized = workspace_cli.materialize_artifacts(
        workspace_root=workspace,
        consumer_workflow_instance_id=idea["workflow_instance_id"],
        transport=transport,
        now=datetime(2026, 8, 7, 0, 22, tzinfo=UTC),
    )
    assert materialized.materialized_count == 1
    source_path = literature_root / artifact["relative_path"]
    source_bytes = source_path.read_bytes()
    source_path.write_bytes(source_bytes + b"\n")
    with pytest.raises(workspace_cli.WorkspaceCLIError) as drift:
        workspace_cli.materialize_artifacts(
            workspace_root=workspace,
            consumer_workflow_instance_id=idea["workflow_instance_id"],
            transport=transport,
            now=datetime(2026, 8, 7, 0, 23, tzinfo=UTC),
        )
    assert drift.value.code == "LOCAL_ARTIFACT_DRIFT"
    source_path.write_bytes(source_bytes)
    recovered = workspace_cli.materialize_artifacts(
        workspace_root=workspace,
        consumer_workflow_instance_id=idea["workflow_instance_id"],
        transport=transport,
        now=datetime(2026, 8, 7, 0, 24, tzinfo=UTC),
    )
    assert recovered.status == "MATERIALIZED"
    ready = workspace_cli.run_workflow(
        workspace_root=workspace,
        workflow_instance_id=idea["workflow_instance_id"],
        transport=transport,
        api_url="http://127.0.0.1:8000",
        preflight_only=True,
    )
    assert ready.status == "PREFLIGHT_READY"
    local_before_idea_progress = {
        item["workflow_definition_id"]: item
        for item in workspace_cli.workflow_list(workspace)["workflows"]
    }
    assert local_before_idea_progress[LITERATURE_SEARCH_WORKFLOW_ID]["next_action"] == "REVIEW_RESULT"
    assert local_before_idea_progress[IDEA_DISCOVERY_WORKFLOW_ID]["local_readiness"] == "LOCALLY_MATERIALIZED"
    assert local_before_idea_progress[IDEA_DISCOVERY_WORKFLOW_ID]["next_action"] == "RUN"

    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    idea_entry = next(
        item for item in lock["installed_capsules"]
        if item["workflow_instance_id"] == idea["workflow_instance_id"]
    )
    idea_root = workspace / idea_entry["relative_path"]
    assert not (idea_root / "outputs/candidate_ideas.json").exists()
    input_bytes = (idea_root / "inputs/selected-paper-library.json").read_bytes()
    assert input_bytes == (
        literature_root / artifact["relative_path"]
    ).read_bytes()
    candidate_ids = [item["candidate_id"] for item in json.loads(input_bytes)["papers"]]
    workspace_cli._prepare_idea_output_provenance(
        capsule=idea_root,
        artifact_id=artifact["artifact_id"],
        checksum=artifact["content_checksum"],
    )
    scaffold = json.loads(
        (idea_root / "outputs/candidate_ideas.json").read_text(encoding="utf-8")
    )
    assert scaffold["source_artifact"] == {
        "artifact_id": artifact["artifact_id"],
        "artifact_type": "selected-paper-library/v1",
        "sha256": artifact["content_checksum"],
    }
    assert scaffold["ideas"] == []
    workspace_cli._prepare_idea_output_provenance(
        capsule=idea_root,
        artifact_id=artifact["artifact_id"],
        checksum=artifact["content_checksum"],
    )
    scaffold["ideas"] = [{
                "idea_id": "idea-001",
                "title": "Fictional continuity study",
                "research_question": "How should explicit handoffs be evaluated?",
                "motivation": "The bounded literature identifies a continuity concern.",
                "literature_basis": candidate_ids[:2],
                "observed_gap": "Longitudinal evidence is limited in the supplied set.",
                "proposed_direction": "Compare explicit and implicit handoff protocols.",
                "assumptions": ["The supplied metadata is representative enough for ideation."],
                "risks": ["The bounded set cannot establish novelty."],
                "validation_needed": ["Run a broader novelty-oriented literature search."],
                "status": "candidate",
            }]
    (idea_root / "outputs/candidate_ideas.json").write_text(
        canonical_json(scaffold),
        encoding="utf-8",
    )
    with pytest.raises(workspace_cli.WorkspaceCLIError) as provenance_conflict:
        workspace_cli._prepare_idea_output_provenance(
            capsule=idea_root,
            artifact_id=artifact["artifact_id"],
            checksum="sha256:" + "f" * 64,
        )
    assert provenance_conflict.value.code == "WORKFLOW_OUTPUT_PROVENANCE_CONFLICT"
    (idea_root / "outputs/idea_discovery_report.md").write_text(
        """# Idea Discovery report
## Literature landscape
Bounded evidence only.
## Observed patterns
Explicit handoffs recur.
## Gaps
Longitudinal evidence is limited.
## Candidate research directions
Compare handoff protocols.
## User choices
Keep the direction as a candidate.
## Uncertainties
The supplied set is incomplete; global novelty is not proven.
## Next validation needs
Broader search and empirical design.
""",
        encoding="utf-8",
    )
    idea_report = _finalize_progress(
        idea_root, state="CANDIDATE_IDEAS", status="IN_PROGRESS"
    )
    _post_progress(
        client,
        idea_root,
        idea["workflow_instance_id"],
        idea_report,
        with_declarations=False,
    )
    local_after_idea_progress = {
        item["workflow_definition_id"]: item
        for item in workspace_cli.workflow_list(workspace)["workflows"]
    }
    assert local_after_idea_progress[IDEA_DISCOVERY_WORKFLOW_ID]["local_readiness"] == "IN_PROGRESS"
    assert local_after_idea_progress[IDEA_DISCOVERY_WORKFLOW_ID]["next_action"] == "CONTINUE"
    projection = client.get(f"/projects/{project_id}/progress").json()
    assert {item["workflow_definition_id"] for item in projection["instances"]} == {
        LITERATURE_SEARCH_WORKFLOW_ID,
        IDEA_DISCOVERY_WORKFLOW_ID,
    }
    assert projection["total_progress_report_count"] == 2
    assert projection["dependency_edges"] == [{
        "binding_id": binding.json()["binding_id"],
        "consumer_workflow_instance_id": idea["workflow_instance_id"],
        "requirement_key": "paper_library",
        "artifact_id": artifact["artifact_id"],
        "expected_checksum": artifact["content_checksum"],
        "state": "ACTIVE",
        "producer_workflow_instance_id": literature["workflow_instance_id"],
        "artifact_type": "selected-paper-library/v1",
        "artifact_schema_version": "selected-paper-library/v1",
        "produced_at": artifact["produced_at"],
    }]

    retired = client.post(
        f"/projects/{project_id}/workflow-instances/"
        f"{literature['workflow_instance_id']}/retire",
        json={"base_revision": 2},
    )
    assert retired.status_code == 200, retired.text
    retired_sync = workspace_cli.sync_workspace(
        workspace_root=workspace,
        transport=transport,
        now=datetime(2026, 8, 7, 0, 30, tzinfo=UTC),
    )
    assert retired_sync.status == "SYNCED"
    assert len(transport.downloads) == 2
    assert literature_root.is_dir() and source_path.read_bytes() == source_bytes
    retained = client.get(f"/projects/{project_id}/artifacts").json()["artifacts"]
    assert retained[0]["artifact_id"] == artifact["artifact_id"]
    return project_id


def test_real_multi_workflow_artifact_handoff_and_progress(tmp_path: Path) -> None:
    database = InMemoryDatabase()
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        local_package_root=str(tmp_path / "cloud-packages"),
    )))
    qualify_real_multi_workflow_artifact_handoff(
        client, tmp_path, database=database
    )
