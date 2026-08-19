"""Deterministic forward lifecycle composition for Generic Harness Experiments."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.artifact_references.generic_experiment_contracts import ExperimentRecordV4
from backend.artifact_references.generic_experiment_v5_contracts import (
    ExperimentRecordV5,
    ScientificEvidenceBlock,
    finalize_experiment_record_v5,
)

from .generic_experiment_contracts import (
    ContractRef,
    DesignApproval,
    EvaluationValidity,
    ExactIdentity,
    GenericMethodology,
    NamedChecksum,
    ResearchObjectiveRef,
    ScientificEvidenceStatus,
)
from .generic_experiment_coordinator import (
    RunApprovalConsumption,
    SuppliedExecution,
    GenericExperimentContinuation,
    GenericRunApproval,
    OwnerResultReview,
)
from .generic_harness_adapter import (
    GenericHarnessBinding,
    GenericHarnessEvaluation,
    GenericHarnessExperimentCoordinator,
    GenericHarnessImplementation,
    HybridExperimentResolver,
)
from .generic_harness_contracts import (
    GenericHarnessImplementationSpec,
    GenericHarnessPath,
    GenericHarnessValidationReceipt,
    HarnessDependency,
    HarnessExecutionUnit,
    HarnessExpectedOutput,
)
from .generic_harness_workspace import GenericHarnessWorkspace, RuntimeDiscovery
from .serialization import canonical_hash, to_json_value


class GenericHarnessLifecycleError(ValueError):
    """A durable Generic Harness lifecycle fact is incomplete or drifted."""


@dataclass(frozen=True, slots=True)
class PreparedGenericHarnessLifecycle:
    coordinator: GenericHarnessExperimentCoordinator
    implementation: GenericHarnessImplementation
    continuation: GenericExperimentContinuation
    discovery: RuntimeDiscovery


@dataclass(frozen=True, slots=True)
class FinalizedGenericHarnessLifecycle:
    lifecycle_record: ExperimentRecordV4
    artifact: ExperimentRecordV5
    evaluation: Any
    continuation: GenericExperimentContinuation


def _write_or_verify(workspace: GenericHarnessWorkspace, name: str, value: Any) -> None:
    path = workspace.root / "contracts" / name
    expected = to_json_value(value)
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
            raise GenericHarnessLifecycleError("Generic Harness contract path is unsafe")
        try:
            actual = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise GenericHarnessLifecycleError("Generic Harness contract is invalid") from error
        if actual != expected:
            raise GenericHarnessLifecycleError("Generic Harness durable contract drifted")
        return
    workspace.write_contract(name, value)


def prepare_generic_harness_lifecycle(
    *,
    workspace: GenericHarnessWorkspace,
    workflow: ExactIdentity,
    objective: ResearchObjectiveRef,
    methodology: GenericMethodology,
    design_approval: DesignApproval,
    path: GenericHarnessPath,
    specification: GenericHarnessImplementationSpec,
    validation: GenericHarnessValidationReceipt,
    discovery: RuntimeDiscovery,
    prepared_at: str,
    validated_at: str,
    runtime_verified_at: str,
    reviewed_bindings: tuple[Any, ...] = (),
) -> PreparedGenericHarnessLifecycle:
    """Rebuild the exact pre-execution state from durable local facts.

    Rebuilding is deterministic and never executes the scientific package.  An
    already promoted package is reused only after an independently rebuilt
    candidate has the same exact validated package and tree identity.
    """

    workspace.initialize()
    workspace.verify_owner()
    implementation = GenericHarnessImplementation(
        implementation_root=workspace.root / "implementation",
        workflow=workflow,
        path=path,
        validation=validation,
    )
    resolver = HybridExperimentResolver((
        *reviewed_bindings,
        GenericHarnessBinding(implementation.descriptor, implementation),
    ))
    coordinator = GenericHarnessExperimentCoordinator(resolver, workflow=workflow)
    state = coordinator.assess_and_select(objective, methodology).continuation
    if state.capability is None:
        raise GenericHarnessLifecycleError("Experiment implementation path is unresolved")
    state = coordinator.authorize_design(state, design_approval).continuation
    if state.design_approval is None:
        raise GenericHarnessLifecycleError("Generic Harness methodology approval is invalid")
    state = coordinator.validate_specification_and_declare(state, specification).continuation
    state = coordinator.evaluate_requirement_readiness(
        state, resources=(), preparation=(),
    ).continuation

    _write_or_verify(workspace, "research-objective.json", objective)
    _write_or_verify(workspace, "methodology.json", methodology)
    _write_or_verify(workspace, "methodology-approval.json", design_approval)
    _write_or_verify(workspace, "implementation-specification.json", specification)
    _write_or_verify(workspace, "implementation-validation.json", validation)

    preparation_root = workspace.root / "sync/candidates"
    preparation_root.mkdir(parents=True, exist_ok=True)
    state = coordinator.prepare_candidate(
        state, preparation_root, prepared_at=prepared_at,
    ).continuation
    promoted = workspace.root / "validated-package/package"
    if promoted.exists() or promoted.is_symlink():
        if promoted.is_symlink() or not promoted.is_dir():
            raise GenericHarnessLifecycleError("Validated Generic Harness package is unsafe")
        rebuilt = coordinator.validate_and_promote_candidate(
            state, validated_at=validated_at,
        ).continuation
        if (
            rebuilt.validated_package is None
            or GenericHarnessExperimentCoordinator._scan_package(promoted)
            != rebuilt.validated_package.package_tree_checksum
        ):
            raise GenericHarnessLifecycleError("Validated Generic Harness package drifted")
        rebuilt_root = rebuilt.validated_package_root
        if rebuilt_root is None or rebuilt_root == promoted or workspace.root not in rebuilt_root.parents:
            raise GenericHarnessLifecycleError("Rebuilt Generic Harness package ownership is invalid")
        shutil.rmtree(rebuilt_root)
        state = replace(
            rebuilt, candidate_root=promoted, validated_package_root=promoted,
        )
    else:
        state = coordinator.validate_and_promote_candidate(
            state, validated_at=validated_at, promoted_root=promoted,
        ).continuation
    _write_or_verify(workspace, "validated-package.json", state.validated_package)
    _write_or_verify(workspace, "runtime-discovery.json", discovery)
    state = coordinator.resolve_runtime(
        state, discovery.candidates, verified_at=runtime_verified_at,
    ).continuation
    if state.runtime_compatibility is None:
        raise GenericHarnessLifecycleError("No compatible existing runtime is available")
    state = coordinator.build_execution_plan(
        state,
        capability_output_contract=ContractRef(
            "experiment-record/v5",
            canonical_hash({"schema": "experiment-record/v5"}),
        ),
    ).continuation
    _write_or_verify(workspace, "runtime-compatibility.json", state.runtime_compatibility)
    _write_or_verify(workspace, "execution-plan.json", state.execution_plan)
    return PreparedGenericHarnessLifecycle(coordinator, implementation, state, discovery)


def finalize_generic_harness_lifecycle(
    prepared: PreparedGenericHarnessLifecycle,
    *,
    approval: GenericRunApproval,
    runner: Any,
    attempt_id: str,
    consumed_at: str,
    evaluation: GenericHarnessEvaluation,
    owner_review: OwnerResultReview,
    evidence_blocks: Sequence[ScientificEvidenceBlock],
) -> FinalizedGenericHarnessLifecycle:
    """Execute one approved plan and finalize exact v4/v5 evidence once."""

    coordinator = prepared.coordinator
    state = coordinator.authorize_run(prepared.continuation, approval).continuation
    if state.run_approval is None:
        raise GenericHarnessLifecycleError("Generic Harness run approval is invalid")
    state = coordinator.handoff_execution(
        state, runner, attempt_id=attempt_id, consumed_at=consumed_at,
    ).continuation
    prepared.implementation.evaluation = evaluation
    state = coordinator.evaluate(state).continuation
    state = coordinator.accept_result_review(state, owner_review).continuation
    if state.owner_result_review is None:
        raise GenericHarnessLifecycleError("Generic Harness result review is invalid")
    state = coordinator.finalize(state).continuation
    if state.finalized_record is None or state.evaluation is None:
        raise GenericHarnessLifecycleError("Generic Harness lifecycle did not finalize")
    artifact = finalize_experiment_record_v5(
        state.finalized_record, state.evaluation, evidence_blocks,
    )
    return FinalizedGenericHarnessLifecycle(
        state.finalized_record, artifact, state.evaluation, state,
    )


def finalize_supplied_generic_harness_lifecycle(
    prepared: PreparedGenericHarnessLifecycle,
    *,
    approval: GenericRunApproval,
    consumption: RunApprovalConsumption,
    supplied: SuppliedExecution,
    evaluation: GenericHarnessEvaluation,
    owner_review: OwnerResultReview,
    evidence_blocks: Sequence[ScientificEvidenceBlock],
) -> FinalizedGenericHarnessLifecycle:
    """Finalize already durable exact execution without rerunning science."""

    coordinator = prepared.coordinator
    state = coordinator.authorize_run(prepared.continuation, approval).continuation
    if state.run_approval is None:
        raise GenericHarnessLifecycleError("Generic Harness run approval is invalid")
    state = coordinator.accept_execution_evidence(
        state, supplied, consumption,
    ).continuation
    prepared.implementation.evaluation = evaluation
    state = coordinator.evaluate(state).continuation
    state = coordinator.accept_result_review(state, owner_review).continuation
    if state.owner_result_review is None:
        raise GenericHarnessLifecycleError("Generic Harness result review is invalid")
    state = coordinator.finalize(state).continuation
    if state.finalized_record is None or state.evaluation is None:
        raise GenericHarnessLifecycleError("Generic Harness lifecycle did not finalize")
    artifact = finalize_experiment_record_v5(
        state.finalized_record, state.evaluation, evidence_blocks,
    )
    return FinalizedGenericHarnessLifecycle(
        state.finalized_record, artifact, state.evaluation, state,
    )


def objective_from_mapping(value: Mapping[str, Any]) -> ResearchObjectiveRef:
    return ResearchObjectiveRef(
        value["source_artifact_type"], value["source_artifact_id"],
        value["source_artifact_checksum"], value["objective_summary"],
    )


def methodology_from_mapping(value: Mapping[str, Any]) -> GenericMethodology:
    domain = value.get("domain_methodology_ref")
    return GenericMethodology(
        objective_from_mapping(value["research_objective"]),
        tuple(value["questions_or_hypotheses"]), tuple(value["inputs_or_materials"]),
        tuple(value["protocol"]), tuple(value["observations_or_outputs"]),
        tuple(value["evaluation_criteria"]), tuple(value["reproducibility_controls"]),
        tuple(value["resource_constraints"]), tuple(value["compute_constraints"]),
        value["network_policy"], tuple(value["assumptions"]),
        tuple(value["claim_boundaries"]), tuple(value["unresolved_material_decisions"]),
        None if domain is None else ContractRef(domain["schema_identity"], domain["checksum"]),
    )


def design_approval_from_mapping(value: Mapping[str, Any]) -> DesignApproval:
    return DesignApproval(
        value["research_objective_checksum"], value["methodology_checksum"],
        value["frozen_scientific_requirements_checksum"],
        value["evaluation_criteria_checksum"], value["claim_boundaries_checksum"],
        value["approved_at"],
    )


def specification_from_mapping(value: Mapping[str, Any]) -> GenericHarnessImplementationSpec:
    return GenericHarnessImplementationSpec(
        value["objective_checksum"], value["methodology_checksum"],
        value["entrypoint_relative_path"], value["runtime_family"],
        value["runtime_version_constraint"],
        tuple(HarnessDependency(item["name"], item["version_constraint"]) for item in value["dependencies"]),
        tuple(value["required_runtime_capabilities"]),
        tuple(HarnessExpectedOutput(
            item["name"], item["relative_path"], item["media_type"],
        ) for item in value["expected_outputs"]),
        tuple(HarnessExecutionUnit(
            item["unit_id"], tuple(item["arguments"]),
            tuple(item["expected_output_names"]), item["scientific_role"],
        ) for item in value["execution_units"]),
        tuple(tuple(item) for item in value["validation_commands"]),
        tuple(tuple(item) for item in value["compute_limits"]),
        value["network_policy"], tuple(value["implementation_summary"]),
    )


def validation_from_mapping(value: Mapping[str, Any]) -> GenericHarnessValidationReceipt:
    return GenericHarnessValidationReceipt(
        value["specification_checksum"], value["methodology_checksum"],
        value["package_tree_checksum"], value["entrypoint_checksum"],
        tuple(value["validation_command_checksums"]), value["package_safe"],
        value["methodology_conformant"], value["validated_at"],
    )


def evaluation_from_mapping(value: Mapping[str, Any]) -> GenericHarnessEvaluation:
    return GenericHarnessEvaluation(
        value["specification_checksum"], value["execution_plan_checksum"],
        tuple(NamedChecksum(item["name"], item["checksum"]) for item in value["execution_outputs"]),
        value["result_payload"], EvaluationValidity(value["validity"]),
        ScientificEvidenceStatus(value["scientific_evidence_status"]),
        tuple(value["limitations"]), value["evaluated_at"],
        value["contract_validation_passed"],
    )
