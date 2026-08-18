from __future__ import annotations

import json
import re
import runpy
import shutil
from pathlib import Path

import pytest

from backend.artifact_references.tests.test_forward_downstream_v5_contracts import _v5
from backend.artifact_references.tests.test_forward_downstream_v5_contracts import _manuscript, _review
from backend.artifact_references.tests.test_research_flow_contracts import _library, _selected
from backend.workflow_packages.forward_downstream_publication import (
    build_initial_writing_v0_7_package, build_review_v0_6_package,
    build_writing_revision_v0_8_package,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes


def _write(path: Path, value) -> bytes:
    content = (canonical_json(value) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return content


def _ref(letter: str, kind: str, content: bytes) -> dict[str, str]:
    return {"artifact_id": "artifact-" + letter * 32, "artifact_type": kind, "sha256": sha256_bytes(content)}


def _answer(prompt: str) -> str:
    match = re.search(r"Type `([^`]+)`", prompt)
    assert match
    return match.group(1)


def _harness(path: Path, role: str) -> Path:
    common = """#!/usr/bin/env python3
import json,pathlib,sys
root=pathlib.Path.cwd(); instruction=sys.argv[-1]
load=lambda p:json.loads((root/p).read_text())
dump=lambda p,v:(root/p).write_text(json.dumps(v,sort_keys=True,separators=(',',':'))+'\\n')
sources=load('memory/input-provenance.json')['artifacts']
"""
    if role == "writing":
        body = """
experiment=load('inputs/experiment-record.json'); block=experiment['bounded_scientific_evidence']['blocks'][0]
base=lambda s,i,lim=None:{**s,'evidence_item':i,'location':i,'availability':'LIMITED' if lim else 'AVAILABLE','limitation':lim}
eref=lambda:{**base(sources['experiment_record'],block['block_id'],'Bounded Experiment evidence'), 'evidence_block_id':block['block_id'],'evidence_block_checksum':block['block_checksum']}
if 'INPUT_REVIEW THROUGH OUTLINE' in instruction:
 brief={'document_type':'initial research manuscript','working_title':'Forward bounded draft','target_audience':'research owner','target_words':{'minimum':100,'maximum':1200},'requested_sections':['Results'],'citation_style':'numeric','abstract_requested':False,'owner_constraints':['Preserve v5 evidence status']}
 evidence=[{'section':'Results','support_status':'SUPPORTED','evidence_refs':[base(sources['experiment_record'],block['block_id'],'Bounded Experiment evidence')],'limitations':['Preserve the bounded source limitation.']}]
 dump('memory/writing-brief.json',brief); dump('memory/evidence-map.json',evidence); dump('memory/outline.json',[{'heading':'Results','support_status':'SUPPORTED'}])
else:
 boundary=experiment['lifecycle_record']['methodology']['claim_boundaries'][0]
 claim={'claim_id':'claim-result-1','claim_type':'RESULT','section':'Results','claim_text':'A bounded categorical finding was observed.','support_status':'SUPPORTED','evidence_refs':[eref()],'citation_ids':[],'limitations':['Preserve the bounded source limitation.'],'evidence_qualification':'BOUNDED_SCIENTIFIC_CLAIM','claim_boundary_refs':[boundary]}
 dump('memory/claims.json',[claim]); dump('memory/citations.json',[]); (root/'outputs/draft.md').write_text('# Forward bounded draft\\n\\n## Results\\nA bounded categorical finding was observed.\\n')
"""
    elif role == "review":
        body = """
manuscript=load('inputs/manuscript-draft.json')
if 'INPUT_REVIEW AND REVIEW_SCOPE' in instruction:
 support=[sources[k] for k in ('research_idea','literature_library','experiment_record') if k in sources]
 scope={'manuscript_identity':sources['manuscript'],'available_evidence':support,'categories':['EVIDENCE_SUPPORT','CLAIM_SCOPE','CITATION','METHOD_CONSISTENCY','RESULT_SUPPORT','REPRODUCIBILITY'],'known_evidence_limitations':['Bounded v5 evidence only'],'owner_focus':[]}; dump('memory/review-scope.json',scope)
else:
 ref={**sources['manuscript'],'evidence_item':'claim-result-1','location':'claims/claim-result-1','availability':'AVAILABLE','limitation':None}
 issue={'issue_id':'issue-1','category':'CLAIM_SCOPE','severity':'MINOR','target':{'section':'Results','claim_id':'claim-result-1'},'summary':'Retain the exact claim boundary in revision.','evidence_refs':[ref],'recommended_action':'Keep the bounded wording and limitation explicit.','blocking':True}
 result={'assessment':'REVISION_REQUIRED','summary':'One bounded wording revision is required.','issues':[issue],'limitations':['Review is limited to exact supplied evidence.']}; dump('memory/review-result.json',result); (root/'outputs/review.md').write_text('# Forward Review\\n\\nOne bounded wording revision is required.\\n')
"""
    else:
        body = """
prior=load('inputs/prior-manuscript.json'); review=load('inputs/review-report.json')
if 'ISSUE RECONCILIATION' in instruction:
 plan=[{'issue_id':'issue-1','intended_disposition':'ADDRESSED','planned_change':'Retain bounded wording and limitation.','affected_section':'Results','affected_claims':['claim-result-1'],'evidence_to_use':[],'known_limitation':None}]; dump('memory/revision-plan.json',plan)
else:
 dump('memory/claims.json',prior['claims']); dump('memory/citations.json',prior['citations']); dump('memory/issue-accounting.json',[{'issue_id':'issue-1','disposition':'ADDRESSED','change_summary':'Retained bounded wording.','changed_sections':['Results'],'changed_claims':['claim-result-1'],'remaining_limitation':None}]); (root/'outputs/revised-draft.md').write_text('# Forward bounded revised draft\\n\\n## Results\\nA bounded categorical finding was observed within the exact boundary.\\n')
"""
    path.write_text(common + body)
    path.chmod(0o700)
    return path


def prepare_real_codex_fixtures(root: Path) -> dict[str, tuple[Path, str]]:
    """Create disposable exact-input Capsules for E7 checkpoint qualification."""
    idea, _ = _selected(); library = _library(); v5, block = _v5()
    idea_bytes = (canonical_json(idea) + "\n").encode(); library_bytes = (canonical_json(library) + "\n").encode(); v5_bytes = (canonical_json(v5) + "\n").encode()
    common_refs = {
        "research_idea": _ref("a", "selected-research-idea/v1", idea_bytes),
        "literature_library": _ref("b", "selected-paper-library/v1", library_bytes),
        "experiment_record": _ref("e", "experiment-record/v5", v5_bytes),
    }
    result: dict[str, tuple[Path, str]] = {}
    writing_id = "wfi-" + "7" * 32
    writing = build_initial_writing_v0_7_package(project_id="project-"+"7"*32, project_name="E7", research_topic="Bounded non-ML evidence", output_root=root/"writing", package_id="e7-writing").package_root
    _write(writing/"inputs/selected-research-idea.json", idea); _write(writing/"inputs/selected-paper-library.json", library); _write(writing/"inputs/experiment-record.json", v5)
    _write(writing/"memory/input-provenance.json", {"schema_version":"reagent.real-writing-input-provenance/v0.1","workflow_instance_id":writing_id,"artifacts":common_refs})
    result["writing"] = (writing, writing_id)

    manuscript, _ = _manuscript(v5, block, inputs=common_refs)
    manuscript_bytes = (canonical_json(manuscript) + "\n").encode(); manuscript_ref = _ref("c", "manuscript-draft/v4", manuscript_bytes)
    review_id = "wfi-" + "8" * 32
    review = build_review_v0_6_package(project_id="project-"+"7"*32, project_name="E7", research_topic="Bounded non-ML evidence", output_root=root/"review", package_id="e7-review").package_root
    _write(review/"inputs/manuscript-draft.json", manuscript); _write(review/"inputs/selected-research-idea.json", idea); _write(review/"inputs/selected-paper-library.json", library); _write(review/"inputs/experiment-record.json", v5)
    review_refs = {"manuscript": manuscript_ref, **common_refs}
    _write(review/"memory/input-provenance.json", {"schema_version":"reagent.real-review-input-provenance/v0.1","workflow_instance_id":review_id,"artifacts":review_refs})
    result["review"] = (review, review_id)

    review_artifact, _ = _review(manuscript, common_refs, v5, manuscript_ref=manuscript_ref)
    review_bytes = (canonical_json(review_artifact) + "\n").encode(); review_ref = _ref("d", "review-report/v3", review_bytes)
    revision_id = "wfi-" + "9" * 32
    revision = build_writing_revision_v0_8_package(project_id="project-"+"7"*32, project_name="E7", research_topic="Bounded non-ML evidence", output_root=root/"revision", package_id="e7-revision").package_root
    _write(revision/"inputs/prior-manuscript.json", manuscript); _write(revision/"inputs/review-report.json", review_artifact); _write(revision/"inputs/selected-research-idea.json", idea); _write(revision/"inputs/selected-paper-library.json", library); _write(revision/"inputs/experiment-record.json", v5)
    _write(revision/"memory/input-provenance.json", {"schema_version":"reagent.writing-revision-input-provenance/v0.1","workflow_instance_id":revision_id,"artifacts":{"prior_manuscript":manuscript_ref,"causal_review":review_ref,**common_refs}})
    result["revision"] = (revision, revision_id)
    return result


def test_forward_revision_checkpoint_preserves_unanchored_unresolved_issue(tmp_path: Path) -> None:
    package = build_writing_revision_v0_8_package(
        project_id="project-" + "6" * 32, project_name="Forward",
        research_topic="Forward", output_root=tmp_path, package_id="revision-plan",
    ).package_root
    validator = runpy.run_path(str(package / "validate_package.py"))
    plan = [{
        "issue_id": "issue-1", "intended_disposition": "NOT_ADDRESSED",
        "planned_change": "No unsupported change is planned.",
        "affected_section": None, "affected_claims": [], "evidence_to_use": [],
        "known_limitation": "The Review did not identify a manuscript anchor.",
    }]
    assert validator["validate_revision_plan"](
        plan, [{"issue_id": "issue-1"}], {},
    ) == plan


def test_fake_harness_closes_exact_forward_chain_and_replay_is_terminal(tmp_path: Path) -> None:
    idea, _ = _selected(); library = _library(); v5, _ = _v5()
    idea_bytes = (canonical_json(idea) + "\n").encode(); library_bytes = (canonical_json(library) + "\n").encode(); v5_bytes = (canonical_json(v5) + "\n").encode()
    common_refs = {
        "research_idea": _ref("a", "selected-research-idea/v1", idea_bytes),
        "literature_library": _ref("b", "selected-paper-library/v1", library_bytes),
        "experiment_record": _ref("e", "experiment-record/v5", v5_bytes),
    }

    writing = build_initial_writing_v0_7_package(project_id="project-" + "1" * 32, project_name="Forward", research_topic="Forward", output_root=tmp_path / "writing", package_id="forward-writing").package_root
    _write(writing / "inputs/selected-research-idea.json", idea); _write(writing / "inputs/selected-paper-library.json", library); _write(writing / "inputs/experiment-record.json", v5)
    _write(writing / "memory/input-provenance.json", {"schema_version":"reagent.real-writing-input-provenance/v0.1","workflow_instance_id":"wfi-"+"1"*32,"artifacts":common_refs})
    writing_runtime = runpy.run_path(str(writing / "reagent_local.py"))
    with pytest.raises(Exception, match="did not approve"):
        writing_runtime["run"](writing, "wfi-"+"1"*32, codex_executable=str(_harness(tmp_path / "writing-codex", "writing")), approval_input=lambda _: "approve wrong")
    assert (writing / "memory/outline.json").is_file() and not (writing / "outputs/manuscript-draft.json").exists()
    written = writing_runtime["run"](writing, "wfi-"+"1"*32, codex_executable=str(_harness(tmp_path / "writing-codex", "writing")), approval_input=_answer, review_input=_answer)
    manuscript_path = writing / written["artifact"]["relative_path"]
    manuscript = json.loads(manuscript_path.read_text()); manuscript_ref = _ref("c", "manuscript-draft/v4", manuscript_path.read_bytes())
    assert manuscript["experiment_evidence"]["scientific_evidence_status"] == "SUPPORTS_BOUNDED_FINDINGS"

    review = build_review_v0_6_package(project_id="project-"+"1"*32, project_name="Forward", research_topic="Forward", output_root=tmp_path / "review", package_id="forward-review").package_root
    shutil.copyfile(manuscript_path, review / "inputs/manuscript-draft.json"); _write(review / "inputs/selected-research-idea.json", idea); _write(review / "inputs/selected-paper-library.json", library); _write(review / "inputs/experiment-record.json", v5)
    review_refs = {"manuscript": manuscript_ref, **common_refs}
    _write(review / "memory/input-provenance.json", {"schema_version":"reagent.real-review-input-provenance/v0.1","workflow_instance_id":"wfi-"+"2"*32,"artifacts":review_refs})
    review_runtime = runpy.run_path(str(review / "reagent_local.py"))
    with pytest.raises(Exception, match="did not approve"):
        review_runtime["run"](review, "wfi-"+"2"*32, codex_executable=str(_harness(tmp_path / "review-codex", "review")), approval_input=lambda _: "approve wrong")
    assert (review / "memory/review-scope.json").is_file() and not (review / "outputs/review-report.json").exists()
    reviewed = review_runtime["run"](review, "wfi-"+"2"*32, codex_executable=str(_harness(tmp_path / "review-codex", "review")), approval_input=_answer, review_input=_answer)
    review_path = review / reviewed["artifact"]["relative_path"]
    review_artifact = json.loads(review_path.read_text()); review_ref = _ref("d", "review-report/v3", review_path.read_bytes())
    assert review_artifact["experiment_evidence_audit"]["evaluation_validity"] == "VALID"

    revision = build_writing_revision_v0_8_package(project_id="project-"+"1"*32, project_name="Forward", research_topic="Forward", output_root=tmp_path / "revision", package_id="forward-revision").package_root
    shutil.copyfile(manuscript_path, revision / "inputs/prior-manuscript.json"); shutil.copyfile(review_path, revision / "inputs/review-report.json"); _write(revision / "inputs/selected-research-idea.json", idea); _write(revision / "inputs/selected-paper-library.json", library); _write(revision / "inputs/experiment-record.json", v5)
    revision_refs = {"prior_manuscript": manuscript_ref, "causal_review": review_ref, **common_refs}
    _write(revision / "memory/input-provenance.json", {"schema_version":"reagent.writing-revision-input-provenance/v0.1","workflow_instance_id":"wfi-"+"3"*32,"artifacts":revision_refs})
    revision_runtime = runpy.run_path(str(revision / "reagent_local.py"))
    with pytest.raises(Exception, match="did not approve"):
        revision_runtime["run"](revision, "wfi-"+"3"*32, codex_executable=str(_harness(tmp_path / "revision-codex", "revision")), approval_input=lambda _: "approve wrong")
    assert (revision / "memory/revision-plan.json").is_file() and not (revision / "outputs/manuscript-draft.json").exists()
    revised = revision_runtime["run"](revision, "wfi-"+"3"*32, codex_executable=str(_harness(tmp_path / "revision-codex", "revision")), approval_input=_answer, review_input=_answer)
    final = json.loads((revision / revised["artifact"]["relative_path"]).read_text())
    assert final["schema"] == "manuscript-draft/v5" and final["prior_manuscript"] == manuscript_ref and final["causal_review"] == review_ref
    with pytest.raises(Exception, match="terminal Progress"):
        revision_runtime["run"](revision, "wfi-"+"3"*32, codex_executable=str(tmp_path / "revision-codex"))
