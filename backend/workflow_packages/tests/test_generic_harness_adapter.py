from __future__ import annotations

from pathlib import Path

from backend.artifact_references.generic_experiment_v5_contracts import (
    EvidenceKind,
    EvidenceSourceKind,
    EvidenceSourceRef,
    ScientificEvidenceBlock,
    finalize_experiment_record_v5,
)
from backend.workflow_packages.generic_experiment_contracts import (
    ContractRef,
    DesignApproval,
    EvaluationValidity,
    ExactIdentity,
    GenericMethodology,
    LocalRuntimeCandidate,
    NamedChecksum,
    ProcessOutcome,
    ResearchObjectiveRef,
    ScientificEvidenceStatus,
)
from backend.workflow_packages.generic_experiment_coordinator import (
    ExecutionEvidence,
    ExecutionOutput,
    GenericRunApproval,
    OwnerResultReview,
    SuppliedExecution,
)
from backend.workflow_packages.generic_harness_adapter import (
    GENERIC_HARNESS_EVALUATION_SCHEMA,
    GenericHarnessBinding,
    GenericHarnessEvaluation,
    GenericHarnessExperimentCoordinator,
    GenericHarnessImplementation,
    HybridExperimentResolver,
)
from backend.workflow_packages.generic_harness_contracts import (
    GENERIC_HARNESS_CLASSIFICATION,
    GENERIC_HARNESS_SPEC_SCHEMA,
    GenericHarnessImplementationSpec,
    GenericHarnessPath,
    HarnessExecutionUnit,
    HarnessExpectedOutput,
)
from backend.workflow_packages.serialization import canonical_hash, sha256_bytes

SHA = ["sha256:" + char * 64 for char in "abcdef0123456789"]


def _objective() -> ResearchObjectiveRef:
    return ResearchObjectiveRef(
        "selected-research-idea/v1", "artifact-" + "a" * 32, SHA[0],
        "Compare one bounded baseline with one bounded treatment.",
    )


def _methodology() -> GenericMethodology:
    return GenericMethodology(
        _objective(), ("Does the treatment change the bounded outcome?",),
        ("One deterministic controlled dataset",),
        ("Run baseline and treatment under the same split.",),
        ("One bounded JSON result",), ("Compare the declared primary metric.",),
        ("Use the exact fixed seed.",), ("No external Resource is required.",),
        ("One local execution unit.",), "DISABLED",
        ("The controlled dataset is sufficient for orchestration qualification.",),
        ("No claim beyond this controlled comparison.",), (),
    )


def _spec() -> GenericHarnessImplementationSpec:
    return GenericHarnessImplementationSpec(
        _objective().objective_ref_checksum, _methodology().methodology_checksum,
        "run.py", "PYTHON", ">=3.10,<4", (), ("PYTHON_SCRIPT",),
        (HarnessExpectedOutput("experiment-result", "result.json", "application/json"),),
        (HarnessExecutionUnit(
            "unit-comparison", ("--output", "result.json"),
            ("experiment-result",), "Compare the exact baseline and treatment.",
        ),),
        (("python", "-m", "py_compile", "run.py"),),
        (("wall_time_seconds", "30"),), "DISABLED",
        ("Deterministic controlled baseline and treatment comparison.",),
    )


class _Runner:
    content = b'{"primary_metric_delta":0.125}'

    def execute(self, handoff):
        output = NamedChecksum("experiment-result", sha256_bytes(self.content))
        evidence = ExecutionEvidence(
            handoff.plan.plan_checksum, handoff.approval.approval_checksum,
            handoff.consumption.consumption_checksum, ProcessOutcome.SUCCEEDED,
            (output,), True, "DISABLED",
            "2026-08-20T08:00:00Z", "2026-08-20T08:00:01Z",
        )
        return SuppliedExecution(evidence, (ExecutionOutput(output.name, self.content),))


def test_generic_harness_is_truthful_fallback_and_finalizes_v5(tmp_path: Path):
    implementation_root = tmp_path / "implementation"
    implementation_root.mkdir()
    (implementation_root / "run.py").write_text("print('bounded')\n", encoding="utf-8")
    workflow = ExactIdentity(
        "reproduction-experiment-local-experimental", "0.8.0", SHA[1]
    )
    path = GenericHarnessPath(
        ContractRef(GENERIC_HARNESS_SPEC_SCHEMA, SHA[2]),
        ContractRef(GENERIC_HARNESS_EVALUATION_SCHEMA, SHA[3]),
    )
    implementation = GenericHarnessImplementation(
        implementation_root=implementation_root, workflow=workflow, path=path,
    )
    resolver = HybridExperimentResolver((
        GenericHarnessBinding(implementation.descriptor, implementation),
    ))
    coordinator = GenericHarnessExperimentCoordinator(resolver, workflow=workflow)

    state = coordinator.assess_and_select(_objective(), _methodology()).continuation
    assert state.capability == implementation.capability
    assert implementation.descriptor.classification == GENERIC_HARNESS_CLASSIFICATION
    assert implementation.descriptor.reviewed_capability is False
    assert implementation.descriptor.user_skill_authority is False
    assert "Generic Agent Harness" in state.selection.rationale

    state = coordinator.authorize_design(
        state, DesignApproval.approve(_methodology(), "2026-08-20T07:59:00Z")
    ).continuation
    state = coordinator.validate_specification_and_declare(state, _spec()).continuation
    state = coordinator.evaluate_requirement_readiness(
        state, resources=(), preparation=()
    ).continuation
    state = coordinator.prepare_candidate(
        state, tmp_path / "candidate", prepared_at="2026-08-20T07:59:30Z"
    ).continuation
    assert state.candidate.receipt.origin.value == "LOCAL_PROJECT"
    assert state.candidate.receipt.origin_provenance.checksum == path.path_checksum
    assert state.candidate.receipt.harness is not None
    state = coordinator.validate_and_promote_candidate(
        state, validated_at="2026-08-20T07:59:40Z",
        promoted_root=tmp_path / "validated",
    ).continuation
    runtime = LocalRuntimeCandidate(
        "python-controlled", "PYTHON", "3.11.0", "/usr/bin/python3",
        ("PYTHON_SCRIPT",), SHA[4], (), True,
    )
    state = coordinator.resolve_runtime(
        state, (runtime,), verified_at="2026-08-20T07:59:45Z"
    ).continuation
    state = coordinator.build_execution_plan(
        state,
        capability_output_contract=ContractRef("experiment-record/v5", SHA[5]),
    ).continuation
    state = coordinator.authorize_run(
        state, GenericRunApproval.approve(state.execution_plan, "2026-08-20T07:59:50Z")
    ).continuation
    state = coordinator.handoff_execution(
        state, _Runner(), attempt_id="attempt-controlled",
        consumed_at="2026-08-20T07:59:55Z",
    ).continuation
    implementation.evaluation = GenericHarnessEvaluation(
        _spec().specification_checksum, state.run_consumption.execution_plan_checksum,
        state.supplied_execution.evidence.outputs,
        {"primary_metric_delta": 0.125}, EvaluationValidity.VALID,
        ScientificEvidenceStatus.SUPPORTS_BOUNDED_FINDINGS,
        ("Controlled orchestration evidence only.",),
        "2026-08-20T08:00:02Z", True,
    )
    state = coordinator.evaluate(state).continuation
    review = OwnerResultReview(
        state.evaluation.receipt.evaluation_checksum,
        canonical_hash(state.normalized_result), "ACCEPT_BOUNDED_RESULT",
        "2026-08-20T08:00:03Z",
    )
    state = coordinator.accept_result_review(state, review).continuation
    lifecycle = coordinator.finalize(state).continuation.finalized_record
    source = (EvidenceSourceRef(
        EvidenceSourceKind.RESULT_PAYLOAD, "result-payload",
        state.evaluation.receipt.result_payload_checksum,
    ),)
    record = finalize_experiment_record_v5(
        lifecycle, state.evaluation,
        (ScientificEvidenceBlock(
            "evidence-primary-delta", EvidenceKind.SCALAR,
            "Primary metric delta", 0.125, source,
        ),),
    )
    assert record.schema == "experiment-record/v5"
    assert record.lifecycle_record.capability == implementation.capability


def test_generic_harness_rejects_specification_lineage_drift(tmp_path: Path):
    implementation_root = tmp_path / "implementation"
    implementation_root.mkdir()
    (implementation_root / "run.py").write_text("pass\n", encoding="utf-8")
    path = GenericHarnessPath(
        ContractRef(GENERIC_HARNESS_SPEC_SCHEMA, SHA[2]),
        ContractRef(GENERIC_HARNESS_EVALUATION_SCHEMA, SHA[3]),
    )
    implementation = GenericHarnessImplementation(
        implementation_root=implementation_root,
        workflow=ExactIdentity("reproduction-experiment-local-experimental", "0.8.0", SHA[1]),
        path=path,
    )
    changed = GenericHarnessImplementationSpec(
        SHA[6], _methodology().methodology_checksum, "run.py", "PYTHON", ">=3.10,<4",
        (), ("PYTHON_SCRIPT",),
        (HarnessExpectedOutput("experiment-result", "result.json", "application/json"),),
        (HarnessExecutionUnit("unit-comparison", ("--output", "result.json"),
                              ("experiment-result",), "Controlled comparison."),),
        (("python", "-m", "py_compile", "run.py"),), (), "DISABLED", ("Controlled.",),
    )
    try:
        implementation.validate_specification(_methodology(), changed)
    except ValueError as error:
        assert "lineage" in str(error)
    else:
        raise AssertionError("specification lineage drift was accepted")
