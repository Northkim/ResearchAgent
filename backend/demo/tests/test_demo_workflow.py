import json

import pytest

from backend.demo.seed import (
    DEMO_WORKFLOW_HASH,
    DEMO_WORKFLOW_ID,
    DEMO_WORKFLOW_VERSION,
    load_demo_workflow,
    DemoSeedError,
    RESEARCH_WORKFLOW_HASH,
    RESEARCH_WORKFLOW_VERSION,
    load_research_workflow,
)
from backend.database.serialization import workflow_document_hash, workflow_to_document


def test_demo_workflow_matches_the_frozen_contract() -> None:
    workflow = load_demo_workflow()

    assert (workflow.id, workflow.version) == (
        DEMO_WORKFLOW_ID,
        DEMO_WORKFLOW_VERSION,
    )
    assert workflow_document_hash(workflow_to_document(workflow)) == DEMO_WORKFLOW_HASH
    assert [step.id for step in workflow.steps] == [
        "search",
        "approve_sources",
        "summarize",
    ]


def test_research_workflow_matches_frozen_v2_contract() -> None:
    workflow = load_research_workflow()
    assert workflow.version == RESEARCH_WORKFLOW_VERSION
    assert (
        workflow_document_hash(workflow_to_document(workflow))
        == RESEARCH_WORKFLOW_HASH
    )
    assert len(workflow.steps) == 10


def test_research_workflow_hash_conflict_fails_closed(tmp_path) -> None:
    canonical = workflow_to_document(load_research_workflow())
    canonical["name"] = "Mutated workflow"
    fixture = tmp_path / "mutated-v2.json"
    fixture.write_text(json.dumps(canonical), encoding="utf-8")

    with pytest.raises(DemoSeedError, match="canonical hash"):
        load_research_workflow(fixture)
