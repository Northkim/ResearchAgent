from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from backend.progress_reports.aggregation import (
    _attach_local_command,
    _local_command,
)
from backend.progress_reports.contracts import (
    WorkflowActionProjection,
    WorkflowNextActionProjection,
    WorkflowOutputProjection,
    WorkflowStageProjection,
)
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.workspace_cli import (
    OwnerCheckpointInvalid,
    WorkspaceCLIError,
)


def _write_executable(path: Path, *, executable: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    mode = path.stat().st_mode | stat.S_IXUSR if executable else path.stat().st_mode
    path.chmod(mode)
    return path


def test_managed_codex_executable_accepts_absolute_and_symlink_paths(
    tmp_path: Path,
) -> None:
    target = _write_executable(tmp_path / "codex-bin" / "codex")
    link = tmp_path / "codex-link"
    link.symlink_to(target)

    resolved_target = workspace_cli._managed_codex_executable(str(target))
    assert resolved_target == str(target.resolve())

    resolved_link = workspace_cli._managed_codex_executable(str(link))
    assert resolved_link == str(target.resolve())


def test_managed_codex_executable_accepts_homebrew_like_symlink(
    tmp_path: Path,
) -> None:
    cask_bin = tmp_path / "Caskroom" / "codex" / "0.146.0" / "bin"
    target = _write_executable(cask_bin / "codex")
    homebrew_bin = tmp_path / "homebrew" / "bin"
    homebrew_bin.mkdir(parents=True)
    link = homebrew_bin / "codex"
    link.symlink_to(target)

    resolved = workspace_cli._managed_codex_executable(str(link))
    assert resolved == str(target.resolve())


def test_managed_codex_executable_rejects_broken_symlink_and_non_executable(
    tmp_path: Path,
) -> None:
    broken = tmp_path / "broken"
    broken.symlink_to(tmp_path / "missing-target")
    with pytest.raises(OwnerCheckpointInvalid, match="unavailable"):
        workspace_cli._managed_codex_executable(str(broken))

    plain = _write_executable(tmp_path / "plain", executable=False)
    with pytest.raises(OwnerCheckpointInvalid, match="unavailable"):
        workspace_cli._managed_codex_executable(str(plain))


def test_managed_codex_executable_default_discovery_and_missing_diagnostic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    discovered = _write_executable(tmp_path / "codex")
    monkeypatch.setattr(workspace_cli.shutil, "which", lambda name: str(discovered))
    assert workspace_cli._managed_codex_executable(None) == str(discovered.resolve())

    monkeypatch.setattr(workspace_cli.shutil, "which", lambda name: None)
    with pytest.raises(OwnerCheckpointInvalid) as error:
        workspace_cli._managed_codex_executable(None)
    message = str(error.value)
    assert "Codex is not ready on this computer." in message
    assert "Your Workspace was not changed." in message


def test_load_workspace_normalizes_relative_root_to_absolute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.project_workspaces.tests.test_sync import _synced_full_research_workspace

    workspace, _descriptor, _transport = _synced_full_research_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    loaded, _descriptor, _bootstrap = workspace_cli.load_workspace(Path("."))
    assert loaded.is_absolute()
    assert loaded == workspace.resolve()


def test_literature_missing_codex_fails_before_workflow_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.project_workspaces.tests.test_sync import (
        _literature_capsule,
        _synced_full_research_workspace,
    )

    workspace, _descriptor, _transport = _synced_full_research_workspace(tmp_path)
    capsule, installed = _literature_capsule(workspace)
    control_path = capsule / "memory/round-control.json"
    control_before = control_path.read_bytes()

    monkeypatch.setattr(workspace_cli.shutil, "which", lambda name: None)
    with pytest.raises(WorkspaceCLIError) as error:
        workspace_cli._advance_literature_checkpoint_workflow(
            workspace=workspace,
            descriptor={
                "project_id": workspace_cli._read_json(
                    workspace / workspace_cli.WORKSPACE_DESCRIPTOR
                )["project_id"],
                "workspace_id": workspace_cli._read_json(
                    workspace / workspace_cli.WORKSPACE_DESCRIPTOR
                )["workspace_id"],
            },
            installed=installed,
            capsule=capsule,
            manifest=workspace_cli._read_json(
                capsule / "package-manifest.json"
            ),
            transport=object(),
            api_url="http://127.0.0.1:8000",
            mode="DEMO",
            codex_executable=None,
            decision_input=lambda _prompt: "approve",
        )
    assert error.value.code == "CODEX_UNAVAILABLE"
    assert control_path.read_bytes() == control_before
    assert not (capsule / "outputs" / "search_plan.md").exists()


def _action(code: str, surface: str = "LOCAL") -> WorkflowActionProjection:
    return WorkflowActionProjection(
        stage=WorkflowStageProjection("READY", "Ready"),
        actor="OWNER",
        attention_state="NORMAL",
        blocker=None,
        next_action=WorkflowNextActionProjection(
            surface,
            code,
            "Label",
            "Description",
        ),
        expected_output=None,
        latest_output=None,
    )


def test_local_command_generation_is_authoritative() -> None:
    assert _local_command("SYNC", workflow_instance_id="wfi-x" * 2,
                          workflow_definition_id="literature-search-local-experimental",
                          unambiguous=False) == "python reagent_local.py sync ."
    assert _local_command("RUN", workflow_instance_id="wfi-" + "1" * 32,
                          workflow_definition_id="literature-search-local-experimental",
                          unambiguous=True) == (
        "python reagent_local.py run . --workflow literature-search-local-experimental"
    )
    assert _local_command("CONTINUE", workflow_instance_id="wfi-" + "1" * 32,
                          workflow_definition_id="idea-discovery-local-experimental",
                          unambiguous=False) == (
        "python reagent_local.py run . --workflow-instance wfi-" + "1" * 32
    )
    assert _local_command("MATERIALIZE", workflow_instance_id="wfi-" + "2" * 32,
                          workflow_definition_id="idea-discovery-local-experimental",
                          unambiguous=False) == (
        "python reagent_local.py artifact materialize . --workflow-instance wfi-" + "2" * 32
    )
    assert _local_command("REVIEW_RESULT", workflow_instance_id="wfi-" + "1" * 32,
                          workflow_definition_id="x", unambiguous=False) is None


def test_attach_local_command_preserves_browser_and_none_actions() -> None:
    browser = _action("SETUP", surface="BROWSER")
    assert _attach_local_command(
        browser,
        workflow_instance_id="wfi-" + "1" * 32,
        workflow_definition_id="x",
        unambiguous=False,
    ) is browser

    none_action = _action("NONE", surface="NONE")
    assert _attach_local_command(
        none_action,
        workflow_instance_id="wfi-" + "1" * 32,
        workflow_definition_id="x",
        unambiguous=False,
    ) is none_action

    sync = _attach_local_command(
        _action("SYNC"),
        workflow_instance_id="wfi-" + "1" * 32,
        workflow_definition_id="x",
        unambiguous=False,
    )
    assert sync.next_action.command == "python reagent_local.py sync ."


def test_expected_output_projection_contract_unaffected() -> None:
    output = WorkflowOutputProjection(
        label="Library",
        artifact_id=None,
        artifact_type="selected-paper-library/v1",
        artifact_schema="selected-paper-library/v1",
        checksum=None,
        produced_at=None,
        progress_round=None,
        state="EXPECTED",
    )
    assert output.state == "EXPECTED"
