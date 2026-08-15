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

# F1A publishes a separate immutable Idea Discovery pin.  The B7 constants
# above intentionally continue to identify the accepted 0.1.0 Capsule.
IDEA_DISCOVERY_V0_2_WORKFLOW_VERSION = "0.2.0"
IDEA_DISCOVERY_V0_2_CAPSULE_VERSION = "0.2.0"
IDEA_DISCOVERY_V0_2_PROMPT_VERSION = "0.2.0"
IDEA_DISCOVERY_V0_2_SKILL_VERSION = "0.2.0"
# Owner-test integration repair: research semantics stay pinned to Workflow 0.2,
# while the immutable Harness integration is published as Capsule 0.3.
IDEA_DISCOVERY_V0_3_CAPSULE_VERSION = "0.3.0"

WRITING_WORKFLOW_ID = "writing-local-experimental"
REVIEW_WORKFLOW_ID = "review-local-experimental"
EXPERIMENT_WORKFLOW_ID = "reproduction-experiment-local-experimental"
SCAFFOLD_WORKFLOW_VERSION = "0.1.0"
SCAFFOLD_CAPSULE_VERSION = "0.1.0"
SCAFFOLD_PROMPT_VERSION = "0.1.0"
SCAFFOLD_SKILL_VERSION = "0.1.0"
SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION = "0.2.0"
SCAFFOLD_SKILL_BACKED_CAPSULE_VERSION = "0.2.0"
SCAFFOLD_SKILL_BACKED_PROMPT_VERSION = "0.2.0"
# Owner-test Harness integration repair: Writing/Review research semantics stay
# pinned to Workflow 0.2, while each receives a new immutable Capsule.
SCAFFOLD_INTERACTIVE_CAPSULE_VERSION = "0.3.0"
# Progress lifecycle repair: the Workflow definition and interactive method are
# unchanged; only new immutable Capsules adopt an Agent-finalized round instead
# of attempting to finalize the same execution twice.
SCAFFOLD_COMPLETION_CAPSULE_VERSION = "0.4.0"
EXPERIMENT_RESOURCE_WORKFLOW_VERSION = "0.3.0"
EXPERIMENT_RESOURCE_CAPSULE_VERSION = "0.3.0"
EXPERIMENT_RESOURCE_PROMPT_VERSION = "0.3.0"
# Owner-test integration repair: Experiment research/resource semantics stay
# pinned to Workflow 0.3, while the interactive Harness bootstrap is a new
# immutable Capsule.
EXPERIMENT_INTERACTIVE_CAPSULE_VERSION = "0.4.0"
EXPERIMENT_COMPLETION_CAPSULE_VERSION = "0.5.0"
REAL_EXPERIMENT_WORKFLOW_VERSION = "0.4.0"
REAL_EXPERIMENT_CAPSULE_VERSION = "0.6.0"
REAL_EXPERIMENT_BUGFIX_CAPSULE_VERSION = "0.7.0"
REAL_EXPERIMENT_PROMPT_VERSION = "0.1.0"
WRITING_TEMPLATE_ID = "writing-scaffold-package-experimental"
REVIEW_TEMPLATE_ID = "review-scaffold-package-experimental"
EXPERIMENT_TEMPLATE_ID = "reproduction-experiment-scaffold-package-experimental"

SELECTED_PAPER_LIBRARY_TYPE = "selected-paper-library/v1"
SELECTED_PAPER_LIBRARY_SCHEMA = "selected-paper-library/v1"
SELECTED_PAPER_LIBRARY_PREFIX = "outputs/artifacts/selected-paper-library"
IDEA_INPUT_TARGET = "inputs/selected-paper-library.json"
SELECTED_RESEARCH_IDEA_TYPE = "selected-research-idea/v1"
SELECTED_RESEARCH_IDEA_SCHEMA = "selected-research-idea/v1"
SELECTED_RESEARCH_IDEA_PREFIX = "outputs/artifacts/selected-research-idea"

MANUSCRIPT_DRAFT_TYPE = "manuscript-draft/v1"
REVIEW_REPORT_TYPE = "review-report/v1"
EXPERIMENT_RECORD_TYPE = "experiment-record/v1"
EXPERIMENT_RECORD_V2_TYPE = "experiment-record/v2"

SCAFFOLD_INPUT_TARGETS = {
    "research_idea": "inputs/selected-research-idea.json",
    "literature_library": "inputs/selected-paper-library.json",
    "experiment_record": "inputs/experiment-record.json",
    "review_feedback": "inputs/review-report.json",
    "prior_manuscript": "inputs/prior-manuscript.json",
    "manuscript": "inputs/manuscript-draft.json",
}

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


def selected_research_idea_output_contract() -> dict[str, str]:
    return {
        "artifact_type": SELECTED_RESEARCH_IDEA_TYPE,
        "artifact_schema_version": SELECTED_RESEARCH_IDEA_SCHEMA,
        "media_type": "application/json",
        "relative_path_prefix": SELECTED_RESEARCH_IDEA_PREFIX,
        "content_addressed_filename": "sha256-<content-sha256>.json",
        "progress_artifact_kind": SELECTED_RESEARCH_IDEA_TYPE,
    }


def scaffold_output_contract(artifact_type: str) -> dict[str, str]:
    slug = artifact_type.split("/", 1)[0]
    return {
        "artifact_type": artifact_type,
        "artifact_schema_version": artifact_type,
        "media_type": "application/json",
        "relative_path_prefix": f"outputs/artifacts/{slug}",
        "content_addressed_filename": "sha256-<content-sha256>.json",
        "progress_artifact_kind": artifact_type,
    }


def _scaffold_requirement(
    key: str, artifact_type: str, *, required: bool
) -> dict[str, Any]:
    return {
        "requirement_key": key,
        "artifact_type": artifact_type,
        "artifact_schema": artifact_type,
        "cardinality": "ONE",
        "required": required,
        "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
        "materialization_mode": "VERIFIED_COPY",
        "target_relative_path": SCAFFOLD_INPUT_TARGETS[key],
    }


WRITING_REQUIREMENTS = (
    _scaffold_requirement("research_idea", SELECTED_RESEARCH_IDEA_TYPE, required=True),
    _scaffold_requirement("literature_library", SELECTED_PAPER_LIBRARY_TYPE, required=True),
    _scaffold_requirement("experiment_record", EXPERIMENT_RECORD_TYPE, required=False),
    _scaffold_requirement("review_feedback", REVIEW_REPORT_TYPE, required=False),
    _scaffold_requirement("prior_manuscript", MANUSCRIPT_DRAFT_TYPE, required=False),
)
REVIEW_REQUIREMENTS = (
    _scaffold_requirement("manuscript", MANUSCRIPT_DRAFT_TYPE, required=True),
    _scaffold_requirement("literature_library", SELECTED_PAPER_LIBRARY_TYPE, required=False),
    _scaffold_requirement("experiment_record", EXPERIMENT_RECORD_TYPE, required=False),
)
EXPERIMENT_REQUIREMENTS = (
    _scaffold_requirement("research_idea", SELECTED_RESEARCH_IDEA_TYPE, required=True),
    _scaffold_requirement("literature_library", SELECTED_PAPER_LIBRARY_TYPE, required=False),
)


def real_experiment_workflow_document() -> dict[str, Any]:
    """Immutable first reviewed Real Experiment Definition contract."""

    return {
        "schema_version": "local-workflow/v0.2",
        "experimental_status": EXPERIMENTAL_STATUS,
        "workflow_type": "Reproduction & Experiment",
        "workflow_id": EXPERIMENT_WORKFLOW_ID,
        "workflow_version": REAL_EXPERIMENT_WORKFLOW_VERSION,
        "execution_owner": "codex-coordinated-local-workspace",
        "hosted_agent_runtime_required": False,
        "network_boundary": "ENFORCED_LOCAL_NO_EGRESS",
        "core_capability_maturity": "REVIEWED_CORE",
        "supported_mode": "IDEA_EXPERIMENT",
        "input_requirements": [
            _scaffold_requirement(
                "research_idea", SELECTED_RESEARCH_IDEA_TYPE, required=True
            )
        ],
        "resource_requirements": [{
            "requirement_key": "source_repository",
            "resource_kind": "SOURCE_REPOSITORY",
            "required": True,
            "cardinality": "ONE",
            "selection_policy": "EXPLICIT_SPECIFIC_RESOURCE",
            "provider": "GITHUB",
            "materialization_mode": "OWNER_STAGED_VERIFIED_COPY",
        }],
        "stages": [
            "INPUT_REVIEW", "EXPERIMENT_REQUIREMENTS", "RESOURCE_READINESS",
            "EXPERIMENT_PLAN", "OWNER_APPROVAL", "PREPARATION",
            "LOCAL_EXECUTION", "EVALUATION", "RESULT_REVIEW", "COMPLETED",
        ],
        "artifact_outputs": [scaffold_output_contract(EXPERIMENT_RECORD_V2_TYPE)],
        "execution_policy": {
            "attempts_per_approval": 1,
            "automatic_retry": False,
            "process_model": "ONE_LOCAL_FOREGROUND_PROCESS",
            "network_policy": "DISABLED",
            "trusted_owner_staged_code_only": True,
            "hostile_code_containment_claimed": False,
        },
        "immutable_versioning": "experiment-record/v1 and prior Capsules remain unchanged",
    }


def real_experiment_contract_checksum() -> str:
    return canonical_hash(real_experiment_workflow_document())


def real_experiment_v0_7_capsule_checksum() -> str:
    return canonical_hash({
        "generator_version": (
            f"reagent-{EXPERIMENT_WORKFLOW_ID}-compiler/"
            f"{REAL_EXPERIMENT_BUGFIX_CAPSULE_VERSION}"
        ),
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "package_template_id": EXPERIMENT_TEMPLATE_ID,
        "package_template_version": REAL_EXPERIMENT_BUGFIX_CAPSULE_VERSION,
        "workflow_checksum": real_experiment_contract_checksum(),
        "artifact_requirements": [{
            "requirement_key": "research_idea",
            "artifact_type": "selected-research-idea/v1",
            "required": True,
        }],
        "artifact_outputs": [scaffold_output_contract(EXPERIMENT_RECORD_V2_TYPE)],
        "resource_requirements": [["source_repository", "SOURCE_REPOSITORY", "GITHUB"]],
        "core_capability_maturity": "REVIEWED_CORE",
        "skill_pins": [{
            "skill_id": "research-artifact-provenance-local-builtin",
            "skill_version": "0.1.0",
            "content_checksum": (
                "sha256:0650f150099823499d1fdcf072abd70275e87cb76e3e9d64dfb12361cc13d7c8"
            ),
        }],
        "execution_boundary": "ONE_APPROVED_LOCAL_NO_EGRESS_ATTEMPT",
    })


REAL_EXPERIMENT_V0_7_CAPSULE_CHECKSUM = real_experiment_v0_7_capsule_checksum()
REAL_EXPERIMENT_V0_7_CAPSULE_ID = (
    "capsule-" + REAL_EXPERIMENT_V0_7_CAPSULE_CHECKSUM[7:39]
)


def scaffold_workflow_document(
    workflow_id: str, *, workflow_version: str = SCAFFOLD_WORKFLOW_VERSION
) -> dict[str, Any]:
    values = {
        WRITING_WORKFLOW_ID: (
            "Writing", WRITING_REQUIREMENTS, MANUSCRIPT_DRAFT_TYPE,
            ("INPUT_REVIEW", "OUTLINE", "SCAFFOLD_DRAFT", "USER_REVIEW", "COMPLETED"),
        ),
        REVIEW_WORKFLOW_ID: (
            "Review", REVIEW_REQUIREMENTS, REVIEW_REPORT_TYPE,
            ("INPUT_REVIEW", "SCAFFOLD_REVIEW", "USER_REVIEW", "COMPLETED"),
        ),
        EXPERIMENT_WORKFLOW_ID: (
            "Reproduction & Experiment", EXPERIMENT_REQUIREMENTS, EXPERIMENT_RECORD_TYPE,
            ("INPUT_REVIEW", "EXPERIMENT_PLAN", "PLACEHOLDER_EXECUTION", "USER_REVIEW", "COMPLETED"),
        ),
    }
    workflow_type, requirements, output_type, stages = values[workflow_id]
    result = {
        "schema_version": "local-workflow/v0.2",
        "experimental_status": EXPERIMENTAL_STATUS,
        "workflow_type": workflow_type,
        "workflow_id": workflow_id,
        "workflow_version": workflow_version,
        "execution_owner": "codex-or-claude-local-agent-harness",
        "hosted_agent_runtime_required": False,
        "network_boundary": "NO_WORKFLOW_NETWORK_REQUIRED",
        "core_capability_maturity": "SCAFFOLD_CORE",
        "scaffold_notice": (
            "Product flow is functional. Research capability is placeholder."
        ),
        "input_requirements": list(requirements),
        "stages": list(stages),
        "artifact_outputs": [scaffold_output_contract(output_type)],
        "completion_semantics": "SCAFFOLD_FLOW_COMPLETED_NOT_RESEARCH_COMPLETED",
        "immutable_replacement_policy": "REVIEWED_CORE_REQUIRES_NEW_VERSION",
    }
    if workflow_id == EXPERIMENT_WORKFLOW_ID:
        result.update({
            "supported_mode": "IDEA_EXPERIMENT",
            "paper_reproduction": "NOT_YET_ENABLED",
            "execution_status": "PLACEHOLDER_NOT_EXECUTED",
            "actual_results": None,
        })
        if workflow_version == EXPERIMENT_RESOURCE_WORKFLOW_VERSION:
            result["resource_requirements"] = [
                {
                    "requirement_key": key,
                    "resource_kind": kind,
                    "required": False,
                    "cardinality": "ONE",
                    "selection_policy": "EXPLICIT_SPECIFIC_RESOURCE",
                }
                for key, kind in (
                    ("source_repository", "SOURCE_REPOSITORY"),
                    ("dataset", "DATASET"),
                    ("model", "MODEL"),
                    ("checkpoint", "CHECKPOINT"),
                )
            ]
            result["resource_execution_policy"] = (
                "VERIFIED_METADATA_ONLY_NO_RESOURCE_EXECUTION"
            )
    return result


def scaffold_contract_checksum(
    workflow_id: str, *, workflow_version: str = SCAFFOLD_WORKFLOW_VERSION
) -> str:
    return canonical_hash(scaffold_workflow_document(
        workflow_id, workflow_version=workflow_version
    ))


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


def idea_discovery_v0_2_workflow_document() -> dict[str, Any]:
    """Reviewed 0.2 contract; the accepted 0.1 document stays byte-stable."""

    value = idea_discovery_workflow_document()
    value["workflow_version"] = IDEA_DISCOVERY_V0_2_WORKFLOW_VERSION
    value["reviewed_skills"] = [{
        **value["reviewed_skills"][0],
        "version": IDEA_DISCOVERY_V0_2_SKILL_VERSION,
    }]
    value["steps"] = [
        "analyze-materialized-literature",
        "develop-candidate-ideas-with-user",
        "require-explicit-user-selection",
        "validate-exactly-one-selected-idea",
        "publish-selected-research-idea-v1-content-addressed-file",
        "append-progress-and-promote-canonical-artifact-metadata",
    ]
    value["artifact_outputs"] = [selected_research_idea_output_contract()]
    value["completion_gate"] = (
        "EXPLICIT_USER_SELECTION_AND_SELECTED_RESEARCH_IDEA_PUBLICATION"
    )
    value["immutable_versioning"] = "0.1.0 remains independently valid"
    return value


def literature_search_contract_checksum() -> str:
    return canonical_hash(literature_search_workflow_document())


def idea_discovery_contract_checksum() -> str:
    return canonical_hash(idea_discovery_workflow_document())


def idea_discovery_v0_2_contract_checksum() -> str:
    return canonical_hash(idea_discovery_v0_2_workflow_document())


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


def _idea_v0_2_progress_source() -> bytes:
    source = Path(__file__).with_name("package_progress.py").read_text(encoding="utf-8")
    source = source.replace(
        "import json\n", "import json\nimport os\nimport runpy\nimport tempfile\n", 1
    )
    marker = "\ndef finalize(\n"
    if marker not in source:
        raise RuntimeError("accepted Progress helper extension point is unavailable")
    source = source.replace(marker, _SELECTED_IDEA_HELPER + marker, 1)
    output_marker = "    skill_pins = [\n"
    if output_marker not in source:
        raise RuntimeError("accepted Progress output extension point is unavailable")
    completion = (
        '    if draft["status"] == "COMPLETED":\n'
        '        if draft["current_state"] != "COMPLETED":\n'
        '            raise ProgressReportError("completed Idea Discovery must use the COMPLETED stage")\n'
        "        outputs.append(_build_selected_research_idea(root))\n"
        '    elif draft["current_state"] == "COMPLETED":\n'
        '        raise ProgressReportError("COMPLETED stage requires completed status and selected Artifact")\n'
    )
    source = source.replace(output_marker, completion + output_marker, 1)
    return source.encode("utf-8")


def _idea_v0_2_runner_source() -> bytes:
    source = Path(__file__).with_name("idea_runtime.py").read_text(encoding="utf-8")
    source = source.replace("import urllib.request\n", "import urllib.request\nimport uuid\n", 1)
    source = source.replace(
        '"client_version": "reagent-local-idea-discovery/0.1.0",',
        '"client_version": "reagent-local-idea-discovery/0.2.0",',
        1,
    )
    payload_marker = "    payload = {\n"
    declaration_source = '''    declarations = []
    namespace = uuid.UUID("85a011a0-88cd-54b9-a649-7ccc9ed2d966")
    for output in report["output_artifacts"]:
        if output["artifact_kind"] != "selected-research-idea/v1":
            continue
        value = uuid.uuid5(
            namespace,
            "production-artifact/v1|package=" + manifest["package_id"]
            + "|report=" + report["report_id"]
            + "|path=" + output["relative_path"]
            + "|checksum=" + output["checksum"],
        )
        declarations.append({
            "artifact_id": "artifact-" + value.hex,
            "artifact_type": "selected-research-idea/v1",
            "artifact_schema_version": "selected-research-idea/v1",
            "media_type": output["media_type"],
            "relative_path": output["relative_path"],
            "content_checksum": output["checksum"],
            "size_bytes": output["size"],
            "produced_at": report["completed_at"],
        })
'''
    if payload_marker not in source:
        raise RuntimeError("accepted Idea runtime payload extension point is unavailable")
    source = source.replace(payload_marker, declaration_source + payload_marker, 1)
    source = source.replace('"artifact_declarations": [],', '"artifact_declarations": declarations,', 1)
    return source.encode("utf-8")


def _idea_v0_3_runner_source() -> bytes:
    """Publish the bounded interactive bootstrap without changing 0.2 bytes."""

    source = _idea_v0_2_runner_source().decode("utf-8")
    source = source.replace("import runpy\n", "import runpy\nimport signal\n", 1)
    source = source.replace(
        '"client_version": "reagent-local-idea-discovery/0.2.0",',
        '"client_version": "reagent-local-idea-discovery/0.3.0",',
        1,
    )
    old = '''def _run_harness(root: Path, executable: str) -> None:
    environment = dict(os.environ)
    for key in (
        "REAGENT_PROXY_TOKEN",
        "REAGENT_LOCAL_SESSION_TOKEN",
        "REAGENT_DATABASE_URL",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        environment.pop(key, None)
    result = subprocess.run([executable], cwd=root, env=environment, check=False)
    if result.returncode != 0:
        raise IdeaDiscoveryError("Codex exited before Idea Discovery finalization")
'''
    new = '''def _initial_instruction() -> str:
    return """REAGENT IDEA DISCOVERY — INPUT_REVIEW

You are beginning the ReAgent Idea Discovery Workflow. Read and follow the root
AGENTS.md and AGENT.md, workflow/AGENT.md, the pinned
workflow/prompts/idea-discovery.md, memory/context.md, and only the exact
materialized Literature Artifact at inputs/selected-paper-library.json.

Begin at INPUT_REVIEW. Before committing to candidate ideas, report the selected
paper count, describe the available metadata and abstracts, state that no full
text was reviewed, summarize the initial bounded literature landscape, and ask
the owner about priorities, constraints, areas of interest, and acceptable scope.
An INSUFFICIENT Literature selection still contains evidence when its selected
paper count is nonzero, but the small evidence base must be stated. Keep evidence,
inference, and validation needed separate; limited retrieval is never proof of
global novelty. Follow the pinned Workflow prompt for the remaining method and
never inspect sibling Capsules or raw Literature Search state."""


def _codex_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for key in (
        "REAGENT_PROXY_TOKEN",
        "REAGENT_LOCAL_SESSION_TOKEN",
        "REAGENT_DATABASE_URL",
        "REAGENT_ENV_FILE",
        "REAGENT_OPENALEX_API_KEY",
        "OPENALEX_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        environment.pop(key, None)
    return environment


def _codex_preflight(executable: str, environment: dict[str, str]) -> None:
    checks = (
        ([executable, "--version"], ()),
        ([executable, "--help"], ("--sandbox", "--ask-for-approval", "--no-alt-screen", "--cd")),
        ([executable, "login", "status"], ()),
    )
    for command, required in checks:
        try:
            result = subprocess.run(
                command, env=environment, capture_output=True, text=True,
                check=False, timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise IdeaDiscoveryError("Codex CLI preflight could not be completed") from error
        if result.returncode != 0 or any(item not in result.stdout for item in required):
            raise IdeaDiscoveryError("Codex CLI does not satisfy the interactive Harness contract")


def _stop_harness(child: subprocess.Popen[Any]) -> None:
    if child.poll() is not None:
        return
    child.send_signal(signal.SIGINT)
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


def _run_harness(root: Path, executable: str) -> None:
    environment = _codex_environment()
    _codex_preflight(executable, environment)
    command = [
        executable,
        "--sandbox", "workspace-write",
        "--ask-for-approval", "on-request",
        "--no-alt-screen",
        "-C", str(root),
        _initial_instruction(),
    ]
    child: subprocess.Popen[Any] | None = None
    previous_handlers: dict[int, Any] = {}

    def terminate_signal(signum: int, frame: Any) -> None:
        raise KeyboardInterrupt

    try:
        for signum in (signal.SIGTERM, signal.SIGHUP):
            previous_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, terminate_signal)
        child = subprocess.Popen(command, cwd=root, env=environment)
        returncode = child.wait()
    except KeyboardInterrupt as error:
        if child is not None:
            _stop_harness(child)
        raise IdeaDiscoveryError(
            "Owner interrupted Idea Discovery; local memory and outputs were retained"
        ) from error
    except OSError as error:
        raise IdeaDiscoveryError("Codex process could not be started") from error
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
    if returncode != 0:
        raise IdeaDiscoveryError("Codex exited before Idea Discovery finalization")
'''
    if old not in source:
        raise RuntimeError("accepted Idea Harness extension point is unavailable")
    source = source.replace(old, new, 1)
    return source.encode("utf-8")


def _idea_v0_2_validator_source() -> bytes:
    source = Path(__file__).with_name("idea_validator.py").read_text(encoding="utf-8")
    source = source.replace(
        '    "memory/progress/receipts/",\n)',
        '    "memory/progress/receipts/",\n'
        f'    "{SELECTED_RESEARCH_IDEA_PREFIX}/",\n)',
        1,
    )
    source = source.replace(
        'manifest.get("workflow_version") != "0.1.0"',
        'manifest.get("workflow_version") != "0.2.0"',
        1,
    )
    source = source.replace(
        'manifest.get("package_template_version") != "0.1.0"',
        'manifest.get("package_template_version") != "0.2.0"',
        1,
    )
    function_marker = "\ndef validate(root: str | Path, *, pristine: bool = False)"
    if function_marker not in source:
        raise RuntimeError("accepted Idea validator extension point is unavailable")
    source = source.replace(
        function_marker, _SELECTED_IDEA_VALIDATOR + function_marker, 1
    )
    return_marker = '    return {\n        "valid": True,\n'
    if return_marker not in source:
        raise RuntimeError("accepted Idea validator return point is unavailable")
    source = source.replace(
        return_marker,
        "    _validate_selected_idea_artifacts(package_root)\n" + return_marker,
        1,
    )
    return source.encode("utf-8")


def _idea_v0_3_validator_source() -> bytes:
    source = _idea_v0_2_validator_source().decode("utf-8")
    old = 'manifest.get("package_template_version") != "0.2.0"'
    if old not in source:
        raise RuntimeError("accepted Idea 0.2 validator pin is unavailable")
    return source.replace(
        old,
        'manifest.get("package_template_version") != "0.3.0"',
        1,
    ).encode("utf-8")


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


def _idea_v0_2_files(
    *, project_id: str, project_name: str, package_id: str,
    package_checksum: str, research_topic: str,
) -> dict[str, FileSpec]:
    """Render 0.2 as a new immutable Capsule without changing 0.1 bytes."""

    files = dict(_idea_files(
        project_id=project_id,
        project_name=project_name,
        package_id=package_id,
        package_checksum=package_checksum,
        research_topic=research_topic,
    ))
    workflow = idea_discovery_v0_2_workflow_document()
    _replace_spec(files, "workflow/workflow.json", _json(workflow))

    context_text = files["memory/context.md"].content.decode("utf-8")
    prefix, remainder = context_text.split("```json\n", 1)
    encoded, suffix = remainder.split("\n```", 1)
    context_payload = json.loads(encoded)
    context_payload["workflow_version"] = IDEA_DISCOVERY_V0_2_WORKFLOW_VERSION
    context_payload["context_checksum"] = canonical_hash(
        {**context_payload, "context_checksum": None}
    )
    _replace_spec(
        files,
        "memory/context.md",
        (
            prefix + "```json\n" + canonical_json(context_payload) + "\n```" + suffix
        ).encode("utf-8"),
    )

    agent = """# ReAgent Idea Discovery\n\nThis Capsule is the authoritative local state for one Idea Discovery Workflow Instance.\n\n1. Run only after Workspace preflight has verified the Installed Lock and materialization receipt.\n2. Read `workflow/prompts/idea-discovery.md`, then the materialized `inputs/selected-paper-library.json`.\n3. Treat `inputs/` as read-only. Never read a sibling Literature Search Capsule directly.\n4. Keep evidence, inference, potential gap, and candidate direction distinct. Do not claim global novelty.\n5. Discuss key direction and shortlist decisions with the user. Never select an idea on the user's behalf.\n6. Only after explicit user confirmation, mark exactly one candidate record `selected`; keep its record fields unchanged.\n7. Write only `outputs/candidate_ideas.json`, `outputs/idea_discovery_report.md`, and this Capsule's `memory/`.\n8. `COMPLETED` is valid only when finalization publishes `selected-research-idea/v1`. Before every exit, update memory and Progress.\n9. Do not access credentials, run a cloud LLM, or invoke unapproved external research.\n"""
    prompt = """# Reviewed Idea Discovery method\n\nUse only the materialized selected-paper-library/v1 input. Group and compare the supplied literature, clearly separate evidence from inference, identify potential gaps or tensions, and discuss candidate directions with the user before selection. Preserve candidate_id references. Never claim global novelty: every direction requires further validation.\n\nCandidate development is not completion. Ask the user to explicitly confirm one research direction. Do not infer confirmation, rank-select, choose the first or latest idea, or silently replace an earlier choice. After explicit confirmation, preserve the exact candidate record and set exactly that record's status to `selected`; all other records must use a non-selected allowed status. Only then may the Progress draft enter `COMPLETED`, which publishes a content-addressed selected-research-idea/v1 Artifact.\n"""
    skill = """# Evidence-grounded ideation\n\nUse the supplied paper records as bounded evidence. Attribute observations with candidate IDs, label inference, involve the user in shortlist decisions, and describe novelty only as a hypothesis requiring further validation. A production selected idea requires one explicit user confirmation and exactly one unchanged candidate record with status `selected`; never auto-select.\n"""
    _replace_spec(files, "AGENT.md", agent.encode("utf-8"))
    _replace_spec(files, "workflow/prompts/idea-discovery.md", prompt.encode("utf-8"))
    _replace_spec(files, "workflow/skills/evidence-grounded-ideation/SKILL.md", skill.encode("utf-8"))
    skill_contract = json.loads(
        files["workflow/skills/evidence-grounded-ideation/skill.json"].content
    )
    skill_contract["version"] = IDEA_DISCOVERY_V0_2_SKILL_VERSION
    skill_contract["required_capabilities"].append("publish_selected_research_idea")
    _replace_spec(
        files,
        "workflow/skills/evidence-grounded-ideation/skill.json",
        _json(skill_contract),
    )
    _replace_spec(files, "reagent_local.py", _idea_v0_2_runner_source())
    _replace_spec(files, "validate_package.py", _idea_v0_2_validator_source())
    _replace_spec(files, "progress_report.py", _idea_v0_2_progress_source())
    _replace_spec(
        files,
        "workflow/AGENT.md",
        b"# Idea Discovery Workflow\n\nUse the reviewed prompt interactively. Completion requires the user's explicit selection and selected-research-idea/v1 publication.\n",
    )
    _replace_spec(
        files,
        "outputs/README.md",
        b"# Idea Discovery outputs\n\nCandidate directions are not proof of global novelty. Completion publishes only the explicitly user-selected direction as selected-research-idea/v1.\n",
    )
    files["workflow/artifact-outputs.json"] = FileSpec(
        _json({
            "schema_version": "reagent.artifact-output-contract/v0.1",
            **selected_research_idea_output_contract(),
            "validity_point": "EXPLICIT_USER_SELECTION_AFTER_IDEA_VALIDATION",
            "source_schema": "candidate-ideas/v0.1",
            "selection_policy": "EXACTLY_ONE_EXPLICITLY_SELECTED",
            "producer_core_capability_maturity": "REVIEWED_CORE",
        }),
        "application/json", "reviewed production Artifact contract", False,
        "CONFIGURATION",
    )
    files["workflow/schemas/selected-research-idea.schema.json"] = FileSpec(
        _json(_selected_research_idea_schema()),
        "application/schema+json", "selected research idea Artifact schema", False,
        "SCHEMA",
    )
    return files


def _idea_v0_3_files(
    *, project_id: str, project_name: str, package_id: str,
    package_checksum: str, research_topic: str,
) -> dict[str, FileSpec]:
    """Render the immutable 0.3 Harness over unchanged Workflow 0.2 assets."""

    files = dict(_idea_v0_2_files(
        project_id=project_id,
        project_name=project_name,
        package_id=package_id,
        package_checksum=package_checksum,
        research_topic=research_topic,
    ))
    _replace_spec(files, "reagent_local.py", _idea_v0_3_runner_source())
    _replace_spec(files, "validate_package.py", _idea_v0_3_validator_source())
    return files


_SCAFFOLD_PROGRESS_HELPER = r'''

def _current_scaffold_artifact(root: Path) -> dict[str, Any]:
    current = _load_object(root / "memory/current-artifact.json", "current scaffold Artifact")
    if set(current) != {"relative_path", "artifact_kind", "media_type", "checksum", "size"}:
        raise ProgressReportError("current scaffold Artifact fields mismatch")
    relative = safe_relative_path(current["relative_path"])
    path = root.joinpath(*relative.split("/"))
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise ProgressReportError("current scaffold Artifact must be one regular file")
    content = path.read_bytes()
    if current["media_type"] != "application/json" or current["checksum"] != sha256_bytes(content) or current["size"] != len(content):
        raise ProgressReportError("current scaffold Artifact identity mismatch")
    return current
'''


def _scaffold_progress_source() -> bytes:
    source = Path(__file__).with_name("package_progress.py").read_text(encoding="utf-8")
    marker = "\ndef finalize(\n"
    output_marker = "    skill_pins = [\n"
    if marker not in source or output_marker not in source:
        raise RuntimeError("Progress helper scaffold extension point is unavailable")
    source = source.replace(marker, _SCAFFOLD_PROGRESS_HELPER + marker, 1)
    source = source.replace(
        output_marker,
        "    outputs.append(_current_scaffold_artifact(root))\n" + output_marker,
        1,
    )
    return source.encode("utf-8")


def _scaffold_files(
    *, workflow_id: str, project_id: str, project_name: str,
    package_id: str, package_checksum: str,
) -> dict[str, FileSpec]:
    from . import scaffold_runtime, scaffold_validator

    workflow = scaffold_workflow_document(workflow_id)
    definitions = {
        WRITING_WORKFLOW_ID: {
            "kind": "WRITING", "slug": "writing", "human": "outputs/manuscript.md",
            "output": MANUSCRIPT_DRAFT_TYPE,
            "next": "Review the placeholder draft and use an explicit Review Workflow if desired",
        },
        REVIEW_WORKFLOW_ID: {
            "kind": "REVIEW", "slug": "review", "human": "outputs/review_report.md",
            "output": REVIEW_REPORT_TYPE,
            "next": "Treat this only as flow-validation feedback; do not make research decisions from it",
        },
        EXPERIMENT_WORKFLOW_ID: {
            "kind": "EXPERIMENT", "slug": "reproduction-experiment",
            "human": "outputs/experiment_plan.md", "output": EXPERIMENT_RECORD_TYPE,
            "next": "Review the placeholder plan; real experiment execution is not enabled",
        },
    }
    definition = definitions[workflow_id]
    config = {
        "schema_version": "reagent.scaffold-workflow/v0.1",
        "workflow_id": workflow_id,
        "workflow_version": SCAFFOLD_WORKFLOW_VERSION,
        "workflow_kind": definition["kind"],
        "workflow_slug": definition["slug"],
        "core_capability_maturity": "SCAFFOLD_CORE",
        "input_requirements": workflow["input_requirements"],
        "human_output_path": definition["human"],
        "output_artifact_type": definition["output"],
        "artifact_path_prefix": scaffold_output_contract(definition["output"])["relative_path_prefix"],
        "completed_next_action": definition["next"],
        "supported_mode": (
            "IDEA_EXPERIMENT" if workflow_id == EXPERIMENT_WORKFLOW_ID else None
        ),
    }
    agent = f"""# ReAgent {workflow['workflow_type']} — SCAFFOLD_CORE

> **SCAFFOLD PLACEHOLDER**
> Product flow is functional. Core research capability is currently scaffold-only.

1. This Capsule is the complete local state for one exact Workflow Instance.
2. Read `workflow/scaffold.json`, the scaffold prompt, `memory/context.md`, and only the materialized files declared under `inputs/`.
3. Treat every input as read-only. Never read sibling Capsule outputs directly.
4. Write only this Capsule's declared `outputs/` and `memory/` paths.
5. Never invent citations, DOI values, papers, novelty, metrics, experiment results, significance, peer-review findings, scores, acceptance predictions, or successful reproduction claims.
6. Do not claim that substantive academic {workflow['workflow_type'].lower()} was performed.
7. Keep every scaffold marker in human-facing and canonical outputs.
8. Finalization must pass the bundled validator and publish a content-addressed Artifact.
9. End every round with a real Progress Report; `COMPLETED` means only that this scaffold flow ended.
10. Memory belongs only to this Workflow Instance. A fresh session continues from local files, not chat history.
11. The user may interrupt and continue safely; immutable Artifacts and prior Progress are never overwritten.
12. Do not access credentials, live Providers, external Resources, or real experiment execution.
"""
    prompt = f"""# Reviewed scaffold method — {workflow['workflow_type']}

This prompt validates product flow and provenance only. The research core is `SCAFFOLD_CORE`.
Read the exact materialized inputs, preserve their Artifact IDs and checksums, and allow the bundled deterministic finalizer to create only the visibly marked placeholder output. Do not add substantive scientific content. Do not fabricate evidence or conclusions. If inputs are insufficient, stop rather than guessing.
"""
    skill = """# Scaffold safety helper

Preserve exact provenance and explicit placeholder language. Never turn missing research capability into fabricated scientific content. This built-in helper is local Capsule guidance, not a general Skill platform.
"""
    context = {
        "schema_version": "reagent.scaffold-context/v0.1",
        "workflow_id": workflow_id,
        "workflow_version": SCAFFOLD_WORKFLOW_VERSION,
        "package_id": package_id,
        "package_checksum": package_checksum,
        "core_capability_maturity": "SCAFFOLD_CORE",
        "completed_rounds": 0,
        "latest_artifact": None,
        "continuation": "Read local files; prior chat history is not required.",
        "updated_at": DETERMINISTIC_GENERATED_AT,
    }
    draft = {
        "execution_round": 1,
        "harness_type": "codex",
        "harness_version": None,
        "harness_session_id": f"{definition['slug']}-round-1",
        "previous_report_id": None,
        "previous_report_checksum": None,
        "started_at": DETERMINISTIC_GENERATED_AT,
        "completed_at": DETERMINISTIC_GENERATED_AT,
        "status": "IN_PROGRESS",
        "completed_work": [],
        "current_state": "INPUT_REVIEW",
        "next_recommended_action": "Bind and materialize every required exact Artifact",
        "continuation_reason": None,
        "warnings": ["SCAFFOLD_CORE: no substantive research capability"],
        "errors": [],
        "unresolved_questions": [],
        "continuation_instructions": ["Read AGENT.md and memory/context.md"],
    }
    project = {
        "schema_version": "local-project-input/v0.1",
        "project_id": project_id,
        "project_name": project_name,
        "selected_workflow": workflow_id,
    }
    provenance = {
        "schema_version": "reagent.scaffold-input-provenance/v0.1",
        "workflow_instance_id": None,
        "artifacts": {},
    }
    return {
        "AGENT.md": FileSpec(agent.encode(), "text/markdown", "scaffold safety instructions", False, "INSTRUCTION"),
        "AGENTS.md": FileSpec(b"# Codex shim\n\nRead and follow `AGENT.md`.\n", "text/markdown", "Codex shim", False, "INSTRUCTION"),
        "CLAUDE.md": FileSpec(b"# Claude Code shim\n\nRead and follow `AGENT.md`.\n", "text/markdown", "Claude shim", False, "INSTRUCTION"),
        "README.md": FileSpec(f"# {workflow['workflow_type']} Scaffold Capsule\n\nProduct flow is functional. Research capability is placeholder. Run only through the Workspace generic CLI.\n".encode(), "text/markdown", "Capsule overview", False, "INSTRUCTION"),
        "reagent_local.py": FileSpec(Path(scaffold_runtime.__file__).read_bytes(), "text/x-python", "shared local scaffold runner", False, "INSTRUCTION"),
        "validate_package.py": FileSpec(Path(scaffold_validator.__file__).read_bytes(), "text/x-python", "shared self-contained scaffold validator", False, "INSTRUCTION"),
        "progress_report.py": FileSpec(_scaffold_progress_source(), "text/x-python", "Progress v0.2 scaffold helper", False, "INSTRUCTION"),
        "workflow/AGENT.md": FileSpec(b"# Scaffold Workflow\n\nFollow the root AGENT.md. Never produce unmarked or substantive scientific output.\n", "text/markdown", "workflow safety instructions", False, "INSTRUCTION"),
        "workflow/workflow.json": FileSpec(_json(workflow), "application/json", "pinned Workflow", False, "CONFIGURATION"),
        "workflow/scaffold.json": FileSpec(_json(config), "application/json", "scaffold execution contract", False, "CONFIGURATION"),
        f"workflow/prompts/{definition['slug']}.md": FileSpec(prompt.encode(), "text/markdown", "reviewed scaffold prompt", False, "INSTRUCTION"),
        "workflow/skills/scaffold-safety/SKILL.md": FileSpec(skill.encode(), "text/markdown", "built-in scaffold safety helper", False, "INSTRUCTION"),
        "workflow/skills/scaffold-safety/skill.json": FileSpec(_json({
            "schema_version": "local-skill/v0.1",
            "name": "reagent.scaffold-safety",
            "version": SCAFFOLD_SKILL_VERSION,
            "trust": "BUILT_IN_REVIEWED_ONLY",
            "required_capabilities": [
                "read_materialized_input", "write_declared_outputs",
                "append_progress_report", "preserve_scaffold_markers",
            ],
        }), "application/json", "built-in helper contract", False, "CONFIGURATION"),
        "workflow/artifact-inputs.json": FileSpec(_json({
            "schema_version": "reagent.artifact-input-contract/v0.1",
            "requirements": workflow["input_requirements"],
        }), "application/json", "typed Artifact input requirements", False, "CONFIGURATION"),
        "workflow/artifact-outputs.json": FileSpec(_json({
            "schema_version": "reagent.artifact-output-contract/v0.1",
            **scaffold_output_contract(definition["output"]),
            "producer_core_capability_maturity": "SCAFFOLD_CORE",
            "validity_point": "VALIDATED_SCAFFOLD_FINALIZATION",
        }), "application/json", "production scaffold Artifact contract", False, "CONFIGURATION"),
        "inputs/project.json": FileSpec(_json(project), "application/json", "immutable Project identity", False, "INPUT"),
        "outputs/README.md": FileSpec(f"# {workflow['workflow_type']} outputs\n\nEvery output is a SCAFFOLD PLACEHOLDER and is not a substantive research result.\n".encode(), "text/markdown", "output safety policy", False, "OUTPUT"),
        "memory/context.md": FileSpec(("# Scaffold Workflow Context\n\n```json\n" + canonical_json(context) + "\n```\n").encode(), "text/markdown", "cross-session context", True, "STATE"),
        "memory/input-provenance.json": FileSpec(_json(provenance), "application/json", "verified exact input provenance", True, "STATE"),
        "memory/progress/report-draft.json": FileSpec(_json(draft), "application/json", "mutable Progress draft", True, "STATE"),
        "memory/progress/reports/README.md": FileSpec(b"# Append-only Progress Reports\n", "text/markdown", "Progress policy", False, "STATE"),
        "memory/progress/receipts/README.md": FileSpec(b"# Verified upload receipts\n", "text/markdown", "receipt policy", False, "STATE"),
    }


def _scaffold_v0_2_files(
    *, workflow_id: str, project_id: str, project_name: str,
    package_id: str, package_checksum: str,
) -> dict[str, FileSpec]:
    """Render a new immutable scaffold Capsule backed by exact Registry Skills."""

    from backend.project_workspaces.skills import PRODUCTION_SKILLS

    files = dict(_scaffold_files(
        workflow_id=workflow_id,
        project_id=project_id,
        project_name=project_name,
        package_id=package_id,
        package_checksum=package_checksum,
    ))
    workflow = scaffold_workflow_document(
        workflow_id, workflow_version=SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION
    )
    _replace_spec(files, "workflow/workflow.json", _json(workflow))

    config = json.loads(files["workflow/scaffold.json"].content)
    config["workflow_version"] = SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION
    config["pinned_skills"] = [
        {
            "skill_id": asset.skill_id,
            "skill_version": asset.version,
            "content_checksum": asset.content_checksum,
            "trust": "BUILT_IN_REVIEWED",
        }
        for asset in PRODUCTION_SKILLS
    ]
    _replace_spec(files, "workflow/scaffold.json", _json(config))

    context_text = files["memory/context.md"].content.decode("utf-8")
    prefix, remainder = context_text.split("```json\n", 1)
    encoded, suffix = remainder.split("\n```", 1)
    context = json.loads(encoded)
    context["workflow_version"] = SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION
    _replace_spec(
        files,
        "memory/context.md",
        (prefix + "```json\n" + canonical_json(context) + "\n```" + suffix).encode(),
    )

    old_skill_root = "workflow/skills/scaffold-safety/"
    for path in tuple(files):
        if path.startswith(old_skill_root):
            del files[path]
    for asset in PRODUCTION_SKILLS:
        root = f"workflow/skills/{asset.skill_id}"
        for relative_path, content in asset.content_files().items():
            media_type = (
                "text/markdown" if relative_path.endswith(".md")
                else "application/json"
            )
            files[f"{root}/{relative_path}"] = FileSpec(
                content,
                media_type,
                f"pinned reviewed Skill {asset.skill_id}",
                False,
                "INSTRUCTION" if relative_path.endswith(".md") else "CONFIGURATION",
            )

    agent = files["AGENT.md"].content.decode("utf-8")
    consumption = """
13. At startup, read `package-manifest.json` and verify its exact `skill_pins`.
14. Read each pinned Skill's `skill.json`, then its declared `SKILL.md`, before the Workflow prompt.
15. Use only Skills bundled in this Capsule; never scan the Workspace or sibling Capsules for Skills.
16. Skills cannot override system safety, modify `inputs/`, change immutable Skill files, or write outside declared mutable roots.
"""
    _replace_spec(files, "AGENT.md", (agent.rstrip() + "\n" + consumption).encode())
    return files


def _writing_files(**kwargs) -> dict[str, FileSpec]:
    kwargs.pop("research_topic", None)
    return _scaffold_files(workflow_id=WRITING_WORKFLOW_ID, **kwargs)


def _review_files(**kwargs) -> dict[str, FileSpec]:
    kwargs.pop("research_topic", None)
    return _scaffold_files(workflow_id=REVIEW_WORKFLOW_ID, **kwargs)


def _experiment_files(**kwargs) -> dict[str, FileSpec]:
    kwargs.pop("research_topic", None)
    return _scaffold_files(workflow_id=EXPERIMENT_WORKFLOW_ID, **kwargs)


def _writing_v0_2_files(**kwargs) -> dict[str, FileSpec]:
    kwargs.pop("research_topic", None)
    return _scaffold_v0_2_files(workflow_id=WRITING_WORKFLOW_ID, **kwargs)


def _review_v0_2_files(**kwargs) -> dict[str, FileSpec]:
    kwargs.pop("research_topic", None)
    return _scaffold_v0_2_files(workflow_id=REVIEW_WORKFLOW_ID, **kwargs)


def _scaffold_interactive_instruction(workflow_id: str) -> str:
    """Return only the bounded first turn; the pinned prompt owns methodology."""

    instructions = {
        WRITING_WORKFLOW_ID: """REAGENT WRITING — INPUT_REVIEW

You are beginning the ReAgent Writing Workflow. Read and follow the root
AGENT.md (and root AGENTS.md when present), workflow/AGENT.md, the pinned
workflow/prompts/writing.md, workflow/scaffold.json, memory/context.md, and
memory/input-provenance.json. Read only the exact materialized inputs declared
by the Workflow: the required inputs/selected-research-idea.json and
inputs/selected-paper-library.json, plus inputs/experiment-record.json,
inputs/review-report.json, and inputs/prior-manuscript.json only when their
exact Artifact records are present. Never inspect sibling Capsules or scan the
Workspace.

Begin at INPUT_REVIEW. Identify every available input by role and preserve its
exact Artifact ID and checksum. Distinguish the selected Idea and Literature
evidence from optional Experiment, Review, and prior-manuscript inputs. When
both prior manuscript and review feedback are present, identify this as a
revision round; never select either input implicitly.

State the safety boundary before discussing document structure: this version
is SCAFFOLD_CORE and will not create a real, substantive, publication-quality
manuscript. Do not fabricate citations, DOI values, papers, experiments,
results, metrics, significance, novelty, or plausible-looking substantive
academic prose. Follow the pinned Writing prompt for the remaining frozen
method. Explain that this flow reviews the available evidence, establishes the
intended document structure, and produces only outputs/manuscript.md plus a
content-addressed manuscript-draft/v1 that remain visibly marked SCAFFOLD
PLACEHOLDER. Begin the Writing interaction automatically; do not ask the owner
for a hidden start, write, begin, or draft-paper phrase.""",
        REVIEW_WORKFLOW_ID: """REAGENT REVIEW — INPUT_REVIEW

You are beginning the ReAgent Review Workflow. Read and follow the root
AGENT.md (and root AGENTS.md when present), workflow/AGENT.md, the pinned
workflow/prompts/review.md, workflow/scaffold.json, memory/context.md, and
memory/input-provenance.json. Read only the exact materialized inputs declared
by the Workflow: the required inputs/manuscript-draft.json, plus
inputs/selected-paper-library.json and inputs/experiment-record.json only when
their exact Artifact records are present. Never inspect sibling Capsules or
scan the Workspace.

Begin at INPUT_REVIEW. Identify the loaded manuscript by its exact Artifact ID
and checksum, then identify any exact optional Literature or Experiment
supporting evidence. Preserve all provenance and never select an input
implicitly.

State the safety boundary before discussing the review record: this version is
SCAFFOLD_CORE and does not perform real peer review, full scientific
validation, correctness verification, scoring, reviewer-confidence assessment,
or acceptance/rejection judgment. Follow the pinned Review prompt for the
remaining frozen method. Explain that this flow produces only
outputs/review_report.md and a content-addressed review-report/v1 visibly
marked SCAFFOLD REVIEW PLACEHOLDER, with empty major/minor issue lists and the
fixed recommendation INSUFFICIENT_EVIDENCE. Do not fabricate substantive
revision advice. Begin the Review interaction automatically; do not ask the
owner for a hidden start-review or review-this-draft phrase.""",
    }
    try:
        return instructions[workflow_id]
    except KeyError as error:
        raise ValueError("interactive scaffold bootstrap supports Writing/Review only") from error


def _scaffold_interactive_runner_source(workflow_id: str) -> bytes:
    """Build the future-safe transport used only by new immutable Capsules."""

    source = Path(__file__).with_name("scaffold_runtime.py").read_text(encoding="utf-8")
    source = source.replace("import runpy\n", "import runpy\nimport signal\n", 1)
    source = source.replace(
        '"client_version": "reagent-local-scaffold/0.1.0",',
        '"client_version": "reagent-local-scaffold/0.3.0",',
        1,
    )
    old = '''def _run_harness(root: Path, executable: str) -> None:
    environment = {
        key: os.environ[key]
        for key in ("PATH", "TMPDIR", "LANG", "LC_ALL", "TERM")
        if key in os.environ
    }
    result = subprocess.run([executable], cwd=root, env=environment, check=False)
    if result.returncode != 0:
        raise ScaffoldRuntimeError("Codex exited before scaffold finalization")
'''
    label = "Writing" if workflow_id == WRITING_WORKFLOW_ID else "Review"
    instruction = _scaffold_interactive_instruction(workflow_id)
    new = f'''def _initial_instruction() -> str:
    return {instruction!r}


def _codex_preflight(executable: str, environment: dict[str, str]) -> None:
    checks = (
        ([executable, "--version"], ()),
        ([executable, "--help"], ("--sandbox", "--ask-for-approval", "--no-alt-screen", "--cd")),
        ([executable, "login", "status"], ()),
    )
    for command, required in checks:
        try:
            result = subprocess.run(
                command, env=environment, capture_output=True, text=True,
                check=False, timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ScaffoldRuntimeError("Codex CLI preflight could not be completed") from error
        if result.returncode != 0 or any(item not in result.stdout for item in required):
            raise ScaffoldRuntimeError("Codex CLI does not satisfy the interactive Harness contract")


def _stop_harness(child: subprocess.Popen[Any]) -> None:
    if child.poll() is not None:
        return
    child.send_signal(signal.SIGINT)
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


def _run_harness(root: Path, executable: str) -> None:
    environment = {{
        key: os.environ[key]
        for key in ("PATH", "TMPDIR", "LANG", "LC_ALL", "TERM")
        if key in os.environ
    }}
    _codex_preflight(executable, environment)
    command = [
        executable,
        "--sandbox", "workspace-write",
        "--ask-for-approval", "on-request",
        "--no-alt-screen",
        "-C", str(root),
        _initial_instruction(),
    ]
    child: subprocess.Popen[Any] | None = None
    previous_handlers: dict[int, Any] = {{}}

    def terminate_signal(signum: int, frame: Any) -> None:
        raise KeyboardInterrupt

    try:
        for signum in (signal.SIGTERM, signal.SIGHUP):
            previous_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, terminate_signal)
        child = subprocess.Popen(command, cwd=root, env=environment)
        returncode = child.wait()
    except KeyboardInterrupt as error:
        if child is not None:
            _stop_harness(child)
        raise ScaffoldRuntimeError(
            "Owner interrupted the {label} scaffold; local memory and outputs were retained"
        ) from error
    except OSError as error:
        raise ScaffoldRuntimeError("Codex process could not be started") from error
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
    if returncode != 0:
        raise ScaffoldRuntimeError("Codex exited before {label} scaffold finalization")
'''
    if old not in source:
        raise RuntimeError("historical scaffold runner bootstrap extension point is unavailable")
    return source.replace(old, new, 1).encode("utf-8")


def _scaffold_v0_3_files(*, workflow_id: str, **kwargs) -> dict[str, FileSpec]:
    """Replace only Harness transport over the immutable Workflow 0.2 body."""

    files = dict(_scaffold_v0_2_files(workflow_id=workflow_id, **kwargs))
    _replace_spec(files, "reagent_local.py", _scaffold_interactive_runner_source(workflow_id))
    return files


def _completion_adoption_runner_source(
    source: bytes, *, client_version: str
) -> bytes:
    """Add strict adopt-or-finalize lifecycle to a future interactive runner.

    This transforms already-rendered new-version source.  It deliberately does
    not edit ``scaffold_runtime.py`` or any historical renderer.
    """

    text = source.decode("utf-8")
    old_client = next(
        value for value in (
            "reagent-local-scaffold/0.3.0",
            "reagent-local-scaffold/0.4.0",
        ) if value in text
    )
    text = text.replace(old_client, client_version, 1)
    marker = "\ndef main(argv: list[str] | None = None) -> int:\n"
    if marker not in text:
        raise RuntimeError("interactive completion extension point is unavailable")
    helper = r'''

def _report_chain_snapshot(root: Path) -> list[dict[str, Any]]:
    reports_root = root / "memory/progress/reports"
    if reports_root.is_symlink() or not reports_root.is_dir():
        raise ScaffoldRuntimeError("Progress history root is unsafe")
    paths = sorted(reports_root.glob("*.json"))
    reports: list[dict[str, Any]] = []
    namespace = runpy.run_path(str(root / "progress_report.py"))
    for path in paths:
        if (
            path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1
            or not path.name.startswith("prv2-")
        ):
            raise ScaffoldRuntimeError("Progress history contains an unsafe entry")
        report = _object(path, "Progress Report")
        try:
            namespace["verify_identity"](report)
        except Exception as error:
            raise ScaffoldRuntimeError("Progress Report identity is invalid") from error
        if path.name != report["report_id"] + ".json":
            raise ScaffoldRuntimeError("Progress Report filename is invalid")
        reports.append(report)
    reports.sort(key=lambda item: (item["execution_round"], item["report_id"]))
    if [item["execution_round"] for item in reports] != list(range(1, len(reports) + 1)):
        raise ScaffoldRuntimeError("Progress history is not one contiguous chain")
    for previous, current in zip(reports, reports[1:]):
        if (
            current.get("previous_report_id") != previous["report_id"]
            or current.get("previous_report_checksum") != previous["report_checksum"]
            or current.get("context_before_checksum") != previous["context_after_checksum"]
        ):
            raise ScaffoldRuntimeError("Progress predecessor chain is invalid")
    return reports


def _verified_file(root: Path, relative: str) -> tuple[str, int, bytes]:
    path = root.joinpath(*relative.split("/"))
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise ScaffoldRuntimeError("Agent-finalized output is unsafe")
    content = path.read_bytes()
    return sha256_bytes(content), len(content), content


def _adopt_agent_finalization(
    root: Path,
    config: dict[str, Any],
    context_before: str,
    before: list[dict[str, Any]],
) -> tuple[Path, dict[str, Any]] | None:
    after = _report_chain_snapshot(root)
    before_identity = [(item["report_id"], item["report_checksum"]) for item in before]
    after_prefix = [(item["report_id"], item["report_checksum"]) for item in after[:len(before)]]
    if after_prefix != before_identity:
        raise ScaffoldRuntimeError("Harness modified immutable Progress history")
    delta = after[len(before):]
    if not delta:
        return None
    if len(delta) != 1:
        raise ScaffoldRuntimeError("Harness created an unexpected Progress delta")
    report = delta[0]
    manifest = _object(root / "package-manifest.json", "package manifest")
    previous = before[-1] if before else None
    expected_identity = {
        "project_id": manifest["experimental_project_identity"],
        "package_id": manifest["package_id"],
        "package_checksum": manifest["package_checksum"],
        "package_schema_version": manifest["package_schema_version"],
        "workflow_id": manifest["workflow_id"],
        "workflow_version": manifest["workflow_version"],
        "workflow_checksum": manifest["workflow_checksum"],
        "execution_round": len(before) + 1,
        "previous_report_id": None if previous is None else previous["report_id"],
        "previous_report_checksum": None if previous is None else previous["report_checksum"],
        "context_before_checksum": context_before,
        "status": "COMPLETED",
        "current_state": "COMPLETED",
    }
    if any(report.get(field) != value for field, value in expected_identity.items()):
        raise ScaffoldRuntimeError("Agent-finalized Progress scope or chain is invalid")
    context_checksum, _, _ = _verified_file(root, "memory/context.md")
    if report.get("context_after_checksum") != context_checksum:
        raise ScaffoldRuntimeError("Agent-finalized Progress context transition is invalid")

    current = _object(root / "memory/current-artifact.json", "current Artifact")
    if set(current) != {"relative_path", "artifact_kind", "media_type", "checksum", "size"}:
        raise ScaffoldRuntimeError("Agent-finalized Artifact identity is invalid")
    checksum, size, content = _verified_file(root, current["relative_path"])
    if (
        current["artifact_kind"] != config["output_artifact_type"]
        or current["media_type"] != "application/json"
        or current["checksum"] != checksum
        or current["size"] != size
        or current not in report.get("output_artifacts", [])
    ):
        raise ScaffoldRuntimeError("Agent-finalized Artifact provenance is invalid")
    try:
        artifact = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ScaffoldRuntimeError("Agent-finalized Artifact is invalid JSON") from error
    provenance = _object(root / "memory/input-provenance.json", "input provenance")
    expected_artifact, expected_human = _scaffold_payload(
        config, provenance["artifacts"], root
    )
    if artifact != expected_artifact:
        raise ScaffoldRuntimeError("Agent-finalized Artifact semantics or provenance drifted")
    human_checksum, human_size, human = _verified_file(root, config["human_output_path"])
    if human != expected_human:
        raise ScaffoldRuntimeError("Agent-finalized human output is not deterministic")
    contracts = manifest.get("output_contracts", [])
    human_contract = next(
        (item for item in contracts
         if item.get("required_output_path") == config["human_output_path"]),
        None,
    )
    if not isinstance(human_contract, dict):
        raise ScaffoldRuntimeError("Scaffold human output contract is unavailable")
    expected_human_output = {
        "relative_path": config["human_output_path"],
        "artifact_kind": human_contract["artifact_kind"],
        "media_type": human_contract["media_type"],
        "checksum": human_checksum,
        "size": human_size,
    }
    if expected_human_output not in report.get("output_artifacts", []):
        raise ScaffoldRuntimeError("Agent-finalized human output provenance is invalid")
    validator = runpy.run_path(str(root / "validate_package.py"))
    try:
        validator["validate_scaffold_artifact"](artifact)
    except Exception as error:
        raise ScaffoldRuntimeError("Agent-finalized scaffold safety validation failed") from error
    return root / "memory/progress/reports" / (report["report_id"] + ".json"), current


def _agent_finalize(root: Path) -> dict[str, Any]:
    """Perform the Capsule's deterministic Agent-owned terminal transition."""

    result = preflight(root)
    config = _object(root / "workflow/scaffold.json", "scaffold contract")
    history = _report_chain_snapshot(root)
    draft = _object(root / "memory/progress/report-draft.json", "Progress Report draft")
    if history and draft.get("execution_round") == history[-1]["execution_round"]:
        latest = history[-1]
        context_checksum, _, _ = _verified_file(root, "memory/context.md")
        if (
            latest.get("status") != "COMPLETED"
            or latest.get("current_state") != "COMPLETED"
            or latest.get("context_after_checksum") != context_checksum
        ):
            raise ScaffoldRuntimeError("Existing Agent finalization is not reusable")
        return {
            **result,
            "artifact": _object(root / "memory/current-artifact.json", "current Artifact"),
            "progress_report": (
                "memory/progress/reports/" + latest["report_id"] + ".json"
            ),
            "idempotent_replay": True,
        }
    if draft.get("execution_round") != len(history) + 1:
        raise ScaffoldRuntimeError("Progress draft does not continue local history")
    namespace = runpy.run_path(str(root / "progress_report.py"))
    context_before = namespace["snapshot"](root)["context_before_checksum"]
    artifact = _publish(root, config)
    _update_context(root, config, artifact)
    report_path = _finalize(root, context_before)
    return {
        **result,
        "artifact": artifact,
        "progress_report": report_path.relative_to(root).as_posix(),
    }
'''
    text = text.replace(marker, helper + marker, 1)
    parser_old = '''    run_parser.add_argument("--codex-executable")
    run_parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        result = preflight(root)
        if not args.preflight_only:
'''
    parser_new = '''    run_parser.add_argument("--codex-executable")
    run_parser.add_argument("--preflight-only", action="store_true")
    finalize_parser = commands.add_parser("finalize-scaffold")
    finalize_parser.add_argument("root", nargs="?", default=".", type=Path)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        if args.command == "finalize-scaffold":
            result = _agent_finalize(root)
        else:
            result = preflight(root)
        if args.command == "run" and not args.preflight_only:
'''
    if parser_old not in text:
        raise RuntimeError("interactive completion CLI extension point is unavailable")
    text = text.replace(parser_old, parser_new, 1)
    prompt_old = '''        _initial_instruction(),
    ]
'''
    prompt_new = '''        _initial_instruction() + (
            "\\n\\nAfter the owner-approved scaffold interaction is complete, "
            "run exactly `PYTHONDONTWRITEBYTECODE=1 python reagent_local.py "
            "finalize-scaffold .`. This is the bundled deterministic finalizer. "
            "Do not import reagent_local.py or call its private helpers."
        ),
    ]
'''
    if prompt_old not in text:
        raise RuntimeError("interactive completion prompt extension point is unavailable")
    text = text.replace(prompt_old, prompt_new, 1)
    old = '''            config = _object(root / "workflow/scaffold.json", "scaffold contract")
            context_before = _prepare_draft(root, config)
            _run_harness(root, _codex_executable(args.codex_executable))
            # The Harness is untrusted with respect to immutable input bytes and
            # scaffold safety. Re-run the exact preflight before publication.
            preflight(root)
            artifact = _publish(root, config)
            _update_context(root, config, artifact)
            report_path = _finalize(root, context_before)
            result = {
'''
    new = '''            config = _object(root / "workflow/scaffold.json", "scaffold contract")
            progress_before = _report_chain_snapshot(root)
            context_before = _prepare_draft(root, config)
            _run_harness(root, _codex_executable(args.codex_executable))
            # The Harness is untrusted with respect to immutable inputs, output
            # provenance, and Progress.  Adopt exactly one valid next terminal
            # round, or retain the historical runner-owned finalization path.
            preflight(root)
            adopted = _adopt_agent_finalization(
                root, config, context_before, progress_before
            )
            if adopted is None:
                artifact = _publish(root, config)
                _update_context(root, config, artifact)
                report_path = _finalize(root, context_before)
            else:
                report_path, artifact = adopted
            result = {
'''
    if old not in text:
        raise RuntimeError("interactive lifecycle extension point is unavailable")
    return text.replace(old, new, 1).encode("utf-8")


def _future_scaffold_validator_source(*, version: str) -> bytes:
    source = Path(__file__).with_name("scaffold_validator.py").read_text(encoding="utf-8")
    old = 'manifest.get("package_template_version") not in {"0.1.0", "0.2.0", "0.3.0"}'
    new = (
        'manifest.get("package_template_version") not in '
        '{"0.1.0", "0.2.0", "0.3.0", ' + repr(version) + '}'
    )
    if old not in source:
        raise RuntimeError("scaffold validator version extension point is unavailable")
    return source.replace(old, new, 1).encode("utf-8")


def _scaffold_v0_4_files(*, workflow_id: str, **kwargs) -> dict[str, FileSpec]:
    files = dict(_scaffold_v0_3_files(workflow_id=workflow_id, **kwargs))
    runner = _completion_adoption_runner_source(
        files["reagent_local.py"].content,
        client_version="reagent-local-scaffold/0.4.0",
    )
    _replace_spec(files, "reagent_local.py", runner)
    _replace_spec(
        files, "validate_package.py",
        _future_scaffold_validator_source(version=SCAFFOLD_COMPLETION_CAPSULE_VERSION),
    )
    return files


def _writing_v0_4_files(**kwargs) -> dict[str, FileSpec]:
    kwargs.pop("research_topic", None)
    return _scaffold_v0_4_files(workflow_id=WRITING_WORKFLOW_ID, **kwargs)


def _review_v0_4_files(**kwargs) -> dict[str, FileSpec]:
    kwargs.pop("research_topic", None)
    return _scaffold_v0_4_files(workflow_id=REVIEW_WORKFLOW_ID, **kwargs)


def _writing_v0_3_files(**kwargs) -> dict[str, FileSpec]:
    kwargs.pop("research_topic", None)
    return _scaffold_v0_3_files(workflow_id=WRITING_WORKFLOW_ID, **kwargs)


def _review_v0_3_files(**kwargs) -> dict[str, FileSpec]:
    kwargs.pop("research_topic", None)
    return _scaffold_v0_3_files(workflow_id=REVIEW_WORKFLOW_ID, **kwargs)


def _experiment_v0_2_files(**kwargs) -> dict[str, FileSpec]:
    kwargs.pop("research_topic", None)
    return _scaffold_v0_2_files(workflow_id=EXPERIMENT_WORKFLOW_ID, **kwargs)


def _experiment_v0_3_files(**kwargs) -> dict[str, FileSpec]:
    """Render Experiment 0.3 without mutating the published 0.2 Capsule."""

    kwargs.pop("research_topic", None)
    files = _scaffold_v0_2_files(workflow_id=EXPERIMENT_WORKFLOW_ID, **kwargs)
    workflow = scaffold_workflow_document(
        EXPERIMENT_WORKFLOW_ID,
        workflow_version=EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
    )
    _replace_spec(files, "workflow/workflow.json", _json(workflow))
    config = json.loads(files["workflow/scaffold.json"].content)
    config["workflow_version"] = EXPERIMENT_RESOURCE_WORKFLOW_VERSION
    config["resource_requirements"] = workflow["resource_requirements"]
    config["resource_execution_policy"] = workflow["resource_execution_policy"]
    _replace_spec(files, "workflow/scaffold.json", _json(config))
    files["workflow/resource-requirements.json"] = FileSpec(
        _json({
            "schema_version": "reagent.resource-requirements/v0.1",
            "requirements": workflow["resource_requirements"],
            "local_index": ".reagent/resource-index.json",
            "policy": "bound resources must be locally verified; bytes are never executed",
        }),
        "application/json",
        "optional external Resource requirements",
        False,
        "CONFIGURATION",
    )
    context_text = files["memory/context.md"].content.decode("utf-8")
    _replace_spec(
        files,
        "memory/context.md",
        context_text.replace(
            '"workflow_version":"0.2.0"',
            '"workflow_version":"0.3.0"',
        ).encode(),
    )
    agent = files["AGENT.md"].content.decode("utf-8")
    resource_contract = """
17. Read only verified Resource metadata from the Workspace Resource Index; never scan for external assets.
18. A configured Resource that is unresolved, drifted, or unsupported fails preflight closed.
19. Resource bytes are external assets, not Skills or Artifacts, and this scaffold must never execute them.
20. Resource presence does not change `SCAFFOLD_CORE`, `PLACEHOLDER_NOT_EXECUTED`, or `actual_results = null`.
"""
    _replace_spec(files, "AGENT.md", (agent.rstrip() + "\n" + resource_contract).encode())
    return files


def _experiment_v0_4_runner_source() -> bytes:
    """Add only the bounded Experiment INPUT_REVIEW Harness bootstrap."""

    source = Path(__file__).with_name("scaffold_runtime.py").read_text(encoding="utf-8")
    source = source.replace("import runpy\n", "import runpy\nimport signal\n", 1)
    source = source.replace(
        '"client_version": "reagent-local-scaffold/0.1.0",',
        '"client_version": "reagent-local-scaffold/0.4.0",',
        1,
    )
    preflight_marker = '''def preflight(root: Path) -> dict[str, Any]:
    _validate_package(root)
    config = _object(root / "workflow/scaffold.json", "scaffold contract")
'''
    preflight_replacement = '''def _validate_experiment_resource_provenance(
    root: Path, config: dict[str, Any]
) -> None:
    if config.get("workflow_kind") != "EXPERIMENT":
        return
    value = _object(
        root / "memory/resource-provenance.json", "Experiment Resource provenance"
    )
    if set(value) != {"schema_version", "workflow_instance_id", "requirements"}:
        raise ScaffoldRuntimeError("Experiment Resource provenance fields mismatch")
    if value.get("schema_version") != "reagent.experiment-resource-provenance/v0.1":
        raise ScaffoldRuntimeError("Experiment Resource provenance schema mismatch")
    instance_id = value.get("workflow_instance_id")
    if not isinstance(instance_id, str) or not instance_id.startswith("wfi-"):
        raise ScaffoldRuntimeError("Experiment Resource provenance identity is unavailable")
    expected = (
        ("source_repository", "SOURCE_REPOSITORY"),
        ("dataset", "DATASET"),
        ("model", "MODEL"),
        ("checkpoint", "CHECKPOINT"),
    )
    requirements = value.get("requirements")
    if not isinstance(requirements, list) or len(requirements) != len(expected):
        raise ScaffoldRuntimeError("Experiment Resource provenance requirements mismatch")
    fields = {
        "requirement_key", "resource_kind", "configured", "resource_id",
        "provider", "display_name", "exact_revision", "resolution_status",
    }
    for item, identity in zip(requirements, expected, strict=True):
        if not isinstance(item, dict) or set(item) != fields:
            raise ScaffoldRuntimeError("Experiment Resource provenance entry mismatch")
        if (item.get("requirement_key"), item.get("resource_kind")) != identity:
            raise ScaffoldRuntimeError("Experiment Resource provenance order mismatch")
        if item.get("configured") is False:
            if any(item.get(field) is not None for field in (
                "resource_id", "provider", "display_name", "exact_revision"
            )) or item.get("resolution_status") != "UNCONFIGURED":
                raise ScaffoldRuntimeError("Unconfigured Resource provenance is invalid")
        elif item.get("configured") is True:
            if (
                not all(isinstance(item.get(field), str) and item[field].strip() for field in (
                    "resource_id", "provider", "display_name", "exact_revision"
                ))
                or item.get("resolution_status") != "RESOLVED_VERIFIED"
            ):
                raise ScaffoldRuntimeError("Configured Resource provenance is invalid")
        else:
            raise ScaffoldRuntimeError("Experiment Resource configured state is invalid")


def preflight(root: Path) -> dict[str, Any]:
    _validate_package(root)
    config = _object(root / "workflow/scaffold.json", "scaffold contract")
    _validate_experiment_resource_provenance(root, config)
'''
    if preflight_marker not in source:
        raise RuntimeError("accepted scaffold preflight extension point is unavailable")
    source = source.replace(preflight_marker, preflight_replacement, 1)
    old = '''def _run_harness(root: Path, executable: str) -> None:
    environment = {
        key: os.environ[key]
        for key in ("PATH", "TMPDIR", "LANG", "LC_ALL", "TERM")
        if key in os.environ
    }
    result = subprocess.run([executable], cwd=root, env=environment, check=False)
    if result.returncode != 0:
        raise ScaffoldRuntimeError("Codex exited before scaffold finalization")
'''
    new = '''def _initial_instruction() -> str:
    return """REAGENT REPRODUCTION & EXPERIMENT — INPUT_REVIEW

You are beginning the ReAgent Reproduction & Experiment Workflow. Read and
follow the root AGENTS.md and AGENT.md, workflow/AGENT.md, the pinned
workflow/prompts/reproduction-experiment.md, workflow/scaffold.json,
workflow/resource-requirements.json, memory/context.md,
memory/input-provenance.json, and memory/resource-provenance.json. Read only
the exact materialized inputs declared by the Workflow: the required
inputs/selected-research-idea.json and, when present, the optional
inputs/selected-paper-library.json. Never inspect sibling Capsules or scan the
Workspace.

Begin at INPUT_REVIEW. First identify the loaded research inputs and accurately
summarize the configured versus unconfigured Resource categories from the
bounded local projection. Explain what each category could support in a future
real Experiment Core without claiming that an unconfigured Resource exists.

State the safety boundary before discussing the plan: this version is
SCAFFOLD_CORE, supports only IDEA_EXPERIMENT, and has PAPER_REPRODUCTION not
enabled. It will not execute Resource bytes, run simulations, train models,
measure metrics, or produce scientific results. Follow the pinned Workflow
prompt for the remaining scaffold method. The only valid result is a visibly
marked scaffold plan and experiment-record/v1 with
PLACEHOLDER_NOT_EXECUTED and actual_results null. Ask the owner to review the
intended scaffold plan; never fabricate execution or results."""


def _codex_preflight(executable: str, environment: dict[str, str]) -> None:
    checks = (
        ([executable, "--version"], ()),
        ([executable, "--help"], ("--sandbox", "--ask-for-approval", "--no-alt-screen", "--cd")),
        ([executable, "login", "status"], ()),
    )
    for command, required in checks:
        try:
            result = subprocess.run(
                command, env=environment, capture_output=True, text=True,
                check=False, timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ScaffoldRuntimeError("Codex CLI preflight could not be completed") from error
        if result.returncode != 0 or any(item not in result.stdout for item in required):
            raise ScaffoldRuntimeError("Codex CLI does not satisfy the interactive Harness contract")


def _stop_harness(child: subprocess.Popen[Any]) -> None:
    if child.poll() is not None:
        return
    child.send_signal(signal.SIGINT)
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


def _run_harness(root: Path, executable: str) -> None:
    environment = {
        key: os.environ[key]
        for key in ("PATH", "TMPDIR", "LANG", "LC_ALL", "TERM")
        if key in os.environ
    }
    _codex_preflight(executable, environment)
    command = [
        executable,
        "--sandbox", "workspace-write",
        "--ask-for-approval", "on-request",
        "--no-alt-screen",
        "-C", str(root),
        _initial_instruction(),
    ]
    child: subprocess.Popen[Any] | None = None
    previous_handlers: dict[int, Any] = {}

    def terminate_signal(signum: int, frame: Any) -> None:
        raise KeyboardInterrupt

    try:
        for signum in (signal.SIGTERM, signal.SIGHUP):
            previous_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, terminate_signal)
        child = subprocess.Popen(command, cwd=root, env=environment)
        returncode = child.wait()
    except KeyboardInterrupt as error:
        if child is not None:
            _stop_harness(child)
        raise ScaffoldRuntimeError(
            "Owner interrupted the Experiment scaffold; local inputs and memory were retained"
        ) from error
    except OSError as error:
        raise ScaffoldRuntimeError("Codex process could not be started") from error
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
    if returncode != 0:
        raise ScaffoldRuntimeError("Codex exited before scaffold finalization")
'''
    if old not in source:
        raise RuntimeError("accepted scaffold Harness extension point is unavailable")
    return source.replace(old, new, 1).encode("utf-8")


def _experiment_v0_4_validator_source() -> bytes:
    """Accept the new immutable Capsule identity without changing old bytes."""

    source = Path(__file__).with_name("scaffold_validator.py").read_text(
        encoding="utf-8"
    )
    old = 'manifest.get("package_template_version") not in {"0.1.0", "0.2.0", "0.3.0"}'
    new = (
        'manifest.get("package_template_version") not in '
        '{"0.1.0", "0.2.0", "0.3.0", "0.4.0"}'
    )
    if old not in source:
        raise RuntimeError("accepted scaffold validator extension point is unavailable")
    return source.replace(old, new, 1).encode("utf-8")


def _experiment_v0_4_files(**kwargs) -> dict[str, FileSpec]:
    """Render Experiment 0.4 without mutating published 0.3 content."""

    files = dict(_experiment_v0_3_files(**kwargs))
    _replace_spec(files, "reagent_local.py", _experiment_v0_4_runner_source())
    _replace_spec(files, "validate_package.py", _experiment_v0_4_validator_source())
    initial_resources = {
        "schema_version": "reagent.experiment-resource-provenance/v0.1",
        "workflow_instance_id": None,
        "requirements": [
            {
                "requirement_key": key,
                "resource_kind": kind,
                "configured": False,
                "resource_id": None,
                "provider": None,
                "display_name": None,
                "exact_revision": None,
                "resolution_status": "UNCONFIGURED",
            }
            for key, kind in (
                ("source_repository", "SOURCE_REPOSITORY"),
                ("dataset", "DATASET"),
                ("model", "MODEL"),
                ("checkpoint", "CHECKPOINT"),
            )
        ],
    }
    files["memory/resource-provenance.json"] = FileSpec(
        _json(initial_resources),
        "application/json",
        "bounded Experiment Resource status projection",
        True,
        "STATE",
    )
    return files


def _experiment_v0_5_files(**kwargs) -> dict[str, FileSpec]:
    """Render only the Progress lifecycle repair over immutable 0.4 bytes."""

    files = dict(_experiment_v0_4_files(**kwargs))
    runner = _completion_adoption_runner_source(
        files["reagent_local.py"].content,
        client_version="reagent-local-scaffold/0.5.0",
    )
    _replace_spec(files, "reagent_local.py", runner)
    validator = files["validate_package.py"].content.decode("utf-8")
    old = '{"0.1.0", "0.2.0", "0.3.0", "0.4.0"}'
    if old not in validator:
        raise RuntimeError("Experiment validator lifecycle extension point is unavailable")
    _replace_spec(
        files, "validate_package.py",
        validator.replace(old, '{"0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0"}', 1).encode(),
    )
    return files


def _real_experiment_files(
    *, project_id: str, project_name: str, package_id: str,
    package_checksum: str, research_topic: str,
) -> dict[str, FileSpec]:
    """Render only the narrow reviewed 0.4/0.6 local Experiment Capsule."""

    del research_topic
    from backend.project_workspaces.skills import RESEARCH_ARTIFACT_PROVENANCE_SKILL
    from . import real_experiment_runtime, real_experiment_validator

    workflow = real_experiment_workflow_document()
    skill = RESEARCH_ARTIFACT_PROVENANCE_SKILL
    skill_files = skill.content_files()
    contract = {
        "schema_version": "reagent.real-experiment-workflow/v0.1",
        "workflow_id": EXPERIMENT_WORKFLOW_ID,
        "workflow_version": REAL_EXPERIMENT_WORKFLOW_VERSION,
        "core_capability_maturity": "REVIEWED_CORE",
        "input_requirements": workflow["input_requirements"],
        "resource_requirements": workflow["resource_requirements"],
        "output_artifact_type": EXPERIMENT_RECORD_V2_TYPE,
        "network_policy": "DISABLED",
        "process_model": "ONE_LOCAL_FOREGROUND_PROCESS",
        "automatic_retry": False,
        "requirements_fields": [
            "research_question", "hypothesis", "scientific_inputs",
            "configuration", "seeds", "repetitions", "metrics", "runtime",
            "limits", "stopping_conditions",
        ],
        "plan_fields": [
            "research_question", "hypothesis", "requirements_sha256",
            "source_artifacts", "resource", "entrypoint", "argv",
            "working_directory", "configuration", "seeds", "repetitions",
            "metrics", "environment", "network_policy", "limits",
            "stopping_conditions", "known_limitations",
        ],
    }
    context = {
        "schema_version": "reagent.real-experiment-context/v0.1",
        "workflow_id": EXPERIMENT_WORKFLOW_ID,
        "workflow_version": REAL_EXPERIMENT_WORKFLOW_VERSION,
        "package_id": package_id,
        "package_checksum": package_checksum,
        "stage": "INPUT_REVIEW",
        "attempt_id": None,
        "result_status": None,
        "latest_artifact": None,
        "updated_at": DETERMINISTIC_GENERATED_AT,
    }
    draft = {
        "execution_round": 1,
        "harness_type": "codex",
        "harness_version": None,
        "harness_session_id": "real-experiment-attempt-1",
        "previous_report_id": None,
        "previous_report_checksum": None,
        "started_at": DETERMINISTIC_GENERATED_AT,
        "completed_at": DETERMINISTIC_GENERATED_AT,
        "status": "IN_PROGRESS",
        "completed_work": [],
        "current_state": "INPUT_REVIEW",
        "next_recommended_action": "Materialize the exact Idea and stage one exact local package",
        "continuation_reason": None,
        "warnings": ["Trusted owner-staged code only; hostile-code containment is not claimed"],
        "errors": [],
        "unresolved_questions": [],
        "continuation_instructions": ["Use the public Workspace path; never retry automatically"],
    }
    prompt = """# Real Experiment narrow-slice planning

Use only the exact materialized selected Idea, Resource provenance, and plan
context. Derive the minimum scientific requirements, then produce one plan whose
Resource identity, argv, working directory, runtime environment, limits, and
DISABLED network policy exactly copy the readiness context. Declare numeric
metrics with stable names and units. Do not execute code or infer owner approval.
"""
    agent = """# ReAgent Real Experiment — REVIEWED_CORE

This Capsule is the authoritative local state for one exact Workflow Instance.
Use only its verified inputs and owner-staged Experiment Package. Codex derives
requirements and the exact plan; the bundled runner alone obtains checksum-bound
approval, consumes it for one attempt, enforces local no-egress, evaluates the
declared metrics, obtains result review, publishes experiment-record/v2, and
finalizes Progress. Never infer approval, retry automatically, enable network,
read sibling Capsules, or claim hostile-code containment.
"""
    project = {
        "schema_version": "local-project-input/v0.1",
        "project_id": project_id,
        "project_name": project_name,
        "selected_workflow": EXPERIMENT_WORKFLOW_ID,
    }
    skill_root = f"workflow/skills/{skill.skill_id}"
    return {
        "AGENT.md": FileSpec(agent.encode(), "text/markdown", "Real Experiment authority", False, "INSTRUCTION"),
        "AGENTS.md": FileSpec(b"# Codex shim\n\nRead and follow `AGENT.md`.\n", "text/markdown", "Codex shim", False, "INSTRUCTION"),
        "CLAUDE.md": FileSpec(b"# Claude Code shim\n\nRead and follow `AGENT.md`.\n", "text/markdown", "Harness shim", False, "INSTRUCTION"),
        "README.md": FileSpec(b"# Real Experiment Capsule\n\nRun only through the public Local Workspace command.\n", "text/markdown", "Capsule overview", False, "INSTRUCTION"),
        "reagent_local.py": FileSpec(Path(real_experiment_runtime.__file__).read_bytes(), "text/x-python", "bounded local Experiment runner", False, "INSTRUCTION"),
        "validate_package.py": FileSpec(Path(real_experiment_validator.__file__).read_bytes(), "text/x-python", "self-contained Real Experiment validator", False, "INSTRUCTION"),
        "progress_report.py": FileSpec(_scaffold_progress_source(), "text/x-python", "Progress v0.2 exact Artifact helper", False, "INSTRUCTION"),
        "workflow/AGENT.md": FileSpec(b"# Real Experiment Workflow\n\nFollow the root authority and preserve exact evidence identity.\n", "text/markdown", "workflow instructions", False, "INSTRUCTION"),
        "workflow/workflow.json": FileSpec(_json(workflow), "application/json", "pinned Workflow", False, "CONFIGURATION"),
        "workflow/real-experiment.json": FileSpec(_json(contract), "application/json", "narrow execution contract", False, "CONFIGURATION"),
        "workflow/prompts/real-experiment.md": FileSpec(prompt.encode(), "text/markdown", "reviewed planning method", False, "INSTRUCTION"),
        f"{skill_root}/SKILL.md": FileSpec(skill_files["SKILL.md"], "text/markdown", "reviewed provenance Skill", False, "INSTRUCTION"),
        f"{skill_root}/skill.json": FileSpec(skill_files["skill.json"], "application/json", "reviewed provenance Skill contract", False, "CONFIGURATION"),
        "workflow/artifact-inputs.json": FileSpec(_json({"schema_version": "reagent.artifact-input-contract/v0.1", "requirements": workflow["input_requirements"]}), "application/json", "exact Idea input contract", False, "CONFIGURATION"),
        "workflow/artifact-outputs.json": FileSpec(_json({"schema_version": "reagent.artifact-output-contract/v0.1", **scaffold_output_contract(EXPERIMENT_RECORD_V2_TYPE), "producer_core_capability_maturity": "REVIEWED_CORE", "validity_point": "OWNER_REVIEWED_EVIDENCE_BACKED_ATTEMPT"}), "application/json", "experiment-record/v2 output contract", False, "CONFIGURATION"),
        "inputs/project.json": FileSpec(_json(project), "application/json", "immutable Project identity", False, "INPUT"),
        "outputs/README.md": FileSpec(b"# Real Experiment outputs\n\nOnly validated content-addressed experiment-record/v2 files are outputs.\n", "text/markdown", "output policy", False, "OUTPUT"),
        "memory/context.md": FileSpec(("# Real Experiment Context\n\n```json\n" + canonical_json(context) + "\n```\n").encode(), "text/markdown", "cross-session state", True, "STATE"),
        "memory/progress/report-draft.json": FileSpec(_json(draft), "application/json", "mutable Progress draft", True, "STATE"),
        "memory/progress/reports/README.md": FileSpec(b"# Append-only Progress Reports\n", "text/markdown", "Progress policy", False, "STATE"),
        "memory/progress/receipts/README.md": FileSpec(b"# Verified upload receipts\n", "text/markdown", "receipt policy", False, "STATE"),
    }


def _real_experiment_v0_7_validator_source(source: bytes) -> bytes:
    """Derive the immutable 0.7 validator from the historical 0.6 bytes."""

    text = source.decode("utf-8")
    identity = (
        'manifest.get("package_template_version") != "0.6.0"'
    )
    if identity not in text:
        raise RuntimeError("Real Experiment 0.6 identity extension point is unavailable")
    text = text.replace(
        identity,
        'manifest.get("package_template_version") != "0.7.0"',
        1,
    )
    old = '''    for path in root.rglob("*"):
        if path.is_dir():
            if path.is_symlink():
                raise PackageValidationError("Capsule directory link rejected")
            continue
        relative = path.relative_to(root).as_posix()
        if relative == "package-manifest.json" or relative in declared or any(relative.startswith(prefix) for prefix in ALLOWED_DYNAMIC):
            if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
                raise PackageValidationError("Capsule dynamic file is unsafe")
            continue
        raise PackageValidationError(f"undeclared Capsule file: {relative}")
    config = _object(root / "workflow/real-experiment.json", "Real Experiment contract")
    if config.get("schema_version") != "reagent.real-experiment-workflow/v0.1" or config.get("output_artifact_type") != "experiment-record/v2" or config.get("network_policy") != "DISABLED":
        raise PackageValidationError("Real Experiment contract is invalid")
'''
    new = '''    config = _object(root / "workflow/real-experiment.json", "Real Experiment contract")
    if config.get("schema_version") != "reagent.real-experiment-workflow/v0.1" or config.get("output_artifact_type") != "experiment-record/v2" or config.get("network_policy") != "DISABLED":
        raise PackageValidationError("Real Experiment contract is invalid")
    requirements = config.get("input_requirements")
    if not isinstance(requirements, list):
        raise PackageValidationError("Real Experiment Artifact inputs are invalid")
    materialized_inputs = set()
    for requirement in requirements:
        if not isinstance(requirement, dict) or requirement.get("materialization_mode") != "VERIFIED_COPY":
            raise PackageValidationError("Real Experiment Artifact input declaration is invalid")
        target = safe_relative_path(requirement.get("target_relative_path"))
        if not target.startswith("inputs/") or target.endswith("/") or target in materialized_inputs:
            raise PackageValidationError("Real Experiment Artifact input target is invalid")
        materialized_inputs.add(target)
    for path in root.rglob("*"):
        if path.is_dir():
            if path.is_symlink():
                raise PackageValidationError("Capsule directory link rejected")
            continue
        relative = path.relative_to(root).as_posix()
        if relative == "package-manifest.json" or relative in declared or relative in materialized_inputs or any(relative.startswith(prefix) for prefix in ALLOWED_DYNAMIC):
            if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
                raise PackageValidationError("Capsule dynamic file is unsafe")
            continue
        raise PackageValidationError(f"undeclared Capsule file: {relative}")
'''
    if old not in text:
        raise RuntimeError("Real Experiment 0.6 validator extension point is unavailable")
    return text.replace(old, new, 1).encode("utf-8")


def _real_experiment_v0_7_files(**kwargs) -> dict[str, FileSpec]:
    """Render the input-validation bugfix without changing Capsule 0.6."""

    files = dict(_real_experiment_files(**kwargs))
    _replace_spec(
        files,
        "validate_package.py",
        _real_experiment_v0_7_validator_source(
            files["validate_package.py"].content
        ),
    )
    return files


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


def _selected_research_idea_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:reagent:selected-research-idea:v1",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema", "core_capability_maturity", "source_candidate_ideas",
            "source_literature_artifact", "selected_idea",
        ],
        "properties": {
            "schema": {"const": SELECTED_RESEARCH_IDEA_SCHEMA},
            "core_capability_maturity": {"const": "REVIEWED_CORE"},
            "source_candidate_ideas": {"type": "object"},
            "source_literature_artifact": {"type": "object"},
            "selected_idea": {"type": "object"},
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
    elif workflow_id == IDEA_DISCOVERY_WORKFLOW_ID:
        idea_v0_2 = workflow_version == IDEA_DISCOVERY_V0_2_WORKFLOW_VERSION
        idea_skill_version = (
            IDEA_DISCOVERY_V0_2_SKILL_VERSION
            if idea_v0_2 else IDEA_DISCOVERY_SKILL_VERSION
        )
        idea_prompt_version = (
            IDEA_DISCOVERY_V0_2_PROMPT_VERSION
            if idea_v0_2 else IDEA_DISCOVERY_PROMPT_VERSION
        )
        skill_path = "workflow/skills/evidence-grounded-ideation/SKILL.md"
        skill_contract_path = "workflow/skills/evidence-grounded-ideation/skill.json"
        skills = (SkillPin(
            name="reagent.evidence-grounded-ideation",
            semantic_version=idea_skill_version,
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
        prompt_version = idea_prompt_version
        outputs = (
            PackageOutputContract("outputs/candidate_ideas.json", "CANDIDATE_IDEAS", "application/json", "candidate-ideas/v0.1", "Codex Agent Harness", "candidate IDs must resolve to materialized literature"),
            PackageOutputContract("outputs/idea_discovery_report.md", "IDEA_DISCOVERY_REPORT", "text/markdown", "idea-discovery-report/v0.1", "Codex Agent Harness", "evidence/inference/novelty boundary"),
        )
        inputs = (
            PackageInputManifest("local-project-display", "inputs/project.json", sha256_bytes(files["inputs/project.json"].content), True, "application/json", "CLOUD_SUPPLIED"),
        )
        continuation = "MULTI ROUND; append Progress every session; local files, not chat history, preserve continuity"
        proxy = "NO PROVIDER CAPABILITY; LOCAL INTERACTIVE HARNESS ONLY"
    elif (
        workflow_id == EXPERIMENT_WORKFLOW_ID
        and workflow_version == REAL_EXPERIMENT_WORKFLOW_VERSION
    ):
        from backend.project_workspaces.skills import RESEARCH_ARTIFACT_PROVENANCE_SKILL

        asset = RESEARCH_ARTIFACT_PROVENANCE_SKILL
        skill_path = f"workflow/skills/{asset.skill_id}/SKILL.md"
        skills = (SkillPin(
            name=asset.skill_id,
            semantic_version=asset.version,
            source_type="BUNDLED_REAGENT_ORIGINAL",
            source_identity=asset.content_source_identity,
            checksum=asset.content_checksum,
            relative_path=skill_path,
            required_capabilities=asset.required_capabilities,
        ),)
        prompt_path = "workflow/prompts/real-experiment.md"
        prompt_id = "real-experiment-narrow-slice"
        prompt_version = REAL_EXPERIMENT_PROMPT_VERSION
        # The exact content-addressed v2 path is not known until execution.
        # Progress appends the validated memory/current-artifact.json identity.
        outputs = ()
        inputs = (PackageInputManifest(
            "local-project-display", "inputs/project.json",
            sha256_bytes(files["inputs/project.json"].content), True,
            "application/json", "CLOUD_SUPPLIED",
        ),)
        continuation = "ONE ATTEMPT PER EXACT OWNER APPROVAL; NO AUTOMATIC RETRY"
        proxy = "NO NETWORK; OWNER-STAGED TRUSTED PACKAGE; LOCAL FOREGROUND EXECUTION ONLY"
    else:
        config = json.loads(files["workflow/scaffold.json"].content)
        if workflow_version in {
            SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
            EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
        }:
            from backend.project_workspaces.skills import PRODUCTION_SKILLS

            skills = tuple(
                SkillPin(
                    name=asset.skill_id,
                    semantic_version=asset.version,
                    source_type="BUNDLED_REAGENT_ORIGINAL",
                    source_identity=asset.content_source_identity,
                    checksum=asset.content_checksum,
                    relative_path=(
                        f"workflow/skills/{asset.skill_id}/SKILL.md"
                    ),
                    required_capabilities=asset.required_capabilities,
                )
                for asset in PRODUCTION_SKILLS
            )
        else:
            skill_path = "workflow/skills/scaffold-safety/SKILL.md"
            skill_contract_path = "workflow/skills/scaffold-safety/skill.json"
            skills = (SkillPin(
                name="reagent.scaffold-safety",
                semantic_version=SCAFFOLD_SKILL_VERSION,
                source_type="BUNDLED_REAGENT_ORIGINAL",
                source_identity="reagent-f1b-scaffold-safety",
                checksum=canonical_hash({
                    "instructions": sha256_bytes(files[skill_path].content),
                    "contract": sha256_bytes(files[skill_contract_path].content),
                }),
                relative_path=skill_path,
                required_capabilities=(
                    "read_materialized_input", "write_declared_outputs",
                    "append_progress_report", "preserve_scaffold_markers",
                ),
            ),)
        prompt_path = f"workflow/prompts/{config['workflow_slug']}.md"
        prompt_id = f"{config['workflow_slug']}-scaffold"
        prompt_version = (
            (
                EXPERIMENT_RESOURCE_PROMPT_VERSION
                if workflow_version == EXPERIMENT_RESOURCE_WORKFLOW_VERSION
                else SCAFFOLD_SKILL_BACKED_PROMPT_VERSION
            )
            if workflow_version in {
                SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
                EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
            }
            else SCAFFOLD_PROMPT_VERSION
        )
        outputs = (PackageOutputContract(
            config["human_output_path"],
            f"{config['workflow_kind']}_SCAFFOLD_PLACEHOLDER",
            "text/markdown", "scaffold-placeholder/v0.1",
            "Codex or Claude Code Agent Harness",
            "visible scaffold marker; no substantive scientific content",
        ),)
        inputs = (PackageInputManifest(
            "local-project-display", "inputs/project.json",
            sha256_bytes(files["inputs/project.json"].content), True,
            "application/json", "CLOUD_SUPPLIED",
        ),)
        continuation = (
            "MULTI ROUND; append-only Progress and immutable Artifacts; "
            "local memory, not chat history, preserves continuity"
        )
        proxy = "NO PROVIDER OR RESOURCE CAPABILITY; LOCAL SCAFFOLD HARNESS ONLY"
    prompts = (PromptPin(
        prompt_id=prompt_id,
        version=prompt_version,
        checksum=sha256_bytes(files[prompt_path].content),
        relative_path=prompt_path,
        purpose=f"Drive reviewed local {workflow_type} interaction safely.",
    ),)
    file_manifest_checksum = canonical_hash(_normalized_entries(entries))
    required_capabilities = [
        "read_and_write_local_files", "run_local_python_validator",
        "calculate_sha256", "follow_AGENT_md", "launch_codex_cli",
        "progress.upload/v0.2",
    ]
    if workflow_version == REAL_EXPERIMENT_WORKFLOW_VERSION:
        required_capabilities.extend((
            "execute_one_local_foreground_process",
            "enforce_child_no_egress",
        ))
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
        required_harness_capabilities=tuple(required_capabilities),
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


def build_idea_discovery_v0_2_package(
    *, project_id: str, project_name: str, research_topic: str,
    output_root: str | Path, package_id: str,
) -> BuildResult:
    return _build(
        renderer=_idea_v0_2_files,
        project_id=project_id, project_name=project_name,
        research_topic=research_topic, output_root=output_root,
        package_id=package_id, workflow_type="Idea Discovery",
        workflow_id=IDEA_DISCOVERY_WORKFLOW_ID,
        workflow_version=IDEA_DISCOVERY_V0_2_WORKFLOW_VERSION,
        template_id=IDEA_DISCOVERY_TEMPLATE_ID,
        template_version=IDEA_DISCOVERY_V0_2_CAPSULE_VERSION,
    )


def build_idea_discovery_v0_3_package(
    *, project_id: str, project_name: str, research_topic: str,
    output_root: str | Path, package_id: str,
) -> BuildResult:
    return _build(
        renderer=_idea_v0_3_files,
        project_id=project_id, project_name=project_name,
        research_topic=research_topic, output_root=output_root,
        package_id=package_id, workflow_type="Idea Discovery",
        workflow_id=IDEA_DISCOVERY_WORKFLOW_ID,
        workflow_version=IDEA_DISCOVERY_V0_2_WORKFLOW_VERSION,
        template_id=IDEA_DISCOVERY_TEMPLATE_ID,
        template_version=IDEA_DISCOVERY_V0_3_CAPSULE_VERSION,
    )


def _build_scaffold_package(
    *, renderer: Callable[..., dict[str, FileSpec]], workflow_id: str,
    workflow_type: str, template_id: str, project_id: str, project_name: str,
    research_topic: str, output_root: str | Path, package_id: str,
    workflow_version: str = SCAFFOLD_WORKFLOW_VERSION,
    capsule_version: str = SCAFFOLD_CAPSULE_VERSION,
) -> BuildResult:
    return _build(
        renderer=renderer, project_id=project_id, project_name=project_name,
        research_topic=research_topic, output_root=output_root,
        package_id=package_id, workflow_type=workflow_type,
        workflow_id=workflow_id, workflow_version=workflow_version,
        template_id=template_id, template_version=capsule_version,
    )


def build_writing_scaffold_package(**kwargs) -> BuildResult:
    return _build_scaffold_package(
        renderer=_writing_files, workflow_id=WRITING_WORKFLOW_ID,
        workflow_type="Writing", template_id=WRITING_TEMPLATE_ID, **kwargs,
    )


def build_review_scaffold_package(**kwargs) -> BuildResult:
    return _build_scaffold_package(
        renderer=_review_files, workflow_id=REVIEW_WORKFLOW_ID,
        workflow_type="Review", template_id=REVIEW_TEMPLATE_ID, **kwargs,
    )


def build_experiment_scaffold_package(**kwargs) -> BuildResult:
    return _build_scaffold_package(
        renderer=_experiment_files, workflow_id=EXPERIMENT_WORKFLOW_ID,
        workflow_type="Reproduction & Experiment", template_id=EXPERIMENT_TEMPLATE_ID,
        **kwargs,
    )


def build_writing_scaffold_v0_2_package(**kwargs) -> BuildResult:
    return _build_scaffold_package(
        renderer=_writing_v0_2_files, workflow_id=WRITING_WORKFLOW_ID,
        workflow_type="Writing", template_id=WRITING_TEMPLATE_ID,
        workflow_version=SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
        capsule_version=SCAFFOLD_SKILL_BACKED_CAPSULE_VERSION,
        **kwargs,
    )


def build_review_scaffold_v0_2_package(**kwargs) -> BuildResult:
    return _build_scaffold_package(
        renderer=_review_v0_2_files, workflow_id=REVIEW_WORKFLOW_ID,
        workflow_type="Review", template_id=REVIEW_TEMPLATE_ID,
        workflow_version=SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
        capsule_version=SCAFFOLD_SKILL_BACKED_CAPSULE_VERSION,
        **kwargs,
    )


def build_writing_scaffold_v0_3_package(**kwargs) -> BuildResult:
    return _build_scaffold_package(
        renderer=_writing_v0_3_files, workflow_id=WRITING_WORKFLOW_ID,
        workflow_type="Writing", template_id=WRITING_TEMPLATE_ID,
        workflow_version=SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
        capsule_version=SCAFFOLD_INTERACTIVE_CAPSULE_VERSION,
        **kwargs,
    )


def build_review_scaffold_v0_3_package(**kwargs) -> BuildResult:
    return _build_scaffold_package(
        renderer=_review_v0_3_files, workflow_id=REVIEW_WORKFLOW_ID,
        workflow_type="Review", template_id=REVIEW_TEMPLATE_ID,
        workflow_version=SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
        capsule_version=SCAFFOLD_INTERACTIVE_CAPSULE_VERSION,
        **kwargs,
    )


def build_writing_scaffold_v0_4_package(**kwargs) -> BuildResult:
    return _build_scaffold_package(
        renderer=_writing_v0_4_files, workflow_id=WRITING_WORKFLOW_ID,
        workflow_type="Writing", template_id=WRITING_TEMPLATE_ID,
        workflow_version=SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
        capsule_version=SCAFFOLD_COMPLETION_CAPSULE_VERSION,
        **kwargs,
    )


def build_review_scaffold_v0_4_package(**kwargs) -> BuildResult:
    return _build_scaffold_package(
        renderer=_review_v0_4_files, workflow_id=REVIEW_WORKFLOW_ID,
        workflow_type="Review", template_id=REVIEW_TEMPLATE_ID,
        workflow_version=SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
        capsule_version=SCAFFOLD_COMPLETION_CAPSULE_VERSION,
        **kwargs,
    )


def build_experiment_scaffold_v0_2_package(**kwargs) -> BuildResult:
    return _build_scaffold_package(
        renderer=_experiment_v0_2_files, workflow_id=EXPERIMENT_WORKFLOW_ID,
        workflow_type="Reproduction & Experiment", template_id=EXPERIMENT_TEMPLATE_ID,
        workflow_version=SCAFFOLD_SKILL_BACKED_WORKFLOW_VERSION,
        capsule_version=SCAFFOLD_SKILL_BACKED_CAPSULE_VERSION,
        **kwargs,
    )


def build_experiment_scaffold_v0_3_package(**kwargs) -> BuildResult:
    return _build_scaffold_package(
        renderer=_experiment_v0_3_files, workflow_id=EXPERIMENT_WORKFLOW_ID,
        workflow_type="Reproduction & Experiment", template_id=EXPERIMENT_TEMPLATE_ID,
        workflow_version=EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
        capsule_version=EXPERIMENT_RESOURCE_CAPSULE_VERSION,
        **kwargs,
    )


def build_experiment_scaffold_v0_4_package(**kwargs) -> BuildResult:
    return _build_scaffold_package(
        renderer=_experiment_v0_4_files, workflow_id=EXPERIMENT_WORKFLOW_ID,
        workflow_type="Reproduction & Experiment", template_id=EXPERIMENT_TEMPLATE_ID,
        workflow_version=EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
        capsule_version=EXPERIMENT_INTERACTIVE_CAPSULE_VERSION,
        **kwargs,
    )


def build_experiment_scaffold_v0_5_package(**kwargs) -> BuildResult:
    return _build_scaffold_package(
        renderer=_experiment_v0_5_files, workflow_id=EXPERIMENT_WORKFLOW_ID,
        workflow_type="Reproduction & Experiment", template_id=EXPERIMENT_TEMPLATE_ID,
        workflow_version=EXPERIMENT_RESOURCE_WORKFLOW_VERSION,
        capsule_version=EXPERIMENT_COMPLETION_CAPSULE_VERSION,
        **kwargs,
    )


def build_real_experiment_v0_6_package(**kwargs) -> BuildResult:
    return _build_scaffold_package(
        renderer=_real_experiment_files,
        workflow_id=EXPERIMENT_WORKFLOW_ID,
        workflow_type="Reproduction & Experiment",
        template_id=EXPERIMENT_TEMPLATE_ID,
        workflow_version=REAL_EXPERIMENT_WORKFLOW_VERSION,
        capsule_version=REAL_EXPERIMENT_CAPSULE_VERSION,
        **kwargs,
    )


def build_real_experiment_v0_7_package(**kwargs) -> BuildResult:
    return _build_scaffold_package(
        renderer=_real_experiment_v0_7_files,
        workflow_id=EXPERIMENT_WORKFLOW_ID,
        workflow_type="Reproduction & Experiment",
        template_id=EXPERIMENT_TEMPLATE_ID,
        workflow_version=REAL_EXPERIMENT_WORKFLOW_VERSION,
        capsule_version=REAL_EXPERIMENT_BUGFIX_CAPSULE_VERSION,
        **kwargs,
    )


_SELECTED_IDEA_HELPER = r'''

def _build_selected_research_idea(root: Path) -> dict[str, Any]:
    validator = runpy.run_path(str(root / "validate_package.py"))
    library_path = root / "inputs/selected-paper-library.json"
    candidates_path = root / "outputs/candidate_ideas.json"
    for path, label in ((library_path, "literature library"), (candidates_path, "candidate ideas")):
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
            raise ProgressReportError(f"{label} must be one regular unlinked file")
    try:
        source_ids = validator["_validate_selected_library"](library_path)
        validator["_validate_candidate_ideas"](candidates_path, source_ids)
    except Exception as error:
        raise ProgressReportError(f"selected idea validation failed: {error}") from error
    library_bytes = library_path.read_bytes()
    candidate_bytes = candidates_path.read_bytes()
    candidates = _load_object(candidates_path, "candidate ideas")
    source = candidates["source_artifact"]
    if source["artifact_type"] != "selected-paper-library/v1":
        raise ProgressReportError("candidate source has the wrong Artifact type")
    if source["sha256"] != sha256_bytes(library_bytes):
        raise ProgressReportError("candidate source checksum differs from materialized literature")
    selected = [item for item in candidates["ideas"] if item["status"] == "selected"]
    if len(selected) != 1:
        raise ProgressReportError("explicit completion requires exactly one selected candidate idea")
    artifact = {
        "schema": "selected-research-idea/v1",
        "core_capability_maturity": "REVIEWED_CORE",
        "source_candidate_ideas": {
            "schema": "candidate-ideas/v0.1",
            "relative_path": "outputs/candidate_ideas.json",
            "sha256": sha256_bytes(candidate_bytes),
        },
        "source_literature_artifact": dict(source),
        "selected_idea": selected[0],
    }
    content = canonical_json(artifact).encode("utf-8")
    checksum = sha256_bytes(content)
    relative = "outputs/artifacts/selected-research-idea/sha256-" + checksum[7:] + ".json"
    target = root.joinpath(*relative.split("/"))
    current = root
    for part in ("outputs", "artifacts", "selected-research-idea"):
        current = current / part
        if current.exists() or current.is_symlink():
            if current.is_symlink() or not current.is_dir():
                raise ProgressReportError("selected idea Artifact parent is unsafe")
        else:
            current.mkdir()
    try:
        target.parent.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise ProgressReportError("selected idea Artifact path escaped the Capsule") from error
    if target.exists() or target.is_symlink():
        if (
            target.is_symlink() or not target.is_file()
            or target.stat().st_nlink != 1 or target.read_bytes() != content
        ):
            raise ProgressReportError("content-addressed selected idea Artifact conflicts")
    else:
        with tempfile.NamedTemporaryFile(
            prefix=".selected-research-idea.", dir=target.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            if target.exists() or target.is_symlink():
                raise ProgressReportError("selected idea Artifact target appeared during publication")
            os.replace(temporary, target)
            directory = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)
    published = target.read_bytes()
    if published != content or sha256_bytes(published) != checksum:
        raise ProgressReportError("published selected idea Artifact failed reread verification")
    return {
        "relative_path": relative,
        "artifact_kind": "selected-research-idea/v1",
        "media_type": "application/json",
        "checksum": checksum,
        "size": len(content),
    }
'''


_SELECTED_IDEA_VALIDATOR = r'''

def _validate_selected_idea_record(item: Any, source_ids: set[str] | None = None) -> None:
    required = {
        "idea_id", "title", "research_question", "motivation", "literature_basis",
        "observed_gap", "proposed_direction", "assumptions", "risks",
        "validation_needed", "status",
    }
    if not isinstance(item, dict) or set(item) != required:
        raise PackageValidationError("selected idea fields mismatch")
    if not re.fullmatch(r"idea-[0-9]{3,}", str(item["idea_id"])):
        raise PackageValidationError("selected idea identity is invalid")
    if item["status"] != "selected":
        raise PackageValidationError("selected idea must retain selected status")
    for field in (
        "title", "research_question", "motivation", "observed_gap", "proposed_direction",
    ):
        if not isinstance(item[field], str) or not item[field].strip():
            raise PackageValidationError(f"selected idea {field} is required")
    basis = item["literature_basis"]
    if (
        not isinstance(basis, list) or not basis
        or len(basis) != len(set(basis))
        or any(not re.fullmatch(r"candidate-[0-9a-f]{16,64}", str(value)) for value in basis)
        or (source_ids is not None and any(value not in source_ids for value in basis))
    ):
        raise PackageValidationError("selected idea literature basis is invalid")
    for field in ("assumptions", "risks", "validation_needed"):
        if not isinstance(item[field], list) or not all(
            isinstance(value, str) and value.strip() for value in item[field]
        ):
            raise PackageValidationError(f"selected idea {field} is invalid")


def _validate_selected_idea_artifacts(package_root: Path) -> None:
    root = package_root / "outputs/artifacts/selected-research-idea"
    if not root.exists():
        return
    if root.is_symlink() or not root.is_dir():
        raise PackageValidationError("selected idea Artifact root is unsafe")
    library_path = package_root / "inputs/selected-paper-library.json"
    source_ids = _validate_selected_library(library_path) if library_path.exists() else None
    candidates_path = package_root / "outputs/candidate_ideas.json"
    candidate_checksum = (
        sha256_bytes(candidates_path.read_bytes())
        if candidates_path.exists() and not candidates_path.is_symlink()
        and candidates_path.is_file() and candidates_path.stat().st_nlink == 1
        else None
    )
    current_candidates = _object(candidates_path, "candidate ideas") if candidate_checksum else None
    for path in sorted(root.iterdir()):
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
            raise PackageValidationError("selected idea Artifact must be one regular unlinked file")
        content = path.read_bytes()
        if path.name != "sha256-" + sha256_bytes(content)[7:] + ".json":
            raise PackageValidationError("selected idea Artifact content address mismatch")
        value = _object(path, "selected idea Artifact")
        if set(value) != {
            "schema", "core_capability_maturity", "source_candidate_ideas",
            "source_literature_artifact", "selected_idea",
        }:
            raise PackageValidationError("selected idea Artifact fields mismatch")
        if value["schema"] != "selected-research-idea/v1":
            raise PackageValidationError("selected idea Artifact schema mismatch")
        if value["core_capability_maturity"] != "REVIEWED_CORE":
            raise PackageValidationError("selected idea Artifact maturity mismatch")
        candidate_source = value["source_candidate_ideas"]
        if (
            not isinstance(candidate_source, dict)
            or set(candidate_source) != {"schema", "relative_path", "sha256"}
            or candidate_source["schema"] != "candidate-ideas/v0.1"
            or candidate_source["relative_path"] != "outputs/candidate_ideas.json"
            or not SHA256.fullmatch(str(candidate_source["sha256"]))
        ):
            raise PackageValidationError("selected idea candidate provenance mismatch")
        literature = value["source_literature_artifact"]
        if (
            not isinstance(literature, dict)
            or set(literature) != {"artifact_id", "artifact_type", "sha256"}
            or not re.fullmatch(r"artifact-[0-9a-f]{32}", str(literature.get("artifact_id", "")))
            or literature.get("artifact_type") != "selected-paper-library/v1"
            or not SHA256.fullmatch(str(literature.get("sha256", "")))
        ):
            raise PackageValidationError("selected idea literature provenance mismatch")
        _validate_selected_idea_record(value["selected_idea"], source_ids)
        if candidate_checksum == candidate_source["sha256"] and current_candidates is not None:
            selected = [
                item for item in current_candidates["ideas"] if item["status"] == "selected"
            ]
            if len(selected) != 1 or selected[0] != value["selected_idea"]:
                raise PackageValidationError("current selected idea Artifact is not exact")
'''


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
