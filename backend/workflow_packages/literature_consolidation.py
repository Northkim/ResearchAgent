"""Explicit local composition of two exact selected paper libraries."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import runpy
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

if __package__:
    from .production_workflows import (
        SELECTED_PAPER_LIBRARY_TYPE,
        _build,
        _literature_v0_8_files,
        _production_progress_source,
        _replace_spec,
        selected_paper_library_output_contract,
    )
    from .serialization import canonical_hash, canonical_json, sha256_bytes
    from .template import FileSpec
else:  # Self-contained copy inside an installed Capsule.
    SELECTED_PAPER_LIBRARY_TYPE = "selected-paper-library/v1"

    def canonical_json(value: Any) -> str:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        )

    def sha256_bytes(value: bytes) -> str:
        return "sha256:" + hashlib.sha256(value).hexdigest()

    def canonical_hash(value: Any) -> str:
        return sha256_bytes(canonical_json(value).encode("utf-8"))

    def selected_paper_library_output_contract() -> dict[str, str]:
        return {
            "artifact_type": SELECTED_PAPER_LIBRARY_TYPE,
            "artifact_schema_version": SELECTED_PAPER_LIBRARY_TYPE,
            "media_type": "application/json",
            "relative_path_prefix": "outputs/artifacts/selected-paper-library",
            "content_addressed_filename": "sha256-<content-sha256>.json",
            "progress_artifact_kind": SELECTED_PAPER_LIBRARY_TYPE,
        }

WORKFLOW_ID = "literature-consolidation-local-experimental"
WORKFLOW_VERSION = "0.1.0"
CAPSULE_VERSION = "0.1.0"
TEMPLATE_ID = "literature-consolidation-package"
SKILL_ID = "reagent.local-literature-consolidation"
SKILL_VERSION = "0.1.0"
PROMPT_ID = "literature-consolidation"
PROMPT_VERSION = "0.1.0"

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
ARTIFACT_ID = re.compile(r"^artifact-[0-9a-f]{32}$")


class LiteratureConsolidationError(RuntimeError):
    pass


def workflow_document() -> dict[str, Any]:
    requirements = [
        {
            "requirement_key": key,
            "artifact_type": SELECTED_PAPER_LIBRARY_TYPE,
            "artifact_schema": SELECTED_PAPER_LIBRARY_TYPE,
            "cardinality": "ONE",
            "required": True,
            "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
            "materialization_mode": "VERIFIED_COPY",
            "target_relative_path": target,
        }
        for key, target in (
            ("base_library", "inputs/base-paper-library.json"),
            ("additional_library", "inputs/additional-paper-library.json"),
        )
    ]
    return {
        "schema_version": "local-workflow/v0.2",
        "experimental_status": "EXPERIMENTAL_NOT_FOR_PRODUCTION",
        "workflow_type": "Literature Consolidation",
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "execution_owner": "codex-coordinated-local-workspace",
        "hosted_agent_runtime_required": False,
        "core_capability_maturity": "REVIEWED_CORE",
        "input_requirements": requirements,
        "steps": [
            "materialize-two-exact-paper-libraries",
            "deduplicate-exact-provider-identities",
            "present-combined-screening-to-owner",
            "persist-exact-owner-dispositions",
            "publish-selected-paper-library-v1-content-addressed-file",
            "append-progress-and-promote-canonical-artifact-metadata",
        ],
        "artifact_outputs": [selected_paper_library_output_contract()],
        "composition_policy": {
            "implicit_latest": False,
            "implicit_merge": False,
            "source_count": 2,
            "recursive_composition": True,
            "deduplication": "EXACT_OPENALEX_DOI_OR_PROVIDER_IDENTITY",
            "owner_final_selection": True,
        },
        "skill_scientific_authority": False,
        "immutable_versioning": "first publication",
    }


def contract_checksum() -> str:
    return canonical_hash(workflow_document())


def capsule_checksum() -> str:
    return canonical_hash({
        "generator": f"reagent-{WORKFLOW_ID}/{CAPSULE_VERSION}",
        "workflow_checksum": contract_checksum(),
        "runtime_source": sha256_bytes(Path(__file__).read_bytes()),
        "artifact_output": selected_paper_library_output_contract(),
        "source_roles": ["base_library", "additional_library"],
    })


CAPSULE_CHECKSUM = capsule_checksum()
CAPSULE_ID = "capsule-" + CAPSULE_CHECKSUM[7:39]


def _json(value: Any) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def _contract() -> dict[str, Any]:
    return {
        "schema": "reagent.literature-consolidation/v0.1",
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "core_capability_maturity": "REVIEWED_CORE",
        "input_requirements": workflow_document()["input_requirements"],
        "output_artifact_type": SELECTED_PAPER_LIBRARY_TYPE,
        "owner_decision_schema": "reagent.owner-decision-snapshot.literature/v0.1",
        "runtime_dynamic_paths": [
            "memory/input-provenance.json",
            "memory/current-artifact.json",
            "memory/owner-decisions.json",
            "memory/progress",
        ],
    }


def _files(
    *, project_id: str, project_name: str, package_id: str,
    package_checksum: str, research_topic: str,
) -> dict[str, FileSpec]:
    files = dict(_literature_v0_8_files(
        project_id=project_id,
        project_name=project_name,
        package_id=package_id,
        package_checksum=package_checksum,
        research_topic=research_topic,
    ))
    old_skill = "workflow/skills/literature-search"
    files.pop(f"{old_skill}/SKILL.md")
    files.pop(f"{old_skill}/skill.json")
    instructions = """# Explicit Literature Consolidation

Read only the two exact materialized paper-library inputs. The runner prepares
one deterministic deduplicated candidate set. Present the candidate sources,
overlaps, evidence limitations, and proposed final dispositions to the Owner.
Preserve SELECTED, UNCERTAIN, and EXCLUDED exactly in memory/owner-decisions.json.
After explicit Owner confirmation, write outputs/selected_papers.json and
outputs/literature_search_report.md. Do not use network, infer latest, silently
merge, read sibling Capsules, or claim global novelty. A pinned or user Skill is
guidance only; it is not scientific evidence or evaluation authority.
"""
    skill_contract = {
        "schema_version": "skill-package/v0.2",
        "name": SKILL_ID,
        "semantic_version": SKILL_VERSION,
        "allowed_capabilities": [
            "read_materialized_input", "write_declared_outputs",
            "update_local_context", "append_progress_report",
            "progress.upload/v0.2", "progress.read/v0.1",
        ],
        "input_contract": [
            "inputs/base-paper-library.json",
            "inputs/additional-paper-library.json",
        ],
        "output_contract": [
            "outputs/candidate_papers.json", "outputs/selected_papers.json",
            "outputs/literature_search_report.md",
            "outputs/artifacts/selected-paper-library/sha256-<content-sha256>.json",
        ],
        "prohibited_behavior": [
            "direct_provider_network", "implicit_latest", "implicit_merge",
            "sibling_workflow_read", "scientific_authority_claim",
        ],
    }
    prompt = """# Consolidate two exact Literature results

Inspect outputs/candidate_papers.json prepared from the two exact inputs. Show
the Owner which records came from each source and where exact duplicates were
removed. Propose bounded final SELECTED, UNCERTAIN, and EXCLUDED dispositions,
with concise reasons and evidence limitations. Wait for explicit confirmation.
Then write the declared selection, durable decision snapshot, and concise report.
Do not retrieve new evidence or infer that either source is latest.
"""
    agent = """# ReAgent Literature Consolidation — REVIEWED_CORE

This Capsule combines exactly two Owner-selected paper-library Artifacts. The
exact bindings and Local bytes are authority. The Agent helps compare and screen;
it does not become scientific authority. Complete only after explicit Owner
confirmation. Never use network or read sibling Workflow private state.
"""
    files["workflow/skills/literature-consolidation/SKILL.md"] = FileSpec(
        instructions.encode(), "text/markdown", "bounded consolidation instructions",
        False, "INSTRUCTION",
    )
    files["workflow/skills/literature-consolidation/skill.json"] = FileSpec(
        _json(skill_contract), "application/json", "consolidation Skill contract",
        False, "CONFIGURATION",
    )
    _replace_spec(files, "AGENT.md", agent.encode())
    _replace_spec(files, "workflow/prompts/one-round.md", prompt.encode())
    _replace_spec(files, "workflow/workflow.json", _json(workflow_document()))
    files["workflow/literature-consolidation.json"] = FileSpec(
        _json(_contract()), "application/json", "exact composition contract",
        False, "CONFIGURATION",
    )
    files["workflow/artifact-inputs.json"] = FileSpec(
        _json({
            "schema_version": "reagent.artifact-input-contract/v0.1",
            "requirements": workflow_document()["input_requirements"],
        }),
        "application/json", "exact source library requirements", False,
        "CONFIGURATION",
    )
    _replace_spec(files, "reagent_local.py", Path(__file__).read_bytes())
    _replace_spec(files, "validate_package.py", Path(__file__).read_bytes())
    _replace_spec(files, "progress_report.py", _production_progress_source())
    control = json.loads(files["memory/round-control.json"].content)
    control.update({
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "workflow_checksum": contract_checksum(),
    })
    _replace_spec(files, "memory/round-control.json", _json(control))
    context = {
        "schema_version": "reagent.literature-consolidation-context/v0.1",
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "package_id": package_id,
        "package_checksum": package_checksum,
        "stage": "SELECT_INPUT",
        "latest_output": None,
        "updated_at": "2026-08-01T00:00:00Z",
    }
    _replace_spec(
        files,
        "memory/context.md",
        ("# Literature Consolidation Context\n\n```json\n" + canonical_json(context) + "\n```\n").encode(),
    )
    project = json.loads(files["inputs/project.json"].content)
    project["selected_workflow"] = WORKFLOW_ID
    _replace_spec(files, "inputs/project.json", _json(project))
    query_plan = json.loads(files["memory/search/query_plan.json"].content)
    query_plan["original_topic"] = research_topic
    _replace_spec(files, "memory/search/query_plan.json", _json(query_plan))
    return files


def build_package(**kwargs: Any):
    return _build(
        renderer=_files,
        workflow_type="Literature Consolidation",
        workflow_id=WORKFLOW_ID,
        workflow_version=WORKFLOW_VERSION,
        template_id=TEMPLATE_ID,
        template_version=CAPSULE_VERSION,
        **kwargs,
    )


def _object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise LiteratureConsolidationError(f"{label} must be one regular unlinked file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LiteratureConsolidationError(f"{label} must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise LiteratureConsolidationError(f"{label} must be an object")
    return value


def _atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = _json(value)
    with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content); handle.flush(); os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{path.name}.", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _normalized_files(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for value in values:
        item = dict(value)
        if item.get("mutable_by_harness"):
            item["sha256"] = None; item["byte_size"] = None
        result.append(item)
    return result


def _validate_library(path: Path, checksum: str) -> dict[str, Any]:
    if sha256_bytes(path.read_bytes()) != checksum:
        raise LiteratureConsolidationError("materialized library checksum drifted")
    value = _object(path, "selected paper library")
    if set(value) != {"schema", "source_schemas", "source_checksums", "papers"} or value["schema"] != SELECTED_PAPER_LIBRARY_TYPE:
        raise LiteratureConsolidationError("selected paper library schema is invalid")
    if not isinstance(value["papers"], list) or len(value["papers"]) > 15:
        raise LiteratureConsolidationError("selected paper library is not bounded")
    return value


def _load_inputs(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    provenance = _object(root / "memory/input-provenance.json", "input provenance")
    if provenance.get("schema_version") != "reagent.literature-consolidation-input-provenance/v0.1":
        raise LiteratureConsolidationError("input provenance schema mismatch")
    records = provenance.get("artifacts")
    if not isinstance(records, dict) or set(records) != {"base_library", "additional_library"}:
        raise LiteratureConsolidationError("exactly two source libraries are required")
    if records["base_library"] == records["additional_library"]:
        raise LiteratureConsolidationError("source libraries must be distinct exact Artifacts")
    values = []
    for key, relative in (
        ("base_library", "inputs/base-paper-library.json"),
        ("additional_library", "inputs/additional-paper-library.json"),
    ):
        record = records[key]
        if not isinstance(record, dict) or set(record) != {"artifact_id", "artifact_type", "sha256"}:
            raise LiteratureConsolidationError(f"{key} provenance is invalid")
        if not ARTIFACT_ID.fullmatch(str(record["artifact_id"])) or record["artifact_type"] != SELECTED_PAPER_LIBRARY_TYPE or not SHA256.fullmatch(str(record["sha256"])):
            raise LiteratureConsolidationError(f"{key} identity is invalid")
        values.append(_validate_library(root / relative, record["sha256"]))
    return records, values[0], values[1]


def _dedupe_key(paper: dict[str, Any]) -> tuple[str, str]:
    for key in ("openalex_id", "doi", "provider_id"):
        value = paper.get(key)
        if isinstance(value, str) and value.strip():
            return key, value.strip().lower()
    raise LiteratureConsolidationError("paper has no stable provider identity")


def _prepare_candidates(root: Path, base: dict[str, Any], additional: dict[str, Any]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for library in (base, additional):
        for item in library["papers"]:
            if not isinstance(item, dict) or set(item) != {"candidate_id", "paper", "selection"}:
                raise LiteratureConsolidationError("source paper entry is invalid")
            paper = item["paper"]
            if not isinstance(paper, dict) or paper.get("candidate_id") != item["candidate_id"]:
                raise LiteratureConsolidationError("source candidate identity is invalid")
            identity = _dedupe_key(paper)
            if identity in seen:
                continue
            seen.add(identity)
            candidates.append(paper)
    if len(candidates) > 15:
        raise LiteratureConsolidationError("combined candidate set exceeds the bounded maximum")
    result = {"schema_version": "candidate-papers/v0.2", "mode": "NORMAL", "candidates": candidates}
    path = root / "outputs/candidate_papers.json"
    if path.exists() or path.is_symlink():
        if path.is_symlink() or _object(path, "candidate papers") != result:
            raise LiteratureConsolidationError("existing combined candidates differ from exact inputs")
    else:
        _atomic(path, result)
    return result


def _validate_owner_state(root: Path, candidates: dict[str, Any]) -> None:
    selected = _object(root / "outputs/selected_papers.json", "selected papers")
    decisions = _object(root / "memory/owner-decisions.json", "Owner decisions")
    candidate_ids = [item["candidate_id"] for item in candidates["candidates"]]
    if decisions.get("candidate_set_checksum") != sha256_bytes((root / "outputs/candidate_papers.json").read_bytes()):
        raise LiteratureConsolidationError("Owner decisions do not bind the exact candidate set")
    rows = decisions.get("decisions")
    if not isinstance(rows, list) or {item.get("candidate_id") for item in rows if isinstance(item, dict)} != set(candidate_ids):
        raise LiteratureConsolidationError("Owner decisions do not cover every candidate")
    by_id = {item["candidate_id"]: item["disposition"] for item in rows}
    if any(value not in {"SELECTED", "UNCERTAIN", "EXCLUDED"} for value in by_id.values()):
        raise LiteratureConsolidationError("Owner disposition is invalid")
    selected_ids = [item.get("candidate_id") for item in selected.get("selected", []) if isinstance(item, dict)]
    excluded_ids = [item.get("candidate_id") for item in selected.get("exclusions", []) if isinstance(item, dict)]
    if set(selected_ids) != {key for key, value in by_id.items() if value == "SELECTED"}:
        raise LiteratureConsolidationError("selected output differs from exact Owner decisions")
    if set(excluded_ids) != {key for key, value in by_id.items() if value != "SELECTED"}:
        raise LiteratureConsolidationError("withheld output differs from exact Owner decisions")


def _validate_literature_outputs(root: Path) -> None:
    """Compatibility seam used by the immutable v1 Artifact finalizer."""

    candidates = _object(root / "outputs/candidate_papers.json", "candidate papers")
    selected = _object(root / "outputs/selected_papers.json", "selected papers")
    if set(candidates) != {"schema_version", "mode", "candidates"} or candidates["schema_version"] != "candidate-papers/v0.2" or candidates["mode"] not in {"NORMAL", "DEMO"}:
        raise LiteratureConsolidationError("candidate-papers/v0.2 is invalid")
    records = candidates["candidates"]
    if not isinstance(records, list) or len(records) > 15:
        raise LiteratureConsolidationError("candidate records are invalid")
    required_candidate = {
        "candidate_id", "provider_id", "openalex_id", "title", "authors",
        "publication_year", "doi", "source", "language", "abstract",
        "source_query_ids", "provenance_checksum", "deduplication_status",
    }
    by_id = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != required_candidate or record.get("candidate_id") in by_id:
            raise LiteratureConsolidationError("candidate record fields are invalid")
        by_id[record["candidate_id"]] = record
    if set(selected) != {"schema_version", "mode", "selection_status", "selected", "exclusions", "exclusion_summary"} or selected["schema_version"] != "selected-papers/v0.2" or selected["mode"] != candidates["mode"] or selected["selection_status"] not in {"SUFFICIENT", "INSUFFICIENT"}:
        raise LiteratureConsolidationError("selected-papers/v0.2 is invalid")
    selected_ids = []
    for item in selected["selected"]:
        if not isinstance(item, dict) or set(item) != {"candidate_id", "relevance_decision", "inclusion_reason", "evidence_availability"} or item.get("candidate_id") not in by_id or item.get("relevance_decision") != "INCLUDE" or item.get("evidence_availability") not in {"METADATA_ONLY", "METADATA_AND_ABSTRACT"}:
            raise LiteratureConsolidationError("selected record is invalid")
        selected_ids.append(item["candidate_id"])
    excluded_ids = []
    for item in selected["exclusions"]:
        if not isinstance(item, dict) or set(item) != {"candidate_id", "reason"} or item.get("candidate_id") not in by_id:
            raise LiteratureConsolidationError("withheld record is invalid")
        excluded_ids.append(item["candidate_id"])
    if len(selected_ids + excluded_ids) != len(set(selected_ids + excluded_ids)) or set(selected_ids + excluded_ids) != set(by_id):
        raise LiteratureConsolidationError("selection must classify every exact candidate once")
    _validate_owner_state(root, candidates)


def validate(root: str | Path, *, pristine: bool = False) -> dict[str, Any]:
    package = Path(root)
    manifest = _object(package / "package-manifest.json", "package manifest")
    files = manifest.get("files")
    if not isinstance(files, list) or manifest.get("workflow_id") != WORKFLOW_ID or manifest.get("workflow_version") != WORKFLOW_VERSION or manifest.get("package_template_version") != CAPSULE_VERSION:
        raise LiteratureConsolidationError("Capsule identity mismatch")
    if manifest.get("file_manifest_checksum") != canonical_hash(_normalized_files(files)):
        raise LiteratureConsolidationError("file manifest checksum mismatch")
    payload = dict(manifest); payload["manifest_checksum"] = None; payload["package_checksum"] = None; payload["files"] = _normalized_files(files)
    if manifest.get("manifest_checksum") != canonical_hash(payload):
        raise LiteratureConsolidationError("manifest checksum mismatch")
    if manifest.get("package_checksum") != canonical_hash({"package_id": manifest["package_id"], "package_schema_version": manifest["package_schema_version"], "file_manifest_checksum": manifest["file_manifest_checksum"], "manifest_checksum": manifest["manifest_checksum"]}):
        raise LiteratureConsolidationError("package checksum mismatch")
    entries = {item["relative_path"]: item for item in files}
    allowed = {
        "package-manifest.json", "memory/input-provenance.json",
        "memory/current-artifact.json", "inputs/base-paper-library.json",
        "inputs/additional-paper-library.json",
    }
    for path in package.rglob("*"):
        if path.is_symlink():
            raise LiteratureConsolidationError("symbolic links are forbidden")
        if not path.is_file():
            continue
        relative = path.relative_to(package).as_posix()
        entry = entries.get(relative)
        dynamic = relative in allowed or relative.startswith(("outputs/", "memory/progress/"))
        if entry is None and not dynamic:
            raise LiteratureConsolidationError(f"undeclared file rejected: {relative}")
        if entry is not None and (pristine or not entry.get("mutable_by_harness")):
            content = path.read_bytes()
            if entry.get("sha256") != sha256_bytes(content) or entry.get("byte_size") != len(content):
                raise LiteratureConsolidationError(f"file integrity mismatch: {relative}")
    if canonical_hash(_object(package / "workflow/workflow.json", "workflow")) != manifest.get("workflow_checksum"):
        raise LiteratureConsolidationError("workflow checksum mismatch")
    provenance = package / "memory/input-provenance.json"
    if provenance.exists() or provenance.is_symlink():
        _, base, additional = _load_inputs(package)
        candidates_path = package / "outputs/candidate_papers.json"
        if candidates_path.exists() or candidates_path.is_symlink():
            candidates = _prepare_candidates(package, base, additional)
            if (package / "outputs/selected_papers.json").exists():
                _validate_owner_state(package, candidates)
    return {"valid": True, "package_id": manifest["package_id"], "package_checksum": manifest["package_checksum"], "manifest_checksum": manifest["manifest_checksum"], "declared_file_count": len(files), "harness_acceptance_status": manifest["harness_acceptance_status"]}


def _run_harness(root: Path, executable: str | None) -> None:
    selected = executable or os.environ.get("REAGENT_CODEX_EXECUTABLE", "codex")
    resolved = str(Path(selected).resolve()) if os.path.sep in selected else shutil.which(selected)
    if resolved is None:
        raise LiteratureConsolidationError("Codex CLI is unavailable")
    environment = {key: value for key, value in os.environ.items() if key in {"PATH", "TMPDIR", "LANG", "LC_ALL", "TERM"}}
    instruction = (root / "workflow/prompts/one-round.md").read_text()
    completed = subprocess.run([resolved, "--sandbox", "workspace-write", "--ask-for-approval", "on-request", "--no-alt-screen", "-C", str(root), instruction], cwd=root, env=environment, check=False)
    if completed.returncode != 0:
        raise LiteratureConsolidationError("Codex exited before consolidation completed")


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def run(root: Path, workflow_instance_id: str, *, codex_executable: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    validate(root, pristine=False)
    if list((root / "memory/progress/reports").glob("*.json")):
        raise LiteratureConsolidationError("Literature Consolidation already has terminal Progress")
    _records, base, additional = _load_inputs(root)
    candidates = _prepare_candidates(root, base, additional)
    _run_harness(root, codex_executable)
    _validate_owner_state(root, candidates)
    progress = runpy.run_path(str(root / "progress_report.py"))
    snapshot = progress["snapshot"](root)
    now = _timestamp()
    context = {"schema_version": "reagent.literature-consolidation-context/v0.1", "workflow_id": WORKFLOW_ID, "workflow_version": WORKFLOW_VERSION, "stage": "COMPLETED", "updated_at": now}
    _atomic_bytes(
        root / "memory/context.md",
        (
            "# Literature Consolidation Context\n\n```json\n"
            + canonical_json(context)
            + "\n```\n"
        ).encode("utf-8"),
    )
    draft = _object(root / "memory/progress/report-draft.json", "Progress draft")
    draft.update({"started_at": now, "completed_at": now, "status": "COMPLETED", "completed_work": ["Combined two exact paper libraries", "Recorded exact Owner screening dispositions", "Published one consolidated selected paper library"], "current_state": "COMPLETED", "next_recommended_action": "Select the exact consolidated paper library for downstream research", "warnings": ["No new evidence was retrieved during consolidation"], "errors": [], "unresolved_questions": [], "continuation_instructions": ["Use the content-addressed selected-paper-library/v1 Artifact"]})
    _atomic(root / "memory/progress/report-draft.json", draft)
    finalized = progress["finalize"](package_root=root, draft_path="memory/progress/report-draft.json", context_before_checksum=snapshot["context_before_checksum"])
    validate(root, pristine=False)
    return {"status": "COMPLETED", "progress_report": finalized["created"], "workflow_instance_id": workflow_instance_id}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("root", type=Path)
    run_parser.add_argument("--workflow-instance", required=True)
    run_parser.add_argument("--api-url")
    run_parser.add_argument("--codex-executable")
    run_parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.preflight_only:
            validate(args.root, pristine=False); _load_inputs(args.root)
            print(canonical_json({"status": "PREFLIGHT_READY"}))
        else:
            print(canonical_json(run(args.root, args.workflow_instance, codex_executable=args.codex_executable)))
    except LiteratureConsolidationError as error:
        print(f"Literature Consolidation stopped: {error}", file=os.sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
