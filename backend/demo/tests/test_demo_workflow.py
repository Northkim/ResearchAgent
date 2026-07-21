from backend.demo.seed import (
    DEMO_WORKFLOW_HASH,
    DEMO_WORKFLOW_ID,
    DEMO_WORKFLOW_VERSION,
    load_demo_workflow,
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
