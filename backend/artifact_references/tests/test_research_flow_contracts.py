from __future__ import annotations

from copy import deepcopy

import pytest

from backend.artifact_references.research_flow_contracts import (
    ARTIFACT_CONTRACTS,
    FUTURE_WORKFLOW_CONTRACTS,
    ResearchFlowContractError,
    build_selected_research_idea,
    canonical_artifact_bytes,
    validate_experiment_record,
    validate_manuscript_draft,
    validate_manuscript_draft_v2,
    validate_review_report,
    validate_review_report_v2,
    validate_selected_research_idea,
    validate_writing_review_revision,
)
from backend.workflow_packages.serialization import canonical_hash, canonical_json, sha256_bytes
from backend.project_workspaces.contracts import CoreCapabilityMaturity


ARTIFACT_A = "artifact-" + "a" * 32
ARTIFACT_B = "artifact-" + "b" * 32
ARTIFACT_C = "artifact-" + "c" * 32
ARTIFACT_D = "artifact-" + "d" * 32
CHECKSUM_A = "sha256:" + "a" * 64
CHECKSUM_B = "sha256:" + "b" * 64
CHECKSUM_C = "sha256:" + "c" * 64
CHECKSUM_D = "sha256:" + "d" * 64
CANDIDATE_A = "candidate-" + "a" * 16
CANDIDATE_B = "candidate-" + "b" * 16


def _ref(artifact_id: str, artifact_type: str, checksum: str) -> dict[str, str]:
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "sha256": checksum,
    }


def _idea(idea_id: str = "idea-001", *, status: str = "selected") -> dict:
    return {
        "idea_id": idea_id,
        "title": "A bounded research direction",
        "research_question": "What should be tested?",
        "motivation": "The supplied literature exposes a tension.",
        "literature_basis": [CANDIDATE_A],
        "observed_gap": "The bounded set does not resolve the tension.",
        "proposed_direction": "Run a controlled comparison.",
        "assumptions": ["The records are representative of the selected set."],
        "risks": ["The direction may not be globally novel."],
        "validation_needed": ["Broader novelty search."],
        "status": status,
    }


def _library() -> dict:
    return {
        "schema": "selected-paper-library/v1",
        "source_schemas": {
            "candidate_papers": "candidate-papers/v0.2",
            "selected_papers": "selected-papers/v0.2",
        },
        "source_checksums": {
            "candidate_papers_sha256": CHECKSUM_A,
            "selected_papers_sha256": CHECKSUM_B,
        },
        "papers": [{
            "candidate_id": CANDIDATE_A,
            "paper": {"candidate_id": CANDIDATE_A},
            "selection": {"candidate_id": CANDIDATE_A},
        }],
    }


def _candidates(*ideas: dict) -> dict:
    return {
        "schema": "candidate-ideas/v0.1",
        "source_artifact": _ref(
            ARTIFACT_A, "selected-paper-library/v1", CHECKSUM_A
        ),
        "ideas": list(ideas),
    }


def _selected() -> tuple[dict, bytes]:
    candidates = _candidates(_idea())
    content = (canonical_json(candidates) + "\n").encode()
    artifact = build_selected_research_idea(
        candidate_ideas=candidates,
        candidate_ideas_bytes=content,
        literature_library=_library(),
        literature_artifact_id=ARTIFACT_A,
        literature_checksum=CHECKSUM_A,
    )
    return artifact, content


def test_selected_research_idea_is_exact_deterministic_and_canonical() -> None:
    artifact, candidate_bytes = _selected()
    assert artifact["selected_idea"] == _idea()
    assert artifact["source_candidate_ideas"]["sha256"] == sha256_bytes(
        candidate_bytes
    )
    assert artifact["source_literature_artifact"] == _ref(
        ARTIFACT_A, "selected-paper-library/v1", CHECKSUM_A
    )
    assert canonical_artifact_bytes(artifact) == canonical_json(artifact).encode()
    assert build_selected_research_idea(
        candidate_ideas=_candidates(_idea()),
        candidate_ideas_bytes=candidate_bytes,
        literature_library=_library(),
        literature_artifact_id=ARTIFACT_A,
        literature_checksum=CHECKSUM_A,
    ) == artifact


@pytest.mark.parametrize("statuses", [[], ["candidate"], ["selected", "selected"]])
def test_selected_research_idea_requires_exactly_one_selected(
    statuses: list[str],
) -> None:
    ideas = [_idea(f"idea-{index + 1:03d}", status=status) for index, status in enumerate(statuses)]
    candidates = _candidates(*ideas)
    with pytest.raises(ResearchFlowContractError, match="exactly one"):
        build_selected_research_idea(
            candidate_ideas=candidates,
            candidate_ideas_bytes=canonical_json(candidates).encode(),
            literature_library=_library(),
            literature_artifact_id=ARTIFACT_A,
            literature_checksum=CHECKSUM_A,
        )


def test_selected_research_idea_rejects_duplicate_ids_and_unknown_literature() -> None:
    duplicated = _candidates(_idea(), _idea())
    with pytest.raises(ResearchFlowContractError, match="duplicate candidate idea"):
        build_selected_research_idea(
            candidate_ideas=duplicated,
            candidate_ideas_bytes=canonical_json(duplicated).encode(),
            literature_library=_library(),
            literature_artifact_id=ARTIFACT_A,
            literature_checksum=CHECKSUM_A,
        )


def test_selected_research_idea_rejects_invalid_candidate_schema_and_source_bytes() -> None:
    candidates = _candidates(_idea())
    invalid = deepcopy(candidates)
    invalid["schema"] = "candidate-ideas/v9"
    with pytest.raises(ResearchFlowContractError, match="schema mismatch"):
        build_selected_research_idea(
            candidate_ideas=invalid,
            candidate_ideas_bytes=b"{}",
            literature_library=_library(),
            literature_artifact_id=ARTIFACT_A,
            literature_checksum=CHECKSUM_A,
        )
    artifact, _ = _selected()
    with pytest.raises(ResearchFlowContractError, match="candidate source checksum"):
        validate_selected_research_idea(
            artifact,
            candidate_ideas=candidates,
            candidate_ideas_bytes=b"mutated candidate bytes",
            literature_library=_library(),
        )
    unknown = _idea()
    unknown["literature_basis"] = [CANDIDATE_B]
    with pytest.raises(ResearchFlowContractError, match="literature basis is unknown"):
        build_selected_research_idea(
            candidate_ideas=_candidates(unknown),
            candidate_ideas_bytes=b"{}",
            literature_library=_library(),
            literature_artifact_id=ARTIFACT_A,
            literature_checksum=CHECKSUM_A,
        )


def test_selected_research_idea_rejects_source_and_maturity_spoofing() -> None:
    artifact, content = _selected()
    spoofed = deepcopy(artifact)
    spoofed["core_capability_maturity"] = "SCAFFOLD_CORE"
    with pytest.raises(ResearchFlowContractError, match="producer Workflow Version"):
        validate_selected_research_idea(spoofed)
    spoofed = deepcopy(artifact)
    spoofed["source_literature_artifact"]["sha256"] = CHECKSUM_B
    with pytest.raises(ResearchFlowContractError, match="literature source checksum"):
        validate_selected_research_idea(
            spoofed,
            candidate_ideas=_candidates(_idea()),
            candidate_ideas_bytes=content,
            literature_library=_library(),
            expected_literature_artifact_id=ARTIFACT_A,
            expected_literature_checksum=CHECKSUM_A,
        )


def _manuscript() -> dict:
    return {
        "schema": "manuscript-draft/v1",
        "core_capability_maturity": "SCAFFOLD_CORE",
        "source_artifacts": {
            "research_idea": _ref(
                ARTIFACT_A, "selected-research-idea/v1", CHECKSUM_A
            ),
            "literature_library": _ref(
                ARTIFACT_B, "selected-paper-library/v1", CHECKSUM_B
            ),
            "experiment_record": None,
            "review_feedback": None,
            "prior_manuscript": None,
        },
        "title": "Draft title",
        "content_markdown": "# Draft\n",
    }


def test_manuscript_contract_required_and_optional_sources() -> None:
    value = _manuscript()
    assert validate_manuscript_draft(value) == value
    value["source_artifacts"]["experiment_record"] = _ref(
        ARTIFACT_C, "experiment-record/v1", CHECKSUM_C
    )
    assert validate_manuscript_draft(value)["source_artifacts"]["experiment_record"]
    with pytest.raises(ResearchFlowContractError, match="producer Workflow Version"):
        validate_manuscript_draft(
            value, producer_maturity=CoreCapabilityMaturity.REVIEWED_CORE
        )
    for role in ("research_idea", "literature_library"):
        invalid = _manuscript()
        invalid["source_artifacts"][role] = None
        with pytest.raises(ResearchFlowContractError):
            validate_manuscript_draft(invalid)


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda value: value["source_artifacts"]["research_idea"].update(artifact_type="review-report/v1"), "type mismatch"),
        (lambda value: value["source_artifacts"]["literature_library"].update(sha256="bad"), "checksum"),
        (lambda value: value.update(core_capability_maturity="UNKNOWN"), "maturity"),
        (lambda value: value.update(title=" "), "title"),
        (lambda value: value.update(content_markdown=[]), "content_markdown"),
    ],
)
def test_manuscript_contract_rejects_invalid_values(mutator, message: str) -> None:
    value = _manuscript()
    mutator(value)
    with pytest.raises(ResearchFlowContractError, match=message):
        validate_manuscript_draft(value)


def _evidence_ref(source: dict, item: str, *, limitation: str | None = None) -> dict:
    return {
        **source, "evidence_item": item, "location": item,
        "availability": "LIMITED" if limitation else "AVAILABLE",
        "limitation": limitation,
    }


def _manuscript_v2() -> dict:
    idea = _ref(ARTIFACT_A, "selected-research-idea/v1", CHECKSUM_A)
    library = _ref(ARTIFACT_B, "selected-paper-library/v1", CHECKSUM_B)
    sources = {"research_idea": idea, "literature_library": library, "experiment_record": None}
    brief = {
        "document_type": "research proposal", "working_title": "Bounded draft",
        "target_audience": "research owner", "target_words": {"minimum": 300, "maximum": 1200},
        "requested_sections": ["Introduction", "Method", "Results"],
        "citation_style": "numeric", "abstract_requested": False,
        "owner_constraints": ["Do not fabricate results"],
    }
    evidence_map = [
        {"section": "Introduction", "support_status": "SUPPORTED", "evidence_refs": [_evidence_ref(library, CANDIDATE_A, limitation="Abstract-level evidence only")], "limitations": ["No full text"]},
        {"section": "Method", "support_status": "PLANNED", "evidence_refs": [_evidence_ref(idea, "selected_idea.proposed_direction")], "limitations": []},
        {"section": "Results", "support_status": "UNAVAILABLE", "evidence_refs": [], "limitations": ["No Experiment bound"]},
    ]
    outline_value = [
        {"heading": "Introduction", "support_status": "SUPPORTED"},
        {"heading": "Method", "support_status": "PLANNED"},
        {"heading": "Results", "support_status": "UNAVAILABLE"},
    ]
    outline = {"sha256": canonical_hash(outline_value), "value": outline_value}
    approval_payload = {
        "outline_sha256": outline["sha256"], "brief_sha256": canonical_hash(brief),
        "evidence_map_sha256": canonical_hash(evidence_map),
        "source_artifacts_sha256": canonical_hash(sources),
        "approved_at": "2026-08-15T00:00:00Z", "decision": "APPROVED",
    }
    citations = [{
        "citation_id": "cite-1", "paper_id": CANDIDATE_A,
        "source_artifact": library, "evidence_scope": "ABSTRACT",
        "reference_markdown": "[1] Controlled synthetic paper.",
    }]
    claims = [
        {"claim_id": "claim-1", "claim_type": "LITERATURE", "section": "Introduction", "claim_text": "The selected abstract reports a bounded observation.", "support_status": "SUPPORTED", "evidence_refs": [_evidence_ref(library, CANDIDATE_A, limitation="Abstract-level evidence only")], "citation_ids": ["cite-1"], "limitations": ["No full text"]},
        {"claim_id": "claim-2", "claim_type": "PROPOSAL", "section": "Method", "claim_text": "The study will evaluate the proposed comparison.", "support_status": "PLANNED", "evidence_refs": [_evidence_ref(idea, "selected_idea.proposed_direction")], "citation_ids": [], "limitations": []},
        {"claim_id": "claim-3", "claim_type": "RESULT", "section": "Results", "claim_text": "Observed results are unavailable.", "support_status": "UNAVAILABLE", "evidence_refs": [], "citation_ids": [], "limitations": ["No Experiment bound"]},
    ]
    title = "Bounded draft"
    content = "# Bounded draft\n\nThe study will evaluate a proposed comparison. Results are unavailable.\n"
    draft_sha = canonical_hash({"title": title, "content_markdown": content, "claims": claims, "citations": citations})
    review_payload = {"draft_sha256": draft_sha, "reviewed_at": "2026-08-15T00:05:00Z", "decision": "APPROVED"}
    return {
        "schema": "manuscript-draft/v2", "core_capability_maturity": "REVIEWED_CORE",
        "producer": {"workflow_instance_id": "wfi-" + "1" * 32, "capsule_id": "capsule-" + "2" * 32, "capsule_version": "0.5.0", "execution_round": 1},
        "source_artifacts": sources, "writing_brief": brief, "evidence_map": evidence_map,
        "approved_outline": outline,
        "outline_approval": {"sha256": canonical_hash(approval_payload), **approval_payload},
        "title": title, "content_markdown": content, "claims": claims, "citations": citations,
        "experiment_evidence_available": False, "unsupported_areas": ["Results"],
        "limitations": ["Controlled synthetic evidence only"],
        "owner_review": {"sha256": canonical_hash(review_payload), **review_payload},
    }


def test_manuscript_v2_preserves_exact_evidence_and_v1_authority() -> None:
    value = _manuscript_v2()
    assert validate_manuscript_draft_v2(value) == value
    assert validate_manuscript_draft(_manuscript())["schema"] == "manuscript-draft/v1"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value["claims"][0].update(evidence_refs=[]), "SUPPORTED claim"),
        (lambda value: value["claims"][2].update(support_status="SUPPORTED"), "SUPPORTED claim"),
        (lambda value: value["citations"][0].update(source_artifact=_ref(ARTIFACT_C, "selected-paper-library/v1", CHECKSUM_C)), "exact selected library"),
        (lambda value: value["approved_outline"]["value"][0].update(heading="Drifted"), "checksum mismatch"),
    ],
)
def test_manuscript_v2_fails_closed_on_evidence_or_approval_drift(mutation, message: str) -> None:
    value = _manuscript_v2()
    mutation(value)
    with pytest.raises(ResearchFlowContractError, match=message):
        validate_manuscript_draft_v2(value)


def _review() -> dict:
    return {
        "schema": "review-report/v1",
        "core_capability_maturity": "SCAFFOLD_CORE",
        "source_manuscript": _ref(
            ARTIFACT_A, "manuscript-draft/v1", CHECKSUM_A
        ),
        "supporting_artifacts": [],
        "summary": "A bounded contract-only review.",
        "major_issues": [{
            "issue_id": "major-1", "title": "Evidence", "description": "Clarify it."
        }],
        "minor_issues": [],
        "requested_revisions": [{
            "revision_id": "revision-1", "description": "Clarify evidence.",
            "priority": "MAJOR",
        }],
        "recommendation": "REVISION",
    }


def _review_v2() -> tuple[dict, dict, dict]:
    manuscript = _manuscript_v2()
    manuscript_ref = _ref(ARTIFACT_C, "manuscript-draft/v2", CHECKSUM_C)
    idea = manuscript["source_artifacts"]["research_idea"]
    library = manuscript["source_artifacts"]["literature_library"]
    support = [idea, library]
    scope_value = {
        "manuscript_identity": manuscript_ref,
        "available_evidence": support,
        "categories": [
            "EVIDENCE_SUPPORT", "CLAIM_SCOPE", "CITATION",
            "METHOD_CONSISTENCY", "RESULT_SUPPORT", "REPRODUCIBILITY",
        ],
        "known_evidence_limitations": ["Literature is abstract-level only"],
        "owner_focus": [],
    }
    scope = {"sha256": canonical_hash(scope_value), "value": scope_value}
    approval_payload = {
        "scope_sha256": scope["sha256"],
        "manuscript_sha256": manuscript_ref["sha256"],
        "bound_artifacts_sha256": canonical_hash(support),
        "approved_at": "2026-08-15T01:00:00Z", "decision": "APPROVED",
    }
    approval = {"sha256": canonical_hash(approval_payload), **approval_payload}
    availability = [
        {
            **library, "evidence_item": CANDIDATE_A, "location": CANDIDATE_A,
            "availability": "SCOPE_LIMITED",
            "limitation": "Abstract-level evidence only",
        },
        {
            **idea, "evidence_item": "selected_idea.proposed_direction",
            "location": "selected_idea.proposed_direction",
            "availability": "AVAILABLE", "limitation": None,
        },
    ]
    issues = [{
        "issue_id": "issue-1", "category": "CLAIM_SCOPE", "severity": "MAJOR",
        "target": {"section": "Introduction", "claim_id": "claim-1"},
        "summary": "The claim exceeds the supplied abstract-level evidence.",
        "evidence_refs": [_evidence_ref(
            library, CANDIDATE_A, limitation="Abstract-level evidence only"
        )],
        "recommended_action": "Narrow the claim to the represented abstract scope.",
        "blocking": True,
    }]
    report_payload = {
        "source_manuscript": manuscript_ref, "supporting_artifacts": support,
        "review_scope": scope, "scope_approval": approval,
        "evidence_availability": availability,
        "assessment": "REVISION_REQUIRED",
        "summary": "One bounded evidence-scope revision is required.",
        "issues": issues,
        "limitations": ["This is a bounded evidence audit, not universal peer review."],
    }
    owner_payload = {
        "review_result_sha256": canonical_hash(report_payload),
        "reviewed_at": "2026-08-15T01:05:00Z", "decision": "APPROVED",
    }
    report = {
        "schema": "review-report/v2", "core_capability_maturity": "REVIEWED_CORE",
        "producer": {
            "workflow_instance_id": "wfi-" + "4" * 32,
            "capsule_id": "capsule-" + "5" * 32,
            "capsule_version": "0.5.0", "execution_round": 1,
        },
        **report_payload,
        "owner_review": {"sha256": canonical_hash(owner_payload), **owner_payload},
    }
    bound = {
        "manuscript": manuscript_ref, "research_idea": idea,
        "literature_library": library, "experiment_record": None,
    }
    return report, manuscript, bound


def test_review_v2_is_structured_exact_and_preserves_v1() -> None:
    report, manuscript, bound = _review_v2()
    assert validate_review_report_v2(
        report, manuscript=manuscript, bound_inputs=bound,
    ) == report
    assert validate_review_report(_review())["schema"] == "review-report/v1"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda value: value["issues"][0]["target"].update(claim_id="claim-missing"),
            "unknown claim",
        ),
        (
            lambda value: value.update(assessment="NO_BLOCKING_ISSUES"),
            "conflicts with a blocking issue",
        ),
        (
            lambda value: value["issues"][0].update(summary="The paper should REJECT."),
            "prohibited publication semantics",
        ),
    ],
)
def test_review_v2_fails_closed_on_structured_contract_drift(mutation, message: str) -> None:
    report, manuscript, bound = _review_v2()
    mutation(report)
    with pytest.raises(ResearchFlowContractError, match=message):
        validate_review_report_v2(report, manuscript=manuscript, bound_inputs=bound)


def test_review_contract_and_writing_revision_cross_reference() -> None:
    review = _review()
    review["source_manuscript"] = _ref(
        ARTIFACT_D, "manuscript-draft/v1", CHECKSUM_D
    )
    assert validate_review_report(review)["recommendation"] == "REVISION"
    revision = _manuscript()
    revision["source_artifacts"]["prior_manuscript"] = _ref(
        ARTIFACT_D, "manuscript-draft/v1", CHECKSUM_D
    )
    revision["source_artifacts"]["review_feedback"] = _ref(
        ARTIFACT_C, "review-report/v1", CHECKSUM_C
    )
    validate_writing_review_revision(manuscript=revision, review=review)
    bad = _review()
    bad["source_manuscript"] = _ref(
        ARTIFACT_B, "manuscript-draft/v1", CHECKSUM_B
    )
    with pytest.raises(ResearchFlowContractError, match="different prior"):
        validate_writing_review_revision(manuscript=revision, review=bad)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(recommendation="ACCEPT_PROBABILITY_93"),
        lambda value: value["minor_issues"].append(dict(value["major_issues"][0])),
        lambda value: value["requested_revisions"].append(dict(value["requested_revisions"][0])),
        lambda value: value["requested_revisions"][0].update(priority="CRITICAL"),
        lambda value: value.update(core_capability_maturity="prototype"),
    ],
)
def test_review_contract_rejects_unsupported_or_duplicate_fields(mutation) -> None:
    value = _review()
    mutation(value)
    with pytest.raises(ResearchFlowContractError):
        validate_review_report(value)


def _experiment(maturity: str = "SCAFFOLD_CORE") -> dict:
    return {
        "schema": "experiment-record/v1",
        "core_capability_maturity": maturity,
        "mode": "IDEA_EXPERIMENT",
        "source_artifacts": [_ref(
            ARTIFACT_A, "selected-research-idea/v1", CHECKSUM_A
        )],
        "execution_status": "PLACEHOLDER_NOT_EXECUTED",
        "plan": {
            "objective": "Specify a future test.",
            "hypothesis": None,
            "method": "Contract-only placeholder.",
            "metrics": ["accuracy"],
            "baselines": [],
        },
        "actual_results": None,
        "limitations": ["No experiment was executed."],
    }


def test_experiment_contract_enforces_scaffold_fake_result_boundary() -> None:
    assert validate_experiment_record(_experiment())["actual_results"] is None
    completed = _experiment()
    completed["execution_status"] = "COMPLETED"
    with pytest.raises(ResearchFlowContractError, match="cannot claim"):
        validate_experiment_record(completed)
    fake = _experiment()
    fake["actual_results"] = {
        "summary": "Fabricated", "metrics": [], "observations": []
    }
    with pytest.raises(ResearchFlowContractError, match="cannot claim"):
        validate_experiment_record(fake)


def test_reviewed_experiment_accepts_real_result_shape_and_rejects_bad_metric() -> None:
    value = _experiment("REVIEWED_CORE")
    value["execution_status"] = "COMPLETED"
    value["actual_results"] = {
        "summary": "Observed result",
        "metrics": [{"name": "accuracy", "value": 0.8, "unit": None}],
        "observations": ["Bounded fixture."],
    }
    assert validate_experiment_record(value)["actual_results"]["metrics"][0]["value"] == 0.8
    value["actual_results"]["metrics"][0]["value"] = {"fabricated": True}
    with pytest.raises(ResearchFlowContractError, match="number or string"):
        validate_experiment_record(value)


def test_downstream_dependency_map_is_production_seeded_and_exact() -> None:
    assert set(FUTURE_WORKFLOW_CONTRACTS) == {
        "writing", "review", "reproduction-experiment"
    }
    writing = FUTURE_WORKFLOW_CONTRACTS["writing"]
    assert [(item.requirement_key, item.artifact_type, item.required) for item in writing.inputs] == [
        ("research_idea", "selected-research-idea/v1", True),
        ("literature_library", "selected-paper-library/v1", True),
        ("experiment_record", "experiment-record/v2", False),
    ]
    review = FUTURE_WORKFLOW_CONTRACTS["review"]
    assert [(item.requirement_key, item.artifact_type, item.required) for item in review.inputs] == [
        ("manuscript", "manuscript-draft/v2", True),
        ("research_idea", "selected-research-idea/v1", False),
        ("literature_library", "selected-paper-library/v1", False),
        ("experiment_record", "experiment-record/v2", False),
    ]
    assert all(
        dependency.selection_policy == "EXPLICIT_SPECIFIC_ARTIFACT"
        and dependency.cardinality == "ONE"
        and dependency.project_scope == "SAME_PROJECT"
        and dependency.identity_binding == "ARTIFACT_ID_AND_CHECKSUM"
        for contract in FUTURE_WORKFLOW_CONTRACTS.values()
        for dependency in contract.inputs
    )
    assert all(contract.production_seeded for contract in FUTURE_WORKFLOW_CONTRACTS.values())
    assert all(
        ARTIFACT_CONTRACTS[artifact_type].production_producer_available
        for artifact_type in (
            "manuscript-draft/v1", "manuscript-draft/v2",
            "review-report/v1", "review-report/v2", "experiment-record/v1"
        )
    )
