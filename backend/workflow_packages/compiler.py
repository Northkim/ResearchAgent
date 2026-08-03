"""Deterministic compiler for one experimental local Literature Search package."""

from __future__ import annotations

import json
import os
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import (
    EXPERIMENTAL_STATUS,
    HARNESS_ACCEPTANCE_STATUS,
    PACKAGE_SCHEMA_VERSION,
    PackageFileEntry,
    PackageInputManifest,
    PackageOutputContract,
    PromptPin,
    SkillPin,
    WorkflowPackageManifest,
)
from .security import reject_sensitive_content, require_relative_path
from .serialization import canonical_hash, canonical_json, sha256_bytes
from .template import (
    DETERMINISTIC_GENERATED_AT,
    GENERATOR_VERSION,
    PROMPT_ID,
    PROMPT_VERSION,
    SKILL_ID,
    SKILL_VERSION,
    TEMPLATE_ID,
    TEMPLATE_VERSION,
    WORKFLOW_ID,
    WORKFLOW_VERSION,
    FileSpec,
    render_files,
    workflow_document,
)
from .validator import ValidationResult, validate_archive, validate_package

_ZERO_HASH = "sha256:" + "0" * 64
_ZIP_TIMESTAMP = (2000, 1, 1, 0, 0, 0)


@dataclass(frozen=True, slots=True)
class BuildResult:
    package_id: str
    package_schema_version: str
    package_root: Path
    archive_path: Path
    manifest_checksum: str
    package_checksum: str
    zip_checksum: str
    file_count: int
    package_size_bytes: int
    validation: ValidationResult
    archive_validation: ValidationResult
    harness_acceptance_status: str


def _project_id(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("project identity must be non-empty")
    if any(character not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for character in value):
        raise ValueError("project identity must be a lowercase portable identifier")
    if not value[0].isalnum() or len(value) > 96:
        raise ValueError("project identity is invalid")
    return value


def _entry(path: str, spec: FileSpec) -> PackageFileEntry:
    reject_sensitive_content(spec.content, path=path)
    return PackageFileEntry(
        relative_path=require_relative_path(path),
        media_type=spec.media_type,
        role=spec.role,
        sha256=sha256_bytes(spec.content),
        byte_size=len(spec.content),
        mutable_by_harness=spec.mutable_by_harness,
        state_classification=spec.state_classification,
        requirement=spec.requirement,
    )


def _normalized_entry_dicts(entries: tuple[PackageFileEntry, ...]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for entry in entries:
        item = entry.to_dict()
        if entry.mutable_by_harness:
            item["sha256"] = None
            item["byte_size"] = None
        values.append(item)
    return values


def _manifest_hash(manifest: WorkflowPackageManifest) -> str:
    payload = manifest.to_dict()
    payload["manifest_checksum"] = None
    payload["package_checksum"] = None
    payload["files"] = _normalized_entry_dicts(manifest.files)
    return canonical_hash(payload)


def _package_hash(*, package_id: str, file_manifest_checksum: str, manifest_checksum: str) -> str:
    return canonical_hash(
        {
            "package_id": package_id,
            "package_schema_version": PACKAGE_SCHEMA_VERSION,
            "file_manifest_checksum": file_manifest_checksum,
            "manifest_checksum": manifest_checksum,
        }
    )


def _pins(files: dict[str, FileSpec]) -> tuple[tuple[SkillPin, ...], tuple[PromptPin, ...]]:
    skill_path = "workflow/skills/literature-search/SKILL.md"
    skill_contract_path = "workflow/skills/literature-search/skill.json"
    skill_checksum = canonical_hash(
        {
            "instructions": sha256_bytes(files[skill_path].content),
            "contract": sha256_bytes(files[skill_contract_path].content),
        }
    )
    skill = SkillPin(
        name=SKILL_ID,
        semantic_version=SKILL_VERSION,
        source_type="BUNDLED_REAGENT_ORIGINAL",
        source_identity="reagent-r1a-local-literature-search",
        checksum=skill_checksum,
        relative_path=skill_path,
        required_capabilities=(
            "read_local_package",
            "write_declared_outputs",
            "update_local_context",
            "append_progress_report",
        ),
    )
    prompt_path = "workflow/prompts/search-planning.md"
    prompt = PromptPin(
        prompt_id=PROMPT_ID,
        version=PROMPT_VERSION,
        checksum=sha256_bytes(files[prompt_path].content),
        relative_path=prompt_path,
        purpose="Plan and document bounded screening of the supplied fictional catalog.",
    )
    return (skill,), (prompt,)


def _inputs(files: dict[str, FileSpec]) -> tuple[PackageInputManifest, ...]:
    return (
        PackageInputManifest(
            input_id="synthetic-research-request",
            relative_path="inputs/research_request.json",
            checksum=sha256_bytes(files["inputs/research_request.json"].content),
            read_only_required=True,
            content_type="application/json",
            source_classification="SYNTHETIC_OFFLINE",
        ),
        PackageInputManifest(
            input_id="fictional-source-catalog",
            relative_path="inputs/fictional_source_catalog.json",
            checksum=sha256_bytes(files["inputs/fictional_source_catalog.json"].content),
            read_only_required=True,
            content_type="application/json",
            source_classification="SYNTHETIC_OFFLINE",
        ),
    )


def _outputs() -> tuple[PackageOutputContract, ...]:
    return (
        PackageOutputContract("outputs/search_plan.md", "SEARCH_PLAN", "text/markdown", "search-plan/v0.1", "Agent Harness", "required Markdown with offline-scope disclosure"),
        PackageOutputContract("outputs/candidate_papers.json", "CANDIDATE_SCREENING", "application/json", "candidate-papers/v0.1", "Agent Harness", "validate against bundled candidate schema"),
        PackageOutputContract("outputs/selected_papers.json", "BOUNDED_SELECTION", "application/json", "selected-papers/v0.1", "Agent Harness", "validate against bundled selection schema"),
        PackageOutputContract("outputs/literature_search_report.md", "LITERATURE_SEARCH_REPORT", "text/markdown", "literature-search-report/v0.1", "Agent Harness", "required Markdown; must not claim real provider search"),
    )


def _make_manifest(project_id: str, package_id: str, files: dict[str, FileSpec]) -> WorkflowPackageManifest:
    entries = tuple(_entry(path, files[path]) for path in sorted(files))
    skill_pins, prompt_pins = _pins(files)
    file_manifest_checksum = canonical_hash(_normalized_entry_dicts(entries))
    manifest = WorkflowPackageManifest(
        package_id=package_id,
        package_schema_version=PACKAGE_SCHEMA_VERSION,
        experimental_project_identity=project_id,
        workflow_type="Literature Search",
        workflow_id=WORKFLOW_ID,
        workflow_version=WORKFLOW_VERSION,
        workflow_checksum=canonical_hash(workflow_document()),
        package_template_id=TEMPLATE_ID,
        package_template_version=TEMPLATE_VERSION,
        skill_pins=skill_pins,
        prompt_pins=prompt_pins,
        input_manifest=_inputs(files),
        output_contracts=_outputs(),
        required_harness_capabilities=(
            "read_and_write_local_files",
            "run_local_python_validator",
            "calculate_sha256",
            "follow_AGENT_md",
        ),
        content_scope_declaration="WHOLLY_FICTIONAL_OFFLINE_CATALOG; NO REAL SEARCH; NO FULL TEXT; NO PDF",
        generated_at=DETERMINISTIC_GENERATED_AT,
        generator_version=GENERATOR_VERSION,
        files=entries,
        file_manifest_checksum=file_manifest_checksum,
        manifest_checksum=_ZERO_HASH,
        package_checksum=_ZERO_HASH,
        continuation_policy="FILES_ONLY; validate, read context and latest immutable Progress Report, preserve prior work",
        proxy_capability_declaration="OFFLINE_DISABLED_R1A_PLACEHOLDER_ONLY; NO CREDENTIAL",
        experimental_status_declaration=EXPERIMENTAL_STATUS,
        harness_acceptance_status=HARNESS_ACCEPTANCE_STATUS,
    )
    manifest_checksum = _manifest_hash(manifest)
    package_checksum = _package_hash(
        package_id=package_id,
        file_manifest_checksum=file_manifest_checksum,
        manifest_checksum=manifest_checksum,
    )
    return WorkflowPackageManifest(
        **{
            **manifest.to_dict(),
            "skill_pins": skill_pins,
            "prompt_pins": prompt_pins,
            "input_manifest": manifest.input_manifest,
            "output_contracts": manifest.output_contracts,
            "files": entries,
            "required_harness_capabilities": manifest.required_harness_capabilities,
            "manifest_checksum": manifest_checksum,
            "package_checksum": package_checksum,
        }
    )


def _render(project_id: str, package_id: str) -> tuple[dict[str, FileSpec], WorkflowPackageManifest]:
    placeholder_files = render_files(project_id=project_id, package_id=package_id, package_checksum=_ZERO_HASH)
    preliminary = _make_manifest(project_id, package_id, placeholder_files)
    files = render_files(project_id=project_id, package_id=package_id, package_checksum=preliminary.package_checksum)
    manifest = _make_manifest(project_id, package_id, files)
    if manifest.package_checksum != preliminary.package_checksum:
        raise RuntimeError("mutable context unexpectedly affected package identity")
    return files, manifest


def _write_files(root: Path, files: dict[str, FileSpec], manifest: WorkflowPackageManifest) -> None:
    root.mkdir(parents=True, exist_ok=False)
    for relative_path in sorted(files):
        target = root.joinpath(*relative_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(files[relative_path].content)
    (root / "package-manifest.json").write_text(canonical_json(manifest) + "\n", encoding="utf-8")


def _same_tree(left: Path, right: Path) -> bool:
    left_files = sorted(path.relative_to(left).as_posix() for path in left.rglob("*") if path.is_file())
    right_files = sorted(path.relative_to(right).as_posix() for path in right.rglob("*") if path.is_file())
    return left_files == right_files and all((left / path).read_bytes() == (right / path).read_bytes() for path in left_files)


def _write_deterministic_zip(root: Path, destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED, strict_timestamps=True) as bundle:
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            if path.is_symlink():
                raise ValueError("package archive refuses symbolic links")
            relative = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(relative, date_time=_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.flag_bits |= 0x800
            bundle.writestr(info, path.read_bytes())


def _write_immutable(path: Path, content: bytes) -> None:
    if path.exists():
        if path.is_symlink() or path.read_bytes() != content:
            raise FileExistsError(f"existing build output differs: {path.name}")
        return
    path.write_bytes(content)


def build_literature_search_package(*, project_id: str, output_root: str | Path) -> BuildResult:
    project_id = _project_id(project_id)
    output = Path(output_root)
    if output.is_absolute():
        raise ValueError("output_root must be repository-relative")
    if output.is_symlink():
        raise ValueError("output_root must not be a symbolic link")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    package_id = f"literature-search-{project_id}-v0.1"
    files, manifest = _render(project_id, package_id)

    with tempfile.TemporaryDirectory(prefix=".r1a-build-", dir=output.parent) as temporary:
        temporary_root = Path(temporary) / "package"
        _write_files(temporary_root, files, manifest)
        validation = validate_package(temporary_root, pristine=True)
        package_root = output / "package"
        if package_root.exists():
            if package_root.is_symlink() or not _same_tree(temporary_root, package_root):
                raise FileExistsError("existing package differs from deterministic rebuild")
        else:
            os.replace(temporary_root, package_root)

    archive_path = output / f"{package_id}.zip"
    with tempfile.NamedTemporaryFile(prefix=".r1a-archive-", suffix=".zip", dir=output, delete=False) as temporary_archive:
        temporary_archive_path = Path(temporary_archive.name)
    try:
        _write_deterministic_zip(package_root, temporary_archive_path)
        archive_bytes = temporary_archive_path.read_bytes()
        _write_immutable(archive_path, archive_bytes)
    finally:
        temporary_archive_path.unlink(missing_ok=True)
    archive_validation = validate_archive(archive_path, pristine=True)
    zip_checksum = sha256_bytes(archive_path.read_bytes())
    package_size = sum(path.stat().st_size for path in package_root.rglob("*") if path.is_file())
    receipt = {
        "schema_version": "workflow-package-build-receipt/v0.1",
        "generated_at": DETERMINISTIC_GENERATED_AT,
        "package_id": package_id,
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "manifest_checksum": manifest.manifest_checksum,
        "package_checksum": manifest.package_checksum,
        "zip_checksum": zip_checksum,
        "relative_package_root": f"{output.as_posix()}/package",
        "relative_archive_path": f"{output.as_posix()}/{archive_path.name}",
        "validation": "PASS",
        "harness_acceptance_status": HARNESS_ACCEPTANCE_STATUS,
        "network_called": False,
        "hosted_agent_runtime_invoked": False,
    }
    validation_receipt = {
        "schema_version": "workflow-package-validation-receipt/v0.1",
        "package_id": package_id,
        "folder_validation": validation.valid,
        "archive_validation": archive_validation.valid,
        "declared_file_count": validation.declared_file_count,
        "package_checksum": validation.package_checksum,
        "harness_acceptance_status": HARNESS_ACCEPTANCE_STATUS,
    }
    handoff = """# R1B Handoff\n\nStatus: `HARNESS_ACCEPTANCE_PENDING`\n\nExtract the ZIP into a clean directory, start a fresh Harness session there, and provide only:\n\n`Read the package instructions and continue the task.`\n\nR1A did not execute or simulate that acceptance.\n"""
    _write_immutable(output / "build-receipt.json", (canonical_json(receipt) + "\n").encode())
    _write_immutable(output / "validation-receipt.json", (canonical_json(validation_receipt) + "\n").encode())
    _write_immutable(output / "R1B_HANDOFF.md", handoff.encode())
    return BuildResult(
        package_id=package_id,
        package_schema_version=PACKAGE_SCHEMA_VERSION,
        package_root=package_root,
        archive_path=archive_path,
        manifest_checksum=manifest.manifest_checksum,
        package_checksum=manifest.package_checksum,
        zip_checksum=zip_checksum,
        file_count=validation.declared_file_count + 1,
        package_size_bytes=package_size,
        validation=validation,
        archive_validation=archive_validation,
        harness_acceptance_status=HARNESS_ACCEPTANCE_STATUS,
    )
