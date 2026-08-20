"""Shared Owner-facing Workflow role and ordinal labels."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass


WRITING_ROLE_LABELS = {
    "INITIAL": "Initial Writing",
    "REVISION": "Writing Revision",
}


@dataclass(frozen=True, slots=True)
class OwnerWorkflowLabelInput:
    workflow_instance_id: str
    workflow_definition_id: str
    base_label: str
    writing_role: str | None = None


def writing_role_label(writing_role: str | None) -> str | None:
    return WRITING_ROLE_LABELS.get(writing_role or "")


def owner_workflow_labels(
    values: Iterable[OwnerWorkflowLabelInput],
) -> dict[str, str]:
    """Use explicit roles and stable exact-ID ordinals, never row order."""

    grouped: dict[tuple[str, str], list[OwnerWorkflowLabelInput]] = defaultdict(list)
    result: dict[str, str] = {}
    for value in values:
        role_label = writing_role_label(value.writing_role)
        if role_label is not None:
            result[value.workflow_instance_id] = role_label
        else:
            grouped[(value.workflow_definition_id, value.base_label)].append(value)
    for (_definition_id, base_label), items in grouped.items():
        ordered = sorted(items, key=lambda item: item.workflow_instance_id)
        for index, item in enumerate(ordered, 1):
            result[item.workflow_instance_id] = (
                base_label if len(ordered) == 1 else f"{base_label} #{index}"
            )
    return result
