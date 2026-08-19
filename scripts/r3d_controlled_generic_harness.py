"""Drive the public R3 Generic Harness journey for controlled browser qualification.

The script is intentionally qualification-only.  It creates one disposable Full
Research Project, seeds one exact reviewed Research Idea, drives the copied public
Workspace CLI with a deterministic fake Harness, and verifies the resulting v5
Artifact can be materialized into Initial Writing.  Scientific execution remains
bounded, local, deterministic, and provider-free.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.artifact_references.contracts import (  # noqa: E402
    PAPER_LIBRARY_QUALIFICATION_SCHEMA,
    ArtifactReference,
    ArtifactState,
)
from backend.artifact_references.research_flow_contracts import (  # noqa: E402
    build_selected_research_idea,
)
from backend.artifact_references.service import ArtifactReferenceService  # noqa: E402
from backend.database import (  # noqa: E402
    SQLAlchemyUnitOfWork,
    create_postgres_engine,
    create_session_factory,
)
from backend.database.disposable import require_disposable_database  # noqa: E402
from backend.progress_reports.contracts import (  # noqa: E402
    ACCEPTED_REPORT_MEDIA_TYPE,
    EXPERIMENTAL_DECLARATION,
    OutputArtifactReference,
    PinReference,
    ProgressReportUploadEnvelope,
    ProgressReportV2,
    ProgressStatus,
)
from backend.progress_reports.service import ProgressReportService  # noqa: E402
from backend.research.adapters import LocalFilesystemArtifactStorage  # noqa: E402
from backend.workflow_packages.serialization import (  # noqa: E402
    canonical_hash,
    canonical_json,
    sha256_bytes,
)

HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64
EXPECTED_INITIAL = {
    "literature-search-local-experimental": ("0.5.0", "0.7.0"),
    "idea-discovery-local-experimental": ("0.4.0", "0.5.0"),
    "reproduction-experiment-local-experimental": ("0.8.0", "0.11.0"),
    "writing-local-experimental": ("0.5.0", "0.7.0"),
    "review-local-experimental": ("0.4.0", "0.6.0"),
}


def _request(base_url: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    data = None if payload is None else canonical_json(payload).encode("utf-8")
    request = urllib.request.Request(
        base_url + path,
        data=data,
        method="GET" if payload is None else "POST",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{request.method} {path} failed: {error.code} {detail}") from error


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def _cli_environment() -> dict[str, str]:
    blocked = ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "API_KEY")
    environment = {
        key: value for key, value in os.environ.items()
        if not any(fragment in key.upper() for fragment in blocked)
    }
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = str(REPO_ROOT) + (os.pathsep + existing if existing else "")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def _run_cli(
    cli: Path,
    workspace: Path,
    arguments: list[str],
    *,
    owner_input: str = "",
) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(cli), *arguments, "--json"],
        cwd=workspace,
        env=_cli_environment(),
        input=owner_input,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    values: list[dict[str, Any]] = []
    decoder = json.JSONDecoder()
    for index, character in enumerate(completed.stdout):
        if character != "{":
            continue
        try:
            value, _end = decoder.raw_decode(completed.stdout, index)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            values.append(value)
    if completed.returncode != 0 or not values:
        raise RuntimeError(
            f"public CLI failed ({completed.returncode})\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return values[-1]


def _fake_harness(path: Path) -> None:
    executable = """#!__PYTHON__
from __future__ import annotations
import argparse
import json
import math
import os
import sys
import tempfile
from pathlib import Path

from backend.artifact_references.generic_experiment_v5_contracts import (
    EvidenceKind, EvidenceSourceKind, EvidenceSourceRef, ScientificEvidenceBlock,
)
from backend.workflow_packages.generic_experiment_contracts import (
    EvaluationValidity, NamedChecksum, ScientificEvidenceStatus,
)
from backend.workflow_packages.generic_harness_adapter import GenericHarnessEvaluation
from backend.workflow_packages.generic_harness_contracts import (
    GenericHarnessImplementationSpec, HarnessExecutionUnit, HarnessExpectedOutput,
)
from backend.workflow_packages.serialization import canonical_hash, canonical_json

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f".{{path.name}}.", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write((canonical_json(value) + "\\n").encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)

args = sys.argv[1:]
root = Path.cwd().resolve()
instruction = args[-1]

if "methodology-proposal.json" in instruction:
    write(root / "memory/methodology-proposal.json", {{
        "questions_or_hypotheses": ["Does feature standardization improve deterministic KNN classification accuracy?"],
        "inputs_or_materials": ["The exact selected Research Idea and a bounded embedded Wine-like fixture."],
        "protocol": ["Compare raw-feature and training-fold-standardized KNN under identical deterministic leave-one-out evaluation."],
        "observations_or_outputs": ["Condition accuracy, predictions, and evaluated sample count."],
        "evaluation_criteria": ["Use the paired accuracy delta between standardized and raw-feature KNN."],
        "reproducibility_controls": ["Fixed embedded rows, k=3, deterministic Euclidean distance, and stable tie-breaking."],
        "resource_constraints": ["Use only local embedded controlled data and the exact materialized Research Idea."],
        "compute_constraints": ["Two bounded execution units, thirty seconds each, and no network."],
        "network_policy": "DISABLED",
        "assumptions": ["The embedded controlled rows exercise orchestration rather than support a real-world Wine claim."],
        "claim_boundaries": ["Only the deterministic controlled comparison may be reported."],
        "unresolved_material_decisions": [],
    }})
elif "implementation-specification.json" in instruction:
    managed = next((root / ".reagent/experiments").iterdir())
    methodology_path = next(root.glob("capsules/**/memory/methodology.json"))
    methodology = json.loads(methodology_path.read_text(encoding="utf-8"))
    implementation = managed / "implementation"
    implementation.mkdir(parents=True, exist_ok=True)
    run_source = '''from __future__ import annotations
import argparse, json, math
from pathlib import Path

ROWS = [
 ([13.2, 2.7, 2.5], 0), ([13.4, 2.5, 2.4], 0), ([12.9, 2.8, 2.3], 0),
 ([11.8, 1.9, 2.0], 1), ([12.0, 2.0, 1.9], 1), ([11.6, 1.8, 2.1], 1),
 ([13.0, 3.1, 2.8], 2), ([12.7, 3.0, 2.9], 2), ([13.1, 3.2, 2.7], 2),
]

def predict(train, point, standardized):
    vectors = [row for row, _ in train]
    if standardized:
        means = [sum(row[j] for row in vectors) / len(vectors) for j in range(3)]
        scales = [math.sqrt(sum((row[j]-means[j])**2 for row in vectors) / len(vectors)) or 1.0 for j in range(3)]
        vectors = [[(row[j]-means[j])/scales[j] for j in range(3)] for row in vectors]
        point = [(point[j]-means[j])/scales[j] for j in range(3)]
    distances = sorted((sum((row[j]-point[j])**2 for j in range(3)), label, index)
                       for index, (row, label) in enumerate(zip(vectors, [label for _, label in train])))
    votes = {}
    for _, label, _ in distances[:3]: votes[label] = votes.get(label, 0) + 1
    return min(votes, key=lambda label: (-votes[label], label))

parser = argparse.ArgumentParser()
parser.add_argument("--condition", choices=("raw", "standardized"), required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--interrupt-once", action="store_true")
args = parser.parse_args()
if args.interrupt_once:
    marker = Path(".controlled-interruption-recorded")
    if not marker.exists():
        marker.write_text("durable controlled interruption\\\\n", encoding="utf-8")
        raise SystemExit(75)
predictions = []
for index, (point, label) in enumerate(ROWS):
    train = [item for candidate, item in enumerate(ROWS) if candidate != index]
    predictions.append({"index": index, "truth": label,
                        "prediction": predict(train, point, args.condition == "standardized")})
accuracy = sum(item["truth"] == item["prediction"] for item in predictions) / len(predictions)
Path(args.output).write_text(json.dumps({"condition": args.condition, "accuracy": accuracy,
                                        "sample_count": len(ROWS), "predictions": predictions},
                                       sort_keys=True, separators=(",", ":")) + "\\\\n", encoding="utf-8")
'''
    (implementation / "run.py").write_text(run_source, encoding="utf-8")
    spec = GenericHarnessImplementationSpec(
        methodology["research_objective"]["objective_ref_checksum"],
        methodology["methodology_checksum"], "run.py", "PYTHON", ">=3.10,<4", (),
        ("PYTHON_SCRIPT",),
        (HarnessExpectedOutput("raw-result", "raw.json", "application/json"),
         HarnessExpectedOutput("standardized-result", "standardized.json", "application/json")),
        (HarnessExecutionUnit("unit-raw", ("--condition", "raw", "--output", "raw.json"),
                              ("raw-result",), "Evaluate raw-feature KNN."),
         HarnessExecutionUnit("unit-standardized", ("--condition", "standardized", "--output", "standardized.json", "--interrupt-once"),
                              ("standardized-result",), "Evaluate standardized-feature KNN after one controlled interruption.")),
        (("python", "-m", "py_compile", "run.py"),),
        (("wall_time_seconds", "30"), ("max_output_bytes", "1048576")),
        "DISABLED", ("Implement a bounded deterministic KNN baseline-versus-standardization comparison.",),
    )
    write(managed / "contracts/implementation-specification.json", spec)
elif "evaluation/evaluation.json" in instruction:
    managed = next((root / ".reagent/experiments").iterdir())
    spec = json.loads((managed / "contracts/implementation-specification.json").read_text(encoding="utf-8"))
    supplied = json.loads((managed / "execution/supplied-execution.json").read_text(encoding="utf-8"))
    results = {{item["name"]: json.loads((managed / item["relative_path"]).read_text(encoding="utf-8"))
               for item in supplied["outputs"]}}
    payload = {{
        "raw_accuracy": results["raw-result"]["accuracy"],
        "standardized_accuracy": results["standardized-result"]["accuracy"],
        "accuracy_delta": results["standardized-result"]["accuracy"] - results["raw-result"]["accuracy"],
        "sample_count": results["raw-result"]["sample_count"],
    }}
    identities = tuple(NamedChecksum(item["name"], item["checksum"])
                       for item in supplied["evidence"]["outputs"])
    evaluation = GenericHarnessEvaluation(
        spec["specification_checksum"], supplied["evidence"]["execution_plan_checksum"],
        identities, payload, EvaluationValidity.VALID,
        ScientificEvidenceStatus.SUPPORTS_BOUNDED_FINDINGS,
        ("Controlled embedded data cannot establish a real Wine-dataset claim.",),
        "2026-08-20T18:00:00Z", True,
    )
    source = (EvidenceSourceRef(EvidenceSourceKind.RESULT_PAYLOAD, "result-payload", canonical_hash(payload)),)
    blocks = (
        ScientificEvidenceBlock("evidence-raw-accuracy", EvidenceKind.SCALAR, "Raw-feature accuracy", payload["raw_accuracy"], source),
        ScientificEvidenceBlock("evidence-standardized-accuracy", EvidenceKind.SCALAR, "Standardized-feature accuracy", payload["standardized_accuracy"], source),
        ScientificEvidenceBlock("evidence-accuracy-delta", EvidenceKind.SCALAR, "Accuracy delta", payload["accuracy_delta"], source),
    )
    write(managed / "evaluation/evaluation.json", evaluation)
    write(managed / "evaluation/evidence-blocks.json", [item.to_dict() for item in blocks])
else:
    raise SystemExit("unexpected controlled Harness instruction")
"""
    executable = executable.replace("__PYTHON__", sys.executable).replace("{{", "{").replace("}}", "}")
    path.write_text(executable, encoding="utf-8")
    path.chmod(0o700)


def _progress_service(
    *,
    engine: Any,
    storage_root: Path,
    project_id: str,
    instances: dict[str, dict[str, Any]],
) -> tuple[SQLAlchemyUnitOfWork, ProgressReportService]:
    uow = SQLAlchemyUnitOfWork(create_session_factory(engine))
    by_id = {item["workflow_instance_id"]: item for item in instances.values()}

    def resolve(envelope: Any, normalized: Any, requested: str | None) -> str:
        item = by_id.get(requested or "")
        if item is None or envelope.project_id != project_id:
            raise ValueError("R3D Progress is outside the controlled Project")
        if normalized is not None and (
            normalized.workflow_id != item["workflow_definition_id"]
            or normalized.workflow_version != item["workflow_version"]
        ):
            raise ValueError("R3D Progress Workflow identity mismatch")
        return item["workflow_instance_id"]

    service = ProgressReportService(
        repository=uow.progress_reports,
        content_storage=LocalFilesystemArtifactStorage(storage_root),
        commit_callback=uow.commit,
        workflow_identity_resolver=resolve,
        clock=lambda: datetime(2026, 8, 20, 17, tzinfo=UTC),
    )
    return uow, service


def _seed_artifact(
    *,
    uow: SQLAlchemyUnitOfWork,
    service: ProgressReportService,
    base_url: str,
    run_id: str,
    project_id: str,
    instance: dict[str, Any],
    artifact_id: str,
    artifact_type: str,
    content: dict[str, Any],
    timestamp: str,
) -> dict[str, Any]:
    content_bytes = canonical_json(content).encode("utf-8")
    checksum = sha256_bytes(content_bytes)
    slug = artifact_type.split("/", 1)[0]
    relative_path = f"outputs/artifacts/{slug}/sha256-{checksum[7:]}.json"
    definition = _request(base_url, f"/workflow-definitions/{instance['workflow_definition_id']}")
    workflow_checksum = next(
        item["contract_checksum"] for item in definition["versions"]
        if item["version"] == instance["workflow_version"]
    )
    package_id = f"r3d-{run_id[:12]}-{instance['workflow_instance_id']}"
    package_checksum = canonical_hash({"package_id": package_id, "run_id": run_id})
    output = OutputArtifactReference(
        relative_path=relative_path,
        artifact_kind=artifact_type,
        media_type="application/json",
        checksum=checksum,
        size=len(content_bytes),
    )
    report = ProgressReportV2.create(
        package_id=package_id,
        package_schema_version="workflow-package/v0.1",
        package_checksum=package_checksum,
        project_id=project_id,
        workflow_id=instance["workflow_definition_id"],
        workflow_version=instance["workflow_version"],
        workflow_checksum=workflow_checksum,
        execution_round=1,
        harness_type="r3d-controlled-fixture",
        harness_version="0.1.0",
        harness_session_id=f"r3d-{instance['workflow_instance_id']}",
        previous_report_id=None,
        previous_report_checksum=None,
        started_at=timestamp,
        completed_at=timestamp,
        status=ProgressStatus.COMPLETED,
        completed_work=(f"Controlled {artifact_type} fixture completed.",),
        current_state=(
            "Standardization Effect on KNN Performance for a controlled Wine-like dataset"
            if artifact_type == "selected-research-idea/v1"
            else "One exact controlled paper was selected."
        ),
        next_recommended_action="Use only through an exact downstream binding.",
        continuation_reason=None,
        output_artifacts=(output,),
        context_before_checksum=HASH_A,
        context_after_checksum=HASH_B,
        warnings=(),
        errors=(),
        unresolved_questions=(),
        continuation_instructions=("Continue through the controlled R3D qualification.",),
        skill_pins=(PinReference("SKILL", "r3d-controlled-skill", "0.1.0", HASH_A),),
        template_pins=(PinReference("TEMPLATE", "r3d-controlled-template", "0.1.0", HASH_B),),
        generated_at=timestamp,
        experimental_declaration=EXPERIMENTAL_DECLARATION,
    )
    report_bytes = (canonical_json(report) + "\n").encode("utf-8")
    envelope = ProgressReportUploadEnvelope.create(
        original_report_bytes=report_bytes,
        project_id=project_id,
        package_id=package_id,
        package_checksum=package_checksum,
        report_schema_version=report.schema_version,
        report_id=report.report_id,
        report_checksum=report.report_checksum,
        original_report_media_type=ACCEPTED_REPORT_MEDIA_TYPE,
        uploaded_at=timestamp,
        uploader_type="r3d-controlled-fixture",
        client_version="r3d-controlled-fixture/0.1.0",
        source_path_hint=f"memory/progress/reports/{report.report_id}.json",
        context_snapshot_metadata=None,
    )
    receipt = service.upload(envelope, workflow_instance_id=instance["workflow_instance_id"])
    if not receipt.accepted_for_projection:
        raise RuntimeError("R3D Progress was not accepted for projection")
    produced_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    artifact = ArtifactReference(
        artifact_id=artifact_id,
        project_id=project_id,
        producer_workflow_instance_id=instance["workflow_instance_id"],
        producer_progress_receipt_id=receipt.receipt_id,
        producer_progress_report_id=report.report_id,
        producer_execution_round=1,
        producer_capsule_id=instance["capsule_id"],
        producer_capsule_version=instance["capsule_version"],
        artifact_type=artifact_type,
        artifact_schema_version=artifact_type,
        media_type="application/json",
        state=ArtifactState.LOCAL_AVAILABLE,
        relative_path=relative_path,
        content_checksum=checksum,
        size_bytes=len(content_bytes),
        cloud_metadata_available=True,
        produced_at=produced_at,
        retired_at=None,
        created_at=produced_at,
        updated_at=produced_at,
    )
    uow.artifact_references.add_artifact(artifact)
    uow.commit()
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "content_checksum": checksum,
        "relative_path": relative_path,
        "content": content,
        "content_bytes": content_bytes,
    }


def _bind(
    base_url: str,
    run_uuid: UUID,
    project_id: str,
    consumer_id: str,
    role: str,
    artifact_id: str,
) -> dict[str, Any]:
    return _request(
        base_url,
        f"/projects/{project_id}/workflow-instances/{consumer_id}/artifact-dependencies",
        {
            "requirement_key": role,
            "artifact_id": artifact_id,
            "idempotency_key": str(uuid5(run_uuid, f"{consumer_id}:{role}:{artifact_id}")),
        },
    )


def _prepare(arguments: argparse.Namespace) -> None:
    root = arguments.root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    workspace = root / "workspace"
    descriptor_path = root / "workspace-bootstrap.json"
    fake_harness = root / "controlled-codex"
    run_uuid = UUID(arguments.run_id)
    project = _request(arguments.api_url, "/projects", {
        "name": "R3D controlled Generic Harness journey",
        "research_topic": "Controlled KNN feature-standardization orchestration",
        "selected_workflow": "LITERATURE_SEARCH",
        "workflow_setup": "full-research",
    })
    project_id = project["project_id"]
    page = _request(arguments.api_url, f"/projects/{project_id}/workflow-instances")
    instances = {item["workflow_definition_id"]: item for item in page["items"]}
    if page["total"] != 5 or set(instances) != set(EXPECTED_INITIAL):
        raise RuntimeError("R3D Full Research did not create exactly five initial Workflows")
    actual_pins = {
        key: (item["workflow_version"], item["capsule_version"])
        for key, item in instances.items()
    }
    if actual_pins != EXPECTED_INITIAL:
        raise RuntimeError(f"R3D forward pins drifted: {actual_pins}")
    descriptor = _request(arguments.api_url, f"/projects/{project_id}/workspace-bootstrap")
    _write(descriptor_path, descriptor)
    bootstrap = _run_cli(
        REPO_ROOT / "reagent_local.py", REPO_ROOT,
        ["bootstrap", str(workspace), "--descriptor", str(descriptor_path)],
    )
    if bootstrap.get("status") != "CREATED":
        raise RuntimeError(f"R3D Workspace bootstrap failed: {bootstrap}")
    root_cli = workspace / "reagent_local.py"
    synced = _run_cli(root_cli, workspace, ["sync", ".", "--api-url", arguments.api_url])
    if synced.get("status") != "SYNCED":
        raise RuntimeError(f"R3D first sync was not SYNCED: {synced}")
    lock = json.loads((workspace / ".reagent/installed-lock.json").read_text(encoding="utf-8"))
    installed = {item["workflow_instance_id"]: item for item in lock["installed_capsules"]}

    database_url = os.environ["REAGENT_DATABASE_URL"]
    engine = create_postgres_engine(database_url)
    require_disposable_database(
        engine,
        database_url=database_url,
        expected_identity=os.environ["REAGENT_TEST_DATABASE_IDENTITY"],
    )
    uow, progress_service = _progress_service(
        engine=engine,
        storage_root=root / "progress-originals",
        project_id=project_id,
        instances=instances,
    )
    literature_id = "artifact-" + uuid5(run_uuid, "r3d-literature").hex
    literature = {
        "schema": "selected-paper-library/v1",
        "source_schemas": {
            "candidate_papers": "candidate-papers/v0.2",
            "selected_papers": "selected-papers/v0.2",
        },
        "source_checksums": {
            "candidate_papers_sha256": HASH_A,
            "selected_papers_sha256": HASH_B,
        },
        "papers": [{
            "candidate_id": "candidate-" + "c" * 16,
            "paper": {"candidate_id": "candidate-" + "c" * 16},
            "selection": {"candidate_id": "candidate-" + "c" * 16},
        }],
    }
    literature_artifact = _seed_artifact(
        uow=uow, service=progress_service, base_url=arguments.api_url,
        run_id=arguments.run_id, project_id=project_id,
        instance=instances["literature-search-local-experimental"],
        artifact_id=literature_id, artifact_type="selected-paper-library/v1",
        content=literature, timestamp="2026-08-20T17:01:00Z",
    )
    qualification_payload = {
        "schema": PAPER_LIBRARY_QUALIFICATION_SCHEMA,
        "artifact_id": literature_id,
        "artifact_checksum": literature_artifact["content_checksum"],
        "selected_count": 1,
    }
    ArtifactReferenceService(
        unit_of_work=uow,
        clock=lambda: datetime(2026, 8, 20, 17, 1, tzinfo=UTC),
    ).report_content_qualification(
        project_id=project_id,
        artifact_id=literature_id,
        payload={
            **qualification_payload,
            "qualification_checksum": canonical_hash(qualification_payload),
        },
    )
    idea_id = "artifact-" + uuid5(run_uuid, "r3d-idea").hex
    selected_idea = {
        "idea_id": "idea-001",
        "title": "Standardization Effect on KNN Performance",
        "research_question": "Does training-fold feature standardization improve deterministic KNN accuracy?",
        "motivation": "Distance-based classification is sensitive to feature scale.",
        "literature_basis": ["candidate-" + "c" * 16],
        "observed_gap": "The bounded source does not establish the controlled paired result.",
        "proposed_direction": "Compare raw and standardized KNN under identical evaluation folds.",
        "assumptions": ["The controlled embedded rows are suitable only for orchestration qualification."],
        "risks": ["The fixture cannot support a real Wine-dataset scientific claim."],
        "validation_needed": ["Validate exact implementation, execution evidence, and bounded claims."],
        "status": "selected",
    }
    candidate_ideas = {
        "schema": "candidate-ideas/v0.1",
        "source_artifact": {
            "artifact_id": literature_id,
            "artifact_type": "selected-paper-library/v1",
            "sha256": literature_artifact["content_checksum"],
        },
        "ideas": [selected_idea],
    }
    candidate_bytes = (canonical_json(candidate_ideas) + "\n").encode("utf-8")
    idea = build_selected_research_idea(
        candidate_ideas=candidate_ideas,
        candidate_ideas_bytes=candidate_bytes,
        literature_library=literature,
        literature_artifact_id=literature_id,
        literature_checksum=literature_artifact["content_checksum"],
    )
    idea_artifact = _seed_artifact(
        uow=uow, service=progress_service, base_url=arguments.api_url,
        run_id=arguments.run_id, project_id=project_id,
        instance=instances["idea-discovery-local-experimental"],
        artifact_id=idea_id, artifact_type="selected-research-idea/v1",
        content=idea, timestamp="2026-08-20T17:02:00Z",
    )
    uow.close()
    engine.dispose()

    for artifact, producer in (
        (literature_artifact, instances["literature-search-local-experimental"]),
        (idea_artifact, instances["idea-discovery-local-experimental"]),
    ):
        producer_root = workspace / installed[producer["workflow_instance_id"]]["relative_path"]
        target = producer_root / artifact["relative_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(artifact["content_bytes"])

    _bind(
        arguments.api_url, run_uuid, project_id,
        instances["idea-discovery-local-experimental"]["workflow_instance_id"],
        "paper_library", literature_id,
    )
    experiment = instances["reproduction-experiment-local-experimental"]
    _bind(
        arguments.api_url, run_uuid, project_id,
        experiment["workflow_instance_id"], "research_idea", idea_id,
    )
    _fake_harness(fake_harness)
    prepared = _run_cli(
        root_cli, workspace,
        ["run", ".", "--workflow-instance", experiment["workflow_instance_id"],
         "--api-url", arguments.api_url, "--codex-executable", str(fake_harness)],
        owner_input="approve\n",
    )
    if prepared.get("status") != "RUN_APPROVAL_REQUIRED":
        raise RuntimeError(f"R3D did not reach exact run approval: {prepared}")
    managed = workspace / ".reagent/experiments" / experiment["workflow_instance_id"]
    approval = json.loads((managed / "contracts/methodology-approval.json").read_text())
    specification = json.loads((managed / "contracts/implementation-specification.json").read_text())
    if not approval.get("approval_checksum") or specification.get("dependencies") != []:
        raise RuntimeError("R3D natural methodology approval or no-install specification drifted")
    _write(arguments.manifest, {
        "schema_version": "reagent.r3d-controlled-journey/v0.1",
        "run_id": arguments.run_id,
        "project_id": project_id,
        "project_name": project["name"],
        "workspace": str(workspace),
        "root_cli": str(root_cli),
        "fake_harness": str(fake_harness),
        "instances": {
            key: value["workflow_instance_id"] for key, value in instances.items()
        },
        "literature": {
            "artifact_id": literature_id,
            "checksum": literature_artifact["content_checksum"],
        },
        "idea": {"artifact_id": idea_id, "checksum": idea_artifact["content_checksum"]},
        "methodology_approval_checksum": approval["approval_checksum"],
        "implementation_specification_checksum": specification["specification_checksum"],
    })


def _finish(arguments: argparse.Namespace) -> None:
    manifest = json.loads(arguments.manifest.read_text(encoding="utf-8"))
    workspace = Path(manifest["workspace"])
    root_cli = Path(manifest["root_cli"])
    fake_harness = Path(manifest["fake_harness"])
    experiment_id = manifest["instances"]["reproduction-experiment-local-experimental"]
    command = [
        "run", ".", "--workflow-instance", experiment_id,
        "--api-url", arguments.api_url, "--codex-executable", str(fake_harness),
    ]
    interrupted = _run_cli(root_cli, workspace, command)
    if interrupted.get("status") != "EXECUTION_INTERRUPTED":
        raise RuntimeError(f"R3D controlled interruption was not surfaced safely: {interrupted}")
    managed = workspace / ".reagent/experiments" / experiment_id
    execution_before = json.loads((managed / "execution/manifest.json").read_text())
    units_before = {item["unit_id"]: item for item in execution_before["units"]}
    if (
        units_before["unit-raw"]["status"] != "COMPLETED"
        or units_before["unit-standardized"]["status"] != "PENDING"
    ):
        raise RuntimeError("R3D execution-unit durability did not preserve the completed unit")
    raw_checksum = units_before["unit-raw"]["output_checksums"][0][1]
    completed = _run_cli(root_cli, workspace, command, owner_input="approve\n")
    if completed.get("status") != "PROGRESS_SYNCHRONIZED":
        raise RuntimeError(f"R3D Generic Harness did not finalize exactly: {completed}")
    execution_after = json.loads((managed / "execution/manifest.json").read_text())
    units_after = {item["unit_id"]: item for item in execution_after["units"]}
    if (
        any(item["status"] != "COMPLETED" for item in units_after.values())
        or units_after["unit-raw"]["output_checksums"][0][1] != raw_checksum
        or units_after["unit-raw"]["attempt_count"] != 1
    ):
        raise RuntimeError("R3D resume did not reuse the exact completed execution unit")

    project_id = manifest["project_id"]
    artifact_page = _request(
        arguments.api_url,
        f"/projects/{project_id}/artifacts?workflow_instance_id={experiment_id}",
    )
    experiments = [
        item for item in artifact_page["artifacts"]
        if item["artifact_type"] == "experiment-record/v5"
    ]
    if len(experiments) != 1:
        raise RuntimeError("R3D did not publish exactly one experiment-record/v5")
    experiment = experiments[0]
    experiment_root = next(
        item for item in json.loads((workspace / ".reagent/installed-lock.json").read_text())["installed_capsules"]
        if item["workflow_instance_id"] == experiment_id
    )
    artifact_path = workspace / experiment_root["relative_path"] / experiment["relative_path"]
    artifact_bytes = artifact_path.read_bytes()
    if sha256_bytes(artifact_bytes) != experiment["content_checksum"]:
        raise RuntimeError("R3D local v5 bytes differ from the exact Cloud Artifact")
    record = json.loads(artifact_bytes)
    capability = record["lifecycle_record"]["capability"]
    if (
        record.get("schema") != "experiment-record/v5"
        or capability.get("review_status") == "REVIEWED"
        or "generic" not in canonical_json(capability).lower()
    ):
        raise RuntimeError("R3D v5 provenance falsely claims an incompatible reviewed Capability")
    progress = _request(
        arguments.api_url,
        f"/projects/{project_id}/workflow-instances/{experiment_id}/progress",
    )
    if (
        progress["history_total"] != 1
        or progress["projection"]["research_status"] != "COMPLETED"
        or progress["projection"]["result_count"] != 1
    ):
        raise RuntimeError("R3D Cloud Progress is not completed exactly once")

    run_uuid = UUID(manifest["run_id"])
    writing_id = manifest["instances"]["writing-local-experimental"]
    for role, artifact_id in (
        ("literature_library", manifest["literature"]["artifact_id"]),
        ("research_idea", manifest["idea"]["artifact_id"]),
        ("experiment_record", experiment["artifact_id"]),
    ):
        _bind(arguments.api_url, run_uuid, project_id, writing_id, role, artifact_id)
    materialized = _run_cli(
        root_cli, workspace,
        ["artifact", "materialize", ".", "--workflow-instance", writing_id,
         "--api-url", arguments.api_url],
    )
    if materialized.get("materialized_count") != 3:
        raise RuntimeError(f"R3D Writing did not consume three exact inputs: {materialized}")
    plan = json.loads((workspace / ".reagent/materialization-plans" / f"{writing_id}.json").read_text())
    experiment_input = next(
        item for item in plan["artifacts"] if item["requirement_key"] == "experiment_record"
    )
    if (
        experiment_input["artifact_id"] != experiment["artifact_id"]
        or experiment_input["expected_checksum"] != experiment["content_checksum"]
    ):
        raise RuntimeError("R3D Writing did not materialize the exact Generic Harness v5")
    replay = _run_cli(root_cli, workspace, command)
    if replay.get("status") != "PROGRESS_SYNCHRONIZED":
        raise RuntimeError(f"R3D terminal replay was not idempotent: {replay}")
    replay_artifacts = _request(
        arguments.api_url,
        f"/projects/{project_id}/artifacts?workflow_instance_id={experiment_id}",
    )
    if len([item for item in replay_artifacts["artifacts"] if item["artifact_type"] == "experiment-record/v5"]) != 1:
        raise RuntimeError("R3D terminal replay duplicated the v5 Artifact")
    manifest.update({
        "experiment": {
            "artifact_id": experiment["artifact_id"],
            "checksum": experiment["content_checksum"],
            "presentation_schema": (
                experiment.get("presentation") or {}
            ).get("schema_identity"),
        },
        "interruption_status": interrupted["status"],
        "completion_status": completed["status"],
        "writing_materialized_count": materialized["materialized_count"],
        "completed_unit_reused_checksum": raw_checksum,
    })
    _write(arguments.manifest, manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "finish"))
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    arguments = parser.parse_args()
    database_url = os.environ.get("REAGENT_DATABASE_URL")
    identity = os.environ.get("REAGENT_TEST_DATABASE_IDENTITY")
    if not database_url or not identity or os.environ.get("REAGENT_AUTOMATED_QUALIFICATION") != "1":
        raise RuntimeError("R3D requires the isolated disposable qualification harness")
    if arguments.phase == "prepare":
        _prepare(arguments)
    else:
        _finish(arguments)
    print(f"R3D_{arguments.phase.upper()}=PASS")


if __name__ == "__main__":
    main()
