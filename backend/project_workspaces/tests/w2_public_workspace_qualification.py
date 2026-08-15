"""Controlled public Workspace qualification for one Review-to-Writing revision."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import httpx

from backend.artifact_references.research_flow_contracts import (
    validate_manuscript_draft_v3,
    validate_review_report_v2,
)
from backend.artifact_references.tests.test_research_flow_contracts import CANDIDATE_A, _library, _selected
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.project_workspaces import workspace_cli
from backend.project_workspaces.production_workflows import (
    REAL_REVIEW_CAPSULE_ID,
    REAL_WRITING_CAPSULE_ID,
    WRITING_REVISION_CAPSULE_CHECKSUM,
    WRITING_REVISION_CAPSULE_ID,
)
from backend.project_workspaces.tests.r1_public_workspace_qualification import _manuscript
from backend.project_workspaces.tests.test_f1b_full_scaffold_flow import _seed_upstream
from backend.project_workspaces.tests.test_owner_real_research_gate import _loopback_server
from backend.project_workspaces.tests.w1_public_workspace_qualification import (
    _add_instance, _bind, _clean_environment, _qualification_app,
    _real_codex_wrapper, _run_public_pty,
)
from backend.workflow_packages.serialization import canonical_hash, canonical_json

WORKFLOW_ID = "writing-local-experimental"
WORKFLOW_VERSION = "0.4.0"
CAPSULE_VERSION = "0.6.0"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _reference(artifact: dict[str, str], artifact_type: str) -> dict[str, str]:
    return {"artifact_id": artifact["artifact_id"], "artifact_type": artifact_type, "sha256": artifact["content_checksum"]}


def _evidence_ref(source: dict[str, str], item: str, limitation: str | None = None) -> dict:
    return {**source, "evidence_item": item, "location": item,
            "availability": "LIMITED" if limitation else "AVAILABLE",
            "limitation": limitation}


def _review(
    manuscript: dict, manuscript_ref: dict[str, str], idea: dict[str, str],
    library: dict[str, str], *, missing_evidence: bool,
) -> dict:
    support = [idea, library]
    scope_value = {
        "manuscript_identity": manuscript_ref, "available_evidence": support,
        "categories": ["EVIDENCE_SUPPORT", "CLAIM_SCOPE", "CITATION", "METHOD_CONSISTENCY", "RESULT_SUPPORT", "REPRODUCIBILITY"],
        "known_evidence_limitations": ["Literature is abstract-level only"], "owner_focus": [],
    }
    scope = {"sha256": canonical_hash(scope_value), "value": scope_value}
    approval_payload = {
        "scope_sha256": scope["sha256"], "manuscript_sha256": manuscript_ref["sha256"],
        "bound_artifacts_sha256": canonical_hash(support),
        "approved_at": "2026-08-15T01:00:00Z", "decision": "APPROVED",
    }
    availability = []
    seen = set()
    for claim in manuscript["claims"]:
        for ref in claim["evidence_refs"]:
            key = tuple(ref[field] for field in ("artifact_id", "artifact_type", "sha256", "evidence_item", "location"))
            if key in seen:
                continue
            seen.add(key)
            availability.append({
                **ref,
                "availability": "SCOPE_LIMITED" if ref["limitation"] else "AVAILABLE",
            })
    issue = {
        "issue_id": "issue-1", "category": "EVIDENCE_SUPPORT" if missing_evidence else "CLAIM_SCOPE",
        "severity": "MAJOR", "target": {"section": "Introduction", "claim_id": "claim-1"},
        "summary": "The requested evidence is unavailable." if missing_evidence else "The universal claim exceeds the selected abstract evidence.",
        "evidence_refs": [] if missing_evidence else [_evidence_ref(library, CANDIDATE_A, "Abstract-level evidence only")],
        "recommended_action": "Add unavailable external evidence." if missing_evidence else "Narrow the claim to the represented abstract scope.",
        "blocking": True,
    }
    payload = {
        "source_manuscript": manuscript_ref, "supporting_artifacts": support,
        "review_scope": scope,
        "scope_approval": {"sha256": canonical_hash(approval_payload), **approval_payload},
        "evidence_availability": availability, "assessment": "REVISION_REQUIRED",
        "summary": "One bounded revision issue requires explicit accounting.",
        "issues": [issue], "limitations": ["Controlled synthetic Review only"],
    }
    owner_payload = {"review_result_sha256": canonical_hash(payload), "reviewed_at": "2026-08-15T01:05:00Z", "decision": "APPROVED"}
    return validate_review_report_v2({
        "schema": "review-report/v2", "core_capability_maturity": "REVIEWED_CORE",
        "producer": {"workflow_instance_id": "wfi-" + ("4" if missing_evidence else "3") * 32,
                     "capsule_id": REAL_REVIEW_CAPSULE_ID, "capsule_version": "0.5.0", "execution_round": 1},
        **payload, "owner_review": {"sha256": canonical_hash(owner_payload), **owner_payload},
    }, manuscript=manuscript, bound_inputs={
        "manuscript": manuscript_ref, "research_idea": idea,
        "literature_library": library, "experiment_record": None,
    })


def _fake_harness(root: Path) -> Path:
    path = root / "controlled-fake-revision-codex"
    path.write_text(
        "#!/usr/bin/env python3\nimport json,pathlib,sys\n"
        "root=pathlib.Path.cwd(); instruction=sys.argv[-1]\n"
        "load=lambda p:json.loads((root/p).read_text()); dump=lambda p,v:(root/p).write_text(json.dumps(v,sort_keys=True,separators=(',',':'))+'\\n')\n"
        "sources=load('memory/input-provenance.json')['artifacts']; review=load('inputs/review-report.json'); prior=load('inputs/prior-manuscript.json'); issue=review['issues'][0]\n"
        "missing=not issue['evidence_refs']; disposition='NOT_ADDRESSED' if missing else 'ADDRESSED'; limitation='Required evidence is not bound.' if missing else None\n"
        "if 'ISSUE RECONCILIATION' in instruction:\n"
        " evidence=[] if missing else issue['evidence_refs']\n"
        " dump('memory/revision-plan.json',[{'issue_id':issue['issue_id'],'intended_disposition':disposition,'planned_change':'Narrow the claim or preserve the missing-evidence limitation.','affected_section':'Introduction','affected_claims':['claim-1'],'evidence_to_use':evidence,'known_limitation':limitation}])\n"
        "else:\n"
        " claims=prior['claims']; claims[0]['claim_text']='The selected abstract reports a bounded observation.' if not missing else claims[0]['claim_text']\n"
        " dump('memory/claims.json',claims);dump('memory/citations.json',prior['citations'])\n"
        " dump('memory/issue-accounting.json',[{'issue_id':issue['issue_id'],'disposition':disposition,'change_summary':'Applied only the evidence-permitted revision.','changed_sections':['Introduction'],'changed_claims':['claim-1'],'remaining_limitation':limitation}])\n"
        " (root/'outputs/revised-draft.md').write_text('# Controlled Revised Draft\\n\\n## Introduction\\nThe selected abstract reports a bounded observation.\\n\\n## Proposed Method\\nThe study will evaluate the proposed comparison.\\n\\n## Results\\nObserved results are unavailable.\\n')\n",
        encoding="utf-8",
    )
    path.chmod(0o700); return path


def _qualify(root: Path, *, real_codex: bool = False) -> dict[str, str]:
    database = InMemoryDatabase(); uow_factory = lambda: InMemoryUnitOfWork(database)
    app = _qualification_app(root, database)
    with _loopback_server(app) as base_url, httpx.Client(base_url=base_url, timeout=30) as client:
        created = client.post("/projects", json={
            "name": "W2 controlled synthetic qualification", "research_topic": "Bounded revision",
            "selected_workflow": "LITERATURE_SEARCH", "workflow_setup": "full-research",
        })
        _require(created.status_code == 201, created.text); project_id = created.json()["project_id"]
        initial = client.get(f"/projects/{project_id}/workflow-instances").json()["items"]
        literature_instance = next(item for item in initial if item["workflow_definition_id"] == "literature-search-local-experimental")
        idea_instance = next(item for item in initial if item["workflow_definition_id"] == "idea-discovery-local-experimental")
        writing_a = _add_instance(client, project_id, WORKFLOW_ID, "0.3.0", REAL_WRITING_CAPSULE_ID, "0.5.0", 1)
        writing_b = _add_instance(client, project_id, WORKFLOW_ID, "0.3.0", REAL_WRITING_CAPSULE_ID, "0.5.0", 2)
        review_a = _add_instance(client, project_id, "review-local-experimental", "0.3.0", REAL_REVIEW_CAPSULE_ID, "0.5.0", 3)
        review_b = _add_instance(client, project_id, "review-local-experimental", "0.3.0", REAL_REVIEW_CAPSULE_ID, "0.5.0", 4)
        revision_a = _add_instance(client, project_id, WORKFLOW_ID, WORKFLOW_VERSION, WRITING_REVISION_CAPSULE_ID, CAPSULE_VERSION, 5)
        revision_b = _add_instance(client, project_id, WORKFLOW_ID, WORKFLOW_VERSION, WRITING_REVISION_CAPSULE_ID, CAPSULE_VERSION, 6)
        descriptor = client.get(f"/projects/{project_id}/workspace-bootstrap").json(); workspace = root / "workspace"
        workspace_cli.bootstrap_workspace(target=workspace, descriptor=descriptor)
        transport = workspace_cli.HTTPWorkspaceSyncTransport(base_url)
        _require(workspace_cli.sync_workspace(workspace_root=workspace, transport=transport).status == "SYNCED", "Workspace sync failed")
        lock = json.loads((workspace / workspace_cli.INSTALLED_LOCK).read_text())
        roots = {item["workflow_instance_id"]: workspace / item["relative_path"] for item in lock["installed_capsules"]}
        library_artifact = _seed_upstream(
            uow_factory=uow_factory, project_id=project_id, instance=literature_instance,
            root=roots[literature_instance["workflow_instance_id"]], artifact_type="selected-paper-library/v1",
            content=_library(), character="a",
        )
        selected_idea, _ = _selected()
        idea_artifact = _seed_upstream(
            uow_factory=uow_factory, project_id=project_id, instance=idea_instance,
            root=roots[idea_instance["workflow_instance_id"]], artifact_type="selected-research-idea/v1",
            content=selected_idea, character="b",
        )
        idea_ref = _reference(idea_artifact, "selected-research-idea/v1"); library_ref = _reference(library_artifact, "selected-paper-library/v1")
        seeded: list[tuple[dict, dict, dict, dict, dict]] = []
        for missing, writing, review_instance, revision, character in (
            (False, writing_a, review_a, revision_a, "c"),
            (True, writing_b, review_b, revision_b, "d"),
        ):
            manuscript = _manuscript(idea_ref, library_ref, seeded_issue=True)
            manuscript_artifact = _seed_upstream(
                uow_factory=uow_factory, project_id=project_id, instance=writing,
                root=roots[writing["workflow_instance_id"]], artifact_type="manuscript-draft/v2",
                content=manuscript, character=character,
            )
            manuscript_ref = _reference(manuscript_artifact, "manuscript-draft/v2")
            report = _review(manuscript, manuscript_ref, idea_ref, library_ref, missing_evidence=missing)
            review_artifact = _seed_upstream(
                uow_factory=uow_factory, project_id=project_id, instance=review_instance,
                root=roots[review_instance["workflow_instance_id"]], artifact_type="review-report/v2",
                content=report, character="e" if not missing else "f",
            )
            seeded.append((revision, manuscript_artifact, review_artifact, manuscript, report))
        workspace_cli.refresh_artifact_index(workspace_root=workspace, transport=transport)
        for revision, manuscript_artifact, review_artifact, _, _ in seeded:
            _bind(client, project_id, revision, "prior_manuscript", manuscript_artifact)
            _bind(client, project_id, revision, "causal_review", review_artifact)
            _bind(client, project_id, revision, "research_idea", idea_artifact)
            _bind(client, project_id, revision, "literature_library", library_artifact)
            materialized = workspace_cli.materialize_artifacts(
                workspace_root=workspace, consumer_workflow_instance_id=revision["workflow_instance_id"], transport=transport,
            )
            _require(materialized.materialized_count == 4, "exact W2 inputs were not materialized")
        harness = _fake_harness(root)
        if real_codex:
            executable = shutil.which("codex"); _require(executable is not None, "Codex executable is unavailable")
            harness = _real_codex_wrapper(root, Path(executable).resolve(strict=True))
        root_cli = workspace / "reagent_local.py"; environment = _clean_environment(); artifacts = {}
        journeys = seeded[:1] if real_codex else seeded
        for revision, _, _, prior, review in journeys:
            capsule = roots[revision["workflow_instance_id"]]
            workspace_cli._verify_locked_capsules(workspace, lock, descriptor); workspace_cli._scan_capsule_for_credentials(capsule)
            output = _run_public_pty([
                sys.executable, str(root_cli), "run", str(workspace),
                "--workflow-instance", revision["workflow_instance_id"], "--api-url", base_url,
                "--codex-executable", str(harness), "--json",
            ], cwd=workspace, environment=environment, timeout_seconds=900.0 if real_codex else 120.0)
            _require("RUN_COMPLETED" in output, f"public W2 run failed:\n{output}")
            reports = list((capsule / "memory/progress/reports").glob("prv2-*.json")); _require(len(reports) == 1, "W2 Progress was not finalized exactly once")
            current = json.loads((capsule / "memory/current-artifact.json").read_text()); artifact = json.loads((capsule / current["relative_path"]).read_text())
            inputs = json.loads((capsule / "memory/input-provenance.json").read_text())["artifacts"]
            validate_manuscript_draft_v3(artifact, prior_manuscript=prior, causal_review=review, bound_inputs={
                "prior_manuscript": inputs["prior_manuscript"], "causal_review": inputs["causal_review"],
                "research_idea": idea_ref, "literature_library": library_ref, "experiment_record": None,
            })
            missing = not review["issues"][0]["evidence_refs"]
            _require(artifact["remaining_blocking_issue_count"] == (1 if missing else 0), "remaining blocker truth is wrong")
            _require(len(artifact["issue_accounting"]) == len(review["issues"]) == 1, "Review issue was not accounted exactly once")
            cloud = client.get(f"/projects/{project_id}/artifacts", params={"workflow_instance_id": revision["workflow_instance_id"]}).json()["artifacts"]
            _require(len(cloud) == 1 and cloud[0]["artifact_type"] == "manuscript-draft/v3" and cloud[0]["producer_capsule_id"] == WRITING_REVISION_CAPSULE_ID and cloud[0]["content_checksum"] == current["checksum"], "Cloud did not promote exact manuscript-draft/v3")
            progress = client.get(f"/projects/{project_id}/workflow-instances/{revision['workflow_instance_id']}/progress").json()
            _require(progress["history_total"] == 1 and progress["projection"]["research_status"] == "COMPLETED" and progress["projection"]["result_count"] == 1, "Cloud W2 Progress is not completed exactly once")
            artifacts["missing_evidence" if missing else "addressable"] = current["checksum"]
        return {"project_id": project_id, **artifacts, "capsule_checksum": WRITING_REVISION_CAPSULE_CHECKSUM}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--real-codex", action="store_true"); args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="reagent-w2-public-qualification-") as temporary:
        root = Path(temporary); evidence = _qualify(root, real_codex=args.real_codex)
    _require(not root.exists(), "temporary W2 qualification state was not removed")
    print("W2_PUBLIC_WORKSPACE_QUALIFICATION=PASS")
    print("CONTROLLED_ADDRESSABLE_ISSUE=PASS")
    print("CONTROLLED_MISSING_EVIDENCE=NOT_RUN_IN_REAL_CODEX_MODE" if args.real_codex else "CONTROLLED_MISSING_EVIDENCE=PASS")
    print("MANUSCRIPT_DRAFT_V3=PASS"); print("PROGRESS_EXACTLY_ONCE=PASS")
    print("CLOUD_PROJECTION=PASS"); print("TEMPORARY_STATE_REMOVED=PASS")
    print("REAL_CODEX_REVISION=PASS" if args.real_codex else "FAKE_HARNESS=PASS")
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
