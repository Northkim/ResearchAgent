"""Seed the smallest deterministic dataset for B0 browser qualification."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from backend.progress_reports.contracts import (
    ACCEPTED_REPORT_MEDIA_TYPE,
    EXPERIMENTAL_DECLARATION,
    OutputArtifactReference,
    PinReference,
    ProgressReportUploadEnvelope,
    ProgressReportV2,
    ProgressStatus,
)
from backend.project_workspaces import workspace_cli
from backend.workflow_packages.serialization import canonical_json, sha256_bytes

HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64
NAMESPACE = uuid.UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966")
TIMES = {
    "literature-search-local-experimental": "2026-08-14T01:01:00Z",
    "idea-discovery-local-experimental": "2026-08-14T01:02:00Z",
    "writing-local-experimental": "2026-08-14T01:03:00Z",
    "reproduction-experiment-local-experimental": "2026-08-14T01:04:00Z",
}


def _request(base_url: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else canonical_json(payload).encode("utf-8")
    request = urllib.request.Request(
        base_url + path,
        data=data,
        method="GET" if payload is None else "POST",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"fixture API failed: {path}: {error.code}: {detail}") from error


def _artifact(root: Path, artifact_type: str, content: dict) -> tuple[OutputArtifactReference, dict]:
    body = (canonical_json(content) + "\n").encode("utf-8")
    checksum = sha256_bytes(body)
    slug = artifact_type.split("/", 1)[0]
    relative_path = f"outputs/artifacts/{slug}/sha256-{checksum[7:]}.json"
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    output = OutputArtifactReference(
        relative_path=relative_path,
        artifact_kind=artifact_type,
        media_type="application/json",
        checksum=checksum,
        size=len(body),
    )
    return output, {
        "artifact_type": artifact_type,
        "artifact_schema_version": artifact_type,
        "media_type": "application/json",
        "relative_path": relative_path,
        "content_checksum": checksum,
        "size_bytes": len(body),
    }


def _report(
    *, project_id: str, manifest: dict, status: ProgressStatus, state: str,
    output: OutputArtifactReference | None,
) -> ProgressReportV2:
    workflow_id = manifest["workflow_id"]
    completed_at = TIMES[workflow_id]
    return ProgressReportV2.create(
        package_id=manifest["package_id"],
        package_schema_version=manifest["package_schema_version"],
        package_checksum=manifest["package_checksum"],
        project_id=project_id,
        workflow_id=workflow_id,
        workflow_version=manifest["workflow_version"],
        workflow_checksum=manifest["workflow_checksum"],
        execution_round=1,
        harness_type="b0-controlled-fixture",
        harness_version="0.1.0",
        harness_session_id=f"b0-{workflow_id}",
        previous_report_id=None,
        previous_report_checksum=None,
        started_at=completed_at,
        completed_at=completed_at,
        status=status,
        completed_work=(state,),
        current_state=state,
        next_recommended_action="Wait for the owner to choose the next explicit action.",
        continuation_reason=None,
        output_artifacts=(() if output is None else (output,)),
        context_before_checksum=HASH_A,
        context_after_checksum=HASH_B,
        warnings=(),
        errors=(),
        unresolved_questions=(() if status is ProgressStatus.COMPLETED else ("Owner action is required.",)),
        continuation_instructions=("Use only this synthetic controlled fixture.",),
        skill_pins=(PinReference("SKILL", "b0-controlled-skill", "0.1.0", HASH_A),),
        template_pins=(PinReference("TEMPLATE", "b0-controlled-template", "0.1.0", HASH_B),),
        generated_at=completed_at,
        experimental_declaration=EXPERIMENTAL_DECLARATION,
    )


def _upload(
    base_url: str, project_id: str, instance: dict, root: Path,
    status: ProgressStatus, state: str, artifact_type: str | None = None,
    content: dict | None = None,
) -> str | None:
    manifest = json.loads((root / "package-manifest.json").read_text(encoding="utf-8"))
    output = declaration = None
    if artifact_type is not None and content is not None:
        output, declaration = _artifact(root, artifact_type, content)
    report = _report(
        project_id=project_id, manifest=manifest, status=status,
        state=state, output=output,
    )
    report_bytes = (canonical_json(report) + "\n").encode("utf-8")
    report_path = root / f"memory/progress/reports/{report.report_id}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(report_bytes)
    envelope = ProgressReportUploadEnvelope.create(
        original_report_bytes=report_bytes,
        project_id=project_id,
        package_id=manifest["package_id"],
        package_checksum=manifest["package_checksum"],
        report_schema_version=report.schema_version,
        report_id=report.report_id,
        report_checksum=report.report_checksum,
        original_report_media_type=ACCEPTED_REPORT_MEDIA_TYPE,
        uploaded_at=report.completed_at,
        uploader_type="b0-controlled-fixture",
        client_version="b0-controlled-fixture/0.1.0",
        source_path_hint=report_path.relative_to(root).as_posix(),
        context_snapshot_metadata=None,
    )
    payload = envelope.to_dict()
    payload["workflow_instance_id"] = instance["workflow_instance_id"]
    payload["artifact_declarations"] = []
    if declaration is not None:
        artifact_id = "artifact-" + uuid.uuid5(
            NAMESPACE,
            "production-artifact/v1|package=" + manifest["package_id"]
            + "|report=" + report.report_id + "|path=" + declaration["relative_path"]
            + "|checksum=" + declaration["content_checksum"],
        ).hex
        payload["artifact_declarations"] = [{
            "artifact_id": artifact_id,
            **declaration,
            "produced_at": report.completed_at,
        }]
    _request(base_url, f"/projects/{project_id}/progress-reports", payload)
    return None if declaration is None else payload["artifact_declarations"][0]["artifact_id"]


def seed(base_url: str, workspace: Path, manifest_path: Path) -> None:
    project = _request(base_url, "/projects", {
        "name": "B0 controlled UX audit",
        "research_topic": "Synthetic browser-runtime qualification only",
        "selected_workflow": "LITERATURE_SEARCH",
        "workflow_setup": "full-research",
        "custom_workflow_definition_ids": [],
    })
    project_id = project["project_id"]
    bootstrap = _request(base_url, f"/projects/{project_id}/workspace-bootstrap")
    workspace_cli.bootstrap_workspace(target=workspace, descriptor=bootstrap)
    sync = workspace_cli.sync_workspace(
        workspace_root=workspace,
        transport=workspace_cli.HTTPWorkspaceSyncTransport(base_url),
    )
    if sync.status != "SYNCED" or sync.acknowledgement_status != "ACKNOWLEDGED":
        raise RuntimeError("disposable Workspace did not reach an acknowledged sync state")
    lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text(encoding="utf-8"))
    instances = {item["workflow_definition_id"]: item for item in lock["installed_capsules"]}
    roots = {key: workspace / item["relative_path"] for key, item in instances.items()}

    library_id = _upload(
        base_url, project_id, instances["literature-search-local-experimental"],
        roots["literature-search-local-experimental"], ProgressStatus.COMPLETED,
        "Synthetic literature fixture completed; output metadata is available.",
        "selected-paper-library/v1", {"schema": "selected-paper-library/v1", "papers": []},
    )
    idea_id = _upload(
        base_url, project_id, instances["idea-discovery-local-experimental"],
        roots["idea-discovery-local-experimental"], ProgressStatus.COMPLETED,
        "Synthetic idea fixture completed after explicit fixture selection.",
        "selected-research-idea/v1",
        {"schema": "selected-research-idea/v1", "selected_idea": {"title": "Synthetic direction"}},
    )
    assert library_id and idea_id
    writing = instances["writing-local-experimental"]["workflow_instance_id"]
    for index, (key, artifact_id) in enumerate(
        (("research_idea", idea_id), ("literature_library", library_id)), 1
    ):
        _request(base_url, f"/projects/{project_id}/workflow-instances/{writing}/artifact-dependencies", {
            "requirement_key": key,
            "artifact_id": artifact_id,
            "idempotency_key": f"00000000-0000-4000-8000-{index:012d}",
            "replace_binding_id": None,
        })
    _upload(
        base_url, project_id, instances["writing-local-experimental"],
        roots["writing-local-experimental"], ProgressStatus.BLOCKED,
        "Awaiting owner confirmation before any scaffold Writing action.",
    )
    _upload(
        base_url, project_id, instances["reproduction-experiment-local-experimental"],
        roots["reproduction-experiment-local-experimental"], ProgressStatus.BLOCKED,
        "Blocked until the owner selects an exact synthetic input; no experiment ran.",
    )
    catalog = _request(base_url, "/workflow-definitions")
    literature = next(item for item in catalog["items"] if item["workflow_definition_id"] == "literature-search-local-experimental")
    _request(base_url, f"/projects/{project_id}/workflow-instances", {
        "workflow_definition_id": literature["workflow_definition_id"],
        "workflow_version": literature["recommended_version"]["version"],
        "capsule_id": literature["recommended_capsule"]["capsule_id"],
        "capsule_version": literature["recommended_capsule"]["capsule_version"],
        "display_name": "B0 stale-sync marker",
        "base_revision": 1,
    })
    progress = _request(base_url, f"/projects/{project_id}/progress")
    by_workflow = {item["workflow_definition_id"]: item for item in progress["instances"] if item["instance_display_name"] != "B0 stale-sync marker"}
    manifest_path.write_text(canonical_json({
        "schema_version": "reagent.b0-controlled-fixtures/v0.1",
        "project_id": project_id,
        "workspace_id": bootstrap["workspace_id"],
        "manifest_revision": progress["manifest_revision"],
        "instances": {key: value["workflow_instance_id"] for key, value in by_workflow.items()},
    }) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    arguments = parser.parse_args()
    seed(arguments.api_url.rstrip("/"), arguments.workspace, arguments.manifest)


if __name__ == "__main__":
    main()
