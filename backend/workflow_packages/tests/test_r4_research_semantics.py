from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from backend.artifact_references.forward_downstream_contracts import (
    ForwardDownstreamContractError,
)
from backend.artifact_references.review_contract_compatibility import (
    validate_review_report_v3,
)
from backend.artifact_references.tests.test_revision_optional_review_support import (
    _case,
    _evidence,
    _rehash_review,
)
from backend.workflow_packages.production_workflows import (
    LITERATURE_SEARCH_V0_6_PROMPT_VERSION,
    LITERATURE_SEARCH_V0_6_SKILL_VERSION,
    LITERATURE_SEARCH_V0_6_WORKFLOW_VERSION,
    LITERATURE_SEARCH_V0_8_CAPSULE_VERSION,
    build_literature_search_v0_8_package,
    literature_search_v0_6_workflow_document,
)


PROJECT_ID = "project-" + "4" * 32


def test_forward_literature_uses_bounded_research_strategy_not_skill_authority(
    tmp_path: Path,
) -> None:
    result = build_literature_search_v0_8_package(
        project_id=PROJECT_ID,
        project_name="Research strategy",
        research_topic="How does preprocessing affect local classifiers?",
        output_root=tmp_path,
        package_id="r4-forward-literature",
    )
    manifest = json.loads(
        (result.package_root / "package-manifest.json").read_text()
    )
    workflow = literature_search_v0_6_workflow_document()
    assert manifest["workflow_version"] == LITERATURE_SEARCH_V0_6_WORKFLOW_VERSION
    assert manifest["package_template_version"] == LITERATURE_SEARCH_V0_8_CAPSULE_VERSION
    assert manifest["skill_pins"][0]["semantic_version"] == LITERATURE_SEARCH_V0_6_SKILL_VERSION
    assert manifest["prompt_pins"][0]["version"] == LITERATURE_SEARCH_V0_6_PROMPT_VERSION
    assert workflow["query_strategy"]["agent_query_families"] == [
        "DIRECT", "SUPPORTING", "CONTEXTUAL", "BACKGROUND",
    ]
    assert workflow["query_strategy"]["global_novelty_claim"] is False
    assert workflow["query_strategy"]["user_skill_scientific_authority"] is False

    for relative in (
        "AGENT.md",
        "workflow/prompts/one-round.md",
        "workflow/skills/literature-search/SKILL.md",
    ):
        text = (result.package_root / relative).read_text()
        assert "DIRECT" in text and "SUPPORTING" in text
        assert "CONTEXTUAL" in text and "BACKGROUND" in text
        assert "do not determine scientific truth" in text
        assert "Never infer global novelty" in text


def test_review_preserves_authoring_provenance_but_cannot_use_omitted_source() -> None:
    revision, manuscript, review, bound = _case(include_idea=False)
    del revision
    review_inputs = {
        "manuscript": bound["prior_manuscript"],
        "literature_library": bound["literature_library"],
    }
    validated = validate_review_report_v3(
        review,
        manuscript=manuscript,
        bound_inputs=review_inputs,
    )
    idea_availability = next(
        item for item in validated["evidence_availability"]
        if item["artifact_type"] == "selected-research-idea/v1"
    )
    assert idea_availability["availability"] == "UNAVAILABLE"
    assert "not explicitly bound to Review" in idea_availability["limitation"]
    assert manuscript["source_artifacts"]["research_idea"] == bound["research_idea"]

    invalid = deepcopy(review)
    invalid["issues"][0]["evidence_refs"] = [_evidence(bound["research_idea"])]
    _rehash_review(invalid)
    with pytest.raises(
        ForwardDownstreamContractError,
        match="not explicitly bound",
    ):
        validate_review_report_v3(
            invalid,
            manuscript=manuscript,
            bound_inputs=review_inputs,
        )
