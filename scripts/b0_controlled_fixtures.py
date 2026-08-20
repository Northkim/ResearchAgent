"""Seed the four contract-bounded states for B0 browser qualification."""
from __future__ import annotations
import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid5
from backend.artifact_references.contracts import (
    PAPER_LIBRARY_QUALIFICATION_SCHEMA,
    ArtifactReference,
    ArtifactState,
)
from backend.artifact_references.service import ArtifactReferenceService
from backend.artifact_references.upstream_presentations import (
    MANUSCRIPT_PRESENTATION_SCHEMA, PAPER_LIBRARY_PRESENTATION_SCHEMA,
    RESEARCH_IDEA_PRESENTATION_SCHEMA, REVIEW_PRESENTATION_SCHEMA_V2,
)
from backend.database import SQLAlchemyUnitOfWork, create_postgres_engine, create_session_factory
from backend.progress_reports.contracts import (
    ACCEPTED_REPORT_MEDIA_TYPE, EXPERIMENTAL_DECLARATION, OutputArtifactReference,
    PinReference, ProgressReportUploadEnvelope, ProgressReportV2, ProgressStatus,
)
from backend.progress_reports.service import ProgressReportService
from backend.research.adapters import LocalFilesystemArtifactStorage
from backend.workflow_packages.serialization import canonical_hash, canonical_json
HASH_A, HASH_B = "sha256:" + "a" * 64, "sha256:" + "b" * 64
WORKFLOWS = ("literature-search-local-experimental", "idea-discovery-local-experimental",
             "writing-local-experimental", "review-local-experimental")


def _report_selected_paper_count(
    service: ArtifactReferenceService,
    *,
    project_id: str,
    artifact_id: str,
    artifact_checksum: str,
    selected_count: int,
) -> None:
    payload = {
        "schema": PAPER_LIBRARY_QUALIFICATION_SCHEMA,
        "artifact_id": artifact_id,
        "artifact_checksum": artifact_checksum,
        "selected_count": selected_count,
    }
    service.report_content_qualification(
        project_id=project_id,
        artifact_id=artifact_id,
        payload={**payload, "qualification_checksum": canonical_hash(payload)},
    )


def _request(base_url: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else canonical_json(payload).encode("utf-8")
    request = urllib.request.Request(base_url + path, data=data,
        method="GET" if payload is None else "POST",
        headers={"Accept": "application/json", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())
def _upload(service: ProgressReportService, run_id: str, project_id: str,
            instance: dict, workflow_checksum: str, status: ProgressStatus,
            state: str, timestamp: str,
            outputs: tuple[OutputArtifactReference, ...] = ()):
    package_id = f"b0-fixture-{run_id}-{instance['workflow_instance_id']}"
    package_checksum = canonical_hash({"schema_version": "reagent.b0-package-reference/v0.1",
        "run_id": run_id, "workflow_instance_id": instance["workflow_instance_id"]})
    report = ProgressReportV2.create(
        package_id=package_id, package_schema_version="workflow-package/v0.1",
        package_checksum=package_checksum, project_id=project_id,
        workflow_id=instance["workflow_definition_id"], workflow_version=instance["workflow_version"],
        workflow_checksum=workflow_checksum, execution_round=1,
        harness_type="b0-controlled-fixture", harness_version="0.1.0",
        harness_session_id=f"b0-{instance['workflow_instance_id']}",
        previous_report_id=None, previous_report_checksum=None, started_at=timestamp,
        completed_at=timestamp, status=status, completed_work=(state,), current_state=state,
        next_recommended_action="Wait for the next explicit owner action.", continuation_reason=None,
        output_artifacts=outputs, context_before_checksum=HASH_A, context_after_checksum=HASH_B,
        warnings=(), errors=(), unresolved_questions=(() if status is ProgressStatus.COMPLETED
            else ("Owner action is required.",)),
        continuation_instructions=("Use only this disposable controlled fixture.",),
        skill_pins=(PinReference("SKILL", "b0-controlled-skill", "0.1.0", HASH_A),),
        template_pins=(PinReference("TEMPLATE", "b0-controlled-template", "0.1.0", HASH_B),),
        generated_at=timestamp, experimental_declaration=EXPERIMENTAL_DECLARATION)
    report_bytes = (canonical_json(report) + "\n").encode("utf-8")
    envelope = ProgressReportUploadEnvelope.create(
        original_report_bytes=report_bytes, project_id=project_id, package_id=package_id,
        package_checksum=package_checksum, report_schema_version=report.schema_version,
        report_id=report.report_id, report_checksum=report.report_checksum,
        original_report_media_type=ACCEPTED_REPORT_MEDIA_TYPE, uploaded_at=timestamp,
        uploader_type="b0-controlled-fixture", client_version="b0-controlled-fixture/0.1.0",
        source_path_hint=f"memory/progress/{report.report_id}.json", context_snapshot_metadata=None)
    receipt = service.upload(envelope, workflow_instance_id=instance["workflow_instance_id"])
    if not receipt.accepted_for_projection:
        raise RuntimeError("B0 fixture Progress was not accepted for projection")
    return receipt, report
def seed(
    base_url: str,
    run_id: str,
    manifest_path: Path,
    *,
    project_name: str | None = None,
    research_topic: str | None = None,
    scenario: str = "b0",
) -> None:
    project_name = project_name or f"B0 controlled {run_id}"
    project = _request(base_url, "/projects", {"name": project_name,
        "research_topic": research_topic or "Disposable browser qualification only",
        "selected_workflow": "LITERATURE_SEARCH", "workflow_setup": "custom",
        "custom_workflow_definition_ids": list(WORKFLOWS)})
    project_id = project["project_id"]
    instances_page = _request(base_url, f"/projects/{project_id}/workflow-instances")
    instances = {item["workflow_definition_id"]: item for item in instances_page["items"]}
    if set(instances) != set(WORKFLOWS) or instances_page["total"] != 4:
        raise RuntimeError("B0 fixture must contain exactly four Workflow Instances")
    catalog = _request(base_url, "/workflow-definitions")
    checksums = {item["workflow_definition_id"]: item["recommended_version"]["contract_checksum"]
                 for item in catalog["items"] if item["workflow_definition_id"] in WORKFLOWS}
    if set(checksums) != set(WORKFLOWS):
        raise RuntimeError("B0 Workflow contract identities are incomplete")
    engine = create_postgres_engine(os.environ["REAGENT_DATABASE_URL"])
    uow = SQLAlchemyUnitOfWork(create_session_factory(engine))
    by_instance = {item["workflow_instance_id"]: item for item in instances.values()}
    def resolve(envelope, normalized, requested):
        item = by_instance.get(requested or "")
        if item is None or envelope.project_id != project_id:
            raise ValueError("B0 Progress identity is outside the controlled Project")
        if normalized is not None and (normalized.workflow_id != item["workflow_definition_id"]
                or normalized.workflow_version != item["workflow_version"]):
            raise ValueError("B0 Progress Workflow identity mismatch")
        return item["workflow_instance_id"]
    now = datetime(2026, 8, 14, tzinfo=timezone.utc)
    service = ProgressReportService(repository=uow.progress_reports,
        content_storage=LocalFilesystemArtifactStorage(manifest_path.parent / "progress-originals"),
        commit_callback=uow.commit, workflow_identity_resolver=resolve, clock=lambda: now)
    artifact_checksum = canonical_hash({"schema_version":
        "reagent.b0-synthetic-artifact-reference/v0.1", "run_id": run_id,
        "scientific_content": False})
    output = OutputArtifactReference(
        relative_path=f"outputs/artifacts/selected-paper-library/sha256-{artifact_checksum[7:]}.json",
        artifact_kind="selected-paper-library/v1", media_type="application/json",
        checksum=artifact_checksum, size=0)
    try:
        receipt, completed_report = _upload(
            service, run_id, project_id, instances[WORKFLOWS[0]], checksums[WORKFLOWS[0]],
            ProgressStatus.COMPLETED, "Synthetic completion metadata only; no research ran.",
            "2026-08-14T01:01:00Z", (output,))
        uow.artifact_references.add_artifact(ArtifactReference(
            artifact_id="artifact-" + run_id, project_id=project_id,
            producer_workflow_instance_id=instances[WORKFLOWS[0]]["workflow_instance_id"],
            producer_progress_receipt_id=receipt.receipt_id,
            producer_progress_report_id=completed_report.report_id, producer_execution_round=1,
            producer_capsule_id=instances[WORKFLOWS[0]]["capsule_id"],
            producer_capsule_version=instances[WORKFLOWS[0]]["capsule_version"],
            artifact_type="selected-paper-library/v1", artifact_schema_version="selected-paper-library/v1",
            media_type="application/json",
            state=(ArtifactState.LOCAL_AVAILABLE
                   if scenario in {"fe-m-desktop", "ep-d2-u1"} else ArtifactState.METADATA_ONLY),
            relative_path=output.relative_path, content_checksum=artifact_checksum, size_bytes=0,
            cloud_metadata_available=True, produced_at=now, retired_at=None, created_at=now,
            updated_at=now))
        uow.commit()
        if scenario in {"fe-m-desktop", "ep-d2-u1"}:
            artifact_service = ArtifactReferenceService(
                unit_of_work=uow, clock=lambda: now
            )
            _report_selected_paper_count(
                artifact_service,
                project_id=project_id,
                artifact_id="artifact-" + run_id,
                artifact_checksum=artifact_checksum,
                selected_count=1,
            )
            _request(base_url,
                f"/projects/{project_id}/workflow-instances/"
                f"{instances[WORKFLOWS[1]]['workflow_instance_id']}/artifact-dependencies", {
                    "requirement_key": "paper_library", "artifact_id": "artifact-" + run_id,
                    "idempotency_key": str(uuid5(UUID(run_id), "fe-m-idea-paper-library")),
                })
            idea_checksum = canonical_hash({
                "schema_version": "reagent.fe-m-selected-research-idea/v0.1",
                "run_id": run_id, "scientific_content": False,
            })
            idea_output = OutputArtifactReference(
                relative_path=("outputs/artifacts/selected-research-idea/sha256-"
                               f"{idea_checksum[7:]}.json"),
                artifact_kind="selected-research-idea/v1", media_type="application/json",
                checksum=idea_checksum, size=0)
            idea_receipt, idea_report = _upload(
                service, run_id, project_id, instances[WORKFLOWS[1]], checksums[WORKFLOWS[1]],
                ProgressStatus.COMPLETED,
                "Selected research idea confirmed from the controlled evidence map.",
                "2026-08-14T01:02:00Z", (idea_output,))
            idea_artifact_id = "artifact-" + uuid5(
                UUID(run_id), "fe-m-selected-research-idea"
            ).hex
            idea_time = datetime(2026, 8, 14, 1, 2, tzinfo=timezone.utc)
            uow.artifact_references.add_artifact(ArtifactReference(
                artifact_id=idea_artifact_id, project_id=project_id,
                producer_workflow_instance_id=instances[WORKFLOWS[1]]["workflow_instance_id"],
                producer_progress_receipt_id=idea_receipt.receipt_id,
                producer_progress_report_id=idea_report.report_id, producer_execution_round=1,
                producer_capsule_id=instances[WORKFLOWS[1]]["capsule_id"],
                producer_capsule_version=instances[WORKFLOWS[1]]["capsule_version"],
                artifact_type="selected-research-idea/v1",
                artifact_schema_version="selected-research-idea/v1",
                media_type="application/json", state=ArtifactState.LOCAL_AVAILABLE,
                relative_path=idea_output.relative_path, content_checksum=idea_checksum,
                size_bytes=0, cloud_metadata_available=True, produced_at=idea_time,
                retired_at=None, created_at=idea_time, updated_at=idea_time))
            uow.commit()
            if scenario == "ep-d2-u1":
                second_artifact_id = "artifact-" + uuid5(
                    UUID(run_id), "ep-d2-u1-second-library"
                ).hex
                absent_artifact_id = "artifact-" + uuid5(
                    UUID(run_id), "ep-d2-u1-absent-library-preview"
                ).hex
                second_checksum = canonical_hash({
                    "schema_version": "reagent.ep-d2-u1-second-library/v0.1",
                    "run_id": run_id, "scientific_content": False,
                })
                uow.artifact_references.add_artifact(ArtifactReference(
                    artifact_id=second_artifact_id, project_id=project_id,
                    producer_workflow_instance_id=instances[WORKFLOWS[0]]["workflow_instance_id"],
                    producer_progress_receipt_id=receipt.receipt_id,
                    producer_progress_report_id=completed_report.report_id,
                    producer_execution_round=1,
                    producer_capsule_id=instances[WORKFLOWS[0]]["capsule_id"],
                    producer_capsule_version=instances[WORKFLOWS[0]]["capsule_version"],
                    artifact_type="selected-paper-library/v1",
                    artifact_schema_version="selected-paper-library/v1",
                    media_type="application/json", state=ArtifactState.LOCAL_AVAILABLE,
                    relative_path=("outputs/artifacts/selected-paper-library/sha256-"
                                   f"{second_checksum[7:]}.json"),
                    content_checksum=second_checksum, size_bytes=0,
                    cloud_metadata_available=True, produced_at=idea_time,
                    retired_at=None, created_at=idea_time, updated_at=idea_time))
                absent_checksum = canonical_hash({
                    "schema_version": "reagent.ep-d2-u1-absent-library/v0.1",
                    "run_id": run_id, "scientific_content": False,
                })
                uow.artifact_references.add_artifact(ArtifactReference(
                    artifact_id=absent_artifact_id, project_id=project_id,
                    producer_workflow_instance_id=instances[WORKFLOWS[0]]["workflow_instance_id"],
                    producer_progress_receipt_id=receipt.receipt_id,
                    producer_progress_report_id=completed_report.report_id,
                    producer_execution_round=1,
                    producer_capsule_id=instances[WORKFLOWS[0]]["capsule_id"],
                    producer_capsule_version=instances[WORKFLOWS[0]]["capsule_version"],
                    artifact_type="selected-paper-library/v1",
                    artifact_schema_version="selected-paper-library/v1",
                    media_type="application/json", state=ArtifactState.LOCAL_AVAILABLE,
                    relative_path=("outputs/artifacts/selected-paper-library/sha256-"
                                   f"{absent_checksum[7:]}.json"),
                    content_checksum=absent_checksum, size_bytes=0,
                    cloud_metadata_available=True, produced_at=idea_time,
                    retired_at=None, created_at=idea_time, updated_at=idea_time))
                uow.commit()
                _report_selected_paper_count(
                    artifact_service,
                    project_id=project_id,
                    artifact_id=second_artifact_id,
                    artifact_checksum=second_checksum,
                    selected_count=1,
                )
                _report_selected_paper_count(
                    artifact_service,
                    project_id=project_id,
                    artifact_id=absent_artifact_id,
                    artifact_checksum=absent_checksum,
                    selected_count=1,
                )
                presentation_service = ArtifactReferenceService(
                    unit_of_work=uow, clock=lambda: now
                )
                def report_papers(artifact_id: str, checksum: str, *, doi: bool) -> None:
                    payload = {
                        "schema": PAPER_LIBRARY_PRESENTATION_SCHEMA,
                        "artifact_id": artifact_id, "artifact_checksum": checksum,
                        "selected_count": 1, "selection_status": "SELECTED",
                        "evidence_basis": ["METADATA_AND_ABSTRACT" if doi else "METADATA_ONLY"],
                        "limitations": ["Full text is not represented in this controlled preview."],
                        "papers": [{
                            "title": ("Bounded archival classification study" if doi
                                      else "Contrasting categorical field record"),
                            "authors": ["Fictional Qualification Author"],
                            "year": 2026 if doi else None,
                            "identifier_kind": "DOI" if doi else "PROVIDER_ID",
                            "identifier": "10.1000/controlled.1" if doi else "controlled-record-2",
                            "why_selected": "Directly informs the controlled research direction.",
                            "evidence_availability": "METADATA_AND_ABSTRACT" if doi else "METADATA_ONLY",
                            "limitation": ("Abstract only; full text is not represented." if doi
                                           else "Metadata only; no abstract or full text is represented."),
                        }],
                        "papers_truncated": False,
                    }
                    presentation_service.report_presentation(
                        project_id=project_id, artifact_id=artifact_id,
                        payload={**payload, "presentation_checksum": canonical_hash(payload)},
                    )
                report_papers("artifact-" + run_id, artifact_checksum, doi=True)
                report_papers(second_artifact_id, second_checksum, doi=False)
                idea_payload = {
                    "schema": RESEARCH_IDEA_PRESENTATION_SCHEMA,
                    "artifact_id": idea_artifact_id, "artifact_checksum": idea_checksum,
                    "title": "Compare archival classification practices",
                    "summary": "Investigate how two bounded practices shape categorical outcomes.",
                    "research_question": "Where do the reported categories diverge?",
                    "observed_gap": "The selected abstracts do not compare the practices directly.",
                    "proposed_direction": "Apply a bounded comparative observation protocol.",
                    "assumptions": ["Reported metadata is internally consistent."],
                    "risks": ["The evidence is limited to metadata and abstracts."],
                    "validation_needed": ["Confirm access to the underlying archival records."],
                    "literature_basis_count": 1,
                    "source_literature_artifact": {
                        "artifact_id": "artifact-" + run_id,
                        "artifact_type": "selected-paper-library/v1",
                        "artifact_checksum": artifact_checksum,
                    },
                }
                presentation_service.report_presentation(
                    project_id=project_id, artifact_id=idea_artifact_id,
                    payload={**idea_payload, "presentation_checksum": canonical_hash(idea_payload)},
                )
            if scenario != "ep-d2-u1":
                writing_id = instances[WORKFLOWS[2]]["workflow_instance_id"]
                for key, artifact_id, idempotency_name in (
                    ("research_idea", idea_artifact_id, "fe-m-writing-research-idea"),
                    ("literature_library", "artifact-" + run_id, "fe-m-writing-literature"),
                ):
                    _request(base_url,
                        f"/projects/{project_id}/workflow-instances/{writing_id}/artifact-dependencies", {
                            "requirement_key": key, "artifact_id": artifact_id,
                            "idempotency_key": str(uuid5(UUID(run_id), idempotency_name)),
                        })
        else:
            _upload(service, run_id, project_id, instances[WORKFLOWS[1]], checksums[WORKFLOWS[1]],
                    ProgressStatus.BLOCKED,
                    "Blocked until an exact controlled input is available.",
                    "2026-08-14T01:02:00Z")
        if scenario != "ep-d2-u1":
            _upload(service, run_id, project_id, instances[WORKFLOWS[2]], checksums[WORKFLOWS[2]],
                    ProgressStatus.BLOCKED,
                    ("The evidence map and six-section outline are ready for owner review."
                     if scenario == "fe-m-desktop"
                     else "Awaiting owner action before any scaffold Writing activity."),
                    "2026-08-14T01:03:00Z")
    finally:
        uow.close()
        engine.dispose()
    manifest = _request(base_url, f"/projects/{project_id}/manifest")
    pin_keys = ("workflow_instance_id", "workflow_definition_id", "workflow_definition_version",
                "capsule_id", "capsule_version", "capsule_definition_checksum")
    installed_capsules = [{key: item[key] for key in pin_keys}
                          for item in manifest["manifest"]["workflow_instances"]]
    _request(base_url, f"/projects/{project_id}/workspace/sync-ack", {
        "schema_version": "reagent.capsule-installation-ack/v0.1",
        "installation_id": "install-" + run_id, "project_id": project_id,
        "workspace_id": manifest["workspace_id"], "manifest_revision": 1,
        "manifest_checksum": manifest["canonical_checksum"], "plan_checksum": HASH_A,
        "installed_lock_schema": "reagent.workspace-installed-lock/v0.1",
        "installed_lock_checksum": HASH_B, "idempotency_key": str(UUID(run_id)),
        "installed_capsules": installed_capsules, "installed_at": "2026-08-14T01:00:00Z",
    })
    review = instances[WORKFLOWS[3]]
    _request(base_url, f"/projects/{project_id}/workflow-instances/{review['workflow_instance_id']}/retire",
             {"base_revision": 1})
    if scenario == "ep-d2-u1":
        manifest = _request(base_url, f"/projects/{project_id}/manifest")
        current_capsules = [
            {key: item[key] for key in pin_keys}
            for item in manifest["manifest"]["workflow_instances"]
            if item.get("desired_state") == "ACTIVE"
        ]
        _request(base_url, f"/projects/{project_id}/workspace/sync-ack", {
            "schema_version": "reagent.capsule-installation-ack/v0.1",
            "installation_id": "install-" + uuid5(UUID(run_id), "ep-d2-u1-current").hex,
            "project_id": project_id, "workspace_id": manifest["workspace_id"],
            "manifest_revision": manifest["manifest_revision"],
            "manifest_checksum": manifest["canonical_checksum"], "plan_checksum": HASH_A,
            "installed_lock_schema": "reagent.workspace-installed-lock/v0.1",
            "installed_lock_checksum": HASH_B,
            "idempotency_key": str(uuid5(UUID(run_id), "ep-d2-u1-current-ack")),
            "installed_capsules": current_capsules, "installed_at": "2026-08-14T01:04:00Z",
        })
    progress = _request(base_url, f"/projects/{project_id}/progress")
    by_workflow = {item["workflow_definition_id"]: item for item in progress["instances"]}
    expected = dict(zip(WORKFLOWS, (
        "COMPLETED", "COMPLETED" if scenario in {"fe-m-desktop", "ep-d2-u1"} else "BLOCKED",
        "NOT_STARTED" if scenario == "ep-d2-u1" else "BLOCKED", "NOT_STARTED",
    )))
    if len(progress["instances"]) != 4 or any(
            by_workflow[key]["research_status"] != value for key, value in expected.items()):
        raise RuntimeError("B0 fixture states do not match the approved mapping")
    completed, mismatch = by_workflow[WORKFLOWS[0]], by_workflow[WORKFLOWS[3]]
    expected_literature_results = 3 if scenario == "ep-d2-u1" else 1
    declared_outputs = completed["artifact_metadata"]
    if (len(declared_outputs) != 1
            or declared_outputs[0]["artifact_kind"] != "selected-paper-library/v1"
            or declared_outputs[0]["checksum"] != artifact_checksum):
        raise RuntimeError("B0 completion lacks its exact latest Progress output")
    if completed["result_count"] != expected_literature_results:
        raise RuntimeError("B0 completion lacks its expected total Artifact results")
    if scenario in {"fe-m-desktop", "ep-d2-u1"}:
        expected_bindings = 1 if scenario == "ep-d2-u1" else 3
        if len(progress["dependency_edges"]) != expected_bindings:
            raise RuntimeError("Controlled fixture lacks its exact Artifact bindings")
    elif progress["dependency_edges"]:
        raise RuntimeError("B0 fixture must not create Artifact dependency bindings")
    if mismatch["installation_state"] != "ACKNOWLEDGED_STALE":
        raise RuntimeError("B0 fixture lacks a proven stale local/Cloud installation")
    writing = by_workflow[WORKFLOWS[2]]
    if scenario == "ep-d2-u1":
        if (writing["next_action"] != "SELECT_INPUT"
                or writing["action"]["next_action"]["code"] != "SELECT_INPUT"
                or set(writing["missing_required_inputs"])
                != {"research_idea", "literature_library"}
                or writing["compatible_input_counts"].get("research_idea") != 1
                or writing["compatible_input_counts"].get("literature_library") != 3):
            raise RuntimeError("EP-D2-U1 Writing fixture is not in exact SELECT_INPUT state")
    else:
        expected_writing_summary = (
            "six-section outline" if scenario == "fe-m-desktop"
            else "Awaiting owner action"
        )
        if expected_writing_summary not in writing["latest_summary"]:
            raise RuntimeError("B0 owner-action state is not observable")
    manifest_path.write_text(canonical_json({
        "schema_version": "reagent.b0-controlled-fixtures/v0.1", "run_id": run_id,
        "project_id": project_id, "project_name": project_name,
        "workspace_id": manifest["workspace_id"], "manifest_revision": progress["manifest_revision"],
        "instances": {key: value["workflow_instance_id"] for key, value in instances.items()}
    }) + "\n", encoding="utf-8")


def _seed_ep_d2_project(
    base_url: str, run_id: str, manifest_path: Path, *, project_name: str,
    with_completed_revision: bool,
) -> dict:
    project = _request(base_url, "/projects", {
        "name": project_name,
        "research_topic": "Controlled forward Full Research product-width qualification",
        "selected_workflow": "LITERATURE_SEARCH",
        "workflow_setup": "full-research",
    })
    project_id = project["project_id"]
    items = _request(base_url, f"/projects/{project_id}/workflow-instances")["items"]
    if len(items) != 5:
        raise RuntimeError("EP-D2 fixture must start with exactly five Workflows")
    roles = {
        "literature": next(item for item in items if item["workflow_definition_id"] == WORKFLOWS[0]),
        "idea": next(item for item in items if item["workflow_definition_id"] == WORKFLOWS[1]),
        "experiment": next(item for item in items if item["workflow_definition_id"] == "reproduction-experiment-local-experimental"),
        "writing": next(item for item in items if item["workflow_definition_id"] == WORKFLOWS[2]),
        "review": next(item for item in items if item["workflow_definition_id"] == WORKFLOWS[3]),
    }
    expected = {
        "literature": ("0.6.0", "0.8.0"), "idea": ("0.4.0", "0.5.0"),
        "experiment": ("0.8.0", "0.11.0"), "writing": ("0.5.0", "0.7.0"),
        "review": ("0.4.0", "0.6.0"),
    }
    if any((roles[key]["workflow_version"], roles[key]["capsule_version"]) != pin
           for key, pin in expected.items()):
        raise RuntimeError("EP-D2 fixture Full Research pins are not exact")

    def workflow_checksum(instance: dict) -> str:
        detail = _request(base_url, f"/workflow-definitions/{instance['workflow_definition_id']}")
        return next(
            version["contract_checksum"] for version in detail["versions"]
            if version["version"] == instance["workflow_version"]
        )

    engine = create_postgres_engine(os.environ["REAGENT_DATABASE_URL"])
    uow = SQLAlchemyUnitOfWork(create_session_factory(engine))
    by_instance = {item["workflow_instance_id"]: item for item in roles.values()}

    def resolve(envelope, normalized, requested):
        item = by_instance.get(requested or "")
        if item is None or envelope.project_id != project_id:
            raise ValueError("EP-D2 Progress identity is outside the controlled Project")
        if normalized is not None and (
            normalized.workflow_id != item["workflow_definition_id"]
            or normalized.workflow_version != item["workflow_version"]
        ):
            raise ValueError("EP-D2 Progress Workflow identity mismatch")
        return item["workflow_instance_id"]

    now = datetime(2026, 8, 18, 8, 0, tzinfo=timezone.utc)
    progress_service = ProgressReportService(
        repository=uow.progress_reports,
        content_storage=LocalFilesystemArtifactStorage(manifest_path.parent / f"progress-{run_id}"),
        commit_callback=uow.commit,
        workflow_identity_resolver=resolve,
        clock=lambda: now,
    )

    def complete(role: str, artifact_type: str, sequence: int) -> dict:
        instance = roles[role]
        artifact_id = "artifact-" + uuid5(UUID(run_id), f"ep-d2-{role}-{artifact_type}").hex
        checksum = canonical_hash({
            "schema_version": artifact_type,
            "qualification": "EP-D2 controlled browser metadata",
            "run_id": run_id,
            "role": role,
        })
        output = OutputArtifactReference(
            relative_path=f"outputs/{artifact_type.replace('/', '-')}.json",
            artifact_kind=artifact_type,
            media_type="application/json",
            checksum=checksum,
            size=0,
        )
        timestamp = f"2026-08-18T08:{sequence:02d}:00Z"
        receipt, report = _upload(
            progress_service, run_id, project_id, instance,
            workflow_checksum(instance), ProgressStatus.COMPLETED,
            f"{role.replace('_', ' ').title()} completed in the controlled qualification.",
            timestamp, (output,),
        )
        produced = datetime(2026, 8, 18, 8, sequence, tzinfo=timezone.utc)
        uow.artifact_references.add_artifact(ArtifactReference(
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
            relative_path=output.relative_path,
            content_checksum=checksum,
            size_bytes=0,
            cloud_metadata_available=True,
            produced_at=produced,
            retired_at=None,
            created_at=produced,
            updated_at=produced,
        ))
        uow.commit()
        return {
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "artifact_checksum": checksum,
        }

    def bind(consumer: dict, key: str, artifact: dict) -> None:
        _request(
            base_url,
            f"/projects/{project_id}/workflow-instances/{consumer['workflow_instance_id']}/artifact-dependencies",
            {
                "requirement_key": key,
                "artifact_id": artifact["artifact_id"],
                "idempotency_key": str(uuid5(UUID(run_id), f"ep-d2-{consumer['workflow_instance_id']}-{key}")),
            },
        )

    try:
        literature = complete("literature", "selected-paper-library/v1", 1)
        artifact_service = ArtifactReferenceService(unit_of_work=uow, clock=lambda: now)
        _report_selected_paper_count(
            artifact_service,
            project_id=project_id,
            artifact_id=literature["artifact_id"],
            artifact_checksum=literature["artifact_checksum"],
            selected_count=1,
        )
        bind(roles["idea"], "paper_library", literature)
        idea = complete("idea", "selected-research-idea/v1", 2)
        bind(roles["experiment"], "research_idea", idea)
        experiment = complete("experiment", "experiment-record/v5", 3)
        for key, artifact in (
            ("research_idea", idea), ("literature_library", literature),
            ("experiment_record", experiment),
        ):
            bind(roles["writing"], key, artifact)
        manuscript = complete("writing", "manuscript-draft/v4", 4)
        for key, artifact in (
            ("manuscript", manuscript), ("research_idea", idea),
            ("literature_library", literature), ("experiment_record", experiment),
        ):
            bind(roles["review"], key, artifact)
        review = complete("review", "review-report/v3", 5)

        presentation_service = artifact_service
        initial_payload = {
            "schema": MANUSCRIPT_PRESENTATION_SCHEMA,
            "artifact_id": manuscript["artifact_id"],
            "artifact_checksum": manuscript["artifact_checksum"],
            "mode": "INITIAL",
            "title": "Bounded archival comparison manuscript",
            "summary": "Reports one controlled categorical observation within the exact supplied evidence boundary.",
            "sections": ["Introduction", "Method", "Results", "Limitations"],
            "evidence_coverage": {
                "claim_count": 3, "supported_claim_count": 2,
                "planned_claim_count": 0, "unavailable_claim_count": 1,
            },
            "result_availability": "AVAILABLE",
            "limitations": ["The selected sources contain metadata and abstracts, not full text."],
            "owner_review_status": "APPROVED",
            "source_artifacts": [
                {"role": "research idea", **idea},
                {"role": "paper library", **literature},
                {"role": "experiment result", **experiment},
            ],
            "parent_manuscript": None,
            "causal_review": None,
            "changed_sections": [],
            "change_summary": None,
            "issue_dispositions": [],
            "unresolved_issue_count": 0,
        }
        if with_completed_revision:
            presentation_service.report_presentation(
                project_id=project_id,
                artifact_id=manuscript["artifact_id"],
                payload={**initial_payload, "presentation_checksum": canonical_hash(initial_payload)},
            )
        review_payload = {
            "schema": REVIEW_PRESENTATION_SCHEMA_V2,
            "artifact_id": review["artifact_id"],
            "artifact_checksum": review["artifact_checksum"],
            "reviewed_manuscript": manuscript,
            "scope": "Claim support, Experiment validity, evidence sufficiency, and reproducibility.",
            "status": "REVISION_REQUIRED",
            "summary": "One bounded limitation must be made explicit before the manuscript is complete.",
            "issues": [{
                "issue_id": "issue-limitation-1", "category": "EVIDENCE_BOUNDARY",
                "severity": "MINOR", "blocking": True,
                "summary": "The abstract-only evidence boundary is implicit.",
                "requested_revision": "State that full-text evidence was not supplied.",
                "status": "REPORTED",
            }],
            "unresolved_evidence_gaps": ["Full-text evidence remains unavailable."],
            "reproducibility_findings": ["The bounded comparison protocol is described."],
            "limitations": ["This controlled Review uses only the exact supplied inputs."],
            "owner_review_status": "APPROVED",
        }
        presentation_service.report_presentation(
            project_id=project_id,
            artifact_id=review["artifact_id"],
            payload={**review_payload, "presentation_checksum": canonical_hash(review_payload)},
        )

        if with_completed_revision:
            revision = _request(base_url, f"/projects/{project_id}/writing-revisions", {
                "parent_manuscript_artifact_id": manuscript["artifact_id"],
                "causal_review_artifact_id": review["artifact_id"],
                "base_revision": 1,
            })
            roles["revision"] = revision
            by_instance[revision["workflow_instance_id"]] = revision
            revised = complete("revision", "manuscript-draft/v5", 6)
            revision_payload = {
                "schema": MANUSCRIPT_PRESENTATION_SCHEMA,
                "artifact_id": revised["artifact_id"],
                "artifact_checksum": revised["artifact_checksum"],
                "mode": "REVISION",
                "title": "Revised bounded archival comparison manuscript",
                "summary": "Makes the exact evidence boundary explicit while preserving the bounded finding.",
                "sections": ["Introduction", "Method", "Results", "Limitations"],
                "evidence_coverage": {
                    "claim_count": 3, "supported_claim_count": 2,
                    "planned_claim_count": 0, "unavailable_claim_count": 1,
                },
                "result_availability": "AVAILABLE",
                "limitations": ["Full-text evidence remains unavailable."],
                "owner_review_status": "APPROVED",
                "source_artifacts": [
                    {"role": "research idea", **idea},
                    {"role": "paper library", **literature},
                    {"role": "experiment result", **experiment},
                ],
                "parent_manuscript": manuscript,
                "causal_review": review,
                "changed_sections": ["Limitations"],
                "change_summary": "The evidence limitation is now explicit.",
                "issue_dispositions": [{
                    "issue_id": "issue-limitation-1", "disposition": "ADDRESSED",
                }],
                "unresolved_issue_count": 0,
            }
            presentation_service.report_presentation(
                project_id=project_id,
                artifact_id=revised["artifact_id"],
                payload={**revision_payload, "presentation_checksum": canonical_hash(revision_payload)},
            )
    finally:
        uow.close()
        engine.dispose()

    manifest = _request(base_url, f"/projects/{project_id}/manifest")
    pin_keys = (
        "workflow_instance_id", "workflow_definition_id", "workflow_definition_version",
        "capsule_id", "capsule_version", "capsule_definition_checksum",
    )
    _request(base_url, f"/projects/{project_id}/workspace/sync-ack", {
        "schema_version": "reagent.capsule-installation-ack/v0.1",
        "installation_id": "install-" + uuid5(UUID(run_id), project_name).hex,
        "project_id": project_id,
        "workspace_id": manifest["workspace_id"],
        "manifest_revision": manifest["manifest_revision"],
        "manifest_checksum": manifest["canonical_checksum"],
        "plan_checksum": HASH_A,
        "installed_lock_schema": "reagent.workspace-installed-lock/v0.1",
        "installed_lock_checksum": HASH_B,
        "idempotency_key": str(uuid5(UUID(run_id), f"ep-d2-install-{project_name}")),
        "installed_capsules": [
            {key: item[key] for key in pin_keys}
            for item in manifest["manifest"]["workflow_instances"]
        ],
        "installed_at": "2026-08-18T08:10:00Z",
    })
    return {
        "project_id": project_id,
        "project_name": project_name,
        "instances": {key: value["workflow_instance_id"] for key, value in roles.items()},
    }


def seed_ep_d2(base_url: str, run_id: str, manifest_path: Path) -> None:
    eligible_id = uuid5(UUID(run_id), "ep-d2-eligible-project").hex
    completed_id = uuid5(UUID(run_id), "ep-d2-completed-project").hex
    manifest_path.write_text(canonical_json({
        "schema_version": "reagent.ep-d2-controlled-fixtures/v0.1",
        "run_id": run_id,
        "eligible": _seed_ep_d2_project(
            base_url, eligible_id, manifest_path,
            project_name="EP-D2 eligible Review",
            with_completed_revision=False,
        ),
        "completed": _seed_ep_d2_project(
            base_url, completed_id, manifest_path,
            project_name="EP-D2 completed product width",
            with_completed_revision=True,
        ),
    }) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--project-name")
    parser.add_argument("--research-topic")
    parser.add_argument(
        "--scenario", choices=("b0", "fe-m-desktop", "ep-d2-u1", "ep-d2"), default="b0"
    )
    arguments = parser.parse_args()
    if arguments.scenario == "ep-d2":
        seed_ep_d2(arguments.api_url.rstrip("/"), arguments.run_id, arguments.manifest)
        return
    seed(
        arguments.api_url.rstrip("/"), arguments.run_id, arguments.manifest,
        project_name=arguments.project_name, research_topic=arguments.research_topic,
        scenario=arguments.scenario,
    )
if __name__ == "__main__":
    main()
