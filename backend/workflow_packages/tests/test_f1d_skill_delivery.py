from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

from backend.project_workspaces.skills import (
    PRODUCTION_SKILLS,
    validate_skill_content_files,
)
from backend.workflow_packages.production_workflows import (
    build_experiment_scaffold_v0_2_package,
    build_review_scaffold_v0_2_package,
    build_writing_scaffold_package,
    build_writing_scaffold_v0_2_package,
)
from backend.workflow_packages import cli


PROJECT_ID = "project-" + "1" * 32


def _build(builder, root: Path, package_id: str):
    return builder(
        project_id=PROJECT_ID,
        project_name="F1D synthetic",
        research_topic="Synthetic bounded topic",
        output_root=root,
        package_id=package_id,
    )


@pytest.mark.parametrize("builder", (
    build_writing_scaffold_v0_2_package,
    build_review_scaffold_v0_2_package,
    build_experiment_scaffold_v0_2_package,
))
def test_exact_reviewed_skills_are_bundled_and_deterministic(tmp_path, builder) -> None:
    first = _build(builder, tmp_path / "first", "f1d-package")
    second = _build(builder, tmp_path / "second", "f1d-package")
    assert first.package_checksum == second.package_checksum
    assert first.zip_checksum == second.zip_checksum
    manifest = json.loads((first.package_root / "package-manifest.json").read_text())
    assert manifest["workflow_version"] == "0.2.0"
    assert [(pin["name"], pin["semantic_version"], pin["checksum"]) for pin in manifest["skill_pins"]] == [
        (asset.skill_id, asset.version, asset.content_checksum)
        for asset in PRODUCTION_SKILLS
    ]
    for asset in PRODUCTION_SKILLS:
        skill_root = first.package_root / "workflow/skills" / asset.skill_id
        assert (skill_root / "SKILL.md").read_bytes() == asset.content_files()["SKILL.md"]
        assert (skill_root / "skill.json").read_bytes() == asset.content_files()["skill.json"]


def test_old_scaffold_capsule_stays_skill_platform_free(tmp_path) -> None:
    built = _build(build_writing_scaffold_package, tmp_path / "old", "f1d-old")
    manifest = json.loads((built.package_root / "package-manifest.json").read_text())
    assert manifest["workflow_version"] == "0.1.0"
    assert [pin["name"] for pin in manifest["skill_pins"]] == ["reagent.scaffold-safety"]
    assert not any(
        (built.package_root / "workflow/skills" / asset.skill_id).exists()
        for asset in PRODUCTION_SKILLS
    )


def test_missing_or_tampered_skill_fails_capsule_validation(tmp_path) -> None:
    missing = _build(
        build_writing_scaffold_v0_2_package, tmp_path / "missing", "f1d-missing"
    ).package_root
    (missing / "workflow/skills" / PRODUCTION_SKILLS[0].skill_id / "SKILL.md").unlink()
    validator = runpy.run_path(str(missing / "validate_package.py"))["validate"]
    with pytest.raises(Exception, match="missing|required package files"):
        validator(missing, pristine=False)

    tampered = _build(
        build_writing_scaffold_v0_2_package, tmp_path / "tampered", "f1d-tampered"
    ).package_root
    skill = tampered / "workflow/skills" / PRODUCTION_SKILLS[1].skill_id / "SKILL.md"
    skill.write_text(skill.read_text() + "\nunsafe drift\n")
    validator = runpy.run_path(str(tampered / "validate_package.py"))["validate"]
    with pytest.raises(Exception, match="integrity|checksum"):
        validator(tampered, pristine=False)


@pytest.mark.parametrize("path", ("../SKILL.md", "/SKILL.md", "x\\SKILL.md", "run.py"))
def test_skill_content_contract_rejects_unsafe_or_executable_paths(path) -> None:
    with pytest.raises(ValueError, match="unsafe|unsupported"):
        validate_skill_content_files({path: b"content"})


def test_operator_skill_shell_is_read_only_and_verifies_assets(capsys) -> None:
    assert cli.main(["skill-list"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["mutation_supported"] is False
    assert len(listed["skills"]) == 2
    assert cli.main(["skill-verify"]) == 0
    verified = json.loads(capsys.readouterr().out)
    assert verified["validation_result"] == "PASS"
    assert all(item["trust"] == "BUILT_IN_REVIEWED" for item in verified["skills"])
