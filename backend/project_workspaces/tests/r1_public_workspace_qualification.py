"""Controlled public Workspace qualification for the bounded Real Review R1.

The fixtures are synthetic software-path evidence, not scientific evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import httpx

from backend.artifact_references.research_flow_contracts import (
    validate_manuscript_draft_v2,
    validate_review_report_v2,
)
from backend.artifact_references.tests.test_research_flow_contracts import (
    CANDIDATE_A,
    _library,
    _selected,
)
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.production_workflows import (
    REAL_REVIEW_CAPSULE_CHECKSUM,
    REAL_REVIEW_CAPSULE_ID,
    REAL_WRITING_CAPSULE_ID,
)
from backend.project_workspaces.tests.test_f1b_full_scaffold_flow import _seed_upstream
from backend.project_workspaces.tests.test_owner_real_research_gate import _loopback_server
from backend.project_workspaces.tests.w1_public_workspace_qualification import (
    _add_instance,
    _bind,
    _clean_environment,
    _qualification_app,
    _real_codex_wrapper,
    _run_public_pty,
)
from backend.workflow_packages.serialization import canonical_hash, canonical_json

WORKFLOW_ID = "review-local-experimental"
WORKFLOW_VERSION = "0.3.0"
CAPSULE_VERSION = "0.5.0"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _reference(artifact: dict[str, str], artifact_type: str) -> dict[str, str]:
    return {
        "artifact_id": artifact["artifact_id"],
        "artifact_type": artifact_type,
        "sha256": artifact["content_checksum"],
    }


def _evidence_ref(source: dict[str, str], item: str, limitation: str | None = None) -> dict:
    return {
        **source,
        "evidence_item": item,
        "location": item,
        "availability": "LIMITED" if limitation else "AVAILABLE",
        "limitation": limitation,
    }


def _manuscript(
    idea: dict[str, str], library: dict[str, str], *, seeded_issue: bool,
) -> dict:
    sources = {
        "research_idea": idea,
        "literature_library": library,
        "experiment_record": None,
    }
    title = "Controlled Overbroad Draft" if seeded_issue else "Controlled Bounded Draft"
    brief = {
        "document_type": "initial research manuscript",
        "working_title": title,
        "target_audience": "research owner",
        "target_words": {"minimum": 300, "maximum": 1200},
        "requested_sections": ["Introduction", "Proposed Method", "Results"],
        "citation_style": "numeric",
        "abstract_requested": False,
        "owner_constraints": ["Do not fabricate results"],
    }
    evidence_map = [
        {
            "section": "Introduction",
            "support_status": "SUPPORTED",
            "evidence_refs": [_evidence_ref(
                library, CANDIDATE_A, "Abstract-level evidence only",
            )],
            "limitations": ["No full text"],
        },
        {
            "section": "Proposed Method",
            "support_status": "PLANNED",
            "evidence_refs": [_evidence_ref(
                idea, "selected_idea.proposed_direction",
            )],
            "limitations": [],
        },
        {
            "section": "Results",
            "support_status": "UNAVAILABLE",
            "evidence_refs": [],
            "limitations": ["No Experiment bound"],
        },
    ]
    outline_value = [
        {"heading": item["section"], "support_status": item["support_status"]}
        for item in evidence_map
    ]
    outline = {"sha256": canonical_hash(outline_value), "value": outline_value}
    approval_payload = {
        "outline_sha256": outline["sha256"],
        "brief_sha256": canonical_hash(brief),
        "evidence_map_sha256": canonical_hash(evidence_map),
        "source_artifacts_sha256": canonical_hash(sources),
        "approved_at": "2026-08-15T00:00:00Z",
        "decision": "APPROVED",
    }
    claim_text = (
        "All research systems always improve every scientific outcome."
        if seeded_issue
        else "The selected abstract reports a bounded observation."
    )
    citations = [{
        "citation_id": "cite-1",
        "paper_id": CANDIDATE_A,
        "source_artifact": library,
        "evidence_scope": "ABSTRACT",
        "reference_markdown": "[1] Controlled synthetic paper.",
    }]
    claims = [
        {
            "claim_id": "claim-1",
            "claim_type": "LITERATURE",
            "section": "Introduction",
            "claim_text": claim_text,
            "support_status": "SUPPORTED",
            "evidence_refs": [_evidence_ref(
                library, CANDIDATE_A, "Abstract-level evidence only",
            )],
            "citation_ids": ["cite-1"],
            "limitations": ["No full text"],
        },
        {
            "claim_id": "claim-2",
            "claim_type": "PROPOSAL",
            "section": "Proposed Method",
            "claim_text": "The study will evaluate the proposed comparison.",
            "support_status": "PLANNED",
            "evidence_refs": [_evidence_ref(
                idea, "selected_idea.proposed_direction",
            )],
            "citation_ids": [],
            "limitations": [],
        },
        {
            "claim_id": "claim-3",
            "claim_type": "RESULT",
            "section": "Results",
            "claim_text": "Observed results are unavailable.",
            "support_status": "UNAVAILABLE",
            "evidence_refs": [],
            "citation_ids": [],
            "limitations": ["No Experiment bound"],
        },
    ]
    content = (
        f"# {title}\n\n## Introduction\n{claim_text} [1]\n\n"
        "## Proposed Method\nThe study will evaluate the proposed comparison.\n\n"
        "## Results\nObserved results are unavailable; no result is claimed.\n\n"
        "## References\n[1] Controlled synthetic paper.\n"
    )
    draft_sha = canonical_hash({
        "title": title,
        "content_markdown": content,
        "claims": claims,
        "citations": citations,
    })
    review_payload = {
        "draft_sha256": draft_sha,
        "reviewed_at": "2026-08-15T00:05:00Z",
        "decision": "APPROVED",
    }
    return validate_manuscript_draft_v2({
        "schema": "manuscript-draft/v2",
        "core_capability_maturity": "REVIEWED_CORE",
        "producer": {
            "workflow_instance_id": "wfi-" + ("1" if seeded_issue else "2") * 32,
            "capsule_id": REAL_WRITING_CAPSULE_ID,
            "capsule_version": "0.5.0",
            "execution_round": 1,
        },
        "source_artifacts": sources,
        "writing_brief": brief,
        "evidence_map": evidence_map,
        "approved_outline": outline,
        "outline_approval": {
            "sha256": canonical_hash(approval_payload), **approval_payload,
        },
        "title": title,
        "content_markdown": content,
        "claims": claims,
        "citations": citations,
        "experiment_evidence_available": False,
        "unsupported_areas": ["Results"],
        "limitations": ["Controlled synthetic evidence only"],
        "owner_review": {
            "sha256": canonical_hash(review_payload), **review_payload,
        },
    })


def _fake_harness(root: Path) -> Path:
    path = root / "controlled-fake-review-codex"
    path.write_text(
        "#!/usr/bin/env python3\nimport json,pathlib,sys\n"
        "root=pathlib.Path.cwd(); instruction=sys.argv[-1]\n"
        "load=lambda p:json.loads((root/p).read_text()); dump=lambda p,v:(root/p).write_text(json.dumps(v,sort_keys=True,separators=(',',':'))+'\\n')\n"
        "sources=load('memory/input-provenance.json')['artifacts']; manuscript=load('inputs/manuscript-draft.json')\n"
        "ref=lambda s,i:{**s,'evidence_item':i,'location':i,'availability':'LIMITED','limitation':'Abstract-level evidence only'}\n"
        "if 'INPUT_REVIEW AND REVIEW_SCOPE' in instruction:\n"
        " support=[sources[k] for k in ('research_idea','literature_library','experiment_record') if k in sources]\n"
        " scope={'manuscript_identity':sources['manuscript'],'available_evidence':support,'categories':['EVIDENCE_SUPPORT','CLAIM_SCOPE','CITATION','METHOD_CONSISTENCY','RESULT_SUPPORT','REPRODUCIBILITY'],'known_evidence_limitations':['Literature is abstract-level only'],'owner_focus':[]}\n"
        " dump('memory/review-scope.json',scope)\n"
        "else:\n"
        " seeded='Overbroad' in manuscript['title']\n"
        " issues=[]\n"
        " if seeded: issues=[{'issue_id':'issue-claim-scope','category':'CLAIM_SCOPE','severity':'MAJOR','target':{'section':'Introduction','claim_id':'claim-1'},'summary':'The universal claim exceeds the selected abstract evidence.','evidence_refs':[ref(sources['literature_library'],manuscript['citations'][0]['paper_id'])],'recommended_action':'Narrow the claim to the bounded abstract-level observation.','blocking':True}]\n"
        " result={'assessment':'REVISION_REQUIRED' if seeded else 'NO_BLOCKING_ISSUES','summary':'A bounded revision is required.' if seeded else 'No blocking evidence-contract issue was identified within the bounded scope.','issues':issues,'limitations':['Synthetic controlled audit only']}\n"
        " dump('memory/review-result.json',result); (root/'outputs/review.md').write_text('# Controlled Review\\n\\n'+result['summary']+'\\n')\n",
        encoding="utf-8",
    )
    path.chmod(0o700)
    return path


def _qualify(root: Path, *, real_codex: bool = False) -> dict[str, str]:
    database = InMemoryDatabase()
    uow_factory = lambda: InMemoryUnitOfWork(database)
    app = _qualification_app(root, database)
    with _loopback_server(app) as base_url, httpx.Client(
        base_url=base_url, timeout=30,
    ) as client:
        created = client.post("/projects", json={
            "name": "R1 controlled synthetic qualification",
            "research_topic": "Bounded evidence audit",
            "selected_workflow": "LITERATURE_SEARCH",
            "workflow_setup": "full-research",
        })
        _require(created.status_code == 201, created.text)
        project_id = created.json()["project_id"]
        initial = client.get(
            f"/projects/{project_id}/workflow-instances"
        ).json()["items"]
        literature_instance = next(item for item in initial if item[
            "workflow_definition_id"] == "literature-search-local-experimental"
        )
        idea_instance = next(item for item in initial if item[
            "workflow_definition_id"] == "idea-discovery-local-experimental"
        )
        writing_issue = _add_instance(
            client, project_id, "writing-local-experimental", "0.3.0",
            REAL_WRITING_CAPSULE_ID, "0.5.0", 1,
        )
        writing_clean = _add_instance(
            client, project_id, "writing-local-experimental", "0.3.0",
            REAL_WRITING_CAPSULE_ID, "0.5.0", 2,
        )
        review_issue = _add_instance(
            client, project_id, WORKFLOW_ID, WORKFLOW_VERSION,
            REAL_REVIEW_CAPSULE_ID, CAPSULE_VERSION, 3,
        )
        review_clean = _add_instance(
            client, project_id, WORKFLOW_ID, WORKFLOW_VERSION,
            REAL_REVIEW_CAPSULE_ID, CAPSULE_VERSION, 4,
        )
        descriptor = client.get(f"/projects/{project_id}/workspace-bootstrap").json()
        workspace = root / "workspace"
        workspace_cli.bootstrap_workspace(target=workspace, descriptor=descriptor)
        transport = workspace_cli.HTTPWorkspaceSyncTransport(base_url)
        _require(
            workspace_cli.sync_workspace(
                workspace_root=workspace, transport=transport,
            ).status == "SYNCED",
            "Workspace sync failed",
        )
        lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
        roots = {
            item["workflow_instance_id"]: workspace / item["relative_path"]
            for item in lock["installed_capsules"]
        }
        library_content = _library()
        selected_idea, _ = _selected()
        library_artifact = _seed_upstream(
            uow_factory=uow_factory, project_id=project_id,
            instance=literature_instance,
            root=roots[literature_instance["workflow_instance_id"]],
            artifact_type="selected-paper-library/v1", content=library_content,
            character="a",
        )
        idea_artifact = _seed_upstream(
            uow_factory=uow_factory, project_id=project_id,
            instance=idea_instance,
            root=roots[idea_instance["workflow_instance_id"]],
            artifact_type="selected-research-idea/v1", content=selected_idea,
            character="b",
        )
        idea_ref = _reference(idea_artifact, "selected-research-idea/v1")
        library_ref = _reference(library_artifact, "selected-paper-library/v1")
        issue_manuscript = _manuscript(idea_ref, library_ref, seeded_issue=True)
        clean_manuscript = _manuscript(idea_ref, library_ref, seeded_issue=False)
        issue_artifact = _seed_upstream(
            uow_factory=uow_factory, project_id=project_id,
            instance=writing_issue, root=roots[writing_issue["workflow_instance_id"]],
            artifact_type="manuscript-draft/v2", content=issue_manuscript,
            character="c",
        )
        clean_artifact = _seed_upstream(
            uow_factory=uow_factory, project_id=project_id,
            instance=writing_clean, root=roots[writing_clean["workflow_instance_id"]],
            artifact_type="manuscript-draft/v2", content=clean_manuscript,
            character="d",
        )
        workspace_cli.refresh_artifact_index(
            workspace_root=workspace, transport=transport,
        )
        for review, manuscript_artifact in (
            (review_issue, issue_artifact), (review_clean, clean_artifact),
        ):
            _bind(client, project_id, review, "manuscript", manuscript_artifact)
            _bind(client, project_id, review, "research_idea", idea_artifact)
            _bind(client, project_id, review, "literature_library", library_artifact)
            materialized = workspace_cli.materialize_artifacts(
                workspace_root=workspace,
                consumer_workflow_instance_id=review["workflow_instance_id"],
                transport=transport,
            )
            _require(
                materialized.materialized_count == 3,
                "exact Review inputs were not materialized",
            )
        harness = _fake_harness(root)
        if real_codex:
            executable = shutil.which("codex")
            _require(executable is not None, "Codex executable is unavailable")
            harness = _real_codex_wrapper(root, Path(executable).resolve(strict=True))
        root_cli = workspace / "reagent_local.py"
        environment = _clean_environment()
        artifacts: dict[str, str] = {}
        journeys = ((review_issue, True),) if real_codex else (
            (review_issue, True), (review_clean, False),
        )
        for review, expected_revision in journeys:
            capsule = roots[review["workflow_instance_id"]]
            workspace_cli._verify_locked_capsules(workspace, lock, descriptor)
            workspace_cli._scan_capsule_for_credentials(capsule)
            output = _run_public_pty([
                sys.executable, str(root_cli), "run", str(workspace),
                "--workflow-instance", review["workflow_instance_id"],
                "--api-url", base_url,
                "--codex-executable", str(harness), "--json",
            ], cwd=workspace, environment=environment,
                timeout_seconds=900.0 if real_codex else 120.0)
            _require("RUN_COMPLETED" in output, f"public Review run failed:\n{output}")
            reports = list((capsule / "memory/progress/reports").glob("prv2-*.json"))
            _require(len(reports) == 1, "Review Progress was not finalized exactly once")
            current = json.loads((capsule / "memory/current-artifact.json").read_text())
            artifact = json.loads((capsule / current["relative_path"]).read_text())
            validate_review_report_v2(
                artifact,
                manuscript=issue_manuscript if expected_revision else clean_manuscript,
                bound_inputs={
                    "manuscript": artifact["source_manuscript"],
                    "research_idea": idea_ref,
                    "literature_library": library_ref,
                    "experiment_record": None,
                },
            )
            _require(
                artifact["assessment"] == (
                    "REVISION_REQUIRED" if expected_revision else "NO_BLOCKING_ISSUES"
                ),
                "bounded Review assessment is wrong",
            )
            if expected_revision:
                _require(
                    any(issue["target"] == {
                        "section": "Introduction", "claim_id": "claim-1",
                    } for issue in artifact["issues"]),
                    "seeded claim-scope inconsistency was not anchored",
                )
            prohibited = ("WEAK_ACCEPT", "ACCEPT", "REJECT", "scientific score")
            _require(
                not any(token.lower() in canonical_json(artifact).lower() for token in prohibited),
                "Review emitted prohibited publication semantics",
            )
            cloud = client.get(
                f"/projects/{project_id}/artifacts",
                params={"workflow_instance_id": review["workflow_instance_id"]},
            ).json()["artifacts"]
            _require(
                len(cloud) == 1
                and cloud[0]["artifact_type"] == "review-report/v2"
                and cloud[0]["producer_capsule_id"] == REAL_REVIEW_CAPSULE_ID
                and cloud[0]["content_checksum"] == current["checksum"],
                "Cloud did not promote exact review-report/v2",
            )
            progress = client.get(
                f"/projects/{project_id}/workflow-instances/"
                f"{review['workflow_instance_id']}/progress"
            ).json()
            _require(
                progress["history_total"] == 1
                and progress["projection"]["research_status"] == "COMPLETED"
                and progress["projection"]["result_count"] == 1,
                "Cloud Review Progress is not completed exactly once",
            )
            artifacts["revision_required" if expected_revision else "clean"] = current["checksum"]
        return {
            "project_id": project_id,
            **artifacts,
            "capsule_checksum": REAL_REVIEW_CAPSULE_CHECKSUM,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-codex", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="reagent-r1-public-qualification-") as temporary:
        root = Path(temporary)
        evidence = _qualify(root, real_codex=args.real_codex)
    _require(not root.exists(), "temporary R1 qualification state was not removed")
    print("R1_PUBLIC_WORKSPACE_QUALIFICATION=PASS")
    print("CONTROLLED_REVISION_REQUIRED=PASS")
    print(
        "CONTROLLED_CLEAN=NOT_RUN_IN_REAL_CODEX_MODE"
        if args.real_codex else "CONTROLLED_CLEAN=PASS"
    )
    print("REVIEW_REPORT_V2=PASS")
    print("PROGRESS_EXACTLY_ONCE=PASS")
    print("CLOUD_PROJECTION=PASS")
    print("TEMPORARY_STATE_REMOVED=PASS")
    print("REAL_CODEX_REVIEW=PASS" if args.real_codex else "FAKE_HARNESS=PASS")
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
