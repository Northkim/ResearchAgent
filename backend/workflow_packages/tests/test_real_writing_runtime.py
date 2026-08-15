from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from backend.artifact_references.tests.test_research_flow_contracts import (
    CANDIDATE_A,
    _library,
    _selected,
)
from backend.workflow_packages import real_writing_runtime as runtime
from backend.workflow_packages.production_workflows import (
    REAL_WRITING_CAPSULE_ID,
    build_real_writing_v0_5_package,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes


def _write(path: Path, value) -> None:
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def _package(tmp_path: Path, *, with_experiment: bool) -> tuple[Path, dict]:
    built = build_real_writing_v0_5_package(
        project_id="project-" + "a" * 32, project_name="Controlled Writing",
        research_topic="Controlled", output_root=tmp_path,
        package_id="package-" + "b" * 32,
    )
    root = built.package_root
    idea, _ = _selected()
    library = _library()
    _write(root / "inputs/selected-research-idea.json", idea)
    _write(root / "inputs/selected-paper-library.json", library)
    sources = {
        "research_idea": {
            "artifact_id": "artifact-" + "1" * 32,
            "artifact_type": "selected-research-idea/v1",
            "sha256": sha256_bytes((root / "inputs/selected-research-idea.json").read_bytes()),
        },
        "literature_library": {
            "artifact_id": "artifact-" + "2" * 32,
            "artifact_type": "selected-paper-library/v1",
            "sha256": sha256_bytes((root / "inputs/selected-paper-library.json").read_bytes()),
        },
    }
    if with_experiment:
        experiment = _experiment()
        _write(root / "inputs/experiment-record.json", experiment)
        sources["experiment_record"] = {
            "artifact_id": "artifact-" + "3" * 32,
            "artifact_type": "experiment-record/v2",
            "sha256": sha256_bytes((root / "inputs/experiment-record.json").read_bytes()),
        }
    _write(root / "memory/input-provenance.json", {
        "schema_version": "reagent.real-writing-input-provenance/v0.1",
        "workflow_instance_id": "wfi-" + "4" * 32,
        "artifacts": sources,
    })
    return root, sources


def _experiment() -> dict:
    return {
        "schema": "experiment-record/v2", "core_capability_maturity": "REVIEWED_CORE",
        "mode": "IDEA_EXPERIMENT", "source_artifacts": [],
        "requirements": {}, "approved_plan": {}, "approval": {},
        "execution": {"status": "SUCCEEDED", "exit_code": 0},
        "evaluation": {"status": "VALID", "metrics": [{"name": "value", "value": 5, "unit": None}]},
        "result_status": "SUCCEEDED", "limitations": ["Controlled synthetic evidence"],
    }


def _fake_harness(tmp_path: Path) -> Path:
    path = tmp_path / "fake-writing-codex"
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import json, pathlib, sys\n"
        "root=pathlib.Path.cwd(); instruction=sys.argv[-1]\n"
        "load=lambda p: json.loads((root/p).read_text())\n"
        "dump=lambda p,v: (root/p).write_text(json.dumps(v,sort_keys=True,separators=(',',':'))+'\\n')\n"
        "sources=load('memory/input-provenance.json')['artifacts']\n"
        "ref=lambda source,item,lim=None: {**source,'evidence_item':item,'location':item,'availability':'LIMITED' if lim else 'AVAILABLE','limitation':lim}\n"
        f"paper={CANDIDATE_A!r}\n"
        "if 'INPUT_REVIEW THROUGH OUTLINE' in instruction:\n"
        " brief={'document_type':'initial research manuscript','working_title':'Controlled Evidence-Bound Draft','target_audience':'research owner','target_words':{'minimum':300,'maximum':1200},'requested_sections':['Introduction','Proposed Method','Results'],'citation_style':'numeric','abstract_requested':False,'owner_constraints':['Do not fabricate observed results']}\n"
        " result_status='SUPPORTED' if 'experiment_record' in sources else 'UNAVAILABLE'\n"
        " result_refs=[ref(sources['experiment_record'],'evaluation.metrics.value')] if 'experiment_record' in sources else []\n"
        " evidence=[{'section':'Introduction','support_status':'SUPPORTED','evidence_refs':[ref(sources['literature_library'],paper,'Abstract-level evidence only')],'limitations':['No full text']},{'section':'Proposed Method','support_status':'PLANNED','evidence_refs':[ref(sources['research_idea'],'selected_idea.proposed_direction')],'limitations':[]},{'section':'Results','support_status':result_status,'evidence_refs':result_refs,'limitations':[] if result_refs else ['No Experiment bound']}]\n"
        " outline=[{'heading':item['section'],'support_status':item['support_status']} for item in evidence]\n"
        " dump('memory/writing-brief.json',brief); dump('memory/evidence-map.json',evidence); dump('memory/outline.json',outline)\n"
        "else:\n"
        " citation={'citation_id':'cite-1','paper_id':paper,'source_artifact':sources['literature_library'],'evidence_scope':'ABSTRACT','reference_markdown':'[1] Controlled synthetic paper.'}\n"
        " claims=[{'claim_id':'claim-1','claim_type':'LITERATURE','section':'Introduction','claim_text':'The selected abstract describes a bounded observation.','support_status':'SUPPORTED','evidence_refs':[ref(sources['literature_library'],paper,'Abstract-level evidence only')],'citation_ids':['cite-1'],'limitations':['No full text']},{'claim_id':'claim-2','claim_type':'PROPOSAL','section':'Proposed Method','claim_text':'The study will evaluate the proposed comparison.','support_status':'PLANNED','evidence_refs':[ref(sources['research_idea'],'selected_idea.proposed_direction')],'citation_ids':[],'limitations':[]}]\n"
        " if 'experiment_record' in sources:\n"
        "  claims.append({'claim_id':'claim-3','claim_type':'RESULT','section':'Results','claim_text':'The controlled execution produced value five.','support_status':'SUPPORTED','evidence_refs':[ref(sources['experiment_record'],'evaluation.metrics.value')],'citation_ids':[],'limitations':['Controlled synthetic evidence']}); result='The controlled execution produced value five.'\n"
        " else:\n"
        "  claims.append({'claim_id':'claim-3','claim_type':'RESULT','section':'Results','claim_text':'Observed results are unavailable.','support_status':'UNAVAILABLE','evidence_refs':[],'citation_ids':[],'limitations':['No Experiment bound']}); result='Observed results are unavailable; no result is claimed.'\n"
        " dump('memory/claims.json',claims); dump('memory/citations.json',[citation])\n"
        " (root/'outputs/draft.md').write_text('# Controlled Evidence-Bound Draft\\n\\n## Introduction\\nThe selected abstract describes a bounded observation [1].\\n\\n## Proposed Method\\nThe study will evaluate the proposed comparison.\\n\\n## Results\\n'+result+'\\n\\n## References\\n[1] Controlled synthetic paper.\\n')\n",
        encoding="utf-8",
    )
    path.chmod(0o700)
    return path


def _answer(prompt: str) -> str:
    match = re.search(r"Type `([^`]+)`", prompt)
    assert match is not None
    return match.group(1)


@pytest.mark.parametrize("with_experiment", [False, True])
def test_real_writing_closes_truthfully_with_and_without_experiment(tmp_path: Path, with_experiment: bool) -> None:
    root, sources = _package(tmp_path / "capsule", with_experiment=with_experiment)
    result = runtime.run(
        root, "wfi-" + "4" * 32,
        codex_executable=str(_fake_harness(tmp_path)),
        approval_input=_answer, review_input=_answer,
    )
    assert result["status"] == "COMPLETED"
    artifact = json.loads((root / result["artifact"]["relative_path"]).read_text())
    assert artifact["schema"] == "manuscript-draft/v2"
    assert artifact["producer"]["capsule_id"] == REAL_WRITING_CAPSULE_ID
    assert artifact["source_artifacts"]["research_idea"] == sources["research_idea"]
    result_claim = next(item for item in artifact["claims"] if item["claim_type"] == "RESULT")
    assert result_claim["support_status"] == ("SUPPORTED" if with_experiment else "UNAVAILABLE")
    assert artifact["experiment_evidence_available"] is with_experiment
    assert len(list((root / "memory/progress/reports").glob("prv2-*.json"))) == 1


def test_outline_approval_and_package_admission_fail_closed(tmp_path: Path) -> None:
    root, sources = _package(tmp_path / "capsule", with_experiment=False)
    namespace = runtime._validator(root)
    assert namespace["validate"](root)["valid"] is True
    descriptor = json.loads((root / "workflow/real-writing.json").read_text())
    assert descriptor["target_words_fields"] == ["minimum", "maximum"]
    assert descriptor["evidence_reference_fields"] == [
        "artifact_id", "artifact_type", "sha256", "evidence_item", "location",
        "availability", "limitation",
    ]
    assert runtime._codex_environment()["PYTHONDONTWRITEBYTECODE"] == "1"
    undeclared = root / "inputs/undeclared.json"
    _write(undeclared, {})
    with pytest.raises(Exception, match="undeclared Capsule file"):
        namespace["validate"](root)
    undeclared.unlink()
    suffix_bypass = root / "outputs/draft.md.undeclared"
    suffix_bypass.write_text("not a declared dynamic path", encoding="utf-8")
    with pytest.raises(Exception, match="undeclared Capsule file"):
        namespace["validate"](root)
    suffix_bypass.unlink()
    with pytest.raises(Exception, match="unsafe relative path"):
        namespace["safe_relative_path"]("inputs/../escape.json")
    brief = {"document_type": "draft", "working_title": "Title", "target_audience": "owner", "target_words": {"minimum": 100, "maximum": 200}, "requested_sections": ["Intro"], "citation_style": "numeric", "abstract_requested": False, "owner_constraints": []}
    evidence = [{"section": "Intro", "support_status": "PLANNED", "evidence_refs": [{**sources["research_idea"], "evidence_item": "selected_idea", "location": "selected_idea", "availability": "AVAILABLE", "limitation": None}], "limitations": []}]
    outline = [{"heading": "Intro", "support_status": "PLANNED"}]
    with pytest.raises(runtime.RealWritingError, match="did not approve"):
        runtime._approve_outline(root, sources, brief, evidence, outline, runtime.canonical_hash(outline), lambda _: "approve wrong")
