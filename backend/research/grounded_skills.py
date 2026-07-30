"""Versioned grounded-report Skills for guided-literature-review@3.0.0."""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from typing import Any, TypeVar

from backend.research.contracts import (
    AccessLimitation,
    ContentType,
    GroundedCitationReference,
    GroundedClaimCategory,
    GroundedClaimV2,
    GroundedEvidenceUnit,
    GroundedReportInput,
    GroundedResearchReport,
    LiteratureCorpus,
    PaperAuthor,
    PaperRecord,
    PerPaperSummary,
    ProviderCategory,
    ProviderFailureCategory,
    ProviderOperation,
    ProviderOperationKind,
    ProviderOperationStatus,
    ProviderUsage,
    SourceContent,
    GROUNDING_DISCLOSURE,
    canonical_hash,
    canonical_json,
    checksum_for_payload,
    sha256_bytes,
)
from backend.research.grounded_prompts import (
    CROSS_PAPER_CLAIMS,
    PAPER_SUMMARY_EVIDENCE,
    REPORT_COMPOSITION,
    MECHANICAL_REPAIR,
    GroundedPrompt,
    GroundedPromptRegistry,
)
from backend.research.ports import (
    ProviderError,
    ProviderIdentity,
    ProviderRequestContext,
    StructuredGenerationRequest,
)
from backend.research.services import (
    BudgetExceededError,
    GroundedProvenanceValidator,
)
from backend.skill_system.exceptions import SkillExecutionFailure
from backend.skill_system.models import SkillDefinition, SkillExecutionContext, SkillMetadata
from backend.skill_system.registry import SkillRegistry
from backend.skill_system.results import EmittedArtifactMetadata, SkillExecutionOutput
from backend.skill_system.schemas import FieldSchema, SkillSchema

_FIXED_TIME = datetime(2026, 7, 30, 9, 0, tzinfo=UTC)
_VERSION = "2.0.0"
_JSON_OBJECT = FieldSchema(kind="object", allow_extra=True)
_JSON_ARRAY = FieldSchema(kind="array", items=_JSON_OBJECT)
_STRING_ARRAY = FieldSchema(kind="array", items=FieldSchema(kind="string"))
_PROMPTS = GroundedPromptRegistry()


def _schema(**fields: FieldSchema) -> SkillSchema:
    return SkillSchema(fields=fields)


def _meta(
    entrypoint: str,
    *,
    capabilities: tuple[str, ...] = (),
    side_effect: str = "none",
) -> SkillMetadata:
    return SkillMetadata(
        capabilities=capabilities,
        side_effect=side_effect,
        idempotency_supported=True,
        retry_safe=True,
        default_timeout_seconds=60,
        implementation_entrypoint=f"builtin:{entrypoint}",
    )


LOAD_APPROVED_SOURCE_CONTENT = SkillDefinition(
    name="research.load_approved_source_content",
    version=_VERSION,
    description="Bind approved synthetic PaperRecords to abstract-only SourceContent.",
    input_schema=_schema(
        selected_papers=_JSON_ARRAY,
        selected_paper_ids=_STRING_ARRAY,
        selected_papers_checksum=FieldSchema(kind="string"),
        approval=_JSON_OBJECT,
    ),
    output_schema=_schema(
        selected_papers=_JSON_ARRAY,
        source_contents=_JSON_ARRAY,
        citations=_JSON_ARRAY,
        citation_label_mapping=_JSON_OBJECT,
        source_content_artifact=_JSON_OBJECT,
    ),
    metadata=_meta(
        "load_approved_source_content",
        capabilities=("artifact_storage",),
        side_effect="write_external",
    ),
)
BUILD_GROUNDED_REPORT_INPUT = SkillDefinition(
    name="research.build_grounded_report_input",
    version=_VERSION,
    description="Construct the exact immutable approved-source generation input.",
    input_schema=_schema(
        query=_JSON_OBJECT,
        query_hash=FieldSchema(kind="string"),
        selected_papers=_JSON_ARRAY,
        selected_paper_ids=_STRING_ARRAY,
        selected_papers_artifact=_JSON_OBJECT,
        selected_papers_checksum=FieldSchema(kind="string"),
        approval=_JSON_OBJECT,
        source_contents=_JSON_ARRAY,
        citation_label_mapping=_JSON_OBJECT,
    ),
    output_schema=_schema(
        grounded_report_input=_JSON_OBJECT,
        grounded_report_input_artifact=_JSON_OBJECT,
    ),
    metadata=_meta(
        "build_grounded_report_input",
        capabilities=("artifact_storage",),
        side_effect="write_external",
    ),
)
SUMMARIZE_PAPERS_AND_EXTRACT_EVIDENCE = SkillDefinition(
    name="research.summarize_papers_and_extract_evidence",
    version=_VERSION,
    description="Generate one validated summary/evidence result per approved paper.",
    input_schema=_schema(
        query=_JSON_OBJECT,
        grounded_report_input=_JSON_OBJECT,
        selected_papers=_JSON_ARRAY,
        source_contents=_JSON_ARRAY,
    ),
    output_schema=_schema(
        paper_summaries=_JSON_ARRAY,
        evidence_units=_JSON_ARRAY,
        provider_operation_ids=_STRING_ARRAY,
        paper_summaries_artifact=_JSON_OBJECT,
        evidence_artifact=_JSON_OBJECT,
    ),
    metadata=_meta(
        "summarize_papers_and_extract_evidence",
        capabilities=(
            "structured_generation",
            "provider_operations",
            "artifact_storage",
        ),
        side_effect="write_external",
    ),
)
SYNTHESIZE_GROUNDED_CLAIMS = SkillDefinition(
    name="research.synthesize_grounded_claims",
    version=_VERSION,
    description="Generate and deterministically validate cross-paper grounded claims.",
    input_schema=_schema(
        query=_JSON_OBJECT,
        grounded_report_input=_JSON_OBJECT,
        paper_summaries=_JSON_ARRAY,
        evidence_units=_JSON_ARRAY,
    ),
    output_schema=_schema(
        grounded_claims=_JSON_ARRAY,
        evidence_units=_JSON_ARRAY,
        provider_operation_ids=_STRING_ARRAY,
        claims_artifact=_JSON_OBJECT,
    ),
    metadata=_meta(
        "synthesize_grounded_claims",
        capabilities=(
            "structured_generation",
            "provider_operations",
            "artifact_storage",
        ),
        side_effect="write_external",
    ),
)
COMPOSE_GROUNDED_REPORT = SkillDefinition(
    name="research.compose_grounded_report",
    version=_VERSION,
    description="Compose a structured citation-aware report and deterministic Markdown.",
    input_schema=_schema(
        query=_JSON_OBJECT,
        grounded_report_input=_JSON_OBJECT,
        selected_papers=_JSON_ARRAY,
        paper_summaries=_JSON_ARRAY,
        evidence_units=_JSON_ARRAY,
        grounded_claims=_JSON_ARRAY,
        citations=_JSON_ARRAY,
    ),
    output_schema=_schema(
        report=_JSON_OBJECT,
        provider_operation_ids=_STRING_ARRAY,
    ),
    metadata=_meta(
        "compose_grounded_report",
        capabilities=("structured_generation", "provider_operations", "artifact_storage"),
        side_effect="write_external",
    ),
)
VALIDATE_GROUNDED_PROVENANCE = SkillDefinition(
    name="research.validate_grounded_provenance",
    version=_VERSION,
    description="Run the blocking grounded-report publication gate.",
    input_schema=_schema(
        grounded_report_input=_JSON_OBJECT,
        source_contents=_JSON_ARRAY,
        paper_summaries=_JSON_ARRAY,
        evidence_units=_JSON_ARRAY,
        grounded_claims=_JSON_ARRAY,
        report=_JSON_OBJECT,
    ),
    output_schema=_schema(validation=_JSON_OBJECT),
    metadata=_meta(
        "validate_grounded_provenance",
        capabilities=("provider_operations",),
    ),
)
PERSIST_GROUNDED_ARTIFACTS = SkillDefinition(
    name="research.persist_grounded_artifacts",
    version=_VERSION,
    description="Publish report/provenance/corpus artifacts only after validation.",
    input_schema=_schema(
        query=_JSON_OBJECT,
        papers=_JSON_ARRAY,
        selected_papers=_JSON_ARRAY,
        source_contents=_JSON_ARRAY,
        grounded_report_input=_JSON_OBJECT,
        paper_summaries=_JSON_ARRAY,
        evidence_units=_JSON_ARRAY,
        grounded_claims=_JSON_ARRAY,
        citations=_JSON_ARRAY,
        report=_JSON_OBJECT,
        validation=_JSON_OBJECT,
        workflow_hash=FieldSchema(kind="string"),
    ),
    output_schema=_schema(
        report_artifact=_JSON_OBJECT,
        provenance_artifact=_JSON_OBJECT,
        usage_artifact=_JSON_OBJECT,
        literature_corpus_artifact=_JSON_OBJECT,
        generation_manifest_artifact=_JSON_OBJECT,
        publication=_JSON_OBJECT,
    ),
    metadata=_meta(
        "persist_grounded_artifacts",
        capabilities=("artifact_storage", "provider_operations"),
        side_effect="write_external",
    ),
)

GROUNDED_SKILL_DEFINITIONS = (
    LOAD_APPROVED_SOURCE_CONTENT,
    BUILD_GROUNDED_REPORT_INPUT,
    SUMMARIZE_PAPERS_AND_EXTRACT_EVIDENCE,
    SYNTHESIZE_GROUNDED_CLAIMS,
    COMPOSE_GROUNDED_REPORT,
    VALIDATE_GROUNDED_PROVENANCE,
    PERSIST_GROUNDED_ARTIFACTS,
)


def _json_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def _stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}_{canonical_hash(value)[7:39]}"


def _paper(value: Mapping[str, Any]) -> PaperRecord:
    return PaperRecord(
        paper_id=str(value["paper_id"]),
        provider_id=str(value["provider_id"]),
        title=str(value["title"]),
        authors=tuple(PaperAuthor(**item) for item in value["authors"]),
        abstract=value.get("abstract"),
        publication_year=value.get("publication_year"),
        publication_venue=value.get("publication_venue"),
        source_provider=str(value["source_provider"]),
        source_url=value.get("source_url"),
        doi=value.get("doi"),
        retrieved_at=datetime.fromisoformat(str(value["retrieved_at"])),
        raw_metadata_hash=str(value["raw_metadata_hash"]),
        language=value.get("language"),
        normalized_metadata_version=str(
            value.get("normalized_metadata_version", "paper-normalization/v1")
        ),
        metadata_limitations=tuple(value.get("metadata_limitations", ())),
        schema_version=str(value.get("schema_version", "paper-record/v1")),
    )


def _source(value: Mapping[str, Any]) -> tuple[str, SourceContent]:
    source = SourceContent(
        paper_id=str(value["paper_id"]),
        content_type=ContentType(str(value["content_type"])),
        abstract=value.get("abstract"),
        full_text=value.get("full_text"),
        content_source=str(value["content_source"]),
        source_url=value.get("source_url"),
        retrieved_at=datetime.fromisoformat(str(value["retrieved_at"])),
        content_hash=str(value["content_hash"]),
        access_limitation=AccessLimitation(str(value["access_limitation"])),
        license_or_usage_metadata=value.get("license_or_usage_metadata"),
        source_locations=tuple(value.get("source_locations", ())),
        schema_version=str(value.get("schema_version", "source-content/v1")),
    )
    return str(value["source_content_id"]), source


def _report_input(value: Mapping[str, Any]) -> GroundedReportInput:
    return GroundedReportInput(
        project_id=str(value["project_id"]),
        workflow_run_id=str(value["workflow_run_id"]),
        workflow_id=str(value["workflow_id"]),
        workflow_version=str(value["workflow_version"]),
        selected_paper_artifact_id=str(value["selected_paper_artifact_id"]),
        selected_paper_artifact_checksum=str(
            value["selected_paper_artifact_checksum"]
        ),
        approval_request_id=str(value["approval_request_id"]),
        approval_fingerprint=str(value["approval_fingerprint"]),
        query_hash=str(value["query_hash"]),
        ordered_paper_ids=tuple(value["ordered_paper_ids"]),
        ordered_source_content_ids=tuple(value["ordered_source_content_ids"]),
        source_content_checksums=value["source_content_checksums"],
        citation_label_mapping=value["citation_label_mapping"],
        content_scope=str(value["content_scope"]),
        prompt_policy=value["prompt_policy"],
        provider_policy=value["provider_policy"],
        budget_policy=value["budget_policy"],
        schema_version=str(value["schema_version"]),
        input_checksum=str(value["input_checksum"]),
    )


def _contract_payload(cls, payload: Mapping[str, Any], checksum_field: str = "checksum"):
    full = dict(payload)
    full[checksum_field] = checksum_for_payload(full, checksum_field)
    return cls(**full)


def _artifact(
    context: SkillExecutionContext,
    *,
    logical_name: str,
    kind: str,
    media_type: str,
    content: bytes,
    metadata: Mapping[str, Any] | None = None,
) -> EmittedArtifactMetadata:
    storage = context.capabilities.require_artifact_storage()
    artifact_id = _stable_id(
        "artifact",
        {"run": context.workflow_run_id, "name": logical_name, "version": 1},
    )
    extension = "md" if logical_name.endswith(".md") else "json"
    storage_key = (
        f"runs/{_stable_id('run', context.workflow_run_id)}/"
        f"{artifact_id}/v1/{logical_name.rsplit('.', 1)[0]}.{extension}"
    )
    stored = storage.write_immutable(storage_key, content, media_type=media_type)
    verified = storage.verify(
        stored.storage_key,
        expected_checksum=stored.checksum,
        expected_size=stored.size,
    )
    if not verified.valid:
        raise SkillExecutionFailure(
            "ARTIFACT_CHECKSUM_MISMATCH",
            f"Artifact {logical_name} failed verification",
        )
    return EmittedArtifactMetadata(
        artifact_id=artifact_id,
        logical_artifact_id=f"{context.workflow_run_id}:{logical_name}",
        logical_name=logical_name,
        kind=kind,
        version=1,
        storage_key=stored.storage_key,
        checksum=stored.checksum,
        media_type=stored.media_type,
        size=stored.size,
        metadata={
            "immutable": True,
            "content_scope": "abstract_only",
            "schema_version": metadata.get("schema_version", "artifact/v1")
            if metadata
            else "artifact/v1",
            **(metadata or {}),
        },
    )


def _artifact_view(item: EmittedArtifactMetadata) -> dict[str, Any]:
    return {
        "artifact_id": item.artifact_id,
        "logical_name": item.logical_name,
        "checksum": item.checksum,
        "media_type": item.media_type,
        "size": item.size,
    }


T = TypeVar("T")


async def _generation_call(
    context: SkillExecutionContext,
    *,
    operation_kind: ProviderOperationKind,
    logical_call: str,
    prompt: GroundedPrompt,
    payload: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ProviderUsage, str]:
    provider = context.capabilities.require_structured_generation()
    service = context.capabilities.require_provider_operations()
    policy = context.capabilities.provider_execution_policy
    identity = provider.identity
    if identity.provider in policy.live_provider_names:
        raise SkillExecutionFailure(
            "LIVE_PROVIDER_PROHIBITED",
            "Phase 9C-1 permits synthetic structured providers only",
        )
    input_checksum = canonical_hash(payload)
    request_document = {
        "operation_kind": operation_kind.value,
        "model": identity.model_or_endpoint,
        "adapter": identity.adapter_version,
        "prompt_version": f"{prompt.prompt_id}@{prompt.version}",
        "prompt_hash": prompt.prompt_hash,
        "input_checksum": input_checksum,
        "schema_version": "structured-generation-request/v1",
    }
    fingerprint = canonical_hash(request_document)
    existing_matches = tuple(
        item
        for item in service.list_for_run(
            project_id=context.project_id,
            workflow_run_id=context.workflow_run_id,
        )
        if item.logical_step_id == context.step_id
        and item.operation_kind is operation_kind
        and item.provider_identity == identity.provider
        and item.adapter_version == identity.adapter_version
        and item.model_or_endpoint == identity.model_or_endpoint
        and item.request_fingerprint == fingerprint
    )
    unsettled = tuple(
        item
        for item in existing_matches
        if item.status in {
            ProviderOperationStatus.RESERVED,
            ProviderOperationStatus.RUNNING,
        }
    )
    if unsettled:
        raise SkillExecutionFailure(
            "UNSETTLED_PROVIDER_OPERATION",
            "An existing generation attempt is not safely duplicable",
        )
    succeeded = tuple(
        item
        for item in existing_matches
        if item.status is ProviderOperationStatus.SUCCEEDED
    )
    if succeeded:
        prior = sorted(succeeded, key=lambda item: (item.created_at, item.id))[0]
        checkpoint_key = (
            f"runs/{_stable_id('run', context.workflow_run_id)}/private-generation/"
            f"{prior.id}.json"
        )
        storage = context.capabilities.require_artifact_storage()
        try:
            checkpoint = json.loads(storage.read(checkpoint_key))
        except (FileNotFoundError, json.JSONDecodeError) as error:
            raise SkillExecutionFailure(
                "SETTLED_OUTPUT_CHECKPOINT_MISSING",
                "Settled generation output has no verified private checkpoint",
            ) from error
        if checkpoint.get("operation_id") != prior.id or prior.actual_usage is None:
            raise SkillExecutionFailure(
                "GENERATION_CHECKPOINT_MISMATCH",
                "Generation checkpoint identity or usage changed",
            )
        return checkpoint["value"], prior.actual_usage, prior.id
    idempotency_key = (
        f"fake:{context.workflow_run_id}:{context.step_id}:{logical_call}:"
        f"attempt-{context.attempt}:{fingerprint}"
    )
    operation_id = _stable_id(
        "provider_op", {"project": context.project_id, "key": idempotency_key}
    )
    operation = ProviderOperation(
        id=operation_id,
        project_id=context.project_id,
        workflow_run_id=context.workflow_run_id,
        logical_step_id=context.step_id,
        step_run_id=context.step_run_id,
        provider_category=ProviderCategory.LLM,
        operation_kind=operation_kind,
        provider_identity=identity.provider,
        adapter_version=identity.adapter_version,
        model_or_endpoint=identity.model_or_endpoint,
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
        reservation=policy.reservation_for(identity.provider),
        is_live_provider=False,
        created_at=_FIXED_TIME,
        updated_at=_FIXED_TIME,
    )
    try:
        reserved, replay = service.reserve(operation, budget=policy.budget)
    except BudgetExceededError as error:
        raise SkillExecutionFailure(
            "BUDGET_EXCEEDED",
            str(error),
            details={"dimension": error.dimension},
        ) from error
    checkpoint_key = (
        f"runs/{_stable_id('run', context.workflow_run_id)}/private-generation/"
        f"{operation_id}.json"
    )
    storage = context.capabilities.require_artifact_storage()
    if replay:
        if reserved.status is not ProviderOperationStatus.SUCCEEDED:
            raise SkillExecutionFailure(
                "UNSETTLED_PROVIDER_OPERATION",
                "An existing generation reservation is not safely replayable",
            )
        try:
            checkpoint = json.loads(storage.read(checkpoint_key))
        except (FileNotFoundError, json.JSONDecodeError) as error:
            raise SkillExecutionFailure(
                "SETTLED_OUTPUT_CHECKPOINT_MISSING",
                "Settled generation output has no verified private checkpoint",
            ) from error
        if checkpoint.get("operation_id") != operation_id:
            raise SkillExecutionFailure(
                "GENERATION_CHECKPOINT_MISMATCH",
                "Generation checkpoint identity changed",
            )
        assert reserved.actual_usage is not None
        return checkpoint["value"], reserved.actual_usage, operation_id
    service.commit_staged()
    service.mark_running(operation_id, at=_FIXED_TIME)
    service.commit_staged()
    request = StructuredGenerationRequest(
        operation_kind=operation_kind.value,
        model_policy={
            "provider": identity.provider,
            "model": identity.model_or_endpoint,
            "no_fallback": True,
        },
        prompt_version=f"{prompt.prompt_id}@{prompt.version}",
        prompt_hash=prompt.prompt_hash,
        system_instruction=prompt.system_instruction,
        untrusted_data_payload=payload,
        structured_output_schema={
            "type": "object",
            "additionalProperties": True,
        },
        maximum_output_tokens=4_000,
        timeout_seconds=policy.operation_timeout_seconds,
        request_fingerprint=fingerprint,
        input_checksum=input_checksum,
        schema_version="structured-generation-request/v1",
    )
    provider_context = ProviderRequestContext(
        operation_id=operation_id,
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
    )
    try:
        result = await provider.generate(request, context=provider_context)
    except ProviderError as error:
        service.settle_failure(
            operation_id,
            category=error.category,
            at=_FIXED_TIME,
            usage=None,
            provider_call_started=True,
            diagnostic_metadata={
                "retryable": error.retryable,
                "safe_details": dict(error.safe_details),
            },
        )
        service.commit_staged()
        raise SkillExecutionFailure(
            error.category.value,
            str(error),
            retryable=error.retryable,
        ) from error
    if (
        result.provider_identity != identity.provider
        or result.model_identity != identity.model_or_endpoint
        or result.adapter_version != identity.adapter_version
        or result.response_checksum != canonical_hash(result.normalized_value)
    ):
        service.settle_failure(
            operation_id,
            category=ProviderFailureCategory.SCHEMA_VALIDATION,
            at=_FIXED_TIME,
            usage=None,
            provider_call_started=True,
            diagnostic_metadata={"identity_or_checksum_mismatch": True},
        )
        service.commit_staged()
        raise SkillExecutionFailure(
            "PROVIDER_IDENTITY_OR_CHECKSUM_MISMATCH",
            "Structured provider result identity or checksum changed",
        )
    usage = ProviderUsage(
        provider=identity.provider,
        model_or_endpoint=identity.model_or_endpoint,
        operation_kind=operation_kind,
        request_count=result.usage.request_count,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
        estimated_cost_minor_units=result.usage.estimated_cost_minor_units,
        cost_currency=result.usage.cost_currency,
        latency_ms=result.usage.latency_ms,
        retry_count=result.usage.retry_count,
        provider_request_ids=result.usage.provider_request_ids,
    )
    service.settle_success(operation_id, usage=usage, at=_FIXED_TIME)
    service.commit_staged()
    checkpoint_content = _json_bytes(
        {
            "schema_version": "private-generation-checkpoint/v1",
            "operation_id": operation_id,
            "response_checksum": result.response_checksum,
            "value": result.normalized_value,
        }
    )
    storage.write_immutable(
        checkpoint_key, checkpoint_content, media_type="application/json"
    )
    return result.normalized_value, usage, operation_id


async def _repair_structure_once(
    context: SkillExecutionContext,
    *,
    original_value: Mapping[str, Any],
    missing_fields: tuple[str, ...],
    target_fixture_key: str,
    target_schema: str,
) -> tuple[Mapping[str, Any], ProviderUsage, str]:
    operations = context.capabilities.require_provider_operations().list_for_run(
        project_id=context.project_id,
        workflow_run_id=context.workflow_run_id,
    )
    if any(
        item.operation_kind is ProviderOperationKind.MECHANICAL_REPAIR
        for item in operations
    ):
        raise SkillExecutionFailure(
            "REPAIR_LIMIT_EXCEEDED",
            "Only one mechanical repair operation is permitted per V3 run",
        )
    return await _generation_call(
        context,
        operation_kind=ProviderOperationKind.MECHANICAL_REPAIR,
        logical_call="single-mechanical-repair",
        prompt=MECHANICAL_REPAIR,
        payload={
            "fixture_key": target_fixture_key,
            "invalid_output_checksum": canonical_hash(original_value),
            "safe_validation_errors": [
                {"code": "MISSING_REQUIRED_FIELD", "field": field_name}
                for field_name in missing_fields
            ],
            "target_schema": target_schema,
            "prohibited_changes": (
                "new_evidence",
                "new_claim",
                "new_paper",
                "new_citation",
            ),
        },
    )


async def _require_structure_or_repair(
    context: SkillExecutionContext,
    *,
    value: Mapping[str, Any],
    required_fields: tuple[str, ...],
    target_fixture_key: str,
    target_schema: str,
) -> tuple[Mapping[str, Any], tuple[ProviderUsage, ...], tuple[str, ...]]:
    missing = tuple(field_name for field_name in required_fields if field_name not in value)
    if not missing:
        return value, (), ()
    repaired, usage, operation_id = await _repair_structure_once(
        context,
        original_value=value,
        missing_fields=missing,
        target_fixture_key=target_fixture_key,
        target_schema=target_schema,
    )
    still_missing = tuple(
        field_name for field_name in required_fields if field_name not in repaired
    )
    if still_missing:
        raise SkillExecutionFailure(
            "REPAIR_FAILED",
            "Mechanical repair did not produce the required structure",
            details={"missing_fields": still_missing},
        )
    return repaired, (usage,), (operation_id,)


async def load_approved_source_content(
    inputs: Mapping[str, Any],
    context: SkillExecutionContext,
) -> SkillExecutionOutput:
    papers = tuple(_paper(item) for item in inputs["selected_papers"])
    ordered_ids = tuple(str(item) for item in inputs["selected_paper_ids"])
    approval = inputs["approval"]
    if tuple(item.paper_id for item in papers) != ordered_ids or not 3 <= len(papers) <= 5:
        raise SkillExecutionFailure(
            "APPROVED_PAPER_SET_MISMATCH",
            "The approved ordered paper set must contain three to five papers",
        )
    if approval.get("approval_status") != "APPROVED":
        raise SkillExecutionFailure("MISSING_APPROVAL", "Approved status is required")
    dois = [item.doi for item in papers if item.doi]
    provider_ids = [item.provider_id for item in papers]
    if len(set(dois)) != len(dois):
        raise SkillExecutionFailure("DUPLICATE_DOI", "Duplicate DOI in approved set")
    if len(set(provider_ids)) != len(provider_ids):
        raise SkillExecutionFailure(
            "DUPLICATE_PROVIDER_ID", "Duplicate provider identity in approved set"
        )
    source_values = []
    citations = []
    label_mapping = {}
    for index, paper in enumerate(papers, 1):
        if not paper.abstract:
            raise SkillExecutionFailure(
                "MISSING_APPROVED_ABSTRACT",
                f"Approved paper {paper.paper_id} has no abstract",
            )
        label = f"[P{index}]"
        source_id = _stable_id(
            "source_content",
            {"paper_id": paper.paper_id, "abstract": paper.abstract},
        )
        source = SourceContent(
            paper_id=paper.paper_id,
            content_type=ContentType.ABSTRACT,
            abstract=paper.abstract,
            full_text=None,
            content_source="approved-paper-record-abstract/v1",
            source_url=paper.source_url,
            retrieved_at=paper.retrieved_at,
            content_hash=sha256_bytes(paper.abstract.encode("utf-8")),
            access_limitation=AccessLimitation.ABSTRACT_ONLY,
            license_or_usage_metadata={
                "synthetic_fixture": True,
                "scope": "abstract_only",
            },
        )
        source_values.append({"source_content_id": source_id, **source.to_dict()})
        label_mapping[paper.paper_id] = label
        citation_payload = {
            "citation_label": label,
            "paper_id": paper.paper_id,
            "title": paper.title,
            "year": paper.publication_year,
            "venue": paper.publication_venue,
            "doi": paper.doi,
            "source_url": paper.source_url,
            "source_checksum": paper.raw_metadata_hash,
            "schema_version": "grounded-citation-reference/v2",
        }
        citations.append(
            _contract_payload(GroundedCitationReference, citation_payload).to_dict()
        )
    document = {
        "schema_version": "grounded-source-content-artifact/v1",
        "content_scope": "abstract_only",
        "selected_papers_checksum": inputs["selected_papers_checksum"],
        "sources": source_values,
    }
    artifact = _artifact(
        context,
        logical_name="source_content.json",
        kind="research.source_content",
        media_type="application/json",
        content=_json_bytes(document),
        metadata={"schema_version": document["schema_version"], "paper_count": len(papers)},
    )
    return SkillExecutionOutput(
        output_data={
            "selected_papers": [item.to_dict() for item in papers],
            "source_contents": source_values,
            "citations": citations,
            "citation_label_mapping": label_mapping,
            "source_content_artifact": _artifact_view(artifact),
        },
        emitted_artifacts=(artifact,),
    )


async def build_grounded_report_input(
    inputs: Mapping[str, Any],
    context: SkillExecutionContext,
) -> SkillExecutionOutput:
    papers = tuple(_paper(item) for item in inputs["selected_papers"])
    ordered_ids = tuple(str(item) for item in inputs["selected_paper_ids"])
    source_pairs = tuple(_source(item) for item in inputs["source_contents"])
    approval = inputs["approval"]
    selected_artifact = inputs["selected_papers_artifact"]
    if tuple(item.paper_id for item in papers) != ordered_ids:
        raise SkillExecutionFailure(
            "APPROVED_PAPER_ORDER_MISMATCH", "Approved paper order changed"
        )
    if selected_artifact.get("checksum") != inputs["selected_papers_checksum"]:
        raise SkillExecutionFailure(
            "SELECTED_ARTIFACT_CHECKSUM_MISMATCH",
            "Selected-paper artifact checksum changed",
        )
    payload = {
        "project_id": context.project_id,
        "workflow_run_id": context.workflow_run_id,
        "workflow_id": context.workflow_id,
        "workflow_version": context.workflow_version,
        "selected_paper_artifact_id": selected_artifact["artifact_id"],
        "selected_paper_artifact_checksum": inputs["selected_papers_checksum"],
        "approval_request_id": approval["approval_request_id"],
        "approval_fingerprint": approval["approval_fingerprint"],
        "query_hash": inputs["query_hash"],
        "ordered_paper_ids": ordered_ids,
        "ordered_source_content_ids": tuple(item[0] for item in source_pairs),
        "source_content_checksums": {
            source_id: source.content_hash for source_id, source in source_pairs
        },
        "citation_label_mapping": inputs["citation_label_mapping"],
        "content_scope": "abstract_only",
        "prompt_policy": _PROMPTS.manifest(),
        "provider_policy": {
            "provider": "synthetic-grounded-generation",
            "model": "fixture-driven-grounding/v1",
            "adapter_target": "anthropic/claude-sonnet-5",
            "fallback": "prohibited",
        },
        "budget_policy": {
            "maximum_logical_operations": 8,
            "maximum_attempts": 11,
            "maximum_input_tokens": 90_000,
            "maximum_output_tokens": 32_000,
            "maximum_cost_minor_units": 125,
            "currency": "USD",
            "authorized_real_spend_minor_units": 0,
            "maximum_repair_operations": 1,
        },
        "schema_version": "grounded-report-input/v1",
    }
    report_input = _contract_payload(
        GroundedReportInput, payload, checksum_field="input_checksum"
    )
    artifact = _artifact(
        context,
        logical_name="grounded_report_input.json",
        kind="research.grounded_report_input",
        media_type="application/json",
        content=_json_bytes(report_input.to_dict()),
        metadata={"schema_version": report_input.schema_version},
    )
    return SkillExecutionOutput(
        output_data={
            "grounded_report_input": report_input.to_dict(),
            "grounded_report_input_artifact": _artifact_view(artifact),
        },
        emitted_artifacts=(artifact,),
    )


async def summarize_papers_and_extract_evidence(
    inputs: Mapping[str, Any],
    context: SkillExecutionContext,
) -> SkillExecutionOutput:
    report_input = _report_input(inputs["grounded_report_input"])
    papers = tuple(_paper(item) for item in inputs["selected_papers"])
    sources = dict(_source(item) for item in inputs["source_contents"])
    if tuple(item.paper_id for item in papers) != report_input.ordered_paper_ids:
        raise SkillExecutionFailure("UNAPPROVED_PAPER", "Summary paper set changed")
    summaries: list[PerPaperSummary] = []
    evidence: list[GroundedEvidenceUnit] = []
    usages: list[ProviderUsage] = []
    operation_ids: list[str] = []
    for index, (paper, source_id) in enumerate(
        zip(papers, report_input.ordered_source_content_ids, strict=True), 1
    ):
        source = sources.get(source_id)
        if (
            source is None
            or source.paper_id != paper.paper_id
            or source.content_hash
            != report_input.source_content_checksums[source_id]
            or source.abstract is None
        ):
            raise SkillExecutionFailure(
                "SOURCE_CONTENT_CHECKSUM_MISMATCH",
                f"Source binding failed for {paper.paper_id}",
            )
        value, usage, operation_id = await _generation_call(
            context,
            operation_kind=ProviderOperationKind.SUMMARIZE_EVIDENCE,
            logical_call=f"paper-{index}",
            prompt=PAPER_SUMMARY_EVIDENCE,
            payload={
                "fixture_key": f"summary:{paper.provider_id}",
                "topic": inputs["query"]["topic"],
                "paper_id": paper.paper_id,
                "citation_label": report_input.citation_label_mapping[paper.paper_id],
                "title": paper.title,
                "year": paper.publication_year,
                "venue": paper.publication_venue,
                "abstract": source.abstract,
                "content_scope": "abstract_only",
            },
        )
        value, repair_usages, repair_ids = await _require_structure_or_repair(
            context,
            value=value,
            required_fields=(
                "objective",
                "methodology",
                "key_findings",
                "contribution",
                "stated_limitations",
                "relevance_to_topic",
                "evidence",
            ),
            target_fixture_key=f"repair:summary:{paper.provider_id}",
            target_schema="per-paper-summary-and-evidence/v1",
        )
        paper_evidence_ids: list[str] = []
        for evidence_index, raw in enumerate(value.get("evidence", ()), 1):
            span = str(raw.get("span", ""))
            if not span or len(span) > 200 or span not in source.abstract:
                raise SkillExecutionFailure(
                    "INVALID_EVIDENCE_SPAN",
                    f"Evidence span {index}.{evidence_index} is not in approved abstract",
                )
            evidence_id = _stable_id(
                "evidence",
                {"paper": paper.paper_id, "index": evidence_index, "span": span},
            )
            evidence_payload = {
                "evidence_id": evidence_id,
                "paper_id": paper.paper_id,
                "source_content_id": source_id,
                "source_content_checksum": source.content_hash,
                "source_field": "abstract",
                "source_locator": {
                    "start": source.abstract.index(span),
                    "length": len(span),
                },
                "bounded_private_span": span,
                "paraphrased_evidence": str(raw["paraphrase"]),
                "span_checksum": canonical_hash(span),
                "evidence_type": str(raw["evidence_type"]),
                "content_scope": "abstract_only",
                "supported_claim_ids": (),
                "extraction_prompt_version": (
                    f"{PAPER_SUMMARY_EVIDENCE.prompt_id}@"
                    f"{PAPER_SUMMARY_EVIDENCE.version}"
                ),
                "schema_version": "evidence-unit/v2",
            }
            unit = _contract_payload(GroundedEvidenceUnit, evidence_payload)
            evidence.append(unit)
            paper_evidence_ids.append(unit.evidence_id)
        summary_payload = {
            "paper_id": paper.paper_id,
            "citation_label": report_input.citation_label_mapping[paper.paper_id],
            "objective": str(value["objective"]),
            "methodology": value["methodology"],
            "key_findings": tuple(value["key_findings"]),
            "contribution": str(value["contribution"]),
            "stated_limitations": value["stated_limitations"],
            "relevance_to_topic": str(value["relevance_to_topic"]),
            "uncertainties": tuple(value.get("uncertainties", ())),
            "missing_information": tuple(value.get("missing_information", ())),
            "abstract_only": True,
            "evidence_unit_ids": tuple(paper_evidence_ids),
            "provider_identity": usage.provider,
            "model_identity": usage.model_or_endpoint,
            "prompt_version": (
                f"{PAPER_SUMMARY_EVIDENCE.prompt_id}@"
                f"{PAPER_SUMMARY_EVIDENCE.version}"
            ),
            "generated_at": _FIXED_TIME,
            "schema_version": "per-paper-summary/v1",
        }
        summaries.append(_contract_payload(PerPaperSummary, summary_payload))
        usages.append(usage)
        usages.extend(repair_usages)
        operation_ids.append(operation_id)
        operation_ids.extend(repair_ids)
    summaries_artifact = _artifact(
        context,
        logical_name="paper_summaries.json",
        kind="research.paper_summaries",
        media_type="application/json",
        content=_json_bytes(
            {
                "schema_version": "paper-summaries-artifact/v1",
                "summaries": [item.to_dict() for item in summaries],
            }
        ),
        metadata={"schema_version": "paper-summaries-artifact/v1"},
    )
    evidence_artifact = _artifact(
        context,
        logical_name="evidence.json",
        kind="research.evidence",
        media_type="application/json",
        content=_json_bytes(
            {
                "schema_version": "evidence-artifact/v2",
                "private_spans_user_visible": False,
                "evidence": [item.to_dict() for item in evidence],
            }
        ),
        metadata={"schema_version": "evidence-artifact/v2"},
    )
    return SkillExecutionOutput(
        output_data={
            "paper_summaries": [item.to_dict() for item in summaries],
            "evidence_units": [item.to_dict() for item in evidence],
            "provider_operation_ids": operation_ids,
            "paper_summaries_artifact": _artifact_view(summaries_artifact),
            "evidence_artifact": _artifact_view(evidence_artifact),
        },
        emitted_artifacts=(summaries_artifact, evidence_artifact),
        provider_usage=tuple(usages),
    )


def _summary(value: Mapping[str, Any]) -> PerPaperSummary:
    return PerPaperSummary(
        **{
            **value,
            "key_findings": tuple(value["key_findings"]),
            "uncertainties": tuple(value["uncertainties"]),
            "missing_information": tuple(value["missing_information"]),
            "evidence_unit_ids": tuple(value["evidence_unit_ids"]),
            "generated_at": datetime.fromisoformat(str(value["generated_at"])),
        }
    )


def _evidence(value: Mapping[str, Any]) -> GroundedEvidenceUnit:
    return GroundedEvidenceUnit(
        **{
            **value,
            "supported_claim_ids": tuple(value["supported_claim_ids"]),
        }
    )


def _claim(value: Mapping[str, Any]) -> GroundedClaimV2:
    return GroundedClaimV2(
        **{
            **value,
            "claim_category": GroundedClaimCategory(str(value["claim_category"])),
            "supporting_evidence_ids": tuple(value["supporting_evidence_ids"]),
            "supporting_paper_ids": tuple(value["supporting_paper_ids"]),
            "limitations": tuple(value["limitations"]),
        }
    )


async def synthesize_grounded_claims(
    inputs: Mapping[str, Any],
    context: SkillExecutionContext,
) -> SkillExecutionOutput:
    report_input = _report_input(inputs["grounded_report_input"])
    summaries = tuple(_summary(item) for item in inputs["paper_summaries"])
    evidence = [_evidence(item) for item in inputs["evidence_units"]]
    evidence_by_ordinal: dict[tuple[int, int], GroundedEvidenceUnit] = {}
    for paper_index, summary in enumerate(summaries, 1):
        for evidence_index, evidence_id in enumerate(summary.evidence_unit_ids, 1):
            evidence_by_ordinal[(paper_index, evidence_index)] = next(
                item for item in evidence if item.evidence_id == evidence_id
            )
    value, usage, operation_id = await _generation_call(
        context,
        operation_kind=ProviderOperationKind.SYNTHESIZE_CLAIMS,
        logical_call="cross-paper-claims",
        prompt=CROSS_PAPER_CLAIMS,
        payload={
            "fixture_key": "claims",
            "topic": inputs["query"]["topic"],
            "summaries": [item.to_dict() for item in summaries],
            "evidence": [
                {
                    **item.to_dict(),
                    "bounded_private_span": "[private-span-redacted-from-synthesis]",
                }
                for item in evidence
            ],
            "citation_label_mapping": report_input.citation_label_mapping,
        },
    )
    value, repair_usages, repair_ids = await _require_structure_or_repair(
        context,
        value=value,
        required_fields=("claims",),
        target_fixture_key="repair:claims",
        target_schema="grounded-claims/v2",
    )
    claims: list[GroundedClaimV2] = []
    links: dict[str, list[str]] = {item.evidence_id: [] for item in evidence}
    for raw in value.get("claims", ()):
        try:
            paper_ids = tuple(
                report_input.ordered_paper_ids[int(ordinal) - 1]
                for ordinal in raw["paper_ordinals"]
            )
            evidence_ids = tuple(
                evidence_by_ordinal[(int(pair[0]), int(pair[1]))].evidence_id
                for pair in raw["evidence_ordinals"]
            )
        except (IndexError, KeyError, TypeError, ValueError) as error:
            raise SkillExecutionFailure(
                "UNKNOWN_CLAIM_SUPPORT",
                "Generated claim references unknown paper/evidence",
            ) from error
        claim_payload = {
            "claim_id": _stable_id(
                "claim",
                {"key": raw["claim_key"], "text": raw["claim_text"]},
            ),
            "claim_text": str(raw["claim_text"]),
            "claim_category": GroundedClaimCategory(str(raw["claim_category"])),
            "supporting_evidence_ids": evidence_ids,
            "supporting_paper_ids": paper_ids,
            "confidence": str(raw["confidence"]),
            "inference_flag": bool(raw["inference_flag"]),
            "limitations": tuple(raw.get("limitations", ())),
            "generation_prompt_version": (
                f"{CROSS_PAPER_CLAIMS.prompt_id}@{CROSS_PAPER_CLAIMS.version}"
            ),
            "provider_identity": usage.provider,
            "model_identity": usage.model_or_endpoint,
            "schema_version": "grounded-claim/v2",
        }
        claim = _contract_payload(GroundedClaimV2, claim_payload)
        claims.append(claim)
        for evidence_id in evidence_ids:
            links[evidence_id].append(claim.claim_id)
    linked_evidence = []
    for item in evidence:
        payload = item.to_dict()
        payload["supported_claim_ids"] = tuple(links[item.evidence_id])
        payload.pop("checksum")
        linked_evidence.append(_contract_payload(GroundedEvidenceUnit, payload))
    claims_artifact = _artifact(
        context,
        logical_name="claims.json",
        kind="research.grounded_claims",
        media_type="application/json",
        content=_json_bytes(
            {
                "schema_version": "grounded-claims-artifact/v2",
                "claims": [item.to_dict() for item in claims],
            }
        ),
        metadata={"schema_version": "grounded-claims-artifact/v2"},
    )
    return SkillExecutionOutput(
        output_data={
            "grounded_claims": [item.to_dict() for item in claims],
            "evidence_units": [item.to_dict() for item in linked_evidence],
            "provider_operation_ids": [operation_id, *repair_ids],
            "claims_artifact": _artifact_view(claims_artifact),
        },
        emitted_artifacts=(claims_artifact,),
        provider_usage=(usage, *repair_usages),
    )


def _citation(value: Mapping[str, Any]) -> GroundedCitationReference:
    return GroundedCitationReference(**value)


def _render_report(
    *,
    title: str,
    executive_summary: str,
    conclusions: str,
    papers: tuple[PaperRecord, ...],
    summaries: tuple[PerPaperSummary, ...],
    claims: tuple[GroundedClaimV2, ...],
    citations: tuple[GroundedCitationReference, ...],
    generation_note: str,
) -> str:
    by_category: dict[GroundedClaimCategory, list[GroundedClaimV2]] = {
        category: [] for category in GroundedClaimCategory
    }
    for claim in claims:
        by_category[claim.claim_category].append(claim)
    lines = [
        f"# {title}",
        "",
        "## Scope and abstract-only disclosure",
        "",
        GROUNDING_DISCLOSURE,
        "",
        "## Search and source-selection methodology",
        "",
        "The user approved the exact ordered synthetic three-paper set before generation.",
        "",
        "## Executive summary",
        "",
        executive_summary,
        "",
        "## Selected papers",
        "",
    ]
    for citation in citations:
        lines.append(f"- {citation.citation_label} {citation.title} ({citation.year})")
    lines.extend(["", "## Per-paper summaries", ""])
    for paper, summary in zip(papers, summaries, strict=True):
        lines.extend(
            [
                f"### {summary.citation_label} {paper.title}",
                "",
                summary.objective,
                "",
                f"Contribution: {summary.contribution}",
                "",
            ]
        )

    def add_claims(heading: str, categories: tuple[GroundedClaimCategory, ...]) -> None:
        lines.extend([f"## {heading}", ""])
        selected = [item for category in categories for item in by_category[category]]
        if not selected:
            lines.extend(["No supported item was generated.", ""])
            return
        for claim in selected:
            labels = " ".join(
                next(
                    citation.citation_label
                    for citation in citations
                    if citation.paper_id == paper_id
                )
                for paper_id in claim.supporting_paper_ids
            )
            qualifier = " (tentative inference)" if claim.inference_flag else ""
            lines.append(f"- {claim.claim_text}{qualifier} {labels}")
        lines.append("")

    add_claims("Cross-paper themes", (GroundedClaimCategory.CROSS_SOURCE_THEME,))
    add_claims("Agreements", (GroundedClaimCategory.AGREEMENT,))
    add_claims("Disagreements", (GroundedClaimCategory.DISAGREEMENT,))
    add_claims("Limitations", (GroundedClaimCategory.LIMITATION,))
    add_claims(
        "Possible research gaps",
        (GroundedClaimCategory.RESEARCH_GAP, GroundedClaimCategory.SYSTEM_INFERENCE),
    )
    lines.extend(["## Conclusions", "", conclusions, "", "## References", ""])
    for citation in citations:
        suffix = f" DOI: {citation.doi}." if citation.doi else " DOI unavailable."
        lines.append(
            f"- {citation.citation_label} {citation.title}. "
            f"{citation.venue or 'Venue unavailable'}, {citation.year or 'year unavailable'}.{suffix}"
        )
    lines.extend(["", "## Generation and provenance note", "", generation_note, ""])
    return "\n".join(lines)


async def compose_grounded_report(
    inputs: Mapping[str, Any],
    context: SkillExecutionContext,
) -> SkillExecutionOutput:
    report_input = _report_input(inputs["grounded_report_input"])
    papers = tuple(_paper(item) for item in inputs["selected_papers"])
    summaries = tuple(_summary(item) for item in inputs["paper_summaries"])
    claims = tuple(_claim(item) for item in inputs["grounded_claims"])
    citations = tuple(_citation(item) for item in inputs["citations"])
    value, usage, operation_id = await _generation_call(
        context,
        operation_kind=ProviderOperationKind.COMPOSE_REPORT,
        logical_call="report",
        prompt=REPORT_COMPOSITION,
        payload={
            "fixture_key": "report",
            "topic": inputs["query"]["topic"],
            "papers": [
                {
                    "paper_id": item.paper_id,
                    "title": item.title,
                    "year": item.publication_year,
                    "venue": item.publication_venue,
                    "citation_label": report_input.citation_label_mapping[item.paper_id],
                }
                for item in papers
            ],
            "summaries": [item.to_dict() for item in summaries],
            "claims": [item.to_dict() for item in claims],
            "citations": [item.to_dict() for item in citations],
            "scope_disclosure": GROUNDING_DISCLOSURE,
        },
    )
    value, repair_usages, repair_ids = await _require_structure_or_repair(
        context,
        value=value,
        required_fields=(
            "title",
            "executive_summary",
            "conclusions",
            "generation_note",
        ),
        target_fixture_key="repair:report",
        target_schema="grounded-research-report/v2",
    )
    markdown = _render_report(
        title=str(value["title"]),
        executive_summary=str(value["executive_summary"]),
        conclusions=str(value["conclusions"]),
        papers=papers,
        summaries=summaries,
        claims=claims,
        citations=citations,
        generation_note=str(value["generation_note"]),
    )
    report_payload = {
        "report_id": _stable_id(
            "report",
            {"run": context.workflow_run_id, "input": report_input.input_checksum},
        ),
        "title": str(value["title"]),
        "scope_disclosure": GROUNDING_DISCLOSURE,
        "methodology": (
            "Deterministic search/ranking followed by exact user approval and staged "
            "abstract-only synthetic generation."
        ),
        "executive_summary": str(value["executive_summary"]),
        "selected_papers": tuple(
            {
                "paper_id": item.paper_id,
                "citation_label": report_input.citation_label_mapping[item.paper_id],
                "title": item.title,
            }
            for item in papers
        ),
        "per_paper_sections": tuple(
            {
                "paper_id": item.paper_id,
                "citation_label": item.citation_label,
                "objective": item.objective,
                "contribution": item.contribution,
            }
            for item in summaries
        ),
        "cross_paper_themes": tuple(
            {"claim_id": item.claim_id, "text": item.claim_text}
            for item in claims
            if item.claim_category is GroundedClaimCategory.CROSS_SOURCE_THEME
        ),
        "agreements": tuple(
            {"claim_id": item.claim_id, "text": item.claim_text}
            for item in claims
            if item.claim_category is GroundedClaimCategory.AGREEMENT
        ),
        "disagreements": tuple(
            {"claim_id": item.claim_id, "text": item.claim_text}
            for item in claims
            if item.claim_category is GroundedClaimCategory.DISAGREEMENT
        ),
        "limitations": tuple(
            item.claim_text
            for item in claims
            if item.claim_category is GroundedClaimCategory.LIMITATION
        )
        + ("All inputs and outputs are synthetic architecture-test fixtures.",),
        "possible_research_gaps": tuple(
            {
                "claim_id": item.claim_id,
                "text": item.claim_text,
                "tentative_inference": item.inference_flag,
            }
            for item in claims
            if item.claim_category is GroundedClaimCategory.RESEARCH_GAP
        ),
        "conclusions": str(value["conclusions"]),
        "references": citations,
        "provenance_note": str(value["generation_note"]),
        "claim_ids": tuple(item.claim_id for item in claims),
        "citation_labels": tuple(item.citation_label for item in citations),
        "workflow_version": context.workflow_version,
        "provider_identity": usage.provider,
        "model_identity": usage.model_or_endpoint,
        "prompt_versions": _PROMPTS.manifest(),
        "generated_at": _FIXED_TIME,
        "markdown": markdown,
        "schema_version": "grounded-research-report/v2",
    }
    report = _contract_payload(GroundedResearchReport, report_payload)
    return SkillExecutionOutput(
        output_data={
            "report": report.to_dict(),
            "provider_operation_ids": [operation_id, *repair_ids],
        },
        provider_usage=(usage, *repair_usages),
    )


def _report(value: Mapping[str, Any]) -> GroundedResearchReport:
    return GroundedResearchReport(
        **{
            **value,
            "selected_papers": tuple(value["selected_papers"]),
            "per_paper_sections": tuple(value["per_paper_sections"]),
            "cross_paper_themes": tuple(value["cross_paper_themes"]),
            "agreements": tuple(value["agreements"]),
            "disagreements": tuple(value["disagreements"]),
            "limitations": tuple(value["limitations"]),
            "possible_research_gaps": tuple(value["possible_research_gaps"]),
            "references": tuple(_citation(item) for item in value["references"]),
            "claim_ids": tuple(value["claim_ids"]),
            "citation_labels": tuple(value["citation_labels"]),
            "generated_at": datetime.fromisoformat(str(value["generated_at"])),
        }
    )


async def validate_grounded_provenance(
    inputs: Mapping[str, Any],
    context: SkillExecutionContext,
) -> Mapping[str, Any]:
    report_input = _report_input(inputs["grounded_report_input"])
    sources = dict(_source(item) for item in inputs["source_contents"])
    summaries = tuple(_summary(item) for item in inputs["paper_summaries"])
    evidence = tuple(_evidence(item) for item in inputs["evidence_units"])
    claims = tuple(_claim(item) for item in inputs["grounded_claims"])
    report = _report(inputs["report"])
    operations = context.capabilities.require_provider_operations().list_for_run(
        project_id=context.project_id,
        workflow_run_id=context.workflow_run_id,
    )
    result = GroundedProvenanceValidator().validate(
        report_input=report_input,
        source_contents=sources,
        summaries=summaries,
        evidence=evidence,
        claims=claims,
        report=report,
        provider_operations=operations,
    )
    if not result.publishable:
        raise SkillExecutionFailure(
            "GROUNDED_PROVENANCE_VALIDATION_FAILED",
            "Grounded report did not pass the publication gate",
            details={
                "issues": [
                    {"code": issue.code, "path": issue.path} for issue in result.issues
                ]
            },
        )
    return {
        "validation": {
            "publishable": True,
            "validator_version": result.validator_version,
            "issue_count": 0,
            "report_checksum": report.checksum,
            "grounded_input_checksum": report_input.input_checksum,
        }
    }


async def persist_grounded_artifacts(
    inputs: Mapping[str, Any],
    context: SkillExecutionContext,
) -> SkillExecutionOutput:
    if not inputs["validation"].get("publishable"):
        raise SkillExecutionFailure(
            "PUBLICATION_GATE_NOT_PASSED",
            "A validated grounded report is required before artifact publication",
        )
    report_input = _report_input(inputs["grounded_report_input"])
    report = _report(inputs["report"])
    summaries = tuple(_summary(item) for item in inputs["paper_summaries"])
    evidence = tuple(_evidence(item) for item in inputs["evidence_units"])
    claims = tuple(_claim(item) for item in inputs["grounded_claims"])
    operations = context.capabilities.require_provider_operations().list_for_run(
        project_id=context.project_id,
        workflow_run_id=context.workflow_run_id,
    )
    if any(
        item.status is not ProviderOperationStatus.SUCCEEDED
        or item.actual_usage is None
        for item in operations
    ):
        raise SkillExecutionFailure(
            "UNSETTLED_PROVIDER_OPERATION",
            "Publication requires settled operation usage",
        )
    total_attempts = sum(
        item.actual_usage.request_count + item.actual_usage.retry_count
        for item in operations
        if item.actual_usage is not None
    )
    total_input_tokens = sum(
        item.actual_usage.input_tokens or 0
        for item in operations
        if item.actual_usage is not None
    )
    total_output_tokens = sum(
        item.actual_usage.output_tokens or 0
        for item in operations
        if item.actual_usage is not None
    )
    total_cost = sum(
        item.actual_usage.estimated_cost_minor_units or 0
        for item in operations
        if item.actual_usage is not None
    )
    if total_attempts > 11:
        raise SkillExecutionFailure(
            "ATTEMPT_BUDGET_EXCEEDED",
            "Generation attempts exceed the accepted Phase 9C-1 envelope",
        )
    if total_input_tokens > 90_000 or total_output_tokens > 32_000:
        raise SkillExecutionFailure(
            "TOKEN_BUDGET_EXCEEDED",
            "Generation token usage exceeds the accepted Phase 9C-1 envelope",
        )
    if total_cost > 125:
        raise SkillExecutionFailure(
            "COST_BUDGET_EXCEEDED",
            "Generation cost exceeds the configured architecture hard cap",
        )
    corpus_payload = {
        "corpus_id": _stable_id(
            "literature_corpus",
            {"run": context.workflow_run_id, "report": report.checksum},
        ),
        "source_workflow_run_id": context.workflow_run_id,
        "source_report_id": report.report_id,
        "source_report_checksum": report.checksum,
        "topic": str(inputs["query"]["topic"]),
        "approved_papers": tuple(
            {
                "paper_id": item["paper_id"],
                "title": item["title"],
                "publication_year": item.get("publication_year"),
                "publication_venue": item.get("publication_venue"),
                "citation_label": report_input.citation_label_mapping[item["paper_id"]],
            }
            for item in inputs["selected_papers"]
        ),
        "summaries": tuple(item.to_dict() for item in summaries),
        "evidence": tuple(
            {
                key: value
                for key, value in item.to_dict().items()
                if key != "bounded_private_span"
            }
            for item in evidence
        ),
        "claims": tuple(item.to_dict() for item in claims),
        "citations": tuple(inputs["citations"]),
        "inference_disclosures": (
            "Research gaps and system inferences are tentative model-assisted outputs.",
            "The corpus is abstract-only and requires original-paper verification.",
        ),
        "content_scope": "abstract_only",
        "downstream_use_policy": {
            "idea_generation": "eligible_after_checksum_verification",
            "academic_writing": "eligible_with_citation_and_scope_disclosure",
            "automatic_execution": "not_authorized_in_phase_9c_1",
        },
        "generated_at": _FIXED_TIME,
        "schema_version": "literature-corpus/v1",
    }
    corpus = _contract_payload(LiteratureCorpus, corpus_payload)
    usage_payload = {
        "schema_version": "grounded-provider-usage/v1",
        "workflow_run_id": context.workflow_run_id,
        "operation_count": len(operations),
        "all_settled": True,
        "actual_cost_minor_units": total_cost,
        "attempt_count": total_attempts,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "currency": "USD",
        "operations": [item.to_dict() for item in operations],
    }
    provenance_payload = {
        "schema_version": "grounded-provenance/v2",
        "project_id": context.project_id,
        "workflow_run_id": context.workflow_run_id,
        "workflow_id": context.workflow_id,
        "workflow_version": context.workflow_version,
        "workflow_hash": inputs["workflow_hash"],
        "grounded_report_input_checksum": report_input.input_checksum,
        "selected_paper_artifact_checksum": (
            report_input.selected_paper_artifact_checksum
        ),
        "approval_request_id": report_input.approval_request_id,
        "approval_fingerprint": report_input.approval_fingerprint,
        "source_content_checksums": report_input.source_content_checksums,
        "report_checksum": report.checksum,
        "literature_corpus_checksum": corpus.checksum,
        "prompt_manifest": _PROMPTS.manifest(),
        "provider_identity": report.provider_identity,
        "model_identity": report.model_identity,
        "provider_operation_ids": [item.id for item in operations],
        "all_operations_settled": True,
        "validator_version": inputs["validation"]["validator_version"],
        "publication_gate": "passed",
    }
    generation_payload = {
        "schema_version": "grounded-generation-manifest/v1",
        "workflow_id": context.workflow_id,
        "workflow_version": context.workflow_version,
        "workflow_hash": inputs["workflow_hash"],
        "skill_versions": {
            definition.name: definition.version
            for definition in GROUNDED_SKILL_DEFINITIONS
        },
        "prompt_manifest": _PROMPTS.manifest(),
        "report_checksum": report.checksum,
        "provenance_checksum": canonical_hash(provenance_payload),
        "literature_corpus_checksum": corpus.checksum,
        "artifact_set_complete": True,
    }
    artifacts = (
        _artifact(
            context,
            logical_name="report.json",
            kind="research.grounded_report",
            media_type="application/json",
            content=_json_bytes(report.to_dict()),
            metadata={"schema_version": report.schema_version},
        ),
        _artifact(
            context,
            logical_name="report.md",
            kind="research.grounded_report_markdown",
            media_type="text/markdown; charset=utf-8",
            content=report.markdown.encode("utf-8"),
            metadata={
                "schema_version": report.schema_version,
                "abstract_only": True,
            },
        ),
        _artifact(
            context,
            logical_name="provenance.json",
            kind="research.grounded_provenance",
            media_type="application/json",
            content=_json_bytes(provenance_payload),
            metadata={"schema_version": provenance_payload["schema_version"]},
        ),
        _artifact(
            context,
            logical_name="usage.json",
            kind="research.provider_usage",
            media_type="application/json",
            content=_json_bytes(usage_payload),
            metadata={"schema_version": usage_payload["schema_version"]},
        ),
        _artifact(
            context,
            logical_name="generation_manifest.json",
            kind="research.generation_manifest",
            media_type="application/json",
            content=_json_bytes(generation_payload),
            metadata={"schema_version": generation_payload["schema_version"]},
        ),
        _artifact(
            context,
            logical_name="literature_corpus.json",
            kind="research.literature_corpus",
            media_type="application/json",
            content=_json_bytes(corpus.to_dict()),
            metadata={
                "schema_version": corpus.schema_version,
                "downstream_eligible": True,
            },
        ),
    )
    by_name = {item.logical_name: item for item in artifacts}
    return SkillExecutionOutput(
        output_data={
            "report_artifact": _artifact_view(by_name["report.md"]),
            "provenance_artifact": _artifact_view(by_name["provenance.json"]),
            "usage_artifact": _artifact_view(by_name["usage.json"]),
            "literature_corpus_artifact": _artifact_view(
                by_name["literature_corpus.json"]
            ),
            "generation_manifest_artifact": _artifact_view(
                by_name["generation_manifest.json"]
            ),
            "publication": {
                "publishable": True,
                "abstract_only": True,
                "paper_count": len(report_input.ordered_paper_ids),
                "summary_count": len(summaries),
                "evidence_count": len(evidence),
                "claim_count": len(claims),
                "citation_count": len(report.citation_labels),
                "artifact_count": 13,
                "actual_cost_minor_units": usage_payload[
                    "actual_cost_minor_units"
                ],
                "all_provider_operations_settled": True,
                "report_checksum": report.checksum,
                "provenance_checksum": canonical_hash(provenance_payload),
                "literature_corpus_checksum": corpus.checksum,
            },
        },
        emitted_artifacts=artifacts,
    )


def register_grounded_research_skills(registry: SkillRegistry) -> None:
    registrations = (
        (LOAD_APPROVED_SOURCE_CONTENT, load_approved_source_content),
        (BUILD_GROUNDED_REPORT_INPUT, build_grounded_report_input),
        (
            SUMMARIZE_PAPERS_AND_EXTRACT_EVIDENCE,
            summarize_papers_and_extract_evidence,
        ),
        (SYNTHESIZE_GROUNDED_CLAIMS, synthesize_grounded_claims),
        (COMPOSE_GROUNDED_REPORT, compose_grounded_report),
        (VALIDATE_GROUNDED_PROVENANCE, validate_grounded_provenance),
        (PERSIST_GROUNDED_ARTIFACTS, persist_grounded_artifacts),
    )
    for definition, implementation in registrations:
        registry.register(definition, implementation)
