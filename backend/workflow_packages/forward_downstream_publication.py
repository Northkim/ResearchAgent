"""Additive forward Writing/Review/Revision publication over Experiment v5."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from backend.artifact_references import forward_downstream_contracts

from .production_workflows import (
    EXPERIMENT_RECORD_V3_TYPE, REVIEW_TEMPLATE_ID, REVIEW_WORKFLOW_ID,
    SCAFFOLD_INPUT_TARGETS, WRITING_TEMPLATE_ID, WRITING_WORKFLOW_ID,
    _build_scaffold_package, _real_review_files, _real_writing_files,
    _replace_spec, _writing_revision_files, scaffold_output_contract,
)
from .serialization import canonical_hash, canonical_json, sha256_bytes
from .template import FileSpec

INITIAL_WRITING_VERSION = "0.5.0"
INITIAL_WRITING_CAPSULE_VERSION = "0.7.0"
REVIEW_VERSION = "0.4.0"
REVIEW_CAPSULE_VERSION = "0.6.0"
WRITING_REVISION_VERSION = "0.6.0"
WRITING_REVISION_CAPSULE_VERSION = "0.8.0"
EXPERIMENT_V5 = "experiment-record/v5"
MANUSCRIPT_V4 = "manuscript-draft/v4"
REVIEW_V3 = "review-report/v3"
MANUSCRIPT_V5 = "manuscript-draft/v5"


def _requirement(key: str, artifact_type: str, required: bool) -> dict[str, Any]:
    return {
        "requirement_key": key, "artifact_type": artifact_type,
        "artifact_schema": artifact_type, "cardinality": "ONE",
        "required": required, "selection_policy": "EXPLICIT_SPECIFIC_ARTIFACT",
        "materialization_mode": "VERIFIED_COPY",
        "target_relative_path": SCAFFOLD_INPUT_TARGETS[key],
    }


INITIAL_WRITING_REQUIREMENTS = (
    _requirement("research_idea", "selected-research-idea/v1", True),
    _requirement("literature_library", "selected-paper-library/v1", True),
    _requirement("experiment_record", EXPERIMENT_V5, False),
)
REVIEW_REQUIREMENTS = (
    _requirement("manuscript", MANUSCRIPT_V4, True),
    _requirement("research_idea", "selected-research-idea/v1", False),
    _requirement("literature_library", "selected-paper-library/v1", False),
    _requirement("experiment_record", EXPERIMENT_V5, False),
)
REVISION_REQUIREMENTS = (
    _requirement("prior_manuscript", MANUSCRIPT_V4, True),
    _requirement("causal_review", REVIEW_V3, True),
    _requirement("research_idea", "selected-research-idea/v1", True),
    _requirement("literature_library", "selected-paper-library/v1", True),
    _requirement("experiment_record", EXPERIMENT_V5, False),
)


def _workflow(role: str) -> dict[str, Any]:
    if role == "initial-writing":
        return {
            "workflow_type": "Writing", "workflow_id": WRITING_WORKFLOW_ID,
            "workflow_version": INITIAL_WRITING_VERSION,
            "supported_mode": "EVIDENCE_BOUND_INITIAL_DRAFT_V5",
            "input_requirements": list(INITIAL_WRITING_REQUIREMENTS),
            "artifact_outputs": [scaffold_output_contract(MANUSCRIPT_V4)],
            "stages": ["INPUT_REVIEW", "WRITING_BRIEF", "EVIDENCE_MAP", "OUTLINE", "OWNER_APPROVAL", "SECTION_DRAFTING", "CLAIM_CITATION_CHECK", "OWNER_REVIEW", "COMPLETED"],
            "approval_policy": "EXACT_OUTLINE_CHECKSUM_AND_EXACT_DRAFT_REVIEW",
        }
    if role == "review":
        return {
            "workflow_type": "Review", "workflow_id": REVIEW_WORKFLOW_ID,
            "workflow_version": REVIEW_VERSION,
            "supported_mode": "BOUNDED_EVIDENCE_AUDIT_V5",
            "input_requirements": list(REVIEW_REQUIREMENTS),
            "artifact_outputs": [scaffold_output_contract(REVIEW_V3)],
            "stages": ["INPUT_REVIEW", "REVIEW_SCOPE", "CLAIM_EVIDENCE_AUDIT", "METHOD_RESULT_AUDIT", "CITATION_REPRODUCIBILITY_AUDIT", "STRUCTURED_ISSUES", "OWNER_REVIEW", "COMPLETED"],
            "approval_policy": "EXACT_SCOPE_CHECKSUM_AND_EXACT_REVIEW_RESULT",
        }
    return {
        "workflow_type": "Writing", "workflow_id": WRITING_WORKFLOW_ID,
        "workflow_version": WRITING_REVISION_VERSION,
        "supported_mode": "REVIEW_TO_WRITING_REVISION_V5_ROUND_ONE",
        "input_requirements": list(REVISION_REQUIREMENTS),
        "artifact_outputs": [scaffold_output_contract(MANUSCRIPT_V5)],
        "stages": ["INPUT_REVIEW", "ISSUE_RECONCILIATION", "REVISION_PLAN", "OWNER_APPROVAL", "DRAFT_REVISION", "CLAIM_CITATION_RECHECK", "OWNER_REVIEW", "COMPLETED"],
        "approval_policy": "EXACT_REVISION_PLAN_AND_EXACT_REVISED_DRAFT",
    }


def workflow_document(role: str) -> dict[str, Any]:
    return {
        "schema_version": "local-workflow/v0.2", "experimental_status": "EXPERIMENTAL",
        "execution_owner": "codex-coordinated-local-workspace",
        "hosted_agent_runtime_required": False,
        "network_boundary": "NO_WORKFLOW_NETWORK_REQUIRED",
        "core_capability_maturity": "REVIEWED_CORE",
        "evidence_authority": "EXACT_MATERIALIZED_EXPERIMENT_RECORD_V5",
        "presentation_companion_authoritative": False,
        **_workflow(role),
    }


def workflow_checksum(role: str) -> str:
    return canonical_hash(workflow_document(role))


def _replace_function(source: str, name: str, replacement: str) -> str:
    marker = f"\ndef {name}("
    start = source.find(marker)
    if start < 0:
        raise RuntimeError(f"forward source seam {name} is unavailable")
    end = source.find("\ndef ", start + len(marker))
    if end < 0:
        raise RuntimeError(f"forward source seam after {name} is unavailable")
    return source[:start] + "\n" + replacement.strip() + "\n" + source[end:]


def _common_replacements(source: str, role: str) -> str:
    mappings = {
        "initial-writing": [
            ('"0.3.0"', '"0.5.0"'), ('"0.5.0"', '"0.7.0"'),
            ('manuscript-draft/v2', 'manuscript-draft/v4'),
            ('experiment-record/v2', 'experiment-record/v5'),
            ('validate_manuscript_draft_v2', 'validate_manuscript_draft_v4'),
            ('validate_experiment_record_v2', 'validate_experiment_record_v5'),
        ],
        "review": [
            ('"0.3.0"', '"0.4.0"'), ('"0.5.0"', '"0.6.0"'),
            ('review-report/v2', 'review-report/v3'),
            ('manuscript-draft/v2', 'manuscript-draft/v4'),
            ('experiment-record/v2', 'experiment-record/v5'),
            ('validate_review_report_v2', 'validate_review_report_v3'),
        ],
        "revision": [
            ('"0.4.0"', '"0.6.0"'), ('"0.6.0"', '"0.8.0"'),
            ('manuscript-draft/v3', 'manuscript-draft/v5'),
            ('manuscript-draft/v2', 'manuscript-draft/v4'),
            ('review-report/v2', 'review-report/v3'),
            ('experiment-record/v2', 'experiment-record/v5'),
            ('validate_manuscript_draft_v3', 'validate_manuscript_draft_v5'),
            ('validate_experiment_record_v2', 'validate_experiment_record_v5'),
        ],
    }
    # Placeholders prevent a new identity from being rewritten by a later rule.
    placeholders: list[tuple[str, str]] = []
    for index, (old, new) in enumerate(mappings[role]):
        if old not in source:
            continue
        placeholder = f"__REAGENT_FORWARD_IDENTITY_{index}__"
        source = source.replace(old, placeholder)
        placeholders.append((placeholder, new))
    for placeholder, new in placeholders:
        source = source.replace(placeholder, new)
    if role == "initial-writing":
        source = source.replace(
            "with SUCCEEDED\nexecution, VALID evaluation, and SUCCEEDED result may support an observed result.",
            "with SUCCEEDED\nexecution, VALID evaluation, and scientific evidence status "
            "SUPPORTS_BOUNDED_FINDINGS may support an observed result.",
            1,
        )
    elif role == "revision":
        source = source.replace(
            "observed results still require valid experiment-record/v5.",
            "observed results still require a SUCCEEDED process outcome, VALID evaluation, "
            "and SUPPORTS_BOUNDED_FINDINGS scientific evidence status in experiment-record/v5.",
            1,
        )
    return source


def _validator_prelude(source: str) -> str:
    marker = "from typing import Any\n"
    addition = '''from typing import Any
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent / "runtime_lib"))
from backend.artifact_references.forward_downstream_contracts import (
    experiment_evidence_audit, experiment_summary,
    manuscript_surface as _forward_manuscript_surface,
    validate_claims as _forward_validate_claims,
    validate_evidence_refs as _forward_validate_evidence_refs,
    validate_manuscript_draft_v4 as _forward_validate_manuscript_v4,
    validate_manuscript_draft_v5 as _forward_validate_manuscript_v5,
    validate_review_report_v3 as _forward_validate_review_v3,
)
from backend.artifact_references.generic_experiment_v5_contracts import (
    validate_experiment_record_v5 as _forward_validate_experiment_v5,
)
'''
    if marker not in source:
        raise RuntimeError("forward validator import seam is unavailable")
    return source.replace(marker, addition, 1)


def _validator_source(role: str) -> bytes:
    filename = {
        "initial-writing": "real_writing_validator.py",
        "review": "real_review_validator.py",
        "revision": "writing_revision_validator.py",
    }[role]
    source = _common_replacements(Path(__file__).with_name(filename).read_text(), role)
    source = _validator_prelude(source)
    if role in {"initial-writing", "revision"}:
        source = _replace_function(source, "validate_experiment_record_v5", '''
def validate_experiment_record_v5(value: Any) -> dict[str, Any]:
    return _forward_validate_experiment_v5(value)
''')
        source = _replace_function(source, "validate_evidence_refs", '''
def validate_evidence_refs(value: Any, sources: dict[str, Any]) -> list[dict[str, Any]]:
    return _forward_validate_evidence_refs(value, sources)
''')
        source = _replace_function(source, "validate_claims", '''
def validate_claims(value: Any, sources: dict[str, Any], citations: list[dict[str, Any]], experiment: dict[str, Any] | None) -> list[dict[str, Any]]:
    return _forward_validate_claims(value, sources, citations, experiment)
''')
    if role == "initial-writing":
        source = _replace_function(source, "validate_manuscript_draft_v4", '''
def validate_manuscript_draft_v4(value: Any, *, root: Path | None = None) -> dict[str, Any]:
    if root is None:
        return _forward_validate_manuscript_v4(value)
    provenance, sources, _library, experiment = _input_state(root)
    artifact = _forward_validate_manuscript_v4(value, bound_inputs=sources, experiment=experiment)
    if artifact["producer"]["workflow_instance_id"] != provenance["workflow_instance_id"]:
        raise PackageValidationError("Writing producer differs from exact input provenance")
    return artifact
''')
    elif role == "review":
        source = _replace_function(source, "manuscript_surface", '''
def manuscript_surface(value: Any) -> dict[str, Any]:
    return _forward_manuscript_surface(value)
''')
        source = _replace_function(source, "validate_review_report_v3", '''
def validate_review_report_v3(value: Any, *, root: Path) -> dict[str, Any]:
    provenance, sources, values = _input_state(root)
    artifact = _forward_validate_review_v3(
        value, manuscript=values["manuscript"], bound_inputs=sources,
        experiment=values.get("experiment_record"),
    )
    if artifact["producer"]["workflow_instance_id"] != provenance["workflow_instance_id"]:
        raise PackageValidationError("Review producer differs from exact input provenance")
    return artifact
''')
    else:
        source = _replace_function(source, "validate_revision_plan", '''
def validate_revision_plan(value: Any, issues: list[dict[str, Any]], sources: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > 100:
        raise PackageValidationError("Revision Plan must be non-empty and bounded")
    issue_ids = {item.get("issue_id") for item in issues}; seen = set(); result = []
    for raw in value:
        item = _object(raw, "Revision Plan item")
        _exact(item, {"issue_id", "intended_disposition", "planned_change", "affected_section", "affected_claims", "evidence_to_use", "known_limitation"}, "Revision Plan item")
        if item["issue_id"] in seen or item["issue_id"] not in issue_ids or item["intended_disposition"] not in DISPOSITIONS:
            raise PackageValidationError("Revision Plan issue or disposition is invalid")
        seen.add(item["issue_id"]); _text(item["planned_change"], "planned change")
        if item["affected_section"] is None:
            if item["intended_disposition"] != "NOT_ADDRESSED":
                raise PackageValidationError("affected section may be absent only for an unresolved issue")
        else:
            _text(item["affected_section"], "affected section")
        _strings(item["affected_claims"], "affected claims"); validate_evidence_refs(item["evidence_to_use"], sources)
        if item["intended_disposition"] in {"PARTIALLY_ADDRESSED", "NOT_ADDRESSED"}:
            _text(item["known_limitation"], "known limitation")
        elif item["known_limitation"] is not None:
            _text(item["known_limitation"], "known limitation")
        result.append(item)
    if seen != issue_ids:
        raise PackageValidationError("Revision Plan must account for every Review issue")
    return result
''')
        source = _replace_function(source, "validate_manuscript_draft_v5", '''
def validate_manuscript_draft_v5(value: Any, *, root: Path) -> dict[str, Any]:
    provenance, inputs, prior, review, _library, experiment = _input_state(root)
    artifact = _forward_validate_manuscript_v5(
        value, prior_manuscript=prior, causal_review=review,
        bound_inputs=inputs, experiment=experiment,
    )
    if artifact["producer"]["workflow_instance_id"] != provenance["workflow_instance_id"]:
        raise PackageValidationError("Revision producer differs from exact input provenance")
    return artifact
''')
    return source.encode()


def _runtime_source(role: str) -> bytes:
    filename = {
        "initial-writing": "real_writing_runtime.py",
        "review": "real_review_runtime.py",
        "revision": "writing_revision_runtime.py",
    }[role]
    source = _common_replacements(Path(__file__).with_name(filename).read_text(), role)
    if role == "initial-writing":
        source = source.replace(
            'contract = _object(root / "workflow/real-writing.json", "Real Writing contract")\n    artifact = {',
            'contract = _object(root / "workflow/real-writing.json", "Real Writing contract")\n    namespace = _validator(root)\n    _, _, _, exact_experiment = namespace["_input_state"](root)\n    experiment_evidence = namespace["experiment_summary"](None, None) if sources.get("experiment_record") is None else namespace["experiment_summary"](exact_experiment, sources["experiment_record"])\n    artifact = {', 1,
        )
        source = source.replace(
            '"experiment_evidence_available": sources.get("experiment_record") is not None,',
            '"experiment_evidence_available": sources.get("experiment_record") is not None,\n        "experiment_evidence": experiment_evidence,', 1,
        )
        source = source.replace(
            '"Mechanical claim/citation validation does not establish scientific correctness.",',
            '"Mechanical claim/citation validation does not establish scientific correctness.",\n            *(experiment_evidence["limitations"] if experiment_evidence else []),', 1,
        )
        source = source.replace(
            'SUPPORTED prose must stay within exact evidence;',
            'Every claim also records evidence_qualification and claim_boundary_refs. Exact v5 RESULT evidence references include evidence_block_id and evidence_block_checksum. SUPPORTED prose must stay within exact evidence;', 1,
        )
    elif role == "review":
        source = source.replace(
            'result_payload = {\n        "source_manuscript": sources["manuscript"],',
            '_, _, exact_values = namespace["_input_state"](root)\n    audit = namespace["experiment_evidence_audit"](exact_values["manuscript"], exact_values.get("experiment_record"))\n    result_payload = {\n        "source_manuscript": sources["manuscript"],', 1,
        )
        source = source.replace(
            '"evidence_availability": availability,\n        **result,',
            '"evidence_availability": availability,\n        "experiment_evidence_audit": audit,\n        **result,', 1,
        )
        source = source.replace(
            'result, _ = _load_result(root, sources, manuscript)\n    result_payload = {',
            'result, _ = _load_result(root, sources, manuscript)\n    audit = _validator(root)["experiment_evidence_audit"](manuscript, values.get("experiment_record"))\n    result_payload = {', 1,
        )
        source = source.replace(
            '"evidence_availability": availability,\n        **result,',
            '"evidence_availability": availability,\n        "experiment_evidence_audit": audit,\n        **result,', 1,
        )
    else:
        source = source.replace(
            '"experiment_evidence_available": "experiment_record" in sources,',
            '"experiment_evidence_available": "experiment_record" in sources,\n        "experiment_evidence": prior["experiment_evidence"],', 1,
        )
        source = source.replace(
            'SUPPORTED claims require evidence;',
            'Every claim also records evidence_qualification and claim_boundary_refs. Exact v5 RESULT evidence references include evidence_block_id and evidence_block_checksum. SUPPORTED claims require evidence;', 1,
        )
    return source.encode()


def capsule_checksum(role: str) -> str:
    return canonical_hash({
        "generator": f"reagent-forward-downstream/{_capsule_version(role)}",
        "workflow_checksum": workflow_checksum(role),
        "runtime_checksum": sha256_bytes(_runtime_source(role)),
        "validator_checksum": sha256_bytes(_validator_source(role)),
        "contract_checksum": sha256_bytes(Path(forward_downstream_contracts.__file__).read_bytes()),
        "artifact_output": _output(role),
        "evidence_authority": EXPERIMENT_V5,
    })


def capsule_id(role: str) -> str:
    return "capsule-" + capsule_checksum(role)[7:39]


def _capsule_version(role: str) -> str:
    return {"initial-writing": INITIAL_WRITING_CAPSULE_VERSION, "review": REVIEW_CAPSULE_VERSION, "revision": WRITING_REVISION_CAPSULE_VERSION}[role]


def _output(role: str) -> str:
    return {"initial-writing": MANUSCRIPT_V4, "review": REVIEW_V3, "revision": MANUSCRIPT_V5}[role]


def _json(value: Any) -> bytes:
    return (canonical_json(value) + "\n").encode()


def _runtime_lib(files: dict[str, FileSpec]) -> None:
    modules = [
        forward_downstream_contracts,
    ]
    from backend.artifact_references import generic_experiment_contracts, generic_experiment_v5_contracts
    from backend.resource_references import contracts as resource_contracts
    from backend.resource_references import experiment_requirement_contracts
    from . import (
        experiment_capability_runtime, generic_experiment_contracts as core_contracts,
        generic_experiment_package, security, serialization,
    )
    modules.extend([
        generic_experiment_contracts, generic_experiment_v5_contracts,
        resource_contracts, experiment_requirement_contracts, experiment_capability_runtime,
        core_contracts, generic_experiment_package, security, serialization,
    ])
    for module in modules:
        relative = "runtime_lib/" + "/".join(module.__name__.split(".")) + ".py"
        files[relative] = FileSpec(Path(module.__file__).read_bytes(), "text/x-python", "forward exact evidence runtime", False, "INSTRUCTION")
    for package in ("backend", "backend/artifact_references", "backend/resource_references", "backend/workflow_packages"):
        files[f"runtime_lib/{package}/__init__.py"] = FileSpec(b"", "text/x-python", "runtime package marker", False, "INSTRUCTION")


def _files(role: str, base: Callable[..., dict[str, FileSpec]], **kwargs: Any) -> dict[str, FileSpec]:
    files = dict(base(**kwargs))
    workflow = workflow_document(role)
    descriptor_path = {"initial-writing": "workflow/real-writing.json", "review": "workflow/real-review.json", "revision": "workflow/writing-revision.json"}[role]
    descriptor = json.loads(files[descriptor_path].content)
    descriptor.update({
        "workflow_version": workflow["workflow_version"],
        "capsule_id": capsule_id(role), "capsule_version": _capsule_version(role),
        "input_requirements": workflow["input_requirements"],
        "output_artifact_type": _output(role),
        "experiment_evidence_authority": EXPERIMENT_V5,
        "claim_grounding_fields": ["evidence_qualification", "claim_boundary_refs", "evidence_block_id", "evidence_block_checksum"],
    })
    _replace_spec(files, "workflow/workflow.json", _json(workflow))
    _replace_spec(files, descriptor_path, _json(descriptor))
    _replace_spec(files, "workflow/artifact-inputs.json", _json({"schema_version": "reagent.artifact-input-contract/v0.1", "requirements": workflow["input_requirements"]}))
    _replace_spec(files, "workflow/artifact-outputs.json", _json({
        "schema_version": "reagent.artifact-output-contract/v0.1",
        **scaffold_output_contract(_output(role)),
        "producer_core_capability_maturity": "REVIEWED_CORE",
        "validity_point": "OWNER_REVIEWED_EXACT_V5_EVIDENCE_BOUND_OUTPUT",
    }))
    _replace_spec(files, "reagent_local.py", _runtime_source(role))
    _replace_spec(files, "validate_package.py", _validator_source(role))
    _replace_spec(files, "AGENT.md", files["AGENT.md"].content + b"\nThe only Experiment research-evidence authority is the exact materialized experiment-record/v5. Use its bounded evidence block IDs/checksums together with evaluation validity, evidence status, claim boundaries, and limitations. Never read Cloud presentation or sibling Workflow files.\n")
    _runtime_lib(files)
    return files


def build_initial_writing_v0_7_package(**kwargs: Any):
    return _build_scaffold_package(renderer=lambda **values: _files("initial-writing", _real_writing_files, **values), workflow_id=WRITING_WORKFLOW_ID, workflow_type="Writing", template_id=WRITING_TEMPLATE_ID, workflow_version=INITIAL_WRITING_VERSION, capsule_version=INITIAL_WRITING_CAPSULE_VERSION, **kwargs)


def build_review_v0_6_package(**kwargs: Any):
    return _build_scaffold_package(renderer=lambda **values: _files("review", _real_review_files, **values), workflow_id=REVIEW_WORKFLOW_ID, workflow_type="Review", template_id=REVIEW_TEMPLATE_ID, workflow_version=REVIEW_VERSION, capsule_version=REVIEW_CAPSULE_VERSION, **kwargs)


def build_writing_revision_v0_8_package(**kwargs: Any):
    return _build_scaffold_package(renderer=lambda **values: _files("revision", _writing_revision_files, **values), workflow_id=WRITING_WORKFLOW_ID, workflow_type="Writing", template_id=WRITING_TEMPLATE_ID, workflow_version=WRITING_REVISION_VERSION, capsule_version=WRITING_REVISION_CAPSULE_VERSION, **kwargs)


INITIAL_WRITING_CAPSULE_CHECKSUM = capsule_checksum("initial-writing")
INITIAL_WRITING_CAPSULE_ID = capsule_id("initial-writing")
REVIEW_CAPSULE_CHECKSUM = capsule_checksum("review")
REVIEW_CAPSULE_ID = capsule_id("review")
WRITING_REVISION_CAPSULE_CHECKSUM = capsule_checksum("revision")
WRITING_REVISION_CAPSULE_ID = capsule_id("revision")

# The frozen stale reservation is documentation only and must not become runtime authority.
assert EXPERIMENT_RECORD_V3_TYPE == "experiment-record/v3"
