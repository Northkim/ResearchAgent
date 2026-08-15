#!/usr/bin/env python3
"""Self-contained runner for the first reviewed local Real Experiment Capsule."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import resource
import runpy
import shutil
import signal
import subprocess
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable


class RealExperimentError(RuntimeError):
    pass


_SANDBOX_PROFILE = "(version 1) (allow default) (deny network*) (deny process-fork)"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def canonical_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise RealExperimentError(f"{label} must be one regular unlinked file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RealExperimentError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise RealExperimentError(f"{label} must be an object")
    return value


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise RealExperimentError("output parent is unsafe")
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


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_bytes(path, (canonical_json(value) + "\n").encode("utf-8"))


def _validator(root: Path) -> dict[str, Any]:
    return runpy.run_path(str(root / "validate_package.py"))


def _validate_package(root: Path) -> None:
    try:
        result = _validator(root)["validate"](root, pristine=False)
    except Exception as error:
        raise RealExperimentError(f"Capsule validation failed: {error}") from error
    if result.get("valid") is not True:
        raise RealExperimentError("Capsule validation failed closed")


def _runtime_environment(resource_provenance: dict[str, Any]) -> dict[str, str]:
    package = resource_provenance["package"]
    return {
        "python_version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "lock_checksum": package["lock_checksum"],
    }


def _plan_context(root: Path, workflow_instance_id: str) -> dict[str, Any]:
    inputs = _object(root / "memory/input-provenance.json", "input provenance")
    resources = _object(root / "memory/resource-provenance.json", "Resource provenance")
    package = resources.get("package")
    if not isinstance(package, dict):
        raise RealExperimentError("staged package provenance is unavailable")
    entrypoint = "inputs/experiment-package/" + package["entrypoint"]
    context = {
        "schema_version": "reagent.real-experiment-plan-context/v0.1",
        "workflow_instance_id": workflow_instance_id,
        "source_artifacts": list(inputs["artifacts"].values()),
        "resource": {
            key: resources[key] for key in (
                "resource_id", "resource_kind", "provider", "locator",
                "exact_revision", "content_checksum",
            )
        } | {
            "package_manifest_checksum": package["manifest_checksum"],
            "entrypoint_checksum": package["entrypoint_checksum"],
            "lock_checksum": package["lock_checksum"],
        },
        "entrypoint": entrypoint,
        "argv": [str(Path(sys.executable).resolve()), entrypoint, "memory/execution/config.json"],
        "working_directory": ".",
        "environment": _runtime_environment(resources),
        "network_policy": "DISABLED",
        "supported_limits": {
            "wall_seconds": {"minimum": 1, "maximum": 300},
            "cpu_seconds": {"minimum": 1, "maximum": 300},
            "max_output_bytes": {"minimum": 1024, "maximum": 10_485_760},
        },
    }
    _atomic_json(root / "memory/plan-context.json", context)
    return context


def _codex_executable(value: str | None) -> str:
    selected = value or os.environ.get("REAGENT_CODEX_EXECUTABLE", "codex")
    if os.path.sep in selected:
        path = Path(selected)
        if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
            raise RealExperimentError("configured Codex executable is unavailable")
        return str(path.resolve())
    resolved = shutil.which(selected)
    if resolved is None:
        raise RealExperimentError("Codex CLI is unavailable")
    return resolved


def _instruction() -> str:
    return """REAGENT REAL EXPERIMENT — INPUT_REVIEW

Read AGENT.md, workflow/prompts/real-experiment.md, the exact selected Idea,
memory/input-provenance.json, memory/resource-provenance.json, and
memory/plan-context.json. Do not inspect sibling Capsules or use network.
Derive the smallest honest Experiment Requirements and one exact executable Plan.
Write canonical JSON objects to memory/experiment-requirements.json and
memory/experiment-plan.json using the shapes in workflow/real-experiment.json.
The Plan must copy every exact identity, argv, environment, working directory,
and DISABLED network policy from plan-context; do not improvise execution facts.
Do not execute the package. The ReAgent runner owns approval, execution,
evaluation, result review, Artifact publication, and Progress finalization."""


def _run_harness(root: Path, executable: str) -> None:
    environment = {
        key: os.environ[key]
        for key in ("PATH", "TMPDIR", "LANG", "LC_ALL", "TERM")
        if key in os.environ
    }
    command = [
        executable, "--sandbox", "workspace-write", "--ask-for-approval", "on-request",
        "--no-alt-screen", "-C", str(root), _instruction(),
    ]
    try:
        completed = subprocess.run(command, cwd=root, env=environment, check=False)
    except OSError as error:
        raise RealExperimentError("Codex process could not be started") from error
    if completed.returncode != 0:
        raise RealExperimentError("Codex exited before producing the exact Experiment Plan")


def _load_plan(root: Path, context: dict[str, Any]) -> tuple[dict[str, Any], str, dict[str, Any], str]:
    requirements = _object(root / "memory/experiment-requirements.json", "Experiment Requirements")
    plan = _object(root / "memory/experiment-plan.json", "Experiment Plan")
    namespace = _validator(root)
    try:
        namespace["validate_requirements"](requirements)
        namespace["validate_plan"](plan, context, canonical_hash(requirements))
    except Exception as error:
        raise RealExperimentError(f"Experiment Plan validation failed: {error}") from error
    return requirements, canonical_hash(requirements), plan, canonical_hash(plan)


def _approval(
    root: Path, plan: dict[str, Any], plan_checksum: str, attempt_id: str,
    approval_input: Callable[[str], str],
) -> dict[str, Any]:
    approval_path = root / "memory/experiment-approval.json"
    consumption_path = root / "memory/approval-consumption.json"
    if approval_path.exists() or approval_path.is_symlink() or consumption_path.exists() or consumption_path.is_symlink():
        raise RealExperimentError("an approval or execution attempt already exists; automatic retry is forbidden")
    print("\nExact Experiment Plan\n" + canonical_json(plan), flush=True)
    print(f"\nPlan checksum: {plan_checksum}\nAttempt: {attempt_id}", flush=True)
    print("Trusted owner-staged code; network denied; not a hostile-code sandbox.", flush=True)
    expected = f"approve {plan_checksum} {attempt_id}"
    if approval_input(f"Type `{expected}` to authorize one attempt: ").strip() != expected:
        raise RealExperimentError("Owner did not approve the exact plan and attempt")
    payload = {
        "plan_sha256": plan_checksum,
        "attempt_id": attempt_id,
        "approved_at": _timestamp(),
        "decision": "APPROVED",
        "scope": "ONE_ATTEMPT",
    }
    approval = {"sha256": canonical_hash(payload), **payload}
    _atomic_json(approval_path, approval)
    return approval


def _consume_approval(root: Path, approval: dict[str, Any], plan_checksum: str) -> None:
    current = _object(root / "memory/experiment-approval.json", "Experiment approval")
    payload = dict(current)
    checksum = payload.pop("sha256", None)
    if current != approval or checksum != canonical_hash(payload) or current.get("plan_sha256") != plan_checksum:
        raise RealExperimentError("approval does not bind the current plan")
    consumption = root / "memory/approval-consumption.json"
    if consumption.exists() or consumption.is_symlink():
        raise RealExperimentError("approval has already been consumed")
    payload = {
        "schema_version": "reagent.experiment-approval-consumption/v0.1",
        "approval_sha256": approval["sha256"],
        "attempt_id": approval["attempt_id"],
        "consumed_at": _timestamp(),
    }
    _atomic_json(consumption, {"sha256": canonical_hash(payload), **payload})


def _verify_consumed_approval(root: Path, approval: dict[str, Any]) -> None:
    current = _object(root / "memory/experiment-approval.json", "Experiment approval")
    if current != approval:
        raise RealExperimentError("approval evidence drifted during execution")
    consumption = _object(root / "memory/approval-consumption.json", "approval consumption")
    payload = dict(consumption)
    checksum = payload.pop("sha256", None)
    if (
        checksum != canonical_hash(payload)
        or payload.get("schema_version")
        != "reagent.experiment-approval-consumption/v0.1"
        or payload.get("approval_sha256") != approval["sha256"]
        or payload.get("attempt_id") != approval["attempt_id"]
    ):
        raise RealExperimentError("approval consumption evidence drifted")


def _child_environment(execution_root: Path) -> dict[str, str]:
    environment = {
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
        "TMPDIR": str(execution_root / "tmp"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
    }
    (execution_root / "tmp").mkdir(exist_ok=True)
    return environment


def _limit_process(limits: dict[str, int]) -> Callable[[], None]:
    def apply() -> None:
        resource.setrlimit(resource.RLIMIT_CPU, (limits["cpu_seconds"], limits["cpu_seconds"]))
        resource.setrlimit(resource.RLIMIT_FSIZE, (limits["max_output_bytes"], limits["max_output_bytes"]))
    return apply


def _require_no_egress_enforcement() -> None:
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file():
        raise RealExperimentError("BLOCKED_NO_EGRESS_ENFORCEMENT: macOS sandbox-exec is unavailable")
    probe = (
        "import socket,sys\n"
        "try:\n socket.create_connection(('127.0.0.1',9),0.2)\n"
        "except PermissionError:\n sys.exit(0)\n"
        "except OSError:\n sys.exit(4)\n"
        "sys.exit(3)\n"
    )
    try:
        with tempfile.TemporaryDirectory(prefix="reagent-egress-probe-") as temporary:
            result = subprocess.run(
                ["/usr/bin/sandbox-exec", "-p", _SANDBOX_PROFILE, str(Path(sys.executable).resolve()), "-c", probe],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, env=_child_environment(Path(temporary)),
                check=False, timeout=5,
            )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RealExperimentError("BLOCKED_NO_EGRESS_ENFORCEMENT: enforcement probe failed") from error
    if result.returncode != 0:
        raise RealExperimentError("BLOCKED_NO_EGRESS_ENFORCEMENT: child network denial is not enforceable")


def _execute(root: Path, plan: dict[str, Any], approval: dict[str, Any]) -> dict[str, Any]:
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file():
        raise RealExperimentError("BLOCKED_NO_EGRESS_ENFORCEMENT: macOS sandbox-exec is unavailable")
    execution_root = root / "memory/execution"
    execution_root.mkdir(parents=True, exist_ok=True)
    if execution_root.is_symlink():
        raise RealExperimentError("execution root is unsafe")
    _atomic_json(execution_root / "config.json", {
        "configuration": plan["configuration"],
        "seeds": plan["seeds"],
        "repetitions": plan["repetitions"],
        "metrics": plan["metrics"],
    })
    stdout_path = execution_root / "stdout.json"
    stderr_path = execution_root / "stderr.log"
    started_at = _timestamp()
    exit_code: int | None = None
    signal_name: str | None = None
    status = "FAILED"
    command = ["/usr/bin/sandbox-exec", "-p", _SANDBOX_PROFILE, *plan["argv"]]
    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            child = subprocess.run(
                command, cwd=root, env=_child_environment(execution_root),
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, check=False,
                timeout=plan["limits"]["wall_seconds"],
                preexec_fn=_limit_process(plan["limits"]),
            )
        exit_code = child.returncode
        if child.returncode < 0:
            signal_name = signal.Signals(-child.returncode).name
        status = "SUCCEEDED" if child.returncode == 0 else "FAILED"
    except subprocess.TimeoutExpired:
        status = "TIMED_OUT"
    except KeyboardInterrupt:
        status = "CANCELLED"
    except OSError as error:
        status = "FAILED"
        stderr_path.write_text(f"Process launch failed: {error}\n", encoding="utf-8")
    completed_at = _timestamp()
    for path in (stdout_path, stderr_path):
        if path.stat().st_size > plan["limits"]["max_output_bytes"]:
            status = "FAILED"
    return {
        "attempt_id": approval["attempt_id"],
        "approval_sha256": approval["sha256"],
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "argv": plan["argv"],
        "working_directory": plan["working_directory"],
        "environment": plan["environment"],
        "network_policy": "DISABLED",
        "limits": plan["limits"],
        "exit_code": exit_code,
        "signal": signal_name,
        "stdout": _evidence(root, stdout_path, None),
        "stderr": _evidence(root, stderr_path, None),
    }


def _evidence(root: Path, path: Path, limitation: str | None) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "sha256": sha256_bytes(content),
        "availability": "AVAILABLE",
        "limitation": limitation,
    }


def _evaluate(root: Path, plan: dict[str, Any], execution: dict[str, Any]) -> tuple[dict[str, Any], str]:
    stdout_path = root / execution["stdout"]["relative_path"]
    metrics: list[dict[str, Any]] = []
    raw = None
    if execution["status"] != "SUCCEEDED":
        return {"status": "NOT_RUN", "metrics": [], "raw_result": None, "summary": "Process did not complete successfully; evaluation was not run."}, "FAILED"
    try:
        value = json.loads(stdout_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or set(value) != {"schema_version", "metrics"} or value["schema_version"] != "reagent.experiment-result/v0.1":
            raise ValueError("raw result shape mismatch")
        if not isinstance(value["metrics"], list):
            raise ValueError("metrics are not an array")
        for metric in value["metrics"]:
            if (
                not isinstance(metric, dict)
                or set(metric) != {"name", "value", "unit"}
                or isinstance(metric["value"], bool)
                or not isinstance(metric["value"], (int, float))
                or not math.isfinite(metric["value"])
            ):
                raise ValueError("metric is invalid")
            metrics.append(metric)
        expected = [(item["name"], item["unit"]) for item in plan["metrics"]]
        actual = [(item["name"], item["unit"]) for item in metrics]
        if actual != expected:
            raise ValueError("declared and observed metrics differ")
        raw = _evidence(root, stdout_path, None)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        return {"status": "INVALID", "metrics": metrics, "raw_result": None, "summary": f"Declared evaluation failed: {error}"}, "PARTIAL"
    return {"status": "VALID", "metrics": metrics, "raw_result": raw, "summary": "All declared metrics were present and valid."}, "SUCCEEDED"


def _publish(
    root: Path, requirements: dict[str, Any], requirements_checksum: str,
    plan: dict[str, Any], plan_checksum: str, approval: dict[str, Any],
    execution: dict[str, Any], evaluation: dict[str, Any], result_status: str,
) -> dict[str, Any]:
    sources = list(_object(root / "memory/input-provenance.json", "input provenance")["artifacts"].values())
    artifact = {
        "schema": "experiment-record/v2",
        "core_capability_maturity": "REVIEWED_CORE",
        "mode": "IDEA_EXPERIMENT",
        "source_artifacts": sources,
        "requirements": {"sha256": requirements_checksum, "value": requirements},
        "approved_plan": {"sha256": plan_checksum, "value": plan},
        "approval": approval,
        "execution": execution,
        "evaluation": evaluation,
        "result_status": result_status,
        "limitations": list(plan["known_limitations"]) + [
            "Owner-staged trusted code; hostile-code filesystem containment is not claimed."
        ],
    }
    try:
        _validator(root)["validate_experiment_record_v2"](artifact)
    except Exception as error:
        raise RealExperimentError(f"experiment-record/v2 validation failed: {error}") from error
    content = canonical_json(artifact).encode("utf-8")
    checksum = sha256_bytes(content)
    relative = "outputs/artifacts/experiment-record/sha256-" + checksum[7:] + ".json"
    target = root / relative
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.read_bytes() != content:
            raise RealExperimentError("content-addressed Experiment Output conflicts")
    else:
        _atomic_bytes(target, content)
    current = {
        "relative_path": relative,
        "artifact_kind": "experiment-record/v2",
        "media_type": "application/json",
        "checksum": checksum,
        "size": len(content),
    }
    _atomic_json(root / "memory/current-artifact.json", current)
    return current


def _finalize_progress(root: Path, current: dict[str, Any], result_status: str, execution: dict[str, Any]) -> str:
    namespace = runpy.run_path(str(root / "progress_report.py"))
    snapshot = namespace["snapshot"](root)
    context = {
        "schema_version": "reagent.real-experiment-context/v0.1",
        "stage": "COMPLETED" if result_status == "SUCCEEDED" else "RESULT_REVIEW",
        "attempt_id": execution["attempt_id"],
        "result_status": result_status,
        "latest_artifact": current,
        "updated_at": _timestamp(),
    }
    _atomic_bytes(root / "memory/context.md", ("# Real Experiment Context\n\n```json\n" + canonical_json(context) + "\n```\n").encode("utf-8"))
    draft = _object(root / "memory/progress/report-draft.json", "Progress draft")
    draft.update({
        "started_at": execution["started_at"],
        "completed_at": execution["completed_at"],
        "status": "COMPLETED" if result_status == "SUCCEEDED" else "FAILED",
        "completed_work": ["Executed one checksum-approved local Experiment attempt", f"Finalized truthful {result_status} experiment-record/v2 evidence"],
        "current_state": "COMPLETED" if result_status == "SUCCEEDED" else "RESULT_REVIEW",
        "next_recommended_action": "Inspect the exact Experiment Output and limitations",
        "warnings": ([] if result_status == "SUCCEEDED" else ["Experiment did not satisfy every scientific success condition"]),
        "errors": ([] if result_status == "SUCCEEDED" else [f"Experiment result status: {result_status}"]),
        "unresolved_questions": [],
        "continuation_instructions": ["Do not rerun automatically; a retry requires a new owner approval."],
    })
    _atomic_json(root / "memory/progress/report-draft.json", draft)
    report = namespace["finalize"](package_root=root, draft_path="memory/progress/report-draft.json", context_before_checksum=snapshot["context_before_checksum"])
    return "memory/progress/reports/" + report["report_id"] + ".json"


def run(
    root: Path, workflow_instance_id: str, *, codex_executable: str | None = None,
    approval_input: Callable[[str], str] = input,
    review_input: Callable[[str], str] = input,
) -> dict[str, Any]:
    root = root.resolve()
    _validate_package(root)
    if list((root / "memory/progress/reports").glob("*.json")):
        raise RealExperimentError("Real Experiment already has terminal Progress; automatic retry is forbidden")
    context = _plan_context(root, workflow_instance_id)
    _run_harness(root, _codex_executable(codex_executable))
    requirements, requirements_checksum, plan, plan_checksum = _load_plan(root, context)
    _require_no_egress_enforcement()
    attempt_id = "attempt-" + uuid.uuid4().hex
    approval = _approval(root, plan, plan_checksum, attempt_id, approval_input)
    _, current_requirements_checksum, _, current_plan_checksum = _load_plan(root, context)
    if current_requirements_checksum != requirements_checksum or current_plan_checksum != plan_checksum:
        raise RealExperimentError("Experiment Plan drifted after approval")
    _consume_approval(root, approval, plan_checksum)
    execution = _execute(root, plan, approval)
    _verify_consumed_approval(root, approval)
    _, post_requirements_checksum, _, post_plan_checksum = _load_plan(root, context)
    if post_requirements_checksum != requirements_checksum or post_plan_checksum != plan_checksum:
        raise RealExperimentError("Experiment Plan drifted during execution")
    _validate_package(root)
    evaluation, result_status = _evaluate(root, plan, execution)
    print(canonical_json({"attempt_id": attempt_id, "process": execution["status"], "evaluation": evaluation["status"], "result": result_status}), flush=True)
    expected_review = f"finalize {attempt_id}"
    if review_input(f"Type `{expected_review}` after reviewing the result: ").strip() != expected_review:
        raise RealExperimentError("Owner did not finalize the visible result review")
    current = _publish(root, requirements, requirements_checksum, plan, plan_checksum, approval, execution, evaluation, result_status)
    report = _finalize_progress(root, current, result_status, execution)
    _validate_package(root)
    return {"status": result_status, "attempt_id": attempt_id, "artifact": current, "progress_report": report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python reagent_local.py")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("root", type=Path)
    run_parser.add_argument("--workflow-instance", required=True)
    run_parser.add_argument("--api-url")
    run_parser.add_argument("--codex-executable")
    run_parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        _validate_package(root)
        if args.preflight_only:
            _plan_context(root, args.workflow_instance)
            _require_no_egress_enforcement()
            print(canonical_json({"status": "PREFLIGHT_READY"}))
        else:
            print(canonical_json(run(root, args.workflow_instance, codex_executable=args.codex_executable)))
    except (RealExperimentError, OSError, ValueError) as error:
        print(f"Real Experiment stopped: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
