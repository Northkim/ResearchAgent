from __future__ import annotations

import ast
import builtins
import json
import shutil
import socket
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from backend.workflow_packages import LocalContext, OutputFileReference, ProgressReport
from backend.workflow_packages.compiler import BuildResult, build_literature_search_package
from backend.workflow_packages.security import reject_sensitive_content
from backend.workflow_packages.serialization import sha256_bytes
from backend.workflow_packages.state import append_progress_report, parse_context, write_context
from backend.workflow_packages.package_progress import finalize, snapshot
from backend.workflow_packages.validator import validate_package
from backend.progress_reports.normalization import ProgressReportNormalizer


def _updated_context(result: BuildResult) -> tuple[LocalContext, str]:
    initial = parse_context((result.package_root / "memory/context.md").read_text())
    updated = replace(
        initial,
        current_workflow_state="COMPLETED",
        completed_outputs=("outputs/search_plan.md",),
        next_action="Start a fresh session and verify continuation.",
        updated_at="2000-01-02T00:00:00Z",
        context_checksum="sha256:" + "0" * 64,
    ).with_computed_checksum()
    return updated, write_context(result.package_root, updated)


def _report(result: BuildResult, context_file_checksum: str, *, report_id: str = "round-001", previous: str | None = None) -> ProgressReport:
    output = result.package_root / "outputs/search_plan.md"
    output.write_text("# Synthetic offline search plan\n")
    report = ProgressReport(
        report_id=report_id,
        package_id=result.package_id,
        package_checksum=result.package_checksum,
        project_identity="experimental-literature-search",
        workflow_id="literature-search-local-experimental",
        workflow_version="0.1.0",
        skill_versions=("reagent.local-literature-search@0.1.0",),
        template_version="0.1.0",
        execution_round=1,
        harness_identity="codex-fresh-session",
        started_at="2000-01-02T00:00:00Z",
        completed_at="2000-01-02T00:10:00Z",
        status="COMPLETED",
        completed_work=("wrote search plan",),
        current_state="completion boundary reached",
        next_recommended_action="verify continuation",
        output_files=(OutputFileReference("outputs/search_plan.md", sha256_bytes(output.read_bytes())),),
        context_checksum=context_file_checksum,
        continuation_instructions=("Read context and latest report.",),
        previous_report_id=previous,
    )
    return report.with_computed_checksum()


def test_initial_and_updated_context_support_continuation(built_package: BuildResult) -> None:
    initial = parse_context((built_package.package_root / "memory/context.md").read_text())
    assert initial.current_workflow_state == "NOT_STARTED"
    updated, _ = _updated_context(built_package)
    reparsed = parse_context((built_package.package_root / "memory/context.md").read_text())
    assert reparsed == updated
    assert reparsed.completed_outputs == ("outputs/search_plan.md",)
    assert "fresh session" in reparsed.next_action


def test_progress_report_append_and_output_checksums(built_package: BuildResult) -> None:
    _, context_checksum = _updated_context(built_package)
    report = _report(built_package, context_checksum)
    path = append_progress_report(built_package.package_root, report)
    assert path.name == "round-001.json"
    assert json.loads(path.read_text())["report_checksum"] == report.report_checksum


def test_progress_report_overwrite_rejected(built_package: BuildResult) -> None:
    _, context_checksum = _updated_context(built_package)
    report = _report(built_package, context_checksum)
    append_progress_report(built_package.package_root, report)
    with pytest.raises(FileExistsError, match="append-only"):
        append_progress_report(built_package.package_root, report)


def test_progress_report_wrong_package_rejected(built_package: BuildResult) -> None:
    _, context_checksum = _updated_context(built_package)
    report = replace(_report(built_package, context_checksum), package_id="different-package", report_checksum="sha256:" + "0" * 64).with_computed_checksum()
    with pytest.raises(ValueError, match="identity"):
        append_progress_report(built_package.package_root, report)


def test_progress_report_previous_link_is_preserved(built_package: BuildResult) -> None:
    _, context_checksum = _updated_context(built_package)
    report = _report(built_package, context_checksum, report_id="round-002", previous="round-001")
    assert report.previous_report_id == "round-001"
    assert report.verify_checksum()


def test_fixture_is_wholly_fictional_and_offline(built_package: BuildResult) -> None:
    catalog_text = (built_package.package_root / "inputs/fictional_source_catalog.json").read_text().lower()
    catalog = json.loads(catalog_text)
    assert catalog["contains_real_titles"] is False
    assert catalog["contains_real_abstracts"] is False
    assert catalog["contains_provider_identifiers"] is False
    assert "doi" not in catalog_text
    assert "openalex" not in catalog_text
    request = json.loads((built_package.package_root / "inputs/research_request.json").read_text())
    assert request["real_external_search_performed"] is False


@pytest.mark.parametrize(
    "content",
    [b"sk-" + b"ant-examplecredential", b"sk-" + b"proj-examplecredential", b"/" + b"Users/person/project", b'"raw_provider_' + b'response":{}'],
)
def test_sensitive_content_rejected(content: bytes) -> None:
    with pytest.raises(ValueError):
        reject_sensitive_content(content, path="probe.txt")


def test_compiler_source_has_no_hosted_imports() -> None:
    package_dir = Path(__file__).resolve().parents[1]
    forbidden = {"backend.agent_runtime", "backend.application.execution", "backend.database", "backend.persistence"}
    for source in package_dir.glob("*.py"):
        tree = ast.parse(source.read_text())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        assert not any(any(name == item or name.startswith(item + ".") for item in forbidden) for name in imports), source.name


def test_generation_makes_no_network_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network attempted")))
    result = build_literature_search_package(project_id="network-canary", output_root=Path("build"))
    assert result.validation.valid


def test_generation_does_not_read_environment_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("CANARY_DO_NOT_READ=yes\n")
    original_open = builtins.open
    def guarded_open(file: object, *args: object, **kwargs: object):
        if Path(file).name == ".env":  # type: ignore[arg-type]
            raise AssertionError("environment file read")
        return original_open(file, *args, **kwargs)  # type: ignore[arg-type]
    monkeypatch.setattr(builtins, "open", guarded_open)
    result = build_literature_search_package(project_id="environment-canary", output_root=Path("build"))
    assert result.validation.valid


def test_generation_does_not_import_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    before = {name for name in sys.modules if name.startswith("backend.database") or name.startswith("backend.persistence")}
    build_literature_search_package(project_id="database-canary", output_root=Path("build"))
    after = {name for name in sys.modules if name.startswith("backend.database") or name.startswith("backend.persistence")}
    assert after == before


def test_local_state_survives_copy(built_package: BuildResult, tmp_path: Path) -> None:
    updated, _ = _updated_context(built_package)
    copied = tmp_path / "moved-package"
    shutil.copytree(built_package.package_root, copied)
    assert parse_context((copied / "memory/context.md").read_text()) == updated


def test_future_package_finalizes_and_self_validates_native_v2_report(
    built_package: BuildResult,
) -> None:
    root = built_package.package_root
    before = snapshot(root)["context_before_checksum"]
    _updated_context(built_package)
    for path in (
        "outputs/search_plan.md",
        "outputs/candidate_papers.json",
        "outputs/selected_papers.json",
        "outputs/literature_search_report.md",
    ):
        (root / path).write_text("Fictional offline output.\n", encoding="utf-8")
    draft_path = root / "memory/progress/report-draft.json"
    draft = json.loads(draft_path.read_text())
    draft.update(
        {
            "harness_type": "codex",
            "harness_session_id": "fictional-package-session-1",
            "started_at": "2026-08-03T01:00:00Z",
            "completed_at": "2026-08-03T01:10:00Z",
            "status": "COMPLETED",
            "completed_work": ["Wrote four wholly fictional offline outputs."],
            "current_state": "Fictional offline task complete.",
            "next_recommended_action": "Explicitly upload this immutable report in R2B.",
            "continuation_instructions": ["Validate package state before continuing."],
        }
    )
    draft_path.write_text(json.dumps(draft), encoding="utf-8")

    result = finalize(
        package_root=root,
        draft_path="memory/progress/report-draft.json",
        context_before_checksum=str(before),
    )
    report_path = root / result["created"]
    normalized = ProgressReportNormalizer().normalize(report_path.read_bytes())

    assert normalized.source_schema_version == "progress-report/v0.2"
    assert normalized.context_before_checksum == before
    assert normalized.context_after_checksum == sha256_bytes(
        (root / "memory/context.md").read_bytes()
    )
    assert validate_package(root).valid
    isolated_validator = subprocess.run(
        [sys.executable, "-I", "validate_package.py", "--root", "."],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    isolated_report_helper = subprocess.run(
        [
            sys.executable,
            "-I",
            "progress_report.py",
            "validate",
            "--root",
            ".",
            "--report",
            result["created"],
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert isolated_validator.returncode == 0, isolated_validator.stdout
    assert isolated_report_helper.returncode == 0, isolated_report_helper.stdout


def test_self_validator_rejects_dynamic_v2_report_tampering(
    built_package: BuildResult,
) -> None:
    root = built_package.package_root
    before = snapshot(root)["context_before_checksum"]
    _updated_context(built_package)
    for contract in json.loads((root / "package-manifest.json").read_text())[
        "output_contracts"
    ]:
        (root / contract["required_output_path"]).write_text("Fictional.\n")
    draft_path = root / "memory/progress/report-draft.json"
    draft = json.loads(draft_path.read_text())
    draft.update(
        {
            "harness_type": "codex",
            "harness_session_id": "fictional-package-session-1",
            "started_at": "2026-08-03T01:00:00Z",
            "completed_at": "2026-08-03T01:10:00Z",
            "current_state": "Fictional task state.",
            "next_recommended_action": "Stop.",
        }
    )
    draft_path.write_text(json.dumps(draft))
    result = finalize(
        package_root=root,
        draft_path="memory/progress/report-draft.json",
        context_before_checksum=str(before),
    )
    report_path = root / result["created"]
    report = json.loads(report_path.read_text())
    report["current_state"] = "Tampered fictional state."
    report_path.write_text(json.dumps(report))

    with pytest.raises(ValueError, match="identity"):
        validate_package(root)
