from __future__ import annotations

import json
import stat
from copy import deepcopy
from pathlib import Path

import pytest

from backend.artifact_references.tests.test_research_flow_contracts import (
    _library, _manuscript_v2, _review_v2,
)
from backend.workflow_packages.production_workflows import (
    REAL_WRITING_CAPSULE_CHECKSUM,
    WRITING_REVISION_CAPSULE_CHECKSUM,
    build_writing_revision_v0_6_package,
)
from backend.workflow_packages.serialization import canonical_hash, canonical_json, sha256_bytes
from backend.workflow_packages.writing_revision_runtime import WritingRevisionError, run


def _write_json(path: Path, value: object) -> bytes:
    content = (canonical_json(value) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(content)
    return content


def _ref(label: str, artifact_type: str, content: bytes) -> dict[str, str]:
    return {
        "artifact_id": "artifact-" + label * 32,
        "artifact_type": artifact_type,
        "sha256": sha256_bytes(content),
    }


def _replace_identity(value: object, old: dict, new: dict) -> None:
    if isinstance(value, dict):
        if all(value.get(key) == old[key] for key in old):
            value.update(new)
        for nested in value.values():
            _replace_identity(nested, old, new)
    elif isinstance(value, list):
        for nested in value:
            _replace_identity(nested, old, new)


def _refresh_prior(prior: dict) -> None:
    sources = prior["source_artifacts"]
    evidence_map = prior["evidence_map"]
    outline = prior["approved_outline"]
    approval_payload = {
        "outline_sha256": outline["sha256"],
        "brief_sha256": canonical_hash(prior["writing_brief"]),
        "evidence_map_sha256": canonical_hash(evidence_map),
        "source_artifacts_sha256": canonical_hash(sources),
        "approved_at": prior["outline_approval"]["approved_at"],
        "decision": "APPROVED",
    }
    prior["outline_approval"] = {"sha256": canonical_hash(approval_payload), **approval_payload}
    draft_sha = canonical_hash({
        "title": prior["title"], "content_markdown": prior["content_markdown"],
        "claims": prior["claims"], "citations": prior["citations"],
    })
    review_payload = {
        "draft_sha256": draft_sha, "reviewed_at": prior["owner_review"]["reviewed_at"],
        "decision": "APPROVED",
    }
    prior["owner_review"] = {"sha256": canonical_hash(review_payload), **review_payload}


def _fixture(root: Path, *, missing_evidence: bool = False) -> tuple[str, dict[str, str]]:
    built = build_writing_revision_v0_6_package(
        project_id="project-" + "1" * 32, project_name="Controlled W2",
        output_root=root, package_id="writing-revision-controlled",
        research_topic="synthetic",
    )
    capsule = built.package_root
    library = _library(); library_bytes = _write_json(capsule / "inputs/selected-paper-library.json", library)
    idea = {"schema": "selected-research-idea/v1", "selected_idea": {"proposed_direction": "A bounded comparison."}}
    idea_bytes = _write_json(capsule / "inputs/selected-research-idea.json", idea)
    library_ref = _ref("b", "selected-paper-library/v1", library_bytes)
    idea_ref = _ref("a", "selected-research-idea/v1", idea_bytes)

    prior = _manuscript_v2()
    old_idea = deepcopy(prior["source_artifacts"]["research_idea"])
    old_library = deepcopy(prior["source_artifacts"]["literature_library"])
    _replace_identity(prior, old_idea, idea_ref); _replace_identity(prior, old_library, library_ref)
    _refresh_prior(prior)
    prior_bytes = _write_json(capsule / "inputs/prior-manuscript.json", prior)
    prior_ref = _ref("c", "manuscript-draft/v2", prior_bytes)

    review, _, _ = _review_v2()
    review["source_manuscript"] = prior_ref
    review["supporting_artifacts"] = [idea_ref, library_ref]
    review["issues"][0]["evidence_refs"] = [] if missing_evidence else [{
        **library_ref, "evidence_item": "candidate-" + "a" * 16,
        "location": "candidate-" + "a" * 16, "availability": "LIMITED",
        "limitation": "Abstract-level evidence only",
    }]
    if missing_evidence:
        review["issues"][0]["recommended_action"] = "Add evidence that is not among the bound Artifacts."
    review_bytes = _write_json(capsule / "inputs/review-report.json", review)
    review_ref = _ref("d", "review-report/v2", review_bytes)
    workflow_instance_id = "wfi-" + "6" * 32
    records = {
        "prior_manuscript": prior_ref, "causal_review": review_ref,
        "research_idea": idea_ref, "literature_library": library_ref,
    }
    _write_json(capsule / "memory/input-provenance.json", {
        "schema_version": "reagent.writing-revision-input-provenance/v0.1",
        "workflow_instance_id": workflow_instance_id, "artifacts": records,
    })
    return workflow_instance_id, {"capsule": str(capsule), "review": review_ref["artifact_id"]}


def _fake_codex(path: Path, *, missing_evidence: bool = False) -> Path:
    disposition = "NOT_ADDRESSED" if missing_evidence else "ADDRESSED"
    limitation = "Required evidence is not bound." if missing_evidence else None
    script = f'''#!/usr/bin/env python3
import json
from pathlib import Path
root = Path.cwd()
instruction = __import__("sys").argv[-1]
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\\n")
if "ISSUE RECONCILIATION" in instruction:
    review = json.loads((root / "inputs/review-report.json").read_text())
    source = json.loads((root / "memory/input-provenance.json").read_text())["artifacts"]["literature_library"]
    evidence = [] if {missing_evidence!r} else [{{**source, "evidence_item": "candidate-aaaaaaaaaaaaaaaa", "location": "candidate-aaaaaaaaaaaaaaaa", "availability": "LIMITED", "limitation": "Abstract-level evidence only"}}]
    write(root / "memory/revision-plan.json", [{{"issue_id": review["issues"][0]["issue_id"], "intended_disposition": "{disposition}", "planned_change": "Narrow the claim or preserve the evidence limitation.", "affected_section": "Introduction", "affected_claims": ["claim-1"], "evidence_to_use": evidence, "known_limitation": {limitation!r}}}])
else:
    prior = json.loads((root / "inputs/prior-manuscript.json").read_text())
    claims = prior["claims"]
    if not {missing_evidence!r}:
        claims[0]["claim_text"] = "The selected abstract reports a bounded observation."
    write(root / "memory/claims.json", claims)
    write(root / "memory/citations.json", prior["citations"])
    write(root / "memory/issue-accounting.json", [{{"issue_id": "issue-1", "disposition": "{disposition}", "change_summary": "Applied only the evidence-permitted revision.", "changed_sections": ["Introduction"], "changed_claims": ["claim-1"], "remaining_limitation": {limitation!r}}}])
    (root / "outputs/revised-draft.md").write_text("# Bounded revised draft\\n\\nThe selected abstract reports a bounded observation.\\n")
'''
    path.write_text(script); path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


@pytest.mark.parametrize(("missing_evidence", "remaining"), [(False, 0), (True, 1)])
def test_writing_revision_runtime_closes_addressable_and_missing_evidence_honestly(
    tmp_path: Path, missing_evidence: bool, remaining: int,
) -> None:
    workflow_instance_id, state = _fixture(tmp_path / "package", missing_evidence=missing_evidence)
    capsule = Path(state["capsule"]); fake = _fake_codex(tmp_path / "fake-codex", missing_evidence=missing_evidence)
    result = run(
        capsule, workflow_instance_id, codex_executable=str(fake),
        approval_input=lambda prompt: "approve " + prompt.split("approve ", 1)[1].split("`", 1)[0],
        review_input=lambda prompt: "finalize " + prompt.split("finalize ", 1)[1].split("`", 1)[0],
    )
    artifact = json.loads((capsule / result["artifact"]["relative_path"]).read_text())
    assert artifact["schema"] == "manuscript-draft/v3"
    assert artifact["remaining_blocking_issue_count"] == remaining
    assert artifact["issue_accounting"][0]["disposition"] == (
        "NOT_ADDRESSED" if missing_evidence else "ADDRESSED"
    )
    assert len(list((capsule / "memory/progress/reports").glob("*.json"))) == 1
    with pytest.raises(WritingRevisionError, match="terminal Progress"):
        run(capsule, workflow_instance_id, codex_executable=str(fake))


def test_writing_revision_capsule_is_new_and_preserves_w1_identity(tmp_path: Path) -> None:
    assert WRITING_REVISION_CAPSULE_CHECKSUM != REAL_WRITING_CAPSULE_CHECKSUM
    built = build_writing_revision_v0_6_package(
        project_id="project-" + "1" * 32, project_name="W2",
        output_root=tmp_path, package_id="w2", research_topic="synthetic",
    )
    assert built.validation.valid and built.archive_validation.valid
