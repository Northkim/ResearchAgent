from __future__ import annotations

import json
import runpy
import shutil
from pathlib import Path

import pytest

from backend.project_workspaces import workspace_cli
from backend.project_workspaces.tests.test_literature_checkpoint_lifecycle import (
    _fixture,
)
from backend.project_workspaces.tests.test_progress_backlog_recovery import (
    _ProgressTransport,
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


def test_interactive_planning_instruction_has_no_auto_stage() -> None:
    instruction = workspace_cli._literature_planning_instruction("NORMAL")
    assert "LITERATURE PLANNING - INTERACTIVE" in instruction
    assert "AUTO_PLANNING_STAGE" not in instruction
    assert "Ask the Owner" in instruction
    assert "PLAN_CONFIRMED" in instruction


def test_finalization_instruction_requires_explicit_finish() -> None:
    instruction = workspace_cli._literature_finalization_instruction("NORMAL")
    assert "LITERATURE FINALIZATION - INTERACTIVE" in instruction
    assert "finish" in instruction
    assert "do not modify any files" in instruction


def test_literature_phases_select_attached_interactive_harness(
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

    runtime["_check_backend"] = lambda _url: None
    calls = {"open": 0, "execute": 0, "close": 0}
    runtime["_open_session"] = lambda **kwargs: (
        calls.__setitem__("open", calls["open"] + 1)
        or {"session_id": "session", "session_token": "token"}
    )

    def execute(**kwargs) -> None:
        calls["execute"] += 1
        from backend.project_workspaces.tests.test_literature_checkpoint_lifecycle import (
            _write_results,
        )

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

    invoked: list[tuple[bool, str]] = []

    def spy_harness(root, executable_path, instruction, *, environment,
                   timeout_seconds=None, interactive=False):
        invoked.append((interactive, instruction))
        if "LITERATURE PLANNING - INTERACTIVE" in instruction:
            fake_codex_cli.plan(root)
            fake_codex_cli.mark_plan_confirmed(root)
        elif "LITERATURE SCREENING - INTERACTIVE" in instruction:
            fake_codex_cli.synthesize(root)
            owner = json.loads((root / "memory/owner-decisions.json").read_text())
            workspace_cli._atomic_write_json(
                root / "memory/proposed-screening.json",
                {
                    "schema_version": "reagent.literature-screening-proposal/v0.1",
                    "decisions": owner["decisions"],
                },
            )
            (root / "memory/owner-decisions.json").unlink()
        elif "LITERATURE FINALIZATION - INTERACTIVE" in instruction:
            return None

    monkeypatch.setattr(workspace_cli, "_managed_harness", spy_harness)
    result = workspace_cli._advance_literature_checkpoint_workflow(
        workspace=workspace,
        descriptor=descriptor,
        installed=installed,
        capsule=capsule,
        manifest=manifest,
        transport=_ProgressTransport(),
        api_url="http://127.0.0.1:8000",
        mode="DEMO",
        codex_executable=str(executable),
        decision_input=lambda _prompt: "approve",
    )
    assert result["status"] == "COMPLETED"
    assert calls == {"open": 1, "execute": 1, "close": 1}
    assert len(invoked) == 3
    assert all(interactive for interactive, _ in invoked)
    texts = " ".join(instruction for _, instruction in invoked)
    assert "AUTO_PLANNING_STAGE" not in texts
    assert "LITERATURE PLANNING - INTERACTIVE" in texts
    assert "LITERATURE SCREENING - INTERACTIVE" in texts
    assert "LITERATURE FINALIZATION - INTERACTIVE" in texts
