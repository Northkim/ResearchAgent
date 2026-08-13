from __future__ import annotations

import hashlib
import json
import os
import runpy
import shutil
import subprocess
from pathlib import Path

import pytest

from backend.workflow_packages.production_workflows import (
    EXPERIMENT_INTERACTIVE_CAPSULE_VERSION,
    EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
    _experiment_v0_3_files,
    build_experiment_scaffold_v0_4_package,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes


PROJECT_ID = "project-" + "7" * 32
INSTANCE_ID = "wfi-" + "8" * 32


def _package(tmp_path: Path):
    return build_experiment_scaffold_v0_4_package(
        project_id=PROJECT_ID,
        project_name="Experiment bootstrap fixture",
        research_topic="Synthetic bounded research",
        output_root=tmp_path / "experiment",
        package_id="experiment-project-bootstrap-wfi-bootstrap-v0.4",
    )


def _fake(tmp_path: Path) -> Path:
    source = Path(__file__).with_name("fake_experiment_codex_cli.py")
    target = tmp_path / "codex-experiment-fixture"
    shutil.copyfile(source, target)
    target.chmod(0o700)
    return target


def _materialize(root: Path) -> None:
    idea = {
        "schema": "selected-research-idea/v1",
        "core_capability_maturity": "REVIEWED_CORE",
        "source_candidate_ideas": {
            "schema": "candidate-ideas/v0.1",
            "relative_path": "outputs/candidate_ideas.json",
            "sha256": "sha256:" + "a" * 64,
        },
        "source_literature_artifact": {
            "artifact_id": "artifact-" + "1" * 32,
            "artifact_type": "selected-paper-library/v1",
            "sha256": "sha256:" + "b" * 64,
        },
        "selected_idea": {
            "idea_id": "idea-003",
            "title": "Stress-testing multi-agent control",
            "research_question": "How can multi-agent control be stress-tested?",
            "hypothesis": "Bounded perturbations expose coordination failures.",
            "scope": "Synthetic planning only",
            "baselines": ["Static controller"],
            "metrics": ["Robustness"],
            "literature_verification_caveats": ["No full text was reviewed"],
        },
    }
    content = (canonical_json(idea) + "\n").encode()
    target = root / "inputs/selected-research-idea.json"
    target.write_bytes(content)
    (root / "memory/input-provenance.json").write_text(
        canonical_json({
            "schema_version": "reagent.scaffold-input-provenance/v0.1",
            "workflow_instance_id": INSTANCE_ID,
            "artifacts": {
                "research_idea": {
                    "artifact_id": "artifact-" + "2" * 32,
                    "artifact_type": "selected-research-idea/v1",
                    "sha256": sha256_bytes(content),
                    "relative_path": "inputs/selected-research-idea.json",
                }
            },
        }) + "\n",
        encoding="utf-8",
    )
    resources = json.loads((root / "memory/resource-provenance.json").read_text())
    resources["workflow_instance_id"] = INSTANCE_ID
    (root / "memory/resource-provenance.json").write_text(
        canonical_json(resources) + "\n", encoding="utf-8"
    )


def test_experiment_0_3_runner_bytes_remain_immutable() -> None:
    files = _experiment_v0_3_files(
        project_id=PROJECT_ID,
        project_name="Immutable Experiment",
        package_id="experiment-v0.3-immutable",
        package_checksum="sha256:" + "0" * 64,
    )
    content = files["reagent_local.py"].content
    assert len(content) == 20_876
    assert hashlib.sha256(content).hexdigest() == (
        "280a3cfaa2e8c4a1599a10e9e2052e270d992d8e1943d28e6b33270c707d8332"
    )


def test_experiment_0_4_changes_only_harness_and_resource_projection_assets(
    tmp_path: Path,
) -> None:
    package = _package(tmp_path)
    manifest = json.loads((package.package_root / "package-manifest.json").read_text())
    assert manifest["workflow_version"] == EXPERIMENT_RESOURCE_WORKFLOW_VERSION
    assert manifest["package_template_version"] == EXPERIMENT_INTERACTIVE_CAPSULE_VERSION
    assert manifest["prompt_pins"][0]["version"] == "0.3.0"
    assert [item["semantic_version"] for item in manifest["skill_pins"]] == [
        "0.1.0", "0.1.0"
    ]
    workflow = json.loads((package.package_root / "workflow/workflow.json").read_text())
    assert workflow["stages"] == [
        "INPUT_REVIEW", "EXPERIMENT_PLAN", "PLACEHOLDER_EXECUTION",
        "USER_REVIEW", "COMPLETED",
    ]
    assert workflow["supported_mode"] == "IDEA_EXPERIMENT"
    assert workflow["paper_reproduction"] == "NOT_YET_ENABLED"
    assert workflow["execution_status"] == "PLACEHOLDER_NOT_EXECUTED"
    assert workflow["actual_results"] is None


def test_current_experiment_harness_requires_and_delivers_bounded_initial_prompt(
    tmp_path: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = _package(tmp_path)
    root = package.package_root
    _materialize(root)
    namespace = runpy.run_path(str(root / "reagent_local.py"))
    assert namespace["preflight"](root)["ready"] is True
    sentinel = "must-not-reach-experiment"
    for key in (
        "REAGENT_OPENALEX_API_KEY", "OPENALEX_API_KEY", "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY", "REAGENT_PROXY_TOKEN",
        "REAGENT_LOCAL_SESSION_TOKEN", "REAGENT_DATABASE_URL",
    ):
        monkeypatch.setenv(key, sentinel)
    namespace["_run_harness"](root, str(_fake(tmp_path)))
    visible = capfd.readouterr().out
    assert "REAGENT REPRODUCTION & EXPERIMENT — INPUT_REVIEW" in visible
    assert "Current capability: SCAFFOLD_CORE" in visible
    assert "Paper reproduction: NOT_YET_ENABLED" in visible
    instruction = namespace["_initial_instruction"]()
    for term in (
        "Reproduction & Experiment", "INPUT_REVIEW", "SCAFFOLD_CORE",
        "IDEA_EXPERIMENT", "PAPER_REPRODUCTION", "PLACEHOLDER_NOT_EXECUTED",
        "actual_results null", "workflow/prompts/reproduction-experiment.md",
        "inputs/selected-research-idea.json", "memory/resource-provenance.json",
    ):
        assert term in instruction
    assert sentinel not in instruction


def test_compliant_experiment_fake_rejects_bare_harness_launch(tmp_path: Path) -> None:
    result = subprocess.run(
        [str(_fake(tmp_path))],
        env={key: os.environ[key] for key in ("PATH", "TMPDIR", "LANG") if key in os.environ},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 10
    assert "requires a ReAgent initial prompt" in result.stderr


def test_experiment_finalizer_safety_remains_fail_closed(tmp_path: Path) -> None:
    package = _package(tmp_path)
    root = package.package_root
    _materialize(root)
    namespace = runpy.run_path(str(root / "reagent_local.py"))
    config = json.loads((root / "workflow/scaffold.json").read_text())
    provenance = json.loads((root / "memory/input-provenance.json").read_text())
    artifact, human = namespace["_scaffold_payload"](
        config, provenance["artifacts"], root
    )
    assert b"SCAFFOLD EXPERIMENT PLACEHOLDER" in human
    assert artifact["execution_status"] == "PLACEHOLDER_NOT_EXECUTED"
    assert artifact["actual_results"] is None
    forged = {
        **artifact,
        "execution_status": "COMPLETED",
        "actual_results": {"summary": "fabricated", "metrics": [], "observations": []},
    }
    validator = runpy.run_path(str(root / "validate_package.py"))
    with pytest.raises(Exception, match="cannot claim execution"):
        validator["validate_scaffold_artifact"](forged)
