from __future__ import annotations

import json
import runpy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.project_workspaces import workspace_cli
from backend.workflow_packages.production_workflows import (
    build_idea_discovery_v0_3_package,
)
from backend.workflow_packages.serialization import canonical_hash, canonical_json
from backend.workflow_packages.tests.test_f1a_selected_idea import (
    _materialize_literature,
    _write_outputs,
)


PROJECT_ID = "project-" + "a" * 32
WORKSPACE_ID = "workspace-" + "b" * 32
INSTANCE_ID = "wfi-" + "c" * 32
OTHER_INSTANCE_ID = "wfi-" + "d" * 32


def _completed_idea_with_six_rounds(tmp_path: Path) -> tuple[Path, dict, list[dict]]:
    package = build_idea_discovery_v0_3_package(
        project_id=PROJECT_ID,
        project_name="Progress backlog fixture",
        research_topic="Bounded synthetic continuity",
        output_root=tmp_path / "idea",
        package_id="idea-discovery-progress-backlog-v0.3",
    )
    root = package.package_root
    library = _materialize_literature(tmp_path, root)
    _write_outputs(root, library, ("candidate",))
    runtime = runpy.run_path(str(root / "reagent_local.py"))
    helper = runpy.run_path(str(root / "progress_report.py"))
    for round_number in range(1, 7):
        final = round_number == 6
        if final:
            _write_outputs(root, library, ("selected",))
        before = runtime["_prepare_draft"](
            root, stage="COMPLETED" if final else "USER_REVIEW"
        )
        draft_path = root / "memory/progress/report-draft.json"
        draft = json.loads(draft_path.read_text(encoding="utf-8"))
        draft["status"] = "COMPLETED" if final else "IN_PROGRESS"
        draft["completed_work"] = [f"Completed bounded Idea round {round_number}"]
        draft["next_recommended_action"] = (
            "Review the selected research idea"
            if final
            else "Continue the bounded Idea review"
        )
        draft_path.write_text(canonical_json(draft) + "\n", encoding="utf-8")
        helper["finalize"](
            package_root=root,
            draft_path="memory/progress/report-draft.json",
            context_before_checksum=before,
        )
    manifest = json.loads((root / "package-manifest.json").read_text())
    reports = workspace_cli._validated_local_progress_reports(root, manifest)
    assert [item["execution_round"] for item in reports] == [1, 2, 3, 4, 5, 6]
    assert [item["status"] for item in reports] == ["IN_PROGRESS"] * 5 + ["COMPLETED"]
    return root, manifest, reports


def _completed_idea_one_round(tmp_path: Path) -> tuple[Path, dict, list[dict]]:
    package = build_idea_discovery_v0_3_package(
        project_id=PROJECT_ID,
        project_name="Progress supersession fixture",
        research_topic="Bounded synthetic continuity",
        output_root=tmp_path / "idea-one",
        package_id="idea-discovery-progress-supersede-v0.3",
    )
    root = package.package_root
    library = _materialize_literature(tmp_path, root)
    _write_outputs(root, library, ("selected",))
    runtime = runpy.run_path(str(root / "reagent_local.py"))
    helper = runpy.run_path(str(root / "progress_report.py"))
    before = runtime["_prepare_draft"](root, stage="COMPLETED")
    draft_path = root / "memory/progress/report-draft.json"
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    draft["status"] = "COMPLETED"
    draft["completed_work"] = ["Completed bounded Idea round 1"]
    draft["next_recommended_action"] = "Review the selected research idea"
    draft_path.write_text(canonical_json(draft) + "\n", encoding="utf-8")
    helper["finalize"](
        package_root=root,
        draft_path="memory/progress/report-draft.json",
        context_before_checksum=before,
    )
    manifest = json.loads((root / "package-manifest.json").read_text())
    reports = workspace_cli._validated_local_progress_reports(root, manifest)
    assert [item["execution_round"] for item in reports] == [1]
    assert [item["status"] for item in reports] == ["COMPLETED"]
    return root, manifest, reports


def _stale_checkpoint(
    manifest: dict,
    *,
    status: str = "IN_PROGRESS",
) -> dict:
    checkpoint = {
        "schema_version": "progress-report/v0.2",
        "report_id": "prv2-" + "a" * 64,
        "report_checksum": "sha256:" + "b" * 64,
        "execution_round": 1,
        "status": status,
    }
    envelope = {
        "original_report_checksum": "sha256:" + "c" * 64,
        "original_report_size": 1,
        "original_report_media_type": "application/json",
        "envelope_checksum": "sha256:" + "d" * 64,
        "uploaded_at": "2026-08-13T00:00:00Z",
        "uploader_type": "local-cli",
        "client_version": "reagent-workspace-progress-recovery/0.1.0",
        "source_path_hint": ".reagent/checkpoints/literature/progress/stale.json",
    }
    return _accepted_history(manifest, INSTANCE_ID, checkpoint, envelope)


class _ProgressTransport:
    def __init__(
        self,
        *,
        accepted: list[dict] | None = None,
        fail_after: int | None = None,
        supersede_rounds: set[int] | None = None,
    ):
        self.accepted = list(accepted or [])
        self.fail_after = fail_after
        self.supersede_rounds = set(supersede_rounds or ())
        self.uploaded_rounds: list[int] = []

    def workflow_instance_progress(self, project_id, workflow_instance_id):
        assert project_id == PROJECT_ID
        assert workflow_instance_id == INSTANCE_ID
        return {
            "schema_version": "reagent.workflow-instance-progress/v0.1",
            "project_id": project_id,
            "workflow_instance_id": workflow_instance_id,
            "projection": {
                "project_id": project_id,
                "workflow_instance_id": workflow_instance_id,
                "latest_execution_round": (
                    self.accepted[-1]["normalized_record"]["execution_round"]
                    if self.accepted else None
                ),
            },
            "history": list(self.accepted),
            "history_total": len(self.accepted),
            "has_more_history": False,
        }

    def upload_progress_report(
        self, project_id, workflow_instance_id, manifest, report, envelope
    ):
        if self.fail_after is not None and len(self.uploaded_rounds) >= self.fail_after:
            raise workspace_cli.WorkspaceCLIError(
                "PROGRESS_UPLOAD_FAILED", "simulated interruption", workspace_cli.EXIT_CLOUD
            )
        expected_round = len(self.accepted) + 1
        if report["execution_round"] not in self.supersede_rounds:
            assert report["execution_round"] == expected_round
        assert envelope["workflow_instance_id"] == workflow_instance_id
        self.uploaded_rounds.append(report["execution_round"])
        uploaded = _accepted_history(manifest, workflow_instance_id, report, envelope)
        if report["execution_round"] in self.supersede_rounds:
            self.accepted = [
                item
                for item in self.accepted
                if item["normalized_record"]["execution_round"]
                != report["execution_round"]
            ]
        self.accepted.append(uploaded)
        return _receipt(uploaded)


def _accepted_history(manifest, instance_id, report, envelope):
    round_number = report["execution_round"]
    return {
        "receipt_id": f"progress-receipt-{round_number:064x}",
        "project_id": PROJECT_ID,
        "workflow_instance_id": instance_id,
        "package_id": manifest["package_id"],
        "package_checksum": manifest["package_checksum"],
        "report_id": report["report_id"],
        "report_checksum": report["report_checksum"],
        "report_schema_version": report["schema_version"],
        "original_report_checksum": envelope["original_report_checksum"],
        "original_report_size": envelope["original_report_size"],
        "original_report_media_type": "application/json",
        "envelope_checksum": envelope["envelope_checksum"],
        "uploaded_at": envelope["uploaded_at"],
        "received_at": f"2026-08-13T00:{round_number:02d}:00Z",
        "uploader_type": "local-cli",
        "client_version": envelope["client_version"],
        "source_path_hint": envelope["source_path_hint"],
        "validation_status": "ACCEPTED",
        "validation_errors": [],
        "validation_warnings": [],
        "chain_state": "VALID_CHAIN",
        "accepted_for_projection": True,
        "normalized_record": {
            "project_id": PROJECT_ID,
            "package_id": manifest["package_id"],
            "package_checksum": manifest["package_checksum"],
            "workflow_id": manifest["workflow_id"],
            "workflow_version": manifest["workflow_version"],
            "workflow_checksum": manifest["workflow_checksum"],
            "execution_round": round_number,
            "report_id": report["report_id"],
            "report_checksum": report["report_checksum"],
            "status": report.get("status"),
        },
    }


def _receipt(uploaded):
    payload = {
        "receipt_id": uploaded["receipt_id"],
        "project_id": uploaded["project_id"],
        "workflow_instance_id": uploaded["workflow_instance_id"],
        "package_id": uploaded["package_id"],
        "report_id": uploaded["report_id"],
        "report_checksum": uploaded["report_checksum"],
        "original_report_checksum": uploaded["original_report_checksum"],
        "validation_status": uploaded["validation_status"],
        "chain_state": uploaded["chain_state"],
        "accepted_for_projection": uploaded["accepted_for_projection"],
        "uploaded_at": uploaded["uploaded_at"],
        "received_at": uploaded["received_at"],
        "warning_count": 0,
        "error_count": 0,
    }
    return {**payload, "receipt_checksum": canonical_hash(payload), "idempotent_replay": False}


def _identity(root: Path, manifest: dict):
    workspace = root.parent / "workspace-metadata"
    workspace.mkdir()
    descriptor = {"project_id": PROJECT_ID, "workspace_id": WORKSPACE_ID}
    installed = {
        "workflow_instance_id": INSTANCE_ID,
        "relative_path": root.relative_to(root.parent).as_posix(),
    }
    return workspace, descriptor, installed


def _recover(root, manifest, reports, transport, workspace, descriptor, installed):
    return workspace_cli._recover_progress_backlog(
        workspace=workspace,
        descriptor=descriptor,
        installed=installed,
        capsule=root,
        manifest=manifest,
        reports=reports,
        transport=transport,
    )


def test_shuffled_content_addressed_filenames_upload_in_execution_round_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, manifest, reports = _completed_idea_with_six_rounds(tmp_path)
    workspace, descriptor, installed = _identity(root, manifest)
    paths = [root / "memory/progress/reports" / f"{item['report_id']}.json" for item in reports]
    shuffled = [paths[index - 1] for index in (2, 4, 1, 5, 6, 3)]
    original_glob = Path.glob

    def unordered_glob(path, pattern):
        if path == root / "memory/progress/reports" and pattern == "prv2-*.json":
            return iter(shuffled)
        return original_glob(path, pattern)

    monkeypatch.setattr(Path, "glob", unordered_glob)
    semantic = workspace_cli._validated_local_progress_reports(root, manifest)
    transport = _ProgressTransport()
    artifact = next(root.glob("outputs/artifacts/selected-research-idea/*.json"))
    before = artifact.read_bytes()

    assert _recover(root, manifest, semantic, transport, workspace, descriptor, installed) == 6
    assert transport.uploaded_rounds == [1, 2, 3, 4, 5, 6]
    assert artifact.read_bytes() == before
    receipts = list((workspace / workspace_cli.PROGRESS_RECEIPTS_ROOT / INSTANCE_ID).glob("*.json"))
    assert len(receipts) == 6


def test_partial_cloud_backlog_uploads_only_missing_rounds(tmp_path: Path) -> None:
    root, manifest, reports = _completed_idea_with_six_rounds(tmp_path)
    workspace, descriptor, installed = _identity(root, manifest)
    seed = _ProgressTransport()
    for report in reports[:3]:
        envelope = workspace_cli._progress_upload_envelope(root, INSTANCE_ID, report, datetime.now(UTC))
        seed.upload_progress_report(PROJECT_ID, INSTANCE_ID, manifest, report, envelope)
    transport = _ProgressTransport(accepted=seed.accepted)

    assert _recover(root, manifest, reports, transport, workspace, descriptor, installed) == 3
    assert transport.uploaded_rounds == [4, 5, 6]


def test_completed_local_result_is_pending_until_exact_cloud_acknowledgement(
    tmp_path: Path,
) -> None:
    root, manifest, reports = _completed_idea_with_six_rounds(tmp_path)
    workspace, descriptor, installed = _identity(root, manifest)
    count, status, acknowledged = workspace_cli._local_progress_summary(
        workspace, descriptor, installed, root
    )
    assert (count, status, acknowledged) == (6, "COMPLETED", False)

    transport = _ProgressTransport()
    _recover(root, manifest, reports, transport, workspace, descriptor, installed)
    count, status, acknowledged = workspace_cli._local_progress_summary(
        workspace, descriptor, installed, root
    )
    assert (count, status, acknowledged) == (6, "COMPLETED", True)


def test_interrupted_upload_retries_from_cloud_latest_without_harness(tmp_path: Path) -> None:
    root, manifest, reports = _completed_idea_with_six_rounds(tmp_path)
    workspace, descriptor, installed = _identity(root, manifest)
    transport = _ProgressTransport(fail_after=3)
    with pytest.raises(workspace_cli.WorkspaceCLIError, match="simulated interruption"):
        _recover(root, manifest, reports, transport, workspace, descriptor, installed)
    assert transport.uploaded_rounds == [1, 2, 3]
    transport.fail_after = None

    assert _recover(root, manifest, reports, transport, workspace, descriptor, installed) == 3
    assert transport.uploaded_rounds == [1, 2, 3, 4, 5, 6]


def test_gap_duplicate_and_foreign_instance_fail_closed(tmp_path: Path) -> None:
    root, manifest, reports = _completed_idea_with_six_rounds(tmp_path)
    workspace, descriptor, installed = _identity(root, manifest)
    transport = _ProgressTransport()
    with pytest.raises(workspace_cli.WorkspaceCLIError, match="does not continue"):
        _recover(root, manifest, [*reports[:3], *reports[4:]], transport, workspace, descriptor, installed)

    duplicate = dict(reports[1])
    duplicate["completed_work"] = ["different content for the same round"]
    duplicate.update(workspace_cli._progress_report_identity(duplicate))
    duplicate_path = root / "memory/progress/reports" / f"{duplicate['report_id']}.json"
    duplicate_path.write_text(canonical_json(duplicate) + "\n", encoding="utf-8")
    with pytest.raises(workspace_cli.WorkspaceCLIError) as branched:
        workspace_cli._validated_local_progress_reports(root, manifest)
    assert branched.value.code == "LOCAL_PROGRESS_BRANCHED"

    foreign = _accepted_history(
        manifest,
        OTHER_INSTANCE_ID,
        reports[0],
        workspace_cli._progress_upload_envelope(root, INSTANCE_ID, reports[0], datetime.now(UTC)),
    )
    page = _ProgressTransport(accepted=[foreign]).workflow_instance_progress(PROJECT_ID, INSTANCE_ID)
    with pytest.raises(workspace_cli.WorkspaceCLIError) as scoped:
        workspace_cli._accepted_cloud_progress(
            page, descriptor=descriptor, installed=installed, manifest=manifest
        )
    assert scoped.value.code == "CLOUD_PROGRESS_INVALID"


def test_accepted_cloud_progress_keeps_terminal_round_representative(
    tmp_path: Path,
) -> None:
    root, manifest, reports = _completed_idea_one_round(tmp_path)
    workspace, descriptor, installed = _identity(root, manifest)
    stale = _stale_checkpoint(manifest)
    terminal = _accepted_history(
        manifest,
        INSTANCE_ID,
        reports[0],
        workspace_cli._progress_upload_envelope(
            root, INSTANCE_ID, reports[0], datetime.now(UTC)
        ),
    )
    terminal["normalized_record"]["status"] = "COMPLETED"
    page = _ProgressTransport(accepted=[stale, terminal]).workflow_instance_progress(
        PROJECT_ID, INSTANCE_ID
    )
    accepted = workspace_cli._accepted_cloud_progress(
        page, descriptor=descriptor, installed=installed, manifest=manifest
    )
    assert [item["report_id"] for item in accepted] == [reports[0]["report_id"]]
    assert accepted[0]["normalized_record"]["status"] == "COMPLETED"


def test_stale_in_progress_cloud_checkpoint_is_superseded_by_terminal_local_report(
    tmp_path: Path,
) -> None:
    root, manifest, reports = _completed_idea_one_round(tmp_path)
    workspace, descriptor, installed = _identity(root, manifest)
    stale = _stale_checkpoint(manifest)
    transport = _ProgressTransport(accepted=[stale], supersede_rounds={1})

    assert _recover(root, manifest, reports, transport, workspace, descriptor, installed) == 1
    assert transport.uploaded_rounds == [1]
    assert [item["report_id"] for item in transport.accepted] == [
        reports[0]["report_id"]
    ]
    receipts = list(
        (workspace / workspace_cli.PROGRESS_RECEIPTS_ROOT / INSTANCE_ID).glob("*.json")
    )
    assert len(receipts) == 1
    acknowledgement = json.loads(receipts[0].read_text())
    assert acknowledgement["report_id"] == reports[0]["report_id"]
    assert acknowledgement["report_checksum"] == reports[0]["report_checksum"]
    assert acknowledgement["execution_round"] == 1
    assert acknowledgement["receipt_id"].startswith("progress-receipt-")
    assert acknowledgement["cloud_receipt_checksum"]


def test_different_completed_cloud_report_fails_closed(tmp_path: Path) -> None:
    root, manifest, reports = _completed_idea_one_round(tmp_path)
    workspace, descriptor, installed = _identity(root, manifest)
    competing = _stale_checkpoint(manifest, status="COMPLETED")
    transport = _ProgressTransport(accepted=[competing])

    with pytest.raises(workspace_cli.WorkspaceCLIError) as error:
        _recover(root, manifest, reports, transport, workspace, descriptor, installed)
    assert error.value.code == "PROGRESS_HISTORY_CONFLICT"
    assert transport.uploaded_rounds == []
    receipts = list(
        (workspace / workspace_cli.PROGRESS_RECEIPTS_ROOT / INSTANCE_ID).glob("*.json")
    )
    assert receipts == []


def test_progress_upload_conflict_message_does_not_claim_no_state_changed() -> None:
    what, next_step = workspace_cli._ERROR_GUIDANCE["PROGRESS_UPLOAD_CONFLICT"]
    combined = what + " " + next_step
    assert "finalized and preserved locally" in what
    assert "No research work needs to be repeated" in next_step
    assert "No state was declared successful" not in combined
    assert "No research state was changed" not in combined
