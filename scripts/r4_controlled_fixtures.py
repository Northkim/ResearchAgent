"""Seed two exact Literature results for controlled R4 browser qualification."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid5

from backend.artifact_references.contracts import ArtifactReference, ArtifactState
from backend.artifact_references.service import ArtifactReferenceService
from backend.database import (
    SQLAlchemyUnitOfWork,
    create_postgres_engine,
    create_session_factory,
)
from backend.progress_reports.contracts import OutputArtifactReference, ProgressStatus
from backend.progress_reports.service import ProgressReportService
from backend.project_workspaces.workspace_cli import _project_artifact_presentation
from backend.research.adapters import LocalFilesystemArtifactStorage
from backend.workflow_packages.serialization import canonical_json, sha256_bytes
from scripts.b0_controlled_fixtures import _report_selected_paper_count, _request, _upload


LITERATURE_ID = "literature-search-local-experimental"
CONSOLIDATION_ID = "literature-consolidation-local-experimental"
IDEA_ID = "idea-discovery-local-experimental"


def _candidate(identifier: str, title: str, *, doi: str | None = None) -> dict:
    return {
        "candidate_id": f"candidate-{identifier * 16}",
        "provider_id": f"provider-{identifier}",
        "openalex_id": f"https://openalex.org/W{identifier * 8}",
        "title": title,
        "authors": ["Controlled Researcher"],
        "publication_year": 2026,
        "doi": doi,
        "source": "Controlled venue",
        "language": "en",
        "abstract": "Controlled bounded abstract evidence.",
        "source_query_ids": ["query-1"],
        "provenance_checksum": "sha256:" + identifier * 64,
        "deduplication_status": "UNIQUE",
    }


def _library(*candidates: dict) -> bytes:
    return (canonical_json({
        "schema": "selected-paper-library/v1",
        "source_schemas": ["candidate-papers/v0.2", "selected-papers/v0.2"],
        "source_checksums": {
            "candidate_papers": "sha256:" + "a" * 64,
            "selected_papers": "sha256:" + "b" * 64,
        },
        "papers": [{
            "candidate_id": item["candidate_id"],
            "paper": item,
            "selection": {
                "relevance_decision": "INCLUDE",
                "inclusion_reason": "Controlled exact source selection.",
                "evidence_availability": "METADATA_AND_ABSTRACT",
            },
        } for item in candidates],
    }) + "\n").encode("utf-8")


def seed(base_url: str, project_id: str, run_id: str, manifest_path: Path) -> None:
    page = _request(base_url, f"/projects/{project_id}/workflow-instances")
    literature = [
        item for item in page["items"]
        if item["workflow_definition_id"] == LITERATURE_ID
    ]
    consolidation = [
        item for item in page["items"]
        if item["workflow_definition_id"] == CONSOLIDATION_ID
    ]
    idea = [
        item for item in page["items"]
        if item["workflow_definition_id"] == IDEA_ID
    ]
    if len(literature) != 2 or len(consolidation) != 1 or len(idea) != 1:
        raise RuntimeError("R4 browser fixture requires two Literature, one consolidation, and one Idea")

    catalog = _request(base_url, "/workflow-definitions")
    checksums = {
        item["workflow_definition_id"]: item["recommended_version"]["contract_checksum"]
        for item in catalog["items"]
        if item["workflow_definition_id"] == LITERATURE_ID
    }
    if set(checksums) != {LITERATURE_ID}:
        raise RuntimeError("R4 Literature publication identity is unavailable")

    engine = create_postgres_engine(os.environ["REAGENT_DATABASE_URL"])
    uow = SQLAlchemyUnitOfWork(create_session_factory(engine))
    by_instance = {item["workflow_instance_id"]: item for item in page["items"]}

    def resolve(envelope, normalized, requested):
        item = by_instance.get(requested or "")
        if item is None or envelope.project_id != project_id:
            raise ValueError("R4 fixture Progress is outside the controlled Project")
        if normalized is not None and (
            normalized.workflow_id != item["workflow_definition_id"]
            or normalized.workflow_version != item["workflow_version"]
        ):
            raise ValueError("R4 fixture Progress Workflow identity mismatch")
        return item["workflow_instance_id"]

    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    progress = ProgressReportService(
        repository=uow.progress_reports,
        content_storage=LocalFilesystemArtifactStorage(manifest_path.parent / "progress-originals"),
        commit_callback=uow.commit,
        workflow_identity_resolver=resolve,
        clock=lambda: now,
    )
    artifacts = ArtifactReferenceService(unit_of_work=uow, clock=lambda: now)
    duplicate = _candidate("c", "Shared exact paper", doi="10.1000/shared")
    contents = (
        _library(_candidate("a", "Base evidence paper", doi="10.1000/base"), duplicate),
        _library(duplicate, _candidate("b", "Additional context paper")),
    )
    manifest_artifacts = []
    try:
        for index, (producer, content) in enumerate(zip(literature, contents, strict=True), 1):
            checksum = sha256_bytes(content)
            relative_path = (
                "outputs/artifacts/selected-paper-library/"
                f"sha256-{checksum[7:]}.json"
            )
            output = OutputArtifactReference(
                relative_path=relative_path,
                artifact_kind="selected-paper-library/v1",
                media_type="application/json",
                checksum=checksum,
                size=len(content),
            )
            receipt, report = _upload(
                progress,
                run_id,
                project_id,
                producer,
                checksums[LITERATURE_ID],
                ProgressStatus.COMPLETED,
                "Controlled exact Literature result for explicit composition.",
                f"2026-08-20T12:0{index}:00Z",
                (output,),
            )
            artifact_id = "artifact-" + uuid5(
                UUID(run_id), f"r4-literature-{index}"
            ).hex
            produced = datetime(2026, 8, 20, 12, index, tzinfo=timezone.utc)
            uow.artifact_references.add_artifact(ArtifactReference(
                artifact_id=artifact_id,
                project_id=project_id,
                producer_workflow_instance_id=producer["workflow_instance_id"],
                producer_progress_receipt_id=receipt.receipt_id,
                producer_progress_report_id=report.report_id,
                producer_execution_round=1,
                producer_capsule_id=producer["capsule_id"],
                producer_capsule_version=producer["capsule_version"],
                artifact_type="selected-paper-library/v1",
                artifact_schema_version="selected-paper-library/v1",
                media_type="application/json",
                state=ArtifactState.LOCAL_AVAILABLE,
                relative_path=relative_path,
                content_checksum=checksum,
                size_bytes=len(content),
                cloud_metadata_available=True,
                produced_at=produced,
                retired_at=None,
                created_at=produced,
                updated_at=produced,
            ))
            uow.commit()
            _report_selected_paper_count(
                artifacts,
                project_id=project_id,
                artifact_id=artifact_id,
                artifact_checksum=checksum,
                selected_count=2,
            )
            payload = _project_artifact_presentation(
                artifact={
                    "artifact_id": artifact_id,
                    "artifact_type": "selected-paper-library/v1",
                    "content_checksum": checksum,
                },
                content=content,
            )
            assert payload is not None
            artifacts.report_presentation(
                project_id=project_id,
                artifact_id=artifact_id,
                payload=payload,
            )
            manifest_artifacts.append({
                "artifact_id": artifact_id,
                "artifact_checksum": checksum,
                "producer_workflow_instance_id": producer["workflow_instance_id"],
                "relative_path": relative_path,
                "content": content.decode("utf-8"),
            })
    finally:
        uow.close()
        engine.dispose()

    manifest_path.write_text(canonical_json({
        "schema_version": "reagent.r4-controlled-fixture/v0.1",
        "project_id": project_id,
        "instances": {
            "literature": [item["workflow_instance_id"] for item in literature],
            "consolidation": consolidation[0]["workflow_instance_id"],
            "idea": idea[0]["workflow_instance_id"],
        },
        "artifacts": manifest_artifacts,
    }) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    seed(args.api_url.rstrip("/"), args.project_id, args.run_id, args.manifest)


if __name__ == "__main__":
    main()
