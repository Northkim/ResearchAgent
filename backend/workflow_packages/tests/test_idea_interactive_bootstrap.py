from __future__ import annotations

import hashlib
import json
import runpy
import shutil
from pathlib import Path

import pytest

from backend.workflow_packages.production_workflows import (
    IDEA_DISCOVERY_V0_2_WORKFLOW_VERSION,
    IDEA_DISCOVERY_V0_3_CAPSULE_VERSION,
    IDEA_DISCOVERY_V0_3_WORKFLOW_VERSION,
    IDEA_DISCOVERY_V0_4_CAPSULE_VERSION,
    _idea_v0_2_runner_source,
    build_idea_discovery_v0_3_package,
    build_idea_discovery_v0_4_package,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes

from backend.workflow_packages.tests.test_f1a_selected_idea import (
    _materialize_literature,
)


def _package(tmp_path: Path):
    return build_idea_discovery_v0_3_package(
        project_id="project-" + "7" * 32,
        project_name="Idea bootstrap fixture",
        research_topic="Bounded synthetic research",
        output_root=tmp_path / "idea",
        package_id="idea-discovery-project-bootstrap-wfi-bootstrap-v0.3",
    )


def _fake(tmp_path: Path) -> Path:
    source = Path(__file__).with_name("fake_idea_codex_cli.py")
    target = tmp_path / "codex-idea-fixture"
    shutil.copyfile(source, target)
    target.chmod(0o700)
    return target


def test_idea_0_2_runner_bytes_remain_immutable() -> None:
    content = _idea_v0_2_runner_source()
    assert len(content) == 12_358
    assert hashlib.sha256(content).hexdigest() == (
        "ef8ae73ee242fc9dc3bb4cf8b343f68a5dbe43cace84ab841a4c1b9c582e5cde"
    )


def test_idea_0_3_changes_only_harness_integration_assets(tmp_path: Path) -> None:
    package = _package(tmp_path)
    manifest = json.loads((package.package_root / "package-manifest.json").read_text())
    assert manifest["workflow_version"] == IDEA_DISCOVERY_V0_2_WORKFLOW_VERSION
    assert manifest["package_template_version"] == IDEA_DISCOVERY_V0_3_CAPSULE_VERSION
    assert manifest["prompt_pins"][0]["version"] == "0.2.0"
    assert manifest["skill_pins"][0]["semantic_version"] == "0.2.0"


def test_forward_idea_0_3_package_publishes_nonempty_input_precondition(
    tmp_path: Path,
) -> None:
    package = build_idea_discovery_v0_4_package(
        project_id="project-" + "7" * 32,
        project_name="Forward Idea precondition fixture",
        research_topic="Bounded synthetic research",
        output_root=tmp_path / "idea-forward",
        package_id="idea-discovery-project-forward-wfi-forward-v0.4",
    )
    manifest = json.loads((package.package_root / "package-manifest.json").read_text())
    workflow = json.loads((package.package_root / "workflow/workflow.json").read_text())
    assert manifest["workflow_version"] == IDEA_DISCOVERY_V0_3_WORKFLOW_VERSION
    assert manifest["package_template_version"] == IDEA_DISCOVERY_V0_4_CAPSULE_VERSION
    assert workflow["input_requirements"][0]["content_precondition"] == {
        "schema": (
            "reagent.artifact-precondition."
            "selected-paper-library-nonempty/v0.1"
        ),
        "qualification_schema": (
            "reagent.artifact-qualification.selected-paper-library/v0.1"
        ),
        "minimum_selected_count": 1,
    }
    assert package.validation.valid and package.archive_validation.valid


def test_current_idea_harness_requires_and_delivers_bounded_initial_prompt(
    tmp_path: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = _package(tmp_path)
    root = package.package_root
    _materialize_literature(tmp_path, root)
    input_path = root / "inputs/selected-paper-library.json"
    (root / "outputs/candidate_ideas.json").write_text(
        canonical_json({
            "schema": "candidate-ideas/v0.1",
            "source_artifact": {
                "artifact_id": "artifact-" + "8" * 32,
                "artifact_type": "selected-paper-library/v1",
                "sha256": sha256_bytes(input_path.read_bytes()),
            },
            "ideas": [],
        }) + "\n",
        encoding="utf-8",
    )
    namespace = runpy.run_path(str(root / "reagent_local.py"))
    namespace["_prepare_draft"](root, stage="INPUT_REVIEW")
    monkeypatch.setenv("REAGENT_OPENALEX_API_KEY", "must-not-reach-idea")
    namespace["_run_harness"](root, str(_fake(tmp_path)))
    visible = capfd.readouterr().out
    assert "ReAgent Idea Discovery — INPUT_REVIEW" in visible
    instruction = namespace["_initial_instruction"]()
    normalized_instruction = " ".join(instruction.split())
    for term in (
        "Idea Discovery", "INPUT_REVIEW", "workflow/prompts/idea-discovery.md",
        "inputs/selected-paper-library.json", "priorities", "no full text",
    ):
        assert term in normalized_instruction
    assert "OpenAlex" not in instruction


def test_compliant_fake_rejects_bare_harness_launch(tmp_path: Path) -> None:
    import os
    import subprocess

    environment = dict(os.environ)
    for key in (
        "REAGENT_OPENALEX_API_KEY", "OPENALEX_API_KEY", "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY", "REAGENT_PROXY_TOKEN",
        "REAGENT_LOCAL_SESSION_TOKEN", "REAGENT_DATABASE_URL",
    ):
        environment.pop(key, None)
    result = subprocess.run(
        [str(_fake(tmp_path))], env=environment,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 10
    assert "requires a ReAgent initial prompt" in result.stderr
