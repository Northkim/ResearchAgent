"""Bounded candidate-pool generation over the existing provider boundary."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.research.contracts import (
    ProviderCategory,
    ProviderFailureCategory,
    ProviderOperation,
    ProviderOperationKind,
    ProviderOperationStatus,
    ProviderUsage,
    ResearchQuery,
    SettlementState,
    canonical_hash,
)
from backend.research.contracts._serialization import canonical_json
from backend.research.ports import (
    ArtifactContentStorage,
    PaperSearchProvider,
    ProviderError,
    ProviderRequestContext,
)
from backend.research.services import (
    BudgetExceededError,
    ProviderExecutionPolicy,
    ProviderOperationService,
)

from .contracts import (
    EvaluationCandidate,
    EvaluationCompletionState,
    EvaluationRun,
    EvaluationTopic,
)
from .topics import EvaluationTopicSet


class EvaluationGenerationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class EvaluationArtifact:
    logical_name: str
    storage_key: str
    checksum: str
    size: int
    media_type: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "logical_name": self.logical_name,
            "storage_key": self.storage_key,
            "checksum": self.checksum,
            "size": self.size,
            "media_type": self.media_type,
        }


@dataclass(frozen=True, slots=True)
class CandidatePoolResult:
    evaluation_run: EvaluationRun
    candidates: tuple[EvaluationCandidate, ...]
    artifacts: tuple[EvaluationArtifact, ...]
    resumed: bool


class CandidatePoolGenerator:
    """Generate immutable normalized pools; it never creates relevance labels."""

    def __init__(
        self,
        *,
        provider: PaperSearchProvider,
        provider_operations: ProviderOperationService,
        execution_policy: ProviderExecutionPolicy,
        artifact_storage: ArtifactContentStorage,
        clock: Callable[[], datetime] | None = None,
        include_abstract_preview: bool = False,
    ) -> None:
        self.provider = provider
        self.provider_operations = provider_operations
        self.execution_policy = execution_policy
        self.artifact_storage = artifact_storage
        self.clock = clock or (lambda: datetime.now(UTC))
        self.include_abstract_preview = include_abstract_preview

    async def generate(
        self,
        *,
        evaluation_id: str,
        topic_set: EvaluationTopicSet,
        topic_ids: tuple[str, ...] | None = None,
    ) -> CandidatePoolResult:
        evaluation_id = self._safe_segment(evaluation_id, "evaluation_id")
        selected = self._select_topics(topic_set, topic_ids)
        top_manifest_key = f"{evaluation_id}/evaluation_manifest.json"
        existing = self._read_json_if_present(top_manifest_key)
        if existing is not None:
            self._assert_no_unsettled(evaluation_id)
            return self._resume_complete(existing, top_manifest_key)

        started_at = self._now()
        all_candidates: list[EvaluationCandidate] = []
        all_artifacts: list[EvaluationArtifact] = []
        query_fingerprints: dict[str, str] = {}
        pool_checksums: dict[str, str] = {}
        usages: list[Mapping[str, Any]] = []

        for topic in selected:
            topic_result = await self._generate_topic(
                evaluation_id=evaluation_id,
                topic=topic,
            )
            all_candidates.extend(topic_result["candidates"])
            all_artifacts.extend(topic_result["artifacts"])
            query_fingerprints[topic.topic_id] = topic_result["query_fingerprint"]
            pool_checksums[topic.topic_id] = topic_result["pool_checksum"]
            usages.append(topic_result["usage"])

        self._assert_no_unsettled(evaluation_id)
        completed_at = self._now()
        evaluation_run = EvaluationRun(
            evaluation_id=evaluation_id,
            topic_set_version=topic_set.version,
            provider=self.provider.identity.provider,
            adapter_version=self.provider.identity.adapter_version,
            api_contract_snapshot=self._contract_snapshot(all_artifacts),
            query_fingerprints=query_fingerprints,
            candidate_pool_checksums=pool_checksums,
            started_at=started_at,
            completed_at=completed_at,
            request_count=sum(int(item["request_count"]) for item in usages),
            latency_ms=sum(int(item["latency_ms"]) for item in usages),
            retry_count=sum(int(item["retry_count"]) for item in usages),
            provider_usage=tuple(usages),
            completion_state=EvaluationCompletionState.CANDIDATES_COMPLETE,
        )
        manifest_document = {
            "schema_version": "openalex-evaluation-manifest/v1",
            "topic_set_hash": topic_set.canonical_hash,
            "evaluation_run": evaluation_run.to_dict(),
            "artifacts": [item.to_dict() for item in all_artifacts],
            "candidate_count": len(all_candidates),
            "human_judgments_generated": False,
            "raw_provider_response_retained": False,
        }
        manifest = self._write_json(
            top_manifest_key,
            "evaluation_manifest.json",
            manifest_document,
        )
        all_artifacts.append(manifest)
        return CandidatePoolResult(
            evaluation_run=evaluation_run,
            candidates=tuple(all_candidates),
            artifacts=tuple(all_artifacts),
            resumed=False,
        )

    async def _generate_topic(
        self,
        *,
        evaluation_id: str,
        topic: EvaluationTopic,
    ) -> dict[str, Any]:
        base = f"{evaluation_id}/topics/{self._safe_segment(topic.topic_id, 'topic_id')}"
        receipt_key = f"{base}/topic_manifest.json"
        receipt = self._read_json_if_present(receipt_key)
        if receipt is not None:
            return self._resume_topic(receipt)

        query = ResearchQuery(
            topic=topic.topic,
            keywords=topic.keywords,
            year_from=topic.year_from,
            year_to=topic.year_to,
            max_results=topic.maximum_candidates,
            language=topic.language_policy,
            inclusion_criteria=(
                "Candidate is topically relevant under human review.",
            ),
            exclusion_criteria=(
                "Candidate is not relevant or cannot be judged from permitted metadata.",
            ),
        )
        selected_paper_limit = min(5, topic.maximum_candidates)
        request_identity = self.provider.request_identity(
            query,
            limit=selected_paper_limit,
        )
        fingerprint = canonical_hash(request_identity)
        operation = self._operation(
            evaluation_id=evaluation_id,
            topic=topic,
            fingerprint=fingerprint,
        )
        try:
            reserved, replay = self.provider_operations.reserve(
                operation,
                budget=self.execution_policy.budget,
            )
        except BudgetExceededError as error:
            raise EvaluationGenerationError(
                f"Evaluation provider budget exceeded: {error.dimension}"
            ) from error
        if replay:
            if reserved.status is ProviderOperationStatus.SUCCEEDED:
                raise EvaluationGenerationError(
                    "Provider operation already succeeded but its immutable topic "
                    "manifest is unavailable; refusing to call the provider again"
                )
            raise EvaluationGenerationError(
                "Provider operation is incomplete or failed; operator review is required"
            )
        self.provider_operations.commit_staged()
        now = self._now()
        self.provider_operations.mark_running(operation.id, at=now)
        self.provider_operations.commit_staged()
        context = ProviderRequestContext(
            operation_id=operation.id,
            idempotency_key=operation.idempotency_key,
            request_fingerprint=fingerprint,
            deadline=now
            + timedelta(seconds=self.execution_policy.operation_timeout_seconds),
        )
        try:
            result = await self.provider.search(
                query,
                limit=selected_paper_limit,
                context=context,
            )
        except ProviderError as error:
            usage = self._failure_usage(error)
            self.provider_operations.settle_failure(
                operation.id,
                category=error.category,
                at=self._now(),
                usage=usage,
                provider_call_started=True,
                diagnostic_metadata={
                    "retryable": error.retryable,
                    **{
                        key: value
                        for key, value in dict(error.safe_details).items()
                        if key not in {"api_key", "authorization", "url"}
                    },
                },
            )
            self.provider_operations.commit_staged()
            raise EvaluationGenerationError(
                f"Provider search failed: {error.category.value}"
            ) from error
        if not result.complete:
            self._settle_invalid_result(
                operation.id,
                result.usage,
                "incomplete_result",
            )
            raise EvaluationGenerationError(
                "Incomplete provider results cannot form an immutable candidate pool"
            )
        if (
            result.search_plan is None
            or result.search_execution is None
            or result.search_statistics is None
        ):
            self._settle_invalid_result(
                operation.id,
                result.usage,
                "missing_search_evidence",
            )
            raise EvaluationGenerationError(
                "Provider did not return the required search evidence contracts"
            )
        self.provider_operations.settle_success(
            operation.id,
            usage=result.usage,
            at=self._now(),
        )
        self.provider_operations.commit_staged()

        execution_id = canonical_hash(
            {
                "topic_id": topic.topic_id,
                "search_plan": result.search_plan.fingerprint,
                "retrieved_at": result.search_execution.retrieved_at,
            }
        )
        candidates = tuple(
            self._candidate(topic, paper, rank, execution_id)
            for rank, paper in enumerate(result.papers, start=1)
        )
        candidate_document = {
            "schema_version": "openalex-candidate-pool/v1",
            "topic_id": topic.topic_id,
            "search_execution_id": execution_id,
            "candidate_count": len(candidates),
            "candidates": [item.to_dict() for item in candidates],
            "contains_human_labels": False,
            "raw_provider_response_retained": False,
        }
        artifacts = [
            self._write_json(
                f"{base}/evaluation_topic.json",
                "evaluation_topic.json",
                topic.to_dict(),
            ),
            self._write_json(
                f"{base}/search_plan.json",
                "search_plan.json",
                result.search_plan.to_dict(),
            ),
            self._write_json(
                f"{base}/search_execution.json",
                "search_execution.json",
                result.search_execution.to_dict(),
            ),
            self._write_json(
                f"{base}/search_statistics.json",
                "search_statistics.json",
                result.search_statistics.to_dict(),
            ),
            self._write_json(
                f"{base}/candidates.json",
                "candidates.json",
                candidate_document,
            ),
        ]
        receipt_document = {
            "schema_version": "openalex-topic-manifest/v1",
            "topic_id": topic.topic_id,
            "query_fingerprint": result.search_plan.fingerprint,
            "pool_checksum": artifacts[-1].checksum,
            "usage": result.usage.to_dict(),
            "operation_id": operation.id,
            "operation_settled": True,
            "artifacts": [item.to_dict() for item in artifacts],
            "candidates": [item.to_dict() for item in candidates],
        }
        receipt_artifact = self._write_json(
            receipt_key,
            "topic_manifest.json",
            receipt_document,
        )
        artifacts.append(receipt_artifact)
        return {
            "candidates": candidates,
            "artifacts": tuple(artifacts),
            "query_fingerprint": result.search_plan.fingerprint,
            "pool_checksum": artifacts[-2].checksum,
            "usage": result.usage.to_dict(),
        }

    def _operation(
        self,
        *,
        evaluation_id: str,
        topic: EvaluationTopic,
        fingerprint: str,
    ) -> ProviderOperation:
        now = self._now()
        idempotency_key = (
            f"live:evaluation:{evaluation_id}:{topic.topic_id}:{fingerprint}"
        )
        operation_id = "provider_op:" + canonical_hash(
            {"project": evaluation_id, "idempotency_key": idempotency_key}
        ).removeprefix("sha256:")
        return ProviderOperation(
            id=operation_id,
            project_id=f"evaluation:{evaluation_id}",
            workflow_run_id=f"evaluation:{evaluation_id}",
            logical_step_id=f"openalex_candidate_pool:{topic.topic_id}",
            step_run_id=None,
            provider_category=ProviderCategory.PAPER_SEARCH,
            operation_kind=ProviderOperationKind.SEARCH,
            provider_identity=self.provider.identity.provider,
            adapter_version=self.provider.identity.adapter_version,
            model_or_endpoint=self.provider.identity.model_or_endpoint,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            reservation=self.execution_policy.reservation_for(
                self.provider.identity.provider
            ),
            is_live_provider=(
                self.provider.identity.provider
                in self.execution_policy.live_provider_names
            ),
            created_at=now,
            updated_at=now,
        )

    def _candidate(
        self,
        topic: EvaluationTopic,
        paper: Any,
        rank: int,
        execution_id: str,
    ) -> EvaluationCandidate:
        candidate_id = "candidate:" + canonical_hash(
            {
                "topic_id": topic.topic_id,
                "paper_id": paper.paper_id,
                "execution_id": execution_id,
            }
        ).removeprefix("sha256:")
        preview = None
        if self.include_abstract_preview and paper.abstract:
            preview = " ".join(paper.abstract.split())[:500]
        return EvaluationCandidate(
            topic_id=topic.topic_id,
            topic_title=topic.title,
            topic=topic.topic,
            research_question=topic.research_question,
            candidate_id=candidate_id,
            rank=rank,
            paper_id=paper.paper_id,
            openalex_id=paper.provider_id,
            title=paper.title,
            authors=tuple(author.name for author in paper.authors),
            year=paper.publication_year,
            venue=paper.publication_venue,
            doi=paper.doi,
            abstract_available=paper.abstract is not None,
            normalized_metadata_hash=paper.raw_metadata_hash,
            search_execution_id=execution_id,
            provider=self.provider.identity.provider,
            adapter_version=self.provider.identity.adapter_version,
            abstract_preview=preview,
        )

    def _write_json(
        self,
        storage_key: str,
        logical_name: str,
        document: Mapping[str, Any],
    ) -> EvaluationArtifact:
        content = canonical_json(document).encode("utf-8")
        stored = self.artifact_storage.write_immutable(
            storage_key,
            content,
            media_type="application/json",
        )
        return EvaluationArtifact(
            logical_name=logical_name,
            storage_key=stored.storage_key,
            checksum=stored.checksum,
            size=stored.size,
            media_type=stored.media_type,
        )

    def _read_json_if_present(self, storage_key: str) -> Mapping[str, Any] | None:
        try:
            content = self.artifact_storage.read(storage_key)
        except FileNotFoundError:
            return None
        value = json.loads(content)
        if not isinstance(value, Mapping):
            raise EvaluationGenerationError("Stored evaluation manifest is invalid")
        return value

    def _resume_topic(self, receipt: Mapping[str, Any]) -> dict[str, Any]:
        if receipt.get("operation_settled") is not True:
            raise EvaluationGenerationError("Topic manifest has an unsettled operation")
        operation_id = str(receipt.get("operation_id", ""))
        operation = self.provider_operations.repository.get(operation_id)
        if operation is None:
            raise EvaluationGenerationError(
                "Durable ProviderOperation is unavailable for the topic manifest"
            )
        if (
            operation.status is not ProviderOperationStatus.SUCCEEDED
            or operation.settlement_state is not SettlementState.SETTLED
        ):
            raise EvaluationGenerationError(
                "Topic manifest does not match a settled successful ProviderOperation"
            )
        artifacts = tuple(
            self._artifact_from_dict(item) for item in receipt.get("artifacts", ())
        )
        self._verify_artifacts(artifacts)
        candidates = tuple(
            EvaluationCandidate.from_dict(item)
            for item in receipt.get("candidates", ())
        )
        return {
            "candidates": candidates,
            "artifacts": artifacts,
            "query_fingerprint": str(receipt["query_fingerprint"]),
            "pool_checksum": str(receipt["pool_checksum"]),
            "usage": dict(receipt["usage"]),
        }

    def _resume_complete(
        self,
        manifest: Mapping[str, Any],
        manifest_key: str,
    ) -> CandidatePoolResult:
        artifacts = tuple(
            self._artifact_from_dict(item) for item in manifest.get("artifacts", ())
        )
        self._verify_artifacts(artifacts)
        all_candidates: list[EvaluationCandidate] = []
        for artifact in artifacts:
            if artifact.logical_name != "topic_manifest.json":
                continue
            receipt = self._read_json_if_present(artifact.storage_key)
            if receipt is None:
                raise EvaluationGenerationError("Topic manifest disappeared")
            all_candidates.extend(self._resume_topic(receipt)["candidates"])
        run_value = manifest.get("evaluation_run")
        if not isinstance(run_value, Mapping):
            raise EvaluationGenerationError("Evaluation manifest has no run contract")
        run = EvaluationRun(
            evaluation_id=str(run_value["evaluation_id"]),
            topic_set_version=str(run_value["topic_set_version"]),
            provider=str(run_value["provider"]),
            adapter_version=str(run_value["adapter_version"]),
            api_contract_snapshot=str(run_value["api_contract_snapshot"]),
            query_fingerprints=dict(run_value["query_fingerprints"]),
            candidate_pool_checksums=dict(run_value["candidate_pool_checksums"]),
            started_at=datetime.fromisoformat(str(run_value["started_at"])),
            completed_at=datetime.fromisoformat(str(run_value["completed_at"])),
            request_count=int(run_value["request_count"]),
            latency_ms=int(run_value["latency_ms"]),
            retry_count=int(run_value["retry_count"]),
            provider_usage=tuple(run_value["provider_usage"]),
            completion_state=EvaluationCompletionState(
                str(run_value["completion_state"])
            ),
            schema_version=str(run_value["schema_version"]),
        )
        manifest_bytes = self.artifact_storage.read(manifest_key)
        from backend.research.contracts import sha256_bytes

        manifest_artifact = EvaluationArtifact(
            logical_name="evaluation_manifest.json",
            storage_key=manifest_key,
            checksum=sha256_bytes(manifest_bytes),
            size=len(manifest_bytes),
            media_type="application/json",
        )
        return CandidatePoolResult(
            evaluation_run=run,
            candidates=tuple(all_candidates),
            artifacts=(*artifacts, manifest_artifact),
            resumed=True,
        )

    def _verify_artifacts(self, artifacts: tuple[EvaluationArtifact, ...]) -> None:
        for artifact in artifacts:
            verification = self.artifact_storage.verify(
                artifact.storage_key,
                expected_checksum=artifact.checksum,
                expected_size=artifact.size,
            )
            if not verification.valid:
                raise EvaluationGenerationError(
                    f"Evaluation artifact checksum mismatch: {artifact.logical_name}"
                )

    def _assert_no_unsettled(self, evaluation_id: str) -> None:
        unsettled = self.provider_operations.repository.list_unsettled(
            project_id=f"evaluation:{evaluation_id}"
        )
        if unsettled:
            raise EvaluationGenerationError(
                "Evaluation publication blocked by unsettled ProviderOperations"
            )

    @staticmethod
    def _artifact_from_dict(value: Mapping[str, Any]) -> EvaluationArtifact:
        return EvaluationArtifact(
            logical_name=str(value["logical_name"]),
            storage_key=str(value["storage_key"]),
            checksum=str(value["checksum"]),
            size=int(value["size"]),
            media_type=str(value["media_type"]),
        )

    @staticmethod
    def _failure_usage(error: ProviderError) -> ProviderUsage | None:
        request_count = error.safe_details.get("request_count")
        if not isinstance(request_count, int):
            return None
        return ProviderUsage(
            provider="openalex",
            model_or_endpoint="GET /works?search=",
            operation_kind=ProviderOperationKind.SEARCH,
            request_count=request_count,
            input_tokens=0,
            output_tokens=0,
            estimated_cost_minor_units=0,
            cost_currency="USD",
            latency_ms=int(error.safe_details.get("latency_ms", 0)),
            retry_count=int(error.safe_details.get("retry_count", 0)),
            failure_category=error.category,
        )

    def _settle_invalid_result(
        self,
        operation_id: str,
        usage: ProviderUsage,
        reason: str,
    ) -> None:
        self.provider_operations.settle_failure(
            operation_id,
            category=ProviderFailureCategory.MALFORMED_PROVIDER_RESPONSE,
            at=self._now(),
            usage=usage,
            provider_call_started=True,
            diagnostic_metadata={"failure_point": reason},
        )
        self.provider_operations.commit_staged()

    @staticmethod
    def _select_topics(
        topic_set: EvaluationTopicSet,
        topic_ids: tuple[str, ...] | None,
    ) -> tuple[EvaluationTopic, ...]:
        if topic_ids is None:
            return topic_set.topics
        requested = tuple(topic_ids)
        if len(requested) != len(set(requested)):
            raise EvaluationGenerationError("Requested topic IDs must be unique")
        by_id = {topic.topic_id: topic for topic in topic_set.topics}
        unknown = set(requested) - set(by_id)
        if unknown:
            raise EvaluationGenerationError(f"Unknown evaluation topics: {sorted(unknown)}")
        return tuple(by_id[item] for item in requested)

    @staticmethod
    def _safe_segment(value: str, field_name: str) -> str:
        if (
            not value
            or value in {".", ".."}
            or "/" in value
            or "\\" in value
            or not all(character.isalnum() or character in "-_." for character in value)
        ):
            raise EvaluationGenerationError(f"{field_name} is not a safe path segment")
        return value

    def _now(self) -> datetime:
        value = self.clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise EvaluationGenerationError("Evaluation clock must be timezone-aware")
        return value

    @staticmethod
    def _contract_snapshot(artifacts: list[EvaluationArtifact]) -> str:
        # OpenAlex-specific search-plan artifacts contain the authoritative value.
        return "openalex-works-api/2026-07-27" if artifacts else "unknown"
