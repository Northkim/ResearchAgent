from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

from backend.project_workspaces.tests.test_b7_multi_workflow import (
    _finalize_progress,
    _literature_outputs,
)
from backend.workflow_packages.production_workflows import (
    IDEA_DISCOVERY_CAPSULE_VERSION,
    IDEA_DISCOVERY_V0_2_CAPSULE_VERSION,
    build_idea_discovery_package,
    build_idea_discovery_v0_2_package,
    build_literature_search_v0_6_package,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes

PROJECT_ID = "project-" + "1" * 32
INSTANCE_ID = "wfi-" + "2" * 32
LITERATURE_ARTIFACT_ID = "artifact-" + "a" * 32


def _build_idea(tmp_path: Path, *, version: str = "0.2.0"):
    builder = (
        build_idea_discovery_v0_2_package
        if version == "0.2.0" else build_idea_discovery_package
    )
    return builder(
        project_id=PROJECT_ID,
        project_name="F1A selected idea fixture",
        research_topic="Bounded synthetic research",
        output_root=tmp_path / f"idea-{version}",
        package_id=f"idea-discovery-{PROJECT_ID}-{INSTANCE_ID}-v{version}",
    )


def _materialize_literature(tmp_path: Path, idea_root: Path) -> dict:
    literature = build_literature_search_v0_6_package(
        project_id=PROJECT_ID,
        project_name="F1A literature fixture",
        research_topic="Bounded synthetic research",
        output_root=tmp_path / "literature",
        package_id=f"literature-{PROJECT_ID}-{INSTANCE_ID}",
    )
    _literature_outputs(literature.package_root)
    progress = runpy.run_path(str(literature.package_root / "progress_report.py"))
    produced = progress["_build_selected_paper_library"](literature.package_root)
    source = literature.package_root / produced["relative_path"]
    target = idea_root / "inputs/selected-paper-library.json"
    target.write_bytes(source.read_bytes())
    return json.loads(target.read_text())


def _idea_record(idea_id: str, candidate_id: str, status: str) -> dict:
    return {
        "idea_id": idea_id,
        "title": f"Direction {idea_id}",
        "research_question": "What bounded comparison should be tested?",
        "motivation": "The selected records expose an unresolved tension.",
        "literature_basis": [candidate_id],
        "observed_gap": "The bounded set leaves this comparison unresolved.",
        "proposed_direction": "Evaluate the comparison with explicit assumptions.",
        "assumptions": ["The selected evidence is relevant."],
        "risks": ["Global novelty is not established."],
        "validation_needed": ["Broader novelty and feasibility validation."],
        "status": status,
    }


def _write_outputs(root: Path, library: dict, statuses: tuple[str, ...]) -> list[dict]:
    candidate_ids = [item["candidate_id"] for item in library["papers"]]
    ideas = [
        _idea_record(f"idea-{index + 1:03d}", candidate_ids[index], status)
        for index, status in enumerate(statuses)
    ]
    input_path = root / "inputs/selected-paper-library.json"
    (root / "outputs/candidate_ideas.json").write_text(
        canonical_json({
            "schema": "candidate-ideas/v0.1",
            "source_artifact": {
                "artifact_id": LITERATURE_ARTIFACT_ID,
                "artifact_type": "selected-paper-library/v1",
                "sha256": sha256_bytes(input_path.read_bytes()),
            },
            "ideas": ideas,
        }) + "\n",
        encoding="utf-8",
    )
    (root / "outputs/idea_discovery_report.md").write_text(
        "# Idea Discovery report\n\n"
        "## Literature landscape\nBounded evidence.\n"
        "## Observed patterns\nA pattern.\n"
        "## Gaps\nA potential gap.\n"
        "## Candidate research directions\nCandidate directions.\n"
        "## User choices\nExplicit selection recorded when present.\n"
        "## Uncertainties\nGlobal novelty is not proven.\n"
        "## Next validation needs\nBroader validation.\n",
        encoding="utf-8",
    )
    return ideas


def test_idea_0_2_is_new_and_idea_0_1_stays_independently_valid(
    tmp_path: Path,
) -> None:
    old = _build_idea(tmp_path, version="0.1.0")
    new = _build_idea(tmp_path)
    old_manifest = json.loads((old.package_root / "package-manifest.json").read_text())
    new_manifest = json.loads((new.package_root / "package-manifest.json").read_text())
    assert old_manifest["workflow_version"] == IDEA_DISCOVERY_CAPSULE_VERSION == "0.1.0"
    assert new_manifest["workflow_version"] == IDEA_DISCOVERY_V0_2_CAPSULE_VERSION == "0.2.0"
    assert "workflow/artifact-outputs.json" not in {
        item["relative_path"] for item in old_manifest["files"]
    }
    assert "workflow/artifact-outputs.json" in {
        item["relative_path"] for item in new_manifest["files"]
    }
    assert old.validation.valid and old.archive_validation.valid
    assert new.validation.valid and new.archive_validation.valid


def test_completed_round_publishes_exact_content_addressed_selected_idea(
    tmp_path: Path,
) -> None:
    package = _build_idea(tmp_path)
    root = package.package_root
    library = _materialize_literature(tmp_path, root)
    ideas = _write_outputs(root, library, ("candidate", "selected", "rejected"))

    report_path = _finalize_progress(root, state="COMPLETED")
    report = json.loads(report_path.read_text())
    selected_output = next(
        item for item in report["output_artifacts"]
        if item["artifact_kind"] == "selected-research-idea/v1"
    )
    artifact_path = root / selected_output["relative_path"]
    artifact = json.loads(artifact_path.read_text())
    assert artifact["selected_idea"] == ideas[1]
    assert artifact["core_capability_maturity"] == "REVIEWED_CORE"
    assert artifact["source_literature_artifact"]["artifact_id"] == LITERATURE_ARTIFACT_ID
    assert artifact["source_candidate_ideas"]["sha256"] == sha256_bytes(
        (root / "outputs/candidate_ideas.json").read_bytes()
    )
    assert artifact_path.name == "sha256-" + sha256_bytes(artifact_path.read_bytes())[7:] + ".json"
    assert selected_output["checksum"] == sha256_bytes(artifact_path.read_bytes())

    helper = runpy.run_path(str(root / "progress_report.py"))
    assert helper["_build_selected_research_idea"](root) == selected_output
    assert runpy.run_path(str(root / "validate_package.py"))["validate"](
        root, pristine=False
    )["valid"] is True


@pytest.mark.parametrize(
    "statuses",
    [("candidate", "shortlisted"), ("selected", "selected")],
)
def test_completion_fails_closed_without_exactly_one_user_selection(
    tmp_path: Path, statuses: tuple[str, ...]
) -> None:
    package = _build_idea(tmp_path)
    root = package.package_root
    library = _materialize_literature(tmp_path, root)
    _write_outputs(root, library, statuses)
    with pytest.raises(Exception, match="exactly one selected"):
        _finalize_progress(root, state="COMPLETED")
    assert not (root / "outputs/artifacts/selected-research-idea").exists()


def test_candidate_stage_cannot_publish_selected_artifact(tmp_path: Path) -> None:
    package = _build_idea(tmp_path)
    root = package.package_root
    library = _materialize_literature(tmp_path, root)
    _write_outputs(root, library, ("candidate",))
    report = json.loads(
        _finalize_progress(
            root, state="CANDIDATE_IDEAS", status="IN_PROGRESS"
        ).read_text()
    )
    assert all(
        output["artifact_kind"] != "selected-research-idea/v1"
        for output in report["output_artifacts"]
    )
    assert not (root / "outputs/artifacts/selected-research-idea").exists()


def test_changed_explicit_selection_creates_new_artifact_and_preserves_old(
    tmp_path: Path,
) -> None:
    package = _build_idea(tmp_path)
    root = package.package_root
    library = _materialize_literature(tmp_path, root)
    _write_outputs(root, library, ("selected", "candidate"))
    helper = runpy.run_path(str(root / "progress_report.py"))
    first = helper["_build_selected_research_idea"](root)
    first_path = root / first["relative_path"]
    first_bytes = first_path.read_bytes()
    _write_outputs(root, library, ("rejected", "selected"))
    second = helper["_build_selected_research_idea"](root)
    assert second["relative_path"] != first["relative_path"]
    assert first_path.read_bytes() == first_bytes
    assert json.loads(first_bytes)["selected_idea"]["idea_id"] == "idea-001"
    assert json.loads((root / second["relative_path"]).read_text())["selected_idea"]["idea_id"] == "idea-002"


def test_selected_idea_publication_rejects_source_drift_links_and_conflict(
    tmp_path: Path,
) -> None:
    package = _build_idea(tmp_path)
    root = package.package_root
    library = _materialize_literature(tmp_path, root)
    _write_outputs(root, library, ("selected",))
    helper = runpy.run_path(str(root / "progress_report.py"))
    source = root / "outputs/candidate_ideas.json"
    linked = tmp_path / "candidate-hardlink.json"
    linked.hardlink_to(source)
    with pytest.raises(Exception, match="regular unlinked"):
        helper["_build_selected_research_idea"](root)
    linked.unlink()

    outside = tmp_path / "outside-selected-idea"
    outside.mkdir()
    (root / "outputs/artifacts").symlink_to(outside, target_is_directory=True)
    with pytest.raises(Exception, match="parent is unsafe"):
        helper["_build_selected_research_idea"](root)
    assert list(outside.iterdir()) == []
    (root / "outputs/artifacts").unlink()

    first = helper["_build_selected_research_idea"](root)
    artifact_path = root / first["relative_path"]
    original = artifact_path.read_bytes()
    artifact_path.write_bytes(original + b"\n")
    with pytest.raises(Exception, match="conflicts"):
        helper["_build_selected_research_idea"](root)


def test_progress_upload_declares_selected_artifact_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _build_idea(tmp_path)
    root = package.package_root
    library = _materialize_literature(tmp_path, root)
    _write_outputs(root, library, ("selected",))
    report_path = _finalize_progress(root, state="COMPLETED")
    runtime = runpy.run_path(str(root / "reagent_local.py"))
    captured: dict = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit):
            return b'{"accepted_for_projection":true}'

    def fake_urlopen(request, timeout):
        assert timeout == 30
        captured.update(json.loads(request.data))
        return Response()

    monkeypatch.setattr(runtime["urllib"].request, "urlopen", fake_urlopen)
    runtime["_upload"](
        root=root,
        report_path=report_path,
        workflow_instance_id=INSTANCE_ID,
        api_url="http://127.0.0.1:8000",
    )
    declarations = captured["artifact_declarations"]
    assert len(declarations) == 1
    assert declarations[0]["artifact_type"] == "selected-research-idea/v1"
    assert declarations[0]["content_checksum"] == next(
        output["checksum"] for output in json.loads(report_path.read_text())["output_artifacts"]
        if output["artifact_kind"] == "selected-research-idea/v1"
    )
