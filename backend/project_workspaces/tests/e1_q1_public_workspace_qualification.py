"""One-shot E1-Q1 controlled public Workspace qualification.

This is a synthetic, fake-Harness E5 qualification.  It exercises the public
Workspace root client and the production Real Experiment Capsule; it is not
scientific evidence and does not qualify Real Codex.
"""

from __future__ import annotations

import errno
import json
import os
import pty
import re
import runpy
import select
import subprocess
import sys
import tempfile
import time
from importlib import import_module
from pathlib import Path
from uuid import uuid4

import httpx

from backend.api import ApplicationContainer, create_app
from backend.artifact_references.research_flow_contracts import (
    validate_experiment_record_v2,
)
from backend.artifact_references.tests.test_research_flow_contracts import _selected
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
    REAL_EXPERIMENT_CAPSULE_CHECKSUM,
)
from backend.project_workspaces.tests.test_f1b_full_scaffold_flow import (
    _seed_upstream,
)
from backend.project_workspaces.tests.test_owner_real_research_gate import (
    _loopback_server,
)
from backend.workflow_packages.serialization import canonical_hash, sha256_bytes
from backend.workflow_packages.production_workflows import (
    REAL_EXPERIMENT_V0_7_CAPSULE_CHECKSUM,
    REAL_EXPERIMENT_V0_7_CAPSULE_ID,
    build_real_experiment_v0_6_package,
    build_real_experiment_v0_7_package,
)


REPOSITORY = Path(__file__).resolve().parents[3]
WORKFLOW_ID = "reproduction-experiment-local-experimental"
WORKFLOW_VERSION = "0.4.0"
CAPSULE_VERSION = "0.7.0"
DRIVER_TIMEOUT_SECONDS = 90.0
HISTORICAL_CAPSULE_CHECKSUM = (
    "sha256:c262ef5522f9967641e28cf1b605bdc1"
    "a4f3c44ab7c00ffdfa1e5de6ef7db2c7"
)
HISTORICAL_PACKAGE_CHECKSUM = (
    "sha256:791badabc717040a8e0f061678e9be67d"
    "c67a563327cf1aff64ba53f6afe9824"
)
HISTORICAL_VALIDATOR_CHECKSUM = (
    "sha256:aca9057866cb5b762fb7642205cee625c"
    "47a94d89412f78bbc9b9ca3c919fbf7"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _expect_validation_failure(call, *, contains: str) -> None:
    try:
        call()
    except Exception as error:
        _require(contains in str(error), f"unexpected validation failure: {error}")
        return
    raise RuntimeError(f"validation unexpectedly accepted: {contains}")


def _assert_capsule_compatibility(root: Path) -> None:
    migration = import_module(
        "backend.database.migrations.versions."
        "20260815_0023_real_experiment_capsule_0_7"
    )
    _require(
        migration.down_revision == "20260814_0022"
        and migration.CAPSULE_ID == REAL_EXPERIMENT_V0_7_CAPSULE_ID
        and migration.CAPSULE_VERSION == CAPSULE_VERSION
        and migration.CAPSULE_CHECKSUM
        == REAL_EXPERIMENT_V0_7_CAPSULE_CHECKSUM,
        "Capsule 0.7 migration differs from runtime publication authority",
    )
    build_args = {
        "project_id": "project-" + "a" * 32,
        "project_name": "Controlled",
        "research_topic": "Controlled",
        "package_id": "package-" + "b" * 32,
    }
    historical = build_real_experiment_v0_6_package(
        output_root=root / "capsule-0.6",
        **build_args,
    )
    corrected = build_real_experiment_v0_7_package(
        output_root=root / "capsule-0.7",
        **build_args,
    )
    _require(
        REAL_EXPERIMENT_CAPSULE_CHECKSUM == HISTORICAL_CAPSULE_CHECKSUM
        and historical.package_checksum == HISTORICAL_PACKAGE_CHECKSUM
        and sha256_bytes(
            (historical.package_root / "validate_package.py").read_bytes()
        )
        == HISTORICAL_VALIDATOR_CHECKSUM,
        "historical Capsule 0.6 bytes or identity changed",
    )
    _require(
        REAL_EXPERIMENT_V0_7_CAPSULE_CHECKSUM != HISTORICAL_CAPSULE_CHECKSUM
        and corrected.package_checksum != historical.package_checksum,
        "Capsule 0.7 did not receive a distinct immutable identity",
    )

    selected_idea, _ = _selected()
    idea_path = corrected.package_root / "inputs/selected-research-idea.json"
    _write_json(idea_path, selected_idea)
    validator = runpy.run_path(
        str(corrected.package_root / "validate_package.py")
    )
    validate = validator["validate"]
    _require(validate(corrected.package_root)["valid"] is True, "declared Idea rejected")

    undeclared = corrected.package_root / "inputs/undeclared.json"
    _write_json(undeclared, {})
    _expect_validation_failure(
        lambda: validate(corrected.package_root),
        contains="undeclared Capsule file",
    )
    undeclared.unlink()

    idea_path.unlink()
    idea_path.symlink_to(corrected.package_root / "inputs/project.json")
    _expect_validation_failure(
        lambda: validate(corrected.package_root),
        contains="Capsule dynamic file is unsafe",
    )
    _expect_validation_failure(
        lambda: validator["safe_relative_path"]("inputs/../escape.json"),
        contains="unsafe relative path",
    )


def _run_public_pty(
    command: list[str], *, cwd: Path, environment: dict[str, str]
) -> tuple[str, int]:
    """Capture a public command until both child exit and genuine PTY EOF."""

    master_fd, slave_fd = pty.openpty()
    process: subprocess.Popen[bytes] | None = None
    output = bytearray()
    answered: set[str] = set()
    eof = False
    deadline = time.monotonic() + DRIVER_TIMEOUT_SECONDS
    patterns = (
        re.compile(r"Type `(approve sha256:[0-9a-f]{64} attempt-[0-9a-f]{32})`"),
        re.compile(r"Type `(finalize attempt-[0-9a-f]{32})`"),
    )
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=environment,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
        )
        os.close(slave_fd)
        slave_fd = -1
        os.set_blocking(master_fd, False)

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                process.kill()
                process.wait(timeout=5)
                raise RuntimeError("public Workspace PTY did not resolve before deadline")

            returncode = process.poll()
            if returncode is not None and eof:
                break

            if eof:
                try:
                    process.wait(timeout=min(0.2, remaining))
                except subprocess.TimeoutExpired:
                    pass
                continue

            ready, _, _ = select.select(
                [master_fd], [], [], min(0.2, remaining)
            )
            if not ready:
                continue
            try:
                chunk = os.read(master_fd, 65_536)
            except BlockingIOError:
                continue
            except OSError as error:
                if error.errno == errno.EIO:
                    eof = True
                    continue
                raise
            if chunk == b"":
                eof = True
                continue

            output.extend(chunk)
            captured = output.decode("utf-8", errors="replace")
            for pattern in patterns:
                match = pattern.search(captured)
                if match is not None and match.group(1) not in answered:
                    os.write(master_fd, (match.group(1) + "\n").encode("utf-8"))
                    answered.add(match.group(1))

        returncode = process.wait(timeout=max(0.1, deadline - time.monotonic()))
    finally:
        if slave_fd >= 0:
            os.close(slave_fd)
        os.close(master_fd)

    captured = output.decode("utf-8", errors="replace")
    _require(returncode == 0, f"public Workspace run failed ({returncode}):\n{captured}")
    _require(len(answered) == 2, "public Workspace run missed an owner checkpoint")
    return captured, returncode


def _controlled_package(root: Path) -> Path:
    package = root / "controlled-owner-staged-package"
    package.mkdir()
    _write_json(
        package / ".reagent-experiment.json",
        {
            "schema_version": "reagent.experiment-package/v0.1",
            "entrypoint": "run.py",
            "runtime": "PYTHON",
            "runtime_version": f"{sys.version_info.major}.{sys.version_info.minor}",
            "lock_file": "requirements.lock",
        },
    )
    (package / "requirements.lock").write_text(
        "# controlled synthetic package; no dependencies or installation\n",
        encoding="utf-8",
    )
    (package / "run.py").write_text(
        "import json, os, socket, sys\n"
        "configuration = json.load(open(sys.argv[1], encoding='utf-8'))\n"
        "network_denied = 0\n"
        "try:\n"
        "    socket.create_connection(('127.0.0.1', 9), 0.2)\n"
        "except PermissionError:\n"
        "    network_denied = 1\n"
        "credential_fragments = "
        "('TOKEN', 'SECRET', 'PASSWORD', 'CREDENTIAL', 'API_KEY')\n"
        "credentials_scrubbed = int(not any(any(fragment in key.upper() "
        "for fragment in credential_fragments) for key in os.environ))\n"
        "value = configuration['configuration']['left'] + "
        "configuration['configuration']['right']\n"
        "print(json.dumps({'schema_version':"
        "'reagent.experiment-result/v0.1','metrics':["
        "{'name':'value','value':value,'unit':None},"
        "{'name':'network_denied','value':network_denied,'unit':None},"
        "{'name':'credentials_scrubbed','value':credentials_scrubbed,"
        "'unit':None}]}))\n",
        encoding="utf-8",
    )
    return package


def _fake_harness(root: Path) -> Path:
    executable = root / "controlled-fake-codex"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import hashlib, json, pathlib\n"
        "root = pathlib.Path.cwd()\n"
        "context = json.loads((root/'memory/plan-context.json').read_text())\n"
        "requirements = {"
        "'research_question':'Does the controlled package compute 2 + 3 and "
        "preserve execution boundaries?',"
        "'hypothesis':'The declared value is five.',"
        "'scientific_inputs':[{'kind':'SOURCE_CODE','role':"
        "'controlled owner-staged deterministic package','required':True}],"
        "'configuration':{'left':2,'right':3},'seeds':[11],'repetitions':1,"
        "'metrics':["
        "{'name':'value','description':'deterministic arithmetic result',"
        "'unit':None},"
        "{'name':'network_denied','description':'sandbox denied loopback "
        "network','unit':None},"
        "{'name':'credentials_scrubbed','description':'child environment "
        "contains no credential-like names','unit':None}],"
        "'runtime':'PYTHON','limits':{'wall_seconds':10,'cpu_seconds':10,"
        "'max_output_bytes':8192},"
        "'stopping_conditions':['one foreground process exits']}\n"
        "canonical = lambda value: json.dumps(value, sort_keys=True, "
        "separators=(',', ':'), ensure_ascii=False, allow_nan=False)\n"
        "requirements_sha = 'sha256:' + "
        "hashlib.sha256(canonical(requirements).encode()).hexdigest()\n"
        "plan = {'research_question':requirements['research_question'],"
        "'hypothesis':requirements['hypothesis'],"
        "'requirements_sha256':requirements_sha,"
        "'source_artifacts':context['source_artifacts'],"
        "'resource':context['resource'],'entrypoint':context['entrypoint'],"
        "'argv':context['argv'],'working_directory':context['working_directory'],"
        "'configuration':requirements['configuration'],"
        "'seeds':requirements['seeds'],'repetitions':1,"
        "'metrics':requirements['metrics'],'environment':context['environment'],"
        "'network_policy':context['network_policy'],'limits':requirements['limits'],"
        "'stopping_conditions':requirements['stopping_conditions'],"
        "'known_limitations':['Controlled synthetic software-path evidence; "
        "not a scientific research claim.']}\n"
        "(root/'memory/experiment-requirements.json').write_text("
        "canonical(requirements)+'\\n')\n"
        "(root/'memory/experiment-plan.json').write_text(canonical(plan)+'\\n')\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    return executable


def _clean_environment() -> dict[str, str]:
    fragments = ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "API_KEY")
    return {
        key: value
        for key, value in os.environ.items()
        if not any(fragment in key.upper() for fragment in fragments)
    }


def _qualification_app(*, root: Path, database: InMemoryDatabase):
    proxy_database = InMemoryProxyDatabase()
    fake_adapter = DeterministicFakePaperSearchAdapter()
    proxy_service = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(proxy_database),
        adapter=fake_adapter,
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


def _qualify(root: Path) -> dict[str, str]:
    database = InMemoryDatabase()
    uow_factory = lambda: InMemoryUnitOfWork(database)
    app = _qualification_app(root=root, database=database)
    with _loopback_server(app) as base_url, httpx.Client(
        base_url=base_url, timeout=30
    ) as client:
        created = client.post(
            "/projects",
            json={
                "name": "E1-Q1 controlled synthetic qualification",
                "research_topic": "Harmless deterministic arithmetic",
                "selected_workflow": "LITERATURE_SEARCH",
                "workflow_setup": "full-research",
            },
        )
        _require(created.status_code == 201, created.text)
        project_id = created.json()["project_id"]
        initial = client.get(
            f"/projects/{project_id}/workflow-instances"
        ).json()["items"]
        idea = next(
            item
            for item in initial
            if item["workflow_definition_id"]
            == "idea-discovery-local-experimental"
        )
        real_response = client.post(
            f"/projects/{project_id}/workflow-instances",
            json={
                "workflow_definition_id": WORKFLOW_ID,
                "workflow_version": WORKFLOW_VERSION,
                "capsule_id": REAL_EXPERIMENT_V0_7_CAPSULE_ID,
                "capsule_version": CAPSULE_VERSION,
                "base_revision": 1,
            },
        )
        _require(real_response.status_code == 201, real_response.text)
        experiment = real_response.json()
        _require(
            (
                experiment["workflow_definition_id"],
                experiment["workflow_version"],
                experiment["capsule_version"],
            )
            == (WORKFLOW_ID, WORKFLOW_VERSION, CAPSULE_VERSION),
            "public API selected the wrong Real Experiment version",
        )

        descriptor = client.get(
            f"/projects/{project_id}/workspace-bootstrap"
        ).json()
        workspace = root / "workspace"
        workspace_cli.bootstrap_workspace(target=workspace, descriptor=descriptor)
        transport = workspace_cli.HTTPWorkspaceSyncTransport(base_url)
        synced = workspace_cli.sync_workspace(
            workspace_root=workspace, transport=transport
        )
        _require(synced.status == "SYNCED", "Workspace sync did not complete")
        lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
        roots = {
            item["workflow_instance_id"]: workspace / item["relative_path"]
            for item in lock["installed_capsules"]
        }
        capsule = roots[experiment["workflow_instance_id"]]

        selected_idea, _ = _selected()
        idea_artifact = _seed_upstream(
            uow_factory=uow_factory,
            project_id=project_id,
            instance=idea,
            root=roots[idea["workflow_instance_id"]],
            artifact_type="selected-research-idea/v1",
            content=selected_idea,
            character="e",
        )
        binding = client.post(
            f"/projects/{project_id}/workflow-instances/"
            f"{experiment['workflow_instance_id']}/artifact-dependencies",
            json={
                "requirement_key": "research_idea",
                "artifact_id": idea_artifact["artifact_id"],
                "idempotency_key": str(uuid4()),
            },
        )
        _require(binding.status_code == 201, binding.text)
        workspace_cli.refresh_artifact_index(
            workspace_root=workspace, transport=transport
        )
        materialized = workspace_cli.materialize_artifacts(
            workspace_root=workspace,
            consumer_workflow_instance_id=experiment["workflow_instance_id"],
            transport=transport,
        )
        _require(
            materialized.materialized_count == 1,
            "exact selected Idea was not materialized",
        )

        package = _controlled_package(root)
        package_checksum, _ = workspace_cli._resource_manifest(package)
        resource_response = client.post(
            f"/projects/{project_id}/resources",
            json={
                "resource_kind": "SOURCE_REPOSITORY",
                "provider": "GITHUB",
                "locator": "owner/e1-q1-controlled-synthetic-package",
                "exact_revision": "a" * 40,
                "expected_content_checksum": package_checksum,
                "display_name": "E1-Q1 controlled synthetic package",
                "metadata": {"qualification": "software-path-only"},
            },
        )
        _require(resource_response.status_code == 201, resource_response.text)
        resource = resource_response.json()
        resource_binding = client.post(
            f"/projects/{project_id}/workflow-instances/"
            f"{experiment['workflow_instance_id']}/resource-bindings",
            json={
                "requirement_key": "source_repository",
                "resource_id": resource["resource_id"],
                "idempotency_key": str(uuid4()),
            },
        )
        _require(resource_binding.status_code == 201, resource_binding.text)

        root_cli = workspace / "reagent_local.py"
        environment = _clean_environment()
        staged = subprocess.run(
            [
                sys.executable,
                str(root_cli),
                "resource",
                "stage",
                str(workspace),
                str(package),
                "--workflow-instance",
                experiment["workflow_instance_id"],
                "--api-url",
                base_url,
                "--json",
            ],
            cwd=workspace,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        _require(
            staged.returncode == 0 and "OWNER_STAGED_VERIFIED" in staged.stdout,
            "public Resource staging failed:\n" + staged.stdout + staged.stderr,
        )

        fake_harness = _fake_harness(root)
        output, returncode = _run_public_pty(
            [
                sys.executable,
                str(root_cli),
                "run",
                str(workspace),
                "--workflow-instance",
                experiment["workflow_instance_id"],
                "--api-url",
                base_url,
                "--codex-executable",
                str(fake_harness),
                "--json",
            ],
            cwd=workspace,
            environment=environment,
        )
        _require(returncode == 0 and "RUN_COMPLETED" in output, "public run failed")

        reports = list((capsule / "memory/progress/reports").glob("prv2-*.json"))
        _require(len(reports) == 1, "local Progress was not finalized exactly once")
        report = json.loads(reports[0].read_text())
        _require(
            report["execution_round"] == 1
            and report["status"] == "COMPLETED"
            and report["current_state"] == "COMPLETED",
            "local Progress does not represent one valid completed round",
        )

        current = json.loads((capsule / "memory/current-artifact.json").read_text())
        _require(
            report["output_artifacts"] == [current],
            "Progress does not reference the exact current v2 Artifact",
        )
        artifact_path = capsule / current["relative_path"]
        artifact_bytes = artifact_path.read_bytes()
        _require(
            current["artifact_kind"] == "experiment-record/v2"
            and current["checksum"] == sha256_bytes(artifact_bytes),
            "local v2 Artifact identity or checksum differs",
        )
        artifact = validate_experiment_record_v2(json.loads(artifact_bytes))

        approval = json.loads((capsule / "memory/experiment-approval.json").read_text())
        consumption = json.loads(
            (capsule / "memory/approval-consumption.json").read_text()
        )
        consumption_payload = dict(consumption)
        consumption_sha = consumption_payload.pop("sha256")
        _require(
            approval["decision"] == "APPROVED"
            and approval["scope"] == "ONE_ATTEMPT"
            and approval["plan_sha256"] == artifact["approved_plan"]["sha256"]
            and approval["sha256"] == artifact["execution"]["approval_sha256"]
            and consumption["approval_sha256"] == approval["sha256"]
            and consumption["attempt_id"] == artifact["execution"]["attempt_id"]
            and consumption_sha == canonical_hash(consumption_payload),
            "approval is not exactly bound and consumed once",
        )

        metrics = {
            item["name"]: item["value"]
            for item in artifact["evaluation"]["metrics"]
        }
        _require(
            artifact["execution"]["attempt_id"] == approval["attempt_id"]
            and artifact["execution"]["status"] == "SUCCEEDED"
            and artifact["execution"]["exit_code"] == 0
            and artifact["execution"]["network_policy"] == "DISABLED"
            and artifact["evaluation"]["status"] == "VALID"
            and artifact["result_status"] == "SUCCEEDED"
            and metrics
            == {"value": 5, "network_denied": 1, "credentials_scrubbed": 1},
            "controlled execution or evaluation truth differs",
        )
        _require(
            artifact["source_artifacts"][0]["artifact_id"]
            == idea_artifact["artifact_id"]
            and artifact["approved_plan"]["value"]["resource"]["resource_id"]
            == resource["resource_id"]
            and any("not a scientific" in item for item in artifact["limitations"])
            and any("hostile-code" in item for item in artifact["limitations"]),
            "v2 provenance or limitations are incomplete",
        )
        for evidence in (
            artifact["execution"]["stdout"],
            artifact["execution"]["stderr"],
            artifact["evaluation"]["raw_result"],
        ):
            evidence_path = capsule / evidence["relative_path"]
            _require(
                evidence["availability"] == "AVAILABLE"
                and evidence["sha256"] == sha256_bytes(evidence_path.read_bytes()),
                "execution evidence checksum differs",
            )

        artifacts_response = client.get(
            f"/projects/{project_id}/artifacts",
            params={"workflow_instance_id": experiment["workflow_instance_id"]},
        )
        _require(artifacts_response.status_code == 200, artifacts_response.text)
        artifacts = artifacts_response.json()["artifacts"]
        _require(
            len(artifacts) == 1
            and artifacts[0]["artifact_type"] == "experiment-record/v2"
            and artifacts[0]["producer_capsule_id"]
            == REAL_EXPERIMENT_V0_7_CAPSULE_ID
            and artifacts[0]["producer_capsule_version"] == CAPSULE_VERSION
            and artifacts[0]["producer_workflow_instance_id"]
            == experiment["workflow_instance_id"]
            and artifacts[0]["producer_execution_round"] == 1
            and artifacts[0]["content_checksum"] == current["checksum"],
            "Cloud did not promote exactly the expected v2 Artifact metadata",
        )

        progress_response = client.get(
            f"/projects/{project_id}/workflow-instances/"
            f"{experiment['workflow_instance_id']}/progress"
        )
        _require(progress_response.status_code == 200, progress_response.text)
        progress = progress_response.json()
        _require(
            progress["history_total"] == 1
            and len(progress["history"]) == 1
            and progress["history"][0]["accepted_for_projection"] is True
            and progress["history"][0]["validation_status"] == "ACCEPTED"
            and progress["history"][0]["chain_state"] == "VALID_CHAIN"
            and progress["history"][0]["normalized_record"]["status"]
            == "COMPLETED"
            and progress["projection"]["latest_execution_round"] == 1
            and progress["projection"]["research_status"] == "COMPLETED"
            and progress["projection"]["report_count"] == 1
            and progress["projection"]["result_count"] == 1,
            "Cloud Instance Progress projection is not exactly completed once",
        )

        project_progress_response = client.get(f"/projects/{project_id}/progress")
        _require(
            project_progress_response.status_code == 200,
            project_progress_response.text,
        )
        project_progress = project_progress_response.json()
        projected = next(
            item
            for item in project_progress["instances"]
            if item["workflow_instance_id"] == experiment["workflow_instance_id"]
        )
        _require(
            projected["research_status"] == "COMPLETED"
            and projected["latest_execution_round"] == 1
            and projected["report_count"] == 1
            and projected["result_count"] == 1
            and projected["artifact_metadata"] == progress["projection"]["artifact_metadata"],
            "Project projection does not reflect the completed Experiment",
        )

        acknowledgements = list(
            (
                workspace
                / workspace_cli.PROGRESS_RECEIPTS_ROOT
                / experiment["workflow_instance_id"]
            ).glob("*.json")
        )
        _require(
            len(acknowledgements) == 1,
            "Workspace does not contain exactly one Cloud Progress acknowledgement",
        )
        acknowledgement = json.loads(acknowledgements[0].read_text())
        acknowledgement_payload = dict(acknowledgement)
        acknowledgement_sha = acknowledgement_payload.pop(
            "acknowledgement_checksum"
        )
        _require(
            acknowledgement["report_id"] == report["report_id"]
            and acknowledgement["execution_round"] == 1
            and acknowledgement_sha == canonical_hash(acknowledgement_payload),
            "local Cloud acknowledgement identity differs",
        )

        return {
            "project_id": project_id,
            "workflow_instance_id": experiment["workflow_instance_id"],
            "attempt_id": artifact["execution"]["attempt_id"],
            "plan_sha256": artifact["approved_plan"]["sha256"],
            "artifact_checksum": current["checksum"],
            "report_id": report["report_id"],
            "progress_receipt_id": progress["history"][0]["receipt_id"],
        }


def main() -> None:
    with tempfile.TemporaryDirectory(
        prefix="reagent-e1-q1-public-qualification-"
    ) as temporary:
        temporary_root = Path(temporary)
        _assert_capsule_compatibility(temporary_root)
        evidence = _qualify(temporary_root)
    _require(
        not temporary_root.exists(),
        "temporary controlled qualification state was not removed",
    )
    print("PUBLIC_WORKSPACE_QUALIFICATION=PASS")
    print("WORKFLOW_0_4_CAPSULE_0_7=PASS")
    print("CAPSULE_0_6_IMMUTABLE=PASS")
    print("PLAN_APPROVAL_ONE_ATTEMPT=PASS")
    print("LOCAL_EXECUTION=PASS")
    print("NO_EGRESS_ENFORCEMENT=PASS")
    print("EVALUATION_VALID=PASS")
    print("EXPERIMENT_RECORD_V2=PASS")
    print("PROGRESS_EXACTLY_ONCE=PASS")
    print("CLOUD_PROJECTION=PASS")
    print("TEMPORARY_STATE_REMOVED=PASS")
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
