"""Seed the four contract-bounded states for B0 browser qualification."""
from __future__ import annotations
import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
from backend.artifact_references.contracts import ArtifactReference, ArtifactState
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
    package_id = f"b0-fixture-{run_id}-{instance['workflow_definition_id']}"
    package_checksum = canonical_hash({"schema_version": "reagent.b0-package-reference/v0.1",
        "run_id": run_id, "workflow_instance_id": instance["workflow_instance_id"]})
    report = ProgressReportV2.create(
        package_id=package_id, package_schema_version="workflow-package/v0.1",
        package_checksum=package_checksum, project_id=project_id,
        workflow_id=instance["workflow_definition_id"], workflow_version=instance["workflow_version"],
        workflow_checksum=workflow_checksum, execution_round=1,
        harness_type="b0-controlled-fixture", harness_version="0.1.0",
        harness_session_id=f"b0-{instance['workflow_definition_id']}",
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
def seed(base_url: str, run_id: str, manifest_path: Path) -> None:
    project_name = f"B0 controlled {run_id}"
    project = _request(base_url, "/projects", {"name": project_name,
        "research_topic": "Disposable browser qualification only",
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
            media_type="application/json", state=ArtifactState.METADATA_ONLY,
            relative_path=output.relative_path, content_checksum=artifact_checksum, size_bytes=0,
            cloud_metadata_available=True, produced_at=now, retired_at=None, created_at=now,
            updated_at=now))
        uow.commit()
        _upload(service, run_id, project_id, instances[WORKFLOWS[1]], checksums[WORKFLOWS[1]],
                ProgressStatus.BLOCKED, "Blocked until an exact controlled input is available.",
                "2026-08-14T01:02:00Z")
        _upload(service, run_id, project_id, instances[WORKFLOWS[2]], checksums[WORKFLOWS[2]],
                ProgressStatus.BLOCKED,
                "Awaiting owner action before any scaffold Writing activity.",
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
    progress = _request(base_url, f"/projects/{project_id}/progress")
    by_workflow = {item["workflow_definition_id"]: item for item in progress["instances"]}
    expected = dict(zip(WORKFLOWS, ("COMPLETED", "BLOCKED", "BLOCKED", "NOT_STARTED")))
    if len(progress["instances"]) != 4 or any(
            by_workflow[key]["research_status"] != value for key, value in expected.items()):
        raise RuntimeError("B0 fixture states do not match the approved mapping")
    completed, mismatch = by_workflow[WORKFLOWS[0]], by_workflow[WORKFLOWS[3]]
    if len(completed["artifact_metadata"]) != 1 or completed["result_count"] != 1:
        raise RuntimeError("B0 completion lacks its single metadata-only Artifact reference")
    if progress["dependency_edges"]:
        raise RuntimeError("B0 fixture must not create Artifact dependency bindings")
    if mismatch["installation_state"] != "ACKNOWLEDGED_STALE":
        raise RuntimeError("B0 fixture lacks a proven stale local/Cloud installation")
    if "Awaiting owner action" not in by_workflow[WORKFLOWS[2]]["latest_summary"]:
        raise RuntimeError("B0 owner-action state is not observable")
    manifest_path.write_text(canonical_json({
        "schema_version": "reagent.b0-controlled-fixtures/v0.1", "run_id": run_id,
        "project_id": project_id, "project_name": project_name,
        "workspace_id": manifest["workspace_id"], "manifest_revision": progress["manifest_revision"],
        "instances": {key: value["workflow_instance_id"] for key, value in instances.items()}
    }) + "\n", encoding="utf-8")
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    arguments = parser.parse_args()
    seed(arguments.api_url.rstrip("/"), arguments.run_id, arguments.manifest)
if __name__ == "__main__":
    main()
