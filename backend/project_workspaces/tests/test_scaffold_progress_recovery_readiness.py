from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

from backend.project_workspaces import workspace_cli
from backend.project_workspaces.production_workflows import (
    EXPERIMENT_V0_4_CAPSULE_CHECKSUM,
    EXPERIMENT_V0_4_CAPSULE_ID,
    SCAFFOLD_V0_3_CAPSULE_CHECKSUMS,
    SCAFFOLD_V0_3_CAPSULE_IDS,
)
from backend.workflow_packages.production_workflows import (
    EXPERIMENT_WORKFLOW_ID,
    WRITING_WORKFLOW_ID,
    build_experiment_scaffold_v0_4_package,
    build_writing_scaffold_v0_3_package,
)
from backend.workflow_packages.forward_downstream_publication import (
    build_initial_writing_v0_7_package,
)
from backend.workflow_packages.serialization import canonical_hash, canonical_json
from backend.workflow_packages.tests.test_forward_downstream_controlled_chain import (
    _answer as _forward_answer,
    _harness as _forward_harness,
    _ref as _forward_ref,
    _write as _forward_write,
)
from backend.artifact_references.tests.test_forward_downstream_v5_contracts import (
    _v5,
)
from backend.artifact_references.tests.test_research_flow_contracts import (
    _library,
    _selected,
)
from backend.workflow_packages.tests.test_experiment_interactive_bootstrap import (
    _materialize as _materialize_experiment,
)
from backend.workflow_packages.tests.test_writing_review_interactive_bootstrap import (
    _materialize as _materialize_writing_review,
)
from backend.project_workspaces.tests import test_progress_backlog_recovery as backlog

PROJECT_ID = "project-" + "7" * 32
WORKSPACE_ID = "workspace-" + "6" * 32
INSTANCE_ID = "wfi-" + "8" * 32
OTHER_INSTANCE_ID = "wfi-" + "9" * 32


def test_completed_forward_real_writing_recovers_without_harness_relaunch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    root = build_initial_writing_v0_7_package(
        project_id=PROJECT_ID,
        project_name="Forward Writing recovery",
        research_topic="Bounded recovery",
        output_root=workspace / "capsules" / "writing",
        package_id="forward-writing-recovery",
    ).package_root
    idea, _ = _selected()
    library = _library()
    experiment, _ = _v5()
    idea_bytes = _forward_write(root / "inputs/selected-research-idea.json", idea)
    library_bytes = _forward_write(root / "inputs/selected-paper-library.json", library)
    experiment_bytes = _forward_write(root / "inputs/experiment-record.json", experiment)
    _forward_write(root / "memory/input-provenance.json", {
        "schema_version": "reagent.real-writing-input-provenance/v0.1",
        "workflow_instance_id": INSTANCE_ID,
        "artifacts": {
            "research_idea": _forward_ref(
                "a", "selected-research-idea/v1", idea_bytes
            ),
            "literature_library": _forward_ref(
                "b", "selected-paper-library/v1", library_bytes
            ),
            "experiment_record": _forward_ref(
                "e", "experiment-record/v5", experiment_bytes
            ),
        },
    })
    runtime = runpy.run_path(str(root / "reagent_local.py"))
    completed = runtime["run"](
        root,
        INSTANCE_ID,
        codex_executable=str(_forward_harness(tmp_path / "forward-writing-codex", "writing")),
        approval_input=_forward_answer,
        review_input=_forward_answer,
    )
    artifact_path = root / completed["artifact"]["relative_path"]
    report_paths = list((root / "memory/progress/reports").glob("prv2-*.json"))
    assert len(report_paths) == 1
    protected = {
        artifact_path: artifact_path.read_bytes(),
        root / "memory/owner-review.json": (root / "memory/owner-review.json").read_bytes(),
        report_paths[0]: report_paths[0].read_bytes(),
    }
    manifest = json.loads((root / "package-manifest.json").read_text())
    assert runpy.run_path(str(root / "validate_package.py"))["validate"](root)["valid"] is True

    descriptor = {"project_id": PROJECT_ID, "workspace_id": WORKSPACE_ID}
    installed = {
        "workflow_instance_id": INSTANCE_ID,
        "workflow_definition_id": "writing-local-experimental",
        "workflow_definition_version": "0.5.0",
        "capsule_version": "0.7.0",
        "relative_path": root.relative_to(workspace).as_posix(),
        "lifecycle": "ACTIVE",
    }
    lock = {"installed_capsules": [installed]}
    monkeypatch.setattr(
        workspace_cli, "load_workspace", lambda _root: (workspace, descriptor, {})
    )
    monkeypatch.setattr(
        workspace_cli, "_require_installed_lock", lambda *_args: lock
    )
    monkeypatch.setattr(
        workspace_cli, "_verify_locked_capsules", lambda *_args: None
    )

    def scaffold_provenance_must_not_run(*_args, **_kwargs):
        raise AssertionError("Forward Real Writing is not a Scaffold Workflow")

    monkeypatch.setattr(
        workspace_cli, "_scaffold_provenance_is_exact", scaffold_provenance_must_not_run
    )

    def harness_must_not_run(*_args, **_kwargs):
        raise AssertionError("upload-only recovery must not launch the Harness")

    monkeypatch.setattr(workspace_cli.subprocess, "run", harness_must_not_run)
    monkeypatch.setattr(backlog, "PROJECT_ID", PROJECT_ID)
    monkeypatch.setattr(backlog, "INSTANCE_ID", INSTANCE_ID)

    class RecordingTransport(backlog._ProgressTransport):
        def __init__(self):
            super().__init__()
            self.envelopes: list[dict] = []

        def upload_progress_report(
            self, project_id, workflow_instance_id, package_manifest, report, envelope
        ):
            self.envelopes.append(envelope)
            return super().upload_progress_report(
                project_id, workflow_instance_id, package_manifest, report, envelope
            )

    transport = RecordingTransport()
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

    assert first.status == second.status == "PROGRESS_SYNCHRONIZED"
    assert transport.uploaded_rounds == [1]
    assert len(transport.accepted) == 1
    assert len(transport.envelopes) == 1
    assert [item["artifact_type"] for item in transport.envelopes[0]["artifact_declarations"]] == [
        "manuscript-draft/v4"
    ]
    assert len(list((root / "memory/progress/reports").glob("prv2-*.json"))) == 1
    assert len(list(artifact_path.parent.glob("*.json"))) == 1
    assert {path: path.read_bytes() for path in protected} == protected
    readiness = workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace,
        descriptor=descriptor,
        installed=installed,
        capsule=root,
        manifest=manifest,
    )
    assert readiness.state == "ACKNOWLEDGED"


def _legacy_state(
    tmp_path: Path, workflow_id: str, *, human_output_drift: bool = False,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    relative = f"capsules/{INSTANCE_ID}"
    builder = (
        build_writing_scaffold_v0_3_package
        if workflow_id == WRITING_WORKFLOW_ID
        else build_experiment_scaffold_v0_4_package
    )
    package = builder(
        project_id=PROJECT_ID,
        project_name="Legacy recovery fixture",
        research_topic="Synthetic bounded recovery",
        output_root=workspace / relative,
        package_id=f"legacy-{workflow_id}",
    )
    root = package.package_root
    relative = root.relative_to(workspace).as_posix()
    if workflow_id == WRITING_WORKFLOW_ID:
        _materialize_writing_review(root, workflow_id)
        definition_version, capsule_version = "0.2.0", "0.3.0"
        capsule_id = SCAFFOLD_V0_3_CAPSULE_IDS[workflow_id]
        capsule_definition_checksum = SCAFFOLD_V0_3_CAPSULE_CHECKSUMS[workflow_id]
    else:
        _materialize_experiment(root)
        definition_version, capsule_version = "0.3.0", "0.4.0"
        capsule_id = EXPERIMENT_V0_4_CAPSULE_ID
        capsule_definition_checksum = EXPERIMENT_V0_4_CAPSULE_CHECKSUM
    manifest = json.loads((root / "package-manifest.json").read_text())
    descriptor = {"project_id": PROJECT_ID, "workspace_id": WORKSPACE_ID}
    installed = {
        "workflow_instance_id": INSTANCE_ID,
        "workflow_definition_id": workflow_id,
        "workflow_definition_version": definition_version,
        "capsule_version": capsule_version,
        "capsule_id": capsule_id,
        "capsule_definition_checksum": capsule_definition_checksum,
        "package_id": manifest["package_id"],
        "package_checksum": manifest["package_checksum"],
        "manifest_checksum": manifest["manifest_checksum"],
        "immutable_contract_checksum": workspace_cli._immutable_contract_checksum(
            root, manifest
        ),
        "relative_path": root.relative_to(workspace).as_posix(),
        "lifecycle": "ACTIVE",
        "verification_status": "VERIFIED",
    }
    receipts = workspace / workspace_cli.MATERIALIZATION_RECEIPTS_ROOT
    receipts.mkdir(parents=True)
    provenance = json.loads((root / "memory/input-provenance.json").read_text())
    for index, (key, record) in enumerate(provenance["artifacts"].items(), 1):
        payload = {
            "schema_version": workspace_cli.MATERIALIZATION_RECEIPT_SCHEMA,
            "project_id": PROJECT_ID,
            "workspace_id": WORKSPACE_ID,
            "consumer_workflow_instance_id": INSTANCE_ID,
            "requirement_key": key,
            "binding_id": "artifact-binding-" + f"{index:032x}",
            "artifact_id": record["artifact_id"],
            "producer_workflow_instance_id": "wfi-" + f"{index:032x}",
            "artifact_type": record["artifact_type"],
            "artifact_schema_version": record["artifact_type"],
            "source_checksum": record["sha256"],
            "target_relative_path": f"{relative}/{record['relative_path']}",
            "target_checksum": record["sha256"],
            "materialized_at": "2026-08-13T00:00:00Z",
            "materialization_version": "0.1.0",
            "plan_checksum": "sha256:" + f"{index:064x}",
        }
        value = {**payload, "receipt_checksum": canonical_hash(payload)}
        (receipts / f"{value['binding_id']}.json").write_text(
            canonical_json(value) + "\n", encoding="utf-8"
        )
    runtime = runpy.run_path(str(root / "reagent_local.py"))
    config = json.loads((root / "workflow/scaffold.json").read_text())
    context_before = runtime["_prepare_draft"](root, config)
    artifact = runtime["_publish"](root, config)
    if human_output_drift:
        if workflow_id != EXPERIMENT_WORKFLOW_ID:
            raise ValueError("human-output drift fixture is limited to Experiment 0.4")
        human_path = root / config["human_output_path"]
        human_path.write_bytes(
            human_path.read_bytes()
            + b"\n## Owner-reviewed bounded scaffold plan\n\n"
            + b"This synthetic plan A preserves the SCAFFOLD EXPERIMENT PLACEHOLDER "
            + b"boundary while recording an owner-reviewed interaction. No Resource "
            + b"bytes were executed and no metrics or results are claimed.\n"
        )
    runtime["_update_context"](root, config, artifact)
    report_path = runtime["_finalize"](root, context_before)
    # Reproduce the exact historical second runner update after report N.
    runtime["_publish"](root, config)
    runtime["_update_context"](root, config, artifact)
    if human_output_drift:
        with pytest.raises(Exception, match="execution round must increment"):
            runtime["_finalize"](root, context_before)
    report = json.loads(report_path.read_text())
    return workspace, descriptor, installed, root, manifest, report


@pytest.mark.parametrize("workflow_id", (WRITING_WORKFLOW_ID, EXPERIMENT_WORKFLOW_ID))
def test_exact_historical_scaffold_drift_is_recoverable_and_tamper_fails_closed(
    tmp_path: Path, workflow_id: str,
) -> None:
    workspace, descriptor, installed, root, manifest, report = _legacy_state(
        tmp_path, workflow_id
    )
    readiness = workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    )
    assert readiness.state == "RECOVERABLE_KNOWN_LEGACY_SCAFFOLD_DRIFT"
    assert [item["report_id"] for item in readiness.reports] == [report["report_id"]]


@pytest.mark.parametrize(
    "field",
    (
        "capsule_id", "capsule_definition_checksum", "verification_status",
        "immutable_contract_checksum", "package_template_id",
        "generator_version", "workflow_checksum",
    ),
)
def test_historical_experiment_output_drift_requires_exact_release_identity(
    tmp_path: Path, field: str,
) -> None:
    workspace, descriptor, installed, root, manifest, _ = _legacy_state(
        tmp_path, EXPERIMENT_WORKFLOW_ID, human_output_drift=True
    )
    if field in installed:
        installed[field] = "INVALID"
    else:
        manifest[field] = "INVALID"
    assert workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    ).state == "INVALID"

    current = json.loads((root / "memory/current-artifact.json").read_text())
    artifact = root / current["relative_path"]
    artifact.write_bytes(artifact.read_bytes() + b"\n")
    rejected = workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    )
    assert rejected.state == "INVALID"


def test_exact_historical_experiment_human_output_and_context_drift_is_recoverable(
    tmp_path: Path,
) -> None:
    workspace, descriptor, installed, root, manifest, report = _legacy_state(
        tmp_path, EXPERIMENT_WORKFLOW_ID, human_output_drift=True
    )
    human = next(
        item for item in report["output_artifacts"]
        if item["relative_path"] == "outputs/experiment_plan.md"
    )
    current_human = root / "outputs/experiment_plan.md"
    assert workspace_cli.sha256_bytes(current_human.read_bytes()) != human["checksum"]
    current = json.loads((root / "memory/current-artifact.json").read_text())
    typed = next(
        item for item in report["output_artifacts"]
        if item["artifact_kind"] == "experiment-record/v1"
    )
    assert current == typed
    assert workspace_cli.sha256_bytes((root / current["relative_path"]).read_bytes()) == (
        typed["checksum"]
    )

    readiness = workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    )
    assert readiness.state == (
        "RECOVERABLE_KNOWN_LEGACY_EXPERIMENT_0_4_OUTPUT_DRIFT"
    )
    assert [item["report_id"] for item in readiness.reports] == [report["report_id"]]


def test_historical_experiment_human_output_drift_uploads_without_research_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, descriptor, installed, root, manifest, report = _legacy_state(
        tmp_path, EXPERIMENT_WORKFLOW_ID, human_output_drift=True
    )
    readiness = workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    )
    assert readiness.state == (
        "RECOVERABLE_KNOWN_LEGACY_EXPERIMENT_0_4_OUTPUT_DRIFT"
    )
    protected = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in (
            root / "outputs/experiment_plan.md",
            root / "memory/context.md",
            root / "memory/progress/reports" / f"{report['report_id']}.json",
            root
            / json.loads((root / "memory/current-artifact.json").read_text())[
                "relative_path"
            ],
        )
    }
    monkeypatch.setattr(backlog, "PROJECT_ID", PROJECT_ID)
    monkeypatch.setattr(backlog, "INSTANCE_ID", INSTANCE_ID)
    transport = backlog._ProgressTransport()

    assert workspace_cli._recover_progress_backlog(
        workspace=workspace,
        descriptor=descriptor,
        installed=installed,
        capsule=root,
        manifest=manifest,
        reports=list(readiness.reports),
        transport=transport,
    ) == 1
    assert transport.uploaded_rounds == [1]
    assert transport.accepted[0]["report_id"] == report["report_id"]
    assert {
        relative: (root / relative).read_bytes() for relative in protected
    } == protected
    assert len(list((root / "memory/progress/reports").glob("prv2-*.json"))) == 1
    assert workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    ).state == "ACKNOWLEDGED"


@pytest.mark.parametrize("operation", ("list", "refresh", "sync", "restart"))
def test_acknowledged_experiment_output_drift_remains_stable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str,
) -> None:
    workspace, descriptor, installed, root, manifest, _ = _legacy_state(
        tmp_path, EXPERIMENT_WORKFLOW_ID, human_output_drift=True
    )
    readiness = workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    )
    monkeypatch.setattr(backlog, "PROJECT_ID", PROJECT_ID)
    monkeypatch.setattr(backlog, "INSTANCE_ID", INSTANCE_ID)
    assert workspace_cli._recover_progress_backlog(
        workspace=workspace,
        descriptor=descriptor,
        installed=installed,
        capsule=root,
        manifest=manifest,
        reports=list(readiness.reports),
        transport=backlog._ProgressTransport(),
    ) == 1
    if operation == "list":
        assert workspace_cli._evaluate_local_progress_readiness(
            workspace=workspace, descriptor=descriptor, installed=installed,
            capsule=root, manifest=manifest,
        ).state == "ACKNOWLEDGED"
    elif operation == "refresh":
        path = workspace / workspace_cli.ARTIFACT_INDEX
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("unrelated refresh\n")
    elif operation == "sync":
        path = workspace / workspace_cli.DESIRED_MANIFEST_CACHE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("semantic no-op sync\n")
    else:
        manifest = json.loads((root / "package-manifest.json").read_text())

    assert workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    ).state == "ACKNOWLEDGED"


@pytest.mark.parametrize(
    "case",
    (
        "human_one_byte", "human_arbitrary", "human_whitespace",
        "human_title", "human_body", "typed_byte", "typed_checksum",
        "report_changed", "wrong_report_id", "wrong_project",
        "wrong_workflow", "wrong_capsule", "wrong_package", "wrong_round",
        "wrong_predecessor", "extra_report", "context_round",
        "context_artifact", "context_continuation", "context_extra",
        "context_time", "input_provenance", "human_symlink", "cross_instance",
    ),
)
def test_historical_experiment_human_output_drift_tamper_matrix_fails_closed(
    tmp_path: Path, case: str,
) -> None:
    workspace, descriptor, installed, root, manifest, report = _legacy_state(
        tmp_path, EXPERIMENT_WORKFLOW_ID, human_output_drift=True
    )
    human = root / "outputs/experiment_plan.md"
    current_path = root / "memory/current-artifact.json"
    current = json.loads(current_path.read_text())
    typed = root / current["relative_path"]
    report_path = root / "memory/progress/reports" / f"{report['report_id']}.json"
    context_path = root / "memory/context.md"
    provenance_path = root / "memory/input-provenance.json"

    def mutate_context(change) -> None:
        raw = context_path.read_text()
        value = json.loads(raw.split("```json\n", 1)[1].rsplit("\n```", 1)[0])
        change(value)
        context_path.write_text(
            "# Scaffold Workflow Context\n\n```json\n"
            + canonical_json(value) + "\n```\n",
            encoding="utf-8",
        )

    if case == "human_one_byte":
        value = human.read_bytes()
        human.write_bytes(value[:-1] + bytes([value[-1] ^ 1]))
    elif case == "human_arbitrary":
        human.write_text("# SCAFFOLD EXPERIMENT PLACEHOLDER\n\narbitrary\n")
    elif case == "human_whitespace":
        human.write_bytes(human.read_bytes() + b" ")
    elif case == "human_title":
        human.write_bytes(
            human.read_bytes().replace(
                b"PLACEHOLDER", b"PLACEHOLDER ALTERED", 1
            )
        )
    elif case == "human_body":
        human.write_bytes(
            human.read_bytes().replace(
                b"No real experiment", b"No actual experiment", 1
            )
        )
    elif case == "typed_byte":
        typed.write_bytes(typed.read_bytes() + b"\n")
    elif case == "typed_checksum":
        current["checksum"] = "sha256:" + "f" * 64
        current_path.write_text(canonical_json(current) + "\n")
    elif case == "report_changed":
        report["warnings"].append("changed")
        report_path.write_text(canonical_json(report) + "\n")
    elif case == "wrong_report_id":
        report["report_id"] = "prv2-" + "f" * 64
        report_path.write_text(canonical_json(report) + "\n")
    elif case == "wrong_project":
        report["project_id"] = "project-" + "9" * 32
        report_path.write_text(canonical_json(report) + "\n")
    elif case == "wrong_workflow":
        report["workflow_id"] = WRITING_WORKFLOW_ID
        report_path.write_text(canonical_json(report) + "\n")
    elif case == "wrong_capsule":
        installed["capsule_version"] = "0.3.0"
    elif case == "wrong_package":
        installed["package_id"] = "different-package"
    elif case == "wrong_round":
        report["execution_round"] = 2
        report_path.write_text(canonical_json(report) + "\n")
    elif case == "wrong_predecessor":
        report["previous_report_id"] = "prv2-" + "e" * 64
        report["previous_report_checksum"] = "sha256:" + "e" * 64
        report_path.write_text(canonical_json(report) + "\n")
    elif case == "extra_report":
        (report_path.parent / ("prv2-" + "e" * 64 + ".json")).write_bytes(
            report_path.read_bytes()
        )
    elif case == "context_round":
        mutate_context(lambda value: value.__setitem__("completed_rounds", 3))
    elif case == "context_artifact":
        mutate_context(
            lambda value: value["latest_artifact"].__setitem__("size", 0)
        )
    elif case == "context_continuation":
        mutate_context(lambda value: value.__setitem__("continuation", "unexpected"))
    elif case == "context_extra":
        mutate_context(lambda value: value.__setitem__("unexpected", True))
    elif case == "context_time":
        mutate_context(
            lambda value: value.__setitem__(
                "updated_at", "2020-01-01T00:00:00Z"
            )
        )
    elif case == "input_provenance":
        provenance = json.loads(provenance_path.read_text())
        provenance["artifacts"]["research_idea"]["sha256"] = "sha256:" + "d" * 64
        provenance_path.write_text(canonical_json(provenance) + "\n")
    elif case == "human_symlink":
        human.unlink()
        human.symlink_to(root / "README.md")
    elif case == "cross_instance":
        provenance = json.loads(provenance_path.read_text())
        provenance["workflow_instance_id"] = OTHER_INSTANCE_ID
        provenance_path.write_text(canonical_json(provenance) + "\n")

    readiness = workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    )
    assert readiness.state == "INVALID"


def test_arbitrary_context_mismatch_is_not_a_legacy_recovery_fingerprint(
    tmp_path: Path,
) -> None:
    workspace, descriptor, installed, root, manifest, _ = _legacy_state(
        tmp_path, WRITING_WORKFLOW_ID
    )
    context = root / "memory/context.md"
    context.write_text(context.read_text().replace("N+1", "arbitrary"), encoding="utf-8")
    # The literal may not exist; add an unexpected semantic field either way.
    raw = context.read_text()
    value = json.loads(raw.split("```json\n", 1)[1].rsplit("\n```", 1)[0])
    value["unexpected"] = True
    context.write_text(
        "# Scaffold Workflow Context\n\n```json\n" + canonical_json(value) + "\n```\n",
        encoding="utf-8",
    )
    readiness = workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    )
    assert readiness.state == "INVALID"


@pytest.mark.parametrize("workflow_id", (WRITING_WORKFLOW_ID, EXPERIMENT_WORKFLOW_ID))
def test_historical_scaffold_drift_uploads_exact_report_without_local_mutation(
    tmp_path: Path, workflow_id: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, descriptor, installed, root, manifest, report = _legacy_state(
        tmp_path, workflow_id
    )
    readiness = workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    )
    assert readiness.state == "RECOVERABLE_KNOWN_LEGACY_SCAFFOLD_DRIFT"
    monkeypatch.setattr(backlog, "PROJECT_ID", PROJECT_ID)
    monkeypatch.setattr(backlog, "INSTANCE_ID", INSTANCE_ID)
    transport = backlog._ProgressTransport()
    context_before = (root / "memory/context.md").read_bytes()
    output_before = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted((root / "outputs").rglob("*")) if path.is_file()
    }

    assert workspace_cli._recover_progress_backlog(
        workspace=workspace,
        descriptor=descriptor,
        installed=installed,
        capsule=root,
        manifest=manifest,
        reports=list(readiness.reports),
        transport=transport,
    ) == 1
    assert transport.uploaded_rounds == [1]
    assert transport.accepted[0]["report_id"] == report["report_id"]
    assert (root / "memory/context.md").read_bytes() == context_before
    assert {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted((root / "outputs").rglob("*")) if path.is_file()
    } == output_before
    assert len(list((root / "memory/progress/reports").glob("prv2-*.json"))) == 1
    acknowledged = workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    )
    assert acknowledged.state == "ACKNOWLEDGED"


@pytest.mark.parametrize("workflow_id", (WRITING_WORKFLOW_ID, EXPERIMENT_WORKFLOW_ID))
def test_list_continue_and_run_share_legacy_readiness_without_harness(
    tmp_path: Path, workflow_id: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, descriptor, installed, root, _manifest, _ = _legacy_state(
        tmp_path, workflow_id
    )
    active = dict(installed)
    lock = {"installed_capsules": [active]}
    lock_path = workspace / workspace_cli.INSTALLED_LOCK
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        workspace_cli, "load_workspace",
        lambda _root: (workspace, descriptor, {}),
    )
    monkeypatch.setattr(workspace_cli, "_require_installed_lock", lambda *_: lock)
    monkeypatch.setattr(workspace_cli, "_verify_locked_capsules", lambda *_: None)
    harness_calls: list[list[str]] = []

    def forbidden_harness(*args, **kwargs):
        harness_calls.append(list(args[0]))
        raise AssertionError("upload-only recovery must not launch a Harness")

    monkeypatch.setattr(workspace_cli.subprocess, "run", forbidden_harness)
    listing = workspace_cli.workflow_list(workspace)
    listed = listing["workflows"][0]
    assert listed["local_readiness"] == "PROGRESS_UPLOAD_PENDING"
    assert listed["next_action"] == "CONTINUE"
    assert listed["next_command"] == listed["run_command"]

    monkeypatch.setattr(backlog, "PROJECT_ID", PROJECT_ID)
    monkeypatch.setattr(backlog, "INSTANCE_ID", INSTANCE_ID)
    result = workspace_cli.run_workflow(
        workspace_root=workspace,
        workflow_instance_id=INSTANCE_ID,
        transport=backlog._ProgressTransport(),
        api_url="http://127.0.0.1:9",
    )
    assert result.status == "PROGRESS_SYNCHRONIZED"
    assert harness_calls == []


def test_list_and_printed_run_share_experiment_output_drift_recovery_without_harness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, descriptor, installed, root, _manifest, report = _legacy_state(
        tmp_path, EXPERIMENT_WORKFLOW_ID, human_output_drift=True
    )
    lock = {"installed_capsules": [installed]}
    lock_path = workspace / workspace_cli.INSTALLED_LOCK
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        workspace_cli, "load_workspace", lambda _root: (workspace, descriptor, {})
    )
    monkeypatch.setattr(workspace_cli, "_require_installed_lock", lambda *_: lock)
    monkeypatch.setattr(workspace_cli, "_verify_locked_capsules", lambda *_: None)
    harness_calls: list[list[str]] = []

    def forbidden_harness(*args, **kwargs):
        harness_calls.append(list(args[0]))
        raise AssertionError("upload-only recovery must not launch a Harness")

    monkeypatch.setattr(workspace_cli.subprocess, "run", forbidden_harness)
    listing = workspace_cli.workflow_list(workspace)
    listed = listing["workflows"][0]
    assert listed["local_readiness"] == "PROGRESS_UPLOAD_PENDING"
    assert listed["next_action"] == "CONTINUE"
    assert listed["next_command"] == listed["run_command"]
    protected = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in (
            root / "outputs/experiment_plan.md",
            root / "memory/context.md",
            root / "memory/progress/reports" / f"{report['report_id']}.json",
            root
            / json.loads((root / "memory/current-artifact.json").read_text())[
                "relative_path"
            ],
        )
    }

    monkeypatch.setattr(backlog, "PROJECT_ID", PROJECT_ID)
    monkeypatch.setattr(backlog, "INSTANCE_ID", INSTANCE_ID)
    result = workspace_cli.run_workflow(
        workspace_root=workspace,
        workflow_instance_id=INSTANCE_ID,
        transport=backlog._ProgressTransport(),
        api_url="http://127.0.0.1:9",
    )
    assert result.status == "PROGRESS_SYNCHRONIZED"
    assert harness_calls == []
    assert {
        relative: (root / relative).read_bytes() for relative in protected
    } == protected
    completed = workspace_cli.workflow_list(workspace)["workflows"][0]
    assert completed["local_readiness"] == "COMPLETED"
    assert completed["next_action"] == "REVIEW_RESULT"


def test_invalid_experiment_output_drift_list_does_not_advertise_continue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, descriptor, installed, root, _manifest, _ = _legacy_state(
        tmp_path, EXPERIMENT_WORKFLOW_ID, human_output_drift=True
    )
    plan = root / "outputs/experiment_plan.md"
    plan.write_bytes(plan.read_bytes() + b" ")
    lock_path = workspace / workspace_cli.INSTALLED_LOCK
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        workspace_cli, "load_workspace", lambda _root: (workspace, descriptor, {})
    )
    monkeypatch.setattr(
        workspace_cli, "_require_installed_lock",
        lambda *_: {"installed_capsules": [installed]},
    )
    monkeypatch.setattr(workspace_cli, "_verify_locked_capsules", lambda *_: None)

    listed = workspace_cli.workflow_list(workspace)["workflows"][0]
    assert listed["local_readiness"] == "LOCAL_PROGRESS_INVALID"
    assert listed["next_action"] == "REPAIR_REQUIRED"
    assert listed["next_command"] is None


@pytest.mark.parametrize(
    "case",
    ("A", "B", "C", "D", "E", "F", "G", "H"),
)
@pytest.mark.parametrize("legacy_kind", ("writing", "experiment-output"))
def test_pending_completion_survives_unrelated_workspace_context_changes(
    tmp_path: Path, case: str, legacy_kind: str,
) -> None:
    workflow_id = (
        WRITING_WORKFLOW_ID
        if legacy_kind == "writing"
        else EXPERIMENT_WORKFLOW_ID
    )
    workspace, descriptor, installed, root, manifest, _ = _legacy_state(
        tmp_path,
        workflow_id,
        human_output_drift=legacy_kind == "experiment-output",
    )
    expected_state = (
        "RECOVERABLE_KNOWN_LEGACY_SCAFFOLD_DRIFT"
        if legacy_kind == "writing"
        else "RECOVERABLE_KNOWN_LEGACY_EXPERIMENT_0_4_OUTPUT_DRIFT"
    )
    if case == "B":
        # A read-only status projection must not consume or mutate readiness.
        assert workspace_cli._evaluate_local_progress_readiness(
            workspace=workspace, descriptor=descriptor, installed=installed,
            capsule=root, manifest=manifest,
        ).state == expected_state
    elif case == "C":
        (workspace / workspace_cli.ARTIFACT_INDEX).parent.mkdir(parents=True, exist_ok=True)
        (workspace / workspace_cli.ARTIFACT_INDEX).write_text("artifact refresh\n")
    elif case == "D":
        (workspace / workspace_cli.DESIRED_MANIFEST_CACHE).parent.mkdir(parents=True, exist_ok=True)
        (workspace / workspace_cli.DESIRED_MANIFEST_CACHE).write_text("semantic noop sync\n")
    elif case == "E":
        (workspace / "capsules" / OTHER_INSTANCE_ID).mkdir(parents=True)
    elif case == "F":
        payload = {
            "schema_version": workspace_cli.MATERIALIZATION_RECEIPT_SCHEMA,
            "project_id": PROJECT_ID,
            "workspace_id": WORKSPACE_ID,
            "consumer_workflow_instance_id": OTHER_INSTANCE_ID,
            "requirement_key": "unrelated",
            "binding_id": "artifact-binding-" + "f" * 32,
            "artifact_id": "artifact-" + "e" * 32,
            "producer_workflow_instance_id": "wfi-" + "d" * 32,
            "artifact_type": "selected-paper-library/v1",
            "artifact_schema_version": "selected-paper-library/v1",
            "source_checksum": "sha256:" + "c" * 64,
            "target_relative_path": "capsules/unrelated/input.json",
            "target_checksum": "sha256:" + "c" * 64,
            "materialized_at": "2026-08-14T00:00:00Z",
            "materialization_version": "0.1.0",
            "plan_checksum": "sha256:" + "b" * 64,
        }
        receipt = {**payload, "receipt_checksum": canonical_hash(payload)}
        receipts = workspace / workspace_cli.MATERIALIZATION_RECEIPTS_ROOT
        (receipts / f"{receipt['binding_id']}.json").write_text(
            canonical_json(receipt) + "\n", encoding="utf-8"
        )
    elif case == "G":
        unrelated = workspace / workspace_cli.PROGRESS_RECEIPTS_ROOT / OTHER_INSTANCE_ID
        unrelated.mkdir(parents=True)
        (unrelated / "receipt.json").write_text("{}\n", encoding="utf-8")
    elif case == "H":
        # A new evaluator invocation represents process/backend restart: all
        # authority is reloaded from durable local bytes.
        manifest = json.loads((root / "package-manifest.json").read_text())

    readiness = workspace_cli._evaluate_local_progress_readiness(
        workspace=workspace, descriptor=descriptor, installed=installed,
        capsule=root, manifest=manifest,
    )
    assert readiness.state == expected_state
