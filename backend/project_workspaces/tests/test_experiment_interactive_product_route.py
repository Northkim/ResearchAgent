from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

from backend.api import ApplicationContainer, create_app
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.tests.test_f1b_full_scaffold_flow import _seed_upstream
from backend.project_workspaces.tests.test_owner_real_research_gate import _loopback_server
from backend.workflow_packages.production_workflows import EXPERIMENT_WORKFLOW_ID


def _copy_executable(source: Path, target: Path) -> Path:
    shutil.copyfile(source, target)
    target.chmod(0o700)
    return target


def test_workspace_root_experiment_run_auto_starts_input_review_and_uploads_progress(
    tmp_path: Path,
) -> None:
    database = InMemoryDatabase()
    uow_factory = lambda: InMemoryUnitOfWork(database)
    app = create_app(ApplicationContainer(
        unit_of_work_factory=uow_factory,
        local_package_root=str(tmp_path / "cloud-packages"),
    ))
    repository = Path(__file__).resolve().parents[3]
    fake = _copy_executable(
        repository / "backend/workflow_packages/tests/fake_completing_scaffold_codex_cli.py",
        tmp_path / "codex-experiment-fixture",
    )
    sentinel = "experiment-secret-must-not-cross-harness"

    with _loopback_server(app) as base_url, httpx.Client(
        base_url=base_url, timeout=30
    ) as client:
        created = client.post("/projects", json={
                "name": "Experiment interactive product route",
                "research_topic": "Synthetic multi-agent stress testing",
                "selected_workflow": "LITERATURE_SEARCH",
                "workflow_setup": "custom",
                "custom_workflow_definition_ids": [
                    "literature-search-local-experimental",
                    "idea-discovery-local-experimental",
                    EXPERIMENT_WORKFLOW_ID,
                ],
            })
        assert created.status_code == 201, created.text
        project_id = created.json()["project_id"]
        instances = {
            item["workflow_definition_id"]: item
            for item in client.get(
                f"/projects/{project_id}/workflow-instances"
            ).json()["items"]
        }
        experiment = instances[EXPERIMENT_WORKFLOW_ID]
        assert (experiment["workflow_version"], experiment["capsule_version"]) == (
            "0.3.0", "0.5.0"
        )
        descriptor = client.get(
            f"/projects/{project_id}/workspace-bootstrap"
        ).json()
        workspace = tmp_path / "Experiment Workspace with 空格"
        workspace_cli.bootstrap_workspace(target=workspace, descriptor=descriptor)
        transport = workspace_cli.HTTPWorkspaceSyncTransport(base_url)
        assert workspace_cli.sync_workspace(
            workspace_root=workspace, transport=transport
        ).status == "SYNCED"
        lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
        roots = {
            item["workflow_instance_id"]: workspace / item["relative_path"]
            for item in lock["installed_capsules"]
        }
        idea = instances["idea-discovery-local-experimental"]
        idea_artifact = _seed_upstream(
            uow_factory=uow_factory,
            project_id=project_id,
            instance=idea,
            root=roots[idea["workflow_instance_id"]],
            artifact_type="selected-research-idea/v1",
            content={
                "schema": "selected-research-idea/v1",
                "core_capability_maturity": "REVIEWED_CORE",
                "source_candidate_ideas": {
                    "schema": "candidate-ideas/v0.1",
                    "relative_path": "outputs/candidate_ideas.json",
                    "sha256": "sha256:" + "a" * 64,
                },
                "source_literature_artifact": {
                    "artifact_id": "artifact-" + "3" * 32,
                    "artifact_type": "selected-paper-library/v1",
                    "sha256": "sha256:" + "b" * 64,
                },
                "selected_idea": {
                    "idea_id": "idea-003",
                    "title": "Stress-testing multi-agent control",
                    "research_question": "How can multi-agent control be stress-tested?",
                    "hypothesis": "Bounded perturbations expose coordination failures.",
                    "scope": "Synthetic scaffold qualification",
                    "baselines": ["Static controller"],
                    "metrics": ["Robustness"],
                    "literature_verification_caveats": ["No full text was reviewed"],
                },
            },
            character="e",
        )
        binding = client.post(
            f"/projects/{project_id}/workflow-instances/"
            f"{experiment['workflow_instance_id']}/artifact-dependencies",
            json={
                "requirement_key": "research_idea",
                "artifact_id": idea_artifact["artifact_id"],
                "idempotency_key": "00000000-0000-4000-8000-000000000119",
            },
        )
        assert binding.status_code == 201, binding.text
        input_setup = client.post(
            f"/projects/{project_id}/workflow-instances/"
            f"{experiment['workflow_instance_id']}/input-setup-decisions",
            json={
                "omitted_optional_requirement_keys": ["literature_library"],
                "idempotency_key": "00000000-0000-4000-8000-000000000120",
            },
        )
        assert input_setup.status_code == 201, input_setup.text
        workspace_cli.refresh_artifact_index(
            workspace_root=workspace, transport=transport
        )
        materialized = workspace_cli.materialize_artifacts(
            workspace_root=workspace,
            consumer_workflow_instance_id=experiment["workflow_instance_id"],
            transport=transport,
        )
        assert materialized.materialized_count == 1
        resource_projection = json.loads(
            (
                roots[experiment["workflow_instance_id"]]
                / "memory/resource-provenance.json"
            ).read_text()
        )
        assert [
            (item["requirement_key"], item["configured"], item["resolution_status"])
            for item in resource_projection["requirements"]
        ] == [
            ("source_repository", False, "UNCONFIGURED"),
            ("dataset", False, "UNCONFIGURED"),
            ("model", False, "UNCONFIGURED"),
            ("checkpoint", False, "UNCONFIGURED"),
        ]
        listing = workspace_cli.workflow_list(workspace)
        listed = next(
            item for item in listing["workflows"]
            if item["workflow_definition_id"] == EXPERIMENT_WORKFLOW_ID
        )
        assert listed["run_command"] == (
            "python reagent_local.py run . "
            "--workflow reproduction-experiment-local-experimental"
        )

        driven = subprocess.run(
            [
                sys.executable,
                str(repository / "backend/workflow_packages/tests/interactive_e2e_driver.py"),
                "--workspace-root", str(workspace),
                "--capsule-root", str(roots[experiment["workflow_instance_id"]]),
                "--workflow", EXPERIMENT_WORKFLOW_ID,
                "--base-url", base_url,
                "--expect-marker", "REAGENT REPRODUCTION & EXPERIMENT — INPUT_REVIEW",
            ],
            cwd=repository,
            env=dict(os.environ) | {
                "REAGENT_CODEX_EXECUTABLE": str(fake),
                "REAGENT_LOCAL_BASE_URL": base_url,
                "REAGENT_OPENALEX_API_KEY": sentinel,
                "REAGENT_DATABASE_URL": sentinel,
            },
            capture_output=True,
            text=True,
            check=False,
            timeout=90,
        )
        assert driven.returncode == 0, driven.stdout + driven.stderr
        assert "REAGENT REPRODUCTION & EXPERIMENT — INPUT_REVIEW" in driven.stdout
        assert "Current capability: SCAFFOLD_CORE" in driven.stdout
        assert sentinel not in driven.stdout + driven.stderr

        root = roots[experiment["workflow_instance_id"]]
        records = list(
            (root / "outputs/artifacts/experiment-record").glob("sha256-*.json")
        )
        assert len(records) == 1
        record = json.loads(records[0].read_text())
        assert record["execution_status"] == "PLACEHOLDER_NOT_EXECUTED"
        assert record["actual_results"] is None
        progress = client.get(
            f"/projects/{project_id}/workflow-instances/"
            f"{experiment['workflow_instance_id']}/progress"
        ).json()
        assert progress["history_total"] == 1
        assert progress["projection"]["latest_execution_round"] == 1
        assert progress["projection"]["research_status"] == "COMPLETED"
        for path in workspace.rglob("*"):
            if path.is_file():
                assert sentinel.encode() not in path.read_bytes()
