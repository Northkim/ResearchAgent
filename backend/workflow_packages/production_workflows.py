"""Reviewed B7 Workflow definitions and deterministic Capsule compilers.

The accepted Literature Search 0.3.0 / Capsule 0.5.0 sources remain untouched.
This module builds the separately pinned 0.4.0/0.6.0 producer and the first
production Idea Discovery 0.1.0 consumer.
"""

from __future__ import annotations

import json
import os
import runpy
import stat
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Callable

from .compiler import BuildResult
from .contracts import (
    CURRENT_HARNESS_ACCEPTANCE_STATUS,
    CURRENT_PROGRESS_SCHEMA_VERSION,
    EXPERIMENTAL_STATUS,
    PACKAGE_SCHEMA_VERSION,
    PROGRESS_UPLOAD_STATUS,
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
    DEFAULT_RESEARCH_TOPIC,
    FileSpec,
    render_files as render_legacy_literature_files,
)
from .validator import ValidationResult

LITERATURE_SEARCH_WORKFLOW_ID = "literature-search-local-experimental"
LITERATURE_SEARCH_WORKFLOW_VERSION = "0.4.0"
LITERATURE_SEARCH_TEMPLATE_ID = "literature-search-package-experimental"
LITERATURE_SEARCH_CAPSULE_VERSION = "0.6.0"
LITERATURE_SEARCH_SKILL_VERSION = "0.4.0"
LITERATURE_SEARCH_PROMPT_VERSION = "0.4.0"

IDEA_DISCOVERY_WORKFLOW_ID = "idea-discovery-local-experimental"
IDEA_DISCOVERY_WORKFLOW_VERSION = "0.1.0"
IDEA_DISCOVERY_TEMPLATE_ID = "idea-discovery-package-experimental"
IDEA_DISCOVERY_CAPSULE_VERSION = "0.1.0"
IDEA_DISCOVERY_PROMPT_ID = "idea-discovery-interactive"
IDEA_DISCOVERY_PROMPT_VERSION = "0.1.0"
IDEA_DISCOVERY_SKILL_VERSION = "0.1.0"

SELECTED_PAPER_LIBRARY_TYPE = "selected-paper-library/v1"
SELECTED_PAPER_LIBRARY_SCHEMA = "selected-paper-library/v1"
SELECTED_PAPER_LIBRARY_PREFIX = "outputs/artifacts/selected-paper-library"
IDEA_INPUT_TARGET = "inputs/selected-paper-library.json"

_ZERO_HASH = "sha256:" + "0" * 64
_ZIP_TIMESTAMP = (2000, 1, 1, 0, 0, 0)


def selected_paper_library_output_contract() -> dict[str, str]:
    return {
        "artifact_type": SELECTED_PAPER_LIBRARY_TYPE,
        "artifact_schema_version": SELECTED_PAPER_LIBRARY_SCHEMA,
        "media_type": "application/json",
        "relative_path_prefix": SELECTED_PAPER_LIBRARY_PREFIX,
        "content_addressed_filename": "sha256-<content-sha256>.json",
        "progress_artifact_kind": SELECTED_PAPER_LIBRARY_TYPE,
    }


def literature_search_workflow_document() -> dict[str, Any]:
    return {
        "schema_version": "local-workflow/v0.2",
        "experimental_status": EXPERIMENTAL_STATUS,
        "workflow_type": "Literature Search",
        "workflow_id": LITERATURE_SEARCH_WORKFLOW_ID,
        "workflow_version": LITERATURE_SEARCH_WORKFLOW_VERSION,
        "execution_owner": "codex-local-agent-harness",
        "hosted_agent_runtime_required": False,
        "network_boundary": "LOCAL_LAUNCHER_TO_REAGENT_PROXY_ONLY",
        "steps": [
            "validate-package-and-local-session",
            "interactive-codex-plan-and-owner-confirmation",
            "bounded-openalex-search-through-reagent-proxy",
            "interactive-screening-and-owner-confirmation",
            "explicit-owner-finish",
            "validate-candidate-and-selection-v0.2",
            "publish-selected-paper-library-v1-content-addressed-file",
            "append-progress-and-promote-canonical-artifact-metadata",
        ],
        "artifact_outputs": [selected_paper_library_output_contract()],
        "immutable_versioning": "0.3.0/0.5.0 remains independently valid",
    }


def idea_discovery_workflow_document() -> dict[str, Any]:
    return {
        "schema_version": "local-workflow/v0.2",
        "experimental_status": EXPERIMENTAL_STATUS,
        "workflow_type": "Idea Discovery",
        "workflow_id": IDEA_DISCOVERY_WORKFLOW_ID,
        "workflow_version": IDEA_DISCOVERY_WORKFLOW_VERSION,
        "execution_owner": "codex-local-agent-harness",
        "hosted_agent_runtime_required": False,
        "network_boundary": "NO_WORKFLOW_NETWORK_REQUIRED",
        "reviewed_skills": [{
            "name": "reagent.evidence-grounded-ideation",
            "version": IDEA_DISCOVERY_SKILL_VERSION,
            "trust": "BUILT_IN_REVIEWED_ONLY",
        }],
        "input_requirements": [
            {
                "requirement_key": "paper_library",
                "artifact_type": SELECTED_PAPER_LIBRARY_TYPE,
                "artifact_schema": SELECTED_PAPER_LIBRARY_SCHEMA,
                "cardinality": "ONE",
                "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
                "materialization_mode": "COPY",
                "target_relative_path": IDEA_INPUT_TARGET,
            }
        ],
        "stages": [
            "INPUT_REVIEW",
            "LANDSCAPE_ANALYSIS",
            "GAP_EXPLORATION",
            "CANDIDATE_IDEAS",
            "USER_REVIEW",
            "REFINEMENT",
            "COMPLETED",
        ],
        "outputs": [
            {"path": "outputs/candidate_ideas.json", "schema": "candidate-ideas/v0.1"},
            {"path": "outputs/idea_discovery_report.md", "schema": "idea-discovery-report/v0.1"},
        ],
        "novelty_boundary": "candidate directions require further validation",
    }


def literature_search_contract_checksum() -> str:
    return canonical_hash(literature_search_workflow_document())


def idea_discovery_contract_checksum() -> str:
    return canonical_hash(idea_discovery_workflow_document())


def _json(value: Any) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def _production_progress_source() -> bytes:
    source = Path(__file__).with_name("package_progress.py").read_text(encoding="utf-8")
    source = source.replace("import json\n", "import json\nimport os\nimport runpy\nimport tempfile\n", 1)
    marker = "\ndef finalize(\n"
    if marker not in source:
        raise RuntimeError("accepted Progress helper extension point is unavailable")
    source = source.replace(marker, _SELECTED_LIBRARY_HELPER + marker, 1)
    output_marker = "    skill_pins = [\n"
    if output_marker not in source:
        raise RuntimeError("accepted Progress output extension point is unavailable")
    source = source.replace(
        output_marker,
        "    outputs.append(_build_selected_paper_library(root))\n" + output_marker,
        1,
    )
    return source.encode("utf-8")


def _production_runner_source() -> bytes:
    return _LITERATURE_RUNNER_WRAPPER.encode("utf-8")


def _production_validator_source() -> bytes:
    source = Path(__file__).with_name("package_validator.py").read_text(encoding="utf-8")
    marker = '        "memory/search/operations/",\n'
    if marker not in source:
        raise RuntimeError("accepted Package validator extension point is unavailable")
    source = source.replace(
        marker,
        marker + f'        "{SELECTED_PAPER_LIBRARY_PREFIX}/",\n',
        1,
    )
    semantic_marker = "    _validate_literature_outputs(package_root)\n"
    source = source.replace(
        semantic_marker,
        semantic_marker + "    _validate_selected_paper_artifacts(package_root)\n",
        1,
    )
    function_marker = "\ndef _progress_v2_identity("
    source = source.replace(function_marker, _SELECTED_LIBRARY_VALIDATOR + function_marker, 1)
    return source.encode("utf-8")


def _replace_spec(files: dict[str, FileSpec], path: str, content: bytes) -> None:
    current = files[path]
    files[path] = FileSpec(
        content=content,
        media_type=current.media_type,
        role=current.role,
        mutable_by_harness=current.mutable_by_harness,
        state_classification=current.state_classification,
        requirement=current.requirement,
    )


def _literature_files(
    *, project_id: str, project_name: str, package_id: str,
    package_checksum: str, research_topic: str,
) -> dict[str, FileSpec]:
    files = dict(render_legacy_literature_files(
        project_id=project_id,
        project_name=project_name,
        package_id=package_id,
        package_checksum=package_checksum,
        research_topic=research_topic,
    ))
    workflow = literature_search_workflow_document()
    workflow_checksum = canonical_hash(workflow)
    _replace_spec(files, "workflow/workflow.json", _json(workflow))

    control = json.loads(files["memory/round-control.json"].content)
    control["workflow_version"] = LITERATURE_SEARCH_WORKFLOW_VERSION
    control["workflow_checksum"] = workflow_checksum
    _replace_spec(files, "memory/round-control.json", _json(control))

    context_text = files["memory/context.md"].content.decode("utf-8")
    payload = json.loads(context_text.split("```json\n", 1)[1].split("\n```", 1)[0])
    payload["workflow_version"] = LITERATURE_SEARCH_WORKFLOW_VERSION
    payload["context_checksum"] = canonical_hash({**payload, "context_checksum": None})
    _replace_spec(
        files,
        "memory/context.md",
        ("# Local Task Context\n\n```json\n" + canonical_json(payload) + "\n```\n").encode(),
    )

    skill_contract = json.loads(files["workflow/skills/literature-search/skill.json"].content)
    skill_contract["semantic_version"] = LITERATURE_SEARCH_SKILL_VERSION
    skill_contract["output_contract"].append(
        f"{SELECTED_PAPER_LIBRARY_PREFIX}/sha256-<content-sha256>.json"
    )
    _replace_spec(files, "workflow/skills/literature-search/skill.json", _json(skill_contract))
    _replace_spec(
        files,
        "workflow/skills/literature-search/SKILL.md",
        files["workflow/skills/literature-search/SKILL.md"].content
        + b"\n## Production Artifact\n\nAfter explicit `finish`, validate both v0.2 JSON sources and publish the reviewed content-addressed selected-paper-library/v1 file. Never publish candidates or an unconfirmed selection.\n",
    )
    _replace_spec(
        files,
        "workflow/prompts/one-round.md",
        files["workflow/prompts/one-round.md"].content
        + b"\nThe final checkpoint also creates selected-paper-library/v1 from the exact validated candidate and selection records. This happens only after the owner types `finish`.\n",
    )
    _replace_spec(
        files,
        "AGENT.md",
        files["AGENT.md"].content
        + b"\n## Reusable literature Artifact\n\nOnly explicit successful `finish` may publish selected-paper-library/v1. The content-addressed Artifact is immutable and Cloud receives metadata, not its bytes.\n",
    )
    _replace_spec(files, "reagent_local.py", _production_runner_source())
    _replace_spec(files, "validate_package.py", _production_validator_source())
    _replace_spec(files, "progress_report.py", _production_progress_source())
    files["legacy_reagent_local.py"] = FileSpec(
        Path(__file__).with_name("local_runner.py").read_bytes(),
        "text/x-python", "reviewed 0.5 launcher core", False, "INSTRUCTION",
    )
    files["legacy_progress_report.py"] = FileSpec(
        Path(__file__).with_name("package_progress.py").read_bytes(),
        "text/x-python", "reviewed Progress v0.2 core", False, "INSTRUCTION",
    )
    files["workflow/artifacts/selected-paper-library.json"] = FileSpec(
        _json({
            "schema_version": "reagent.artifact-output-contract/v0.1",
            **selected_paper_library_output_contract(),
            "validity_point": "EXPLICIT_FINISH_AFTER_FINAL_VALIDATION",
            "source_schemas": ["candidate-papers/v0.2", "selected-papers/v0.2"],
            "ordering": "VALIDATED_SELECTED_ORDER",
            "duplicate_policy": "REJECT",
        }),
        "application/json", "reviewed production Artifact contract", False, "CONFIGURATION",
    )
    files["workflow/schemas/selected-paper-library.schema.json"] = FileSpec(
        _json(_selected_library_schema()),
        "application/schema+json", "selected paper Artifact schema", False, "SCHEMA",
    )
    return files


def _idea_files(
    *, project_id: str, project_name: str, package_id: str,
    package_checksum: str, research_topic: str,
) -> dict[str, FileSpec]:
    del research_topic
    workflow = idea_discovery_workflow_document()
    workflow_checksum = canonical_hash(workflow)
    prompt = """# Reviewed Idea Discovery method\n\nUse only the materialized selected-paper-library/v1 input. Group and compare the supplied literature, clearly separate evidence from inference, identify potential gaps or tensions, and discuss candidate directions with the user before selection. Preserve candidate_id references. Never claim global novelty: every direction requires further validation. Write only this Capsule's outputs and memory.\n"""
    skill = """# Evidence-grounded ideation\n\nUse the supplied paper records as bounded evidence. Attribute observations with candidate IDs, label inference, involve the user in shortlist decisions, and describe novelty only as a hypothesis requiring further validation.\n"""
    agent = """# ReAgent Idea Discovery\n\nThis Capsule is the authoritative local state for one Idea Discovery Workflow Instance.\n\n1. Run only after Workspace preflight has verified the Installed Lock and materialization receipt.\n2. Read `workflow/prompts/idea-discovery.md`, then the materialized `inputs/selected-paper-library.json`.\n3. Treat `inputs/` as read-only. Never read a sibling Literature Search Capsule directly.\n4. Keep evidence, inference, potential gap, and candidate direction distinct. Do not claim global novelty.\n5. Discuss key direction and shortlist decisions with the user.\n6. Write only `outputs/candidate_ideas.json`, `outputs/idea_discovery_report.md`, and this Capsule's `memory/`.\n7. Before ending each round, update `memory/context.md`, the Progress draft, and upload Progress through `reagent_local.py`.\n8. Do not access credentials, run a cloud LLM, or invoke unapproved external research.\n"""
    context_payload = {
        "schema_version": "idea-discovery-context/v0.1",
        "package_id": package_id,
        "package_checksum": package_checksum,
        "workflow_id": IDEA_DISCOVERY_WORKFLOW_ID,
        "workflow_version": IDEA_DISCOVERY_WORKFLOW_VERSION,
        "current_stage": "INPUT_REVIEW",
        "evidence_observations": [],
        "user_decisions": [],
        "excluded_directions": [],
        "candidate_directions": [],
        "unresolved_questions": [],
        "next_action": "Review the materialized literature with the user",
        "latest_progress_report": None,
        "updated_at": DETERMINISTIC_GENERATED_AT,
    }
    context_payload["context_checksum"] = canonical_hash(
        {**context_payload, "context_checksum": None}
    )
    context = (
        "# Idea Discovery Context\n\n```json\n"
        + canonical_json(context_payload)
        + "\n```\n"
    )
    draft = {
        "execution_round": 1,
        "harness_type": "codex",
        "harness_version": None,
        "harness_session_id": "idea-discovery-round-1",
        "previous_report_id": None,
        "previous_report_checksum": None,
        "started_at": DETERMINISTIC_GENERATED_AT,
        "completed_at": DETERMINISTIC_GENERATED_AT,
        "status": "IN_PROGRESS",
        "completed_work": [],
        "current_state": "INPUT_REVIEW",
        "next_recommended_action": "Review the materialized literature with the user",
        "continuation_reason": None,
        "warnings": [],
        "errors": [],
        "unresolved_questions": [],
        "continuation_instructions": ["Read AGENT.md and memory/context.md"],
    }
    project = {
        "schema_version": "local-project-input/v0.1",
        "project_id": project_id,
        "project_name": project_name,
        "selected_workflow": "IDEA_DISCOVERY",
    }
    from . import idea_runtime, idea_validator
    return {
        "AGENT.md": FileSpec(agent.encode(), "text/markdown", "canonical Idea Discovery instructions", False, "INSTRUCTION"),
        "AGENTS.md": FileSpec(b"# Codex shim\n\nRead and follow `AGENT.md`.\n", "text/markdown", "Codex shim", False, "INSTRUCTION"),
        "CLAUDE.md": FileSpec(b"# Claude Code shim\n\nRead and follow `AGENT.md`.\n", "text/markdown", "Claude shim", False, "INSTRUCTION"),
        "README.md": FileSpec(b"# Idea Discovery Capsule\n\nRun through the Workspace `reagent_local.py run` command after explicit materialization.\n", "text/markdown", "Capsule overview", False, "INSTRUCTION"),
        "reagent_local.py": FileSpec(Path(idea_runtime.__file__).read_bytes(), "text/x-python", "interactive local runner", False, "INSTRUCTION"),
        "validate_package.py": FileSpec(Path(idea_validator.__file__).read_bytes(), "text/x-python", "self-contained validator", False, "INSTRUCTION"),
        "progress_report.py": FileSpec(Path(__file__).with_name("package_progress.py").read_bytes(), "text/x-python", "Progress v0.2 helper", False, "INSTRUCTION"),
        "workflow/AGENT.md": FileSpec(b"# Idea Discovery Workflow\n\nUse the reviewed prompt interactively; the local Harness owns execution.\n", "text/markdown", "workflow instructions", False, "INSTRUCTION"),
        "workflow/workflow.json": FileSpec(_json(workflow), "application/json", "pinned Workflow", False, "CONFIGURATION"),
        "workflow/prompts/idea-discovery.md": FileSpec(prompt.encode(), "text/markdown", "reviewed interactive method", False, "INSTRUCTION"),
        "workflow/skills/evidence-grounded-ideation/SKILL.md": FileSpec(skill.encode(), "text/markdown", "reviewed evidence discipline", False, "INSTRUCTION"),
        "workflow/skills/evidence-grounded-ideation/skill.json": FileSpec(_json({
            "schema_version": "local-skill/v0.1",
            "name": "reagent.evidence-grounded-ideation",
            "version": IDEA_DISCOVERY_SKILL_VERSION,
            "trust": "BUILT_IN_REVIEWED_ONLY",
            "required_capabilities": [
                "read_materialized_input", "write_declared_outputs",
                "append_progress_report",
            ],
        }), "application/json", "reviewed Skill contract", False, "CONFIGURATION"),
        "workflow/artifact-inputs.json": FileSpec(_json({
            "schema_version": "reagent.artifact-input-contract/v0.1",
            "requirements": workflow["input_requirements"],
        }), "application/json", "typed Artifact input requirement", False, "CONFIGURATION"),
        "workflow/schemas/candidate-ideas.schema.json": FileSpec(_json(_candidate_ideas_schema()), "application/schema+json", "candidate idea schema", False, "SCHEMA"),
        "inputs/project.json": FileSpec(_json(project), "application/json", "immutable Project identity", False, "INPUT"),
        "outputs/README.md": FileSpec(b"# Idea Discovery outputs\n\nCandidate directions are not proof of global novelty.\n", "text/markdown", "output policy", False, "OUTPUT"),
        "memory/context.md": FileSpec(context.encode(), "text/markdown", "cross-session local context", True, "STATE"),
        "memory/progress/report-draft.json": FileSpec(_json(draft), "application/json", "mutable Progress draft", True, "STATE"),
        "memory/progress/reports/README.md": FileSpec(b"# Append-only Progress Reports\n", "text/markdown", "Progress policy", False, "STATE"),
        "memory/progress/receipts/README.md": FileSpec(b"# Verified upload receipts\n", "text/markdown", "receipt policy", False, "STATE"),
    }


def _selected_library_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:reagent:selected-paper-library:v1",
        "type": "object",
        "additionalProperties": False,
        "required": ["schema", "source_schemas", "source_checksums", "papers"],
        "properties": {
            "schema": {"const": SELECTED_PAPER_LIBRARY_SCHEMA},
            "source_schemas": {"type": "object"},
            "source_checksums": {"type": "object"},
            "papers": {"type": "array", "maxItems": 15},
        },
    }


def _candidate_ideas_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:reagent:candidate-ideas:v0.1",
        "type": "object",
        "additionalProperties": False,
        "required": ["schema", "source_artifact", "ideas"],
        "properties": {
            "schema": {"const": "candidate-ideas/v0.1"},
            "source_artifact": {"type": "object"},
            "ideas": {"type": "array", "maxItems": 100},
        },
    }


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


def _normalized_entries(entries: tuple[PackageFileEntry, ...]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for entry in entries:
        item = entry.to_dict()
        if entry.mutable_by_harness:
            item["sha256"] = None
            item["byte_size"] = None
        values.append(item)
    return values


def _make_manifest(
    *, files: dict[str, FileSpec], project_id: str, package_id: str,
    workflow_type: str, workflow_id: str, workflow_version: str,
    template_id: str, template_version: str,
) -> WorkflowPackageManifest:
    entries = tuple(_entry(path, files[path]) for path in sorted(files))
    workflow = json.loads(files["workflow/workflow.json"].content)
    workflow_checksum = canonical_hash(workflow)
    if workflow_id == LITERATURE_SEARCH_WORKFLOW_ID:
        skill_path = "workflow/skills/literature-search/SKILL.md"
        skill_contract_path = "workflow/skills/literature-search/skill.json"
        skills = (SkillPin(
            name="reagent.local-literature-search",
            semantic_version=LITERATURE_SEARCH_SKILL_VERSION,
            source_type="BUNDLED_REAGENT_ORIGINAL",
            source_identity="reagent-r1a-local-literature-search",
            checksum=canonical_hash({
                "instructions": sha256_bytes(files[skill_path].content),
                "contract": sha256_bytes(files[skill_contract_path].content),
            }),
            relative_path=skill_path,
            required_capabilities=(
                "read_local_package", "write_declared_outputs", "update_local_context",
                "append_progress_report", "paper.search/v0.1", "progress.upload/v0.2",
            ),
        ),)
        prompt_path = "workflow/prompts/one-round.md"
        prompt_id = "literature-search-one-round"
        prompt_version = LITERATURE_SEARCH_PROMPT_VERSION
        outputs = (
            PackageOutputContract("outputs/search_plan.md", "SEARCH_PLAN", "text/markdown", "search-plan/v0.2", "Codex Agent Harness", "reviewed headings"),
            PackageOutputContract("outputs/candidate_papers.json", "CANDIDATE_LIBRARY", "application/json", "candidate-papers/v0.2", "Codex Agent Harness", "exact validated records"),
            PackageOutputContract("outputs/selected_papers.json", "SELECTED_PAPER_LIBRARY", "application/json", "selected-papers/v0.2", "Codex Agent Harness", "exact decisions"),
            PackageOutputContract("outputs/literature_search_report.md", "LITERATURE_SEARCH_REPORT", "text/markdown", "literature-search-report/v0.2", "Codex Agent Harness", "evidence limits"),
        )
        inputs = (
            PackageInputManifest("local-project-display", "inputs/project.json", sha256_bytes(files["inputs/project.json"].content), True, "application/json", "CLOUD_SUPPLIED"),
            PackageInputManifest("owner-research-request", "inputs/research_request.json", sha256_bytes(files["inputs/research_request.json"].content), True, "application/json", "OWNER_SUPPLIED"),
        )
        continuation = "ONE ROUND; explicit finish publishes selected-paper-library/v1; upload-only retry remains idempotent"
        proxy = "SHORT_LIVED EXACT-PACKAGE LOCAL SESSION; OPENALEX ONLY; NO CREDENTIAL IN PACKAGE"
    else:
        skill_path = "workflow/skills/evidence-grounded-ideation/SKILL.md"
        skill_contract_path = "workflow/skills/evidence-grounded-ideation/skill.json"
        skills = (SkillPin(
            name="reagent.evidence-grounded-ideation",
            semantic_version=IDEA_DISCOVERY_SKILL_VERSION,
            source_type="BUNDLED_REAGENT_ORIGINAL",
            source_identity="reagent-b7-evidence-grounded-ideation",
            checksum=canonical_hash({
                "instructions": sha256_bytes(files[skill_path].content),
                "contract": sha256_bytes(files[skill_contract_path].content),
            }),
            relative_path=skill_path,
            required_capabilities=(
                "read_materialized_input", "write_declared_outputs",
                "update_local_context", "append_progress_report",
            ),
        ),)
        prompt_path = "workflow/prompts/idea-discovery.md"
        prompt_id = IDEA_DISCOVERY_PROMPT_ID
        prompt_version = IDEA_DISCOVERY_PROMPT_VERSION
        outputs = (
            PackageOutputContract("outputs/candidate_ideas.json", "CANDIDATE_IDEAS", "application/json", "candidate-ideas/v0.1", "Codex Agent Harness", "candidate IDs must resolve to materialized literature"),
            PackageOutputContract("outputs/idea_discovery_report.md", "IDEA_DISCOVERY_REPORT", "text/markdown", "idea-discovery-report/v0.1", "Codex Agent Harness", "evidence/inference/novelty boundary"),
        )
        inputs = (
            PackageInputManifest("local-project-display", "inputs/project.json", sha256_bytes(files["inputs/project.json"].content), True, "application/json", "CLOUD_SUPPLIED"),
        )
        continuation = "MULTI ROUND; append Progress every session; local files, not chat history, preserve continuity"
        proxy = "NO PROVIDER CAPABILITY; LOCAL INTERACTIVE HARNESS ONLY"
    prompts = (PromptPin(
        prompt_id=prompt_id,
        version=prompt_version,
        checksum=sha256_bytes(files[prompt_path].content),
        relative_path=prompt_path,
        purpose=f"Drive reviewed local {workflow_type} interaction.",
    ),)
    file_manifest_checksum = canonical_hash(_normalized_entries(entries))
    base = WorkflowPackageManifest(
        package_id=package_id,
        package_schema_version=PACKAGE_SCHEMA_VERSION,
        experimental_project_identity=project_id,
        workflow_type=workflow_type,
        workflow_id=workflow_id,
        workflow_version=workflow_version,
        workflow_checksum=workflow_checksum,
        package_template_id=template_id,
        package_template_version=template_version,
        skill_pins=skills,
        prompt_pins=prompts,
        input_manifest=inputs,
        output_contracts=outputs,
        required_harness_capabilities=(
            "read_and_write_local_files", "run_local_python_validator",
            "calculate_sha256", "follow_AGENT_md", "launch_codex_cli",
            "progress.upload/v0.2",
        ),
        content_scope_declaration="OWNER-SCOPED LOCAL RESEARCH STATE; NO SECRET; NO CLOUD ARTIFACT BYTES",
        generated_at=DETERMINISTIC_GENERATED_AT,
        generator_version=f"reagent-{workflow_id}-compiler/{template_version}",
        files=entries,
        file_manifest_checksum=file_manifest_checksum,
        manifest_checksum=_ZERO_HASH,
        package_checksum=_ZERO_HASH,
        continuation_policy=continuation,
        proxy_capability_declaration=proxy,
        experimental_status_declaration=EXPERIMENTAL_STATUS,
        harness_acceptance_status=CURRENT_HARNESS_ACCEPTANCE_STATUS,
        progress_report_schema_version=CURRENT_PROGRESS_SCHEMA_VERSION,
        progress_upload_status=PROGRESS_UPLOAD_STATUS,
    )
    payload = base.to_dict()
    payload["manifest_checksum"] = None
    payload["package_checksum"] = None
    payload["files"] = _normalized_entries(entries)
    manifest_checksum = canonical_hash(payload)
    package_checksum = canonical_hash({
        "package_id": package_id,
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "file_manifest_checksum": file_manifest_checksum,
        "manifest_checksum": manifest_checksum,
    })
    return WorkflowPackageManifest(**{
        **base.to_dict(),
        "skill_pins": skills,
        "prompt_pins": prompts,
        "input_manifest": inputs,
        "output_contracts": outputs,
        "files": entries,
        "required_harness_capabilities": base.required_harness_capabilities,
        "manifest_checksum": manifest_checksum,
        "package_checksum": package_checksum,
    })


def _render_two_pass(
    renderer: Callable[..., dict[str, FileSpec]], *, project_id: str,
    project_name: str, package_id: str, research_topic: str,
    workflow_type: str, workflow_id: str, workflow_version: str,
    template_id: str, template_version: str,
) -> tuple[dict[str, FileSpec], WorkflowPackageManifest]:
    kwargs = dict(
        project_id=project_id, project_name=project_name, package_id=package_id,
        research_topic=research_topic,
    )
    first = renderer(package_checksum=_ZERO_HASH, **kwargs)
    preliminary = _make_manifest(
        files=first, project_id=project_id, package_id=package_id,
        workflow_type=workflow_type, workflow_id=workflow_id,
        workflow_version=workflow_version, template_id=template_id,
        template_version=template_version,
    )
    files = renderer(package_checksum=preliminary.package_checksum, **kwargs)
    manifest = _make_manifest(
        files=files, project_id=project_id, package_id=package_id,
        workflow_type=workflow_type, workflow_id=workflow_id,
        workflow_version=workflow_version, template_id=template_id,
        template_version=template_version,
    )
    if manifest.package_checksum != preliminary.package_checksum:
        raise RuntimeError("mutable state affected deterministic Capsule identity")
    return files, manifest


def _validate_with_bundled(root: Path, *, pristine: bool) -> ValidationResult:
    namespace = runpy.run_path(str(root / "validate_package.py"))
    result = namespace["validate"](root, pristine=pristine)
    return ValidationResult(**result)


def _validate_archive_with_bundled(archive: Path) -> ValidationResult:
    with zipfile.ZipFile(archive, "r") as bundle:
        names: set[str] = set()
        total = 0
        for info in bundle.infolist():
            name = require_relative_path(info.filename.rstrip("/"))
            if not name:
                continue
            if name in names:
                raise ValueError("duplicate archive member")
            names.add(name)
            total += info.file_size
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode) or total > 536_870_912:
                raise ValueError("unsafe Capsule archive")
        with tempfile.TemporaryDirectory(prefix="reagent-b7-archive-") as temporary:
            root = Path(temporary)
            bundle.extractall(root)
            return _validate_with_bundled(root, pristine=True)


def _write_zip(root: Path, destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as bundle:
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            relative = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(relative, date_time=_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.flag_bits |= 0x800
            bundle.writestr(info, path.read_bytes())


def _build(
    *, renderer: Callable[..., dict[str, FileSpec]], project_id: str,
    project_name: str, research_topic: str, output_root: str | Path,
    package_id: str, workflow_type: str, workflow_id: str,
    workflow_version: str, template_id: str, template_version: str,
) -> BuildResult:
    output = Path(output_root)
    if output.is_symlink():
        raise ValueError("output root must not be a symbolic link")
    output.mkdir(parents=True, exist_ok=True)
    files, manifest = _render_two_pass(
        renderer, project_id=project_id, project_name=project_name,
        package_id=package_id, research_topic=research_topic,
        workflow_type=workflow_type, workflow_id=workflow_id,
        workflow_version=workflow_version, template_id=template_id,
        template_version=template_version,
    )
    package_root = output / "package"
    with tempfile.TemporaryDirectory(prefix=".reagent-b7-build-", dir=output) as temporary:
        staged = Path(temporary) / "package"
        staged.mkdir()
        for relative, spec in sorted(files.items()):
            target = staged.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(spec.content)
        (staged / "package-manifest.json").write_text(
            canonical_json(manifest) + "\n", encoding="utf-8"
        )
        validation = _validate_with_bundled(staged, pristine=True)
        if package_root.exists():
            existing = {
                path.relative_to(package_root).as_posix(): path.read_bytes()
                for path in package_root.rglob("*") if path.is_file()
            }
            candidate = {
                path.relative_to(staged).as_posix(): path.read_bytes()
                for path in staged.rglob("*") if path.is_file()
            }
            if package_root.is_symlink() or existing != candidate:
                raise FileExistsError("existing deterministic Capsule differs")
        else:
            os.replace(staged, package_root)
    archive = output / f"{package_id}.zip"
    with tempfile.NamedTemporaryFile(prefix=".reagent-b7-", suffix=".zip", dir=output, delete=False) as handle:
        temporary_archive = Path(handle.name)
    try:
        _write_zip(package_root, temporary_archive)
        content = temporary_archive.read_bytes()
        if archive.exists():
            if archive.is_symlink() or archive.read_bytes() != content:
                raise FileExistsError("existing deterministic archive differs")
        else:
            os.replace(temporary_archive, archive)
        archive_validation = _validate_archive_with_bundled(archive)
    finally:
        temporary_archive.unlink(missing_ok=True)
    package_size = sum(path.stat().st_size for path in package_root.rglob("*") if path.is_file())
    return BuildResult(
        package_id=package_id,
        package_schema_version=PACKAGE_SCHEMA_VERSION,
        package_root=package_root,
        archive_path=archive,
        manifest_checksum=manifest.manifest_checksum,
        package_checksum=manifest.package_checksum,
        zip_checksum=sha256_bytes(archive.read_bytes()),
        file_count=validation.declared_file_count + 1,
        package_size_bytes=package_size,
        validation=validation,
        archive_validation=archive_validation,
        harness_acceptance_status=CURRENT_HARNESS_ACCEPTANCE_STATUS,
    )


def build_literature_search_v0_6_package(
    *, project_id: str, project_name: str, research_topic: str,
    output_root: str | Path, package_id: str,
) -> BuildResult:
    return _build(
        renderer=_literature_files,
        project_id=project_id, project_name=project_name,
        research_topic=research_topic, output_root=output_root,
        package_id=package_id, workflow_type="Literature Search",
        workflow_id=LITERATURE_SEARCH_WORKFLOW_ID,
        workflow_version=LITERATURE_SEARCH_WORKFLOW_VERSION,
        template_id=LITERATURE_SEARCH_TEMPLATE_ID,
        template_version=LITERATURE_SEARCH_CAPSULE_VERSION,
    )


def build_idea_discovery_package(
    *, project_id: str, project_name: str, research_topic: str,
    output_root: str | Path, package_id: str,
) -> BuildResult:
    return _build(
        renderer=_idea_files,
        project_id=project_id, project_name=project_name,
        research_topic=research_topic, output_root=output_root,
        package_id=package_id, workflow_type="Idea Discovery",
        workflow_id=IDEA_DISCOVERY_WORKFLOW_ID,
        workflow_version=IDEA_DISCOVERY_WORKFLOW_VERSION,
        template_id=IDEA_DISCOVERY_TEMPLATE_ID,
        template_version=IDEA_DISCOVERY_CAPSULE_VERSION,
    )


_SELECTED_LIBRARY_HELPER = r'''

def _build_selected_paper_library(root: Path) -> dict[str, Any]:
    validator = runpy.run_path(str(root / "validate_package.py"))
    try:
        validator["_validate_literature_outputs"](root)
    except Exception as error:
        raise ProgressReportError(f"final Literature Search validation failed: {error}") from error
    candidates_path = root / "outputs/candidate_papers.json"
    selected_path = root / "outputs/selected_papers.json"
    for path, label in ((candidates_path, "candidate library"), (selected_path, "selection library")):
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
            raise ProgressReportError(f"{label} must be one regular unlinked file")
    candidate_bytes = candidates_path.read_bytes()
    selected_bytes = selected_path.read_bytes()
    candidates = _load_object(candidates_path, "candidate library")
    selected = _load_object(selected_path, "selection library")
    if set(candidates) != {"schema_version", "mode", "candidates"} or candidates["schema_version"] != "candidate-papers/v0.2":
        raise ProgressReportError("candidate-papers/v0.2 validation failed")
    candidate_records = candidates["candidates"]
    if not isinstance(candidate_records, list):
        raise ProgressReportError("candidate records must be an array")
    by_id: dict[str, dict[str, Any]] = {}
    required_candidate = {
        "candidate_id", "provider_id", "openalex_id", "title", "authors",
        "publication_year", "doi", "source", "language", "abstract",
        "source_query_ids", "provenance_checksum", "deduplication_status",
    }
    for record in candidate_records:
        if not isinstance(record, dict) or set(record) != required_candidate:
            raise ProgressReportError("candidate record fields mismatch")
        candidate_id = record.get("candidate_id")
        if not isinstance(candidate_id, str) or candidate_id in by_id:
            raise ProgressReportError("candidate identity is missing or duplicated")
        if not isinstance(record.get("provider_id"), str) or not record["provider_id"].strip():
            raise ProgressReportError("candidate stable provider identity is required")
        if candidates.get("mode") == "NORMAL" and (
            not isinstance(record.get("openalex_id"), str) or not record["openalex_id"].strip()
        ):
            raise ProgressReportError("normal candidate requires an OpenAlex identity")
        by_id[candidate_id] = record
    if set(selected) != {"schema_version", "mode", "selection_status", "selected", "exclusions", "exclusion_summary"} or selected["schema_version"] != "selected-papers/v0.2":
        raise ProgressReportError("selected-papers/v0.2 validation failed")
    selected_records = selected["selected"]
    if not isinstance(selected_records, list):
        raise ProgressReportError("selected records must be an array")
    papers: list[dict[str, Any]] = []
    seen: set[str] = set()
    required_selection = {"candidate_id", "relevance_decision", "inclusion_reason", "evidence_availability"}
    for selection in selected_records:
        if not isinstance(selection, dict) or set(selection) != required_selection:
            raise ProgressReportError("selection record fields mismatch")
        candidate_id = selection.get("candidate_id")
        if candidate_id in seen or candidate_id not in by_id:
            raise ProgressReportError("selection-to-candidate join is not exactly one")
        seen.add(candidate_id)
        papers.append({"candidate_id": candidate_id, "paper": by_id[candidate_id], "selection": selection})
    artifact = {
        "schema": "selected-paper-library/v1",
        "source_schemas": {"candidate_papers": "candidate-papers/v0.2", "selected_papers": "selected-papers/v0.2"},
        "source_checksums": {
            "candidate_papers_sha256": sha256_bytes(candidate_bytes),
            "selected_papers_sha256": sha256_bytes(selected_bytes),
        },
        "papers": papers,
    }
    content = canonical_json(artifact).encode("utf-8")
    checksum = sha256_bytes(content)
    relative = "outputs/artifacts/selected-paper-library/sha256-" + checksum[7:] + ".json"
    target = root.joinpath(*relative.split("/"))
    current = root
    for part in ("outputs", "artifacts", "selected-paper-library"):
        current = current / part
        if current.exists() or current.is_symlink():
            if current.is_symlink() or not current.is_dir():
                raise ProgressReportError("selected paper Artifact parent is unsafe")
        else:
            current.mkdir()
    current = target.parent
    while current != root:
        if current.is_symlink() or not current.is_dir():
            raise ProgressReportError("selected paper Artifact parent is unsafe")
        current = current.parent
    try:
        target.parent.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise ProgressReportError("selected paper Artifact path escaped the Capsule") from error
    if target.exists():
        if target.is_symlink() or not target.is_file() or target.stat().st_nlink != 1 or target.read_bytes() != content:
            raise ProgressReportError("content-addressed Artifact target conflicts")
    else:
        with tempfile.NamedTemporaryFile(prefix=".selected-paper-library.", dir=target.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.replace(temporary, target)
            directory = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)
    if target.read_bytes() != content or sha256_bytes(target.read_bytes()) != checksum:
        raise ProgressReportError("published selected paper Artifact failed reread verification")
    return {"relative_path": relative, "artifact_kind": "selected-paper-library/v1", "media_type": "application/json", "checksum": checksum, "size": len(content)}
'''


_LITERATURE_RUNNER_WRAPPER = r'''#!/usr/bin/env python3
from __future__ import annotations
import runpy
import uuid
from pathlib import Path

_NAMESPACE = uuid.UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966")
_namespace = runpy.run_path(str(Path(__file__).with_name("legacy_reagent_local.py")))
_original_upload_envelope = _namespace["_upload_envelope"]

def _upload_envelope(*, root, manifest, report_path):
    payload = _original_upload_envelope(root=root, manifest=manifest, report_path=report_path)
    report = _namespace["_load_object"](report_path, "Progress Report")
    declarations = []
    for output in report["output_artifacts"]:
        if output["artifact_kind"] != "selected-paper-library/v1":
            continue
        value = uuid.uuid5(_NAMESPACE, "production-artifact/v1|package=" + manifest["package_id"] + "|report=" + report["report_id"] + "|path=" + output["relative_path"] + "|checksum=" + output["checksum"])
        declarations.append({
            "artifact_id": "artifact-" + value.hex,
            "artifact_type": "selected-paper-library/v1",
            "artifact_schema_version": "selected-paper-library/v1",
            "media_type": output["media_type"],
            "relative_path": output["relative_path"],
            "content_checksum": output["checksum"],
            "size_bytes": output["size"],
            "produced_at": report["completed_at"],
        })
    payload["artifact_declarations"] = declarations
    payload["envelope_checksum"] = None
    payload["envelope_checksum"] = _namespace["canonical_hash"]({key: value for key, value in payload.items() if key != "artifact_declarations"})
    return payload

_namespace["_upload_envelope"] = _upload_envelope

if __name__ == "__main__":
    raise SystemExit(_namespace["main"]())
'''


_SELECTED_LIBRARY_VALIDATOR = r'''

def _validate_selected_paper_artifacts(package_root: Path) -> None:
    root = package_root / "outputs/artifacts/selected-paper-library"
    if not root.exists():
        return
    if root.is_symlink() or not root.is_dir():
        raise PackageValidationError("selected paper Artifact root is unsafe")
    candidates = _read_json_if_present(package_root / "outputs/candidate_papers.json", "candidate library")
    selected = _read_json_if_present(package_root / "outputs/selected_papers.json", "selected library")
    if candidates is None or selected is None:
        raise PackageValidationError("production Artifact requires final Literature Search outputs")
    by_id = {item["candidate_id"]: item for item in candidates["candidates"]}
    expected_papers = []
    seen = set()
    for selection in selected["selected"]:
        candidate_id = selection["candidate_id"]
        if candidate_id in seen or candidate_id not in by_id:
            raise PackageValidationError("production Artifact join mismatch")
        seen.add(candidate_id)
        expected_papers.append({"candidate_id": candidate_id, "paper": by_id[candidate_id], "selection": selection})
    expected = {
        "schema": "selected-paper-library/v1",
        "source_schemas": {"candidate_papers": "candidate-papers/v0.2", "selected_papers": "selected-papers/v0.2"},
        "source_checksums": {
            "candidate_papers_sha256": sha256_bytes((package_root / "outputs/candidate_papers.json").read_bytes()),
            "selected_papers_sha256": sha256_bytes((package_root / "outputs/selected_papers.json").read_bytes()),
        },
        "papers": expected_papers,
    }
    expected_bytes = canonical_json(expected).encode("utf-8")
    expected_name = "sha256-" + sha256_bytes(expected_bytes)[7:] + ".json"
    paths = sorted(path for path in root.iterdir())
    current_found = False
    for path in paths:
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
            raise PackageValidationError("selected paper Artifact must be a regular unlinked file")
        content = path.read_bytes()
        if path.name != "sha256-" + sha256_bytes(content)[7:] + ".json":
            raise PackageValidationError("selected paper Artifact content address mismatch")
        value = _read_json_if_present(path, "selected paper Artifact")
        if value is None or set(value) != {"schema", "source_schemas", "source_checksums", "papers"}:
            raise PackageValidationError("selected paper Artifact fields mismatch")
        if value["schema"] != "selected-paper-library/v1" or value["source_schemas"] != {
            "candidate_papers": "candidate-papers/v0.2", "selected_papers": "selected-papers/v0.2"
        }:
            raise PackageValidationError("selected paper Artifact schema mismatch")
        checksums = value["source_checksums"]
        if not isinstance(checksums, dict) or set(checksums) != {
            "candidate_papers_sha256", "selected_papers_sha256"
        } or any(not SHA256.fullmatch(str(item)) for item in checksums.values()):
            raise PackageValidationError("selected paper Artifact source checksum mismatch")
        artifact_ids = set()
        if not isinstance(value["papers"], list):
            raise PackageValidationError("selected paper Artifact papers must be an array")
        for item in value["papers"]:
            if not isinstance(item, dict) or set(item) != {"candidate_id", "paper", "selection"}:
                raise PackageValidationError("selected paper Artifact entry mismatch")
            candidate_id = item["candidate_id"]
            if (
                not isinstance(candidate_id, str)
                or candidate_id in artifact_ids
                or not isinstance(item["paper"], dict)
                or item["paper"].get("candidate_id") != candidate_id
                or not isinstance(item["selection"], dict)
                or item["selection"].get("candidate_id") != candidate_id
            ):
                raise PackageValidationError("selected paper Artifact identity mismatch")
            artifact_ids.add(candidate_id)
        if path.name == expected_name and content == expected_bytes:
            current_found = True
    if not current_found:
        raise PackageValidationError("current final outputs have no matching production Artifact")
'''
