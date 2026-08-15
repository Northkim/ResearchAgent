from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from backend.workflow_packages import real_review_runtime as runtime
from backend.workflow_packages import real_writing_runtime
from backend.workflow_packages.production_workflows import (
    REAL_REVIEW_CAPSULE_ID,
    build_real_review_v0_5_package,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes
from backend.workflow_packages.tests.test_real_writing_runtime import (
    _answer,
    _fake_harness as _writing_harness,
    _package as _writing_package,
)


def _write(path: Path, value) -> None:
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def _package(tmp_path: Path, *, revision_required: bool) -> tuple[Path, dict]:
    writing_root, _ = _writing_package(tmp_path / "writing", with_experiment=False)
    writing_result = real_writing_runtime.run(
        writing_root, "wfi-" + "4" * 32,
        codex_executable=str(_writing_harness(tmp_path)),
        approval_input=_answer, review_input=_answer,
    )
    manuscript_path = writing_root / writing_result["artifact"]["relative_path"]
    manuscript = json.loads(manuscript_path.read_text())
    manuscript_ref = {
        "artifact_id": "artifact-" + "9" * 32,
        "artifact_type": "manuscript-draft/v2",
        "sha256": sha256_bytes(manuscript_path.read_bytes()),
    }
    built = build_real_review_v0_5_package(
        project_id="project-" + "a" * 32,
        project_name="Controlled Review", research_topic="Controlled",
        output_root=tmp_path / "review", package_id="package-" + "b" * 32,
    )
    root = built.package_root
    shutil.copyfile(manuscript_path, root / "inputs/manuscript-draft.json")
    shutil.copyfile(
        writing_root / "inputs/selected-research-idea.json",
        root / "inputs/selected-research-idea.json",
    )
    shutil.copyfile(
        writing_root / "inputs/selected-paper-library.json",
        root / "inputs/selected-paper-library.json",
    )
    sources = {
        "manuscript": manuscript_ref,
        "research_idea": manuscript["source_artifacts"]["research_idea"],
        "literature_library": manuscript["source_artifacts"]["literature_library"],
    }
    _write(root / "memory/input-provenance.json", {
        "schema_version": "reagent.real-review-input-provenance/v0.1",
        "workflow_instance_id": "wfi-" + "6" * 32,
        "artifacts": sources,
    })
    return root, sources


def _fake_harness(tmp_path: Path, *, revision_required: bool) -> Path:
    path = tmp_path / ("fake-review-issues" if revision_required else "fake-review-clean")
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import json,pathlib,sys\n"
        "root=pathlib.Path.cwd(); instruction=sys.argv[-1]\n"
        "load=lambda p:json.loads((root/p).read_text())\n"
        "dump=lambda p,v:(root/p).write_text(json.dumps(v,sort_keys=True,separators=(',',':'))+'\\n')\n"
        "sources=load('memory/input-provenance.json')['artifacts']; manuscript=load('inputs/manuscript-draft.json')\n"
        "ref=lambda s,i:{**s,'evidence_item':i,'location':i,'availability':'AVAILABLE','limitation':None}\n"
        "if 'INPUT_REVIEW AND REVIEW_SCOPE' in instruction:\n"
        " scope={'manuscript_identity':sources['manuscript'],'available_evidence':[sources[k] for k in ('research_idea','literature_library','experiment_record') if k in sources],'categories':['EVIDENCE_SUPPORT','CLAIM_SCOPE','CITATION','METHOD_CONSISTENCY','RESULT_SUPPORT','REPRODUCIBILITY'],'known_evidence_limitations':['Literature is abstract-level only'],'owner_focus':[]}\n"
        " dump('memory/review-scope.json',scope)\n"
        "else:\n"
        + (
            " issue={'issue_id':'issue-1','category':'CLAIM_SCOPE','severity':'MAJOR','target':{'section':'Introduction','claim_id':'claim-1'},'summary':'The controlled claim exceeds the represented abstract scope.','evidence_refs':[ref(sources['manuscript'],'claims.claim-1')],'recommended_action':'Narrow the claim to the exact abstract-level evidence.','blocking':True}; result={'assessment':'REVISION_REQUIRED','summary':'A bounded claim-scope revision is required.','issues':[issue],'limitations':['Synthetic controlled audit only']}\n"
            if revision_required else
            " result={'assessment':'NO_BLOCKING_ISSUES','summary':'No blocking evidence-contract issue was identified in the bounded scope.','issues':[],'limitations':['Synthetic controlled audit only']}\n"
        )
        + " dump('memory/review-result.json',result); (root/'outputs/review.md').write_text('# Controlled Review\\n\\n'+result['summary']+'\\n')\n",
        encoding="utf-8",
    )
    path.chmod(0o700)
    return path


@pytest.mark.parametrize("revision_required", [True, False])
def test_real_review_closes_structured_revision_contract(
    tmp_path: Path, revision_required: bool,
) -> None:
    root, sources = _package(tmp_path, revision_required=revision_required)
    result = runtime.run(
        root, "wfi-" + "6" * 32,
        codex_executable=str(_fake_harness(tmp_path, revision_required=revision_required)),
        approval_input=_answer, review_input=_answer,
    )
    assert result["status"] == "COMPLETED"
    artifact = json.loads((root / result["artifact"]["relative_path"]).read_text())
    assert artifact["schema"] == "review-report/v2"
    assert artifact["producer"]["capsule_id"] == REAL_REVIEW_CAPSULE_ID
    assert artifact["source_manuscript"] == sources["manuscript"]
    assert artifact["assessment"] == (
        "REVISION_REQUIRED" if revision_required else "NO_BLOCKING_ISSUES"
    )
    assert bool(artifact["issues"]) is revision_required
    assert all(set(issue) == {
        "issue_id", "category", "severity", "target", "summary",
        "evidence_refs", "recommended_action", "blocking",
    } for issue in artifact["issues"])
    assert len(list((root / "memory/progress/reports").glob("prv2-*.json"))) == 1


def test_scope_approval_and_package_admission_fail_closed(tmp_path: Path) -> None:
    root, sources = _package(tmp_path, revision_required=True)
    namespace = runtime._validator(root)
    assert namespace["validate"](root)["valid"] is True
    descriptor = json.loads((root / "workflow/real-review.json").read_text())
    assert descriptor["assessment_values"] == [
        "NO_BLOCKING_ISSUES", "REVISION_REQUIRED", "INSUFFICIENT_EVIDENCE",
    ]
    assert runtime._codex_environment()["PYTHONDONTWRITEBYTECODE"] == "1"
    undeclared = root / "inputs/undeclared.json"
    _write(undeclared, {})
    with pytest.raises(Exception, match="undeclared Capsule file"):
        namespace["validate"](root)
    undeclared.unlink()
    with pytest.raises(Exception, match="unsafe relative path"):
        namespace["safe_relative_path"]("inputs/../escape.json")
    manuscript_ref = sources["manuscript"]
    support = namespace["supporting_refs"](sources)
    scope = {
        "manuscript_identity": manuscript_ref, "available_evidence": support,
        "categories": ["EVIDENCE_SUPPORT"],
        "known_evidence_limitations": [], "owner_focus": [],
    }
    with pytest.raises(runtime.RealReviewError, match="did not approve"):
        runtime._approve_scope(
            root, scope, runtime.canonical_hash(scope), sources,
            lambda _: "approve wrong",
        )


def test_issue_evidence_uses_shared_availability_values(tmp_path: Path) -> None:
    root, sources = _package(tmp_path, revision_required=True)
    namespace = runtime._validator(root)
    manuscript = json.loads((root / "inputs/manuscript-draft.json").read_text())
    result = {
        "assessment": "REVISION_REQUIRED",
        "summary": "A bounded revision is required.",
        "issues": [{
            "issue_id": "issue-1", "category": "CLAIM_SCOPE",
            "severity": "MAJOR",
            "target": {"section": "Introduction", "claim_id": "claim-1"},
            "summary": "The claim exceeds the represented evidence scope.",
            "evidence_refs": [{
                **sources["literature_library"],
                "evidence_item": "paper-1", "location": "paper-1",
                "availability": "SCOPE_LIMITED",
                "limitation": "Abstract-level evidence only",
            }],
            "recommended_action": "Narrow the claim.", "blocking": True,
        }],
        "limitations": [],
    }
    with pytest.raises(Exception, match="evidence availability"):
        namespace["validate_review_result"](
            result, manuscript_ref=sources["manuscript"],
            support=namespace["supporting_refs"](sources),
            surface=namespace["manuscript_surface"](manuscript),
        )


def test_scope_instruction_forbids_identity_shape_drift() -> None:
    instruction = runtime._scope_instruction()
    assert "contain exactly artifact_id" in instruction
    assert "never add role" in instruction
    assert "arrays of non-empty strings" in instruction
    assert "never objects and never null" in instruction
