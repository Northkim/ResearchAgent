"""Seed disposable Experiment 0.6 states for GEN-D-C1 controlled E6."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid5

from backend.artifact_references.contracts import ArtifactReference, ArtifactState
from backend.artifact_references.generic_experiment_contracts import (
    GenericExperimentPresentation,
    PresentationBlock,
    PresentationKind,
)
from backend.controlled_local_run_approvals import (
    ControlledLocalRunApproval,
    ControlledLocalRunSummary,
)
from backend.database import (
    SQLAlchemyUnitOfWork,
    create_postgres_engine,
    create_session_factory,
)
from backend.progress_reports.contracts import (
    ACCEPTED_REPORT_MEDIA_TYPE,
    EXPERIMENTAL_DECLARATION,
    OutputArtifactReference,
    PinReference,
    ProgressReportUploadEnvelope,
    ProgressReportV2,
    ProgressStatus,
)
from backend.progress_reports.service import ProgressReportService
from backend.research.adapters import LocalFilesystemArtifactStorage
from backend.workflow_packages.serialization import canonical_hash, canonical_json, to_json_value

HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64
EXPERIMENT = "reproduction-experiment-local-experimental"
IDEA = "idea-discovery-local-experimental"


def _request(base_url: str, path: str, payload: dict | None = None, *, method: str | None = None) -> dict:
    data = None if payload is None else canonical_json(payload).encode("utf-8")
    request = urllib.request.Request(
        base_url + path,
        data=data,
        method=method or ("GET" if payload is None else "POST"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def _upload(
    service: ProgressReportService,
    run_id: str,
    project_id: str,
    instance: dict,
    workflow_checksum: str,
    status: ProgressStatus,
    summary: str,
    timestamp: datetime,
    outputs: tuple[OutputArtifactReference, ...] = (),
):
    package_id = f"c1-{run_id[:8]}-{instance['workflow_instance_id'][4:16]}"
    package_checksum = canonical_hash({"package": package_id, "controlled": True})
    report = ProgressReportV2.create(
        package_id=package_id,
        package_schema_version="workflow-package/v0.1",
        package_checksum=package_checksum,
        project_id=project_id,
        workflow_id=instance["workflow_definition_id"],
        workflow_version=instance["workflow_version"],
        workflow_checksum=workflow_checksum,
        execution_round=1,
        harness_type="gen-d-c1-controlled-fixture",
        harness_version="0.1.0",
        harness_session_id=f"c1-{instance['workflow_instance_id'][4:20]}",
        previous_report_id=None,
        previous_report_checksum=None,
        started_at=timestamp.isoformat().replace("+00:00", "Z"),
        completed_at=timestamp.isoformat().replace("+00:00", "Z"),
        status=status,
        completed_work=(summary,),
        current_state=summary,
        next_recommended_action="Continue from this exact durable checkpoint.",
        continuation_reason=None,
        output_artifacts=outputs,
        context_before_checksum=HASH_A,
        context_after_checksum=HASH_B,
        warnings=(),
        errors=(),
        unresolved_questions=(() if status is ProgressStatus.COMPLETED else ("Owner attention is required.",)),
        continuation_instructions=("Use only this disposable controlled fixture.",),
        skill_pins=(PinReference("SKILL", "c1-controlled-skill", "0.1.0", HASH_A),),
        template_pins=(PinReference("TEMPLATE", "c1-controlled-template", "0.1.0", HASH_B),),
        generated_at=timestamp.isoformat().replace("+00:00", "Z"),
        experimental_declaration=EXPERIMENTAL_DECLARATION,
    )
    body = (canonical_json(report) + "\n").encode("utf-8")
    envelope = ProgressReportUploadEnvelope.create(
        original_report_bytes=body,
        project_id=project_id,
        package_id=package_id,
        package_checksum=package_checksum,
        report_schema_version=report.schema_version,
        report_id=report.report_id,
        report_checksum=report.report_checksum,
        original_report_media_type=ACCEPTED_REPORT_MEDIA_TYPE,
        uploaded_at=timestamp.isoformat().replace("+00:00", "Z"),
        uploader_type="gen-d-c1-controlled-fixture",
        client_version="gen-d-c1-controlled-fixture/0.1.0",
        source_path_hint=f"memory/progress/{report.report_id}.json",
        context_snapshot_metadata=None,
    )
    receipt = service.upload(envelope, workflow_instance_id=instance["workflow_instance_id"])
    if not receipt.accepted_for_projection:
        raise RuntimeError("GEN-D-C1 fixture Progress was not accepted")
    return receipt, report


def _presentation(artifact_id: str, artifact_checksum: str, shape: str) -> dict:
    common = (
        PresentationBlock(PresentationKind.PROSE, "Research objective", "Observe whether a bounded state transition preserves category order."),
        PresentationBlock(PresentationKind.SCALAR, "Process outcome", "COMPLETED"),
        PresentationBlock(PresentationKind.SCALAR, "Evaluation validity", "VALID"),
        PresentationBlock(PresentationKind.SCALAR, "Scientific evidence status", "INSUFFICIENT" if shape == "non_ml" else "SUFFICIENT"),
    )
    if shape == "sklearn":
        blocks = common + (
            PresentationBlock(PresentationKind.SCALAR, "Held-out score", 91),
            PresentationBlock(PresentationKind.TABLE, "Configuration comparison", {"columns": ["Configuration", "Score"], "rows": [["A", 87], ["B", 91]]}),
            PresentationBlock(PresentationKind.SERIES, "Comparison series", ({"x": "A", "y": 87}, {"x": "B", "y": 91})),
            PresentationBlock(PresentationKind.PROSE, "Key findings", "Configuration B was stronger in this controlled reference-shaped fixture."),
            PresentationBlock(PresentationKind.PROSE, "Limitations", "No scientific dependency was executed for this qualification."),
        )
    else:
        blocks = common + (
            PresentationBlock(PresentationKind.PROSE, "Key findings", "The final category remained amber under the bounded transition."),
            PresentationBlock(PresentationKind.TABLE, "Observed categories", {"columns": ["Step", "Category"], "rows": [["Start", "amber"], ["Finish", "amber"]]}),
            PresentationBlock(PresentationKind.SERIES, "Categorical sequence", ({"x": "Start", "y": "amber"}, {"x": "Finish", "y": "amber"})),
            PresentationBlock(PresentationKind.PROSE, "Limitations", "The controlled observation set is too small for a broad claim."),
        )
    return to_json_value(GenericExperimentPresentation(
        artifact_id=artifact_id,
        artifact_checksum=artifact_checksum,
        blocks=blocks,
    ))


def _approval(project_id: str, instance_id: str, created_at: datetime, *, variant: str = "initial") -> ControlledLocalRunApproval:
    summary = ControlledLocalRunSummary(
        what_will_run="A bounded categorical observation protocol.",
        research_objective="Determine whether category order is preserved.",
        preparation_method="Reviewed categorical observation preparation",
        research_resources=("Verified observation schedule",),
        execution_environment="Compatible local observation runtime",
        network_policy="DISABLED",
        compute_limits=("Five minutes", "One process"),
        expected_outputs=("Categorical observation record",),
        evaluation_approach="Compare observed category order with the declared protocol.",
        important_assumptions=("The observation schedule is complete",),
        important_limitations=("This supports only a narrow categorical claim",),
    )
    salt = canonical_hash({"variant": variant, "instance": instance_id})
    return ControlledLocalRunApproval.create(
        project_id=project_id,
        workflow_instance_id=instance_id,
        research_objective_checksum=canonical_hash({"objective": instance_id}),
        execution_plan_checksum=salt,
        validated_package_checksum=canonical_hash({"package": instance_id, "variant": variant}),
        runtime_compatibility_checksum=canonical_hash({"runtime": instance_id}),
        capability_checksum=canonical_hash({"capability": "categorical-observation"}),
        summary=summary,
        created_at=created_at,
    )


def seed(base_url: str, run_id: str, manifest_path: Path) -> None:
    project = _request(base_url, "/projects", {
        "name": "GEN-D-C1 controlled browser qualification",
        "research_topic": "Disposable categorical experiment projection",
        "selected_workflow": "LITERATURE_SEARCH",
        "workflow_setup": "custom",
        "custom_workflow_definition_ids": [IDEA, EXPERIMENT],
    })
    project_id = project["project_id"]
    page = _request(base_url, f"/projects/{project_id}/workflow-instances")
    initial = {item["workflow_definition_id"]: item for item in page["items"]}
    catalog = _request(base_url, f"/workflow-definitions/{EXPERIMENT}")
    v06 = next(item for item in catalog["versions"] if item["version"] == "0.6.0")
    capsule09 = next(item for item in catalog["capsules"] if item["capsule_version"] == "0.9.0")
    revision = page["manifest_revision"]
    instances: dict[str, dict] = {"fresh": initial[EXPERIMENT]}
    names = (
        "methodology", "design", "unsupported", "resource", "preparation_requirement",
        "preparation_complete", "runtime", "run_approval", "run_reject",
        "run_superseded", "result_review", "completed_presented", "completed_absent",
        "non_ml", "sklearn",
    )
    for name in names:
        created = _request(base_url, f"/projects/{project_id}/workflow-instances", {
            "workflow_definition_id": EXPERIMENT,
            "workflow_version": "0.6.0",
            "capsule_id": capsule09["capsule_id"],
            "capsule_version": "0.9.0",
            "display_name": f"C1 {name.replace('_', ' ')}",
            "base_revision": revision,
        })
        revision += 1
        instances[name] = created
    historical: dict[str, dict] = {}
    for key, version, capsule_version in (("experiment_04", "0.4.0", "0.7.0"), ("experiment_05", "0.5.0", "0.8.0")):
        capsule = next(item for item in catalog["capsules"] if item["capsule_version"] == capsule_version)
        historical[key] = _request(base_url, f"/projects/{project_id}/workflow-instances", {
            "workflow_definition_id": EXPERIMENT,
            "workflow_version": version,
            "capsule_id": capsule["capsule_id"],
            "capsule_version": capsule_version,
            "display_name": f"Historical Experiment {version}",
            "base_revision": revision,
        })
        revision += 1

    workspace_manifest = _request(base_url, f"/projects/{project_id}/manifest")
    pin_keys = (
        "workflow_instance_id", "workflow_definition_id", "workflow_definition_version",
        "capsule_id", "capsule_version", "capsule_definition_checksum",
    )
    installed_capsules = [
        {key: item[key] for key in pin_keys}
        for item in workspace_manifest["manifest"]["workflow_instances"]
    ]
    _request(base_url, f"/projects/{project_id}/workspace/sync-ack", {
        "schema_version": "reagent.capsule-installation-ack/v0.1",
        "installation_id": "install-" + run_id,
        "project_id": project_id,
        "workspace_id": workspace_manifest["workspace_id"],
        "manifest_revision": revision,
        "manifest_checksum": workspace_manifest["canonical_checksum"],
        "plan_checksum": HASH_A,
        "installed_lock_schema": "reagent.workspace-installed-lock/v0.1",
        "installed_lock_checksum": HASH_B,
        "idempotency_key": str(uuid5(UUID(run_id), "gen-d-c3-workspace-installation")),
        "installed_capsules": installed_capsules,
        "installed_at": "2026-08-17T03:00:00Z",
    })

    engine = create_postgres_engine(os.environ["REAGENT_DATABASE_URL"])
    uow = SQLAlchemyUnitOfWork(create_session_factory(engine))
    all_instances = [initial[IDEA], *instances.values(), *historical.values()]
    by_id = {item["workflow_instance_id"]: item for item in all_instances}

    def resolve(envelope, normalized, requested):
        item = by_id.get(requested or "")
        if item is None or envelope.project_id != project_id:
            raise ValueError("C1 fixture identity escaped the disposable Project")
        return item["workflow_instance_id"]

    service = ProgressReportService(
        repository=uow.progress_reports,
        content_storage=LocalFilesystemArtifactStorage(manifest_path.parent / "progress-originals"),
        commit_callback=uow.commit,
        workflow_identity_resolver=resolve,
        clock=lambda: datetime(2026, 8, 17, tzinfo=timezone.utc),
    )
    base_time = datetime(2026, 8, 17, 3, tzinfo=timezone.utc)
    idea_checksum = canonical_hash({"selected_idea": run_id})
    idea_output = OutputArtifactReference(
        relative_path=f"outputs/selected-research-idea-{run_id[:8]}.json",
        artifact_kind="selected-research-idea/v1",
        media_type="application/json",
        checksum=idea_checksum,
        size=512,
    )
    idea_detail = _request(base_url, f"/workflow-definitions/{IDEA}")
    idea_version = next(item for item in idea_detail["versions"] if item["version"] == initial[IDEA]["workflow_version"])
    idea_receipt, idea_report = _upload(
        service, run_id, project_id, initial[IDEA], idea_version["contract_checksum"],
        ProgressStatus.COMPLETED,
        "A controlled categorical observation objective is ready.",
        base_time,
        (idea_output,),
    )
    idea_artifact_id = "artifact-" + uuid5(UUID(run_id), "c1-selected-idea").hex
    uow.artifact_references.add_artifact(ArtifactReference(
        artifact_id=idea_artifact_id,
        project_id=project_id,
        producer_workflow_instance_id=initial[IDEA]["workflow_instance_id"],
        producer_progress_receipt_id=idea_receipt.receipt_id,
        producer_progress_report_id=idea_report.report_id,
        producer_execution_round=1,
        producer_capsule_id=initial[IDEA]["capsule_id"],
        producer_capsule_version=initial[IDEA]["capsule_version"],
        artifact_type="selected-research-idea/v1",
        artifact_schema_version="selected-research-idea/v1",
        media_type="application/json",
        state=ArtifactState.LOCAL_AVAILABLE,
        relative_path=idea_output.relative_path,
        content_checksum=idea_checksum,
        size_bytes=512,
        cloud_metadata_available=True,
        produced_at=base_time,
        retired_at=None,
        created_at=base_time,
        updated_at=base_time,
    ))
    uow.commit()
    for index, instance in enumerate(instances.values(), start=1):
        _request(base_url, f"/projects/{project_id}/workflow-instances/{instance['workflow_instance_id']}/artifact-dependencies", {
            "requirement_key": "research_idea",
            "artifact_id": idea_artifact_id,
            "idempotency_key": str(uuid5(UUID(run_id), f"idea-{instance['workflow_instance_id']}")),
        })

    summaries = {
        "methodology": "METHODOLOGY_DECISION_REQUIRED: choose whether observations are matched or independent.",
        "design": "DESIGN_APPROVAL_REQUIRED: the bounded categorical protocol is ready for scientific review.",
        "unsupported": "AUTOMATIC_PREPARATION_UNSUPPORTED: no reviewed preparation method supports this controlled methodology.",
        "resource": "RESOURCE_READINESS_REQUIRED: the observation schedule is known but not verified locally.",
        "preparation_requirement": "PREPARATION_REQUIREMENT_UNMET: a reviewed local observation tool is missing.",
        "preparation_complete": "PREPARATION_COMPLETE: the experiment implementation is prepared.",
        "runtime": "RUNTIME_INCOMPATIBLE: no compatible categorical observation runtime is available.",
        "run_approval": "RUN_APPROVAL_REQUIRED: review the exact bounded categorical run.",
        "run_reject": "RUN_APPROVAL_REQUIRED: review the exact run or request changes.",
        "run_superseded": "RUN_APPROVAL_REQUIRED: review the exact current prepared run.",
        "result_review": "RESULT_REVIEW_REQUIRED: review whether the categorical result and limitations are accurate.",
        "completed_presented": "Finalized controlled result with bounded presentation.",
        "completed_absent": "Finalized controlled result; presentation not yet reported.",
        "non_ml": "Finalized non-ML categorical result.",
        "sklearn": "Finalized reference-shaped comparison result.",
    }
    artifact_shapes = {
        "result_review": "non_ml",
        "completed_presented": "non_ml",
        "completed_absent": None,
        "non_ml": "non_ml",
        "sklearn": "sklearn",
    }
    artifacts: dict[str, str] = {}
    try:
        for offset, (name, summary) in enumerate(summaries.items(), start=1):
            instance = instances[name]
            shape = artifact_shapes.get(name, "missing")
            output: tuple[OutputArtifactReference, ...] = ()
            artifact_checksum = canonical_hash({"artifact": name, "run_id": run_id})
            if shape != "missing":
                output = (OutputArtifactReference(
                    relative_path=f"outputs/experiment-{name}.json",
                    artifact_kind="experiment-record/v4",
                    media_type="application/json",
                    checksum=artifact_checksum,
                    size=2048,
                ),)
            status = ProgressStatus.COMPLETED if shape != "missing" else ProgressStatus.BLOCKED
            receipt, report = _upload(
                service, run_id, project_id, instance, v06["contract_checksum"], status,
                summary, base_time + timedelta(minutes=offset), output,
            )
            if shape != "missing":
                artifact_id = "artifact-" + uuid5(UUID(run_id), f"c1-v4-{name}").hex
                artifacts[name] = artifact_id
                when = base_time + timedelta(minutes=offset)
                uow.artifact_references.add_artifact(ArtifactReference(
                    artifact_id=artifact_id,
                    project_id=project_id,
                    producer_workflow_instance_id=instance["workflow_instance_id"],
                    producer_progress_receipt_id=receipt.receipt_id,
                    producer_progress_report_id=report.report_id,
                    producer_execution_round=1,
                    producer_capsule_id=instance["capsule_id"],
                    producer_capsule_version=instance["capsule_version"],
                    artifact_type="experiment-record/v4",
                    artifact_schema_version="experiment-record/v4",
                    media_type="application/json",
                    state=ArtifactState.LOCAL_AVAILABLE,
                    relative_path=output[0].relative_path,
                    content_checksum=artifact_checksum,
                    size_bytes=2048,
                    cloud_metadata_available=True,
                    produced_at=when,
                    retired_at=None,
                    created_at=when,
                    updated_at=when,
                ))
                uow.commit()
                if shape is not None:
                    _request(
                        base_url,
                        f"/projects/{project_id}/artifacts/{artifact_id}/presentation",
                        _presentation(artifact_id, artifact_checksum, shape),
                        method="PUT",
                    )
    finally:
        uow.close()
        engine.dispose()

    approval_payloads = {}
    for index, name in enumerate(("run_approval", "run_reject", "run_superseded"), start=1):
        value = _approval(project_id, instances[name]["workflow_instance_id"], base_time + timedelta(hours=index))
        _request(base_url, f"/projects/{project_id}/workflow-instances/{instances[name]['workflow_instance_id']}/run-approvals", value.request_dict())
        if name == "run_superseded":
            replacement = _approval(project_id, instances[name]["workflow_instance_id"], base_time + timedelta(hours=index, minutes=1), variant="replacement")
            approval_payloads["superseding_request"] = replacement.request_dict()

    manifest = {
        "schema": "reagent.gen-d-c1-controlled-fixtures/v0.1",
        "run_id": run_id,
        "project_id": project_id,
        "project_name": project["name"],
        "instances": {name: value["workflow_instance_id"] for name, value in instances.items()},
        "historical": {name: value["workflow_instance_id"] for name, value in historical.items()},
        "non_experiment": initial[IDEA]["workflow_instance_id"],
        "artifacts": artifacts,
        **approval_payloads,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(canonical_json(manifest) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    seed(args.api_url, args.run_id, args.manifest)


if __name__ == "__main__":
    main()
