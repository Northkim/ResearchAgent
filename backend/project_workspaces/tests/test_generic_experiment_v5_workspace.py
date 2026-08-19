from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.artifact_references.contracts import (
    CompatibilityMode, MaterializationMode, WorkflowArtifactRequirement,
)
from backend.artifact_references.generic_experiment_v5_contracts import (
    EvidenceKind, EvidenceSourceKind, EvidenceSourceRef, ScientificEvidenceBlock,
    finalize_experiment_record_v5, validate_experiment_record_v5,
)
from backend.artifact_references.tests.test_generic_experiment_record_v5 import _result
from backend.artifact_references.tests.test_research_flow_contracts import _selected
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.contracts import (
    CoreCapabilityMaturity, WorkflowCapsuleVersion, WorkflowDefinitionVersion,
    WorkflowDefinitionVersionSkillPin, WorkflowReviewStatus,
)
from backend.project_workspaces.tests.test_f1b_full_scaffold_flow import _seed_upstream
from backend.project_workspaces.tests.test_generic_experiment_public_workspace import (
    _seed_publication,
)
from backend.project_workspaces.tests.test_owner_real_research_gate import _loopback_server
from backend.project_workspaces.tests.test_real_experiment_workspace import _Transport
from backend.workflow_packages.experiment_capability_runtime import CapabilityEvaluationResult
from backend.workflow_packages.generic_experiment_v5_publication import (
    GENERIC_EXPERIMENT_V5_ARTIFACT_TYPE, GENERIC_EXPERIMENT_V5_CAPSULE_CHECKSUM,
    GENERIC_EXPERIMENT_V5_CAPSULE_ID, GENERIC_EXPERIMENT_V5_CAPSULE_VERSION,
    GENERIC_EXPERIMENT_V5_CONTRACT_CHECKSUM, GENERIC_EXPERIMENT_V5_WORKFLOW_VERSION,
)
from backend.workflow_packages.generic_experiment_publication import REFERENCE_CAPABILITY_SKILL

WORKFLOW_ID = "reproduction-experiment-local-experimental"


def _seed_forward(database: InMemoryDatabase) -> None:
    _seed_publication(database)
    now = datetime(2026, 8, 18, tzinfo=UTC)
    database.workflow_definition_versions[(WORKFLOW_ID, "0.7.0")] = WorkflowDefinitionVersion(
        WORKFLOW_ID, GENERIC_EXPERIMENT_V5_WORKFLOW_VERSION,
        GENERIC_EXPERIMENT_V5_CONTRACT_CHECKSUM, "selected-research-idea/v1",
        GENERIC_EXPERIMENT_V5_ARTIFACT_TYPE,
        {
            "default_project_setup": False,
            "capability_interface": "reagent.experiment-capability/v0.1",
            "bounded_scientific_evidence_schema":
                "reagent.experiment-bounded-scientific-evidence/v0.1",
            "artifact_outputs": [{"artifact_type": GENERIC_EXPERIMENT_V5_ARTIFACT_TYPE}],
        },
        WorkflowReviewStatus.REVIEWED, CoreCapabilityMaturity.REVIEWED_CORE,
        now, now, now,
    )
    database.workflow_capsule_versions[(
        GENERIC_EXPERIMENT_V5_CAPSULE_ID, GENERIC_EXPERIMENT_V5_CAPSULE_VERSION,
    )] = WorkflowCapsuleVersion(
        GENERIC_EXPERIMENT_V5_CAPSULE_ID, GENERIC_EXPERIMENT_V5_CAPSULE_VERSION,
        WORKFLOW_ID, GENERIC_EXPERIMENT_V5_WORKFLOW_VERSION,
        GENERIC_EXPERIMENT_V5_CAPSULE_CHECKSUM, 0, "application/zip",
        ("inputs", "outputs", "memory"),
        ("experiment.capability/v0.1", "network.no-egress/v0.1"),
        {
            "package_template_id": "reproduction-experiment-scaffold-package-experimental",
            "package_schema_version": "workflow-package/v0.1",
            "trust_classification": "TRUSTED_BUILT_IN_UNSIGNED",
            "skill_pins": [{"skill_id": REFERENCE_CAPABILITY_SKILL.skill_id}],
        },
        WorkflowReviewStatus.REVIEWED, False, now, now,
    )
    database.workflow_skill_pins[(WORKFLOW_ID, "0.7.0", 0)] = (
        WorkflowDefinitionVersionSkillPin(
            WORKFLOW_ID, "0.7.0", 0, REFERENCE_CAPABILITY_SKILL.skill_id,
            REFERENCE_CAPABILITY_SKILL.version, REFERENCE_CAPABILITY_SKILL.content_checksum,
            REFERENCE_CAPABILITY_SKILL.purpose, now,
        )
    )
    database.workflow_artifact_requirements[(WORKFLOW_ID, "0.7.0", "research_idea")] = (
        WorkflowArtifactRequirement(
            WORKFLOW_ID, "0.7.0", "research_idea", "selected-research-idea/v1",
            CompatibilityMode.EXACT, "selected-research-idea/v1", 1, 1, True,
            MaterializationMode.VERIFIED_COPY, "inputs/selected-research-idea.json",
            now, now,
        )
    )


def test_public_workspace_materializes_one_v5_artifact_without_presentation_lookup(
    tmp_path: Path,
) -> None:
    database = InMemoryDatabase()
    uow_factory = lambda: InMemoryUnitOfWork(database)
    app = create_app(ApplicationContainer(
        unit_of_work_factory=uow_factory,
        local_package_root=str(tmp_path / "packages"),
    ))
    client = TestClient(app)
    project = client.post("/projects", json={
        "name": "EP-D0 disposable Workspace",
        "research_topic": "Materializable bounded scientific evidence",
        "selected_workflow": "LITERATURE_SEARCH",
    }).json()
    project_id = project["project_id"]
    _seed_forward(database)
    catalog = client.get(f"/workflow-definitions/{WORKFLOW_ID}").json()
    assert catalog["recommended_version"]["version"] == "0.8.0"

    created = client.post(f"/projects/{project_id}/workflow-instances", json={
        "workflow_definition_id": WORKFLOW_ID,
        "workflow_version": GENERIC_EXPERIMENT_V5_WORKFLOW_VERSION,
        "capsule_id": GENERIC_EXPERIMENT_V5_CAPSULE_ID,
        "capsule_version": GENERIC_EXPERIMENT_V5_CAPSULE_VERSION,
        "base_revision": 1,
    })
    assert created.status_code == 201, created.text
    experiment = created.json()
    descriptor = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
    workspace = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=descriptor)
    transport = _Transport(client)
    assert workspace_cli.sync_workspace(workspace_root=workspace, transport=transport).status == "SYNCED"
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    installed = {
        item["workflow_instance_id"]: item for item in lock["installed_capsules"]
    }
    forward = installed[experiment["workflow_instance_id"]]
    assert (forward["workflow_definition_version"], forward["capsule_version"]) == (
        "0.7.0", "0.10.0",
    )
    producer = next(
        item for item in lock["installed_capsules"]
        if item["workflow_definition_id"] == "literature-search-local-experimental"
    )

    idea, _ = _selected()
    idea_artifact = _seed_upstream(
        uow_factory=uow_factory, project_id=project_id, instance=producer,
        root=workspace / producer["relative_path"], artifact_type="selected-research-idea/v1",
        content=idea, character="d",
    )
    bound = client.post(
        f"/projects/{project_id}/workflow-instances/{experiment['workflow_instance_id']}/artifact-dependencies",
        json={
            "requirement_key": "research_idea", "artifact_id": idea_artifact["artifact_id"],
            "idempotency_key": str(uuid4()),
        },
    )
    assert bound.status_code == 201, bound.text
    workspace_cli.refresh_artifact_index(workspace_root=workspace, transport=transport)
    assert workspace_cli.materialize_artifacts(
        workspace_root=workspace,
        consumer_workflow_instance_id=experiment["workflow_instance_id"],
        transport=transport,
    ).materialized_count == 1

    lifecycle, evaluated = _result()
    assert isinstance(evaluated, CapabilityEvaluationResult)
    source = (EvidenceSourceRef(
        EvidenceSourceKind.RESULT_PAYLOAD, "result-payload",
        evaluated.receipt.result_payload_checksum,
    ),)
    record = finalize_experiment_record_v5(lifecycle, evaluated, (
        ScientificEvidenceBlock(
            "evidence-downstream-readable", EvidenceKind.PROSE, "Bounded finding",
            "Three controlled archival statements remained concordant.", source,
        ),
    ))
    v5_artifact = _seed_upstream(
        uow_factory=uow_factory, project_id=project_id, instance=experiment,
        root=workspace / forward["relative_path"], artifact_type="experiment-record/v5",
        content=record.to_dict(), character="e",
    )

    # A test-only exact downstream role uses the ordinary verified-copy handoff.
    now = datetime(2026, 8, 18, tzinfo=UTC)
    consumer_version = producer["workflow_definition_version"]
    database.workflow_artifact_requirements[(
        producer["workflow_definition_id"], consumer_version, "experiment_evidence_test",
    )] = WorkflowArtifactRequirement(
        producer["workflow_definition_id"], consumer_version,
        "experiment_evidence_test", "experiment-record/v5", CompatibilityMode.EXACT,
        "experiment-record/v5", 0, 1, False, MaterializationMode.VERIFIED_COPY,
        "inputs/experiment-record-v5.json", now, now,
    )
    bound = client.post(
        f"/projects/{project_id}/workflow-instances/{producer['workflow_instance_id']}/artifact-dependencies",
        json={
            "requirement_key": "experiment_evidence_test",
            "artifact_id": v5_artifact["artifact_id"], "idempotency_key": str(uuid4()),
        },
    )
    assert bound.status_code == 201, bound.text
    # Exercise the copied public Workspace command against a real loopback API.
    with _loopback_server(app) as api_url:
        root_cli = workspace / "reagent_local.py"
        refresh = subprocess.run(
            [sys.executable, str(root_cli), "artifact", "refresh", ".", "--api-url", api_url, "--json"],
            cwd=workspace, capture_output=True, text=True, check=False,
        )
        assert refresh.returncode == 0, refresh.stderr
        commands = []
        for _ in range(2):
            current = subprocess.run(
                [
                    sys.executable, str(root_cli), "artifact", "materialize", ".",
                    "--workflow-instance", producer["workflow_instance_id"],
                    "--api-url", api_url, "--json",
                ],
                cwd=workspace, capture_output=True, text=True, check=False,
            )
            assert current.returncode == 0, current.stderr
            commands.append(json.loads(current.stdout))
    assert commands[0]["status"] == commands[1]["status"] == "MATERIALIZED"
    target = workspace / producer["relative_path"] / "inputs/experiment-record-v5.json"
    value = validate_experiment_record_v5(json.loads(target.read_text()))
    assert value["bounded_scientific_evidence"]["blocks"][0]["value"].startswith("Three")
    assert value["lifecycle_record"]["methodology"]["claim_boundaries"]
    assert "presentation_payload" not in value
