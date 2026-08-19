"""Root Workspace orchestration for forward Generic Harness Experiments."""

from __future__ import annotations

import json
import os
import runpy
import shutil
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from backend.artifact_references.generic_experiment_v5_contracts import (
    validate_experiment_record_v5,
)
from backend.controlled_local_run_approvals import (
    ControlledLocalRunApproval,
    ControlledLocalRunSummary,
)
from backend.workflow_packages.generic_experiment_contracts import (
    DesignApproval,
    ExactIdentity,
    NamedChecksum,
    ProcessOutcome,
)
from backend.workflow_packages.generic_experiment_coordinator import (
    ExecutionEvidence,
    ExecutionHandoff,
    ExecutionOutput,
    GenericRunApproval,
    OwnerResultReview,
    RunApprovalConsumption,
    SuppliedExecution,
)
from backend.workflow_packages.generic_harness_adapter import system_generic_harness_path
from backend.workflow_packages.generic_harness_lifecycle import (
    PreparedGenericHarnessLifecycle,
    design_approval_from_mapping,
    finalize_supplied_generic_harness_lifecycle,
    prepare_generic_harness_lifecycle,
)
from backend.workflow_packages.generic_harness_public_runtime import (
    evaluation_instruction,
    ensure_progress_draft,
    implementation_instruction,
    load_evaluation,
    load_exact_objective,
    load_implementation_specification,
    load_methodology_proposal,
    methodology_instruction,
    publish_final_artifact,
    validate_capsule,
    validate_implementation,
)
from backend.workflow_packages.generic_harness_workspace import (
    GenericHarnessWorkspace,
    discover_python_runtimes,
)
from backend.workflow_packages.serialization import canonical_hash, canonical_json, sha256_bytes


class GenericHarnessWorkflowError(RuntimeError):
    """The high-level Generic Harness Workflow cannot advance safely."""


class GenericHarnessExecutionInterrupted(GenericHarnessWorkflowError):
    """A bounded execution stopped with durable unit state available."""


@dataclass(frozen=True, slots=True)
class GenericHarnessWorkflowResult:
    status: str
    workflow_instance_id: str
    detail: str
    artifact: dict[str, Any] | None = None
    progress_report: str | None = None


Decision = Callable[[str, list[str], str], None]
HarnessPhase = Callable[[Path, str], None]
ValidationExecutor = Callable[[tuple[str, ...], Path], Mapping[str, Any]]


def _now() -> datetime:
    return datetime.now(UTC)


def _timestamp() -> str:
    return _now().isoformat().replace("+00:00", "Z")


def _read(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise GenericHarnessWorkflowError(f"{label} is unavailable or unsafe")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GenericHarnessWorkflowError(f"{label} is invalid") from error
    if not isinstance(value, dict):
        raise GenericHarnessWorkflowError(f"{label} must be an object")
    return value


def _write_once(path: Path, value: Any, label: str) -> dict[str, Any]:
    document = json.loads(canonical_json(value))
    if path.exists() or path.is_symlink():
        if _read(path, label) != document:
            raise GenericHarnessWorkflowError(f"{label} drifted")
        return document
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write((canonical_json(document) + "\n").encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return document


def _replace_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{path.name}.", dir=path.parent, delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _finalize_progress_with_exact_artifact(
    capsule: Path, current: Mapping[str, Any],
) -> str:
    """Finalize one Generic Harness report with its exact dynamic Artifact."""

    namespace = runpy.run_path(str(capsule / "progress_report.py"))
    snapshot = namespace["snapshot"](capsule)
    now = _timestamp()
    context = {
        "schema": "reagent.generic-harness-experiment-context/v0.1",
        "stage": "COMPLETED",
        "latest_output": dict(current),
        "updated_at": now,
    }
    _replace_bytes(
        capsule / "memory/context.md",
        (
            "# Generic Experiment Context\n\n```json\n"
            + canonical_json(context)
            + "\n```\n"
        ).encode(),
    )
    draft_path = capsule / "memory/progress/report-draft.json"
    draft = _read(draft_path, "Progress draft")
    draft.update({
        "started_at": draft.get("started_at") or now,
        "completed_at": now,
        "status": "COMPLETED",
        "completed_work": [
            "Approved one exact scientific contract",
            "Validated and executed one exact Generic Harness package",
            "Reviewed one bounded scientific result",
        ],
        "current_state": "COMPLETED",
        "next_recommended_action": (
            "Inspect the exact Experiment evidence and limitations"
        ),
        "warnings": [
            "Process success alone does not establish scientific validity"
        ],
        "errors": [],
        "unresolved_questions": [],
        "continuation_instructions": [
            "Use the exact experiment-record/v5 downstream"
        ],
    })
    namespace["_validate_draft"](draft)
    _replace_bytes(
        draft_path, (canonical_json(draft) + "\n").encode("utf-8"),
    )
    if namespace["_existing_reports"](capsule):
        raise GenericHarnessWorkflowError(
            "Generic Harness terminal Progress already exists"
        )
    manifest = _read(capsule / "package-manifest.json", "Package manifest")
    output = {
        "relative_path": current["relative_path"],
        "artifact_kind": current["artifact_kind"],
        "media_type": current["media_type"],
        "checksum": current["checksum"],
        "size": current["size"],
    }
    skill_pins = [
        {
            "pin_type": "SKILL",
            "identity": pin["name"],
            "version": pin["semantic_version"],
            "checksum": pin["checksum"],
        }
        for pin in manifest["skill_pins"]
    ]
    template_pins = [{
        "pin_type": "TEMPLATE",
        "identity": manifest["package_template_id"],
        "version": manifest["package_template_version"],
        "checksum": manifest["manifest_checksum"],
    }]
    base = {
        "schema_version": namespace["SCHEMA_VERSION"],
        "report_id": None,
        "report_content_checksum": None,
        "report_checksum": None,
        "package_id": manifest["package_id"],
        "package_schema_version": manifest["package_schema_version"],
        "package_checksum": manifest["package_checksum"],
        "project_id": manifest["experimental_project_identity"],
        "workflow_id": manifest["workflow_id"],
        "workflow_version": manifest["workflow_version"],
        "workflow_checksum": manifest["workflow_checksum"],
        **draft,
        "output_artifacts": [output],
        "context_before_checksum": snapshot["context_before_checksum"],
        "context_after_checksum": sha256_bytes(
            (capsule / "memory/context.md").read_bytes()
        ),
        "skill_pins": skill_pins,
        "template_pins": template_pins,
        "generated_at": draft["completed_at"],
        "experimental_declaration": namespace["EXPERIMENTAL_DECLARATION"],
    }
    report = namespace["compute_identity"](base)
    namespace["verify_identity"](report)
    reports_root = capsule / "memory/progress/reports"
    target = reports_root / f"{report['report_id']}.json"
    if target.exists() or target.is_symlink():
        raise GenericHarnessWorkflowError("Progress Reports are append-only")
    _replace_bytes(target, (canonical_json(report) + "\n").encode("utf-8"))
    return target.relative_to(capsule).as_posix()


def _lifecycle_times(managed: GenericHarnessWorkspace) -> dict[str, str]:
    path = managed.root / "contracts/lifecycle-times.json"
    if path.exists() or path.is_symlink():
        value = _read(path, "Generic Harness lifecycle times")
    else:
        now = _timestamp()
        value = {
            "prepared_at": now,
            "validated_at": now,
            "runtime_verified_at": now,
        }
        _write_once(path, value, "Generic Harness lifecycle times")
    if set(value) != {"prepared_at", "validated_at", "runtime_verified_at"} or any(
        not isinstance(item, str) or not item.endswith("Z") for item in value.values()
    ):
        raise GenericHarnessWorkflowError("Generic Harness lifecycle times are invalid")
    return value


def _load_design_approval(path: Path, methodology: Any) -> DesignApproval:
    approval = design_approval_from_mapping(_read(path, "methodology approval"))
    approval.validate(methodology)
    return approval


def _completed_result(
    capsule: Path, workflow_instance_id: str,
) -> GenericHarnessWorkflowResult | None:
    current_path = capsule / "memory/current-artifact.json"
    reports = sorted((capsule / "memory/progress/reports").glob("*.json"))
    if not current_path.exists() and not current_path.is_symlink() and not reports:
        return None
    if len(reports) != 1 or (not current_path.exists() and not current_path.is_symlink()):
        raise GenericHarnessWorkflowError("Generic Harness terminal state is incomplete")
    current = _read(current_path, "current Experiment Artifact")
    required = {
        "relative_path", "artifact_kind", "media_type", "checksum", "size",
    }
    if (
        set(current) != required
        or current["artifact_kind"] != "experiment-record/v5"
        or current["media_type"] != "application/json"
    ):
        raise GenericHarnessWorkflowError("Current Experiment Artifact identity is invalid")
    relative = Path(current["relative_path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise GenericHarnessWorkflowError("Current Experiment Artifact path is unsafe")
    artifact_path = capsule / relative
    if (
        artifact_path.is_symlink() or not artifact_path.is_file()
        or artifact_path.stat().st_nlink != 1
        or artifact_path.stat().st_size != current["size"]
        or sha256_bytes(artifact_path.read_bytes()) != current["checksum"]
    ):
        raise GenericHarnessWorkflowError("Current Experiment Artifact bytes drifted")
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        validate_experiment_record_v5(artifact)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise GenericHarnessWorkflowError("Current Experiment Artifact is invalid") from error
    progress = runpy.run_path(str(capsule / "progress_report.py"))
    relative_report = reports[0].relative_to(capsule).as_posix()
    progress["validate_report"](package_root=capsule, report_path=relative_report)
    report = _read(reports[0], "completed Experiment Progress")
    if report.get("status") != "COMPLETED":
        raise GenericHarnessWorkflowError("Completed Experiment Progress drifted")
    return GenericHarnessWorkflowResult(
        "COMPLETED", workflow_instance_id,
        "The exact Generic Harness Experiment result is completed.",
        current, relative_report,
    )


def _default_validation_executor(capsule: Path) -> ValidationExecutor:
    bounded = runpy.run_path(str(capsule / "bounded_runner.py"))

    def execute(command: tuple[str, ...], implementation_root: Path) -> Mapping[str, Any]:
        if not command or command[0] != "python":
            raise GenericHarnessWorkflowError(
                "Generic Harness validation supports declared Python commands only"
            )
        parent = implementation_root.parent / "sync/validation"
        parent.mkdir(parents=True, exist_ok=True)
        attempt = Path(tempfile.mkdtemp(prefix="command-", dir=parent))
        package = attempt / "package"
        try:
            shutil.copytree(implementation_root, package)
            limits = {
                "wall_seconds": 120,
                "cpu_seconds": 120,
                "max_output_bytes": 2_097_152,
            }
            plan = {
                "argv": [str(Path(sys.executable).resolve()), *command[1:]],
                "working_directory": ".", "configuration": {}, "seeds": [],
                "repetitions": 1, "metrics": [],
                "environment": {"runtime": "declared-python-validation"},
                "network_policy": "DISABLED", "limits": limits,
            }
            result = bounded["_execute"](
                package, plan,
                {"attempt_id": "validation-" + uuid.uuid4().hex, "sha256": canonical_hash(plan)},
            )
            execution = package / "memory/execution"
            stdout = execution / "stdout.json"
            stderr = execution / "stderr.log"
            return {
                "returncode": 0 if result["status"] == "SUCCEEDED" else 1,
                "stdout_checksum": sha256_bytes(stdout.read_bytes()),
                "stderr_checksum": sha256_bytes(stderr.read_bytes()),
            }
        finally:
            shutil.rmtree(attempt, ignore_errors=True)

    return execute


class GenericHarnessBoundedRunner:
    """Adapt execution units to the existing no-egress bounded runner."""

    def __init__(
        self,
        *,
        managed: GenericHarnessWorkspace,
        specification: Any,
        validation: Any,
        capsule: Path,
    ) -> None:
        self.managed = managed
        self.specification = specification
        self.validation = validation
        self.bounded = runpy.run_path(str(capsule / "bounded_runner.py"))

    def execute(self, handoff: ExecutionHandoff) -> SuppliedExecution:
        manifest = self.managed.reconcile_execution_manifest(
            self.specification, self.validation, handoff.approval.approval_checksum,
        )
        output_specs = {item.name: item for item in self.specification.expected_outputs}
        timestamps: list[tuple[str, str]] = []
        for unit in self.specification.execution_units:
            state = next(item for item in manifest.units if item.unit_id == unit.unit_id)
            if state.status.value == "COMPLETED":
                assert state.started_at is not None and state.completed_at is not None
                timestamps.append((state.started_at, state.completed_at))
                continue
            attempt_root = self.managed.root / "execution/attempts" / unit.unit_id
            attempt_root.mkdir(parents=True, exist_ok=True)
            limits = dict(self.specification.compute_limits)
            wall = int(limits.get("wall_time_seconds", "300"))
            maximum = int(limits.get("max_output_bytes", "10485760"))
            plan = {
                "argv": [
                    handoff.local_runtime.local_launcher_path,
                    str(handoff.package_root / handoff.plan.launch_target_relative_path),
                    *unit.arguments,
                ],
                "working_directory": ".", "configuration": {}, "seeds": [],
                "repetitions": 1, "metrics": [],
                "environment": handoff.local_runtime.portable_identity(),
                "network_policy": "DISABLED",
                "limits": {
                    "wall_seconds": wall, "cpu_seconds": wall,
                    "max_output_bytes": maximum,
                },
            }
            result = self.bounded["_execute"](
                attempt_root, plan,
                {
                    "attempt_id": f"{handoff.consumption.attempt_id}-{unit.unit_id}",
                    "sha256": handoff.approval.approval_checksum,
                },
            )
            timestamps.append((result["started_at"], result["completed_at"]))
            if result["status"] != "SUCCEEDED":
                raise GenericHarnessExecutionInterrupted(
                    f"Execution unit {unit.unit_id} stopped as {result['status']}"
                )
            outputs: dict[str, bytes] = {}
            for name in unit.expected_output_names:
                path = attempt_root / output_specs[name].relative_path
                if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
                    raise GenericHarnessWorkflowError(
                        f"Execution unit {unit.unit_id} omitted {name}"
                    )
                outputs[name] = path.read_bytes()
            manifest = self.managed.mark_unit_completed(
                manifest, self.specification, unit.unit_id, outputs,
                started_at=result["started_at"], completed_at=result["completed_at"],
            )
        manifest = self.managed.reconcile_execution_manifest(
            self.specification, self.validation, handoff.approval.approval_checksum,
        )
        if manifest.next_pending_unit is not None:
            raise GenericHarnessExecutionInterrupted("Generic Harness execution remains incomplete")
        payloads: list[ExecutionOutput] = []
        identities: list[NamedChecksum] = []
        for unit in self.specification.execution_units:
            state = next(item for item in manifest.units if item.unit_id == unit.unit_id)
            for name, checksum in state.output_checksums:
                content = (self.managed.root / "outputs" / unit.unit_id / name).read_bytes()
                if sha256_bytes(content) != checksum:
                    raise GenericHarnessWorkflowError("Completed execution output drifted")
                payloads.append(ExecutionOutput(name, content))
                identities.append(NamedChecksum(name, checksum))
        started = min((item[0] for item in timestamps), default=_timestamp())
        completed = max((item[1] for item in timestamps), default=started)
        evidence = ExecutionEvidence(
            handoff.plan.plan_checksum, handoff.approval.approval_checksum,
            handoff.consumption.consumption_checksum, ProcessOutcome.SUCCEEDED,
            tuple(identities), True, "DISABLED", started, completed,
        )
        return SuppliedExecution(evidence, tuple(payloads))


def _store_supplied(managed: GenericHarnessWorkspace, supplied: SuppliedExecution) -> None:
    outputs = []
    for item in supplied.outputs:
        matching = [
            path for path in (managed.root / "outputs").glob(f"*/{item.name}")
            if path.is_file() and sha256_bytes(path.read_bytes()) == sha256_bytes(item.content)
        ]
        if len(matching) != 1:
            raise GenericHarnessWorkflowError("Execution output ownership is ambiguous")
        outputs.append({
            "name": item.name,
            "relative_path": matching[0].relative_to(managed.root).as_posix(),
            "checksum": sha256_bytes(item.content),
            "size": len(item.content),
        })
    _write_once(
        managed.root / "execution/supplied-execution.json",
        {"schema": "reagent.generic-harness-supplied-execution/v0.1",
         "evidence": supplied.evidence.to_dict(), "outputs": outputs},
        "supplied execution",
    )


def _load_supplied(managed: GenericHarnessWorkspace) -> SuppliedExecution | None:
    path = managed.root / "execution/supplied-execution.json"
    if not path.exists() and not path.is_symlink():
        return None
    value = _read(path, "supplied execution")
    evidence = value["evidence"]
    outputs: list[ExecutionOutput] = []
    identities: list[NamedChecksum] = []
    for item in value["outputs"]:
        target = managed.root / item["relative_path"]
        if (
            target.is_symlink() or not target.is_file() or target.stat().st_nlink != 1
            or target.stat().st_size != item["size"]
            or sha256_bytes(target.read_bytes()) != item["checksum"]
        ):
            raise GenericHarnessWorkflowError("Durable execution output drifted")
        content = target.read_bytes()
        outputs.append(ExecutionOutput(item["name"], content))
        identities.append(NamedChecksum(item["name"], item["checksum"]))
    supplied_evidence = ExecutionEvidence(
        evidence["execution_plan_checksum"], evidence["run_approval_checksum"],
        evidence["approval_consumption_checksum"],
        ProcessOutcome(evidence["process_outcome"]), tuple(identities),
        evidence["bounds_respected"], evidence["network_policy"],
        evidence["started_at"], evidence["completed_at"],
    )
    if evidence.get("evidence_checksum") != supplied_evidence.evidence_checksum:
        raise GenericHarnessWorkflowError("Execution evidence checksum drifted")
    return SuppliedExecution(supplied_evidence, tuple(outputs))


def _approval_request(
    prepared: PreparedGenericHarnessLifecycle,
    *, project_id: str, workflow_instance_id: str,
) -> ControlledLocalRunApproval:
    state = prepared.continuation
    assert state.execution_plan and state.validated_package and state.runtime_compatibility
    summary = ControlledLocalRunSummary(
        "One exact Generic Harness experiment package",
        state.objective.objective_summary,
        "System-owned Generic Agent Harness under the approved scientific contract",
        tuple(item.requirement_key for item in state.requirements.resource_requirements),
        (
            f"Existing {state.local_runtime.runtime_family} "
            f"{state.local_runtime.runtime_version}"
        ),
        state.execution_plan.network_policy,
        tuple(f"{name}: {value}" for name, value in state.execution_plan.execution_limits),
        tuple(item.name for item in state.execution_plan.expected_outputs),
        "Contract validation, exact output checksums, bounded evaluation, and Owner result review",
        tuple(state.methodology.assumptions), tuple(state.methodology.claim_boundaries),
    )
    return ControlledLocalRunApproval.create(
        project_id=project_id, workflow_instance_id=workflow_instance_id,
        research_objective_checksum=state.objective.objective_ref_checksum,
        execution_plan_checksum=state.execution_plan.plan_checksum,
        validated_package_checksum=state.validated_package.validated_package_checksum,
        runtime_compatibility_checksum=state.runtime_compatibility.compatibility_checksum,
        capability_checksum=state.capability.capability_checksum,
        summary=summary, created_at=_now(),
    )


def _generic_approval(plan: Any, projection: Mapping[str, Any]) -> GenericRunApproval:
    decided_at = projection.get("decided_at")
    if not isinstance(decided_at, str):
        raise GenericHarnessWorkflowError("Cloud run approval has no decision time")
    return GenericRunApproval.approve(plan, decided_at)


def advance_generic_harness_workflow(
    *,
    capsule: Path,
    workspace_root: Path,
    project_id: str,
    workflow_instance_id: str,
    run_harness: HarnessPhase,
    owner_decision: Decision,
    transport: Any,
    validation_executor: ValidationExecutor | None = None,
    bounded_runner: Any | None = None,
    runtime_candidates: tuple[str, ...] = (),
) -> GenericHarnessWorkflowResult:
    """Advance one exact forward Generic Experiment without hidden orchestration."""

    workspace_root = workspace_root.resolve()
    capsule = capsule.resolve()
    validate_capsule(capsule, pristine=False)
    completed = _completed_result(capsule, workflow_instance_id)
    if completed is not None:
        return completed
    objective = load_exact_objective(capsule)
    ensure_progress_draft(capsule)
    managed = GenericHarnessWorkspace(workspace_root, project_id, workflow_instance_id)
    managed.initialize()
    proposal = capsule / "memory/methodology-proposal.json"
    if not proposal.exists() and not proposal.is_symlink():
        run_harness(capsule, methodology_instruction())
    methodology = load_methodology_proposal(capsule, objective)
    if methodology.unresolved_material_decisions:
        return GenericHarnessWorkflowResult(
            "METHODOLOGY_DECISION_REQUIRED", workflow_instance_id,
            "Material scientific choices remain unresolved.",
        )
    approval_path = managed.root / "contracts/methodology-approval.json"
    if not approval_path.exists() and not approval_path.is_symlink():
        owner_decision(
            "Experiment methodology is ready",
            [
                f"Research question: {methodology.questions_or_hypotheses[0]}",
                f"Protocol: {methodology.protocol[0]}",
                f"Evaluation: {methodology.evaluation_criteria[0]}",
                f"Claim boundary: {methodology.claim_boundaries[0]}",
            ],
            "Codex will implement and validate this exact scientific contract locally; no experiment runs yet.",
        )
        _write_once(
            approval_path, DesignApproval.approve(methodology, _timestamp()),
            "methodology approval",
        )
    design_approval = _load_design_approval(approval_path, methodology)
    spec_path = managed.root / "contracts/implementation-specification.json"
    if not spec_path.exists() and not spec_path.is_symlink():
        relative = managed.root.relative_to(workspace_root).as_posix()
        run_harness(workspace_root, implementation_instruction(relative))
    specification = load_implementation_specification(spec_path)
    dependency_names = tuple(item.name for item in specification.dependencies)
    dependency_constraints = tuple(
        (item.name, item.version_constraint) for item in specification.dependencies
    )
    discovery = discover_python_runtimes(
        version_constraint=specification.runtime_version_constraint,
        required_packages=dependency_names,
        package_constraints=dependency_constraints,
        candidate_paths=runtime_candidates,
    )
    if not discovery.candidates:
        detail = "; ".join(
            reason for _candidate, reasons in discovery.rejected for reason in reasons
        ) or "No compatible existing Python environment was found."
        return GenericHarnessWorkflowResult("RUNTIME_INCOMPATIBLE", workflow_instance_id, detail)
    validation_path = managed.root / "contracts/implementation-validation.json"
    if not validation_path.exists() and not validation_path.is_symlink():
        validation = validate_implementation(
            implementation_root=managed.root / "implementation",
            methodology=methodology, specification=specification,
            execute_validation=validation_executor or _default_validation_executor(capsule),
        )
        _write_once(validation_path, validation, "implementation validation")
    from backend.workflow_packages.generic_harness_lifecycle import validation_from_mapping

    validation = validation_from_mapping(_read(validation_path, "implementation validation"))
    contract = _read(capsule / "workflow/generic-experiment.json", "Experiment contract")
    identity = contract["workflow_capsule"]
    workflow = ExactIdentity(
        identity["workflow_definition_id"], identity["workflow_version"],
        identity["workflow_checksum"],
    )
    times = _lifecycle_times(managed)
    prepared = prepare_generic_harness_lifecycle(
        workspace=managed, workflow=workflow, objective=objective,
        methodology=methodology, design_approval=design_approval,
        path=system_generic_harness_path(), specification=specification,
        validation=validation, discovery=discovery,
        prepared_at=times["prepared_at"], validated_at=times["validated_at"],
        runtime_verified_at=times["runtime_verified_at"],
    )
    state = prepared.continuation
    assert state.execution_plan is not None
    request_path = managed.root / "contracts/run-approval-request.json"
    if not request_path.exists() and not request_path.is_symlink():
        request = _approval_request(
            prepared, project_id=project_id,
            workflow_instance_id=workflow_instance_id,
        )
        response = transport.report_run_approval(
            project_id, workflow_instance_id, request.request_dict(),
        )
        if response.get("request_checksum") != request.request_checksum:
            raise GenericHarnessWorkflowError("Cloud acknowledged a different run request")
        _write_once(request_path, request.request_dict(), "run approval request")
        return GenericHarnessWorkflowResult(
            "RUN_APPROVAL_REQUIRED", workflow_instance_id,
            "The exact validated run plan is waiting for Owner approval.",
        )
    request = _read(request_path, "run approval request")
    if (
        request.get("execution_plan_checksum") != state.execution_plan.plan_checksum
        or request.get("validated_package_checksum")
        != state.validated_package.validated_package_checksum
    ):
        raise GenericHarnessWorkflowError("Durable run request drifted from the current plan")
    projection = transport.observe_run_approval(project_id, workflow_instance_id)
    cloud = projection.get("request")
    if not isinstance(cloud, dict) or cloud.get("request_checksum") != request["request_checksum"]:
        raise GenericHarnessWorkflowError("Cloud run approval projection drifted")
    if cloud.get("status") in {"REQUESTED", "REJECTED"}:
        return GenericHarnessWorkflowResult(
            "RUN_APPROVAL_REQUIRED", workflow_instance_id,
            "The exact run plan still requires Owner approval." if cloud["status"] == "REQUESTED"
            else "The Owner declined this exact run plan.",
        )
    approval = _generic_approval(state.execution_plan, cloud)
    consumption_path = managed.root / "contracts/run-approval-consumption.json"
    if not consumption_path.exists() and not consumption_path.is_symlink():
        if cloud.get("status") != "APPROVED":
            raise GenericHarnessWorkflowError(
                "Consumed Cloud approval has no exact local consumption receipt"
            )
        attempt_id = "attempt-" + uuid.uuid4().hex
        consumed = transport.consume_run_approval(
            project_id, workflow_instance_id, cloud["request_id"],
            {"execution_plan_checksum": state.execution_plan.plan_checksum,
             "attempt_id": attempt_id},
        )
        cloud = consumed["approval"]
        receipt = consumed["receipt"]
        _write_once(
            consumption_path, {"approval": cloud, "receipt": receipt},
            "run approval consumption",
        )
    consumed = _read(consumption_path, "run approval consumption")
    receipt = consumed["receipt"]
    if (
        consumed["approval"].get("request_checksum") != request["request_checksum"]
        or receipt.get("execution_plan_checksum") != state.execution_plan.plan_checksum
        or receipt.get("approval_checksum") != cloud.get("approval_checksum")
    ):
        raise GenericHarnessWorkflowError("Run approval consumption drifted")
    consumption = RunApprovalConsumption(
        approval.approval_checksum, state.execution_plan.plan_checksum,
        receipt["attempt_id"], receipt["consumed_at"],
    )
    supplied = _load_supplied(managed)
    if supplied is None:
        runner = bounded_runner or GenericHarnessBoundedRunner(
            managed=managed, specification=specification,
            validation=validation, capsule=capsule,
        )
        supplied = runner.execute(ExecutionHandoff(
            state.execution_plan, approval, consumption,
            state.validated_package_root, state.local_runtime,
        ))
        _store_supplied(managed, supplied)
    evaluation_path = managed.root / "evaluation/evaluation.json"
    evidence_path = managed.root / "evaluation/evidence-blocks.json"
    if not evaluation_path.exists() or not evidence_path.exists():
        relative = managed.root.relative_to(workspace_root).as_posix()
        run_harness(workspace_root, evaluation_instruction(relative))
    evaluation, evidence_blocks = load_evaluation(evaluation_path, evidence_path)
    prepared.implementation.evaluation = evaluation
    evaluated = prepared.coordinator.authorize_run(
        prepared.continuation, approval,
    ).continuation
    evaluated = prepared.coordinator.accept_execution_evidence(
        evaluated, supplied, consumption,
    ).continuation
    evaluated = prepared.coordinator.evaluate(evaluated).continuation
    review_path = managed.root / "contracts/result-review.json"
    if not review_path.exists() and not review_path.is_symlink():
        owner_decision(
            "Experiment evidence is ready for review",
            [
                f"Process outcome: {evaluated.normalized_result.process_outcome.value}",
                f"Evaluation validity: {evaluated.normalized_result.evaluation_validity.value}",
                f"Scientific evidence: {evaluated.normalized_result.scientific_evidence_status.value}",
                f"Limitations: {len(evaluated.normalized_result.limitations)}",
            ],
            "Approval publishes this exact bounded result as experiment-record/v5.",
        )
        decision = (
            "ACCEPT_BOUNDED_RESULT"
            if evaluated.normalized_result.evaluation_validity.value == "VALID"
            else "ACKNOWLEDGE_LIMITED_OR_INVALID"
        )
        review = OwnerResultReview(
            evaluated.evaluation.receipt.evaluation_checksum,
            canonical_hash(evaluated.normalized_result), decision, _timestamp(),
        )
        _write_once(review_path, review, "result review")
    review_value = _read(review_path, "result review")
    review = OwnerResultReview(
        review_value["evaluation_checksum"], review_value["normalized_result_checksum"],
        review_value["decision"], review_value["reviewed_at"],
    )
    if review_value.get("review_checksum") != review.review_checksum:
        raise GenericHarnessWorkflowError("Result review checksum drifted")
    finalized = finalize_supplied_generic_harness_lifecycle(
        prepared, approval=approval, consumption=consumption, supplied=supplied,
        evaluation=evaluation, owner_review=review, evidence_blocks=evidence_blocks,
    )
    current = publish_final_artifact(capsule, workflow_instance_id, finalized)
    report = _finalize_progress_with_exact_artifact(capsule, current)
    return GenericHarnessWorkflowResult(
        "COMPLETED", workflow_instance_id,
        "The exact Generic Harness Experiment result is completed.",
        current, report,
    )
