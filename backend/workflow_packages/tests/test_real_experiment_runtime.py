from __future__ import annotations

import json
import os
import platform
import re
import sys
from pathlib import Path

import pytest

from backend.artifact_references.research_flow_contracts import (
    ARTIFACT_CONTRACTS,
    validate_experiment_record_v2,
)
from backend.workflow_packages import real_experiment_runtime as runtime
from backend.workflow_packages.production_workflows import build_real_experiment_v0_6_package


def _package(tmp_path: Path) -> Path:
    built = build_real_experiment_v0_6_package(
        project_id="project-" + "a" * 32,
        project_name="Controlled",
        research_topic="Controlled",
        output_root=tmp_path,
        package_id="package-" + "b" * 32,
    )
    return built.package_root


def _plan(root: Path, script: str, *, wall_seconds: int = 5, metrics=None) -> dict:
    path = root / "inputs/experiment-package/run.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script, encoding="utf-8")
    return {
        "research_question": "Does the controlled entrypoint satisfy evaluation?",
        "hypothesis": None,
        "requirements_sha256": "sha256:" + "a" * 64,
        "source_artifacts": [],
        "resource": {},
        "entrypoint": "inputs/experiment-package/run.py",
        "argv": [str(Path(sys.executable).resolve()), "inputs/experiment-package/run.py", "memory/execution/config.json"],
        "working_directory": ".",
        "configuration": {}, "seeds": [1], "repetitions": 1,
        "metrics": metrics or [{"name": "value", "description": "value", "unit": None}],
        "environment": {"python_version": platform.python_version(), "implementation": platform.python_implementation(), "platform": platform.platform(), "lock_checksum": "sha256:" + "b" * 64},
        "network_policy": "DISABLED",
        "limits": {"wall_seconds": wall_seconds, "cpu_seconds": 5, "max_output_bytes": 4096},
        "stopping_conditions": [], "known_limitations": [],
    }


def _approval(plan: dict, attempt: str = "attempt-" + "c" * 32) -> dict:
    payload = {
        "plan_sha256": runtime.canonical_hash(plan), "attempt_id": attempt,
        "approved_at": "2026-08-14T00:00:00Z", "decision": "APPROVED",
        "scope": "ONE_ATTEMPT",
    }
    return {"sha256": runtime.canonical_hash(payload), **payload}


@pytest.mark.parametrize("result_status", ["SUCCEEDED", "FAILED", "PARTIAL"])
def test_experiment_record_v2_contract_is_truthful_and_v1_is_unchanged(
    tmp_path: Path, result_status: str,
) -> None:
    root = _package(tmp_path)
    source = {"artifact_id": "artifact-" + "a" * 32, "artifact_type": "selected-research-idea/v1", "sha256": "sha256:" + "a" * 64}
    runtime._atomic_json(root / "memory/input-provenance.json", {
        "schema_version": "reagent.real-experiment-input-provenance/v0.1",
        "workflow_instance_id": "wfi-" + "a" * 32,
        "artifacts": {"research_idea": source},
    })
    requirements = {
        "research_question": "Does the controlled package produce value?", "hypothesis": None,
        "scientific_inputs": [{"kind": "SOURCE_CODE", "role": "owner-staged package", "required": True}],
        "configuration": {}, "seeds": [1], "repetitions": 1,
        "metrics": [{"name": "value", "description": "value", "unit": None}],
        "runtime": "PYTHON", "limits": {"wall_seconds": 5, "cpu_seconds": 5, "max_output_bytes": 4096},
        "stopping_conditions": [],
    }
    plan = _plan(root, "print('{}')")
    plan.update({
        "requirements_sha256": runtime.canonical_hash(requirements),
        "source_artifacts": [source],
        "resource": {
            "resource_id": "resource-" + "b" * 32, "resource_kind": "SOURCE_REPOSITORY",
            "provider": "GITHUB", "locator": "owner/repo", "exact_revision": "b" * 40,
            "content_checksum": "sha256:" + "b" * 64,
            "package_manifest_checksum": "sha256:" + "c" * 64,
            "entrypoint_checksum": "sha256:" + "d" * 64,
            "lock_checksum": plan["environment"]["lock_checksum"],
        },
    })
    approval = _approval(plan)
    evidence = {"relative_path": "memory/execution/stdout.json", "sha256": "sha256:" + "1" * 64, "availability": "AVAILABLE", "limitation": None}
    process_status = "SUCCEEDED" if result_status != "FAILED" else "FAILED"
    execution = {
        "attempt_id": approval["attempt_id"], "approval_sha256": approval["sha256"],
        "status": process_status, "started_at": "2026-08-14T00:00:00Z",
        "completed_at": "2026-08-14T00:00:01Z", "argv": plan["argv"],
        "working_directory": ".", "environment": plan["environment"],
        "network_policy": "DISABLED", "limits": plan["limits"],
        "exit_code": 0 if process_status == "SUCCEEDED" else 2, "signal": None,
        "stdout": evidence, "stderr": {**evidence, "relative_path": "memory/execution/stderr.log"},
    }
    evaluation_status = "VALID" if result_status == "SUCCEEDED" else ("INVALID" if result_status == "PARTIAL" else "NOT_RUN")
    evaluation = {
        "status": evaluation_status,
        "metrics": ([{"name": "value", "value": 2, "unit": None}] if result_status == "SUCCEEDED" else []),
        "raw_result": evidence if result_status == "SUCCEEDED" else None,
        "summary": "Controlled evaluation state.",
    }
    current = runtime._publish(
        root, requirements, runtime.canonical_hash(requirements), plan,
        runtime.canonical_hash(plan), approval, execution, evaluation, result_status,
    )
    artifact = json.loads((root / current["relative_path"]).read_text())
    assert validate_experiment_record_v2(artifact)["result_status"] == result_status
    assert ARTIFACT_CONTRACTS["experiment-record/v1"].schema == "experiment-record/v1"


def test_plan_hash_and_one_attempt_approval_are_exact(tmp_path: Path) -> None:
    root = _package(tmp_path)
    plan = _plan(root, "print('{}')")
    assert runtime.canonical_hash(plan) == runtime.canonical_hash(json.loads(runtime.canonical_json(plan)))
    attempt = "attempt-" + "d" * 32
    approved = runtime._approval(
        root, plan, runtime.canonical_hash(plan), attempt,
        lambda _prompt: f"approve {runtime.canonical_hash(plan)} {attempt}",
    )
    with pytest.raises(runtime.RealExperimentError, match="does not bind"):
        runtime._consume_approval(root, approved, "sha256:" + "0" * 64)
    runtime._consume_approval(root, approved, runtime.canonical_hash(plan))
    consumption = json.loads((root / "memory/approval-consumption.json").read_text())
    payload = dict(consumption)
    assert payload.pop("sha256") == runtime.canonical_hash(payload)
    with pytest.raises(runtime.RealExperimentError, match="already been consumed"):
        runtime._consume_approval(root, approved, runtime.canonical_hash(plan))
    with pytest.raises(runtime.RealExperimentError, match="automatic retry"):
        runtime._approval(root, plan, runtime.canonical_hash(plan), attempt, lambda _: "")


@pytest.mark.parametrize(("failure", "status"), [
    (KeyboardInterrupt(), "CANCELLED"),
    (OSError("controlled launch failure"), "FAILED"),
])
@pytest.mark.skipif(sys.platform != "darwin", reason="E1 execution boundary is macOS sandbox-exec")
def test_cancellation_and_launch_failure_are_truthful_attempts(
    tmp_path: Path, monkeypatch, failure: BaseException, status: str,
) -> None:
    root = _package(tmp_path)
    plan = _plan(root, "print('{}')")

    def stop(*_args, **_kwargs):
        raise failure

    monkeypatch.setattr(runtime.subprocess, "run", stop)
    execution = runtime._execute(root, plan, _approval(plan))
    assert execution["status"] == status
    assert execution["exit_code"] is None
    assert runtime._evaluate(root, plan, execution)[1] == "FAILED"


@pytest.mark.skipif(sys.platform != "darwin", reason="E1 no-egress mechanism is owner-supported macOS sandbox-exec")
def test_execution_enforces_no_egress_and_scrubs_credentials(tmp_path: Path, monkeypatch) -> None:
    root = _package(tmp_path)
    monkeypatch.setenv("SECRET_TOKEN", "must-not-reach-child")
    script = """import json, os, socket, sys
denied = 0
try:
    socket.create_connection(('127.0.0.1', 9), 0.1)
except PermissionError:
    denied = 1
clean = int(not any('TOKEN' in key or 'SECRET' in key or 'PASSWORD' in key for key in os.environ))
print(json.dumps({'schema_version':'reagent.experiment-result/v0.1','metrics':[{'name':'network_denied','value':denied,'unit':None},{'name':'credentials_scrubbed','value':clean,'unit':None}]}))
"""
    metrics = [
        {"name": "network_denied", "description": "network denied", "unit": None},
        {"name": "credentials_scrubbed", "description": "credentials absent", "unit": None},
    ]
    plan = _plan(root, script, metrics=metrics)
    execution = runtime._execute(root, plan, _approval(plan))
    evaluation, status = runtime._evaluate(root, plan, execution)
    assert execution["status"] == "SUCCEEDED"
    assert execution["argv"] == plan["argv"]
    assert execution["network_policy"] == "DISABLED"
    assert [item["value"] for item in evaluation["metrics"]] == [1, 1]
    assert status == "SUCCEEDED"


@pytest.mark.skipif(sys.platform != "darwin", reason="E1 no-egress mechanism is macOS sandbox-exec")
def test_timeout_nonzero_and_invalid_evaluation_remain_truthful(tmp_path: Path) -> None:
    timed_root = _package(tmp_path / "timed")
    timed_plan = _plan(timed_root, "import time; time.sleep(3)", wall_seconds=1)
    timed = runtime._execute(timed_root, timed_plan, _approval(timed_plan))
    assert timed["status"] == "TIMED_OUT"
    assert runtime._evaluate(timed_root, timed_plan, timed)[1] == "FAILED"

    failed_root = _package(tmp_path / "failed")
    failed_plan = _plan(failed_root, "raise SystemExit(7)")
    failed = runtime._execute(failed_root, failed_plan, _approval(failed_plan))
    assert failed["exit_code"] == 7
    assert runtime._evaluate(failed_root, failed_plan, failed)[1] == "FAILED"

    partial_root = _package(tmp_path / "partial")
    partial_plan = _plan(partial_root, "print('{}')")
    partial = runtime._execute(partial_root, partial_plan, _approval(partial_plan))
    evaluation, status = runtime._evaluate(partial_root, partial_plan, partial)
    assert partial["status"] == "SUCCEEDED"
    assert evaluation["status"] == "INVALID"
    assert status == "PARTIAL"


@pytest.mark.skipif(sys.platform != "darwin", reason="E1 execution boundary is macOS sandbox-exec")
def test_one_attempt_finalizes_v2_and_progress_exactly_once(tmp_path: Path, monkeypatch) -> None:
    root = _package(tmp_path)
    source = {"artifact_id": "artifact-" + "a" * 32, "artifact_type": "selected-research-idea/v1", "sha256": "sha256:" + "a" * 64}
    runtime._atomic_json(root / "memory/input-provenance.json", {
        "schema_version": "reagent.real-experiment-input-provenance/v0.1",
        "workflow_instance_id": "wfi-" + "a" * 32,
        "artifacts": {"research_idea": source},
    })
    package = root / "inputs/experiment-package"
    package.mkdir(parents=True)
    runtime._atomic_json(package / ".reagent-experiment.json", {
        "schema_version": "reagent.experiment-package/v0.1", "entrypoint": "run.py",
        "runtime": "PYTHON", "runtime_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "lock_file": "requirements.lock",
    })
    (package / "requirements.lock").write_text("# no dependencies\n", encoding="utf-8")
    (package / "run.py").write_text(
        "import json\nprint(json.dumps({'schema_version':'reagent.experiment-result/v0.1','metrics':[{'name':'value','value':2,'unit':None}]}))\n",
        encoding="utf-8",
    )
    validator = runtime._validator(root)
    content_checksum, _ = validator["_tree_manifest"](package)
    runtime._atomic_json(root / "memory/resource-provenance.json", {
        "schema_version": "reagent.real-experiment-resource-provenance/v0.1",
        "workflow_instance_id": "wfi-" + "a" * 32,
        "resource_id": "resource-" + "b" * 32, "resource_kind": "SOURCE_REPOSITORY",
        "provider": "GITHUB", "locator": "owner/controlled", "exact_revision": "b" * 40,
        "content_checksum": content_checksum, "target_relative_path": "inputs/experiment-package",
        "package": {
            "manifest_checksum": runtime.sha256_bytes((package / ".reagent-experiment.json").read_bytes()),
            "entrypoint": "run.py", "entrypoint_checksum": runtime.sha256_bytes((package / "run.py").read_bytes()),
            "lock_file": "requirements.lock", "lock_checksum": runtime.sha256_bytes((package / "requirements.lock").read_bytes()),
            "runtime": "PYTHON", "runtime_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        },
    })

    def fake_harness(capsule: Path, _executable: str) -> None:
        context = json.loads((capsule / "memory/plan-context.json").read_text())
        requirements = {
            "research_question": "Does the controlled package produce value two?", "hypothesis": "It does.",
            "scientific_inputs": [{"kind": "SOURCE_CODE", "role": "owner-staged package", "required": True}],
            "configuration": {}, "seeds": [1], "repetitions": 1,
            "metrics": [{"name": "value", "description": "controlled value", "unit": None}],
            "runtime": "PYTHON", "limits": {"wall_seconds": 5, "cpu_seconds": 5, "max_output_bytes": 4096},
            "stopping_conditions": ["one process exits"],
        }
        plan = {
            "research_question": requirements["research_question"], "hypothesis": requirements["hypothesis"],
            "requirements_sha256": runtime.canonical_hash(requirements),
            "source_artifacts": context["source_artifacts"], "resource": context["resource"],
            "entrypoint": context["entrypoint"], "argv": context["argv"],
            "working_directory": context["working_directory"], "configuration": {},
            "seeds": [1], "repetitions": 1, "metrics": requirements["metrics"],
            "environment": context["environment"], "network_policy": context["network_policy"],
            "limits": requirements["limits"], "stopping_conditions": requirements["stopping_conditions"],
            "known_limitations": ["Controlled software-path evidence only."],
        }
        runtime._atomic_json(capsule / "memory/experiment-requirements.json", requirements)
        runtime._atomic_json(capsule / "memory/experiment-plan.json", plan)

    monkeypatch.setattr(runtime, "_run_harness", fake_harness)
    answer = lambda prompt: re.search(r"`([^`]+)`", prompt).group(1)
    result = runtime.run(
        root, "wfi-" + "a" * 32, codex_executable="/usr/bin/true",
        approval_input=answer, review_input=answer,
    )
    assert result["status"] == "SUCCEEDED"
    assert json.loads((root / result["artifact"]["relative_path"]).read_text())["schema"] == "experiment-record/v2"
    report = json.loads((root / result["progress_report"]).read_text())
    assert report["status"] == "COMPLETED"
    assert report["output_artifacts"] == [result["artifact"]]
    with pytest.raises(runtime.RealExperimentError, match="terminal Progress"):
        runtime.run(root, "wfi-" + "a" * 32, codex_executable="/usr/bin/true")
