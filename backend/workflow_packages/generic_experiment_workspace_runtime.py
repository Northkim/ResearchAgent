#!/usr/bin/env python3
"""Public Local Workspace entrypoint for generic Experiment 0.6.

This entrypoint intentionally stops at a typed methodology/capability checkpoint.
Later lifecycle stages remain owned by the generic coordinator and the existing
bounded-runner handoff; starting the Workflow never probes or installs a
scientific runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

sys.dont_write_bytecode = True

_ROOT = Path(__file__).resolve().parent
_LIB = _ROOT / "runtime_lib"
if _LIB.is_dir() and str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from backend.workflow_packages.experiment_capability_runtime import (  # noqa: E402
    BoundedCapabilityResolver, CapabilityBinding,
)
from backend.workflow_packages.generic_experiment_contracts import (  # noqa: E402
    ExactIdentity, GenericMethodology, ResearchObjectiveRef,
)
from backend.workflow_packages.generic_experiment_coordinator import (  # noqa: E402
    GenericExperimentCoordinator,
)
from backend.workflow_packages.serialization import (  # noqa: E402
    canonical_hash, canonical_json, sha256_bytes, to_json_value,
)
from backend.workflow_packages.sklearn_reference_capability import (  # noqa: E402
    REFERENCE_DESCRIPTOR, SklearnReferenceCapability,
)

WORKFLOW_ID = "reproduction-experiment-local-experimental"
WORKFLOW_VERSION = "0.6.0"
CAPSULE_VERSION = "0.9.0"
CHECKPOINT_PATH = "memory/generic-checkpoint.json"
METHODOLOGY_PATH = "memory/methodology.json"
PROPOSAL_PATH = "memory/methodology-proposal.json"
MAX_CONTROL_BYTES = 2_097_152


class GenericWorkspaceExperimentError(RuntimeError):
    pass


def _object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise GenericWorkspaceExperimentError(f"{label} must be one regular unlinked file")
    if not 0 < path.stat().st_size <= MAX_CONTROL_BYTES:
        raise GenericWorkspaceExperimentError(f"{label} exceeds its bound")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GenericWorkspaceExperimentError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise GenericWorkspaceExperimentError(f"{label} must be a JSON object")
    return value


def _atomic_json(path: Path, value: Any) -> None:
    content = (canonical_json(value) + "\n").encode("utf-8")
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


def _safe_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise GenericWorkspaceExperimentError("Capsule path is unsafe")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise GenericWorkspaceExperimentError("Capsule path is unsafe")
    return value


def validate(root: str | Path, pristine: bool = True) -> dict[str, Any]:
    """Independently validate the immutable Capsule tree and forward identity."""

    package = Path(root).resolve()
    if package.is_symlink() or not package.is_dir():
        raise GenericWorkspaceExperimentError("Capsule root is unsafe")
    manifest = _object(package / "package-manifest.json", "Package manifest")
    if (
        manifest.get("workflow_id") != WORKFLOW_ID
        or manifest.get("workflow_version") != WORKFLOW_VERSION
        or manifest.get("package_template_version") != CAPSULE_VERSION
    ):
        raise GenericWorkspaceExperimentError("Generic Experiment pin mismatch")
    contract = _object(package / "workflow/generic-experiment.json", "generic Experiment contract")
    requirements = contract.get("input_requirements")
    runtime_paths = contract.get("runtime_dynamic_paths")
    if not isinstance(requirements, list) or not isinstance(runtime_paths, list):
        raise GenericWorkspaceExperimentError("Generic Experiment dynamic path contract is invalid")
    dynamic = {
        _safe_path(item.get("target_relative_path"))
        for item in requirements if isinstance(item, dict)
    } | {_safe_path(item) for item in runtime_paths}
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries or len(entries) > 300:
        raise GenericWorkspaceExperimentError("Capsule file manifest is invalid")
    declared: dict[str, dict[str, Any]] = {}
    folded: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise GenericWorkspaceExperimentError("Capsule file entry is invalid")
        relative = _safe_path(entry.get("relative_path"))
        if relative.casefold() in folded:
            raise GenericWorkspaceExperimentError("Capsule paths collide")
        folded.add(relative.casefold())
        declared[relative] = entry
        path = package.joinpath(*relative.split("/"))
        metadata = path.stat(follow_symlinks=False)
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise GenericWorkspaceExperimentError("Capsule contains a link or special file")
        if entry.get("mutable_by_harness") is False:
            if sha256_bytes(path.read_bytes()) != entry.get("sha256"):
                raise GenericWorkspaceExperimentError("Immutable Capsule file checksum drifted")
        elif pristine and entry.get("mutable_by_harness") is not True:
            raise GenericWorkspaceExperimentError("Capsule mutability declaration is invalid")
    for path in package.rglob("*"):
        if path.is_dir():
            if path.is_symlink():
                raise GenericWorkspaceExperimentError("Capsule directory link rejected")
            continue
        metadata = path.stat(follow_symlinks=False)
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise GenericWorkspaceExperimentError("Capsule dynamic file is unsafe")
        relative = path.relative_to(package).as_posix()
        if (
            relative != "package-manifest.json"
            and relative not in declared
            and relative not in dynamic
            and not relative.startswith("outputs/artifacts/")
        ):
            raise GenericWorkspaceExperimentError("Undeclared Capsule file rejected")
    if (
        contract.get("output_artifact_type") != "experiment-record/v4"
        or contract.get("capability_interface") != "reagent.experiment-capability/v0.1"
        or contract.get("network_policy") != "DISABLED"
    ):
        raise GenericWorkspaceExperimentError("Generic Experiment contract drifted")
    return {
        "valid": True,
        "package_id": manifest["package_id"],
        "package_checksum": manifest["package_checksum"],
        "manifest_checksum": manifest["manifest_checksum"],
        "declared_file_count": len(entries),
        "harness_acceptance_status": manifest["harness_acceptance_status"],
    }


def _exact_input(root: Path) -> tuple[ResearchObjectiveRef, dict[str, Any]]:
    provenance = _object(root / "memory/input-provenance.json", "input provenance")
    if provenance.get("schema_version") != "reagent.generic-experiment-input-provenance/v0.1":
        raise GenericWorkspaceExperimentError("Generic input provenance schema mismatch")
    record = provenance.get("artifacts", {}).get("research_idea")
    if not isinstance(record, dict) or set(record) != {
        "artifact_id", "artifact_type", "sha256",
    }:
        raise GenericWorkspaceExperimentError("One exact selected research Idea is required")
    path = root / "inputs/selected-research-idea.json"
    if sha256_bytes(path.read_bytes()) != record["sha256"]:
        raise GenericWorkspaceExperimentError("Selected research Idea checksum drifted")
    idea = _object(path, "selected research Idea")
    selected = idea.get("selected_idea")
    if idea.get("schema") != "selected-research-idea/v1" or not isinstance(selected, dict):
        raise GenericWorkspaceExperimentError("Selected research Idea contract is invalid")
    summary = selected.get("research_question") or selected.get("title")
    if not isinstance(summary, str) or not summary.strip():
        raise GenericWorkspaceExperimentError("Selected research Idea has no objective summary")
    objective = ResearchObjectiveRef(
        record["artifact_type"], record["artifact_id"], record["sha256"], summary,
    )
    return objective, idea


def _codex_executable(value: str | None) -> str:
    selected = value or os.environ.get("REAGENT_CODEX_EXECUTABLE", "codex")
    resolved = str(Path(selected).resolve()) if os.path.sep in selected else shutil.which(selected)
    if resolved is None or not Path(resolved).is_file() or not os.access(resolved, os.X_OK):
        raise GenericWorkspaceExperimentError("Codex CLI is unavailable")
    return resolved


def _harness_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for key in (
        "REAGENT_PROXY_TOKEN", "REAGENT_LOCAL_SESSION_TOKEN", "REAGENT_DATABASE_URL",
        "REAGENT_TEST_DATABASE_URL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
    ):
        environment.pop(key, None)
    return environment


def _methodology_instruction() -> str:
    return """Construct a generic Experiment Methodology v0.2 for the exact materialized selected-research-idea/v1.
Read inputs/selected-research-idea.json, workflow/prompts/generic-methodology.md, and workflow/capabilities.json. Do not change the research objective to fit an installed Capability. Separate frozen scientific requirements, implementation-only choices, and unresolved choices that materially affect interpretation, reproducibility, evaluation, resources, or claim boundaries. Do not write code, prepare a package, probe a runtime, install dependencies, use Git, or execute an experiment.

Write memory/methodology-proposal.json as exactly one JSON object with these array-of-string fields: questions_or_hypotheses, inputs_or_materials, protocol, observations_or_outputs, evaluation_criteria, reproducibility_controls, resource_constraints, compute_constraints, assumptions, claim_boundaries, unresolved_material_decisions; and network_policy="DISABLED". Every field except unresolved_material_decisions must be non-empty. Preserve genuine unresolved material decisions instead of inventing Owner answers. Exit immediately after writing the file."""


def _run_codex(root: Path, executable: str) -> None:
    command = [
        executable, "--sandbox", "workspace-write", "--ask-for-approval", "on-request",
        "--no-alt-screen", "-C", str(root), _methodology_instruction(),
    ]
    completed = subprocess.run(command, cwd=root, env=_harness_environment(), check=False)
    if completed.returncode != 0:
        raise GenericWorkspaceExperimentError("Codex stopped before durable methodology evidence was written")


_METHODOLOGY_FIELDS = {
    "questions_or_hypotheses", "inputs_or_materials", "protocol",
    "observations_or_outputs", "evaluation_criteria", "reproducibility_controls",
    "resource_constraints", "compute_constraints", "network_policy", "assumptions",
    "claim_boundaries", "unresolved_material_decisions",
}


def _methodology(root: Path, objective: ResearchObjectiveRef) -> GenericMethodology:
    value = _object(root / PROPOSAL_PATH, "methodology proposal")
    if set(value) != _METHODOLOGY_FIELDS:
        raise GenericWorkspaceExperimentError("Generic Methodology proposal fields mismatch")
    try:
        method = GenericMethodology(
            objective,
            tuple(value["questions_or_hypotheses"]), tuple(value["inputs_or_materials"]),
            tuple(value["protocol"]), tuple(value["observations_or_outputs"]),
            tuple(value["evaluation_criteria"]), tuple(value["reproducibility_controls"]),
            tuple(value["resource_constraints"]), tuple(value["compute_constraints"]),
            value["network_policy"], tuple(value["assumptions"]),
            tuple(value["claim_boundaries"]), tuple(value["unresolved_material_decisions"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise GenericWorkspaceExperimentError("Generic Methodology proposal is invalid") from error
    _atomic_json(root / METHODOLOGY_PATH, method)
    return method


def _checkpoint_document(objective: ResearchObjectiveRef, methodology: GenericMethodology, result: Any) -> dict[str, Any]:
    continuation = result.continuation
    return {
        "schema": "reagent.public-generic-experiment-checkpoint/v0.1",
        "status": result.checkpoint.value if result.checkpoint is not None else result.status.value,
        "summary": result.summary,
        "research_objective": to_json_value(objective),
        "methodology": to_json_value(methodology),
        "capability_selection": (
            None if continuation.selection is None else to_json_value(continuation.selection)
        ),
        "selected_capability": (
            None if continuation.capability is None else to_json_value(continuation.capability)
        ),
        "continuation": to_json_value(continuation.durable_receipt()),
        "resume_command": "python reagent_local.py run . --workflow-instance <exact-instance-id>",
    }


def run(root: Path, workflow_instance_id: str, *, codex_executable: str | None = None) -> dict[str, Any]:
    validate(root, pristine=False)
    objective, _idea = _exact_input(root)
    checkpoint_path = root / CHECKPOINT_PATH
    if checkpoint_path.exists():
        checkpoint = _object(checkpoint_path, "generic Experiment checkpoint")
        if checkpoint.get("research_objective", {}).get("objective_ref_checksum") != objective.objective_ref_checksum:
            raise GenericWorkspaceExperimentError("Durable checkpoint objective drifted")
        return checkpoint
    _atomic_json(root / "memory/research-objective.json", objective)
    if not (root / PROPOSAL_PATH).exists():
        _run_codex(root, _codex_executable(codex_executable))
    methodology = _methodology(root, objective)
    implementation = SklearnReferenceCapability()
    resolver = BoundedCapabilityResolver((
        CapabilityBinding(REFERENCE_DESCRIPTOR, implementation),
    ))
    workflow = _object(root / "workflow/generic-experiment.json", "generic Experiment contract")
    coordinator = GenericExperimentCoordinator(
        resolver,
        workflow=ExactIdentity(
            WORKFLOW_ID, WORKFLOW_VERSION, workflow["workflow_checksum"],
        ),
    )
    result = coordinator.assess_and_select(objective, methodology)
    checkpoint = _checkpoint_document(objective, methodology, result)
    _atomic_json(checkpoint_path, checkpoint)
    _atomic_json(root / "memory/capability-selection.json", checkpoint["capability_selection"])
    return checkpoint


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
        validate(root, pristine=False)
        if args.preflight_only:
            _exact_input(root)
            result = {"status": "PREFLIGHT_READY"}
        else:
            result = run(root, args.workflow_instance, codex_executable=args.codex_executable)
        print(canonical_json(result))
    except (GenericWorkspaceExperimentError, OSError, ValueError) as error:
        print(f"Generic Experiment stopped: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
