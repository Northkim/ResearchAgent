"""Budget reservation and application-facing artifact gateway tests."""

from __future__ import annotations

from dataclasses import replace

import pytest

from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.persistence.ports import DuplicateEntityError
from backend.research.adapters import LocalFilesystemArtifactStorage
from backend.research.contracts import (
    ProviderBudget,
    ProviderCategory,
    ProviderFailureCategory,
    ProviderOperationKind,
    ProviderReservation,
    SettlementState,
    canonical_hash,
)
from backend.research.services import (
    ArtifactApplicationGateway,
    ArtifactGatewayError,
    BudgetExceededError,
    CreateArtifactContent,
    ProviderOperationService,
)
from backend.persistence.tests.adapter_contracts import (
    contract_execution,
    contract_provider_operation,
)
from backend.research.tests.fixtures import FIXED_TIME


def test_budget_rejects_excess_reservation_without_staging_operation() -> None:
    execution, _, _ = contract_execution("budget-exceeded")
    operation = replace(
        contract_provider_operation(execution, suffix="budget-exceeded"),
        reservation=ProviderReservation(cost_minor_units=1),
    )
    uow = InMemoryUnitOfWork()
    service = ProviderOperationService(uow.provider_operations)

    with pytest.raises(BudgetExceededError) as captured:
        service.reserve(operation, budget=ProviderBudget.fake_only_default())

    assert captured.value.dimension == "estimated_cost"
    assert uow.provider_operations.get(operation.id) is None


def test_budget_counts_llm_calls_separately() -> None:
    execution, _, _ = contract_execution("llm-budget-exceeded")
    operation = replace(
        contract_provider_operation(execution, suffix="llm-budget-exceeded"),
        provider_category=ProviderCategory.LLM,
        operation_kind=ProviderOperationKind.GENERATE_STRUCTURED,
        provider_identity="synthetic-llm",
        model_or_endpoint="deterministic-structured/v1",
    )
    budget = replace(ProviderBudget.fake_only_default(), max_llm_calls=0)
    uow = InMemoryUnitOfWork()

    with pytest.raises(BudgetExceededError) as captured:
        ProviderOperationService(uow.provider_operations).reserve(
            operation,
            budget=budget,
        )

    assert captured.value.dimension == "llm_calls"


def test_live_provider_mode_fails_closed_by_default() -> None:
    execution, _, _ = contract_execution("live-disabled")
    operation = replace(
        contract_provider_operation(execution, suffix="live-disabled"),
        is_live_provider=True,
    )
    uow = InMemoryUnitOfWork()

    with pytest.raises(BudgetExceededError) as captured:
        ProviderOperationService(uow.provider_operations).reserve(
            operation,
            budget=ProviderBudget.fake_only_default(),
        )

    assert captured.value.dimension == "live_provider_disabled"


def test_failure_before_provider_call_releases_reservation() -> None:
    execution, _, _ = contract_execution("budget-release")
    operation = contract_provider_operation(execution, suffix="budget-release")
    uow = InMemoryUnitOfWork()
    service = ProviderOperationService(uow.provider_operations)
    service.reserve(operation, budget=ProviderBudget.fake_only_default())
    failed = service.settle_failure(
        operation.id,
        category=ProviderFailureCategory.CANCELLED,
        at=FIXED_TIME,
        provider_call_started=False,
    )

    assert failed.settlement_state is SettlementState.RELEASED
    assert failed.actual_usage is None


def test_cancelled_operation_releases_unstarted_reservation() -> None:
    execution, _, _ = contract_execution("budget-cancel")
    operation = contract_provider_operation(execution, suffix="budget-cancel")
    uow = InMemoryUnitOfWork()
    service = ProviderOperationService(uow.provider_operations)
    service.reserve(operation, budget=ProviderBudget.fake_only_default())
    cancelled = service.cancel(
        operation.id,
        at=FIXED_TIME,
        provider_call_started=False,
    )

    assert cancelled.failure_category is ProviderFailureCategory.CANCELLED
    assert cancelled.settlement_state is SettlementState.RELEASED


def test_idempotency_key_cannot_be_reused_for_different_request() -> None:
    execution, _, _ = contract_execution("budget-conflict")
    operation = contract_provider_operation(execution, suffix="budget-conflict")
    changed = replace(
        operation,
        id="provider-operation-conflict-second",
        request_fingerprint=canonical_hash({"query": "different"}),
    )
    uow = InMemoryUnitOfWork()
    service = ProviderOperationService(uow.provider_operations)
    service.reserve(operation, budget=ProviderBudget.fake_only_default())

    with pytest.raises(DuplicateEntityError):
        service.reserve(changed, budget=ProviderBudget.fake_only_default())


def test_provider_operation_rollback_discards_reservation() -> None:
    execution, _, _ = contract_execution("budget-rollback")
    operation = contract_provider_operation(execution, suffix="budget-rollback")
    database = InMemoryDatabase()
    writer = InMemoryUnitOfWork(database)
    ProviderOperationService(writer.provider_operations).reserve(
        operation,
        budget=ProviderBudget.fake_only_default(),
    )
    writer.rollback()

    observer = InMemoryUnitOfWork(database)
    assert observer.provider_operations.get(operation.id) is None


def test_artifact_gateway_persists_relative_metadata_and_verifies_after_restart(
    tmp_path,
) -> None:
    database = InMemoryDatabase()
    storage = LocalFilesystemArtifactStorage(tmp_path / "artifacts")
    writer = InMemoryUnitOfWork(database)
    gateway = ArtifactApplicationGateway(unit_of_work=writer, content_storage=storage)
    artifact = gateway.create(
        CreateArtifactContent(
            id="artifact-report-1",
            project_id="project-1",
            workflow_run_id="run-1",
            step_run_id="step-1",
            logical_artifact_id="report",
            logical_name="report.md",
            version=1,
            kind="research_report",
            storage_key="projects/project-1/runs/run-1/report/v1/report.md",
            media_type="text/markdown",
            content=b"# Synthetic report",
            metadata={"schema_version": "research-report/v1"},
            created_at=FIXED_TIME,
        )
    )
    writer.commit()

    restarted = ArtifactApplicationGateway(
        unit_of_work=InMemoryUnitOfWork(database),
        content_storage=LocalFilesystemArtifactStorage(tmp_path / "artifacts"),
    )
    assert artifact.storage_ref == "projects/project-1/runs/run-1/report/v1/report.md"
    assert not artifact.storage_ref.startswith("/")
    assert restarted.list_for_run(project_id="project-1", workflow_run_id="run-1") == (
        artifact,
    )
    assert restarted.read_verified(artifact.id) == b"# Synthetic report"


def test_artifact_gateway_fails_closed_after_content_tampering(tmp_path) -> None:
    uow = InMemoryUnitOfWork()
    storage = LocalFilesystemArtifactStorage(tmp_path)
    gateway = ArtifactApplicationGateway(unit_of_work=uow, content_storage=storage)
    artifact = gateway.create(
        CreateArtifactContent(
            id="artifact-1",
            project_id="project-1",
            workflow_run_id="run-1",
            step_run_id=None,
            logical_artifact_id="papers",
            logical_name="papers.json",
            version=1,
            kind="research_dataset",
            storage_key="runs/run-1/papers.json",
            media_type="application/json",
            content=b"{}",
            created_at=FIXED_TIME,
        )
    )
    (tmp_path / artifact.storage_ref).write_bytes(b"tampered")

    with pytest.raises(ArtifactGatewayError):
        gateway.read_verified(artifact.id)
