from __future__ import annotations

from pathlib import Path

import pytest

from backend.project_workspaces import workspace_cli


INSTANCE_ID = "wfi-" + "1" * 32


def _sync_result(status: str = "ACKNOWLEDGED") -> workspace_cli.WorkspaceSyncResult:
    return workspace_cli.WorkspaceSyncResult(
        status="NO_CHANGE",
        project_id="project-" + "2" * 32,
        workspace_id="workspace-" + "3" * 32,
        manifest_revision=1,
        installed_capsules=5,
        retained_capsules=0,
        acknowledgement_status=status,
        lock_checksum="sha256:" + "4" * 64,
    )


def test_normal_continue_composes_sync_materialization_and_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, object]] = []
    transport = object()

    monkeypatch.setattr(
        workspace_cli,
        "sync_workspace",
        lambda **kwargs: calls.append(("sync", kwargs["transport"])) or _sync_result(),
    )
    monkeypatch.setattr(
        workspace_cli,
        "resolve_workflow_selector",
        lambda root, workflow: calls.append(("resolve", (root, workflow))) or INSTANCE_ID,
    )
    monkeypatch.setattr(
        workspace_cli,
        "materialize_artifacts",
        lambda **kwargs: calls.append(
            ("materialize", kwargs["consumer_workflow_instance_id"])
        ),
    )
    expected = workspace_cli.WorkflowRunResult(
        status="RUN_COMPLETED",
        project_id="project-" + "2" * 32,
        workspace_id="workspace-" + "3" * 32,
        workflow_instance_id=INSTANCE_ID,
        capsule_relative_path="capsules/example",
    )
    monkeypatch.setattr(
        workspace_cli,
        "run_workflow",
        lambda **kwargs: calls.append(("run", kwargs["workflow_instance_id"])) or expected,
    )

    result = workspace_cli.continue_workflow(
        workspace_root=tmp_path,
        workflow_instance_id=None,
        workflow_definition_id="writing-local-experimental",
        transport=transport,
        api_url="http://127.0.0.1:8000",
    )

    assert result is expected
    assert calls == [
        ("sync", transport),
        ("resolve", (tmp_path, "writing-local-experimental")),
        ("materialize", INSTANCE_ID),
        ("run", INSTANCE_ID),
    ]


def test_continue_stops_when_sync_acknowledgement_is_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        workspace_cli,
        "sync_workspace",
        lambda **_kwargs: _sync_result("ACK_PENDING"),
    )
    monkeypatch.setattr(
        workspace_cli,
        "materialize_artifacts",
        lambda **_kwargs: pytest.fail("pending sync must not materialize"),
    )

    with pytest.raises(workspace_cli.WorkspaceCLIError) as captured:
        workspace_cli.continue_workflow(
            workspace_root=tmp_path,
            workflow_instance_id=INSTANCE_ID,
            workflow_definition_id=None,
            transport=object(),
            api_url="http://127.0.0.1:8000",
        )

    assert captured.value.code == "WORKSPACE_ACK_PENDING"


def test_main_reports_bounded_owner_cancellation_without_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        workspace_cli,
        "continue_workflow",
        lambda **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    exit_code = workspace_cli.main(
        ["run", str(tmp_path), "--workflow-instance", INSTANCE_ID]
    )

    output = capsys.readouterr()
    assert exit_code == workspace_cli.EXIT_VALIDATION
    assert "OWNER_CANCELLED" in output.err
    assert "Traceback" not in output.out + output.err
