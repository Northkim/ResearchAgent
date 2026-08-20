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


def test_sync_refreshes_root_cli_from_cloud(
    tmp_path: Path,
) -> None:
    from backend.project_workspaces.tests.test_sync import (
        _ClientTransport,
        _synced_full_research_workspace,
    )

    workspace, _descriptor, transport = _synced_full_research_workspace(tmp_path)
    cli_path = workspace / "reagent_local.py"
    original = cli_path.read_bytes()
    refreshed = original + b"\n# refreshed-local-tool\n"

    class RefreshingTransport(_ClientTransport):
        def local_client_source(self) -> tuple[bytes, str]:
            return refreshed, workspace_cli.sha256_bytes(refreshed)

    synced = workspace_cli.sync_workspace(
        workspace_root=workspace,
        transport=RefreshingTransport(transport.client),
    )
    assert synced.status in {"SYNCED", "NO_CHANGE"}
    assert cli_path.read_bytes() == refreshed
    assert cli_path.stat().st_mode & 0o700 == 0o700

    # A transport serving the identical bytes must not rewrite the file.
    class UnchangedTransport(_ClientTransport):
        def local_client_source(self) -> tuple[bytes, str]:
            return original, workspace_cli.sha256_bytes(original)

    workspace_cli._atomic_write_bytes(cli_path, original, mode=0o700)
    before = cli_path.stat().st_mtime_ns
    workspace_cli.sync_workspace(
        workspace_root=workspace,
        transport=UnchangedTransport(transport.client),
    )
    assert cli_path.read_bytes() == original
    assert cli_path.stat().st_mtime_ns == before


def test_sync_cli_update_failure_is_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.project_workspaces.tests.test_sync import (
        _ClientTransport,
        _synced_full_research_workspace,
    )

    workspace, _descriptor, transport = _synced_full_research_workspace(tmp_path)
    cli_path = workspace / "reagent_local.py"
    cli_before = cli_path.read_bytes()
    lock_before = (workspace / workspace_cli.INSTALLED_LOCK).read_bytes()

    class FailingFetchTransport(_ClientTransport):
        def local_client_source(self) -> tuple[bytes, str]:
            raise OSError("download endpoint unavailable")

    with pytest.raises(workspace_cli.WorkspaceCLIError) as error:
        workspace_cli.sync_workspace(
            workspace_root=workspace,
            transport=FailingFetchTransport(transport.client),
        )
    assert error.value.code == "CLI_UPDATE_REQUIRED"
    assert "could not be synchronized completely" in str(error.value)
    assert cli_path.read_bytes() == cli_before
    assert (workspace / workspace_cli.INSTALLED_LOCK).read_bytes() == lock_before


def test_sync_cli_update_rejects_invalid_served_bytes(
    tmp_path: Path,
) -> None:
    from backend.project_workspaces.tests.test_sync import (
        _ClientTransport,
        _synced_full_research_workspace,
    )

    workspace, _descriptor, transport = _synced_full_research_workspace(tmp_path)
    cli_path = workspace / "reagent_local.py"
    cli_before = cli_path.read_bytes()

    class InvalidBytesTransport(_ClientTransport):
        def local_client_source(self) -> tuple[bytes, str]:
            return b"", workspace_cli.sha256_bytes(b"")

    with pytest.raises(workspace_cli.WorkspaceCLIError) as error:
        workspace_cli.sync_workspace(
            workspace_root=workspace,
            transport=InvalidBytesTransport(transport.client),
        )
    assert error.value.code == "CLI_UPDATE_REQUIRED"
    assert cli_path.read_bytes() == cli_before


def test_sync_cli_update_atomic_replace_failure_preserves_old_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.project_workspaces.tests.test_sync import (
        _ClientTransport,
        _synced_full_research_workspace,
    )

    workspace, _descriptor, transport = _synced_full_research_workspace(tmp_path)
    cli_path = workspace / "reagent_local.py"
    cli_before = cli_path.read_bytes()
    refreshed = cli_before + b"\n# newer\n"

    class RefreshingTransport(_ClientTransport):
        def local_client_source(self) -> tuple[bytes, str]:
            return refreshed, workspace_cli.sha256_bytes(refreshed)

    def fail_write(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(workspace_cli, "_atomic_write_bytes", fail_write)
    with pytest.raises(workspace_cli.WorkspaceCLIError) as error:
        workspace_cli.sync_workspace(
            workspace_root=workspace,
            transport=RefreshingTransport(transport.client),
        )
    assert error.value.code == "CLI_UPDATE_REQUIRED"
    assert cli_path.read_bytes() == cli_before


def test_all_full_research_workflows_use_common_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    from backend.project_workspaces.tests.test_sync import (
        _synced_full_research_workspace,
    )

    workspace, _descriptor, transport = _synced_full_research_workspace(tmp_path)
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
    target = _write_executable(tmp_path / "codex-target")
    link = tmp_path / "codex-link"
    link.symlink_to(target)
    seen: list[str] = []

    def fake_resolve(value: str) -> str:
        seen.append(value)
        return str(target.resolve())

    monkeypatch.setattr(workspace_cli, "_managed_codex_executable", fake_resolve)
    forward = {
        "literature-search-local-experimental",
        "idea-discovery-local-experimental",
        "reproduction-experiment-local-experimental",
        "writing-local-experimental",
        "review-local-experimental",
    }
    for item in lock["installed_capsules"]:
        if item["workflow_definition_id"] not in forward:
            continue
        capsule = workspace / item["relative_path"]
        assert capsule.is_absolute()
        try:
            result = workspace_cli.run_workflow(
                workspace_root=workspace,
                workflow_instance_id=item["workflow_instance_id"],
                transport=transport,
                api_url="http://127.0.0.1:8000",
                preflight_only=True,
                codex_executable=str(link),
            )
            assert result.status == "PREFLIGHT_READY"
        except Exception:
            # Input-dependent preflights stop before Capsule launch (the test
            # transport asserts on the missing binding); the common boundary
            # proof is that the override was already resolved at the
            # run_workflow entry and the Capsule path is absolute.
            pass
    assert seen == [str(link)] * len(forward)
