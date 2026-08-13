from __future__ import annotations

import hashlib
import json
import os
import runpy
import shutil
import subprocess
from pathlib import Path

import pytest

from backend.project_workspaces.production_workflows import (
    REVIEW_WORKFLOW_ID,
    SCAFFOLD_V0_2_CAPSULE_CHECKSUMS,
    SCAFFOLD_V0_3_CAPSULE_CHECKSUMS,
    WRITING_WORKFLOW_ID,
)
from backend.workflow_packages.production_workflows import (
    _scaffold_v0_3_files,
    _scaffold_v0_2_files,
    build_review_scaffold_v0_3_package,
    build_writing_scaffold_v0_3_package,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes

PROJECT_ID = "project-" + "7" * 32
INSTANCE_ID = "wfi-" + "8" * 32


def _build(tmp_path: Path, workflow_id: str):
    builder = (
        build_writing_scaffold_v0_3_package
        if workflow_id == WRITING_WORKFLOW_ID
        else build_review_scaffold_v0_3_package
    )
    return builder(
        project_id=PROJECT_ID,
        project_name="Writing Review bootstrap fixture",
        research_topic="Synthetic bounded research",
        output_root=tmp_path / workflow_id,
        package_id=f"{workflow_id}-bootstrap-v0.3",
    )


def _fake(tmp_path: Path) -> Path:
    source = Path(__file__).with_name("fake_writing_review_codex_cli.py")
    target = tmp_path / "codex-writing-review-fixture"
    shutil.copyfile(source, target)
    target.chmod(0o700)
    return target


def _materialize(root: Path, workflow_id: str, *, revision: bool = False) -> None:
    if workflow_id == WRITING_WORKFLOW_ID:
        values = {
            "research_idea": ("selected-research-idea/v1", "selected-research-idea.json", {
                "schema": "selected-research-idea/v1",
                "selected_idea": {"title": "Synthetic direction", "research_question": "What is bounded?"},
            }),
            "literature_library": ("selected-paper-library/v1", "selected-paper-library.json", {
                "schema": "selected-paper-library/v1", "papers": [],
            }),
        }
        if revision:
            values.update({
                "prior_manuscript": ("manuscript-draft/v1", "prior-manuscript.json", {
                    "schema": "manuscript-draft/v1", "content_markdown": "SCAFFOLD PLACEHOLDER",
                }),
                "review_feedback": ("review-report/v1", "review-report.json", {
                    "schema": "review-report/v1", "recommendation": "INSUFFICIENT_EVIDENCE",
                }),
            })
    else:
        values = {
            "manuscript": ("manuscript-draft/v1", "manuscript-draft.json", {
                "schema": "manuscript-draft/v1", "content_markdown": "SCAFFOLD PLACEHOLDER",
            }),
        }
    records = {}
    for index, (role, (artifact_type, filename, value)) in enumerate(values.items(), 1):
        content = (canonical_json(value) + "\n").encode()
        (root / "inputs" / filename).write_bytes(content)
        records[role] = {
            "artifact_id": "artifact-" + str(index) * 32,
            "artifact_type": artifact_type,
            "sha256": sha256_bytes(content),
            "relative_path": f"inputs/{filename}",
        }
    (root / "memory/input-provenance.json").write_text(
        canonical_json({
            "schema_version": "reagent.scaffold-input-provenance/v0.1",
            "workflow_instance_id": INSTANCE_ID,
            "artifacts": records,
        }) + "\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize("workflow_id", (WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID))
def test_scaffold_0_2_runner_bytes_and_capsule_checksums_remain_immutable(
    workflow_id: str,
) -> None:
    files = _scaffold_v0_2_files(
        workflow_id=workflow_id,
        project_id=PROJECT_ID,
        project_name="Immutable scaffold",
        package_id="immutable-v0.2",
        package_checksum="sha256:" + "0" * 64,
    )
    runner = files["reagent_local.py"].content
    assert len(runner) == 20_876
    assert hashlib.sha256(runner).hexdigest() == (
        "280a3cfaa2e8c4a1599a10e9e2052e270d992d8e1943d28e6b33270c707d8332"
    )
    assert SCAFFOLD_V0_2_CAPSULE_CHECKSUMS[workflow_id] in {
        "sha256:84896829db7ee1cb6b24a5e10bf6705beac93fa42857d0dc08d4916e0243ee0c",
        "sha256:9c3e4e8f065914393f5dc786b36d07bbbdc962f381ea70f125353429c48089f1",
    }


@pytest.mark.parametrize("workflow_id", (WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID))
def test_new_capsule_changes_only_harness_integration_assets(
    tmp_path: Path, workflow_id: str,
) -> None:
    package = _build(tmp_path, workflow_id)
    manifest = json.loads((package.package_root / "package-manifest.json").read_text())
    assert manifest["workflow_version"] == "0.2.0"
    assert manifest["package_template_version"] == "0.3.0"
    assert manifest["prompt_pins"][0]["version"] == "0.2.0"
    assert [item["semantic_version"] for item in manifest["skill_pins"]] == [
        "0.1.0", "0.1.0",
    ]
    assert SCAFFOLD_V0_3_CAPSULE_CHECKSUMS[workflow_id].startswith("sha256:")

    common = {
        "project_id": PROJECT_ID,
        "project_name": "Byte comparison",
        "package_id": "byte-comparison",
        "package_checksum": "sha256:" + "0" * 64,
    }
    old_files = _scaffold_v0_2_files(workflow_id=workflow_id, **common)
    new_files = _scaffold_v0_3_files(workflow_id=workflow_id, **common)
    assert set(old_files) == set(new_files)
    assert {
        path for path in old_files
        if old_files[path].content != new_files[path].content
    } == {"reagent_local.py"}


@pytest.mark.parametrize("workflow_id", (WRITING_WORKFLOW_ID, REVIEW_WORKFLOW_ID))
def test_current_harness_delivers_bounded_positional_prompt(
    tmp_path: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
    workflow_id: str,
) -> None:
    package = _build(tmp_path, workflow_id)
    root = package.package_root
    _materialize(root, workflow_id, revision=workflow_id == WRITING_WORKFLOW_ID)
    namespace = runpy.run_path(str(root / "reagent_local.py"))
    assert namespace["preflight"](root)["ready"] is True
    for key in (
        "REAGENT_OPENALEX_API_KEY", "OPENALEX_API_KEY", "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY", "REAGENT_PROXY_TOKEN",
        "REAGENT_LOCAL_SESSION_TOKEN", "REAGENT_DATABASE_URL",
    ):
        monkeypatch.setenv(key, "must-not-cross-harness")
    namespace["_run_harness"](root, str(_fake(tmp_path)))
    visible = capfd.readouterr().out
    expected = (
        "REAGENT WRITING — INPUT_REVIEW"
        if workflow_id == WRITING_WORKFLOW_ID
        else "REAGENT REVIEW — INPUT_REVIEW"
    )
    assert expected in visible
    assert "Current capability: SCAFFOLD_CORE" in visible
    if workflow_id == WRITING_WORKFLOW_ID:
        assert "Revision round: yes" in visible
    assert "must-not-cross-harness" not in visible


def test_prompt_enforcing_fake_rejects_bare_launch(tmp_path: Path) -> None:
    result = subprocess.run(
        [str(_fake(tmp_path))],
        env={key: os.environ[key] for key in ("PATH", "TMPDIR", "LANG") if key in os.environ},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 10
    assert "requires a ReAgent initial prompt" in result.stderr
