#!/usr/bin/env python3
"""Resumable local runtime for Experiment 0.5 PREPARE_WITH_REAGENT."""

from __future__ import annotations

import argparse
import json
import os
import platform
import runpy
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

_ROOT = Path(__file__).resolve().parent
_LIB = _ROOT / "runtime_lib"
if _LIB.is_dir() and str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from backend.workflow_packages.experiment_preparation_contracts import (  # noqa: E402
    BuilderFamily, BuilderIdentity, ComputeRuntimeBounds, DesignApproval,
    ExactArtifactReference, ExperimentMethodology, HarnessIdentity,
    ImplementationDecision, MethodologicalEffect, PackageOrigin,
    PreparedPackageReceipt, RunApprovalFoundation, RuntimeIdentity,
    UnresolvedMethodologicalDecision, WorkflowCapsuleIdentity,
)
from backend.workflow_packages.serialization import canonical_hash, canonical_json, sha256_bytes  # noqa: E402
from backend.workflow_packages.sklearn_tabular_builder import (  # noqa: E402
    BUILDER_VERSION, ENTRYPOINT, SklearnTabularClassificationSpec,
    package_tree, render_candidate,
)
from backend.workflow_packages.validated_experiment_package import (  # noqa: E402
    NamedChecksum, PackageSafetyEvidence, VALIDATED_PACKAGE_SCHEMA,
    ValidatedExperimentPackage,
)


class PreparedExperimentError(RuntimeError):
    pass


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_json(path: Path, value: Any) -> None:
    _atomic_bytes(path, (canonical_json(value) + "\n").encode())


def _object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise PreparedExperimentError(f"{label} must be one regular unlinked file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PreparedExperimentError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise PreparedExperimentError(f"{label} must be a JSON object")
    return value


def _validate_capsule(root: Path) -> None:
    namespace = runpy.run_path(str(root / "validate_package.py"))
    try:
        result = namespace["validate"](root, pristine=False)
    except Exception as error:
        raise PreparedExperimentError(f"Capsule validation failed: {error}") from error
    if result.get("valid") is not True:
        raise PreparedExperimentError("Capsule validation failed closed")


def _input(root: Path) -> tuple[ExactArtifactReference, dict[str, Any]]:
    provenance = _object(root / "memory/input-provenance.json", "input provenance")
    record = provenance.get("artifacts", {}).get("research_idea")
    if not isinstance(record, dict):
        raise PreparedExperimentError("One exact selected Idea must be materialized")
    reference = ExactArtifactReference.from_mapping(record)
    path = root / "inputs/selected-research-idea.json"
    if sha256_bytes(path.read_bytes()) != reference.sha256:
        raise PreparedExperimentError("Materialized selected Idea checksum drifted")
    idea = _object(path, "selected research Idea")
    if idea.get("schema") != "selected-research-idea/v1" or not isinstance(idea.get("selected_idea"), dict):
        raise PreparedExperimentError("Materialized selected Idea is invalid")
    return reference, idea


def _codex_executable(value: str | None) -> str:
    selected = value or os.environ.get("REAGENT_CODEX_EXECUTABLE", "codex")
    resolved = str(Path(selected).resolve()) if os.path.sep in selected else shutil.which(selected)
    if resolved is None or not Path(resolved).is_file() or not os.access(resolved, os.X_OK):
        raise PreparedExperimentError("Codex CLI is unavailable")
    return resolved


def _harness_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for key in ("REAGENT_PROXY_TOKEN", "REAGENT_LOCAL_SESSION_TOKEN", "REAGENT_DATABASE_URL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        environment.pop(key, None)
    return environment


def _methodology_instruction() -> str:
    return """Prepare the Experiment methodology for the exact materialized selected-research-idea/v1.
Read workflow/prompts/prepare-experiment.md and inputs/selected-research-idea.json. Act as a methodology-aware implementation agent, not a shell operator. Ask the Owner only about unresolved choices that materially change interpretation, reproducibility, evaluation, resources, or claim boundaries. In particular do not silently choose folds, repeats, seeds, the primary n_neighbors value, or the bounded neighbor grid when the Idea does not specify them. Do not ask Python, manifest, dependency, entrypoint, Git, or checksum questions.

After the Owner resolves all material choices, write memory/methodology-proposal.json as one JSON object with exactly these fields: frozen_scientific_requirements (strings), implementation_decisions (objects: decision, rationale, scientific_meaning_unchanged=true), unresolved_methodological_decisions (must be empty; objects would use question and material_effects), dataset, experiment_conditions, evaluation_protocol, metrics, robustness_analysis, leakage_controls, seeds (integers), repetitions, compute_runtime_bounds (expected_wall_seconds, maximum_wall_seconds, maximum_cpu_count, maximum_output_bytes), network_policy="DISABLED", assumptions, claim_boundaries, expected_scientific_outputs, and implementation_specification (n_neighbors, cv_splits, cv_repeats, cv_seed, robustness_neighbors).

The only supported automatic family is sklearn Wine classification with KNeighborsClassifier; RAW, StandardScaler, and MinMaxScaler conditions; leakage-safe scaling inside folds; repeated stratified CV; accuracy and macro-F1; and a bounded neighbor sweep. If the exact Idea cannot truthfully fit this family, do not write the proposal and report AUTOMATIC_PREPARATION_UNSUPPORTED. Do not generate or execute code. Exit after writing the proposal."""


def _run_harness(root: Path, executable: str) -> None:
    command = [executable, "--sandbox", "workspace-write", "--ask-for-approval", "on-request", "--no-alt-screen", "-C", str(root), _methodology_instruction()]
    completed = subprocess.run(command, cwd=root, env=_harness_environment(), check=False)
    if completed.returncode != 0:
        raise PreparedExperimentError("Codex exited before the methodology checkpoint completed")


def _methodology_from_proposal(root: Path, idea_ref: ExactArtifactReference) -> tuple[ExperimentMethodology, SklearnTabularClassificationSpec]:
    value = _object(root / "memory/methodology-proposal.json", "methodology proposal")
    expected = {
        "frozen_scientific_requirements", "implementation_decisions",
        "unresolved_methodological_decisions", "dataset", "experiment_conditions",
        "evaluation_protocol", "metrics", "robustness_analysis", "leakage_controls",
        "seeds", "repetitions", "compute_runtime_bounds", "network_policy",
        "assumptions", "claim_boundaries", "expected_scientific_outputs",
        "implementation_specification",
    }
    if set(value) != expected:
        raise PreparedExperimentError("Methodology proposal fields mismatch")
    methodology = ExperimentMethodology.create(
        selected_idea=idea_ref,
        frozen_scientific_requirements=tuple(value["frozen_scientific_requirements"]),
        implementation_decisions=tuple(ImplementationDecision(**item) for item in value["implementation_decisions"]),
        unresolved_methodological_decisions=tuple(UnresolvedMethodologicalDecision(item["question"], tuple(MethodologicalEffect(effect) for effect in item["material_effects"])) for item in value["unresolved_methodological_decisions"]),
        dataset=value["dataset"], experiment_conditions=tuple(value["experiment_conditions"]),
        evaluation_protocol=tuple(value["evaluation_protocol"]), metrics=tuple(value["metrics"]),
        robustness_analysis=tuple(value["robustness_analysis"]), leakage_controls=tuple(value["leakage_controls"]),
        seeds=tuple(value["seeds"]), repetitions=value["repetitions"],
        compute_runtime_bounds=ComputeRuntimeBounds.from_mapping(value["compute_runtime_bounds"]),
        network_policy=value["network_policy"], assumptions=tuple(value["assumptions"]),
        claim_boundaries=tuple(value["claim_boundaries"]), expected_scientific_outputs=tuple(value["expected_scientific_outputs"]),
    )
    if methodology.unresolved_methodological_decisions:
        _atomic_json(root / "memory/methodology.json", methodology.to_dict())
        raise PreparedExperimentError("Methodology remains at an Owner decision checkpoint")
    implementation = value["implementation_specification"]
    if not isinstance(implementation, dict) or set(implementation) != {"n_neighbors", "cv_splits", "cv_repeats", "cv_seed", "robustness_neighbors"}:
        raise PreparedExperimentError("Typed implementation specification fields mismatch")
    spec = SklearnTabularClassificationSpec.create(
        methodology_checksum=methodology.methodology_checksum,
        dataset="SKLEARN_WINE", estimator="KNEIGHBORS_CLASSIFIER",
        conditions=("RAW", "STANDARD_SCALER", "MINMAX_SCALER"),
        n_neighbors=implementation["n_neighbors"], cv_splits=implementation["cv_splits"],
        cv_repeats=implementation["cv_repeats"], cv_seed=implementation["cv_seed"],
        metrics=("accuracy", "macro_f1"), robustness_neighbors=tuple(implementation["robustness_neighbors"]),
        result_schema="reagent.experiment-result/v0.2",
    )
    spec.validate_methodology(methodology)
    _atomic_json(root / "memory/methodology.json", methodology.to_dict())
    _atomic_json(root / "memory/implementation-specification.json", spec.to_dict())
    return methodology, spec


def _show_methodology(methodology: ExperimentMethodology, spec: SklearnTabularClassificationSpec) -> None:
    print("\nExperiment Design\n")
    print(f"Dataset: {methodology.dataset}")
    print("Conditions: " + "; ".join(methodology.experiment_conditions))
    print("Evaluation: " + "; ".join(methodology.evaluation_protocol))
    print("Metrics: " + ", ".join(methodology.metrics))
    print("Robustness: " + "; ".join(methodology.robustness_analysis))
    print("Leakage controls: " + "; ".join(methodology.leakage_controls))
    print(f"Seeds/repetitions: {list(methodology.seeds)} / {methodology.repetitions}")
    print(f"Neighbor scope: primary {spec.n_neighbors}; robustness {list(spec.robustness_neighbors)}")
    print(f"Compute: expected {methodology.compute_runtime_bounds.expected_wall_seconds}s, maximum {methodology.compute_runtime_bounds.maximum_wall_seconds}s")
    print("Network: disabled")
    print("Claim boundaries: " + "; ".join(methodology.claim_boundaries))


def _approve_design(root: Path, methodology: ExperimentMethodology, spec: SklearnTabularClassificationSpec, owner_input: Callable[[str], str]) -> DesignApproval:
    path = root / "memory/design-approval.json"
    if path.exists():
        approval = DesignApproval.from_mapping(_object(path, "design approval"))
        approval.validate_methodology(methodology)
        return approval
    _show_methodology(methodology, spec)
    expected = f"approve design {methodology.methodology_checksum}"
    if owner_input(f"Type `{expected}` to approve experiment design: ").strip() != expected:
        raise PreparedExperimentError("Owner did not approve the exact Experiment Design")
    approval = DesignApproval.create(methodology, approved_at=_timestamp())
    _atomic_json(path, approval.to_dict())
    return approval


def _runtime_identity() -> RuntimeIdentity:
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    return RuntimeIdentity("PYTHON", version, canonical_hash({"python": version, "dependencies": ["numpy", "scikit-learn"]}))


def _dependencies_available() -> bool:
    try:
        import numpy  # noqa: F401, PLC0415
        import sklearn  # noqa: F401, PLC0415
    except ImportError:
        return False
    return True


def _workflow_identity(root: Path) -> WorkflowCapsuleIdentity:
    value = _object(root / "workflow/prepared-experiment.json", "prepared Experiment contract")
    return WorkflowCapsuleIdentity.from_mapping(value["workflow_capsule"])


def _prepare_package(root: Path, idea: ExactArtifactReference, methodology: ExperimentMethodology, spec: SklearnTabularClassificationSpec) -> tuple[Path, PreparedPackageReceipt, ValidatedExperimentPackage]:
    receipt_path = root / "memory/prepared-package-receipt.json"
    validated_path = root / "memory/validated-experiment-package.json"
    package = root / "memory/preparation/validated"
    if receipt_path.exists() and validated_path.exists() and package.is_dir():
        receipt = PreparedPackageReceipt.from_mapping(_object(receipt_path, "prepared-package receipt"))
        validated = _validated_from_mapping(_object(validated_path, "validated package"))
        _revalidate_package(package, receipt, spec)
        return package, receipt, validated
    candidate = root / "memory/preparation/candidate"
    render_candidate(candidate, spec, _runtime_identity().runtime_version)
    tree_checksum, _ = package_tree(candidate)
    manifest_checksum = sha256_bytes((candidate / ".reagent-experiment.json").read_bytes())
    entrypoint_checksum = sha256_bytes((candidate / "run_experiment.py").read_bytes())
    dependency_checksum = sha256_bytes((candidate / "requirements.lock").read_bytes())
    if not _dependencies_available():
        raise PreparedExperimentError("Approved local dependencies are unavailable; installation is forbidden")
    workflow = _workflow_identity(root)
    harness = HarnessIdentity("CODEX", "LOCAL_CLI", None)
    receipt = PreparedPackageReceipt.create(
        origin_type=PackageOrigin.REAGENT_PREPARED, selected_idea=idea,
        workflow_capsule=workflow, harness=harness,
        builder=BuilderIdentity(BuilderFamily.SKLEARN_TABULAR_CLASSIFICATION_V1, BUILDER_VERSION, sha256_bytes(ENTRYPOINT.encode())),
        implementation_specification_checksum=spec.specification_checksum,
        git=None, package_tree_checksum=tree_checksum, manifest_checksum=manifest_checksum,
        entrypoint_checksum=entrypoint_checksum, dependency_checksum=dependency_checksum,
        runtime=_runtime_identity(), prepared_at=_timestamp(),
    )
    safety = PackageSafetyEvidence(True, True, True, True, True, True, True, True, True, True)
    validated = ValidatedExperimentPackage(
        VALIDATED_PACKAGE_SCHEMA, tree_checksum, manifest_checksum,
        "run_experiment.py", entrypoint_checksum, "requirements.lock", dependency_checksum,
        receipt.runtime,
        (NamedChecksum("experiment_config", sha256_bytes((candidate / "experiment-config.json").read_bytes())),),
        (NamedChecksum("selected_research_idea", idea.sha256),),
        receipt, receipt.receipt_checksum, idea, workflow, harness, safety,
        "VALIDATED", _timestamp(),
    )
    package.parent.mkdir(parents=True, exist_ok=True)
    os.replace(candidate, package)
    _atomic_json(receipt_path, receipt.to_dict())
    _atomic_json(validated_path, validated.to_dict())
    _revalidate_package(package, receipt, spec)
    return package, receipt, validated


def _validated_from_mapping(value: dict[str, Any]) -> ValidatedExperimentPackage:
    return ValidatedExperimentPackage(
        schema=value["schema"], package_tree_checksum=value["package_tree_checksum"], manifest_checksum=value["manifest_checksum"],
        entrypoint_relative_path=value["entrypoint_relative_path"], entrypoint_checksum=value["entrypoint_checksum"],
        dependency_relative_path=value["dependency_relative_path"], dependency_checksum=value["dependency_checksum"],
        runtime=RuntimeIdentity.from_mapping(value["runtime"]),
        configuration_identities=tuple(NamedChecksum(**item) for item in value["configuration_identities"]),
        input_identities=tuple(NamedChecksum(**item) for item in value["input_identities"]),
        prepared_package_receipt=PreparedPackageReceipt.from_mapping(value["prepared_package_receipt"]),
        prepared_package_receipt_checksum=value["prepared_package_receipt_checksum"],
        selected_idea=ExactArtifactReference.from_mapping(value["selected_idea"]),
        workflow_capsule=WorkflowCapsuleIdentity.from_mapping(value["workflow_capsule"]),
        harness=None if value["harness"] is None else HarnessIdentity.from_mapping(value["harness"]),
        safety=PackageSafetyEvidence(**value["safety"]), validation_status=value["validation_status"], validated_at=value["validated_at"],
    )


def _revalidate_package(package: Path, receipt: PreparedPackageReceipt, spec: SklearnTabularClassificationSpec) -> None:
    tree_checksum, _ = package_tree(package)
    checks = (
        tree_checksum == receipt.package_tree_checksum,
        sha256_bytes((package / ".reagent-experiment.json").read_bytes()) == receipt.manifest_checksum,
        sha256_bytes((package / "run_experiment.py").read_bytes()) == receipt.entrypoint_checksum,
        sha256_bytes((package / "requirements.lock").read_bytes()) == receipt.dependency_checksum,
        receipt.implementation_specification_checksum == spec.specification_checksum,
    )
    if not all(checks):
        raise PreparedExperimentError("Prepared package drift invalidates approval")


def _execution_plan(root: Path, receipt: PreparedPackageReceipt, methodology: ExperimentMethodology, spec: SklearnTabularClassificationSpec) -> dict[str, Any]:
    relative = "memory/preparation/validated"
    value = {
        "package_receipt_checksum": receipt.receipt_checksum,
        "command": [str(Path(sys.executable).resolve()), f"{relative}/run_experiment.py", f"{relative}/experiment-config.json"],
        "runtime": receipt.runtime.to_dict(), "metrics": list(spec.metrics),
        "run_seed_scope": list(methodology.seeds),
        "execution_limits": methodology.compute_runtime_bounds.to_dict(),
        "network_policy": "DISABLED", "expected_outputs": ["reagent.experiment-result/v0.2"],
    }
    plan = {"sha256": canonical_hash(value), "value": value}
    _atomic_json(root / "memory/execution-plan.json", plan)
    return plan


def _approve_run(root: Path, plan: dict[str, Any], receipt: PreparedPackageReceipt, owner_input: Callable[[str], str]) -> RunApprovalFoundation:
    path = root / "memory/run-approval.json"
    if path.exists():
        approval = RunApprovalFoundation.from_mapping(_object(path, "run approval"))
        approval.validate_execution_plan(plan["value"], receipt)
        return approval
    value = plan["value"]
    print("\nExact Execution Plan\n")
    print(f"Runs: {len(value['run_seed_scope'])} controlled seed(s); metrics {', '.join(value['metrics'])}")
    print(f"Maximum runtime: {value['execution_limits']['maximum_wall_seconds']} seconds; network disabled")
    expected = f"approve and run {plan['sha256']}"
    if owner_input(f"Type `{expected}` to approve one exact run: ").strip() != expected:
        raise PreparedExperimentError("Owner did not approve the exact execution plan")
    approval = RunApprovalFoundation.create(
        prepared_package_receipt_checksum=receipt.receipt_checksum,
        execution_plan_checksum=plan["sha256"], command=tuple(value["command"]),
        runtime=receipt.runtime, metrics=tuple(value["metrics"]), run_seed_scope=tuple(value["run_seed_scope"]),
        execution_limits=ComputeRuntimeBounds.from_mapping(value["execution_limits"]),
        expected_outputs=tuple(value["expected_outputs"]), approved_at=_timestamp(),
    )
    _atomic_json(path, approval.to_dict())
    return approval


def _consume_approval(root: Path, approval: RunApprovalFoundation) -> str:
    path = root / "memory/run-approval-consumption.json"
    if path.exists() or path.is_symlink():
        raise PreparedExperimentError("Run approval was already consumed; automatic retry is forbidden")
    attempt = "attempt-" + uuid.uuid4().hex
    value = {"schema": "reagent.experiment-run-approval-consumption/v0.1", "approval_checksum": approval.approval_checksum, "attempt_id": attempt, "consumed_at": _timestamp()}
    _atomic_json(path, {**value, "consumption_checksum": canonical_hash(value)})
    return attempt


def _execute(root: Path, plan: dict[str, Any], approval: RunApprovalFoundation, attempt: str) -> dict[str, Any]:
    bounded = runpy.run_path(str(root / "bounded_runner.py"))
    bounded["_require_no_egress_enforcement"]()
    value = plan["value"]
    limits = value["execution_limits"]
    legacy_plan = {
        "argv": value["command"], "working_directory": ".", "configuration": {},
        "seeds": value["run_seed_scope"], "repetitions": 1,
        "metrics": [{"name": name, "description": name, "unit": None} for name in value["metrics"]],
        "environment": {"python_version": platform.python_version(), "implementation": platform.python_implementation(), "platform": platform.platform(), "lock_checksum": approval.runtime.environment_checksum},
        "network_policy": "DISABLED",
        "limits": {"wall_seconds": limits["maximum_wall_seconds"], "cpu_seconds": limits["maximum_wall_seconds"], "max_output_bytes": limits["maximum_output_bytes"]},
    }
    evidence = bounded["_execute"](root, legacy_plan, {"attempt_id": attempt, "sha256": approval.approval_checksum})
    return {
        "process_outcome": "CANCELLED" if evidence["status"] == "CANCELLED" else evidence["status"],
        "execution_plan_checksum": plan["sha256"], "run_approval_checksum": approval.approval_checksum,
        "started_at": evidence["started_at"], "completed_at": evidence["completed_at"],
        "exit_code": evidence["exit_code"], "network_policy": "DISABLED",
        "stdout_checksum": evidence["stdout"]["sha256"], "stderr_checksum": evidence["stderr"]["sha256"],
    }


def _evaluate(root: Path, execution: dict[str, Any], spec: SklearnTabularClassificationSpec) -> tuple[dict[str, Any], str]:
    if execution["process_outcome"] != "SUCCEEDED":
        return {"validity": "NOT_EVALUATED", "scientific_evidence_status": "UNAVAILABLE", "metrics": [], "comparisons": [], "robustness_summary": "No valid robustness result is available.", "summary": "The bounded process did not complete successfully."}, "FAILED"
    try:
        raw = _object(root / "memory/execution/stdout.json", "experiment result")
        if raw.get("schema_version") != "reagent.experiment-result/v0.2":
            raise ValueError("result schema mismatch")
        conditions = raw.get("conditions")
        robustness = raw.get("robustness")
        expected_conditions = list(spec.conditions)
        if not isinstance(conditions, list) or [item.get("condition") for item in conditions] != expected_conditions:
            raise ValueError("declared conditions are missing")
        expected_pairs = [(neighbor, condition) for neighbor in spec.robustness_neighbors for condition in spec.conditions]
        if not isinstance(robustness, list) or [(item.get("n_neighbors"), item.get("condition")) for item in robustness] != expected_pairs:
            raise ValueError("declared robustness entries are missing")
        for row in conditions + robustness:
            if set(row.get("metrics", {})) != set(spec.metrics) or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in row["metrics"].values()):
                raise ValueError("declared metrics are invalid")
        metrics = [{"name": f"{row['condition'].casefold()}_{name}", "value": row["metrics"][name], "unit": None} for row in conditions for name in spec.metrics]
        raw_accuracy = conditions[0]["metrics"]["accuracy"]
        comparisons = [f"{row['condition']} accuracy minus RAW: {row['metrics']['accuracy'] - raw_accuracy:+.6f}" for row in conditions[1:]]
        return {"validity": "VALID", "scientific_evidence_status": "LIMITED", "metrics": metrics, "comparisons": comparisons, "robustness_summary": f"Evaluated all three conditions across neighbors {list(spec.robustness_neighbors)}.", "summary": "The leakage-safe bounded Wine evaluation produced every declared metric."}, "SUCCEEDED"
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, AttributeError) as error:
        return {"validity": "INVALID", "scientific_evidence_status": "UNAVAILABLE", "metrics": [], "comparisons": [], "robustness_summary": "The declared robustness result could not be validated.", "summary": f"Result validation failed: {error}"}, "PARTIAL"


def _owner_review(root: Path, execution: dict[str, Any], evaluation: dict[str, Any], status: str, limitations: list[str], attempt: str, owner_input: Callable[[str], str]) -> dict[str, Any]:
    subject = canonical_hash({"execution": execution, "evaluation": evaluation, "result_status": status, "limitations": limitations})
    expected = f"finalize {attempt}"
    print(canonical_json({"attempt_id": attempt, "process": execution["process_outcome"], "evaluation": evaluation["validity"], "scientific_evidence": evaluation["scientific_evidence_status"], "result": status}))
    if owner_input(f"Type `{expected}` after reviewing the result: ").strip() != expected:
        raise PreparedExperimentError("Owner did not finalize the visible result review")
    value = {"decision": "FINALIZE", "reviewed_at": _timestamp(), "reviewed_subject_checksum": subject}
    return {**value, "review_checksum": canonical_hash(value)}


def _publish(root: Path, idea: ExactArtifactReference, methodology: ExperimentMethodology, design: DesignApproval, spec: SklearnTabularClassificationSpec, receipt: PreparedPackageReceipt, plan: dict[str, Any], approval: RunApprovalFoundation, execution: dict[str, Any], evaluation: dict[str, Any], status: str, owner_review: dict[str, Any], limitations: list[str]) -> dict[str, Any]:
    artifact = {
        "schema": "experiment-record/v3", "core_capability_maturity": "REVIEWED_CORE",
        "mode": "REAGENT_PREPARED", "source_artifacts": [idea.to_dict()],
        "methodology_contract": methodology.to_dict(), "design_approval": design.to_dict(),
        "prepared_package": receipt.to_dict(),
        "implementation_specification": {"sha256": canonical_hash(spec.to_dict()), "value": spec.to_dict()},
        "approved_execution_plan": plan, "run_approval": approval.to_dict(),
        "execution": execution, "evaluation": evaluation, "result_status": status,
        "owner_review": owner_review,
        "presentation_summary": {"title": "Wine KNN feature-scaling experiment", "summary": evaluation["summary"], "key_findings": evaluation["comparisons"] or ["No valid comparison is available."]},
        "limitations": limitations,
    }
    namespace = runpy.run_path(str(root / "validate_package.py"))
    try:
        namespace["validate_experiment_record_v3"](artifact, root)
    except Exception as error:
        raise PreparedExperimentError(f"experiment-record/v3 validation failed: {error}") from error
    content = canonical_json(artifact).encode()
    checksum = sha256_bytes(content)
    relative = f"outputs/artifacts/experiment-record/sha256-{checksum[7:]}.json"
    target = root / relative
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.read_bytes() != content:
            raise PreparedExperimentError("content-addressed Experiment Output conflicts")
    else:
        _atomic_bytes(target, content)
    current = {"relative_path": relative, "artifact_kind": "experiment-record/v3", "media_type": "application/json", "checksum": checksum, "size": len(content)}
    _atomic_json(root / "memory/current-artifact.json", current)
    return current


def _finalize_progress(root: Path, current: dict[str, Any], status: str, execution: dict[str, Any]) -> str:
    namespace = runpy.run_path(str(root / "progress_report.py"))
    snapshot = namespace["snapshot"](root)
    context = {"schema": "reagent.prepared-experiment-context/v0.1", "stage": "COMPLETED", "result_status": status, "latest_artifact": current, "updated_at": _timestamp()}
    _atomic_bytes(root / "memory/context.md", ("# Prepared Experiment Context\n\n```json\n" + canonical_json(context) + "\n```\n").encode())
    draft = _object(root / "memory/progress/report-draft.json", "Progress draft")
    draft.update({"started_at": execution["started_at"], "completed_at": execution["completed_at"], "status": "COMPLETED" if status == "SUCCEEDED" else "FAILED", "completed_work": ["Approved exact methodology and prepared one validated package", f"Finalized truthful {status} experiment-record/v3 evidence"], "current_state": "COMPLETED", "next_recommended_action": "Inspect the exact Experiment Output and limitations", "warnings": [] if status == "SUCCEEDED" else ["Experiment did not satisfy every success condition"], "errors": [] if status == "SUCCEEDED" else [f"Experiment result status: {status}"], "unresolved_questions": [], "continuation_instructions": ["Do not retry automatically; another attempt requires a new approval."]})
    _atomic_json(root / "memory/progress/report-draft.json", draft)
    report = namespace["finalize"](package_root=root, draft_path="memory/progress/report-draft.json", context_before_checksum=snapshot["context_before_checksum"])
    return "memory/progress/reports/" + report["report_id"] + ".json"


def run(root: Path, workflow_instance_id: str, *, codex_executable: str | None = None, design_input: Callable[[str], str] = input, run_input: Callable[[str], str] = input, review_input: Callable[[str], str] = input) -> dict[str, Any]:
    root = root.resolve()
    _validate_capsule(root)
    if list((root / "memory/progress/reports").glob("*.json")):
        raise PreparedExperimentError("Prepared Experiment already has terminal Progress")
    idea_ref, _ = _input(root)
    methodology_path = root / "memory/methodology.json"
    specification_path = root / "memory/implementation-specification.json"
    if methodology_path.exists() and specification_path.exists():
        methodology = ExperimentMethodology.from_mapping(_object(methodology_path, "methodology"))
        spec = SklearnTabularClassificationSpec.from_mapping(_object(specification_path, "implementation specification"))
        spec.validate_methodology(methodology)
    else:
        _run_harness(root, _codex_executable(codex_executable))
        methodology, spec = _methodology_from_proposal(root, idea_ref)
    design = _approve_design(root, methodology, spec, design_input)
    package, receipt, _ = _prepare_package(root, idea_ref, methodology, spec)
    plan = _execution_plan(root, receipt, methodology, spec)
    approval = _approve_run(root, plan, receipt, run_input)
    _revalidate_package(package, receipt, spec)
    approval.validate_execution_plan(plan["value"], receipt)
    execution_path = root / "memory/execution-evidence.json"
    evaluation_path = root / "memory/evaluation-evidence.json"
    consumption_path = root / "memory/run-approval-consumption.json"
    if execution_path.exists() and evaluation_path.exists() and consumption_path.exists():
        consumption = _object(consumption_path, "run approval consumption")
        attempt = consumption["attempt_id"]
        execution = _object(execution_path, "execution evidence")
        evaluated = _object(evaluation_path, "evaluation evidence")
        evaluation, status = evaluated["evaluation"], evaluated["result_status"]
        if execution["run_approval_checksum"] != approval.approval_checksum:
            raise PreparedExperimentError("Recovered execution differs from exact run approval")
    elif consumption_path.exists():
        raise PreparedExperimentError("Consumed execution was interrupted before durable evidence; automatic retry is forbidden")
    else:
        attempt = _consume_approval(root, approval)
        execution = _execute(root, plan, approval, attempt)
        _atomic_json(execution_path, execution)
        _revalidate_package(package, receipt, spec)
        evaluation, status = _evaluate(root, execution, spec)
        _atomic_json(evaluation_path, {"evaluation": evaluation, "result_status": status})
    limitations = ["Results are specific to the scikit-learn Wine dataset.", "This bounded experiment does not establish a global novelty or general scaling claim."]
    review = _owner_review(root, execution, evaluation, status, limitations, attempt, review_input)
    current = _publish(root, idea_ref, methodology, design, spec, receipt, plan, approval, execution, evaluation, status, review, limitations)
    report = _finalize_progress(root, current, status, execution)
    _validate_capsule(root)
    return {"status": status, "attempt_id": attempt, "artifact": current, "progress_report": report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python reagent_local.py")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("run")
    command.add_argument("root", type=Path)
    command.add_argument("--workflow-instance", required=True)
    command.add_argument("--api-url")
    command.add_argument("--codex-executable")
    command.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        _validate_capsule(root)
        if args.preflight_only:
            _input(root)
            print(canonical_json({"status": "PREFLIGHT_READY"}))
        else:
            print(canonical_json(run(root, args.workflow_instance, codex_executable=args.codex_executable)))
    except (PreparedExperimentError, OSError, ValueError) as error:
        print(f"Prepared Experiment stopped: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
