"""Canonical construction and hashing for exact resolved approval actions."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from backend.agent_runtime._immutability import thaw_json


def build_resolved_approval_action(
    *,
    project_id: str,
    workflow_id: str,
    workflow_version: str,
    workflow_run_id: str,
    approval_step_id: str,
    step_run_id: str,
    attempt: int,
    policy_key: str,
    approval_role: str,
    expires_at: datetime,
    resolved_inputs: Mapping[str, Any],
    skill_versions: Mapping[str, str],
) -> dict[str, Any]:
    """Return canonical JSON data binding the exact Engine-resolved action."""

    return {
        "kind": "workflow_approval",
        "project_id": project_id,
        "workflow_id": workflow_id,
        "workflow_version": workflow_version,
        "workflow_run_id": workflow_run_id,
        "approval_step_id": approval_step_id,
        "step_run_id": step_run_id,
        "attempt": attempt,
        "policy_key": policy_key,
        "approval_role": approval_role,
        "expires_at": expires_at.isoformat(),
        "resolved_inputs": thaw_json(resolved_inputs),
        "skill_versions": dict(sorted(skill_versions.items())),
    }


def approval_action_fingerprint(action: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        thaw_json(action),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
