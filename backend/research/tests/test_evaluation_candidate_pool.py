from __future__ import annotations

import asyncio
import json
import stat
from datetime import UTC, datetime
from typing import Any

import pytest

from backend.persistence.adapters import InMemoryUnitOfWork
from backend.research.adapters import (
    FakePaperSearchProvider,
    LocalFilesystemArtifactStorage,
    OpenAlexConfiguration,
    OpenAlexHttpResponse,
    OpenAlexPaperSearchProvider,
)
from backend.research.evaluation.candidate_pool import CandidatePoolGenerator
from backend.research.evaluation.candidate_pool import EvaluationGenerationError
from backend.research.evaluation.operation_journal import (
    EvaluationOperationJournalError,
    JournaledProviderOperationUnit,
)
from backend.research.evaluation.topics import EvaluationTopicSet, load_topic_set
from backend.research.contracts import ProviderBudget, ProviderReservation
from backend.research.services import ProviderExecutionPolicy, ProviderOperationService

NOW = datetime(2026, 7, 28, 11, 0, tzinfo=UTC)


class SyntheticTransport:
    def __init__(self, responses: list[OpenAlexHttpResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def get(self, path, *, params, timeout_seconds, headers):
        del timeout_seconds, headers
        self.calls.append((path, dict(params)))
        return self.responses.pop(0)


def _response(value: Any) -> OpenAlexHttpResponse:
    return OpenAlexHttpResponse(
        status_code=200,
        body=json.dumps(value).encode(),
        headers={"x-request-id": "synthetic-evaluation-request"},
    )


def _work(index: int) -> dict[str, Any]:
    return {
        "id": f"https://openalex.org/W{index}",
        "doi": f"https://doi.org/10.1234/evaluation-{index}",
        "display_name": f"Synthetic evaluation paper {index}",
        "authorships": [
            {
                "author": {
                    "id": f"https://openalex.org/A{index}",
                    "display_name": f"Synthetic Author {index}",
                    "orcid": None,
                }
            }
        ],
        "abstract_inverted_index": {
            "Synthetic": [0],
            "evaluation": [1],
            "abstract": [2],
            f"{index}": [3],
        },
        "publication_year": 2025,
        "publication_date": "2025-01-01",
        "primary_location": {
            "source": {"display_name": "Synthetic Evaluation Venue"}
        },
        "language": "en",
        "type": "article",
        "updated_date": "2026-01-01T00:00:00",
    }


def _topic_set() -> EvaluationTopicSet:
    full = load_topic_set("evaluation/topics/openalex_v1.json")
    return EvaluationTopicSet(
        topic_set_id=full.topic_set_id,
        version=full.version,
        description=full.description,
        topics=(full.topics[0],),
    )


def _three_topic_set() -> EvaluationTopicSet:
    full = load_topic_set("evaluation/topics/openalex_v1.json")
    return EvaluationTopicSet(
        topic_set_id=full.topic_set_id,
        version=full.version,
        description=full.description,
        topics=full.topics[:3],
    )


def test_candidate_pool_generation_is_immutable_resumable_and_network_free(tmp_path) -> None:
    rate = _response(
        {
            "rate_limit": {
                "daily_remaining_usd": "1",
                "prepaid_remaining_usd": "0",
                "endpoint_costs_usd": {"search": "0.001"},
            }
        }
    )
    works = _response(
        {
            "meta": {
                "count": 3,
                "per_page": 3,
                "next_cursor": None,
                "cost_usd": "0.001",
            },
            "results": [_work(index) for index in range(1, 4)],
        }
    )
    transport = SyntheticTransport([rate, works])
    provider = OpenAlexPaperSearchProvider(
        OpenAlexConfiguration(api_key="synthetic-key-never-persisted"),
        transport=transport,
        clock=lambda: NOW,
        sleeper=lambda _: None,
    )
    uow = InMemoryUnitOfWork()
    operation_service = ProviderOperationService(
        uow.provider_operations,
        commit_callback=uow.commit,
    )
    storage = LocalFilesystemArtifactStorage(tmp_path)
    generator = CandidatePoolGenerator(
        provider=provider,
        provider_operations=operation_service,
        execution_policy=ProviderExecutionPolicy.supervised_openalex(),
        artifact_storage=storage,
        clock=lambda: NOW,
        include_abstract_preview=False,
    )
    first = asyncio.run(
        generator.generate(
            evaluation_id="synthetic-evaluation",
            topic_set=_topic_set(),
        )
    )
    assert first.resumed is False
    assert len(first.candidates) == 3
    assert first.candidates[0].topic == "persistent research agents"
    assert first.candidates[0].research_question is not None
    assert any(
        artifact.logical_name == "evaluation_topic.json"
        for artifact in first.artifacts
    )
    assert len(transport.calls) == 2
    assert all(candidate.abstract_preview is None for candidate in first.candidates)
    assert first.evaluation_run.request_count == 2
    assert first.evaluation_run.retry_count == 0
    operations = operation_service.list_for_run(
        project_id="evaluation:synthetic-evaluation",
        workflow_run_id="evaluation:synthetic-evaluation",
    )
    assert len(operations) == 1
    assert operations[0].status.value == "SUCCEEDED"
    assert operations[0].settlement_state.value == "SETTLED"
    assert uow.provider_operations.list_unsettled(
        project_id="evaluation:synthetic-evaluation"
    ) == ()

    second = asyncio.run(
        generator.generate(
            evaluation_id="synthetic-evaluation",
            topic_set=_topic_set(),
        )
    )
    assert second.resumed is True
    assert len(transport.calls) == 2
    assert [item.candidate_id for item in second.candidates] == [
        item.candidate_id for item in first.candidates
    ]
    assert [item.checksum for item in second.artifacts[:-1]] == [
        item.checksum for item in first.artifacts[:-1]
    ]
    empty_transport = SyntheticTransport([])
    empty_uow = InMemoryUnitOfWork()
    with pytest.raises(
        EvaluationGenerationError,
        match="Durable ProviderOperation is unavailable",
    ):
        asyncio.run(
            CandidatePoolGenerator(
                provider=OpenAlexPaperSearchProvider(
                    OpenAlexConfiguration(api_key="synthetic-only"),
                    transport=empty_transport,
                    clock=lambda: NOW,
                ),
                provider_operations=ProviderOperationService(
                    empty_uow.provider_operations,
                    commit_callback=empty_uow.commit,
                ),
                execution_policy=ProviderExecutionPolicy.supervised_openalex(),
                artifact_storage=storage,
                clock=lambda: NOW,
            ).generate(
                evaluation_id="synthetic-evaluation",
                topic_set=_topic_set(),
            )
        )
    assert empty_transport.calls == []

    generated_text = "\n".join(
        path.read_text(errors="ignore") for path in tmp_path.rglob("*") if path.is_file()
    )
    assert "synthetic-key-never-persisted" not in generated_text
    assert "Synthetic evaluation abstract 1" not in generated_text
    assert '"results":[' not in generated_text
    assert '"human_judgments_generated":false' in generated_text
    assert all(not item.storage_key.startswith("/") for item in first.artifacts)


def test_candidate_pool_uses_topic_maximum_candidates(tmp_path) -> None:
    rate = _response(
        {
            "rate_limit": {
                "daily_remaining_usd": "1",
                "prepaid_remaining_usd": "0",
                "endpoint_costs_usd": {"search": "0.001"},
            }
        }
    )
    works = _response(
        {
            "meta": {
                "count": 20,
                "per_page": 20,
                "next_cursor": None,
                "cost_usd": "0.001",
            },
            "results": [_work(index) for index in range(1, 21)],
        }
    )
    transport = SyntheticTransport([rate, works])
    provider = OpenAlexPaperSearchProvider(
        OpenAlexConfiguration(api_key="synthetic-only"),
        transport=transport,
        clock=lambda: NOW,
        sleeper=lambda _: None,
    )
    uow = InMemoryUnitOfWork()
    result = asyncio.run(
        CandidatePoolGenerator(
            provider=provider,
            provider_operations=ProviderOperationService(
                uow.provider_operations,
                commit_callback=uow.commit,
            ),
            execution_policy=ProviderExecutionPolicy.supervised_openalex(),
            artifact_storage=LocalFilesystemArtifactStorage(tmp_path),
            clock=lambda: NOW,
        ).generate(
            evaluation_id="twenty-candidate-evaluation",
            topic_set=_topic_set(),
        )
    )
    assert len(result.candidates) == 20
    assert transport.calls[1][1]["per_page"] == "20"


def test_candidate_pool_budget_fails_before_transport_call(tmp_path) -> None:
    transport = SyntheticTransport([])
    provider = OpenAlexPaperSearchProvider(
        OpenAlexConfiguration(api_key="synthetic-only"),
        transport=transport,
        clock=lambda: NOW,
    )
    uow = InMemoryUnitOfWork()
    generator = CandidatePoolGenerator(
        provider=provider,
        provider_operations=ProviderOperationService(
            uow.provider_operations,
            commit_callback=uow.commit,
        ),
        execution_policy=ProviderExecutionPolicy(
            budget=ProviderBudget(
                max_provider_requests=3,
                max_llm_calls=0,
                max_input_tokens=0,
                max_output_tokens=0,
                max_cost_minor_units=0,
                live_provider_enabled=True,
            ),
            live_provider_names=frozenset({"openalex"}),
            reservations={"openalex": ProviderReservation(request_count=4)},
            operation_timeout_seconds=90,
        ),
        artifact_storage=LocalFilesystemArtifactStorage(tmp_path),
        clock=lambda: NOW,
    )
    with pytest.raises(EvaluationGenerationError, match="budget exceeded"):
        asyncio.run(
            generator.generate(
                evaluation_id="budget-evaluation",
                topic_set=_topic_set(),
            )
        )
    assert transport.calls == []


def test_candidate_pool_missing_search_evidence_settles_failure(tmp_path) -> None:
    uow = InMemoryUnitOfWork()
    service = ProviderOperationService(
        uow.provider_operations,
        commit_callback=uow.commit,
    )
    with pytest.raises(EvaluationGenerationError, match="required search evidence"):
        asyncio.run(
            CandidatePoolGenerator(
                provider=FakePaperSearchProvider(),
                provider_operations=service,
                execution_policy=ProviderExecutionPolicy.fake_only(),
                artifact_storage=LocalFilesystemArtifactStorage(tmp_path),
                clock=lambda: NOW,
            ).generate(
                evaluation_id="missing-evidence-evaluation",
                topic_set=_topic_set(),
            )
        )
    operations = service.list_for_run(
        project_id="evaluation:missing-evidence-evaluation",
        workflow_run_id="evaluation:missing-evidence-evaluation",
    )
    assert len(operations) == 1
    assert operations[0].status.value == "FAILED"
    assert operations[0].settlement_state.value == "SETTLED"
    assert operations[0].failure_category.value == "MALFORMED_PROVIDER_RESPONSE"


def test_candidate_pool_resume_rejects_corrupted_artifact(tmp_path) -> None:
    rate = _response(
        {
            "rate_limit": {
                "daily_remaining_usd": "1",
                "prepaid_remaining_usd": "0",
                "endpoint_costs_usd": {"search": "0.001"},
            }
        }
    )
    works = _response(
        {
            "meta": {
                "count": 3,
                "per_page": 3,
                "next_cursor": None,
                "cost_usd": "0.001",
            },
            "results": [_work(index) for index in range(1, 4)],
        }
    )
    provider = OpenAlexPaperSearchProvider(
        OpenAlexConfiguration(api_key="synthetic-only"),
        transport=SyntheticTransport([rate, works]),
        clock=lambda: NOW,
    )
    uow = InMemoryUnitOfWork()
    generator = CandidatePoolGenerator(
        provider=provider,
        provider_operations=ProviderOperationService(
            uow.provider_operations,
            commit_callback=uow.commit,
        ),
        execution_policy=ProviderExecutionPolicy.supervised_openalex(),
        artifact_storage=LocalFilesystemArtifactStorage(tmp_path),
        clock=lambda: NOW,
    )
    result = asyncio.run(
        generator.generate(
            evaluation_id="corruption-evaluation",
            topic_set=_topic_set(),
        )
    )
    candidate_artifact = next(
        item for item in result.artifacts if item.logical_name == "candidates.json"
    )
    (tmp_path / candidate_artifact.storage_key).write_bytes(b"corrupted")
    with pytest.raises(EvaluationGenerationError, match="checksum mismatch"):
        asyncio.run(
            generator.generate(
                evaluation_id="corruption-evaluation",
                topic_set=_topic_set(),
            )
        )


def test_three_topic_batch_shares_one_evaluation_request_budget(tmp_path) -> None:
    responses: list[OpenAlexHttpResponse] = []
    for _ in range(3):
        responses.extend(
            [
                _response(
                    {
                        "rate_limit": {
                            "daily_remaining_usd": "1",
                            "prepaid_remaining_usd": "0",
                            "endpoint_costs_usd": {"search": "0.001"},
                        }
                    }
                ),
                _response(
                    {
                        "meta": {
                            "count": 3,
                            "per_page": 3,
                            "next_cursor": None,
                            "cost_usd": "0.001",
                        },
                        "results": [_work(index) for index in range(1, 4)],
                    }
                ),
            ]
        )
    transport = SyntheticTransport(responses)
    provider = OpenAlexPaperSearchProvider(
        OpenAlexConfiguration(api_key="synthetic-only"),
        transport=transport,
        clock=lambda: NOW,
    )
    uow = InMemoryUnitOfWork()
    service = ProviderOperationService(
        uow.provider_operations,
        commit_callback=uow.commit,
    )
    result = asyncio.run(
        CandidatePoolGenerator(
            provider=provider,
            provider_operations=service,
            execution_policy=ProviderExecutionPolicy.supervised_openalex(),
            artifact_storage=LocalFilesystemArtifactStorage(tmp_path),
            clock=lambda: NOW,
        ).generate(
            evaluation_id="three-topic-evaluation",
            topic_set=_three_topic_set(),
        )
    )
    operations = service.list_for_run(
        project_id="evaluation:three-topic-evaluation",
        workflow_run_id="evaluation:three-topic-evaluation",
    )
    assert len(operations) == 3
    assert all(item.settlement_state.value == "SETTLED" for item in operations)
    assert result.evaluation_run.request_count == 6
    assert len(transport.calls) == 6


def test_journaled_operation_restart_resumes_without_provider_call(tmp_path) -> None:
    rate = _response(
        {
            "rate_limit": {
                "daily_remaining_usd": "1",
                "prepaid_remaining_usd": "0",
                "endpoint_costs_usd": {"search": "0.001"},
            }
        }
    )
    works = _response(
        {
            "meta": {
                "count": 3,
                "per_page": 3,
                "next_cursor": None,
                "cost_usd": "0.001",
            },
            "results": [_work(index) for index in range(1, 4)],
        }
    )
    storage = LocalFilesystemArtifactStorage(tmp_path / "artifacts")
    journal_path = tmp_path / "provider_operations.journal.jsonl"
    first_unit = JournaledProviderOperationUnit(journal_path)
    first_transport = SyntheticTransport([rate, works])
    first = asyncio.run(
        CandidatePoolGenerator(
            provider=OpenAlexPaperSearchProvider(
                OpenAlexConfiguration(api_key="synthetic-journal-only"),
                transport=first_transport,
                clock=lambda: NOW,
            ),
            provider_operations=ProviderOperationService(
                first_unit.provider_operations,
                commit_callback=first_unit.commit,
            ),
            execution_policy=ProviderExecutionPolicy.supervised_openalex(),
            artifact_storage=storage,
            clock=lambda: NOW,
        ).generate(
            evaluation_id="journal-evaluation",
            topic_set=_topic_set(),
        )
    )
    assert first.resumed is False
    assert len(first_transport.calls) == 2

    restart_unit = JournaledProviderOperationUnit(journal_path)
    restart_transport = SyntheticTransport([])
    resumed = asyncio.run(
        CandidatePoolGenerator(
            provider=OpenAlexPaperSearchProvider(
                OpenAlexConfiguration(api_key="synthetic-journal-only"),
                transport=restart_transport,
                clock=lambda: NOW,
            ),
            provider_operations=ProviderOperationService(
                restart_unit.provider_operations,
                commit_callback=restart_unit.commit,
            ),
            execution_policy=ProviderExecutionPolicy.supervised_openalex(),
            artifact_storage=storage,
            clock=lambda: NOW,
        ).generate(
            evaluation_id="journal-evaluation",
            topic_set=_topic_set(),
        )
    )
    operations = restart_unit.provider_operations.list_for_run(
        "evaluation:journal-evaluation",
        "evaluation:journal-evaluation",
    )
    assert resumed.resumed is True
    assert restart_transport.calls == []
    assert len(operations) == 1
    assert operations[0].status.value == "SUCCEEDED"
    assert operations[0].settlement_state.value == "SETTLED"
    assert stat.S_IMODE(journal_path.stat().st_mode) == 0o600
    journal_text = journal_path.read_text(encoding="utf-8")
    assert "synthetic-journal-only" not in journal_text
    assert "abstract_inverted_index" not in journal_text


def test_journaled_operation_repository_rejects_partial_record(tmp_path) -> None:
    journal_path = tmp_path / "provider_operations.journal.jsonl"
    journal_path.write_bytes(b'{"partial":true}')
    with pytest.raises(EvaluationOperationJournalError, match="partial trailing"):
        JournaledProviderOperationUnit(journal_path)
