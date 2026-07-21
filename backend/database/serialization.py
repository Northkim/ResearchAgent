"""Stable JSON representation for immutable Workflow definitions."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from backend.domain.enums import WorkflowStepKind
from backend.domain.models import Workflow, WorkflowStep
from backend.persistence.models._immutability import thaw_json


def workflow_to_document(workflow: Workflow) -> dict[str, Any]:
    return {
        "id": workflow.id,
        "version": workflow.version,
        "name": workflow.name,
        "schema_version": workflow.schema_version,
        "input_schema": thaw_json(workflow.input_schema),
        "steps": [
            {
                "id": step.id,
                "kind": step.kind.value,
                "needs": list(step.needs),
                "uses": step.uses,
                "input_mapping": thaw_json(step.input_mapping),
                "timeout_seconds": step.timeout_seconds,
                "max_attempts": step.max_attempts,
                "retry_backoff": step.retry_backoff,
                "retry_initial_seconds": step.retry_initial_seconds,
                "retry_max_seconds": step.retry_max_seconds,
                "checkpoint_policy": step.checkpoint_policy,
                "approval_policy": step.approval_policy,
            }
            for step in workflow.steps
        ],
        "outputs": thaw_json(workflow.outputs),
    }


def workflow_from_document(document: Mapping[str, Any]) -> Workflow:
    steps = tuple(
        WorkflowStep(
            id=str(step["id"]),
            kind=WorkflowStepKind(str(step["kind"])),
            needs=tuple(str(item) for item in step.get("needs", ())),
            uses=str(step["uses"]) if step.get("uses") is not None else None,
            input_mapping=dict(step.get("input_mapping", {})),
            timeout_seconds=int(step.get("timeout_seconds", 300)),
            max_attempts=int(step.get("max_attempts", 1)),
            retry_backoff=str(step.get("retry_backoff", "exponential")),
            retry_initial_seconds=float(step.get("retry_initial_seconds", 1.0)),
            retry_max_seconds=float(step.get("retry_max_seconds", 30.0)),
            checkpoint_policy=str(step.get("checkpoint_policy", "after_success")),
            approval_policy=(
                str(step["approval_policy"])
                if step.get("approval_policy") is not None
                else None
            ),
        )
        for step in document["steps"]
    )
    return Workflow(
        id=str(document["id"]),
        version=str(document["version"]),
        name=str(document["name"]),
        schema_version=str(document.get("schema_version", "reagent/v1alpha1")),
        input_schema=dict(document.get("input_schema", {})),
        steps=steps,
        outputs=dict(document.get("outputs", {})),
    )


def workflow_document_hash(document: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
