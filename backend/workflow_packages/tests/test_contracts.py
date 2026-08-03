from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from backend.workflow_packages.contracts import (
    LocalContext,
    PackageFileEntry,
    PackageOutputContract,
    PromptPin,
    SkillPin,
)
from backend.workflow_packages.security import reject_duplicate_paths, require_relative_path
from backend.workflow_packages.serialization import canonical_hash, canonical_json

HASH = "sha256:" + "1" * 64


def test_contract_is_immutable() -> None:
    pin = PromptPin("search-prompt", "0.1.0", HASH, "workflow/prompts/search.md", "plan")
    with pytest.raises(FrozenInstanceError):
        pin.version = "0.2.0"  # type: ignore[misc]


def test_nested_collections_are_immutable() -> None:
    source = ["read_local"]
    pin = SkillPin("reagent.search", "0.1.0", "BUNDLED", "original", HASH, "workflow/skills/search/SKILL.md", source)
    source.append("network")
    assert pin.required_capabilities == ("read_local",)


def test_canonical_hash_is_stable() -> None:
    left = {"b": [2, 1], "a": "value"}
    right = {"a": "value", "b": [2, 1]}
    assert canonical_json(left) == canonical_json(right)
    assert canonical_hash(left) == canonical_hash(right)


@pytest.mark.parametrize("path", ["/absolute", "../escape", "a/../b", "a\\b", "C:" + "\\temp\\file", ".env", "state.sqlite"])
def test_invalid_paths_are_rejected(path: str) -> None:
    with pytest.raises(ValueError):
        require_relative_path(path)


def test_duplicate_paths_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        reject_duplicate_paths(["a.md", "a.md"])


def test_invalid_skill_pin_is_rejected() -> None:
    with pytest.raises(ValueError):
        SkillPin("Invalid Skill", "latest", "", "", "bad", "/bad", ())


def test_invalid_prompt_pin_is_rejected() -> None:
    with pytest.raises(ValueError):
        PromptPin("Prompt", "v1", "bad", "../prompt", "")


def test_invalid_output_contract_is_rejected() -> None:
    with pytest.raises(ValueError, match="outputs"):
        PackageOutputContract("memory/report.md", "REPORT", "text/markdown", "v0.1", "Harness", "required")


def test_invalid_file_entry_hash_is_rejected() -> None:
    with pytest.raises(ValueError):
        PackageFileEntry("AGENT.md", "text/markdown", "entry", "bad", 1, False, "INSTRUCTION", "REQUIRED")


def test_context_checksum_detects_change() -> None:
    context = LocalContext(
        package_id="package-id",
        package_checksum=HASH,
        workflow_id="workflow-id",
        workflow_version="0.1.0",
        current_workflow_state="NOT_STARTED",
        completed_outputs=(),
        relevant_decisions=(),
        unresolved_issues=(),
        next_action="start",
        latest_progress_report=None,
        previous_session_history_pointer=None,
        updated_at="2000-01-01T00:00:00Z",
    ).with_computed_checksum()
    assert context.verify_checksum()
    changed = LocalContext(**{**context.to_dict(), "next_action": "changed"})
    assert not changed.verify_checksum()
