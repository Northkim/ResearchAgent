from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.project_workspaces import workspace_cli
from backend.workflow_packages.tests.test_forward_downstream_controlled_chain import (
    _harness,
    prepare_real_codex_fixtures,
)


@pytest.mark.parametrize(
    ("fixture_name", "workflow_kind", "harness_role", "approval_paths"),
    [
        (
            "writing",
            "INITIAL_WRITING",
            "writing",
            ("memory/outline-approval.json", "memory/owner-review.json"),
        ),
        (
            "review",
            "REVIEW",
            "review",
            ("memory/scope-approval.json", "memory/owner-review.json"),
        ),
        (
            "revision",
            "WRITING_REVISION",
            "revision",
            ("memory/revision-plan-approval.json", "memory/owner-review.json"),
        ),
    ],
)
def test_natural_owner_decisions_create_exact_runner_owned_records(
    tmp_path: Path,
    fixture_name: str,
    workflow_kind: str,
    harness_role: str,
    approval_paths: tuple[str, str],
) -> None:
    root, instance_id = prepare_real_codex_fixtures(tmp_path / "fixtures")[fixture_name]
    harness = _harness(tmp_path / f"{fixture_name}-codex", harness_role)
    prompts: list[str] = []

    def approve(prompt: str) -> str:
        prompts.append(prompt)
        return "Approve"

    result = workspace_cli._run_forward_owner_checkpoint(
        capsule=root,
        workflow_instance_id=instance_id,
        workflow_kind=workflow_kind,
        codex_executable=str(harness),
        decision_input=approve,
    )

    assert result["status"] == "COMPLETED"
    assert len(prompts) == 2
    assert all(prompt == "Approve / Revise / Explain / Abort: " for prompt in prompts)
    for relative in approval_paths:
        record = json.loads((root / relative).read_text())
        assert record["decision"] == "APPROVED"
        assert record["sha256"].startswith("sha256:")
    reports = list((root / "memory/progress/reports").glob("*.json"))
    artifacts = list((root / "outputs/artifacts").glob("**/*.json"))
    assert len(reports) == len(artifacts) == 1


def test_revise_stops_without_fabricating_exact_approval(tmp_path: Path) -> None:
    root, instance_id = prepare_real_codex_fixtures(tmp_path / "fixtures")["writing"]
    harness = _harness(tmp_path / "writing-codex", "writing")

    with pytest.raises(workspace_cli.WorkspaceCLIError) as captured:
        workspace_cli._run_forward_owner_checkpoint(
            capsule=root,
            workflow_instance_id=instance_id,
            workflow_kind="INITIAL_WRITING",
            codex_executable=str(harness),
            decision_input=lambda _prompt: "Revise",
        )

    assert captured.value.code == "OWNER_DECISION_REQUIRED"
    assert (root / "memory/outline.json").is_file()
    assert not (root / "memory/outline-approval.json").exists()
    assert not list((root / "memory/progress/reports").glob("*.json"))
