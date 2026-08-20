"""R4 E3/E5 exact Literature composition through public Workspace surfaces."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import runpy
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.artifact_references.contracts import ArtifactReference, ArtifactState
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.tests.test_generic_experiment_v5_workspace import (
    _seed_forward,
)
from backend.project_workspaces.tests.test_sync import _ClientTransport
from backend.workflow_packages.literature_consolidation import WORKFLOW_ID
from backend.workflow_packages.serialization import canonical_json, sha256_bytes


def _candidate(identifier: str, title: str, *, doi: str | None = None) -> dict:
    return {
        "candidate_id": f"candidate-{identifier * 16}",
        "provider_id": f"provider-{identifier}",
        "openalex_id": f"https://openalex.org/W{identifier * 8}",
        "title": title,
        "authors": ["Controlled Researcher"],
        "publication_year": 2026,
        "doi": doi,
        "source": "Controlled venue",
        "language": "en",
        "abstract": "Controlled bounded abstract evidence.",
        "source_query_ids": ["query-1"],
        "provenance_checksum": "sha256:" + identifier * 64,
        "deduplication_status": "UNIQUE",
    }


def _library(*candidates: dict) -> bytes:
    value = {
        "schema": "selected-paper-library/v1",
        "source_schemas": ["candidate-papers/v0.2", "selected-papers/v0.2"],
        "source_checksums": {
            "candidate_papers": "sha256:" + "a" * 64,
            "selected_papers": "sha256:" + "b" * 64,
        },
        "papers": [
            {
                "candidate_id": item["candidate_id"],
                "paper": item,
                "selection": {
                    "relevance_decision": "INCLUDE",
                    "inclusion_reason": "Controlled exact source selection.",
                    "evidence_availability": "METADATA_AND_ABSTRACT",
                },
            }
            for item in candidates
        ],
    }
    return (canonical_json(value) + "\n").encode("utf-8")


def _reference(project_id: str, producer: dict, content: bytes, digit: str) -> ArtifactReference:
    checksum = sha256_bytes(content)
    now = datetime(2026, 8, 20, tzinfo=UTC)
    return ArtifactReference(
        artifact_id="artifact-" + digit * 32,
        project_id=project_id,
        producer_workflow_instance_id=producer["workflow_instance_id"],
        producer_progress_receipt_id="progress-receipt-" + digit * 64,
        producer_progress_report_id="prv2-" + digit * 64,
        producer_execution_round=1,
        producer_capsule_id=producer["capsule_id"],
        producer_capsule_version=producer["capsule_version"],
        artifact_type="selected-paper-library/v1",
        artifact_schema_version="selected-paper-library/v1",
        media_type="application/json",
        state=ArtifactState.LOCAL_AVAILABLE,
        relative_path=(
            "outputs/artifacts/selected-paper-library/"
            f"sha256-{checksum[7:]}.json"
        ),
        content_checksum=checksum,
        size_bytes=len(content),
        cloud_metadata_available=True,
        produced_at=now,
        retired_at=None,
        created_at=now,
        updated_at=now,
    )


def test_two_exact_libraries_compose_without_latest_or_implicit_merge(
    tmp_path: Path,
) -> None:
    database = InMemoryDatabase()
    _seed_forward(database)
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
        local_package_root=str(tmp_path / "cloud-packages"),
    )))
    created = client.post("/projects", json={
        "name": "Controlled iterative Literature",
        "research_topic": "Exact explicit evidence composition",
        "selected_workflow": "LITERATURE_SEARCH",
        "workflow_setup": "literature-only",
    })
    assert created.status_code == 201, created.text
    project_id = created.json()["project_id"]
    initial = client.get(f"/projects/{project_id}/workflow-instances").json()
    first = initial["items"][0]
    second_response = client.post(
        f"/projects/{project_id}/workflow-instances",
        json={
            "workflow_definition_id": first["workflow_definition_id"],
            "workflow_version": first["workflow_version"],
            "capsule_id": first["capsule_id"],
            "capsule_version": first["capsule_version"],
            "base_revision": 1,
        },
    )
    assert second_response.status_code == 201, second_response.text
    second = second_response.json()
    catalog = client.get(f"/workflow-definitions/{WORKFLOW_ID}")
    assert catalog.status_code == 200, catalog.text
    recommended = catalog.json()
    assert recommended["recommended_version"]["version"] == "0.1.0"
    assert recommended["recommended_capsule"]["capsule_version"] == "0.1.0"
    consolidation_response = client.post(
        f"/projects/{project_id}/workflow-instances",
        json={
            "workflow_definition_id": WORKFLOW_ID,
            "workflow_version": "0.1.0",
            "capsule_id": recommended["recommended_capsule"]["capsule_id"],
            "capsule_version": "0.1.0",
            "base_revision": 2,
        },
    )
    assert consolidation_response.status_code == 201, consolidation_response.text
    consolidation = consolidation_response.json()

    workspace = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(
        target=workspace,
        descriptor=client.get(
            f"/projects/{project_id}/workspace-bootstrap"
        ).json(),
    )
    transport = _ClientTransport(client)
    assert workspace_cli.sync_workspace(
        workspace_root=workspace, transport=transport
    ).status == "SYNCED"
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    installed = {
        item["workflow_instance_id"]: item
        for item in lock["installed_capsules"]
    }

    duplicate = _candidate("c", "Shared exact paper", doi="10.1/shared")
    contents = (
        _library(_candidate("a", "Base paper"), duplicate),
        _library(duplicate, _candidate("b", "Additional paper")),
    )
    producers = (first, second)
    references = []
    for producer, content, digit in zip(producers, contents, ("1", "2"), strict=True):
        reference = _reference(project_id, producer, content, digit)
        root = workspace / installed[producer["workflow_instance_id"]]["relative_path"]
        target = root / reference.relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        database.local_artifact_references[reference.artifact_id] = reference
        references.append(reference)

    for requirement, reference in zip(
        ("base_library", "additional_library"), references, strict=True
    ):
        response = client.post(
            f"/projects/{project_id}/workflow-instances/"
            f"{consolidation['workflow_instance_id']}/artifact-dependencies",
            json={
                "requirement_key": requirement,
                "artifact_id": reference.artifact_id,
                "idempotency_key": str(uuid4()),
            },
        )
        assert response.status_code == 201, response.text
    workspace_cli.refresh_artifact_index(
        workspace_root=workspace, transport=transport
    )
    materialized = workspace_cli.materialize_artifacts(
        workspace_root=workspace,
        consumer_workflow_instance_id=consolidation["workflow_instance_id"],
        transport=transport,
    )
    assert materialized.materialized_count == 2
    root = workspace / installed[consolidation["workflow_instance_id"]]["relative_path"]
    assert (root / "inputs/base-paper-library.json").read_bytes() == contents[0]
    assert (root / "inputs/additional-paper-library.json").read_bytes() == contents[1]

    preflight = workspace_cli.run_workflow(
        workspace_root=workspace,
        workflow_instance_id=consolidation["workflow_instance_id"],
        transport=transport,
        api_url="http://127.0.0.1:8000",
        preflight_only=True,
    )
    assert preflight.status == "PREFLIGHT_READY"
    runtime = runpy.run_path(str(root / "reagent_local.py"))

    def owner_screening(capsule: Path, _executable: str | None) -> None:
        candidates = json.loads((capsule / "outputs/candidate_papers.json").read_text())
        rows = candidates["candidates"]
        (capsule / "outputs/selected_papers.json").write_text(
            canonical_json({
                "schema_version": "selected-papers/v0.2",
                "mode": "NORMAL",
                "selection_status": "SUFFICIENT",
                "selected": [{
                    "candidate_id": item["candidate_id"],
                    "relevance_decision": "INCLUDE",
                    "inclusion_reason": "Owner kept the controlled exact source.",
                    "evidence_availability": "METADATA_AND_ABSTRACT",
                } for item in rows],
                "exclusions": [],
                "exclusion_summary": {},
            }) + "\n",
            encoding="utf-8",
        )
        (capsule / "memory/owner-decisions.json").write_text(
            canonical_json({
                "schema_version": (
                    "reagent.owner-decision-snapshot.literature/v0.1"
                ),
                "candidate_set_checksum": sha256_bytes(
                    (capsule / "outputs/candidate_papers.json").read_bytes()
                ),
                "decisions": [{
                    "candidate_id": item["candidate_id"],
                    "disposition": "SELECTED",
                } for item in rows],
            }) + "\n",
            encoding="utf-8",
        )
        (capsule / "outputs/literature_search_report.md").write_text(
            "# Consolidated Literature\n\nThree exact deduplicated records.\n",
            encoding="utf-8",
        )

    runtime["run"].__globals__["_run_harness"] = owner_screening
    runtime["run"](
        root, consolidation["workflow_instance_id"], codex_executable=None
    )
    reports = workspace_cli._validated_local_progress_reports(
        root, json.loads((root / "package-manifest.json").read_text())
    )
    assert reports[-1]["status"] == "COMPLETED"
    selected_outputs = [
        item for item in reports[-1]["output_artifacts"]
        if item["artifact_kind"] == "selected-paper-library/v1"
    ]
    assert len(selected_outputs) == 1
    final_library = json.loads((root / selected_outputs[0]["relative_path"]).read_text())
    assert [item["paper"]["title"] for item in final_library["papers"]] == [
        "Base paper", "Shared exact paper", "Additional paper",
    ]
