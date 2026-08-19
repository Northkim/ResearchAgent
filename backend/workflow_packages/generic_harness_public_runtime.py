"""Forward public helpers for Generic Harness Experiment 0.8.

The installed Capsule owns scientific-contract parsing and final Artifact bytes.
The root Workspace launcher supplies natural decisions, Cloud transport, managed
Harness phases, and the existing bounded runner.
"""

from __future__ import annotations

import json
import os
import runpy
import stat
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

from backend.artifact_references.generic_experiment_v5_contracts import (
    EvidenceKind,
    EvidenceSourceKind,
    EvidenceSourceRef,
    ScientificEvidenceBlock,
    validate_experiment_record_v5,
)
from backend.workflow_packages.generic_experiment_contracts import (
    GenericMethodology,
    ResearchObjectiveRef,
)
from backend.workflow_packages.generic_harness_adapter import (
    GenericHarnessEvaluation,
)
from backend.workflow_packages.generic_harness_contracts import (
    GenericHarnessImplementationSpec,
    GenericHarnessValidationReceipt,
)
from backend.workflow_packages.generic_harness_lifecycle import (
    FinalizedGenericHarnessLifecycle,
    specification_from_mapping,
)
from backend.workflow_packages.serialization import (
    canonical_hash,
    canonical_json,
    sha256_bytes,
    to_json_value,
)

WORKFLOW_ID = "reproduction-experiment-local-experimental"
WORKFLOW_VERSION = "0.8.0"
CAPSULE_VERSION = "0.11.0"
ARTIFACT_TYPE = "experiment-record/v5"
MAX_CONTROL_BYTES = 2_097_152


class GenericHarnessPublicRuntimeError(RuntimeError):
    """The forward public Generic Harness runtime failed closed."""


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _safe_relative(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise GenericHarnessPublicRuntimeError("Capsule path is unsafe")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise GenericHarnessPublicRuntimeError("Capsule path is unsafe")
    return value


def _object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise GenericHarnessPublicRuntimeError(f"{label} must be one regular managed file")
    if not 0 < path.stat().st_size <= MAX_CONTROL_BYTES:
        raise GenericHarnessPublicRuntimeError(f"{label} exceeds its bound")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GenericHarnessPublicRuntimeError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise GenericHarnessPublicRuntimeError(f"{label} must be a JSON object")
    return value


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise GenericHarnessPublicRuntimeError("Managed output parent is unsafe")
    with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_json(path: Path, value: Any) -> None:
    _atomic_bytes(path, (canonical_json(value) + "\n").encode("utf-8"))


def validate_capsule(root: Path, *, pristine: bool = False) -> dict[str, Any]:
    package = root.resolve()
    manifest = _object(package / "package-manifest.json", "Package manifest")
    if (
        manifest.get("workflow_id") != WORKFLOW_ID
        or manifest.get("workflow_version") != WORKFLOW_VERSION
        or manifest.get("package_template_version") != CAPSULE_VERSION
    ):
        raise GenericHarnessPublicRuntimeError("Generic Harness Capsule pin mismatch")
    contract = _object(package / "workflow/generic-experiment.json", "Experiment contract")
    if (
        contract.get("output_artifact_type") != ARTIFACT_TYPE
        or contract.get("implementation_fallback") != "GENERIC_AGENT_HARNESS"
        or contract.get("network_policy") != "DISABLED"
    ):
        raise GenericHarnessPublicRuntimeError("Generic Harness contract drifted")
    requirements = contract.get("input_requirements")
    dynamic_paths = contract.get("runtime_dynamic_paths")
    if not isinstance(requirements, list) or not isinstance(dynamic_paths, list):
        raise GenericHarnessPublicRuntimeError("Generic Harness dynamic path contract is invalid")
    dynamic = {
        _safe_relative(item["target_relative_path"])
        for item in requirements if isinstance(item, dict)
    } | {_safe_relative(item) for item in dynamic_paths}
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise GenericHarnessPublicRuntimeError("Package manifest entries are invalid")
    declared: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise GenericHarnessPublicRuntimeError("Package manifest entry is invalid")
        relative = _safe_relative(entry.get("relative_path"))
        declared[relative] = entry
        path = package / relative
        metadata = path.stat(follow_symlinks=False)
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise GenericHarnessPublicRuntimeError("Capsule contains a link or special file")
        if entry.get("mutable_by_harness") is False and sha256_bytes(path.read_bytes()) != entry.get("sha256"):
            raise GenericHarnessPublicRuntimeError("Immutable Capsule file checksum drifted")
    for path in package.rglob("*"):
        if path.is_dir():
            if path.is_symlink():
                raise GenericHarnessPublicRuntimeError("Capsule directory link is unsafe")
            continue
        relative = path.relative_to(package).as_posix()
        if (
            relative != "package-manifest.json"
            and relative not in declared
            and relative not in dynamic
            and not relative.startswith("outputs/artifacts/")
            and path.name != ".DS_Store"
        ):
            raise GenericHarnessPublicRuntimeError("Undeclared Capsule file rejected")
    return {
        "valid": True,
        "package_id": manifest["package_id"],
        "package_checksum": manifest["package_checksum"],
        "manifest_checksum": manifest["manifest_checksum"],
        "declared_file_count": len(entries),
        "harness_acceptance_status": manifest["harness_acceptance_status"],
    }


def validate(root: str | Path, pristine: bool = True) -> dict[str, Any]:
    """Package compiler/Workspace validation entrypoint."""

    return validate_capsule(Path(root), pristine=pristine)


def load_exact_objective(root: Path) -> ResearchObjectiveRef:
    provenance = _object(root / "memory/input-provenance.json", "input provenance")
    if provenance.get("schema_version") != "reagent.generic-experiment-input-provenance/v0.1":
        raise GenericHarnessPublicRuntimeError("Generic input provenance schema mismatch")
    record = provenance.get("artifacts", {}).get("research_idea")
    if not isinstance(record, dict) or set(record) != {"artifact_id", "artifact_type", "sha256"}:
        raise GenericHarnessPublicRuntimeError("One exact selected Research Idea is required")
    path = root / "inputs/selected-research-idea.json"
    if path.is_symlink() or not path.is_file() or sha256_bytes(path.read_bytes()) != record["sha256"]:
        raise GenericHarnessPublicRuntimeError("Selected Research Idea checksum drifted")
    idea = _object(path, "selected Research Idea")
    selected = idea.get("selected_idea")
    if idea.get("schema") != "selected-research-idea/v1" or not isinstance(selected, dict):
        raise GenericHarnessPublicRuntimeError("Selected Research Idea contract is invalid")
    summary = selected.get("research_question") or selected.get("title")
    if not isinstance(summary, str) or not summary.strip():
        raise GenericHarnessPublicRuntimeError("Selected Research Idea has no objective summary")
    return ResearchObjectiveRef(
        record["artifact_type"], record["artifact_id"], record["sha256"], summary,
    )


def methodology_instruction() -> str:
    return """Read inputs/selected-research-idea.json and create memory/methodology-proposal.json only. Express the exact scientific contract as one JSON object with arrays questions_or_hypotheses, inputs_or_materials, protocol, observations_or_outputs, evaluation_criteria, reproducibility_controls, resource_constraints, compute_constraints, assumptions, claim_boundaries, unresolved_material_decisions and network_policy=\"DISABLED\". Separate material scientific choices from implementation details. Do not write implementation code, install packages, execute the experiment, or fabricate Owner decisions. Exit after the exact proposal is durable."""


def load_methodology_proposal(root: Path, objective: ResearchObjectiveRef) -> GenericMethodology:
    value = _object(root / "memory/methodology-proposal.json", "methodology proposal")
    expected = {
        "questions_or_hypotheses", "inputs_or_materials", "protocol",
        "observations_or_outputs", "evaluation_criteria", "reproducibility_controls",
        "resource_constraints", "compute_constraints", "network_policy", "assumptions",
        "claim_boundaries", "unresolved_material_decisions",
    }
    if set(value) != expected:
        raise GenericHarnessPublicRuntimeError("Methodology proposal fields mismatch")
    try:
        methodology = GenericMethodology(
            objective, tuple(value["questions_or_hypotheses"]),
            tuple(value["inputs_or_materials"]), tuple(value["protocol"]),
            tuple(value["observations_or_outputs"]), tuple(value["evaluation_criteria"]),
            tuple(value["reproducibility_controls"]), tuple(value["resource_constraints"]),
            tuple(value["compute_constraints"]), value["network_policy"],
            tuple(value["assumptions"]), tuple(value["claim_boundaries"]),
            tuple(value["unresolved_material_decisions"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise GenericHarnessPublicRuntimeError("Methodology proposal is invalid") from error
    _atomic_json(root / "memory/methodology.json", methodology)
    return methodology


def implementation_instruction(managed_relative_root: str) -> str:
    managed = _safe_relative(managed_relative_root)
    return f"""Read the exact selected Research Idea and approved methodology in the current Capsule. Implement the experiment under {managed}/implementation and write {managed}/contracts/implementation-specification.json using schema reagent.generic-harness-implementation-spec/v0.1. The specification must bind the exact objective and methodology checksums, declare one relative entrypoint, an existing runtime/version, dependencies, runtime capabilities, expected outputs, stable execution units, non-scientific validation commands, compute limits, network_policy=DISABLED, and a bounded implementation summary. Do not install, upgrade, or download anything. Do not execute scientific work. Do not write inside Capsule memory except the already approved methodology files. Exit after implementation and specification are durable."""


def load_implementation_specification(path: Path) -> GenericHarnessImplementationSpec:
    value = _object(path, "Generic Harness implementation specification")
    try:
        specification = specification_from_mapping(value)
    except (KeyError, TypeError, ValueError) as error:
        raise GenericHarnessPublicRuntimeError("Implementation specification is invalid") from error
    if value.get("specification_checksum") != specification.specification_checksum:
        raise GenericHarnessPublicRuntimeError("Implementation specification checksum drifted")
    return specification


ValidationExecutor = Callable[[tuple[str, ...], Path], Mapping[str, Any]]


def validate_implementation(
    *,
    implementation_root: Path,
    methodology: GenericMethodology,
    specification: GenericHarnessImplementationSpec,
    execute_validation: ValidationExecutor,
    validated_at: str | None = None,
) -> GenericHarnessValidationReceipt:
    if (
        specification.objective_checksum != methodology.research_objective.objective_ref_checksum
        or specification.methodology_checksum != methodology.methodology_checksum
    ):
        raise GenericHarnessPublicRuntimeError("Implementation specification lineage drifted")
    from backend.workflow_packages.generic_experiment_coordinator import GenericExperimentCoordinator

    tree_checksum = GenericExperimentCoordinator._scan_package(implementation_root)
    entrypoint = implementation_root / specification.entrypoint_relative_path
    if entrypoint.is_symlink() or not entrypoint.is_file() or entrypoint.stat().st_nlink != 1:
        raise GenericHarnessPublicRuntimeError("Implementation entrypoint is unavailable")
    receipts: list[str] = []
    for command in specification.validation_commands:
        result = dict(execute_validation(command, implementation_root))
        if set(result) != {"returncode", "stdout_checksum", "stderr_checksum"}:
            raise GenericHarnessPublicRuntimeError("Validation executor receipt is invalid")
        if result["returncode"] != 0:
            raise GenericHarnessPublicRuntimeError("Implementation validation failed")
        receipts.append(canonical_hash({"command": command, **result}))
    receipt = GenericHarnessValidationReceipt(
        specification.specification_checksum, methodology.methodology_checksum,
        tree_checksum, sha256_bytes(entrypoint.read_bytes()), tuple(receipts),
        True, True, validated_at or _timestamp(),
    )
    return receipt


def evaluation_instruction(managed_relative_root: str) -> str:
    managed = _safe_relative(managed_relative_root)
    return f"""Read the approved scientific contract, exact execution plan, validated execution outputs, and checksums under {managed}. Write {managed}/evaluation/evaluation.json and {managed}/evaluation/evidence-blocks.json only. Report process outcome separately from scientific validity. The evaluation must bind the exact specification, plan, and output checksums; declare VALID, INVALID, INDETERMINATE, or NOT_EVALUATED; declare bounded scientific evidence status; retain limitations; and set contract_validation_passed only after checking methodology conformity. Evidence blocks may be PROSE, SCALAR, TABLE, SERIES, or exact output references and must cite result-payload or execution-output checksums. Do not rerun the experiment, alter outputs, or claim validity from process success alone."""


def load_evaluation(
    evaluation_path: Path, evidence_path: Path,
) -> tuple[GenericHarnessEvaluation, tuple[ScientificEvidenceBlock, ...]]:
    value = _object(evaluation_path, "Generic Harness evaluation")
    from backend.workflow_packages.generic_harness_lifecycle import evaluation_from_mapping

    try:
        evaluation = evaluation_from_mapping(value)
    except (KeyError, TypeError, ValueError) as error:
        raise GenericHarnessPublicRuntimeError("Generic Harness evaluation is invalid") from error
    if value.get("evaluation_input_checksum") != evaluation.evaluation_input_checksum:
        raise GenericHarnessPublicRuntimeError("Generic Harness evaluation checksum drifted")
    if evidence_path.is_symlink() or not evidence_path.is_file():
        raise GenericHarnessPublicRuntimeError("Bounded evidence document is unavailable")
    try:
        raw_blocks = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GenericHarnessPublicRuntimeError("Bounded evidence document is invalid") from error
    if not isinstance(raw_blocks, list):
        raise GenericHarnessPublicRuntimeError("Bounded evidence must be an array")
    blocks: list[ScientificEvidenceBlock] = []
    for raw in raw_blocks:
        if not isinstance(raw, dict):
            raise GenericHarnessPublicRuntimeError("Bounded evidence block is invalid")
        sources = tuple(EvidenceSourceRef(
            EvidenceSourceKind(item["kind"]), item["name"], item["checksum"],
        ) for item in raw.get("source_refs", []))
        block = ScientificEvidenceBlock(
            raw["block_id"], EvidenceKind(raw["kind"]), raw["label"],
            raw["value"], sources,
        )
        if raw.get("block_checksum") != block.block_checksum:
            raise GenericHarnessPublicRuntimeError("Bounded evidence block checksum drifted")
        blocks.append(block)
    return evaluation, tuple(blocks)


def publish_final_artifact(
    root: Path,
    workflow_instance_id: str,
    finalized: FinalizedGenericHarnessLifecycle,
) -> dict[str, Any]:
    artifact = validate_experiment_record_v5(finalized.artifact)
    content = canonical_json(artifact).encode("utf-8")
    checksum = sha256_bytes(content)
    relative = f"outputs/artifacts/experiment-record/sha256-{checksum[7:]}.json"
    target = root / relative
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.read_bytes() != content:
            raise GenericHarnessPublicRuntimeError("Content-addressed Experiment Output conflicts")
    else:
        _atomic_bytes(target, content)
    current = {
        "relative_path": relative,
        "artifact_kind": ARTIFACT_TYPE,
        "media_type": "application/json",
        "checksum": checksum,
        "size": len(content),
        "workflow_instance_id": workflow_instance_id,
    }
    _atomic_json(root / "memory/current-artifact.json", current)
    return current


def finalize_progress(root: Path, current: Mapping[str, Any]) -> str:
    namespace = runpy.run_path(str(root / "progress_report.py"))
    snapshot = namespace["snapshot"](root)
    now = _timestamp()
    context = {
        "schema": "reagent.generic-harness-experiment-context/v0.1",
        "stage": "COMPLETED", "latest_output": dict(current), "updated_at": now,
    }
    _atomic_bytes(
        root / "memory/context.md",
        ("# Generic Experiment Context\n\n```json\n" + canonical_json(context) + "\n```\n").encode(),
    )
    draft = _object(root / "memory/progress/report-draft.json", "Progress draft")
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
        "next_recommended_action": "Inspect the exact Experiment evidence and limitations",
        "warnings": ["Process success alone does not establish scientific validity"],
        "errors": [], "unresolved_questions": [],
        "continuation_instructions": ["Use the exact experiment-record/v5 downstream"],
    })
    _atomic_json(root / "memory/progress/report-draft.json", draft)
    report = namespace["finalize"](
        package_root=root,
        draft_path="memory/progress/report-draft.json",
        context_before_checksum=snapshot["context_before_checksum"],
    )
    return "memory/progress/reports/" + report["report_id"] + ".json"
