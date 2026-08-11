from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import httpx
import uvicorn

from backend.api import ApplicationContainer, create_app
from backend.api.deployment import DeploymentProfile, DeploymentSettings
from backend.cloud_api_proxy import (
    CloudAPIProxyService,
    InMemoryProxyDatabase,
    InMemoryProxyUnitOfWork,
    OpenAlexPaperSearchAdapter,
)
from backend.cloud_api_proxy.composition import ProxyApplicationContainer
from backend.cloud_api_proxy.tests.test_openalex_adapter import (
    ScriptedTransport,
    SyntheticCredentialSource,
    _response,
    _work,
)
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import workspace_cli
from backend.workflow_packages.production_workflows import (
    IDEA_DISCOVERY_WORKFLOW_ID,
    LITERATURE_SEARCH_WORKFLOW_ID,
)


SENTINEL = "synthetic-secret-sentinel"


@contextmanager
def _loopback_server(app):
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    server = uvicorn.Server(
        uvicorn.Config(app, log_level="critical", lifespan="on")
    )
    thread = threading.Thread(
        target=server.run,
        kwargs={"sockets": [listener]},
        daemon=True,
    )
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.01)
    if not server.started:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()
        raise RuntimeError("test API did not start")
    try:
        yield f"http://127.0.0.1:{listener.getsockname()[1]}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
        if thread.is_alive():
            raise RuntimeError("test API did not stop")


def _executable_copy(source: Path, target: Path) -> Path:
    shutil.copyfile(source, target)
    target.chmod(0o700)
    return target


def _artifact(client: httpx.Client, project_id: str, artifact_type: str) -> dict:
    response = client.get(
        f"/projects/{project_id}/artifacts",
        params={"artifact_type": artifact_type},
    )
    assert response.status_code == 200, response.text
    artifacts = response.json()["artifacts"]
    assert len(artifacts) == 1
    return artifacts[0]


def test_owner_normal_product_route_is_consent_bound_secret_isolated_and_hands_off_to_idea(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Qualify the real product route with the real adapter and no live network."""

    project_database = InMemoryDatabase()
    product = ApplicationContainer(
        unit_of_work_factory=lambda: InMemoryUnitOfWork(project_database),
        local_package_root=str(tmp_path / "cloud-packages"),
    )
    provider_transport = ScriptedTransport(
        [
            _response(results=[_work(index) for index in range(1, 4)]),
            _response(results=[_work(index) for index in range(1, 4)]),
        ]
    )
    credential = SyntheticCredentialSource(SENTINEL)
    adapter = OpenAlexPaperSearchAdapter(
        credential_source=credential,
        transport=provider_transport,
        clock=lambda: datetime(2026, 8, 11, tzinfo=UTC),
    )
    proxy_database = InMemoryProxyDatabase()
    proxy_service = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(proxy_database),
        adapters={adapter.adapter_id: adapter},
    )
    settings = DeploymentSettings(
        profile=DeploymentProfile.LOCAL_DEVELOPMENT,
        maximum_request_bytes=1024 * 1024,
        cors_allowed_origins=(),
        expose_api_docs=False,
        expose_legacy_hosted_routes=False,
    )
    app = create_app(
        product,
        proxy_container=ProxyApplicationContainer(service=proxy_service),
        enable_experimental_proxy=True,
        enable_local_workflow_sessions=True,
        deployment_settings=settings,
    )

    repository = Path(__file__).resolve().parents[3]
    literature_codex = _executable_copy(
        repository / "backend/workflow_packages/tests/fake_codex_cli.py",
        tmp_path / "normal-literature-codex",
    )
    idea_codex = _executable_copy(
        repository / "backend/workflow_packages/tests/fake_idea_codex_cli.py",
        tmp_path / "normal-idea-codex",
    )
    monkeypatch.setenv("REAGENT_OPENALEX_API_KEY", SENTINEL)
    monkeypatch.setenv("OPENALEX_API_KEY", SENTINEL)
    monkeypatch.setenv("REAGENT_CODEX_EXECUTABLE", str(literature_codex))

    with _loopback_server(app) as base_url, httpx.Client(
        base_url=base_url,
        timeout=30,
    ) as client:
        monkeypatch.setenv("REAGENT_LOCAL_BASE_URL", base_url)
        created = client.post(
            "/projects",
            json={
                "name": "Owner NORMAL offline qualification",
                "research_topic": "Multi-agent reinforcement learning for urban drainage systems",
                "selected_workflow": "LITERATURE_SEARCH",
                "workflow_setup": "full-research",
            },
        )
        assert created.status_code == 201, created.text
        project_id = created.json()["project_id"]
        instances_response = client.get(f"/projects/{project_id}/workflow-instances")
        assert instances_response.status_code == 200, instances_response.text
        instances = {
            item["workflow_definition_id"]: item
            for item in instances_response.json()["items"]
        }
        descriptor_response = client.get(f"/projects/{project_id}/workspace-bootstrap")
        assert descriptor_response.status_code == 200, descriptor_response.text
        workspace = tmp_path / "owner workspace with 空格"
        workspace_cli.bootstrap_workspace(
            target=workspace,
            descriptor=descriptor_response.json(),
        )
        transport = workspace_cli.HTTPWorkspaceSyncTransport(base_url)
        assert workspace_cli.sync_workspace(
            workspace_root=workspace,
            transport=transport,
        ).status == "SYNCED"

        literature = instances[LITERATURE_SEARCH_WORKFLOW_ID]
        literature_root = next(
            workspace / entry["relative_path"]
            for entry in json.loads(
                (workspace / workspace_cli.INSTALLED_LOCK).read_text()
            )["installed_capsules"]
            if entry["workflow_instance_id"] == literature["workflow_instance_id"]
        )
        driven = subprocess.run(
            [
                sys.executable,
                str(repository / "backend/workflow_packages/tests/interactive_e2e_driver.py"),
                "--workspace-root",
                str(workspace),
                "--capsule-root",
                str(literature_root),
                "--base-url",
                base_url,
            ],
            cwd=repository,
            env=dict(os.environ)
            | {
                "REAGENT_CODEX_EXECUTABLE": str(literature_codex),
                "REAGENT_LOCAL_BASE_URL": base_url,
            },
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )
        assert driven.returncode == 0, driven.stdout + driven.stderr
        assert adapter.invocation_count == 2
        assert credential.read_count == 2
        assert len(provider_transport.calls) == 2

        library = _artifact(client, project_id, "selected-paper-library/v1")
        lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
        roots = {
            entry["workflow_instance_id"]: workspace / entry["relative_path"]
            for entry in lock["installed_capsules"]
        }
        literature_root = roots[literature["workflow_instance_id"]]
        report = (literature_root / "outputs/literature_search_report.md").read_text()
        assert "REAL PROVIDER METADATA" in report
        assert "FICTIONAL DEMO EVIDENCE" not in report
        artifact_value = json.loads(
            (literature_root / library["relative_path"]).read_text()
        )
        assert len(artifact_value["papers"]) == 3
        assert all(
            item["paper"]["openalex_id"].startswith("W")
            for item in artifact_value["papers"]
        )

        idea = instances[IDEA_DISCOVERY_WORKFLOW_ID]
        binding = client.post(
            f"/projects/{project_id}/workflow-instances/"
            f"{idea['workflow_instance_id']}/artifact-dependencies",
            json={
                "requirement_key": "paper_library",
                "artifact_id": library["artifact_id"],
                "idempotency_key": "00000000-0000-4000-8000-000000000091",
            },
        )
        assert binding.status_code == 201, binding.text
        workspace_cli.refresh_artifact_index(
            workspace_root=workspace,
            transport=transport,
        )
        materialized = workspace_cli.materialize_artifacts(
            workspace_root=workspace,
            consumer_workflow_instance_id=idea["workflow_instance_id"],
            transport=transport,
        )
        assert materialized.materialized_count == 1
        monkeypatch.setenv("REAGENT_FAKE_IDEA_EXPLICIT_SELECTION", "1")
        idea_result = workspace_cli.run_workflow(
            workspace_root=workspace,
            workflow_instance_id=idea["workflow_instance_id"],
            transport=transport,
            api_url=base_url,
            codex_executable=str(idea_codex),
        )
        assert idea_result.status == "RUN_COMPLETED"
        selected_idea = _artifact(client, project_id, "selected-research-idea/v1")
        idea_root = roots[idea["workflow_instance_id"]]
        selected_value = json.loads(
            (idea_root / selected_idea["relative_path"]).read_text()
        )
        assert selected_value["selected_idea"]["status"] == "selected"
        assert selected_value["source_literature_artifact"]["artifact_id"] == library["artifact_id"]
        assert "Global novelty is not proven" in (
            idea_root / "outputs/idea_discovery_report.md"
        ).read_text()

    for path in workspace.rglob("*"):
        if path.is_file():
            assert SENTINEL.encode() not in path.read_bytes()
    assert all(
        operation.request.query_checksum.startswith("sha256:")
        and not hasattr(operation.request, "query")
        for operation in proxy_database.operations.values()
    )
