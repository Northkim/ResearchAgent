from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
from typing import Any

import pytest

from backend.resource_references.experiment_requirement_contracts import (
    ExperimentResourceReadinessEvidence, ExperimentResourceRequirementRef,
    ResourceReadiness,
)
from backend.workflow_packages.experiment_capability_runtime import (
    BoundedCapabilityResolver, CapabilityBinding, CapabilityEvaluationResult,
    CapabilityImplementationDescriptor, CapabilityRequirementDeclaration,
    PreparedCapabilityCandidate, ValidatedOpaqueSpecification,
)
from backend.workflow_packages.generic_experiment_contracts import (
    CapabilityAssessment, CapabilityEvaluationReceipt, CapabilityOperation,
    ContractRef, DesignApproval, EvaluationValidity, ExactIdentity,
    ExperimentCapability, GenericMethodology, ImplementationSpecificationRef,
    LocalRuntimeCandidate, NamedChecksum, PreparationRequirement, ProcessOutcome,
    ResearchObjectiveRef, RuntimeRequirement, SupportStatus,
)
from backend.workflow_packages.generic_experiment_coordinator import (
    CheckpointCode, ContinuationStage, ExecutionEvidence, ExecutionOutput,
    GenericExperimentCoordinator, GenericExperimentCoordinatorError,
    GenericRunApproval, OwnerResultReview, PreparationReadinessEvidence,
    RunApprovalConsumption, SuppliedExecution,
)
from backend.workflow_packages.generic_experiment_package import (
    DependencyDeclaration, ExperimentPackageManifest, LaunchTarget, PackageOrigin,
    PreparedExperimentPackageReceipt,
)
from backend.workflow_packages.serialization import canonical_hash, sha256_bytes

SHA = ["sha256:" + char * 64 for char in "abcdef0123456789"]
WORKFLOW = ExactIdentity("reproduction-experiment-local-experimental", "0.6.0", SHA[0])


def objective() -> ResearchObjectiveRef:
    return ResearchObjectiveRef(
        "selected-research-idea/v1", "artifact-" + "a" * 32, SHA[1],
        "Check whether three archival statements retain their categorical meaning.",
    )


def methodology(*, unresolved=(), protocol="Apply the reviewed concordance rubric.") -> GenericMethodology:
    return GenericMethodology(
        objective(), ("Which statements preserve their meaning?",),
        ("Three supplied statements",), (protocol,),
        ("A textual categorical observation",),
        ("Classify each statement as concordant, changed, or absent.",),
        ("Use stable statement order.",), ("No research Resource is required.",),
        ("One bounded local text process.",), "DISABLED",
        ("The statements are authoritative for this test.",),
        ("No claim beyond the supplied statements.",), unresolved,
    )


class SyntheticCapability:
    def __init__(
        self, char: str = "2", *, status=SupportStatus.SUPPORTED,
        fallback: str | None = None, resources: int = 0, preparation=False,
        dependencies: int = 0, prepare=True, present=True,
    ) -> None:
        operations = [CapabilityOperation.ASSESS_SUPPORT, CapabilityOperation.DECLARE_REQUIREMENTS,
                      CapabilityOperation.EVALUATE]
        if prepare:
            operations.append(CapabilityOperation.PREPARE)
        if present:
            operations.append(CapabilityOperation.PRESENT)
        self.capability = ExperimentCapability(
            "0.1.0", ExactIdentity(f"synthetic-text-skill-{char}", "0.1.0", "sha256:" + char * 64),
            ExactIdentity(f"synthetic-text-capsule-{char}", "0.1.0", "sha256:" + char * 64),
            f"capabilities/text-{char}", "sha256:" + char * 64, tuple(operations),
            "reagent.synthetic.text-spec/v0.1", "reagent.synthetic.text-evaluation/v0.1",
            "reagent.synthetic.text-presentation/v0.1" if present else None,
        )
        self.descriptor = CapabilityImplementationDescriptor(
            self.capability, self.capability.schema, self.capability.skill.checksum,
            self.capability.capsule.checksum, self.capability.implementation_entrypoint or "",
            self.capability.implementation_entrypoint_checksum or "", fallback,
            "TEST_ONLY_EXPERIMENT_CAPABILITY",
        )
        self.status, self.resource_count, self.has_preparation = status, resources, preparation
        self.dependency_count = dependencies

    def assess_support(self, obj, method):
        return CapabilityAssessment(
            self.capability.capability_checksum, obj.objective_ref_checksum,
            method.methodology_checksum, self.status, ("Synthetic bounded support result.",), int(self.capability.skill.identity[-1], 16),
        )

    def validate_specification(self, method, specification):
        checksum = canonical_hash(specification)
        ref = ImplementationSpecificationRef(
            self.capability.capability_checksum, self.capability.implementation_spec_schema or "",
            method.methodology_checksum, checksum,
            ContractRef("reagent.synthetic.spec-validation/v0.1", canonical_hash({"spec": checksum, "method": method.methodology_checksum})),
            (("Observation form", "Categorical textual concordance."),),
        )
        return ValidatedOpaqueSpecification(ref, specification)

    def declare_requirements(self, method, specification):
        resources = tuple(
            ExperimentResourceRequirementRef(
                self.capability.capability_checksum, "reproduction-experiment-local-experimental",
                "0.6.0", f"source_{i}", "SOURCE_REPOSITORY", 1, 1, True,
                ("GITHUB",), "Exact synthetic research source.",
            ) for i in range(self.resource_count)
        )
        preparation = () if not self.has_preparation else (
            PreparationRequirement(
                "text_renderer", self.capability.capability_checksum, "TEXT_RENDERER",
                ">=1,<2", ("UTF8",), True,
            ),
        )
        dependencies = tuple(
            ContractRef("reagent.synthetic.dependency/v0.1", sha256_bytes(f"dependency-{i}".encode()))
            for i in range(self.dependency_count)
        )
        runtime = RuntimeRequirement(
            "REVIEWED_TEXT_PROCESS", ">=1,<2", ("UTF8_TEXT",), dependencies,
            ContractRef("reagent.launch-contract/text-plan/v0.1", SHA[3]), "DISABLED",
            (("wall_time_seconds", "30"),),
        )
        return CapabilityRequirementDeclaration(
            self.capability.capability_checksum, specification.reference.reference_checksum,
            resources, preparation, runtime,
        )

    def prepare(self, root: Path, context):
        launch = b"READ STATEMENTS\nEMIT CATEGORY\n"
        (root / "plan").mkdir()
        (root / "plan/review.plan").write_bytes(launch)
        dependencies = []
        for index, identity in enumerate(context.requirements.runtime_requirement.dependency_declarations):
            path = root / f"deps/dependency-{index}.decl"
            path.parent.mkdir(exist_ok=True)
            content = f"dependency-{index}".encode()
            path.write_bytes(content)
            assert sha256_bytes(content) == identity.checksum
            dependencies.append(DependencyDeclaration("SYNTHETIC_DECLARATION", f"deps/dependency-{index}.decl", identity.checksum))
        entries = tuple(
            {"path": p.relative_to(root).as_posix(), "sha256": sha256_bytes(p.read_bytes()), "size_bytes": p.stat().st_size}
            for p in sorted(root.rglob("*")) if p.is_file()
        )
        runtime = context.requirements.runtime_requirement
        manifest = ExperimentPackageManifest(
            self.capability.capability_checksum, context.specification.reference,
            LaunchTarget("plan/review.plan", sha256_bytes(launch), runtime.launch_contract),
            tuple(dependencies), (),
            (NamedChecksum("objective", context.objective.source_artifact_checksum),),
            context.resource_identity_checksums, runtime.requirement_checksum,
            (NamedChecksum("categorical-observations", SHA[4]),),
        )
        receipt = PreparedExperimentPackageReceipt(
            PackageOrigin.REAGENT_PREPARED, context.objective, context.methodology.methodology_checksum,
            ExactIdentity("synthetic-text-capability", "0.1.0", self.capability.capability_checksum),
            context.specification.reference, canonical_hash(entries), manifest.manifest_checksum,
            manifest.launch_target.checksum, tuple(item.checksum for item in dependencies), runtime,
            context.resource_identity_checksums, WORKFLOW, self.capability.capsule, None, None,
            context.prepared_at,
        )
        return PreparedCapabilityCandidate(manifest, receipt)

    def evaluate(self, context: Any):
        raw = context["outputs"][0].content.decode()
        valid = raw in {"CONCORDANT", "INSUFFICIENT"}
        limited = raw == "CONCORDANT"
        payload = {"categorical_finding": raw if valid else "INVALID"}
        limitations = ("Only the three supplied statements were reviewed.",) if valid else ("Categorical evidence is invalid.",)
        receipt = CapabilityEvaluationReceipt(
            self.capability.capability_checksum, context["objective"].objective_ref_checksum,
            context["methodology"].methodology_checksum,
            context["specification"].reference.specification_checksum,
            context["plan"].plan_checksum, context["execution_evidence"].outputs,
            context["plan"].capability_output_contract.checksum,
            self.capability.evaluation_schema or "", canonical_hash(payload),
            EvaluationValidity.VALID if limited else (EvaluationValidity.INDETERMINATE if valid else EvaluationValidity.INVALID),
            limitations, context["execution_evidence"].completed_at,
        )
        return CapabilityEvaluationResult(receipt, "LIMITED" if limited else "INCONCLUSIVE", payload)

    def present(self, context):
        return ContractRef(self.capability.presentation_schema or "", canonical_hash({"finding": context["evaluation"].result_payload}))


def coordinator(*capabilities: SyntheticCapability):
    return GenericExperimentCoordinator(
        BoundedCapabilityResolver(tuple(CapabilityBinding(item.descriptor, item) for item in capabilities)),
        workflow=WORKFLOW,
    )


def selected(current: GenericExperimentCoordinator, method=None):
    return current.assess_and_select(objective(), method or methodology()).continuation


class FakeRunner:
    def __init__(self, content=b"CONCORDANT", outcome=ProcessOutcome.SUCCEEDED):
        self.content, self.outcome, self.calls = content, outcome, 0

    def execute(self, handoff):
        self.calls += 1
        output = NamedChecksum("categorical-observations", sha256_bytes(self.content))
        evidence = ExecutionEvidence(
            handoff.plan.plan_checksum, handoff.approval.approval_checksum,
            handoff.consumption.consumption_checksum, self.outcome, (output,), True,
            "DISABLED", "2026-08-17T08:05:00Z", "2026-08-17T08:06:00Z",
        )
        return SuppliedExecution(evidence, (ExecutionOutput(output.name, self.content),))


def ready_for_runtime(tmp_path, capability=None):
    capability = capability or SyntheticCapability()
    core = coordinator(capability)
    state = selected(core)
    state = core.authorize_design(state, DesignApproval.approve(methodology(), "2026-08-17T08:00:00Z")).continuation
    state = core.validate_specification_and_declare(state, {"rubric": ("CONCORDANT", "CHANGED", "ABSENT")}).continuation
    prep = ()
    if capability.has_preparation:
        req = state.requirements.preparation_requirements[0]
        prep = (PreparationReadinessEvidence(req.requirement_checksum, "TEXT_RENDERER", "1.2", ("UTF8",), SHA[5], True),)
    state = core.evaluate_requirement_readiness(state, resources=(), preparation=prep).continuation
    state = core.prepare_candidate(state, tmp_path / "preparation", prepared_at="2026-08-17T08:01:00Z").continuation
    state = core.validate_and_promote_candidate(state, validated_at="2026-08-17T08:02:00Z", promoted_root=tmp_path / "validated").continuation
    return core, state


def test_non_ml_full_lifecycle_fake_runner_and_v4(tmp_path):
    core, state = ready_for_runtime(tmp_path)
    runtime = LocalRuntimeCandidate("text-runtime", "REVIEWED_TEXT_PROCESS", "1.2", "/opt/reagent/text-process", ("UTF8_TEXT",), SHA[6], (), True)
    state = core.resolve_runtime(state, (runtime,), verified_at="2026-08-17T08:03:00Z").continuation
    state = core.build_execution_plan(state, capability_output_contract=ContractRef("reagent.synthetic.output/v0.1", SHA[7])).continuation
    assert core.authorize_run(state, None).checkpoint is CheckpointCode.RUN_APPROVAL_REQUIRED
    approval = GenericRunApproval.approve(state.execution_plan, "2026-08-17T08:04:00Z")
    state = core.authorize_run(state, approval).continuation
    runner = FakeRunner()
    state = core.handoff_execution(state, runner, attempt_id="attempt-1", consumed_at="2026-08-17T08:04:30Z").continuation
    with pytest.raises(GenericExperimentCoordinatorError, match="CONSUMED"):
        core.handoff_execution(state, runner, attempt_id="attempt-2", consumed_at="2026-08-17T08:04:40Z")
    state = core.evaluate(state).continuation
    assert core.require_result_review(state).checkpoint is CheckpointCode.RESULT_REVIEW_REQUIRED
    review = OwnerResultReview(state.evaluation.receipt.evaluation_checksum, canonical_hash(state.normalized_result), "ACCEPT_BOUNDED_RESULT", "2026-08-17T08:07:00Z")
    state = core.accept_result_review(state, review).continuation
    result = core.finalize(state)
    assert result.continuation.stage is ContinuationStage.FINALIZED
    assert result.continuation.finalized_record.schema == "experiment-record/v4"
    assert "rubric" not in result.continuation.durable_receipt().canonical_json()
    serialized = result.continuation.finalized_record.canonical_json().lower()
    assert not any(item in serialized for item in ("sklearn", "knn", '"metrics"', "cross-validation"))
    assert runner.calls == 1


def test_support_selection_and_owner_checkpoints():
    unsupported = SyntheticCapability(status=SupportStatus.UNSUPPORTED)
    assert selected(coordinator(unsupported)).checkpoint is CheckpointCode.AUTOMATIC_PREPARATION_UNSUPPORTED
    decision = SyntheticCapability(status=SupportStatus.NEEDS_OWNER_DECISION)
    assert selected(coordinator(decision)).checkpoint is CheckpointCode.METHODOLOGY_DECISION_REQUIRED
    assert coordinator(SyntheticCapability()).assess_and_select(objective(), methodology(unresolved=("Choose rubric.",))).checkpoint is CheckpointCode.METHODOLOGY_DECISION_REQUIRED
    one, two = SyntheticCapability("2"), SyntheticCapability("3")
    material = coordinator(one, two).assess_and_select(objective(), methodology())
    assert material.checkpoint is CheckpointCode.CAPABILITY_SELECTION_REQUIRED
    confirmed = coordinator(one, two).assess_and_select(
        objective(), methodology(), owner_selected_capability_checksum=one.capability.capability_checksum,
        owner_confirmation_checksum=SHA[8],
    )
    assert confirmed.checkpoint is CheckpointCode.DESIGN_APPROVAL_REQUIRED
    fallback = coordinator(SyntheticCapability("2", fallback="same"), SyntheticCapability("3", fallback="same")).assess_and_select(objective(), methodology())
    assert fallback.checkpoint is CheckpointCode.DESIGN_APPROVAL_REQUIRED


def test_design_resource_preparation_and_candidate_failure_boundaries(tmp_path):
    capability = SyntheticCapability(resources=1, preparation=True)
    core = coordinator(capability)
    state = selected(core)
    assert core.authorize_design(state, None).checkpoint is CheckpointCode.DESIGN_APPROVAL_REQUIRED
    drift = DesignApproval.approve(methodology(protocol="Different protocol."), "2026-08-17T08:00:00Z")
    assert core.authorize_design(state, drift).checkpoint is CheckpointCode.DESIGN_APPROVAL_REQUIRED
    state = core.authorize_design(state, DesignApproval.approve(methodology(), "2026-08-17T08:00:00Z")).continuation
    with pytest.raises(GenericExperimentCoordinatorError, match="drift"):
        core.validate_specification_and_declare(
            replace(state, selection=replace(state.selection, rationale="Drifted selection evidence.")),
            {"opaque": "categorical"},
        )
    state = core.validate_specification_and_declare(state, {"opaque": "categorical"}).continuation
    assert core.evaluate_requirement_readiness(state, resources=(), preparation=()).checkpoint is CheckpointCode.RESOURCE_READINESS_REQUIRED
    req = state.requirements.resource_requirements[0]
    metadata_only = ExperimentResourceReadinessEvidence(req.requirement_checksum, ResourceReadiness.BOUND_METADATA_ONLY, "binding-1", "resource-1", SHA[1], None)
    assert core.evaluate_requirement_readiness(state, resources=(metadata_only,), preparation=()).checkpoint is CheckpointCode.RESOURCE_READINESS_REQUIRED
    drifted = ExperimentResourceReadinessEvidence(req.requirement_checksum, ResourceReadiness.DRIFTED, "binding-1", "resource-1", SHA[1], None)
    assert core.evaluate_requirement_readiness(state, resources=(drifted,), preparation=()).checkpoint is CheckpointCode.RESOURCE_READINESS_REQUIRED
    mismatch = ExperimentResourceReadinessEvidence(req.requirement_checksum, ResourceReadiness.RESOLVED_VERIFIED, "binding-1", "resource-1", SHA[1], SHA[2])
    assert core.evaluate_requirement_readiness(state, resources=(mismatch,), preparation=()).checkpoint is CheckpointCode.RESOURCE_READINESS_REQUIRED
    ready_resource = ExperimentResourceReadinessEvidence(req.requirement_checksum, ResourceReadiness.RESOLVED_VERIFIED, "binding-1", "resource-1", SHA[1], SHA[1])
    assert core.evaluate_requirement_readiness(state, resources=(ready_resource,), preparation=()).checkpoint is CheckpointCode.PREPARATION_REQUIREMENT_UNMET
    prep_req = state.requirements.preparation_requirements[0]
    ready_prep = PreparationReadinessEvidence(prep_req.requirement_checksum, "TEXT_RENDERER", "1.2", ("UTF8",), SHA[5], True)
    state = core.evaluate_requirement_readiness(state, resources=(ready_resource,), preparation=(ready_prep,)).continuation
    state = core.prepare_candidate(state, tmp_path / "prep", prepared_at="2026-08-17T08:01:00Z").continuation
    (state.candidate_root / "plan/review.plan").write_bytes(b"drift")
    destination = tmp_path / "validated"
    with pytest.raises(GenericExperimentCoordinatorError, match="launch target"):
        core.validate_and_promote_candidate(state, validated_at="2026-08-17T08:02:00Z", promoted_root=destination)
    assert not destination.exists()


def test_generic_variants_runtime_drift_plan_approval_and_evaluation(tmp_path):
    capability = SyntheticCapability(dependencies=2, present=False)
    core, state = ready_for_runtime(tmp_path, capability)
    assert len(state.validated_package.manifest.dependency_declarations) == 2
    incompatible = LocalRuntimeCandidate("wrong", "PYTHON", "3.11", "/usr/bin/python3", (), SHA[2], (), True)
    assert core.resolve_runtime(state, (incompatible,), verified_at="2026-08-17T08:03:00Z").checkpoint is CheckpointCode.RUNTIME_INCOMPATIBLE
    dependencies = tuple(item.checksum for item in state.requirements.runtime_requirement.dependency_declarations)
    runtime = LocalRuntimeCandidate("text", "REVIEWED_TEXT_PROCESS", "1.1", "/opt/text", ("UTF8_TEXT",), SHA[6], dependencies, True)
    state = core.resolve_runtime(state, (runtime,), verified_at="2026-08-17T08:03:00Z").continuation
    drifted_runtime = LocalRuntimeCandidate("text", "REVIEWED_TEXT_PROCESS", "1.1", "/opt/text", ("UTF8_TEXT",), SHA[7], dependencies, True)
    with pytest.raises(GenericExperimentCoordinatorError, match="environment drift"):
        core.build_execution_plan(replace(state, local_runtime=drifted_runtime), capability_output_contract=ContractRef("reagent.synthetic.output/v0.1", SHA[7]))
    state = core.build_execution_plan(state, capability_output_contract=ContractRef("reagent.synthetic.output/v0.1", SHA[7])).continuation
    wrong_plan = replace(state.execution_plan, network_policy="BOUNDED_DECLARED")
    wrong_approval = GenericRunApproval.approve(wrong_plan, "2026-08-17T08:04:00Z")
    assert core.authorize_run(state, wrong_approval).checkpoint is CheckpointCode.RUN_APPROVAL_REQUIRED
    state = core.authorize_run(state, GenericRunApproval.approve(state.execution_plan, "2026-08-17T08:04:00Z")).continuation
    approved = state
    state = core.handoff_execution(approved, FakeRunner(b"INSUFFICIENT"), attempt_id="attempt-1", consumed_at="2026-08-17T08:04:30Z").continuation
    state = core.evaluate(state).continuation
    assert state.normalized_result.evaluation_validity is EvaluationValidity.INDETERMINATE
    assert state.normalized_result.scientific_evidence_status.value == "INCONCLUSIVE"
    review = OwnerResultReview(state.evaluation.receipt.evaluation_checksum, canonical_hash(state.normalized_result), "ACKNOWLEDGE_LIMITED_OR_INVALID", "2026-08-17T08:07:00Z")
    assert core.finalize(core.accept_result_review(state, review).continuation).continuation.presentation.schema_identity == "reagent.artifact-presentation.experiment-record/v0.2"
    invalid = core.handoff_execution(approved, FakeRunner(b"INVALID"), attempt_id="attempt-invalid", consumed_at="2026-08-17T08:04:31Z").continuation
    assert core.evaluate(invalid).continuation.normalized_result.evaluation_validity is EvaluationValidity.INVALID
    multi = SyntheticCapability("5", resources=2)
    multi_core = coordinator(multi)
    multi_state = selected(multi_core)
    multi_state = multi_core.authorize_design(multi_state, DesignApproval.approve(methodology(), "2026-08-17T08:00:00Z")).continuation
    multi_state = multi_core.validate_specification_and_declare(multi_state, {"opaque": True}).continuation
    assert len(multi_state.requirements.resource_requirements) == 2
    no_prepare = SyntheticCapability("4", prepare=False)
    no_prepare_core = coordinator(no_prepare)
    no_prepare_state = selected(no_prepare_core)
    no_prepare_state = no_prepare_core.authorize_design(no_prepare_state, DesignApproval.approve(methodology(), "2026-08-17T08:00:00Z")).continuation
    no_prepare_state = no_prepare_core.validate_specification_and_declare(no_prepare_state, {"opaque": True}).continuation
    no_prepare_state = no_prepare_core.evaluate_requirement_readiness(no_prepare_state, resources=(), preparation=()).continuation
    assert no_prepare_core.prepare_candidate(no_prepare_state, tmp_path / "path-b", prepared_at="2026-08-17T08:01:00Z").checkpoint is CheckpointCode.CAPABILITY_PREPARATION_UNAVAILABLE


@pytest.mark.parametrize("unsafe", ("symlink", "hardlink", "special"))
def test_independent_package_scan_rejects_unsafe_tree_entries(tmp_path, unsafe):
    root = tmp_path / unsafe
    root.mkdir()
    (root / "entry").write_bytes(b"bounded")
    if unsafe == "symlink":
        (root / "link").symlink_to("entry")
    elif unsafe == "hardlink":
        os.link(root / "entry", root / "linked")
    elif unsafe == "special":
        os.mkfifo(root / "pipe")
    with pytest.raises(GenericExperimentCoordinatorError):
        GenericExperimentCoordinator._scan_package(root)


def test_independent_package_scan_rejects_case_collisions_portably():
    folded: set[str] = set()
    GenericExperimentCoordinator._record_package_path("Plan/ENTRY", folded)
    with pytest.raises(GenericExperimentCoordinatorError, match="case collision"):
        GenericExperimentCoordinator._record_package_path("plan/entry", folded)
