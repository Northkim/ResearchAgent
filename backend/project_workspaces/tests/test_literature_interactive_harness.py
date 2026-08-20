from __future__ import annotations

import json
import runpy
import shutil
from pathlib import Path

import pytest

from backend.project_workspaces import workspace_cli
from backend.project_workspaces.tests.test_literature_checkpoint_lifecycle import (
    _fixture,
    _stub_upload,
    _write_results,
)
from backend.project_workspaces.tests.test_sync import (
    _ClientTransport,
    _literature_capsule,
    _synced_full_research_workspace,
)
from backend.workflow_packages.tests import fake_codex_cli


def test_normal_literature_run_fails_closed_when_backend_offers_demo(
    tmp_path: Path,
) -> None:
    workspace, _descriptor, base_transport = _synced_full_research_workspace(
        tmp_path, enable_local_workflow_sessions=True
    )
    capsule, installed = _literature_capsule(workspace)

    class DemoT(_ClientTransport):
        def literature_execution_mode(self, project_id, package_identity):
            return {**package_identity, "mode": "DEMO"}

    transport = DemoT(base_transport.client)
    with pytest.raises(workspace_cli.WorkspaceCLIError) as error:
        workspace_cli.run_workflow(
            workspace_root=workspace,
            workflow_instance_id=installed["workflow_instance_id"],
            transport=transport,
            api_url="http://127.0.0.1:8000",
            codex_executable=None,
        )
    assert error.value.code == "NORMAL_REQUIRED"
    assert "Demo mode" in str(error.value)
    assert not (capsule / "outputs" / "search_plan.md").exists()


def test_interactive_instruction_is_one_round(tmp_path: Path) -> None:
    _workspace, capsule, _descriptor, _installed, manifest, _control, _executable = _fixture(
        tmp_path
    )
    runtime = runpy.run_path(str(capsule / "legacy_reagent_local.py"))
    instruction = runtime["_interactive_instruction"]("NORMAL", resume=False)
    assert "MVP-LS2 INTERACTIVE_ONE_ROUND" in instruction
    assert "AUTO_PLANNING_STAGE" not in instruction
    assert "AUTO_SYNTHESIS_STAGE" not in instruction
    assert "PLAN_CONFIRMED" in instruction
    assert "SEARCH_COMPLETED" in instruction
    assert "finish" in instruction
    assert "FINALIZED" in instruction


def test_literature_run_selects_single_attached_interactive_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace, capsule, descriptor, installed, manifest, _control, executable = _fixture(tmp_path)
    runtime = runpy.run_path(str(capsule / "legacy_reagent_local.py"))
    control = runtime["_load_control"](capsule, manifest)
    control.update({
        "state": "NOT_STARTED",
        "last_completed_state": "NOT_STARTED",
        "plan_confirmation_count": 0,
        "query_plan_checksum": None,
        "search_result_checksums": [],
    })
    runtime["_write_control"](capsule, control)
    for path in (
        capsule / "outputs" / "search_plan.md",
        capsule / "memory" / "search" / "query_plan.json",
    ):
        path.unlink(missing_ok=True)

    calls = {"open": 0, "execute": 0, "close": 0}
    runtime["_open_session"] = lambda **kwargs: (
        calls.__setitem__("open", calls["open"] + 1)
        or {"session_id": "session", "session_token": "token"}
    )

    def execute(**kwargs) -> None:
        calls["execute"] += 1
        _write_results(capsule, runtime, manifest)

    # runpy.run_path returns a globals copy; the controller resolves internal
    # calls through the real module globals, so patch those directly.
    runtime["_execute_queries"].__globals__["_execute_queries"] = execute
    runtime["_cleanup_session"] = lambda **kwargs: calls.__setitem__(
        "close", calls["close"] + 1
    )
    runtime["_upload_with_fresh_session"] = _stub_upload("receipt-one-session")
    monkeypatch.setenv("REAGENT_FAKE_CODEX_AUTO_CONFIRM", "1")

    invoked: list[tuple[bool, str]] = []
    original_harness = workspace_cli._managed_harness

    def spy_harness(root, executable_path, instruction, *, environment,
                    timeout_seconds=None, interactive=False):
        invoked.append((interactive, instruction))
        assert interactive is True
        return original_harness(
            root, executable_path, instruction, environment=environment,
            timeout_seconds=timeout_seconds, interactive=interactive,
        )

    monkeypatch.setattr(workspace_cli, "_managed_harness", spy_harness)
    result = workspace_cli._run_literature_interactive_round(
        capsule=capsule,
        manifest=manifest,
        runtime=runtime,
        api_url="http://127.0.0.1:8000",
        mode="DEMO",
        codex_executable=str(executable),
    )
    assert result["status"] == "ROUND_COMPLETED"
    assert calls == {"open": 1, "execute": 1, "close": 1}
    # ONE run must open exactly ONE attached interactive Codex session.
    assert len(invoked) == 1
    assert all(interactive for interactive, _ in invoked)
    texts = " ".join(instruction for _, instruction in invoked)
    assert "MVP-LS2 INTERACTIVE_ONE_ROUND" in texts
    assert "AUTO_PLANNING_STAGE" not in texts
    assert "AUTO_SYNTHESIS_STAGE" not in texts
    control = runtime["_load_control"](capsule, manifest)
    assert control["state"] == "UPLOADED"
    assert control["plan_confirmation_count"] >= 1
    assert control["candidate_review_confirmed"] is True
    assert control["finalization_confirmed"] is True


def test_literature_finish_is_required_and_no_report_without_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace, capsule, _descriptor, _installed, manifest, _control, executable = _fixture(
        tmp_path
    )
    runtime = runpy.run_path(str(capsule / "legacy_reagent_local.py"))
    control = runtime["_load_control"](capsule, manifest)
    control.update({
        "state": "NOT_STARTED",
        "last_completed_state": "NOT_STARTED",
        "plan_confirmation_count": 0,
        "query_plan_checksum": None,
        "search_result_checksums": [],
    })
    runtime["_write_control"](capsule, control)
    for path in (
        capsule / "outputs" / "search_plan.md",
        capsule / "memory" / "search" / "query_plan.json",
    ):
        path.unlink(missing_ok=True)
    runtime["_open_session"] = lambda **kwargs: {
        "session_id": "session", "session_token": "token"
    }
    runtime["_execute_queries"] = lambda **kwargs: _write_results(
        capsule, runtime, manifest
    )
    runtime["_cleanup_session"] = lambda **kwargs: None
    # Auto-confirm the plan and screening checkpoints; refuse only the final
    # `finish` command so the test isolates the explicit-finish requirement.
    monkeypatch.setenv("REAGENT_FAKE_CODEX_AUTO_CONFIRM", "1")
    monkeypatch.setenv("REAGENT_FAKE_CODEX_REFUSE_FINISH", "1")
    with pytest.raises(
        workspace_cli.OwnerCheckpointInvalid, match="exited before completing"
    ):
        workspace_cli._run_literature_interactive_round(
            capsule=capsule,
            manifest=manifest,
            runtime=runtime,
            api_url="http://127.0.0.1:8000",
            mode="DEMO",
            codex_executable=str(executable),
        )
    control = runtime["_load_control"](capsule, manifest)
    assert control["state"] != "FINALIZED"
    assert not list((capsule / "memory/progress/reports").glob("prv2-*.json"))


def test_owner_abort_is_safe_and_does_not_finalize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace, capsule, _descriptor, _installed, manifest, _control, executable = _fixture(
        tmp_path
    )
    runtime = runpy.run_path(str(capsule / "legacy_reagent_local.py"))
    control = runtime["_load_control"](capsule, manifest)
    control.update({
        "state": "NOT_STARTED",
        "last_completed_state": "NOT_STARTED",
        "plan_confirmation_count": 0,
        "query_plan_checksum": None,
        "search_result_checksums": [],
    })
    runtime["_write_control"](capsule, control)
    for path in (
        capsule / "outputs" / "search_plan.md",
        capsule / "memory" / "search" / "query_plan.json",
    ):
        path.unlink(missing_ok=True)
    runtime["_open_session"] = lambda **kwargs: {
        "session_id": "session", "session_token": "token"
    }
    runtime["_cleanup_session"] = lambda **kwargs: None
    monkeypatch.setenv("REAGENT_FAKE_CODEX_ABORT", "1")
    with pytest.raises(workspace_cli.OwnerCheckpointStopped, match="aborted"):
        workspace_cli._run_literature_interactive_round(
            capsule=capsule,
            manifest=manifest,
            runtime=runtime,
            api_url="http://127.0.0.1:8000",
            mode="DEMO",
            codex_executable=str(executable),
        )
    control = runtime["_load_control"](capsule, manifest)
    assert control["state"] == "INTERRUPTED"
    assert not list((capsule / "memory/progress/reports").glob("prv2-*.json"))
    assert not list(
        (capsule / "outputs/artifacts/selected-paper-library").glob("sha256-*.json")
    )


def test_interactive_harness_keeps_stdin_attached_and_has_no_wall_clock_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, dict] = {}

    class FakeChild:
        def __init__(self, command):
            self.command = command
            captured["command"] = command

        def wait(self):
            return 0

    def fake_popen(command, **kwargs):
        captured["kwargs"] = kwargs
        return FakeChild(command)

    monkeypatch.setattr(workspace_cli.subprocess, "Popen", fake_popen)
    workspace_cli._managed_harness(
        tmp_path,
        "/safe/fake-codex",
        "interactive instruction",
        environment={},
        interactive=True,
    )
    assert captured["command"] == [
        "/safe/fake-codex",
        "--sandbox", "workspace-write",
        "--ask-for-approval", "on-request",
        "--no-alt-screen",
        "-C", str(tmp_path),
        "interactive instruction",
    ]
    # stdin stays inherited (Popen without stdin=DEVNULL) and no wall-clock
    # timeout is applied, so Owner dwell inside the TUI cannot trigger a
    # Harness timeout.
    assert "stdin" not in captured["kwargs"]
    assert "timeout" not in captured["kwargs"]
