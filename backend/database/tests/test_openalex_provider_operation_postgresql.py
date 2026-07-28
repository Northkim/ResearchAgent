"""Network-free PostgreSQL proof for supervised OpenAlex operation persistence."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from backend.database import SQLAlchemyUnitOfWork
from backend.persistence.tests.adapter_contracts import (
    contract_execution,
    save_contract_checkpoints,
)
from backend.research.adapters import (
    LocalFilesystemArtifactStorage,
    OpenAlexConfiguration,
    OpenAlexHttpResponse,
    OpenAlexPaperSearchProvider,
)
from backend.research.contracts import ResearchQuery, canonical_hash
from backend.research.services import ProviderExecutionPolicy, ProviderOperationService
from backend.research.skills import search_papers
from backend.skill_system.exceptions import SkillExecutionFailure
from backend.skill_system.models import SkillCapabilities, SkillExecutionContext


class _SyntheticTransport:
    def __init__(self) -> None:
        self.calls = 0

    async def get(self, path, *, params, timeout_seconds, headers):
        del params, timeout_seconds, headers
        self.calls += 1
        if path == "/rate-limit":
            value = {
                "rate_limit": {
                    "daily_remaining_usd": 1,
                    "endpoint_costs_usd": {"search": 0.001},
                }
            }
        else:
            value = {
                "meta": {
                    "count": 3,
                    "per_page": 3,
                    "next_cursor": None,
                    "cost_usd": 0.001,
                },
                "results": [
                    {
                        "id": f"https://openalex.org/W{index}",
                        "doi": f"https://doi.org/10.1234/synthetic.{index}",
                        "display_name": f"Synthetic OpenAlex-shaped record {index}",
                        "authorships": [
                            {
                                "author": {
                                    "id": f"https://openalex.org/A{index}",
                                    "display_name": f"Synthetic Author {index}",
                                }
                            }
                        ],
                        "abstract_inverted_index": {
                            "Synthetic": [0],
                            "abstract": [1],
                            str(index): [2],
                        },
                        "publication_year": 2020 + index,
                        "primary_location": {
                            "source": {"display_name": "Synthetic Venue"}
                        },
                    }
                    for index in range(1, 4)
                ],
            }
        return OpenAlexHttpResponse(
            status_code=200,
            body=json.dumps(value).encode(),
        )


def _context(
    uow: SQLAlchemyUnitOfWork,
    provider: OpenAlexPaperSearchProvider,
    storage: LocalFilesystemArtifactStorage,
    *,
    project_id: str,
    workflow_run_id: str,
) -> SkillExecutionContext:
    return SkillExecutionContext(
        project_id=project_id,
        workflow_run_id=workflow_run_id,
        workflow_id="guided-literature-review",
        workflow_version="2.0.0",
        step_id="search_papers",
        step_run_id="openalex-search-step",
        attempt=1,
        capabilities=SkillCapabilities(
            paper_search=provider,
            artifact_storage=storage,
            provider_operations=ProviderOperationService(
                uow.provider_operations,
                commit_callback=uow.commit,
            ),
            provider_execution_policy=ProviderExecutionPolicy.supervised_openalex(),
        ),
    )


def test_openalex_operation_settlement_reconstructs_and_replay_is_network_free(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
    tmp_path,
) -> None:
    transport = _SyntheticTransport()
    provider = OpenAlexPaperSearchProvider(
        OpenAlexConfiguration(),
        transport=transport,
        clock=lambda: datetime.now(UTC),
    )
    storage = LocalFilesystemArtifactStorage(tmp_path / "artifacts")
    query = ResearchQuery(
        topic="supervised PostgreSQL adapter evidence",
        year_from=2020,
        year_to=2026,
        max_results=3,
    )
    execution, _, _ = contract_execution("openalex-postgres")
    first = sql_uow_factory()
    try:
        first.workflows.save(execution, expected_version=None)
        save_contract_checkpoints(first, execution)
        first.commit()
        output = asyncio.run(
            search_papers(
                {"query": query.to_dict()},
                _context(
                    first,
                    provider,
                    storage,
                    project_id=execution.workflow_run.project_id,
                    workflow_run_id=execution.workflow_run.id,
                ),
            )
        )
        operation_id = output.output_data["provider_operation_ids"][0]
    finally:
        first.close()

    restarted = sql_uow_factory()
    try:
        operation = restarted.provider_operations.get(operation_id)
        assert operation is not None
        assert operation.provider_identity == "openalex"
        assert operation.is_live_provider is True
        assert operation.status.value == "SUCCEEDED"
        assert operation.settlement_state.value == "SETTLED"
        assert operation.reservation.request_count == 4
        assert operation.actual_usage.request_count == 2
        assert operation.actual_usage.estimated_cost_minor_units == 0
        assert operation.request_fingerprint == canonical_hash(
            provider.request_identity(query, limit=3)
        )
    finally:
        restarted.close()

    # The exact hash is checked without exposing request values or credentials.
    replay = sql_uow_factory()
    try:
        operation = replay.provider_operations.get(operation_id)
        assert operation.request_fingerprint == canonical_hash(
            provider.request_identity(query, limit=3)
        )
        with pytest.raises(SkillExecutionFailure) as caught:
            asyncio.run(
                search_papers(
                    {"query": query.to_dict()},
                    _context(
                        replay,
                        provider,
                        storage,
                        project_id=execution.workflow_run.project_id,
                        workflow_run_id=execution.workflow_run.id,
                    ),
                )
            )
        assert caught.value.code == "PROVIDER_REPLAY_REQUIRES_PERSISTED_OUTPUT"
        assert transport.calls == 2
    finally:
        replay.close()
