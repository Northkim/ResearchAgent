from __future__ import annotations

import json
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api import ApplicationContainer, create_app
from backend.artifact_references.contracts import (
    CompatibilityMode, MaterializationMode, WorkflowArtifactRequirement,
)
from backend.artifact_references.tests.test_research_flow_contracts import _selected
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.contracts import (
    CoreCapabilityMaturity, WorkflowCapsuleVersion, WorkflowDefinitionVersion,
    WorkflowDefinitionVersionSkillPin, WorkflowReviewStatus,
)
from backend.project_workspaces.tests.test_f1b_full_scaffold_flow import _seed_upstream
from backend.project_workspaces.tests.test_real_experiment_workspace import _Transport
from backend.workflow_packages.generic_experiment_publication import (
    GENERIC_EXPERIMENT_CAPSULE_CHECKSUM, GENERIC_EXPERIMENT_CAPSULE_ID,
    GENERIC_EXPERIMENT_CAPSULE_VERSION, GENERIC_EXPERIMENT_CONTRACT_CHECKSUM,
    GENERIC_EXPERIMENT_WORKFLOW_VERSION, REFERENCE_CAPABILITY_SKILL,
)

WORKFLOW_ID = "reproduction-experiment-local-experimental"


def _seed_publication(database: InMemoryDatabase) -> None:
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    database.workflow_definition_versions[(WORKFLOW_ID, "0.6.0")] = WorkflowDefinitionVersion(
        WORKFLOW_ID, "0.6.0", GENERIC_EXPERIMENT_CONTRACT_CHECKSUM,
        "selected-research-idea/v1", "experiment-record/v4",
        {
            "default_project_setup": True,
            "capability_interface": "reagent.experiment-capability/v0.1",
            "artifact_outputs": [{"artifact_type": "experiment-record/v4"}],
        },
        WorkflowReviewStatus.REVIEWED, CoreCapabilityMaturity.REVIEWED_CORE,
        now, now, now,
    )
    database.workflow_capsule_versions[(GENERIC_EXPERIMENT_CAPSULE_ID, "0.9.0")] = WorkflowCapsuleVersion(
        GENERIC_EXPERIMENT_CAPSULE_ID, "0.9.0", WORKFLOW_ID, "0.6.0",
        GENERIC_EXPERIMENT_CAPSULE_CHECKSUM, 0, "application/zip",
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
    definition = REFERENCE_CAPABILITY_SKILL.definition(now)
    version = REFERENCE_CAPABILITY_SKILL.skill_version(now)
    database.skill_definitions[definition.skill_id] = definition
    database.skill_versions[(version.skill_id, version.skill_version)] = version
    pin = WorkflowDefinitionVersionSkillPin(
        WORKFLOW_ID, "0.6.0", 0, version.skill_id, version.skill_version,
        version.content_checksum, REFERENCE_CAPABILITY_SKILL.purpose, now,
    )
    database.workflow_skill_pins[(WORKFLOW_ID, "0.6.0", 0)] = pin
    requirement = WorkflowArtifactRequirement(
        WORKFLOW_ID, "0.6.0", "research_idea", "selected-research-idea/v1",
        CompatibilityMode.EXACT, "selected-research-idea/v1", 1, 1, True,
        MaterializationMode.VERIFIED_COPY, "inputs/selected-research-idea.json",
        now, now,
    )
    database.workflow_artifact_requirements[(WORKFLOW_ID, "0.6.0", "research_idea")] = requirement


def _fake_codex(path: Path) -> Path:
    proposal = {
        key: ["Bounded generic declaration."]
        for key in (
            "questions_or_hypotheses", "inputs_or_materials", "protocol",
            "observations_or_outputs", "evaluation_criteria",
            "reproducibility_controls", "resource_constraints",
            "compute_constraints", "assumptions", "claim_boundaries",
        )
    }
    proposal.update({
        "questions_or_hypotheses": ["Does nearest classification retain accuracy on Wine?"],
        "inputs_or_materials": ["Wine classification material."],
        "protocol": ["Nearest neighbor with stratified assessment."],
        "evaluation_criteria": ["Accuracy is reviewed."],
        "network_policy": "DISABLED", "unresolved_material_decisions": [],
    })
    source = (
        f"#!{sys.executable}\n"
        "import json\n"
        "from pathlib import Path\n"
        f"value={proposal!r}\n"
        "Path('memory/methodology-proposal.json').write_text(json.dumps(value,sort_keys=True,separators=(',',':'))+'\\n')\n"
    )
    path.write_text(source, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_catalog_sync_materialize_public_checkpoint_and_durable_resume(tmp_path: Path) -> None:
    database = InMemoryDatabase()
    uow_factory = lambda: InMemoryUnitOfWork(database)
    client = TestClient(create_app(ApplicationContainer(
        unit_of_work_factory=uow_factory,
        local_package_root=str(tmp_path / "packages"),
    )))
    project = client.post("/projects", json={
        "name": "GEN-C isolated qualification",
        "research_topic": "Controlled generic local computation",
        "selected_workflow": "LITERATURE_SEARCH",
    }).json()
    project_id = project["project_id"]
    _seed_publication(database)
    detail = client.get(f"/workflow-definitions/{WORKFLOW_ID}").json()
    assert detail["recommended_version"]["version"] == "0.8.0"
    assert detail["recommended_capsule"]["capsule_version"] == "0.11.0"
    assert detail["recommended_version"]["output_schema_id"] == "experiment-record/v5"
    assert any(item["version"] == "0.6.0" for item in detail["versions"])

    created = client.post(f"/projects/{project_id}/workflow-instances", json={
        "workflow_definition_id": WORKFLOW_ID,
        "workflow_version": GENERIC_EXPERIMENT_WORKFLOW_VERSION,
        "capsule_id": GENERIC_EXPERIMENT_CAPSULE_ID,
        "capsule_version": GENERIC_EXPERIMENT_CAPSULE_VERSION,
        "base_revision": 1,
    })
    assert created.status_code == 201, created.text
    experiment = created.json()
    descriptor = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
    workspace = tmp_path / "workspace"
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=descriptor)
    transport = _Transport(client)
    synced = workspace_cli.sync_workspace(workspace_root=workspace, transport=transport)
    assert synced.status == "SYNCED"
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    installed = next(
        item for item in lock["installed_capsules"]
        if item["workflow_instance_id"] == experiment["workflow_instance_id"]
    )
    assert (installed["workflow_definition_version"], installed["capsule_version"]) == ("0.6.0", "0.9.0")
    capsule = workspace / installed["relative_path"]
    manifest = json.loads((capsule / "package-manifest.json").read_text())
    assert manifest["skill_pins"][0]["name"] == REFERENCE_CAPABILITY_SKILL.skill_id

    literature = next(
        item for item in lock["installed_capsules"]
        if item["workflow_definition_id"] == "literature-search-local-experimental"
    )
    selected_idea, _ = _selected()
    selected_idea["selected_idea"]["title"] = "Wine nearest classification"
    selected_idea["selected_idea"]["research_question"] = (
        "Does nearest classification retain accuracy on Wine?"
    )
    artifact = _seed_upstream(
        uow_factory=uow_factory, project_id=project_id, instance=literature,
        root=workspace / literature["relative_path"],
        artifact_type="selected-research-idea/v1", content=selected_idea,
        character="d",
    )
    bound = client.post(
        f"/projects/{project_id}/workflow-instances/{experiment['workflow_instance_id']}/artifact-dependencies",
        json={
            "requirement_key": "research_idea", "artifact_id": artifact["artifact_id"],
            "idempotency_key": str(uuid4()),
        },
    )
    assert bound.status_code == 201, bound.text
    workspace_cli.refresh_artifact_index(workspace_root=workspace, transport=transport)
    materialized = workspace_cli.materialize_artifacts(
        workspace_root=workspace,
        consumer_workflow_instance_id=experiment["workflow_instance_id"],
        transport=transport,
    )
    assert materialized.materialized_count == 1
    assert workspace_cli.run_workflow(
        workspace_root=workspace,
        workflow_instance_id=experiment["workflow_instance_id"],
        transport=transport, api_url="http://127.0.0.1",
        preflight_only=True,
    ).status == "PREFLIGHT_READY"

    fake = _fake_codex(tmp_path / "fake-codex")
    first = workspace_cli.run_workflow(
        workspace_root=workspace,
        workflow_instance_id=experiment["workflow_instance_id"],
        transport=transport, api_url="http://127.0.0.1",
        codex_executable=str(fake),
    )
    assert first.status == "DESIGN_APPROVAL_REQUIRED"
    checkpoint_bytes = (capsule / "memory/generic-checkpoint.json").read_bytes()
    assert not (capsule / "memory/preparation").exists()
    fake.unlink()
    with pytest.raises(workspace_cli.WorkspaceCLIError) as error:
        workspace_cli.run_workflow(
            workspace_root=workspace,
            workflow_instance_id=experiment["workflow_instance_id"],
            transport=transport, api_url="http://127.0.0.1",
            codex_executable=str(tmp_path / "missing-codex"),
        )
    assert error.value.code == "CODEX_UNAVAILABLE"
    assert (capsule / "memory/generic-checkpoint.json").read_bytes() == checkpoint_bytes
