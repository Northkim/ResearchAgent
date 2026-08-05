from __future__ import annotations

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from backend.workflow_packages import build_literature_search_package, validate_package
from backend.workflow_packages.compiler import BuildResult
from backend.workflow_packages.validator import PackageValidationError, validate_archive


def test_required_package_files_and_pins(built_package: BuildResult, manifest: dict[str, object]) -> None:
    root = built_package.package_root
    for relative in (
        "AGENT.md", "AGENTS.md", "CLAUDE.md", "README.md", "package-manifest.json",
        "validate_package.py", "progress_report.py", "workflow/AGENT.md", "workflow/workflow.json",
        "workflow/skills/literature-search/SKILL.md", "workflow/prompts/search-planning.md",
        "inputs/research_request.json", "inputs/fictional_source_catalog.json",
        "outputs/README.md", "memory/context.md", "memory/progress/report-draft.json",
        "memory/progress/reports/README.md",
        "cloud/proxy.example.json",
    ):
        assert (root / relative).is_file(), relative
    assert manifest["experimental_status_declaration"] == "EXPERIMENTAL_V0_1"
    assert manifest["harness_acceptance_status"] == "CODEX_LOCAL_FOLDER_BOUNDARY_PROVEN_CLAUDE_UNTESTED"
    assert manifest["progress_report_schema_version"] == "progress-report/v0.2"
    assert manifest["progress_upload_status"] == "UPLOAD_ACCEPTANCE_PENDING"
    assert manifest["package_template_version"] == "0.3.0"
    assert manifest["proxy_capability_declaration"] == (
        "DISABLED_BY_DEFAULT_R3B_FAKE_PAPER_SEARCH_ONLY; NO CREDENTIAL; NO REAL PROVIDER"
    )
    assert manifest["skill_pins"][0]["semantic_version"] == "0.1.0"  # type: ignore[index]
    assert manifest["prompt_pins"][0]["version"] == "0.1.0"  # type: ignore[index]


def test_deterministic_folder_and_zip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    first = build_literature_search_package(project_id="repeatable-project", output_root=Path("first"))
    second = build_literature_search_package(project_id="repeatable-project", output_root=Path("second"))
    assert first.package_checksum == second.package_checksum
    assert first.manifest_checksum == second.manifest_checksum
    assert first.zip_checksum == second.zip_checksum
    first_files = {path.relative_to(first.package_root).as_posix(): path.read_bytes() for path in first.package_root.rglob("*") if path.is_file()}
    second_files = {path.relative_to(second.package_root).as_posix(): path.read_bytes() for path in second.package_root.rglob("*") if path.is_file()}
    assert first_files == second_files


def test_owner_declared_topic_is_bound_into_package_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    first = build_literature_search_package(
        project_id="topic-project",
        research_topic="A fictional public topic about portable research state",
        output_root=Path("first"),
    )
    second = build_literature_search_package(
        project_id="topic-project",
        research_topic="A different fictional public topic",
        output_root=Path("second"),
    )
    first_request = json.loads(
        (first.package_root / "inputs/research_request.json").read_text()
    )
    assert first_request["topic"] == (
        "A fictional public topic about portable research state"
    )
    assert first.package_checksum != second.package_checksum


def test_idempotent_same_target_rebuild(built_package: BuildResult) -> None:
    rebuilt = build_literature_search_package(project_id="experimental-literature-search", output_root=Path("build"))
    assert rebuilt.package_checksum == built_package.package_checksum
    assert rebuilt.zip_checksum == built_package.zip_checksum


def test_archive_extract_and_copy_validate(built_package: BuildResult, tmp_path: Path) -> None:
    extracted = tmp_path / "extracted"
    copied = tmp_path / "copied"
    with zipfile.ZipFile(built_package.archive_path) as bundle:
        bundle.extractall(extracted)
    assert validate_package(extracted, pristine=True).valid
    shutil.copytree(extracted, copied)
    assert validate_package(copied, pristine=True).package_checksum == built_package.package_checksum
    command = [sys.executable, "-I", "validate_package.py", "--root", ".", "--pristine"]
    completed = subprocess.run(command, cwd=copied, check=False, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["valid"] is True


def test_shims_point_only_to_canonical_agent(built_package: BuildResult) -> None:
    for name in ("AGENTS.md", "CLAUDE.md"):
        content = (built_package.package_root / name).read_text()
        assert "canonical `AGENT.md`" in content
        assert "Required sequence" not in content


def test_instruction_boundaries(built_package: BuildResult) -> None:
    content = (built_package.package_root / "AGENT.md").read_text().lower()
    for phrase in ("inputs/` as read-only", "Progress Report", "provider credentials", "preserve prior", "checksum", "untrusted data"):
        assert phrase.lower() in content
    workflow = json.loads((built_package.package_root / "workflow/workflow.json").read_text())
    assert workflow["hosted_agent_runtime_required"] is False
    assert workflow["network_mode"] == "OFFLINE_SYNTHETIC_ONLY"
    proxy = json.loads((built_package.package_root / "cloud/proxy.example.json").read_text())
    assert proxy["enabled"] is False
    assert proxy["allowed_capabilities"] == ["paper.search/v0.1"]
    assert proxy["credential_present"] is False
    assert not {"token", "token_value", "api_key", "authorization"} & set(proxy)


def test_inputs_immutable_outputs_mutable_policy(manifest: dict[str, object]) -> None:
    entries = manifest["files"]  # type: ignore[assignment]
    inputs = [entry for entry in entries if entry["relative_path"].startswith("inputs/")]  # type: ignore[index]
    assert inputs and all(not entry["mutable_by_harness"] and entry["state_classification"] == "INPUT" for entry in inputs)
    assert all(item["required_output_path"].startswith("outputs/") for item in manifest["output_contracts"])  # type: ignore[index]


def test_no_undeclared_file(built_package: BuildResult) -> None:
    unexpected = built_package.package_root / "unexpected.txt"
    unexpected.write_text("unexpected")
    with pytest.raises(PackageValidationError, match="undeclared"):
        validate_package(built_package.package_root)


def test_symlink_rejected(built_package: BuildResult) -> None:
    link = built_package.package_root / "link"
    try:
        link.symlink_to("AGENT.md")
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(PackageValidationError, match="symbolic"):
        validate_package(built_package.package_root)


def test_archive_traversal_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../escape", "bad")
    with pytest.raises((PackageValidationError, ValueError)):
        validate_archive(archive)
