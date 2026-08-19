from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

from backend.artifact_references.tests.test_forward_downstream_v5_contracts import (
    _manuscript,
    _v5,
)
from backend.artifact_references.tests.test_research_flow_contracts import (
    _library,
    _selected,
)
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.tests import test_progress_backlog_recovery as backlog
from backend.workflow_packages.forward_downstream_publication import (
    build_review_v0_6_package,
)
from backend.workflow_packages.serialization import canonical_json
from backend.workflow_packages.tests.test_forward_downstream_controlled_chain import (
    _answer,
    _harness,
    _ref,
    _write,
)

PROJECT_ID = "project-" + "7" * 32
WORKSPACE_ID = "workspace-" + "6" * 32
INSTANCE_ID = "wfi-" + "8" * 32


def test_approved_scoped_review_recovers_once_without_harness_relaunch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    root = build_review_v0_6_package(
        project_id=PROJECT_ID,
        project_name="Scoped Review recovery",
        research_topic="Bounded recovery",
        output_root=workspace / "capsules" / "review",
        package_id="forward-review-recovery",
    ).package_root
    idea, _ = _selected()
    library = _library()
    experiment, block = _v5()
    idea_bytes = (canonical_json(idea) + "\n").encode()
    library_bytes = _write(root / "inputs/selected-paper-library.json", library)
    experiment_bytes = _write(root / "inputs/experiment-record.json", experiment)
    sources = {
        "research_idea": _ref("a", "selected-research-idea/v1", idea_bytes),
        "literature_library": _ref(
            "b", "selected-paper-library/v1", library_bytes
        ),
        "experiment_record": _ref("e", "experiment-record/v5", experiment_bytes),
    }
    manuscript, _ = _manuscript(experiment, block, inputs=sources)
    manuscript_bytes = _write(root / "inputs/manuscript-draft.json", manuscript)
    manuscript_ref = _ref("c", "manuscript-draft/v4", manuscript_bytes)
    review_sources = {
        "manuscript": manuscript_ref,
        "literature_library": sources["literature_library"],
        "experiment_record": sources["experiment_record"],
    }
    _write(root / "memory/input-provenance.json", {
        "schema_version": "reagent.real-review-input-provenance/v0.1",
        "workflow_instance_id": INSTANCE_ID,
        "artifacts": review_sources,
    })

    runtime = runpy.run_path(str(root / "reagent_local.py"))
    with pytest.raises(Exception, match="manuscript sources differ from exact bindings"):
        runtime["run"](
            root,
            INSTANCE_ID,
            codex_executable=str(_harness(tmp_path / "review-codex", "review")),
            approval_input=_answer,
            review_input=_answer,
        )
    assert not list((root / "outputs/artifacts/review-report").glob("*.json"))
    assert not list((root / "memory/progress/reports").glob("*.json"))
    protected_paths = (
        root / "inputs/manuscript-draft.json",
        root / "memory/input-provenance.json",
        root / "memory/review-result.json",
        root / "memory/owner-review.json",
    )
    protected = {path: path.read_bytes() for path in protected_paths}

    manifest = json.loads((root / "package-manifest.json").read_text())
    descriptor = {"project_id": PROJECT_ID, "workspace_id": WORKSPACE_ID}
    installed = {
        "workflow_instance_id": INSTANCE_ID,
        "workflow_definition_id": "review-local-experimental",
        "workflow_definition_version": "0.4.0",
        "capsule_version": "0.6.0",
        "relative_path": root.relative_to(workspace).as_posix(),
        "lifecycle": "ACTIVE",
    }
    monkeypatch.setattr(
        workspace_cli, "load_workspace", lambda _root: (workspace, descriptor, {})
    )
    monkeypatch.setattr(
        workspace_cli, "_require_installed_lock",
        lambda *_args: {"installed_capsules": [installed]},
    )
    monkeypatch.setattr(workspace_cli, "_verify_locked_capsules", lambda *_args: None)

    prepared: list[str] = []

    def exact_inputs_already_prepared(**kwargs):
        assert kwargs["workflow_instance_id"] == INSTANCE_ID
        assert kwargs["real_review"] is True
        assert json.loads((root / "memory/input-provenance.json").read_text())[
            "artifacts"
        ] == review_sources
        prepared.append(INSTANCE_ID)

    monkeypatch.setattr(
        workspace_cli, "_prepare_scaffold_input_provenance", exact_inputs_already_prepared
    )

    def harness_must_not_run(*_args, **_kwargs):
        raise AssertionError("approved Review recovery must not launch the Harness")

    monkeypatch.setattr(workspace_cli.subprocess, "run", harness_must_not_run)
    monkeypatch.setattr(backlog, "PROJECT_ID", PROJECT_ID)
    monkeypatch.setattr(backlog, "INSTANCE_ID", INSTANCE_ID)
    transport = backlog._ProgressTransport()

    first = workspace_cli.run_workflow(
        workspace_root=workspace,
        workflow_instance_id=INSTANCE_ID,
        transport=transport,
        api_url="http://127.0.0.1:8000",
    )
    second = workspace_cli.run_workflow(
        workspace_root=workspace,
        workflow_instance_id=INSTANCE_ID,
        transport=transport,
        api_url="http://127.0.0.1:8000",
    )

    artifacts = list((root / "outputs/artifacts/review-report").glob("*.json"))
    reports = list((root / "memory/progress/reports").glob("prv2-*.json"))
    assert first.status == second.status == "PROGRESS_SYNCHRONIZED"
    assert prepared == [INSTANCE_ID]
    assert transport.uploaded_rounds == [1]
    assert len(transport.accepted) == len(artifacts) == len(reports) == 1
    artifact = json.loads(artifacts[0].read_text())
    assert artifact["schema"] == "review-report/v3"
    assert artifact["supporting_artifacts"] == [
        sources["literature_library"], sources["experiment_record"]
    ]
    assert {path: path.read_bytes() for path in protected_paths} == protected
    assert workspace_cli._forward_review_validator(root)["validate"](
        root, pristine=False
    )["valid"] is True
