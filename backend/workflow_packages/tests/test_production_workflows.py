from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

from backend.project_workspaces.tests.test_b7_multi_workflow import (
    _finalize_progress,
    _literature_outputs,
)
from backend.workflow_packages.compiler import build_literature_search_package
from backend.workflow_packages.production_workflows import (
    IDEA_DISCOVERY_CAPSULE_VERSION,
    IDEA_DISCOVERY_WORKFLOW_ID,
    LITERATURE_SEARCH_CAPSULE_VERSION,
    LITERATURE_SEARCH_WORKFLOW_VERSION,
    build_idea_discovery_package,
    build_literature_search_v0_6_package,
)
from backend.workflow_packages.serialization import sha256_bytes

PROJECT_ID = "project-" + "1" * 32
INSTANCE_ID = "wfi-" + "2" * 32


def _build_literature(tmp_path: Path):
    return build_literature_search_v0_6_package(
        project_id=PROJECT_ID,
        project_name="Fictional literature Project",
        research_topic="Fictional bounded evidence",
        output_root=tmp_path / "literature",
        package_id=f"literature-search-{PROJECT_ID}-{INSTANCE_ID}-v0.1",
    )


def _build_idea(tmp_path: Path):
    return build_idea_discovery_package(
        project_id=PROJECT_ID,
        project_name="Fictional Idea Project",
        research_topic="Fictional bounded evidence",
        output_root=tmp_path / "idea",
        package_id=f"idea-discovery-{PROJECT_ID}-{INSTANCE_ID}-v0.1",
    )


def test_reviewed_versions_do_not_change_legacy_package_bytes(tmp_path: Path) -> None:
    before = build_literature_search_package(
        project_id=PROJECT_ID,
        project_name="Fictional legacy Project",
        research_topic="Fictional legacy topic",
        output_root=tmp_path / "legacy-before",
        allow_absolute_output_root=True,
    )
    literature = _build_literature(tmp_path)
    idea = _build_idea(tmp_path)
    after = build_literature_search_package(
        project_id=PROJECT_ID,
        project_name="Fictional legacy Project",
        research_topic="Fictional legacy topic",
        output_root=tmp_path / "legacy-after",
        allow_absolute_output_root=True,
    )

    assert before.archive_path.read_bytes() == after.archive_path.read_bytes()
    assert before.package_checksum == after.package_checksum
    assert literature.validation.valid and literature.archive_validation.valid
    assert idea.validation.valid and idea.archive_validation.valid
    literature_manifest = json.loads(
        (literature.package_root / "package-manifest.json").read_text()
    )
    idea_manifest = json.loads((idea.package_root / "package-manifest.json").read_text())
    assert literature_manifest["workflow_version"] == LITERATURE_SEARCH_WORKFLOW_VERSION
    assert literature_manifest["package_template_version"] == LITERATURE_SEARCH_CAPSULE_VERSION
    assert idea_manifest["workflow_id"] == IDEA_DISCOVERY_WORKFLOW_ID
    assert idea_manifest["package_template_version"] == IDEA_DISCOVERY_CAPSULE_VERSION
    assert idea_manifest["skill_pins"][0]["name"] == "reagent.evidence-grounded-ideation"


def test_finish_publishes_exact_ordered_content_addressed_artifact(tmp_path: Path) -> None:
    package = _build_literature(tmp_path)
    root = package.package_root
    _literature_outputs(root)
    assert not (root / "outputs/artifacts").exists()

    report_path = _finalize_progress(root, state="COMPLETED")
    report = json.loads(report_path.read_text())
    output = next(
        item for item in report["output_artifacts"]
        if item["artifact_kind"] == "selected-paper-library/v1"
    )
    artifact_path = root / output["relative_path"]
    artifact = json.loads(artifact_path.read_text())
    candidates = json.loads((root / "outputs/candidate_papers.json").read_text())
    selected = json.loads((root / "outputs/selected_papers.json").read_text())

    assert artifact["schema"] == "selected-paper-library/v1"
    assert [item["candidate_id"] for item in artifact["papers"]] == [
        item["candidate_id"] for item in selected["selected"]
    ]
    for item in artifact["papers"]:
        candidate_id = item["candidate_id"]
        assert item["paper"] == next(
            value for value in candidates["candidates"]
            if value["candidate_id"] == candidate_id
        )
        assert item["selection"] == next(
            value for value in selected["selected"]
            if value["candidate_id"] == candidate_id
        )
    assert artifact_path.name == f"sha256-{sha256_bytes(artifact_path.read_bytes())[7:]}.json"
    assert output["checksum"] == sha256_bytes(artifact_path.read_bytes())
    assert output["size"] == artifact_path.stat().st_size

    runner = runpy.run_path(str(root / "reagent_local.py"))
    payload = runner["_upload_envelope"](
        root=root,
        manifest=json.loads((root / "package-manifest.json").read_text()),
        report_path=report_path,
    )
    declaration = payload["artifact_declarations"][0]
    assert declaration["relative_path"] == output["relative_path"]
    assert declaration["content_checksum"] == output["checksum"]


def test_production_artifact_join_and_immutable_history_fail_closed(tmp_path: Path) -> None:
    package = _build_literature(tmp_path)
    root = package.package_root
    _literature_outputs(root)
    progress = runpy.run_path(str(root / "progress_report.py"))
    first = progress["_build_selected_paper_library"](root)
    first_path = root / first["relative_path"]
    first_bytes = first_path.read_bytes()
    assert progress["_build_selected_paper_library"](root) == first
    first_path.write_bytes(first_bytes + b"\n")
    with pytest.raises(Exception, match="target conflicts"):
        progress["_build_selected_paper_library"](root)
    first_path.write_bytes(first_bytes)

    candidates_path = root / "outputs/candidate_papers.json"
    candidates = json.loads(candidates_path.read_text())
    candidates["candidates"][0]["title"] = "A different validated fictional title"
    candidates_path.write_text(json.dumps(candidates), encoding="utf-8")
    second = progress["_build_selected_paper_library"](root)
    assert second["relative_path"] != first["relative_path"]
    assert first_path.read_bytes() == first_bytes
    validator = runpy.run_path(str(root / "validate_package.py"))
    assert validator["validate"](root, pristine=False)["valid"] is True

    selected_path = root / "outputs/selected_papers.json"
    selected = json.loads(selected_path.read_text())
    selected["selected"].append(dict(selected["selected"][0]))
    selected_path.write_text(json.dumps(selected), encoding="utf-8")
    with pytest.raises(Exception, match="duplicated|invalid|join"):
        progress["_build_selected_paper_library"](root)


def test_production_artifact_publication_rejects_symlink_and_hardlink_sources(
    tmp_path: Path,
) -> None:
    package = _build_literature(tmp_path)
    root = package.package_root
    _literature_outputs(root)
    progress = runpy.run_path(str(root / "progress_report.py"))
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "outputs/artifacts").symlink_to(outside, target_is_directory=True)
    with pytest.raises(Exception, match="parent is unsafe"):
        progress["_build_selected_paper_library"](root)
    assert list(outside.iterdir()) == []

    (root / "outputs/artifacts").unlink()
    source = root / "outputs/candidate_papers.json"
    linked = tmp_path / "candidate-hardlink.json"
    linked.hardlink_to(source)
    with pytest.raises(Exception, match="regular unlinked file"):
        progress["_build_selected_paper_library"](root)


def test_idea_preflight_requires_materialized_input_and_valid_outputs(tmp_path: Path) -> None:
    package = _build_idea(tmp_path)
    root = package.package_root
    runtime = runpy.run_path(str(root / "reagent_local.py"))
    with pytest.raises(Exception, match="materialized selected paper library"):
        runtime["preflight"](root)

    literature = _build_literature(tmp_path)
    _literature_outputs(literature.package_root)
    progress = runpy.run_path(str(literature.package_root / "progress_report.py"))
    produced = progress["_build_selected_paper_library"](literature.package_root)
    input_path = root / "inputs/selected-paper-library.json"
    input_path.write_bytes((literature.package_root / produced["relative_path"]).read_bytes())
    assert runtime["preflight"](root)["ready"] is True

    artifact = json.loads(input_path.read_text())
    (root / "outputs/candidate_ideas.json").write_text(json.dumps({
        "schema": "candidate-ideas/v0.1",
        "source_artifact": {
            "artifact_id": "artifact-" + "a" * 32,
            "artifact_type": "selected-paper-library/v1",
            "sha256": sha256_bytes(input_path.read_bytes()),
        },
        "ideas": [{
            "idea_id": "idea-001",
            "title": "Fictional direction",
            "research_question": "What should be tested?",
            "motivation": "Bounded evidence motivates the question.",
            "literature_basis": [artifact["papers"][0]["candidate_id"]],
            "observed_gap": "A potential gap in the supplied set.",
            "proposed_direction": "Test the potential gap.",
            "assumptions": [],
            "risks": ["Global novelty is not established."],
            "validation_needed": ["Broader search."],
            "status": "candidate",
        }],
    }), encoding="utf-8")
    (root / "outputs/idea_discovery_report.md").write_text(
        "# Report\n## Literature landscape\nBounded.\n## Observed patterns\nPattern.\n"
        "## Gaps\nPotential gap.\n## Candidate research directions\nCandidate.\n"
        "## User choices\nPending.\n## Uncertainties\nGlobal novelty is not proven.\n"
        "## Next validation needs\nBroader validation.\n",
        encoding="utf-8",
    )
    validator = runpy.run_path(str(root / "validate_package.py"))
    assert validator["validate"](root, pristine=False)["valid"] is True

    first_report = _finalize_progress(root, state="CANDIDATE_IDEAS", status="IN_PROGRESS")
    first = json.loads(first_report.read_text())
    second_report = _finalize_progress(root, state="USER_REVIEW", status="IN_PROGRESS")
    second = json.loads(second_report.read_text())
    assert second["execution_round"] == 2
    assert second["previous_report_id"] == first["report_id"]
    assert second["previous_report_checksum"] == first["report_checksum"]
    assert len(list((root / "memory/progress/reports").glob("prv2-*.json"))) == 2

    ideas = json.loads((root / "outputs/candidate_ideas.json").read_text())
    ideas["ideas"][0]["literature_basis"] = ["candidate-ffffffffffffffff"]
    (root / "outputs/candidate_ideas.json").write_text(json.dumps(ideas), encoding="utf-8")
    with pytest.raises(Exception, match="literature basis"):
        validator["validate"](root, pristine=False)
