"""Controlled public Workspace qualification for Real Writing W1.

The fixtures are synthetic software-path evidence, not scientific evidence.
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import pty
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import httpx

from backend.api import ApplicationContainer, create_app
from backend.artifact_references.research_flow_contracts import (
    validate_experiment_record_v2,
    validate_manuscript_draft_v2,
)
from backend.artifact_references.tests.test_research_flow_contracts import (
    CANDIDATE_A,
    _library,
    _selected,
)
from backend.cloud_api_proxy import (
    CloudAPIProxyService,
    DeterministicFakePaperSearchAdapter,
    InMemoryProxyDatabase,
    InMemoryProxyUnitOfWork,
)
from backend.cloud_api_proxy.composition import ProxyApplicationContainer
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.production_workflows import (
    REAL_WRITING_CAPSULE_CHECKSUM,
    REAL_WRITING_CAPSULE_ID,
)
from backend.project_workspaces.tests.test_f1b_full_scaffold_flow import _seed_upstream
from backend.project_workspaces.tests.test_owner_real_research_gate import _loopback_server
from backend.workflow_packages import real_experiment_runtime
from backend.workflow_packages.production_workflows import (
    REAL_EXPERIMENT_V0_7_CAPSULE_ID,
)
from backend.workflow_packages.serialization import canonical_hash, canonical_json, sha256_bytes

WORKFLOW_ID = "writing-local-experimental"
WORKFLOW_VERSION = "0.3.0"
CAPSULE_VERSION = "0.5.0"
DRIVER_TIMEOUT_SECONDS = 120.0


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _write(path: Path, value) -> None:
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def _qualification_app(root: Path, database: InMemoryDatabase):
    proxy_database = InMemoryProxyDatabase()
    proxy_service = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(proxy_database),
        adapter=DeterministicFakePaperSearchAdapter(),
    )
    return create_app(
        ApplicationContainer(
            unit_of_work_factory=lambda: InMemoryUnitOfWork(database),
            local_package_root=str(root / "cloud-packages"),
        ),
        proxy_container=ProxyApplicationContainer(service=proxy_service),
        enable_experimental_proxy=True,
        enable_local_workflow_sessions=True,
    )


def _run_public_pty(
    command: list[str], *, cwd: Path, environment: dict[str, str],
    timeout_seconds: float = DRIVER_TIMEOUT_SECONDS,
) -> str:
    master_fd, slave_fd = pty.openpty()
    output = bytearray()
    answered: set[str] = set()
    eof = False
    process = None
    deadline = time.monotonic() + timeout_seconds
    patterns = (
        re.compile(r"Type `(approve sha256:[0-9a-f]{64})`"),
        re.compile(r"Type `(finalize sha256:[0-9a-f]{64})`"),
    )
    try:
        process = subprocess.Popen(command, cwd=cwd, env=environment, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd, close_fds=True)
        os.close(slave_fd); slave_fd = -1
        os.set_blocking(master_fd, False)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                process.kill(); process.wait(timeout=5)
                raise RuntimeError("public Writing PTY did not resolve before deadline")
            returncode = process.poll()
            if returncode is not None and eof:
                break
            if eof:
                try:
                    process.wait(timeout=min(0.2, remaining))
                except subprocess.TimeoutExpired:
                    pass
                continue
            ready, _, _ = select.select([master_fd], [], [], min(0.2, remaining))
            if not ready:
                continue
            try:
                chunk = os.read(master_fd, 65_536)
            except BlockingIOError:
                continue
            except OSError as error:
                if error.errno == errno.EIO:
                    eof = True; continue
                raise
            if not chunk:
                eof = True; continue
            output.extend(chunk)
            captured = output.decode("utf-8", errors="replace")
            for pattern in patterns:
                match = pattern.search(captured)
                if match is not None and match.group(1) not in answered:
                    os.write(master_fd, (match.group(1) + "\n").encode())
                    answered.add(match.group(1))
        returncode = process.wait(timeout=max(0.1, deadline - time.monotonic()))
    finally:
        if slave_fd >= 0:
            os.close(slave_fd)
        os.close(master_fd)
    captured = output.decode("utf-8", errors="replace")
    _require(returncode == 0, f"public Writing run failed ({returncode}):\n{captured}")
    _require(len(answered) == 2, "public Writing run missed an exact Owner checkpoint")
    return captured


def _fake_harness(root: Path) -> Path:
    path = root / "controlled-fake-writing-codex"
    path.write_text(
        "#!/usr/bin/env python3\nimport json,pathlib,sys\n"
        "root=pathlib.Path.cwd(); instruction=sys.argv[-1]\n"
        "load=lambda p:json.loads((root/p).read_text()); dump=lambda p,v:(root/p).write_text(json.dumps(v,sort_keys=True,separators=(',',':'))+'\\n')\n"
        "sources=load('memory/input-provenance.json')['artifacts']; ref=lambda s,i,l=None:{**s,'evidence_item':i,'location':i,'availability':'LIMITED' if l else 'AVAILABLE','limitation':l}\n"
        f"paper={CANDIDATE_A!r}\n"
        "if 'INPUT_REVIEW THROUGH OUTLINE' in instruction:\n"
        " brief={'document_type':'initial research manuscript','working_title':'Controlled Evidence-Bound Draft','target_audience':'research owner','target_words':{'minimum':300,'maximum':1200},'requested_sections':['Introduction','Proposed Method','Results'],'citation_style':'numeric','abstract_requested':False,'owner_constraints':['No fabricated results']}\n"
        " status='SUPPORTED' if 'experiment_record' in sources else 'UNAVAILABLE'; result_refs=[ref(sources['experiment_record'],'evaluation.metrics.value')] if 'experiment_record' in sources else []\n"
        " evidence=[{'section':'Introduction','support_status':'SUPPORTED','evidence_refs':[ref(sources['literature_library'],paper,'Abstract-level evidence only')],'limitations':['No full text']},{'section':'Proposed Method','support_status':'PLANNED','evidence_refs':[ref(sources['research_idea'],'selected_idea.proposed_direction')],'limitations':[]},{'section':'Results','support_status':status,'evidence_refs':result_refs,'limitations':[] if result_refs else ['No Experiment bound']}]\n"
        " dump('memory/writing-brief.json',brief);dump('memory/evidence-map.json',evidence);dump('memory/outline.json',[{'heading':x['section'],'support_status':x['support_status']} for x in evidence])\n"
        "else:\n"
        " citation={'citation_id':'cite-1','paper_id':paper,'source_artifact':sources['literature_library'],'evidence_scope':'ABSTRACT','reference_markdown':'[1] Controlled synthetic paper.'}\n"
        " claims=[{'claim_id':'claim-1','claim_type':'LITERATURE','section':'Introduction','claim_text':'The selected abstract describes a bounded observation.','support_status':'SUPPORTED','evidence_refs':[ref(sources['literature_library'],paper,'Abstract-level evidence only')],'citation_ids':['cite-1'],'limitations':['No full text']},{'claim_id':'claim-2','claim_type':'PROPOSAL','section':'Proposed Method','claim_text':'The study will evaluate the proposed comparison.','support_status':'PLANNED','evidence_refs':[ref(sources['research_idea'],'selected_idea.proposed_direction')],'citation_ids':[],'limitations':[]}]\n"
        " if 'experiment_record' in sources: claims.append({'claim_id':'claim-3','claim_type':'RESULT','section':'Results','claim_text':'The controlled execution produced value five.','support_status':'SUPPORTED','evidence_refs':[ref(sources['experiment_record'],'evaluation.metrics.value')],'citation_ids':[],'limitations':['Synthetic fixture']}); result='The controlled execution produced value five.'\n"
        " else: claims.append({'claim_id':'claim-3','claim_type':'RESULT','section':'Results','claim_text':'Observed results are unavailable.','support_status':'UNAVAILABLE','evidence_refs':[],'citation_ids':[],'limitations':['No Experiment bound']}); result='Observed results are unavailable; no result is claimed.'\n"
        " dump('memory/claims.json',claims);dump('memory/citations.json',[citation]);(root/'outputs/draft.md').write_text('# Controlled Evidence-Bound Draft\\n\\n## Introduction\\nThe selected abstract describes a bounded observation [1].\\n\\n## Proposed Method\\nThe study will evaluate the proposed comparison.\\n\\n## Results\\n'+result+'\\n\\n## References\\n[1] Controlled synthetic paper.\\n')\n",
        encoding="utf-8",
    )
    path.chmod(0o700)
    return path


def _real_codex_wrapper(root: Path, executable: Path) -> Path:
    """Adapt the public interactive Harness hook to one bounded Codex exec."""

    path = root / "bounded-real-writing-codex"
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import os,sys\n"
        f"executable={str(executable)!r}\n"
        "os.execv(executable,[executable,'exec','-c',"
        "'model_reasoning_effort=\"medium\"','--sandbox','workspace-write',"
        "'--skip-git-repo-check',sys.argv[-1]])\n",
        encoding="utf-8",
    )
    path.chmod(0o700)
    return path


def _valid_experiment_record(idea_ref: dict[str, str]) -> dict:
    requirements = {
        "research_question": "Does controlled arithmetic produce five?", "hypothesis": None,
        "scientific_inputs": [{"kind": "SOURCE_CODE", "role": "synthetic package", "required": True}],
        "configuration": {"left": 2, "right": 3}, "seeds": [1], "repetitions": 1,
        "metrics": [{"name": "value", "description": "arithmetic result", "unit": None}],
        "runtime": "PYTHON", "limits": {"wall_seconds": 5, "cpu_seconds": 5, "max_output_bytes": 4096},
        "stopping_conditions": ["one process exits"],
    }
    req_sha = canonical_hash(requirements)
    plan = {
        "research_question": requirements["research_question"], "hypothesis": None,
        "requirements_sha256": req_sha, "source_artifacts": [idea_ref],
        "resource": {"resource_id": "resource-" + "9" * 32, "resource_kind": "SOURCE_REPOSITORY", "provider": "GITHUB", "locator": "owner/synthetic", "exact_revision": "9" * 40, "content_checksum": "sha256:" + "1" * 64, "package_manifest_checksum": "sha256:" + "2" * 64, "entrypoint_checksum": "sha256:" + "3" * 64, "lock_checksum": "sha256:" + "4" * 64},
        "entrypoint": "inputs/experiment-package/run.py", "argv": [sys.executable, "inputs/experiment-package/run.py", "memory/execution/config.json"], "working_directory": ".",
        "configuration": requirements["configuration"], "seeds": [1], "repetitions": 1,
        "metrics": requirements["metrics"], "environment": {"python_version": "3.11", "implementation": "CPython", "platform": "controlled", "lock_checksum": "sha256:" + "4" * 64},
        "network_policy": "DISABLED", "limits": requirements["limits"], "stopping_conditions": requirements["stopping_conditions"], "known_limitations": ["Synthetic fixture"],
    }
    plan_sha = canonical_hash(plan)
    approval_payload = {"plan_sha256": plan_sha, "attempt_id": "attempt-" + "8" * 32, "approved_at": "2026-08-15T00:00:00Z", "decision": "APPROVED", "scope": "ONE_ATTEMPT"}
    approval = {"sha256": canonical_hash(approval_payload), **approval_payload}
    evidence = {"relative_path": "memory/execution/stdout.json", "sha256": "sha256:" + "5" * 64, "availability": "AVAILABLE", "limitation": None}
    artifact = {
        "schema": "experiment-record/v2", "core_capability_maturity": "REVIEWED_CORE", "mode": "IDEA_EXPERIMENT", "source_artifacts": [idea_ref],
        "requirements": {"sha256": req_sha, "value": requirements}, "approved_plan": {"sha256": plan_sha, "value": plan}, "approval": approval,
        "execution": {"attempt_id": approval["attempt_id"], "approval_sha256": approval["sha256"], "status": "SUCCEEDED", "started_at": "2026-08-15T00:00:00Z", "completed_at": "2026-08-15T00:00:01Z", "argv": plan["argv"], "working_directory": ".", "environment": plan["environment"], "network_policy": "DISABLED", "limits": plan["limits"], "exit_code": 0, "signal": None, "stdout": evidence, "stderr": {**evidence, "relative_path": "memory/execution/stderr.log"}},
        "evaluation": {"status": "VALID", "metrics": [{"name": "value", "value": 5, "unit": None}], "raw_result": evidence, "summary": "Controlled metric valid."},
        "result_status": "SUCCEEDED", "limitations": ["Controlled synthetic software-path evidence"],
    }
    return validate_experiment_record_v2(artifact)


def _clean_environment() -> dict[str, str]:
    blocked = ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "API_KEY")
    return {key: value for key, value in os.environ.items() if not any(fragment in key.upper() for fragment in blocked)}


def _add_instance(client: httpx.Client, project_id: str, workflow: str, version: str, capsule_id: str, capsule_version: str, revision: int) -> dict:
    response = client.post(f"/projects/{project_id}/workflow-instances", json={"workflow_definition_id": workflow, "workflow_version": version, "capsule_id": capsule_id, "capsule_version": capsule_version, "base_revision": revision})
    _require(response.status_code == 201, response.text)
    return response.json()


def _bind(client: httpx.Client, project_id: str, instance: dict, key: str, artifact: dict) -> None:
    response = client.post(f"/projects/{project_id}/workflow-instances/{instance['workflow_instance_id']}/artifact-dependencies", json={"requirement_key": key, "artifact_id": artifact["artifact_id"], "idempotency_key": str(uuid4())})
    _require(response.status_code == 201, response.text)


def _qualify(root: Path, *, real_codex: bool = False) -> dict[str, str]:
    database = InMemoryDatabase(); uow_factory = lambda: InMemoryUnitOfWork(database)
    app = _qualification_app(root, database)
    with _loopback_server(app) as base_url, httpx.Client(base_url=base_url, timeout=30) as client:
        created = client.post("/projects", json={"name": "W1 controlled synthetic qualification", "research_topic": "Evidence-bound initial drafting", "selected_workflow": "LITERATURE_SEARCH", "workflow_setup": "full-research"})
        _require(created.status_code == 201, created.text)
        project_id = created.json()["project_id"]
        initial = client.get(f"/projects/{project_id}/workflow-instances").json()["items"]
        literature_instance = next(item for item in initial if item["workflow_definition_id"] == "literature-search-local-experimental")
        idea_instance = next(item for item in initial if item["workflow_definition_id"] == "idea-discovery-local-experimental")
        experiment_instance = _add_instance(client, project_id, "reproduction-experiment-local-experimental", "0.4.0", REAL_EXPERIMENT_V0_7_CAPSULE_ID, "0.7.0", 1)
        no_experiment = _add_instance(client, project_id, WORKFLOW_ID, WORKFLOW_VERSION, REAL_WRITING_CAPSULE_ID, CAPSULE_VERSION, 2)
        with_experiment = _add_instance(client, project_id, WORKFLOW_ID, WORKFLOW_VERSION, REAL_WRITING_CAPSULE_ID, CAPSULE_VERSION, 3)
        descriptor = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
        workspace = root / "workspace"
        workspace_cli.bootstrap_workspace(target=workspace, descriptor=descriptor)
        transport = workspace_cli.HTTPWorkspaceSyncTransport(base_url)
        _require(workspace_cli.sync_workspace(workspace_root=workspace, transport=transport).status == "SYNCED", "Workspace sync failed")
        lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
        roots = {item["workflow_instance_id"]: workspace / item["relative_path"] for item in lock["installed_capsules"]}
        library_content = _library(); selected_idea, _ = _selected()
        library_artifact = _seed_upstream(uow_factory=uow_factory, project_id=project_id, instance=literature_instance, root=roots[literature_instance["workflow_instance_id"]], artifact_type="selected-paper-library/v1", content=library_content, character="a")
        idea_artifact = _seed_upstream(uow_factory=uow_factory, project_id=project_id, instance=idea_instance, root=roots[idea_instance["workflow_instance_id"]], artifact_type="selected-research-idea/v1", content=selected_idea, character="b")
        experiment_content = _valid_experiment_record({"artifact_id": idea_artifact["artifact_id"], "artifact_type": "selected-research-idea/v1", "sha256": idea_artifact["content_checksum"]})
        experiment_artifact = _seed_upstream(uow_factory=uow_factory, project_id=project_id, instance=experiment_instance, root=roots[experiment_instance["workflow_instance_id"]], artifact_type="experiment-record/v2", content=experiment_content, character="c")
        workspace_cli.refresh_artifact_index(workspace_root=workspace, transport=transport)
        for writing in (no_experiment, with_experiment):
            _bind(client, project_id, writing, "research_idea", idea_artifact)
            _bind(client, project_id, writing, "literature_library", library_artifact)
        _bind(client, project_id, with_experiment, "experiment_record", experiment_artifact)
        for writing, expected_count in ((no_experiment, 2), (with_experiment, 3)):
            materialized = workspace_cli.materialize_artifacts(workspace_root=workspace, consumer_workflow_instance_id=writing["workflow_instance_id"], transport=transport)
            _require(materialized.materialized_count == expected_count, "exact Writing inputs were not materialized")
        harness = _fake_harness(root)
        if real_codex:
            executable = shutil.which("codex")
            _require(executable is not None, "Codex executable is unavailable")
            harness = _real_codex_wrapper(
                root, Path(executable).resolve(strict=True)
            )
        root_cli = workspace / "reagent_local.py"; environment = _clean_environment()
        artifacts = {}
        journeys = (
            ((no_experiment, False),)
            if real_codex
            else ((no_experiment, False), (with_experiment, True))
        )
        for writing, expected_experiment in journeys:
            try:
                workspace_cli._verify_locked_capsules(workspace, lock, descriptor)
                workspace_cli._scan_capsule_for_credentials(
                    roots[writing["workflow_instance_id"]]
                )
            except workspace_cli.WorkspaceCLIError as error:
                raise RuntimeError(str(error)) from error
            output = _run_public_pty([sys.executable, str(root_cli), "run", str(workspace), "--workflow-instance", writing["workflow_instance_id"], "--api-url", base_url, "--codex-executable", str(harness), "--json"], cwd=workspace, environment=environment, timeout_seconds=900.0 if real_codex else DRIVER_TIMEOUT_SECONDS)
            _require(
                "RUN_COMPLETED" in output,
                f"public Writing run did not complete normally:\n{output}",
            )
            capsule = roots[writing["workflow_instance_id"]]
            reports = list((capsule / "memory/progress/reports").glob("prv2-*.json")); _require(len(reports) == 1, "Writing Progress was not finalized exactly once")
            report = json.loads(reports[0].read_text()); current = json.loads((capsule / "memory/current-artifact.json").read_text())
            artifact = json.loads((capsule / current["relative_path"]).read_text())
            validate_manuscript_draft_v2(artifact, bound_inputs={"research_idea": artifact["source_artifacts"]["research_idea"], "literature_library": artifact["source_artifacts"]["literature_library"], "experiment_record": artifact["source_artifacts"]["experiment_record"]}, literature_library=library_content, experiment_record=experiment_content if expected_experiment else None)
            result_claim = next(item for item in artifact["claims"] if item["claim_type"] == "RESULT")
            _require(result_claim["support_status"] == ("SUPPORTED" if expected_experiment else "UNAVAILABLE"), "result evidence truth boundary failed")
            if not expected_experiment:
                _require("unavailable" in artifact["content_markdown"].lower() and "produced value five" not in artifact["content_markdown"].lower(), "no-Experiment draft fabricated an observed result")
            cloud_artifacts = client.get(f"/projects/{project_id}/artifacts", params={"workflow_instance_id": writing["workflow_instance_id"]}).json()["artifacts"]
            _require(len(cloud_artifacts) == 1 and cloud_artifacts[0]["artifact_type"] == "manuscript-draft/v2" and cloud_artifacts[0]["producer_capsule_id"] == REAL_WRITING_CAPSULE_ID and cloud_artifacts[0]["content_checksum"] == current["checksum"], "Cloud did not promote exact manuscript-draft/v2")
            progress = client.get(f"/projects/{project_id}/workflow-instances/{writing['workflow_instance_id']}/progress").json()
            _require(progress["history_total"] == 1 and progress["projection"]["research_status"] == "COMPLETED" and progress["projection"]["result_count"] == 1, "Cloud Writing Progress is not completed exactly once")
            artifacts["with_experiment" if expected_experiment else "no_experiment"] = current["checksum"]
        return {"project_id": project_id, **artifacts, "capsule_checksum": REAL_WRITING_CAPSULE_CHECKSUM}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-codex", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="reagent-w1-public-qualification-") as temporary:
        root = Path(temporary)
        evidence = _qualify(root, real_codex=args.real_codex)
    _require(not root.exists(), "temporary W1 qualification state was not removed")
    print("W1_PUBLIC_WORKSPACE_QUALIFICATION=PASS")
    print("CONTROLLED_NO_EXPERIMENT=PASS")
    print(
        "CONTROLLED_EXPERIMENT_BACKED=NOT_RUN_IN_REAL_CODEX_MODE"
        if args.real_codex else "CONTROLLED_EXPERIMENT_BACKED=PASS"
    )
    print("MANUSCRIPT_DRAFT_V2=PASS")
    print("PROGRESS_EXACTLY_ONCE=PASS")
    print("CLOUD_PROJECTION=PASS")
    print("TEMPORARY_STATE_REMOVED=PASS")
    print("REAL_CODEX_WRITING=PASS" if args.real_codex else "FAKE_HARNESS=PASS")
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
