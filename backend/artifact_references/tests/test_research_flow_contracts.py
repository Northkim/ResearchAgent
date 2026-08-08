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
    validate_review_report,
    validate_selected_research_idea,
    validate_writing_review_revision,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes
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


def test_future_dependency_map_is_contract_only_and_exact() -> None:
    assert set(FUTURE_WORKFLOW_CONTRACTS) == {
        "writing", "review", "reproduction-experiment"
    }
    writing = FUTURE_WORKFLOW_CONTRACTS["writing"]
    assert [(item.requirement_key, item.artifact_type, item.required) for item in writing.inputs] == [
        ("research_idea", "selected-research-idea/v1", True),
        ("literature_library", "selected-paper-library/v1", True),
        ("experiment_record", "experiment-record/v1", False),
        ("review_feedback", "review-report/v1", False),
        ("prior_manuscript", "manuscript-draft/v1", False),
    ]
    assert all(
        dependency.selection_policy == "EXPLICIT_SPECIFIC_ARTIFACT"
        and dependency.cardinality == "ONE"
        and dependency.project_scope == "SAME_PROJECT"
        and dependency.identity_binding == "ARTIFACT_ID_AND_CHECKSUM"
        for contract in FUTURE_WORKFLOW_CONTRACTS.values()
        for dependency in contract.inputs
    )
    assert all(not contract.production_seeded for contract in FUTURE_WORKFLOW_CONTRACTS.values())
    assert not ARTIFACT_CONTRACTS["manuscript-draft/v1"].production_producer_available
