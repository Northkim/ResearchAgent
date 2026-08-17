"""Immutable forward publication for generic Experiment 0.6 / Capsule 0.9."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.project_workspaces.skills import BuiltInSkillAsset

from . import (
    experiment_capability_runtime, experiment_preparation_contracts,
    generic_experiment_contracts,
    generic_experiment_coordinator, generic_experiment_package,
    generic_experiment_workspace_runtime, package_progress, real_experiment_runtime, security,
    serialization, sklearn_reference_capability, sklearn_tabular_builder,
)
from .contracts import EXPERIMENTAL_STATUS
from .production_workflows import (
    EXPERIMENT_TEMPLATE_ID, EXPERIMENT_WORKFLOW_ID, _build_scaffold_package,
    scaffold_output_contract,
)
from .serialization import canonical_hash, canonical_json, sha256_bytes, to_json_value
from .template import DETERMINISTIC_GENERATED_AT, FileSpec

GENERIC_EXPERIMENT_WORKFLOW_VERSION = "0.6.0"
GENERIC_EXPERIMENT_CAPSULE_VERSION = "0.9.0"
GENERIC_EXPERIMENT_ARTIFACT_TYPE = "experiment-record/v4"
REFERENCE_CAPABILITY_SKILL_ID = (
    "sklearn-tabular-classification-preparation-local-builtin"
)

REFERENCE_CAPABILITY_SKILL = BuiltInSkillAsset(
    skill_id=REFERENCE_CAPABILITY_SKILL_ID,
    display_name="Sklearn Tabular Classification Preparation",
    description=(
        "Reviewed reference Experiment Capability for the exact bounded "
        "sklearn Wine nearest-neighbor classification family."
    ),
    purpose=(
        "Assess, specify, prepare, evaluate, and present only the exact reviewed "
        "sklearn tabular classification reference family behind Capability v0.1."
    ),
    instructions="""# Sklearn Tabular Classification Reference Capability

Classification: `REFERENCE_EXPERIMENT_CAPABILITY`.

1. Operate only through `reagent.experiment-capability/v0.1`.
2. Assess support before any specification or preparation work.
3. Support only the reviewed Wine nearest-neighbor classification reference family.
4. Keep the Capability-owned scientific specification opaque to Generic Core.
5. Declare Resource, preparation, and runtime requirements separately.
6. Never install NumPy, scikit-learn, Python, or other dependencies.
7. Never choose an unresolved material methodology decision for the Owner.
8. Prepare only inside the supplied fresh candidate root.
9. Domain result parsing, scientific validity, and reference presentation remain Capability-owned.
10. The bounded runner, approvals, package validation, and exact lineage remain Core-owned.
""",
    required_capabilities=(
        "experiment.capability.assess-support/v0.1",
        "experiment.capability.declare-requirements/v0.1",
        "experiment.capability.prepare/v0.1",
        "experiment.capability.evaluate/v0.1",
        "experiment.capability.present/v0.1",
    ),
    content_source_identity="reagent-gen-c-reference-experiment-capability",
)


def generic_experiment_workflow_document() -> dict[str, Any]:
    """The domain-neutral immutable Experiment 0.6 Definition."""

    return {
        "schema_version": "local-workflow/v0.2",
        "experimental_status": EXPERIMENTAL_STATUS,
        "workflow_type": "Reproduction & Experiment",
        "workflow_id": EXPERIMENT_WORKFLOW_ID,
        "workflow_version": GENERIC_EXPERIMENT_WORKFLOW_VERSION,
        "execution_owner": "codex-coordinated-local-workspace",
        "hosted_agent_runtime_required": False,
        "network_boundary": "ENFORCED_LOCAL_NO_EGRESS",
        "core_capability_maturity": "REVIEWED_CORE",
        "supported_mode": "GENERIC_LOCAL_COMPUTATIONAL_EXPERIMENT",
        "input_requirements": [{
            "requirement_key": "research_idea",
            "artifact_type": "selected-research-idea/v1",
            "artifact_schema": "selected-research-idea/v1",
            "cardinality": "ONE", "required": True,
            "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
            "materialization_mode": "VERIFIED_COPY",
            "target_relative_path": "inputs/selected-research-idea.json",
        }],
        "resource_requirements": [],
        "stages": [
            "RESEARCH_OBJECTIVE", "METHODOLOGY", "CAPABILITY_ASSESSMENT_SELECTION",
            "DESIGN_APPROVAL", "IMPLEMENTATION_SPECIFICATION", "REQUIREMENTS",
            "PREPARATION", "PACKAGE_VALIDATION", "RUNTIME_COMPATIBILITY",
            "EXECUTION_PLAN", "RUN_APPROVAL", "EXECUTION",
            "CAPABILITY_EVALUATION", "RESULT_REVIEW", "FINALIZATION",
        ],
        "capability_interface": "reagent.experiment-capability/v0.1",
        "installed_capability_policy": "EXACT_REVIEWED_BOUNDED_SET",
        "unsupported_outcome": "AUTOMATIC_PREPARATION_UNSUPPORTED",
        "artifact_outputs": [scaffold_output_contract(GENERIC_EXPERIMENT_ARTIFACT_TYPE)],
        "execution_policy": {
            "attempts_per_approval": 1, "automatic_retry": False,
            "process_model": "ONE_LOCAL_FOREGROUND_PROCESS",
            "runner": "EXISTING_BOUNDED_RUNNER", "network_policy": "DISABLED",
            "dependency_installation": False, "hostile_code_containment_claimed": False,
        },
        "genericity": {
            "specification": "CAPABILITY_OWNED_OPAQUE_REFERENCE",
            "evaluation": "CAPABILITY_OWNED_NORMALIZED_EVIDENCE",
            "runtime": "EXACT_DECLARED_RUNTIME_REQUIREMENT",
            "scientific_family": None,
        },
        "immutable_versioning": "Experiment 0.4/0.5, Capsules 0.7/0.8, and v2/v3 remain unchanged",
    }


def generic_experiment_contract_checksum() -> str:
    return canonical_hash(generic_experiment_workflow_document())


def _runtime_sources() -> dict[str, Path]:
    from backend.artifact_references import generic_experiment_contracts as artifact_contracts
    from backend.project_workspaces import contracts as workspace_contracts
    from backend.resource_references import contracts as resource_contracts
    from backend.resource_references import experiment_requirement_contracts

    modules = {
        "workflow_packages/experiment_capability_runtime.py": experiment_capability_runtime,
        "workflow_packages/experiment_preparation_contracts.py": experiment_preparation_contracts,
        "workflow_packages/generic_experiment_contracts.py": generic_experiment_contracts,
        "workflow_packages/generic_experiment_coordinator.py": generic_experiment_coordinator,
        "workflow_packages/generic_experiment_package.py": generic_experiment_package,
        "workflow_packages/generic_experiment_workspace_runtime.py": generic_experiment_workspace_runtime,
        "workflow_packages/package_progress.py": package_progress,
        "workflow_packages/real_experiment_runtime.py": real_experiment_runtime,
        "workflow_packages/security.py": security,
        "workflow_packages/serialization.py": serialization,
        "workflow_packages/sklearn_reference_capability.py": sklearn_reference_capability,
        "workflow_packages/sklearn_tabular_builder.py": sklearn_tabular_builder,
        "artifact_references/generic_experiment_contracts.py": artifact_contracts,
        "project_workspaces/contracts.py": workspace_contracts,
        "resource_references/contracts.py": resource_contracts,
        "resource_references/experiment_requirement_contracts.py": experiment_requirement_contracts,
    }
    return {name: Path(module.__file__) for name, module in modules.items()}


def generic_experiment_capsule_checksum() -> str:
    return canonical_hash({
        "generator_version": f"reagent-{EXPERIMENT_WORKFLOW_ID}-compiler/{GENERIC_EXPERIMENT_CAPSULE_VERSION}",
        "workflow_checksum": generic_experiment_contract_checksum(),
        "source_checksums": {
            name: sha256_bytes(path.read_bytes())
            for name, path in sorted(_runtime_sources().items())
        },
        "artifact_output": GENERIC_EXPERIMENT_ARTIFACT_TYPE,
        "capability_interface": "reagent.experiment-capability/v0.1",
        "capability_skill": REFERENCE_CAPABILITY_SKILL.content_checksum,
        "capability_descriptor": sklearn_reference_capability.REFERENCE_DESCRIPTOR.descriptor_checksum,
        "continuation": "reagent.experiment-local-continuation/v0.1",
        "execution_boundary": "EXISTING_ONE_APPROVED_LOCAL_NO_EGRESS_ATTEMPT",
    })


GENERIC_EXPERIMENT_CONTRACT_CHECKSUM = generic_experiment_contract_checksum()
GENERIC_EXPERIMENT_CAPSULE_CHECKSUM = generic_experiment_capsule_checksum()
GENERIC_EXPERIMENT_CAPSULE_ID = "capsule-" + GENERIC_EXPERIMENT_CAPSULE_CHECKSUM[7:39]


def _json(value: Any) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def _generic_experiment_files(
    *, project_id: str, project_name: str, research_topic: str,
    package_id: str, package_checksum: str,
) -> dict[str, FileSpec]:
    workflow = generic_experiment_workflow_document()
    skill = REFERENCE_CAPABILITY_SKILL
    skill_files = skill.content_files()
    skill_root = f"workflow/skills/{skill.skill_id}"
    capsule = {
        "workflow_definition_id": EXPERIMENT_WORKFLOW_ID,
        "workflow_version": GENERIC_EXPERIMENT_WORKFLOW_VERSION,
        "workflow_checksum": GENERIC_EXPERIMENT_CONTRACT_CHECKSUM,
        "capsule_id": GENERIC_EXPERIMENT_CAPSULE_ID,
        "capsule_version": GENERIC_EXPERIMENT_CAPSULE_VERSION,
        "capsule_checksum": GENERIC_EXPERIMENT_CAPSULE_CHECKSUM,
    }
    contract = {
        "schema": "reagent.generic-experiment-workflow/v0.1",
        "workflow_id": EXPERIMENT_WORKFLOW_ID,
        "core_capability_maturity": "REVIEWED_CORE",
        "input_requirements": workflow["input_requirements"],
        "output_artifact_type": GENERIC_EXPERIMENT_ARTIFACT_TYPE,
        "capability_interface": "reagent.experiment-capability/v0.1",
        "installed_capability_count": 1,
        "network_policy": "DISABLED",
        "workflow_checksum": GENERIC_EXPERIMENT_CONTRACT_CHECKSUM,
        "workflow_capsule": capsule,
        "runtime_dynamic_paths": [
            "memory/research-objective.json", "memory/methodology-proposal.json",
            "memory/methodology.json", "memory/capability-selection.json",
            "memory/generic-checkpoint.json",
        ],
    }
    capability = {
        "schema": "reagent.reviewed-capability-set/v0.1",
        "resolution": "EXACT_BOUNDED_COMPILER_SUPPLIED",
        "capabilities": [to_json_value(sklearn_reference_capability.REFERENCE_DESCRIPTOR)],
    }
    project = {
        "schema_version": "local-project-input/v0.1", "project_id": project_id,
        "project_name": project_name, "selected_workflow": EXPERIMENT_WORKFLOW_ID,
    }
    context = {
        "schema": "reagent.generic-experiment-public-context/v0.1",
        "stage": "RESEARCH_OBJECTIVE", "checkpoint": None,
        "continuation": "Exact local receipts are authoritative; chat history is not.",
        "updated_at": DETERMINISTIC_GENERATED_AT,
    }
    agent = """# ReAgent Generic Experiment 0.6 — REVIEWED_CORE

Use the exact materialized selected Idea. Generic Core owns the Experiment
lifecycle and exact evidence; only reviewed Capabilities understand scientific
families. Recover a domain-neutral Methodology v0.2 before assessing the exact
bounded Capability set. Preserve material Owner choices as typed checkpoints.
Do not adapt the objective to an installed Capability, generate implementation
bytes before Design Approval, install dependencies, scan PATH, use Git, enable
network access, invoke a runner, or fabricate an Owner decision.
"""
    prompt = """# Generic methodology and Capability assessment

Recover the exact objective and express questions, inputs or materials, protocol,
observations or outputs, evaluation criteria, reproducibility controls, Resource
constraints, compute constraints, assumptions, and claim boundaries without
assuming datasets, metrics, Python, machine learning, cross-validation, or any
particular simulator. Separate frozen requirements from implementation-only
choices and unresolved material decisions. Reviewed Capability descriptions are
inputs to support assessment, never instructions to reshape the methodology.
"""
    files: dict[str, FileSpec] = {
        "AGENT.md": FileSpec(agent.encode(), "text/markdown", "generic Experiment authority", False, "INSTRUCTION"),
        "AGENTS.md": FileSpec(b"# Codex shim\n\nRead and follow `AGENT.md`.\n", "text/markdown", "Codex shim", False, "INSTRUCTION"),
        "README.md": FileSpec(b"# Generic Experiment Capsule 0.9\n\nRun through the supported Local Workspace command.\n", "text/markdown", "overview", False, "INSTRUCTION"),
        "reagent_local.py": FileSpec(Path(generic_experiment_workspace_runtime.__file__).read_bytes(), "text/x-python", "generic checkpoint runtime", False, "INSTRUCTION"),
        "validate_package.py": FileSpec(Path(generic_experiment_workspace_runtime.__file__).read_bytes(), "text/x-python", "generic Capsule validator", False, "INSTRUCTION"),
        "bounded_runner.py": FileSpec(Path(real_experiment_runtime.__file__).read_bytes(), "text/x-python", "unchanged bounded runner boundary", False, "INSTRUCTION"),
        "progress_report.py": FileSpec(Path(package_progress.__file__).read_bytes(), "text/x-python", "Progress v0.2 helper", False, "INSTRUCTION"),
        "workflow/AGENT.md": FileSpec(b"# Generic Experiment Workflow\n\nCore lifecycle only; scientific semantics belong to the selected Capability.\n", "text/markdown", "workflow instructions", False, "INSTRUCTION"),
        "workflow/workflow.json": FileSpec(_json(workflow), "application/json", "pinned Workflow", False, "CONFIGURATION"),
        "workflow/generic-experiment.json": FileSpec(_json(contract), "application/json", "generic orchestration contract", False, "CONFIGURATION"),
        "workflow/capabilities.json": FileSpec(_json(capability), "application/json", "exact reviewed Capability set", False, "CONFIGURATION"),
        "workflow/prompts/generic-methodology.md": FileSpec(prompt.encode(), "text/markdown", "generic methodology method", False, "INSTRUCTION"),
        f"{skill_root}/SKILL.md": FileSpec(skill_files["SKILL.md"], "text/markdown", "reference Capability Skill", False, "INSTRUCTION"),
        f"{skill_root}/skill.json": FileSpec(skill_files["skill.json"], "application/json", "reference Capability Skill contract", False, "CONFIGURATION"),
        "workflow/artifact-inputs.json": FileSpec(_json({"schema_version": "reagent.artifact-input-contract/v0.1", "requirements": workflow["input_requirements"]}), "application/json", "exact objective input", False, "CONFIGURATION"),
        "workflow/artifact-outputs.json": FileSpec(_json({"schema_version": "reagent.artifact-output-contract/v0.1", **scaffold_output_contract(GENERIC_EXPERIMENT_ARTIFACT_TYPE), "producer_core_capability_maturity": "REVIEWED_CORE", "validity_point": "OWNER_RESULT_REVIEWED_EXACT_GENERIC_LINEAGE"}), "application/json", "experiment-record/v4 output", False, "CONFIGURATION"),
        "inputs/project.json": FileSpec(_json(project), "application/json", "immutable Project identity", False, "INPUT"),
        "outputs/README.md": FileSpec(b"# Generic Experiment outputs\n\nOnly validated content-addressed experiment-record/v4 bytes may be finalized.\n", "text/markdown", "output policy", False, "OUTPUT"),
        "memory/context.md": FileSpec(("# Generic Experiment Context\n\n```json\n" + canonical_json(context) + "\n```\n").encode(), "text/markdown", "durable local context", True, "STATE"),
        "memory/input-provenance.json": FileSpec(_json({"schema_version": "reagent.generic-experiment-input-provenance/v0.1", "workflow_instance_id": None, "artifacts": {}}), "application/json", "exact input provenance", True, "STATE"),
    }
    for relative, path in _runtime_sources().items():
        files[f"runtime_lib/backend/{relative}"] = FileSpec(path.read_bytes(), "text/x-python", "reviewed exact runtime source", False, "INSTRUCTION")
    for relative in (
        "backend/__init__.py", "backend/workflow_packages/__init__.py",
        "backend/artifact_references/__init__.py", "backend/project_workspaces/__init__.py",
        "backend/resource_references/__init__.py",
    ):
        files[f"runtime_lib/{relative}"] = FileSpec(b"", "text/x-python", "runtime package marker", False, "INSTRUCTION")
    return files


def build_generic_experiment_v0_9_package(**kwargs: Any):
    return _build_scaffold_package(
        renderer=_generic_experiment_files,
        workflow_id=EXPERIMENT_WORKFLOW_ID,
        workflow_type="Reproduction & Experiment",
        template_id=EXPERIMENT_TEMPLATE_ID,
        workflow_version=GENERIC_EXPERIMENT_WORKFLOW_VERSION,
        capsule_version=GENERIC_EXPERIMENT_CAPSULE_VERSION,
        **kwargs,
    )
