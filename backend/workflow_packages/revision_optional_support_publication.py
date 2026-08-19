"""Additive Writing Revision publication with optional causal-Review support."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.artifact_references import forward_downstream_contracts

from . import forward_downstream_publication as previous
from .production_workflows import (
    WRITING_TEMPLATE_ID,
    WRITING_WORKFLOW_ID,
    _build_scaffold_package,
    _writing_revision_files,
)
from .serialization import canonical_hash, canonical_json, sha256_bytes
from .template import FileSpec

WRITING_REVISION_VERSION = "0.7.0"
WRITING_REVISION_CAPSULE_VERSION = "0.9.0"
WRITING_REVISION_REQUIREMENTS = previous.REVISION_REQUIREMENTS
MANUSCRIPT_V5 = previous.MANUSCRIPT_V5
SUPPORTED_MODE = "REVIEW_TO_WRITING_REVISION_V5_OPTIONAL_REVIEW_SUPPORT"


def workflow_document() -> dict[str, Any]:
    document = previous.workflow_document("revision")
    document["workflow_version"] = WRITING_REVISION_VERSION
    document["supported_mode"] = SUPPORTED_MODE
    return document


def workflow_checksum() -> str:
    return canonical_hash(workflow_document())


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    if source.count(old) != 1:
        raise RuntimeError(f"forward Revision {label} seam is unavailable")
    return source.replace(old, new, 1)


def _contract_source() -> bytes:
    source = Path(forward_downstream_contracts.__file__).read_text()
    old = '''    prior = validate_manuscript_draft_v4(prior_manuscript)
    review = validate_review_report_v3(
        causal_review, manuscript=prior, bound_inputs={
            "manuscript": bound_inputs["prior_manuscript"],
            **{key: bound_inputs[key] for key in ("research_idea", "literature_library", "experiment_record") if key in bound_inputs},
        }, experiment=experiment,
    )
'''
    new = '''    prior = validate_manuscript_draft_v4(prior_manuscript)
    review = validate_review_report_v3(causal_review)
    context = {
        "research_idea": bound_inputs["research_idea"],
        "literature_library": bound_inputs["literature_library"],
        "experiment_record": bound_inputs.get("experiment_record"),
    }
    if prior["source_artifacts"] != context:
        raise ForwardDownstreamContractError("Revision support differs from prior manuscript lineage")
    if artifact_ref(review["source_manuscript"], MANUSCRIPT_DRAFT_V4) != bound_inputs["prior_manuscript"]:
        raise ForwardDownstreamContractError("causal Review refers to a different prior manuscript")
    roles_by_type = {
        "selected-research-idea/v1": "research_idea",
        "selected-paper-library/v1": "literature_library",
        "experiment-record/v5": "experiment_record",
    }
    review_sources = {"manuscript": bound_inputs["prior_manuscript"]}
    seen_review_roles = set()
    for raw in review["supporting_artifacts"]:
        ref = artifact_ref(raw)
        role = roles_by_type.get(ref["artifact_type"])
        if role is None or role in seen_review_roles or context.get(role) != ref:
            raise ForwardDownstreamContractError("causal Review support differs from Revision context")
        seen_review_roles.add(role)
        review_sources[role] = ref
    review_experiment = experiment if "experiment_record" in seen_review_roles else None
    expected_audit = (
        experiment_evidence_audit(prior, experiment)
        if "experiment_record" in seen_review_roles else None
    )
    if review["experiment_evidence_audit"] != expected_audit:
        raise ForwardDownstreamContractError("causal Review Experiment audit exceeds its support scope")
    for issue in review["issues"]:
        validate_evidence_refs(issue.get("evidence_refs"), review_sources, review_experiment)
'''
    return _replace_once(source, old, new, "context validator").encode()


def _validator_source() -> bytes:
    source = previous._validator_source("revision").decode()
    source = _replace_once(
        source,
        'manifest.get("workflow_version") != "0.6.0" or manifest.get("package_template_version") != "0.8.0"',
        'manifest.get("workflow_version") != "0.7.0" or manifest.get("package_template_version") != "0.9.0"',
        "manifest identity",
    )
    old = '''    exact_support = [normalized[key] for key in ("research_idea", "literature_library", "experiment_record") if key in normalized]
    if review.get("supporting_artifacts") != exact_support:
        raise PackageValidationError("causal Review support differs from exact bindings")
'''
    new = '''    roles_by_type = {
        "selected-research-idea/v1": "research_idea",
        "selected-paper-library/v1": "literature_library",
        "experiment-record/v5": "experiment_record",
    }
    review_sources = {"manuscript": normalized["prior_manuscript"]}
    seen_review_roles = set()
    for raw in review.get("supporting_artifacts", []):
        ref = artifact_ref(raw)
        role = roles_by_type.get(ref["artifact_type"])
        if role is None or role in seen_review_roles or normalized.get(role) != ref:
            raise PackageValidationError("causal Review support differs from Revision context")
        seen_review_roles.add(role)
        review_sources[role] = ref
    for issue in issues:
        validate_evidence_refs(issue.get("evidence_refs"), review_sources)
'''
    return _replace_once(source, old, new, "package support validator").encode()


def _runtime_source() -> bytes:
    return previous._runtime_source("revision")


def capsule_checksum() -> str:
    return canonical_hash({
        "generator": f"reagent-forward-downstream/{WRITING_REVISION_CAPSULE_VERSION}",
        "workflow_checksum": workflow_checksum(),
        "runtime_checksum": sha256_bytes(_runtime_source()),
        "validator_checksum": sha256_bytes(_validator_source()),
        "contract_checksum": sha256_bytes(_contract_source()),
        "artifact_output": MANUSCRIPT_V5,
        "evidence_authority": previous.EXPERIMENT_V5,
    })


def capsule_id() -> str:
    return "capsule-" + capsule_checksum()[7:39]


def _json(value: Any) -> bytes:
    return (canonical_json(value) + "\n").encode()


def _files(**kwargs: Any) -> dict[str, FileSpec]:
    files = previous._files("revision", _writing_revision_files, **kwargs)
    workflow = workflow_document()
    descriptor = json.loads(files["workflow/writing-revision.json"].content)
    descriptor.update({
        "workflow_version": WRITING_REVISION_VERSION,
        "capsule_id": capsule_id(),
        "capsule_version": WRITING_REVISION_CAPSULE_VERSION,
    })
    previous._replace_spec(files, "workflow/workflow.json", _json(workflow))
    previous._replace_spec(files, "workflow/writing-revision.json", _json(descriptor))
    previous._replace_spec(files, "validate_package.py", _validator_source())
    previous._replace_spec(
        files,
        "runtime_lib/backend/artifact_references/forward_downstream_contracts.py",
        _contract_source(),
    )
    return files


def build_writing_revision_v0_9_package(**kwargs: Any):
    return _build_scaffold_package(
        renderer=_files,
        workflow_id=WRITING_WORKFLOW_ID,
        workflow_type="Writing",
        template_id=WRITING_TEMPLATE_ID,
        workflow_version=WRITING_REVISION_VERSION,
        capsule_version=WRITING_REVISION_CAPSULE_VERSION,
        **kwargs,
    )


WRITING_REVISION_CAPSULE_CHECKSUM = capsule_checksum()
WRITING_REVISION_CAPSULE_ID = capsule_id()
