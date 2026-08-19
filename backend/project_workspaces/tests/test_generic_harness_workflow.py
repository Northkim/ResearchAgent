from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.artifact_references.generic_experiment_v5_contracts import (
    EvidenceKind,
    EvidenceSourceKind,
    EvidenceSourceRef,
    ScientificEvidenceBlock,
)
from backend.artifact_references.service import (
    _validate_generic_experiment_presentation,
)
from backend.project_workspaces.generic_harness_workflow import (
    advance_generic_harness_workflow,
)
from backend.project_workspaces.workspace_cli import (
    _progress_upload_envelope,
    _project_artifact_presentation,
)
from backend.workflow_packages.generic_experiment_contracts import (
    EvaluationValidity,
    NamedChecksum,
    ProcessOutcome,
    ScientificEvidenceStatus,
)
from backend.workflow_packages.generic_experiment_coordinator import (
    ExecutionEvidence,
    ExecutionOutput,
    SuppliedExecution,
)
from backend.workflow_packages.generic_harness_adapter import GenericHarnessEvaluation
from backend.workflow_packages.generic_harness_contracts import (
    GenericHarnessImplementationSpec,
    HarnessExecutionUnit,
    HarnessExpectedOutput,
)
from backend.workflow_packages.generic_harness_publication import (
    build_generic_harness_v0_11_package,
)
from backend.workflow_packages.serialization import canonical_hash, canonical_json, sha256_bytes

PROJECT = "project-" + "1" * 32
WORKFLOW = "wfi-" + "2" * 32
ARTIFACT = "artifact-" + "3" * 32
NOW = "2026-08-20T12:00:00Z"


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def _capsule(tmp_path: Path) -> Path:
    root = build_generic_harness_v0_11_package(
        project_id=PROJECT, project_name="Controlled Generic Experiment",
        research_topic="One deterministic comparison", output_root=tmp_path / "capsules",
        package_id="generic-harness-controlled",
    ).package_root
    idea = {
        "schema": "selected-research-idea/v1",
        "selected_idea": {
            "title": "Controlled comparison",
            "research_question": "Does one deterministic treatment change the result?",
        },
    }
    content = (canonical_json(idea) + "\n").encode()
    (root / "inputs/selected-research-idea.json").write_bytes(content)
    _write(root / "memory/input-provenance.json", {
        "schema_version": "reagent.generic-experiment-input-provenance/v0.1",
        "workflow_instance_id": WORKFLOW,
        "artifacts": {"research_idea": {
            "artifact_id": ARTIFACT, "artifact_type": "selected-research-idea/v1",
            "sha256": sha256_bytes(content),
        }},
    })
    return root


class _Transport:
    def __init__(self) -> None:
        self.request: dict | None = None
        self.consumptions = 0

    def report_run_approval(self, project_id, workflow_instance_id, document):
        assert project_id == PROJECT and workflow_instance_id == WORKFLOW
        self.request = {
            **document, "status": "REQUESTED", "owner_actor": None,
            "decision_reason": None, "decision_idempotency_key": None,
            "decided_at": None, "approval_checksum": None,
            "consumed_attempt_id": None, "consumed_at": None,
            "consumption_checksum": None,
        }
        return dict(self.request)

    def approve(self) -> None:
        assert self.request is not None
        decided_at = NOW
        approval_checksum = canonical_hash({
            "request_id": self.request["request_id"],
            "execution_plan_checksum": self.request["execution_plan_checksum"],
            "request_checksum": self.request["request_checksum"],
            "decision": "APPROVED", "owner_actor": "CONTROLLED_LOCAL_OWNER",
            "idempotency_key": "controlled-owner-approval", "decided_at": decided_at,
        })
        self.request.update({
            "status": "APPROVED", "owner_actor": "CONTROLLED_LOCAL_OWNER",
            "decision_idempotency_key": "controlled-owner-approval",
            "decided_at": decided_at, "approval_checksum": approval_checksum,
        })

    def observe_run_approval(self, project_id, workflow_instance_id):
        assert project_id == PROJECT and workflow_instance_id == WORKFLOW
        return {"request": None if self.request is None else dict(self.request),
                "next_action": "WAIT"}

    def consume_run_approval(
        self, project_id, workflow_instance_id, request_id, payload,
    ):
        assert self.request is not None and request_id == self.request["request_id"]
        self.consumptions += 1
        receipt = {
            "schema": "reagent.controlled-local-run-approval-consumption/v0.1",
            "request_id": request_id,
            "approval_checksum": self.request["approval_checksum"],
            "execution_plan_checksum": payload["execution_plan_checksum"],
            "attempt_id": payload["attempt_id"], "consumed_at": NOW,
        }
        receipt["consumption_checksum"] = canonical_hash(receipt)
        self.request.update({
            "status": "CONSUMED", "consumed_attempt_id": payload["attempt_id"],
            "consumed_at": NOW, "consumption_checksum": receipt["consumption_checksum"],
        })
        return {"approval": dict(self.request), "receipt": receipt}


class _Runner:
    def __init__(self, managed_root: Path) -> None:
        self.managed_root = managed_root
        self.calls = 0

    def execute(self, handoff):
        self.calls += 1
        content = b'{"primary_metric_delta":0.125}\n'
        output = self.managed_root / "outputs/unit-comparison/experiment-result"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(content)
        identity = NamedChecksum("experiment-result", sha256_bytes(content))
        evidence = ExecutionEvidence(
            handoff.plan.plan_checksum, handoff.approval.approval_checksum,
            handoff.consumption.consumption_checksum, ProcessOutcome.SUCCEEDED,
            (identity,), True, "DISABLED", NOW, NOW,
        )
        return SuppliedExecution(
            evidence, (ExecutionOutput("experiment-result", content),),
        )


def test_generic_harness_public_workflow_is_exact_resumable_and_idempotent(
    tmp_path: Path,
) -> None:
    capsule = _capsule(tmp_path)
    workspace = tmp_path / "workspace"
    managed = workspace / ".reagent/experiments" / WORKFLOW
    transport = _Transport()
    decisions: list[str] = []

    def decide(title, lines, explanation):
        assert lines and explanation
        decisions.append(title)

    def harness(root: Path, instruction: str) -> None:
        if "methodology-proposal.json" in instruction:
            _write(capsule / "memory/methodology-proposal.json", {
                "questions_or_hypotheses": ["Does the treatment change the outcome?"],
                "inputs_or_materials": ["The exact controlled Research Idea."],
                "protocol": ["Run one deterministic baseline-treatment comparison."],
                "observations_or_outputs": ["One bounded JSON metric."],
                "evaluation_criteria": ["Validate the declared primary metric."],
                "reproducibility_controls": ["Use one fixed deterministic unit."],
                "resource_constraints": ["Use only the exact materialized input."],
                "compute_constraints": ["Complete within thirty seconds."],
                "network_policy": "DISABLED",
                "assumptions": ["The controlled fixture is deterministic."],
                "claim_boundaries": ["No claim beyond the controlled comparison."],
                "unresolved_material_decisions": [],
            })
            return
        if "implementation-specification.json" in instruction:
            methodology = json.loads((capsule / "memory/methodology.json").read_text())
            objective = methodology["research_objective"]
            implementation = managed / "implementation"
            implementation.mkdir(parents=True, exist_ok=True)
            (implementation / "run.py").write_text("print('controlled')\n", encoding="utf-8")
            spec = GenericHarnessImplementationSpec(
                objective["objective_ref_checksum"], methodology["methodology_checksum"],
                "run.py", "PYTHON", ">=3.10,<4", (), ("PYTHON_SCRIPT",),
                (HarnessExpectedOutput(
                    "experiment-result", "result.json", "application/json"
                ),),
                (HarnessExecutionUnit(
                    "unit-comparison", ("--output", "result.json"),
                    ("experiment-result",), "Run the controlled comparison.",
                ),),
                (("python", "-m", "py_compile", "run.py"),),
                (("wall_time_seconds", "30"),), "DISABLED",
                ("Implement one deterministic comparison.",),
            )
            _write(managed / "contracts/implementation-specification.json", spec)
            return
        if "evaluation/evaluation.json" in instruction:
            supplied = json.loads(
                (managed / "execution/supplied-execution.json").read_text()
            )
            specification = json.loads(
                (managed / "contracts/implementation-specification.json").read_text()
            )
            evidence = supplied["evidence"]
            outputs = tuple(
                NamedChecksum(item["name"], item["checksum"])
                for item in evidence["outputs"]
            )
            payload = {"primary_metric_delta": 0.125}
            evaluation = GenericHarnessEvaluation(
                specification["specification_checksum"],
                evidence["execution_plan_checksum"], outputs, payload,
                EvaluationValidity.VALID,
                ScientificEvidenceStatus.SUPPORTS_BOUNDED_FINDINGS,
                ("Controlled orchestration evidence only.",), NOW, True,
            )
            _write(managed / "evaluation/evaluation.json", evaluation)
            block = ScientificEvidenceBlock(
                "evidence-primary-delta", EvidenceKind.SCALAR,
                "Primary metric delta", 0.125,
                (EvidenceSourceRef(
                    EvidenceSourceKind.RESULT_PAYLOAD, "result-payload",
                    canonical_hash(payload),
                ),),
            )
            _write(managed / "evaluation/evidence-blocks.json", [block])
            return
        raise AssertionError(f"unexpected Harness instruction: {instruction}")

    validation = lambda command, root: {
        "returncode": 0,
        "stdout_checksum": sha256_bytes(canonical_json(command).encode()),
        "stderr_checksum": sha256_bytes(b""),
    }
    runner = _Runner(managed)
    first = advance_generic_harness_workflow(
        capsule=capsule, workspace_root=workspace, project_id=PROJECT,
        workflow_instance_id=WORKFLOW, run_harness=harness,
        owner_decision=decide, transport=transport,
        validation_executor=validation, bounded_runner=runner,
    )
    assert first.status == "RUN_APPROVAL_REQUIRED"
    assert decisions == ["Experiment methodology is ready"]
    assert runner.calls == 0

    transport.approve()
    completed = advance_generic_harness_workflow(
        capsule=capsule, workspace_root=workspace, project_id=PROJECT,
        workflow_instance_id=WORKFLOW, run_harness=harness,
        owner_decision=decide, transport=transport,
        validation_executor=validation, bounded_runner=runner,
    )
    assert completed.status == "COMPLETED"
    assert decisions == [
        "Experiment methodology is ready", "Experiment evidence is ready for review",
    ]
    assert runner.calls == transport.consumptions == 1
    artifacts = tuple((capsule / "outputs/artifacts/experiment-record").glob("*.json"))
    reports = tuple((capsule / "memory/progress/reports").glob("*.json"))
    assert len(artifacts) == len(reports) == 1
    artifact_content = artifacts[0].read_bytes()
    presentation = _project_artifact_presentation(
        artifact={
            "artifact_id": "artifact-" + "4" * 32,
            "artifact_type": "experiment-record/v5",
            "content_checksum": sha256_bytes(artifact_content),
        },
        content=artifact_content,
    )
    assert presentation is not None
    assert presentation["schema"] == (
        "reagent.artifact-presentation.experiment-record/v0.2"
    )
    assert presentation["blocks"][:4] == [
        {
            "kind": "PROSE",
            "label": "Research objective",
            "value": "Does one deterministic treatment change the result?",
        },
        {"kind": "SCALAR", "label": "Process outcome", "value": "SUCCEEDED"},
        {"kind": "SCALAR", "label": "Evaluation validity", "value": "VALID"},
        {
            "kind": "SCALAR",
            "label": "Scientific evidence",
            "value": "SUPPORTS_BOUNDED_FINDINGS",
        },
    ]
    assert presentation["presentation_checksum"] == canonical_hash({
        key: value
        for key, value in presentation.items()
        if key != "presentation_checksum"
    })
    assert _validate_generic_experiment_presentation(presentation) == presentation
    report = json.loads(reports[0].read_text())
    envelope = _progress_upload_envelope(
        capsule, WORKFLOW, report,
        datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
    )
    assert envelope["artifact_declarations"] == [{
        "artifact_id": envelope["artifact_declarations"][0]["artifact_id"],
        "artifact_type": "experiment-record/v5",
        "artifact_schema_version": "experiment-record/v5",
        "media_type": "application/json",
        "relative_path": completed.artifact["relative_path"],
        "content_checksum": completed.artifact["checksum"],
        "size_bytes": completed.artifact["size"],
        "produced_at": report["completed_at"],
    }]

    replay = advance_generic_harness_workflow(
        capsule=capsule, workspace_root=workspace, project_id=PROJECT,
        workflow_instance_id=WORKFLOW, run_harness=harness,
        owner_decision=decide, transport=transport,
        validation_executor=validation, bounded_runner=runner,
    )
    assert replay == completed
    assert runner.calls == transport.consumptions == 1
    assert len(tuple((capsule / "outputs/artifacts/experiment-record").glob("*.json"))) == 1
    assert len(tuple((capsule / "memory/progress/reports").glob("*.json"))) == 1
