from __future__ import annotations

import json
import runpy
import shutil
import subprocess
from pathlib import Path

import pytest

from backend.cloud_api_proxy.contracts import PaperSearchV01Request
from backend.cloud_api_proxy.fake_adapter import DeterministicFakePaperSearchAdapter
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.tests.test_progress_backlog_recovery import (
    INSTANCE_ID,
    PROJECT_ID,
    WORKSPACE_ID,
    _ProgressTransport,
)
from backend.project_workspaces.tests.test_sync import (
    _DemoClientTransport,
    _literature_capsule,
    _synced_full_research_workspace,
)
from backend.workflow_packages.production_workflows import (
    build_literature_search_v0_8_package,
)
from backend.workflow_packages.tests import fake_codex_cli


FAKE_CODEX = Path(fake_codex_cli.__file__).resolve()
HASH = "sha256:" + "a" * 64


def _fixture(tmp_path: Path) -> tuple[Path, Path, dict, dict, dict, dict, Path]:
    workspace = tmp_path / "workspace"
    capsule = build_literature_search_v0_8_package(
        project_id=PROJECT_ID,
        project_name="Checkpoint fixture",
        research_topic="Durable human review",
        output_root=workspace / "capsule-build",
        package_id="literature-checkpoint-fixture",
    ).package_root
    manifest = json.loads((capsule / "package-manifest.json").read_text())
    descriptor = {"project_id": PROJECT_ID, "workspace_id": WORKSPACE_ID}
    installed = {
        "workflow_instance_id": INSTANCE_ID,
        "workflow_definition_id": manifest["workflow_id"],
        "workflow_definition_version": manifest["workflow_version"],
        "capsule_version": manifest["package_template_version"],
        "relative_path": capsule.relative_to(workspace).as_posix(),
    }
    runtime = runpy.run_path(str(capsule / "legacy_reagent_local.py"))
    runtime["_initialize_control"](
        root=capsule,
        manifest=manifest,
        mode="DEMO",
        execution_style="INTERACTIVE",
    )
    fake_codex_cli.plan(capsule)
    runtime["_mark_plan_confirmed"](capsule)
    _write_results(capsule, runtime, manifest)
    runtime["_mark_search_completed"](capsule)
    control = runtime["_load_control"](capsule, manifest)
    executable = tmp_path / "fake-codex"
    shutil.copy2(FAKE_CODEX, executable)
    executable.chmod(0o755)
    return workspace, capsule, descriptor, installed, manifest, control, executable


def _write_results(capsule: Path, runtime: dict, manifest: dict) -> None:
    adapter = DeterministicFakePaperSearchAdapter()
    queries = runtime["_validate_query_plan"](
        capsule,
        json.loads((capsule / "inputs/research_request.json").read_text())["topic"],
    )
    for item in queries:
        provider_data = adapter.search(
            PaperSearchV01Request(query=item["query"], max_results=5)
        )
        result = {
            "schema_version": "literature-search-normalized-query-result/v0.1",
            "mode": "DEMO",
            "query_id": item["query_id"],
            "issued_query": item["query"],
            "operation_id": "proxyop-v1-" + item["query_id"][-1] * 64,
            "request_content_checksum": HASH,
            "provider_data_checksum": HASH,
            "response_content_checksum": HASH,
            "provider_adapter": {"adapter_id": runtime["FAKE_ADAPTER_ID"]},
            "usage": {"provider_http_calls": 1, "reported_cost_microusd": 0},
            "provider_data": provider_data,
        }
        path = capsule / "memory/search/operations" / f"{item['query_id']}.result.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")


def _stub_upload(receipt_id: str):
    """Simulate the runtime's bounded upload while persisting the exact local
    receipt contract so the Capsule validator stays authoritative."""

    def upload(**kwargs) -> dict:
        report = json.loads(kwargs["report_path"].read_text())
        receipt = {
            "schema_version": "local-progress-upload-receipt/v0.1",
            "report_id": report["report_id"],
            "report_checksum": report["report_checksum"],
            "receipt_id": receipt_id,
            "receipt_checksum": "sha256:" + "b" * 64,
            "validation_status": "ACCEPTED",
            "chain_state": "HEAD",
            "accepted_for_projection": True,
            "idempotent_replay": False,
            "projection_checksum": "sha256:" + "d" * 64,
            "verified_at": "2026-08-21T00:00:00Z",
        }
        target = kwargs["root"] / "memory/progress/receipts" / f"{report['report_id']}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n"
        )
        return receipt

    return upload


def test_screening_checkpoint_survives_long_owner_dwell_and_resume(
    tmp_path: Path,
) -> None:
    workspace, capsule, descriptor, installed, manifest, control, executable = _fixture(tmp_path)
    root, pending = workspace_cli._prepare_literature_synthesis_checkpoint(
        workspace=workspace,
        descriptor=descriptor,
        installed=installed,
        capsule=capsule,
        manifest=manifest,
        runtime=runpy.run_path(str(capsule / "legacy_reagent_local.py")),
        control=control,
        codex_executable=str(executable),
    )
    assert pending["phase"] == "SCREENING_DECISION_REQUIRED"
    assert pending["decision_revision"] == 0

    # The interactive screening phase recorded the Owner's exact dispositions
    # in the conversation; the coordinator validates and persists them after
    # the Harness has exited, so Owner dwell never holds the Harness.
    decisions = workspace_cli._literature_proposed_decisions(root)
    approved = workspace_cli._write_literature_checkpoint(root, {
        **pending,
        "phase": "FINALIZATION_DECISION_REQUIRED",
        "decision_revision": 1,
        "decisions": decisions,
        "staged_files": workspace_cli._literature_staged_files(root),
    })
    assert approved["phase"] == "FINALIZATION_DECISION_REQUIRED"
    exact = list(approved["decisions"])

    original = workspace_cli._managed_harness
    workspace_cli._managed_harness = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("resume repeated the interactive screening phase")
    )
    try:
        _root, resumed = workspace_cli._prepare_literature_synthesis_checkpoint(
            workspace=workspace,
            descriptor=descriptor,
            installed=installed,
            capsule=capsule,
            manifest=manifest,
            runtime=runpy.run_path(str(capsule / "legacy_reagent_local.py")),
            control=control,
            codex_executable=str(executable),
        )
    finally:
        workspace_cli._managed_harness = original
    assert resumed["decisions"] == exact
    assert resumed["candidate_set_checksum"] == pending["candidate_set_checksum"]


def test_pending_screening_checkpoint_resumes_without_fabricated_approval(
    tmp_path: Path,
) -> None:
    workspace, capsule, descriptor, installed, manifest, control, executable = _fixture(tmp_path)
    root, pending = workspace_cli._prepare_literature_synthesis_checkpoint(
        workspace=workspace,
        descriptor=descriptor,
        installed=installed,
        capsule=capsule,
        manifest=manifest,
        runtime=runpy.run_path(str(capsule / "legacy_reagent_local.py")),
        control=control,
        codex_executable=str(executable),
    )
    reloaded = workspace_cli._read_literature_checkpoint(
        root, descriptor=descriptor, installed=installed, manifest=manifest
    )
    assert reloaded is not None
    assert reloaded["phase"] == "SCREENING_DECISION_REQUIRED"
    assert reloaded["decisions"] == []
    assert reloaded["decision_revision"] == 0


def test_provider_is_released_before_screening_wait_and_queries_do_not_repeat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace, capsule, descriptor, installed, manifest, _control, executable = _fixture(tmp_path)
    runtime = runpy.run_path(str(capsule / "legacy_reagent_local.py"))
    control = runtime["_load_control"](capsule, manifest)
    control["state"] = "PLAN_CONFIRMED"
    control["last_completed_state"] = "PLAN_CONFIRMED"
    control["search_result_checksums"] = []
    runtime["_write_control"](capsule, control)
    for path in (capsule / "memory/search/operations").glob("*.result.json"):
        path.unlink()

    calls = {"open": 0, "execute": 0, "close": 0}

    runtime["_check_backend"] = lambda _url: None
    runtime["_open_session"] = lambda **kwargs: (
        calls.__setitem__("open", calls["open"] + 1)
        or {"session_id": "session", "session_token": "token"}
    )

    def execute(**kwargs):
        calls["execute"] += 1
        _write_results(capsule, runtime, manifest)

    runtime["_execute_queries"] = execute
    runtime["_cleanup_session"] = lambda **kwargs: calls.__setitem__(
        "close", calls["close"] + 1
    )
    real_run_path = workspace_cli.runpy.run_path

    def run_path(path, *args, **kwargs):
        if Path(path) == capsule / "legacy_reagent_local.py":
            return runtime
        return real_run_path(path, *args, **kwargs)

    monkeypatch.setattr(workspace_cli.runpy, "run_path", run_path)
    transport = _ProgressTransport()

    first = workspace_cli._advance_literature_checkpoint_workflow(
        workspace=workspace,
        descriptor=descriptor,
        installed=installed,
        capsule=capsule,
        manifest=manifest,
        transport=transport,
        api_url="http://127.0.0.1:8000",
        mode="DEMO",
        codex_executable=str(executable),
        decision_input=lambda _prompt: "approve",
    )
    assert first["status"] == "COMPLETED"
    assert calls == {"open": 1, "execute": 1, "close": 1}

    runtime["_open_session"] = lambda **kwargs: (_ for _ in ()).throw(
        AssertionError("completed queries were repeated on replay")
    )
    replay = workspace_cli._advance_literature_checkpoint_workflow(
        workspace=workspace,
        descriptor=descriptor,
        installed=installed,
        capsule=capsule,
        manifest=manifest,
        transport=transport,
        api_url="http://127.0.0.1:8000",
        mode="DEMO",
        codex_executable=str(executable),
        decision_input=lambda _prompt: "approve",
    )
    assert replay["status"] == "COMPLETED"
    assert calls["execute"] == 1


def test_active_managed_harness_timeout_remains_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        workspace_cli.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(args[0], kwargs["timeout"])
        ),
    )
    with pytest.raises(
        workspace_cli.OwnerCheckpointInvalid, match="active-work time limit"
    ):
        workspace_cli._managed_harness(
            tmp_path,
            "/safe/codex",
            "bounded active work",
            environment={},
            timeout_seconds=1,
        )


def test_synthesis_staged_context_carries_authoritative_contracts(
    tmp_path: Path,
) -> None:
    workspace, capsule, descriptor, installed, manifest, control, executable = _fixture(tmp_path)
    root, checkpoint = workspace_cli._prepare_literature_synthesis_checkpoint(
        workspace=workspace,
        descriptor=descriptor,
        installed=installed,
        capsule=capsule,
        manifest=manifest,
        runtime=runpy.run_path(str(capsule / "legacy_reagent_local.py")),
        control=control,
        codex_executable=str(executable),
    )
    staged = root / "staged"
    for relative in workspace_cli.LITERATURE_STAGED_SCHEMA_CONTRACTS:
        assert (staged / relative).read_bytes() == (capsule / relative).read_bytes()
        recorded = next(
            item for item in checkpoint["staged_files"]
            if item["relative_path"] == "staged/" + relative
        )
        assert recorded["checksum"] == workspace_cli.sha256_bytes(
            (staged / relative).read_bytes()
        )
    assert (staged / "validate_package.py").read_bytes() == (
        capsule / "validate_package.py"
    ).read_bytes()
    proposal_schema = json.loads(
        (staged / "workflow/schemas/proposed-screening.schema.json").read_text()
    )
    assert proposal_schema == workspace_cli.LITERATURE_PROPOSED_SCREENING_SCHEMA
    instruction = workspace_cli._literature_screening_instruction("DEMO")
    assert "workflow/schemas/candidate-papers.schema.json" in instruction
    assert "workflow/schemas/proposed-screening.schema.json" in instruction
    assert "do" in instruction and "execute it" in instruction

    # Drift guard: the staged proposal schema is derived from the same exact
    # field/disposition constants the coordinator validator enforces.
    schema = workspace_cli.LITERATURE_PROPOSED_SCREENING_SCHEMA
    assert schema["additionalProperties"] is False
    assert schema["required"] == sorted(
        workspace_cli.LITERATURE_PROPOSED_SCREENING_FIELDS
    )
    items = schema["properties"]["decisions"]["items"]
    assert items["additionalProperties"] is False
    assert items["required"] == sorted(
        workspace_cli.LITERATURE_PROPOSAL_DECISION_FIELDS
    )
    assert items["properties"]["disposition"]["enum"] == list(
        workspace_cli.LITERATURE_PROPOSAL_DISPOSITIONS
    )
    assert (
        schema["properties"]["schema_version"]["const"]
        == workspace_cli.LITERATURE_PROPOSED_SCREENING_SCHEMA_VERSION
    )


def test_proposal_exact_contract_accepts_conforming_and_rejects_extra_or_missing(
    tmp_path: Path,
) -> None:
    workspace, capsule, descriptor, installed, manifest, control, executable = _fixture(tmp_path)
    root, _pending = workspace_cli._prepare_literature_synthesis_checkpoint(
        workspace=workspace,
        descriptor=descriptor,
        installed=installed,
        capsule=capsule,
        manifest=manifest,
        runtime=runpy.run_path(str(capsule / "legacy_reagent_local.py")),
        control=control,
        codex_executable=str(executable),
    )
    proposal_path = root / "staged/memory/proposed-screening.json"
    original = json.loads(proposal_path.read_text())
    assert set(original) == {"schema_version", "decisions"}
    candidates = json.loads(
        (root / "staged/outputs/candidate_papers.json").read_text()
    )["candidates"]
    assert len(original["decisions"]) == len(candidates)

    # C: a conforming exact proposal is accepted.
    accepted = workspace_cli._literature_proposed_decisions(root)
    assert len(accepted) == len(candidates)

    # D: additional forbidden fields fail closed (top-level and entry level).
    extra_top = {**original, "mode": "DEMO"}
    workspace_cli._atomic_write_json(proposal_path, extra_top)
    with pytest.raises(
        workspace_cli.WorkspaceCLIError, match="proposal fields are invalid"
    ):
        workspace_cli._literature_proposed_decisions(root)
    extra_entry = {
        **original,
        "decisions": [
            {**item, "generated_at": "2026-08-20T00:00:00Z"}
            for item in original["decisions"]
        ],
    }
    workspace_cli._atomic_write_json(proposal_path, extra_entry)
    with pytest.raises(
        workspace_cli.WorkspaceCLIError,
        match="proposal entry fields are invalid",
    ):
        workspace_cli._literature_proposed_decisions(root)

    # E: missing required fields fail closed (top-level and entry level).
    missing_decisions = {"schema_version": original["schema_version"]}
    workspace_cli._atomic_write_json(proposal_path, missing_decisions)
    with pytest.raises(
        workspace_cli.WorkspaceCLIError, match="proposal fields are invalid"
    ):
        workspace_cli._literature_proposed_decisions(root)
    missing_reason = {
        **original,
        "decisions": [
            {"candidate_id": item["candidate_id"], "disposition": item["disposition"]}
            for item in original["decisions"]
        ],
    }
    workspace_cli._atomic_write_json(proposal_path, missing_reason)
    with pytest.raises(
        workspace_cli.WorkspaceCLIError,
        match="proposal entry fields are invalid",
    ):
        workspace_cli._literature_proposed_decisions(root)


def test_exact_checkpoint_finalizes_and_uploads_progress_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace, capsule, descriptor, installed, manifest, _control, executable = _fixture(tmp_path)
    runtime = runpy.run_path(str(capsule / "legacy_reagent_local.py"))
    runtime["_check_backend"] = lambda _url: None
    runtime["_open_session"] = lambda **kwargs: (_ for _ in ()).throw(
        AssertionError("SEARCH_COMPLETED recovery reopened Provider access")
    )
    real_run_path = workspace_cli.runpy.run_path

    def run_path(path, *args, **kwargs):
        if Path(path) == capsule / "legacy_reagent_local.py":
            return runtime
        return real_run_path(path, *args, **kwargs)

    monkeypatch.setattr(workspace_cli.runpy, "run_path", run_path)

    class Transport(_ProgressTransport):
        def __init__(self):
            super().__init__()
            self.declarations: list[list[dict]] = []

        def upload_progress_report(self, *args, **kwargs):
            envelope = args[4] if len(args) > 4 else kwargs["envelope"]
            self.declarations.append(list(envelope["artifact_declarations"]))
            return super().upload_progress_report(*args, **kwargs)

    transport = Transport()
    result = workspace_cli._advance_literature_checkpoint_workflow(
        workspace=workspace,
        descriptor=descriptor,
        installed=installed,
        capsule=capsule,
        manifest=manifest,
        transport=transport,
        api_url="http://127.0.0.1:8000",
        mode="DEMO",
        codex_executable=str(executable),
        decision_input=lambda _prompt: "approve",
    )
    assert result["status"] == "COMPLETED"
    assert transport.uploaded_rounds == [1, 2]
    assert transport.declarations[:1] == [[]]
    assert len(transport.declarations[1]) == 1
    assert transport.declarations[1][0]["artifact_type"] == "selected-paper-library/v1"
    root = workspace_cli._literature_checkpoint_root(workspace, INSTANCE_ID)
    reports = workspace_cli._validated_literature_checkpoint_reports(
        root, capsule, manifest
    )
    assert [item["status"] for item in reports] == [
        "IN_PROGRESS", "COMPLETED"
    ]
    assert workspace_cli._validated_local_progress_reports(capsule, manifest) == []
    # The immutable Capsule contract remains at its exact FINALIZED state;
    # coordinator-owned acknowledgements prove the three bounded Cloud uploads.
    assert runtime["_load_control"](capsule, manifest)["state"] == "FINALIZED"
    receipts = list(
        (workspace / workspace_cli.PROGRESS_RECEIPTS_ROOT / INSTANCE_ID).glob("*.json")
    )
    assert len(receipts) == 2
    owner = json.loads((capsule / "memory/owner-decisions.json").read_text())
    assert owner["decision_revision"] == 1
    assert owner["candidate_set_checksum"] == workspace_cli.sha256_bytes(
        (capsule / "outputs/candidate_papers.json").read_bytes()
    )
    artifacts = list(
        (capsule / "outputs/artifacts/selected-paper-library").glob("sha256-*.json")
    )
    assert len(artifacts) == 1

    replay = workspace_cli._advance_literature_checkpoint_workflow(
        workspace=workspace,
        descriptor=descriptor,
        installed=installed,
        capsule=capsule,
        manifest=manifest,
        transport=transport,
        api_url="http://127.0.0.1:8000",
        mode="DEMO",
        codex_executable=str(executable),
        decision_input=lambda _prompt: (_ for _ in ()).throw(
            AssertionError("completed replay requested another Owner decision")
        ),
    )
    assert replay["status"] == "COMPLETED"
    assert transport.uploaded_rounds == [1, 2]
    assert len(artifacts) == 1


def test_public_workspace_run_uses_one_attached_interactive_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace, _database, base_transport = _synced_full_research_workspace(
        tmp_path, enable_local_workflow_sessions=True
    )
    capsule, installed = _literature_capsule(workspace)
    runtime = runpy.run_path(str(capsule / "legacy_reagent_local.py"))
    runtime["_check_backend"] = lambda _url: None
    calls = {"open": 0, "execute": 0, "close": 0}
    runtime["_open_session"] = lambda **kwargs: (
        calls.__setitem__("open", calls["open"] + 1)
        or {"session_id": "controlled", "session_token": "controlled"}
    )

    def execute(**kwargs) -> None:
        calls["execute"] += 1
        _write_results(capsule, runtime, json.loads(
            (capsule / "package-manifest.json").read_text()
        ))

    runtime["_execute_queries"] = execute
    runtime["_cleanup_session"] = lambda **kwargs: calls.__setitem__(
        "close", calls["close"] + 1
    )
    runtime["_upload_with_fresh_session"] = _stub_upload("receipt-single-session")
    real_run_path = workspace_cli.runpy.run_path

    def run_path(path, *args, **kwargs):
        if Path(path) == capsule / "legacy_reagent_local.py":
            return runtime
        return real_run_path(path, *args, **kwargs)

    monkeypatch.setattr(workspace_cli.runpy, "run_path", run_path)
    monkeypatch.setenv("REAGENT_FAKE_CODEX_AUTO_CONFIRM", "1")
    executable = tmp_path / "public-fake-codex"
    shutil.copy2(FAKE_CODEX, executable)
    executable.chmod(0o755)
    project_id = json.loads((workspace / "project.json").read_text())["project_id"]

    harness_invocations: list[tuple[bool, str]] = []
    original_harness = workspace_cli._managed_harness

    def spy_harness(root, executable_path, instruction, *, environment,
                    timeout_seconds=None, interactive=False):
        harness_invocations.append((interactive, instruction))
        assert interactive is True
        return original_harness(
            root, executable_path, instruction, environment=environment,
            timeout_seconds=timeout_seconds, interactive=interactive,
        )

    monkeypatch.setattr(workspace_cli, "_managed_harness", spy_harness)

    class Transport(_DemoClientTransport):
        def workflow_instance_progress(self, project_id, workflow_instance_id):
            response = self.client.get(
                f"/projects/{project_id}/workflow-instances/"
                f"{workflow_instance_id}/progress",
                params={"offset": 0, "limit": 100},
            )
            assert response.status_code == 200, response.text
            return response.json()

        def upload_progress_report(
            self, project_id, workflow_instance_id, manifest, report, envelope
        ):
            identity = {
                "package_id": manifest["package_id"],
                "package_checksum": manifest["package_checksum"],
                "workflow_id": manifest["workflow_id"],
                "workflow_version": manifest["workflow_version"],
                "workflow_checksum": manifest["workflow_checksum"],
            }
            created = self.client.post(
                f"/projects/{project_id}/local-sessions",
                json={
                    **identity,
                    "mode": "UPLOAD_ONLY",
                    "execution_round": report["execution_round"],
                    "report_id": report["report_id"],
                    "report_content_checksum": report["report_content_checksum"],
                },
            )
            assert created.status_code == 201, created.text
            session = created.json()
            headers = {"Authorization": f"Bearer {session['session_token']}"}
            uploaded = self.client.post(
                f"/projects/{project_id}/local-sessions/{session['session_id']}"
                "/progress-reports",
                params={
                    "workflow_id": manifest["workflow_id"],
                    "workflow_version": manifest["workflow_version"],
                    "workflow_checksum": manifest["workflow_checksum"],
                },
                json=envelope,
                headers=headers,
            )
            assert uploaded.status_code in {200, 201}, uploaded.text
            closed = self.client.delete(
                f"/projects/{project_id}/local-sessions/{session['session_id']}",
                params=identity,
                headers=headers,
            )
            assert closed.status_code in {200, 204}, closed.text
            return uploaded.json()

    transport = Transport(base_transport.client)
    result = workspace_cli.run_workflow(
        workspace_root=workspace,
        workflow_instance_id=installed["workflow_instance_id"],
        transport=transport,
        api_url="http://127.0.0.1:8000",
        codex_executable=str(executable),
        mode="DEMO",
        consent_input=lambda _prompt: "approve",
    )

    assert result.status == "PROGRESS_SYNCHRONIZED"
    assert calls == {"open": 1, "execute": 1, "close": 1}
    assert len(harness_invocations) == 1
    interactive, instruction = harness_invocations[0]
    assert interactive is True
    assert "MVP-LS2 INTERACTIVE_ONE_ROUND" in instruction
    assert "AUTO_PLANNING_STAGE" not in instruction
    assert "AUTO_SYNTHESIS_STAGE" not in instruction
    assert "PLAN_CONFIRMED" in instruction
    assert "finish" in instruction
    control = runtime["_load_control"](capsule, json.loads(
        (capsule / "package-manifest.json").read_text()
    ))
    assert control["state"] == "UPLOADED"
    assert control["mode"] == "DEMO"
    assert control["candidate_review_confirmed"] is True
    assert control["finalization_confirmed"] is True
    assert control["plan_confirmation_count"] >= 1
    report_markdown = (capsule / "outputs/literature_search_report.md").read_text()
    assert "FICTIONAL DEMO EVIDENCE" in report_markdown
    progress = base_transport.client.get(
        f"/projects/{project_id}/workflow-instances/"
        f"{installed['workflow_instance_id']}/progress"
    )
    assert progress.status_code == 200, progress.text
    # The runtime's bounded upload is stubbed in this in-process test; the
    # real Cloud upload path is qualified separately against a loopback API.
    # Locally the exact selected-paper-library artifact must be published.
    reports = list((capsule / "memory/progress/reports").glob("prv2-*.json"))
    assert len(reports) == 1
    assert json.loads(reports[0].read_text())["status"] == "COMPLETED"
    artifacts = list(
        (capsule / "outputs/artifacts/selected-paper-library").glob("sha256-*.json")
    )
    assert len(artifacts) == 1
    selected = json.loads(artifacts[0].read_text())
    assert selected["schema"] == "selected-paper-library/v1"
