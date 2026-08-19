from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

from backend.artifact_references.tests.test_forward_downstream_v5_contracts import (
    _manuscript,
    _review,
    _v5,
)
from backend.artifact_references.tests.test_research_flow_contracts import (
    _library,
    _selected,
)
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.tests import test_progress_backlog_recovery as backlog
from backend.workflow_packages.revision_optional_support_publication import (
    build_writing_revision_v0_9_package,
)
from backend.workflow_packages.serialization import canonical_json
from backend.workflow_packages.tests.test_forward_downstream_controlled_chain import (
    _answer,
    _harness,
    _ref,
    _write,
)

PROJECT_ID = "project-" + "4" * 32
WORKSPACE_ID = "workspace-" + "5" * 32
INSTANCE_ID = "wfi-" + "6" * 32


def _approved_revision_with_complete_draft(
    workspace: Path, tmp_path: Path
) -> tuple[Path, dict[str, bytes]]:
    idea, _ = _selected()
    library = _library()
    experiment, block = _v5()
    idea_bytes = (canonical_json(idea) + "\n").encode()
    library_bytes = (canonical_json(library) + "\n").encode()
    experiment_bytes = (canonical_json(experiment) + "\n").encode()
    sources = {
        "research_idea": _ref("a", "selected-research-idea/v1", idea_bytes),
        "literature_library": _ref(
            "b", "selected-paper-library/v1", library_bytes
        ),
        "experiment_record": _ref("e", "experiment-record/v5", experiment_bytes),
    }
    manuscript, _ = _manuscript(experiment, block, inputs=sources)
    manuscript_bytes = (canonical_json(manuscript) + "\n").encode()
    manuscript_ref = _ref("c", "manuscript-draft/v4", manuscript_bytes)
    review, _ = _review(
        manuscript, sources, experiment, manuscript_ref=manuscript_ref
    )
    review_bytes = (canonical_json(review) + "\n").encode()
    review_ref = _ref("d", "review-report/v3", review_bytes)

    root = build_writing_revision_v0_9_package(
        project_id=PROJECT_ID,
        project_name="Revision lifecycle recovery",
        research_topic="Controlled recovery",
        output_root=workspace / "capsules" / "revision",
        package_id="forward-revision-lifecycle-recovery",
    ).package_root
    _write(root / "inputs/prior-manuscript.json", manuscript)
    _write(root / "inputs/review-report.json", review)
    _write(root / "inputs/selected-research-idea.json", idea)
    _write(root / "inputs/selected-paper-library.json", library)
    _write(root / "inputs/experiment-record.json", experiment)
    exact_inputs = {
        "prior_manuscript": manuscript_ref,
        "causal_review": review_ref,
        **sources,
    }
    _write(
        root / "memory/input-provenance.json",
        {
            "schema_version": "reagent.writing-revision-input-provenance/v0.1",
            "workflow_instance_id": INSTANCE_ID,
            "artifacts": exact_inputs,
        },
    )
    runtime = runpy.run_path(str(root / "reagent_local.py"))
    with pytest.raises(Exception, match="did not approve the exact revised draft"):
        runtime["run"](
            root,
            INSTANCE_ID,
            codex_executable=str(_harness(tmp_path / "revision-codex", "revision")),
            approval_input=_answer,
            review_input=lambda _prompt: "do not finalize",
        )
    protected_paths = (
        root / "memory/revision-plan.json",
        root / "memory/revision-plan-approval.json",
        root / "outputs/revised-draft.md",
        root / "memory/claims.json",
        root / "memory/citations.json",
        root / "memory/issue-accounting.json",
    )
    assert not (root / "memory/owner-review.json").exists()
    assert not list((root / "outputs/artifacts/manuscript-draft").glob("*.json"))
    assert not list((root / "memory/progress/reports").glob("*.json"))
    return root, {path.as_posix(): path.read_bytes() for path in protected_paths}


def test_exact_plan_approval_resumes_at_owner_review_without_harness_relaunch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    root, protected = _approved_revision_with_complete_draft(workspace, tmp_path)
    manifest = json.loads((root / "package-manifest.json").read_text())
    descriptor = {"project_id": PROJECT_ID, "workspace_id": WORKSPACE_ID}
    installed = {
        "workflow_instance_id": INSTANCE_ID,
        "workflow_definition_id": "writing-local-experimental",
        "workflow_definition_version": "0.7.0",
        "capsule_version": "0.9.0",
        "relative_path": root.relative_to(workspace).as_posix(),
        "lifecycle": "ACTIVE",
    }
    monkeypatch.setattr(
        workspace_cli, "load_workspace", lambda _root: (workspace, descriptor, {})
    )
    monkeypatch.setattr(
        workspace_cli,
        "_require_installed_lock",
        lambda *_args: {"installed_capsules": [installed]},
    )
    monkeypatch.setattr(workspace_cli, "_verify_locked_capsules", lambda *_args: None)

    prepared: list[str] = []

    def exact_inputs_already_prepared(**kwargs):
        assert kwargs["workflow_instance_id"] == INSTANCE_ID
        assert kwargs["writing_revision"] is True
        prepared.append(INSTANCE_ID)

    monkeypatch.setattr(
        workspace_cli,
        "_prepare_scaffold_input_provenance",
        exact_inputs_already_prepared,
    )

    def harness_must_not_run(*_args, **_kwargs):
        raise AssertionError("complete approved Revision recovery must not launch Harness")

    monkeypatch.setattr(workspace_cli.subprocess, "run", harness_must_not_run)
    monkeypatch.setattr(backlog, "PROJECT_ID", PROJECT_ID)
    monkeypatch.setattr(backlog, "INSTANCE_ID", INSTANCE_ID)
    transport = backlog._ProgressTransport()

    first = workspace_cli.run_workflow(
        workspace_root=workspace,
        workflow_instance_id=INSTANCE_ID,
        transport=transport,
        api_url="http://127.0.0.1:8000",
        consent_input=lambda _prompt: "Approve",
    )
    owner_bytes = (root / "memory/owner-review.json").read_bytes()
    artifacts = list((root / "outputs/artifacts/manuscript-draft").glob("*.json"))
    reports = list((root / "memory/progress/reports").glob("prv2-*.json"))
    second = workspace_cli.run_workflow(
        workspace_root=workspace,
        workflow_instance_id=INSTANCE_ID,
        transport=transport,
        api_url="http://127.0.0.1:8000",
        consent_input=lambda _prompt: pytest.fail("replay must not ask for approval"),
    )

    assert first.status == second.status == "PROGRESS_SYNCHRONIZED"
    assert prepared == [INSTANCE_ID]
    assert transport.uploaded_rounds == [1]
    assert len(transport.accepted) == len(artifacts) == len(reports) == 1
    assert (root / "memory/owner-review.json").read_bytes() == owner_bytes
    assert {
        path: Path(path).read_bytes() for path in protected
    } == protected
    artifact = json.loads(artifacts[0].read_text())
    assert artifact["schema"] == "manuscript-draft/v5"
    assert [
        (item["issue_id"], item["disposition"])
        for item in artifact["issue_accounting"]
    ] == [("issue-1", "ADDRESSED")]
    assert artifact["revision_plan_approval"] == json.loads(
        (root / "memory/revision-plan-approval.json").read_text()
    )
    assert manifest["workflow_version"] == "0.7.0"
