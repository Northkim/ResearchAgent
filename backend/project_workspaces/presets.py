"""Reviewed product setup presets that resolve to ordinary Workflow Instances."""

from __future__ import annotations

from backend.workflow_packages.production_workflows import (
    EXPERIMENT_WORKFLOW_ID,
    IDEA_DISCOVERY_WORKFLOW_ID,
    LITERATURE_SEARCH_WORKFLOW_ID,
    REVIEW_WORKFLOW_ID,
    WRITING_WORKFLOW_ID,
)

LITERATURE_ONLY = "literature-only"
LITERATURE_AND_IDEA = "literature-and-idea"
FULL_RESEARCH = "full-research"
CUSTOM = "custom"
PROJECT_SETUP_KEYS = frozenset({
    LITERATURE_ONLY, LITERATURE_AND_IDEA, FULL_RESEARCH, CUSTOM,
})

PRESET_WORKFLOW_IDS: dict[str, tuple[str, ...]] = {
    LITERATURE_ONLY: (LITERATURE_SEARCH_WORKFLOW_ID,),
    LITERATURE_AND_IDEA: (
        LITERATURE_SEARCH_WORKFLOW_ID,
        IDEA_DISCOVERY_WORKFLOW_ID,
    ),
    FULL_RESEARCH: (
        LITERATURE_SEARCH_WORKFLOW_ID,
        IDEA_DISCOVERY_WORKFLOW_ID,
        WRITING_WORKFLOW_ID,
        REVIEW_WORKFLOW_ID,
        EXPERIMENT_WORKFLOW_ID,
    ),
}


def resolve_project_setup(
    setup: str, custom_workflow_definition_ids: tuple[str, ...]
) -> tuple[str, ...]:
    """Resolve only reviewed server-side presets; custom remains Registry validated."""

    if setup not in PROJECT_SETUP_KEYS:
        raise ValueError("unknown Project Workflow setup")
    if setup != CUSTOM:
        if custom_workflow_definition_ids:
            raise ValueError("custom Workflow choices require the custom setup")
        return PRESET_WORKFLOW_IDS[setup]
    if not custom_workflow_definition_ids:
        raise ValueError("custom setup requires at least one Workflow")
    if len(custom_workflow_definition_ids) > 20:
        raise ValueError("custom setup exceeds the Workflow selection bound")
    if len(set(custom_workflow_definition_ids)) != len(
        custom_workflow_definition_ids
    ):
        raise ValueError("custom setup contains duplicate Workflows")
    return custom_workflow_definition_ids
