"""Reusable adapter contract scenarios shared by in-memory and PostgreSQL tests."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from backend.domain.enums import ApprovalRequestStatus, WorkflowRunStatus, WorkflowStepKind
from backend.domain.models import (
    ApprovalRequest,
    ArtifactMetadata,
    Workflow,
    WorkflowStep,
)
from backend.domain.services import ExecutionCoordinator
from backend.execution_events import EventPayload, ExecutionEvent, ExecutionEventType
from backend.persistence.models import CheckpointBoundary
from backend.persistence.ports import DuplicateEntityError, StaleStateError, UnitOfWork
from backend.research.contracts import (
    ProviderBudget,
    ProviderCategory,
    ProviderFailureCategory,
    ProviderOperation,
    ProviderOperationKind,
    ProviderOperationStatus,
    ProviderReservation,
    ProviderUsage,
    SettlementState,
    canonical_hash,
)
from backend.research.services import BudgetExceededError, ProviderOperationService


class ContractIds:
    def __init__(self, namespace: str) -> None:
        self.namespace = namespace
        self.counts: defaultdict[str, int] = defaultdict(int)

    def __call__(self, prefix: str) -> str:
        self.counts[prefix] += 1
        return f"{prefix}-{self.namespace}-{self.counts[prefix]}"


def contract_clock() -> datetime:
    return datetime(2026, 7, 21, 14, 0, tzinfo=UTC)


def contract_workflow() -> Workflow:
    return Workflow(
        id="adapter-contract-workflow",
        version="1.0.0",
        name="Adapter contract workflow",
        input_schema={"topic": {"type": "string"}},
        steps=(
            WorkflowStep(
                id="search",
                kind=WorkflowStepKind.SKILL,
                uses="mock_paper_search@1.0.0",
                input_mapping={"query": "${inputs.topic}"},
                max_attempts=2,
            ),
        ),
        outputs={"papers": "${nodes.search.outputs.papers}"},
    )


def contract_execution(namespace: str = "contract"):
    ids = ContractIds(namespace)
    coordinator = ExecutionCoordinator(clock=contract_clock, id_factory=ids)
    execution = coordinator.create_workflow_run(
        workflow=contract_workflow(),
        project_id=f"project-{namespace}",
        actor_user_id=f"user-{namespace}",
        idempotency_key=f"request-{namespace}",
        inputs={"topic": "persistent research agents"},
        agent_profile_ref="agent@1.0.0",
    )
    coordinator.start_execution(execution)
    coordinator.mark_step_ready(
        execution,
        step_id="search",
        inputs={"query": "persistent research agents"},
    )
    return execution, coordinator, ids


def save_contract_checkpoints(unit_of_work: UnitOfWork, execution) -> None:
    for checkpoint in execution.checkpoints:
        unit_of_work.checkpoints.save(
            checkpoint,
            boundary=CheckpointBoundary.DOMAIN_TRANSITION,
        )


def contract_provider_operation(execution, *, suffix: str = "primary") -> ProviderOperation:
    step_run = execution.latest_step_run("search")
    return ProviderOperation(
        id=f"provider-operation-{suffix}",
        project_id=execution.workflow_run.project_id,
        workflow_run_id=execution.workflow_run.id,
        logical_step_id="search",
        step_run_id=step_run.id,
        provider_category=ProviderCategory.PAPER_SEARCH,
        operation_kind=ProviderOperationKind.SEARCH,
        provider_identity="synthetic-paper-search",
        adapter_version="1.0.0",
        model_or_endpoint="synthetic-catalog/v1",
        idempotency_key=f"provider-search-{suffix}",
        request_fingerprint=canonical_hash({"query": "persistent research agents"}),
        reservation=ProviderReservation(),
        created_at=contract_clock(),
        updated_at=contract_clock(),
    )


def exercise_full_repository_round_trip(
    make_unit_of_work: Callable[[], UnitOfWork],
) -> None:
    execution, _, _ = contract_execution("round-trip")
    step_run = execution.latest_step_run("search")
    approval = ApprovalRequest(
        id="approval-round-trip",
        project_id=execution.workflow_run.project_id,
        workflow_run_id=execution.workflow_run.id,
        step_run_id=step_run.id,
        policy_key="project_reviewer",
        request_fingerprint="sha256:round-trip",
        prompt="Approve the selected sources?",
        requested_action={"capability": "review_sources"},
        requested_by=execution.agent_session.id,
        permitted_approver_role="reviewer",
        requested_at=contract_clock(),
        expires_at=contract_clock() + timedelta(hours=1),
    )
    artifact = ArtifactMetadata(
        id="artifact-round-trip",
        project_id=execution.workflow_run.project_id,
        logical_artifact_id="sources",
        logical_name="sources.json",
        version=1,
        kind="dataset",
        storage_ref="object://sources/1",
        checksum="sha256:round-trip",
        media_type="application/json",
        size=128,
        producer_run_id=execution.workflow_run.id,
        producer_step_run_id=step_run.id,
        metadata={"verified": False},
        created_at=contract_clock(),
    )
    event = ExecutionEvent(
        id="event-round-trip",
        project_id=execution.workflow_run.project_id,
        workflow_run_id=execution.workflow_run.id,
        sequence=1,
        event_type=ExecutionEventType.WORKFLOW_STARTED,
        payload=EventPayload(data={"status": "RUNNING"}),
        request_id="request-round-trip",
        occurred_at=contract_clock(),
        agent_session_id=execution.agent_session.id,
    )

    writer = make_unit_of_work()
    assert writer.workflows.save(execution, expected_version=None) == 1
    save_contract_checkpoints(writer, execution)
    writer.memory.initialize_context(
        project_id=execution.workflow_run.project_id,
        workflow_run_id=execution.workflow_run.id,
        context={"goal": "round trip"},
        producer="contract-test",
        source_references=("input:topic",),
    )
    writer.artifacts.save(artifact)
    assert writer.approvals.save(approval, expected_version=None) == 1
    writer.events.append(event, expected_sequence=0)
    writer.commit()
    _close(writer)

    reader = make_unit_of_work()
    restored = reader.workflows.get(execution.workflow_run.id)
    assert restored is not None
    restored.checkpoints.extend(reader.checkpoints.list(execution.workflow_run.id))
    assert restored.workflow_run.status is WorkflowRunStatus.RUNNING
    assert restored.workflow == execution.workflow
    assert restored.latest_step_run("search").id == step_run.id
    assert restored.latest_checkpoint.restore_state() == execution.latest_checkpoint.restore_state()
    assert reader.memory.read_context(
        execution.workflow_run.project_id,
        execution.workflow_run.id,
    )["goal"] == "round trip"
    assert reader.artifacts.get(artifact.id) == artifact
    recovered_approval = reader.approvals.get(approval.id)
    assert recovered_approval is not None
    assert recovered_approval.status is ApprovalRequestStatus.PENDING
    assert reader.events.replay(
        execution.workflow_run.project_id,
        execution.workflow_run.id,
    ) == (event,)
    _close(reader)


def exercise_transaction_rollback(
    make_unit_of_work: Callable[[], UnitOfWork],
) -> None:
    execution, _, _ = contract_execution("rollback")
    operation = contract_provider_operation(execution, suffix="rollback")
    uow = make_unit_of_work()
    uow.workflows.save(execution, expected_version=None)
    save_contract_checkpoints(uow, execution)
    uow.memory.initialize_context(
        project_id=execution.workflow_run.project_id,
        workflow_run_id=execution.workflow_run.id,
        context={"goal": "must disappear"},
        producer="contract-test",
    )
    ProviderOperationService(uow.provider_operations).reserve(
        operation,
        budget=ProviderBudget.fake_only_default(),
    )
    uow.rollback()
    _close(uow)

    observer = make_unit_of_work()
    assert observer.workflows.get(execution.workflow_run.id) is None
    assert observer.checkpoints.list(execution.workflow_run.id) == ()
    assert observer.memory.history(
        execution.workflow_run.project_id,
        execution.workflow_run.id,
    ) == ()
    assert observer.provider_operations.get(operation.id) is None
    _close(observer)


def exercise_event_and_approval_recovery(
    make_unit_of_work: Callable[[], UnitOfWork],
) -> None:
    execution, _, _ = contract_execution("approval-recovery")
    step_run = execution.latest_step_run("search")
    baseline = make_unit_of_work()
    baseline.workflows.save(execution, expected_version=None)
    save_contract_checkpoints(baseline, execution)
    baseline.commit()
    _close(baseline)

    approval = ApprovalRequest(
        id="approval-recovery",
        project_id=execution.workflow_run.project_id,
        workflow_run_id=execution.workflow_run.id,
        step_run_id=step_run.id,
        policy_key="project_reviewer",
        request_fingerprint="sha256:approval-recovery",
        prompt="Approve recovery?",
        requested_action={"capability": "resume"},
        requested_by=execution.agent_session.id,
        permitted_approver_role="reviewer",
        requested_at=contract_clock(),
        expires_at=contract_clock() + timedelta(hours=1),
    )
    first_event = ExecutionEvent(
        id="event-approval-recovery-1",
        project_id=execution.workflow_run.project_id,
        workflow_run_id=execution.workflow_run.id,
        sequence=1,
        event_type=ExecutionEventType.APPROVAL_REQUESTED,
        payload=EventPayload(data={"approval_request_id": approval.id}),
        request_id="request-approval-recovery",
        occurred_at=contract_clock(),
        agent_session_id=execution.agent_session.id,
        step_run_id=step_run.id,
    )
    second_event = ExecutionEvent(
        id="event-approval-recovery-2",
        project_id=execution.workflow_run.project_id,
        workflow_run_id=execution.workflow_run.id,
        sequence=2,
        event_type=ExecutionEventType.CHECKPOINT_CREATED,
        payload=EventPayload(data={"checkpoint_id": execution.latest_checkpoint.id}),
        request_id="request-approval-recovery",
        occurred_at=contract_clock(),
        agent_session_id=execution.agent_session.id,
        causation_id=first_event.id,
    )

    writer = make_unit_of_work()
    writer.approvals.save(approval, expected_version=None)
    writer.events.append(first_event, expected_sequence=0)
    writer.events.append(second_event, expected_sequence=1)
    writer.commit()
    _close(writer)

    restarted = make_unit_of_work()
    pending = restarted.approvals.list_pending_for_run(
        approval.project_id,
        approval.workflow_run_id,
    )
    assert len(pending) == 1
    recovered = pending[0]
    assert restarted.events.replay(
        approval.project_id,
        approval.workflow_run_id,
        after_sequence=1,
    ) == (second_event,)
    recovered.approve(
        resolved_by="reviewer-1",
        decision_idempotency_key="decision-recovery",
        current_fingerprint=recovered.request_fingerprint,
        at=contract_clock() + timedelta(minutes=30),
        reason="Recovered and approved",
    )
    restarted.approvals.save(recovered, expected_version=1)
    restarted.commit()
    _close(restarted)

    observer = make_unit_of_work()
    resolved = observer.approvals.get(approval.id)
    assert resolved is not None
    assert resolved.status is ApprovalRequestStatus.APPROVED
    assert observer.approvals.get_version(approval.id) == 2
    assert observer.events.latest_sequence(
        approval.project_id,
        approval.workflow_run_id,
    ) == 2
    _close(observer)


def exercise_optimistic_concurrency(
    make_unit_of_work: Callable[[], UnitOfWork],
) -> None:
    execution, _, _ = contract_execution("concurrency")
    initial = make_unit_of_work()
    initial.workflows.save(execution, expected_version=None)
    save_contract_checkpoints(initial, execution)
    initial.commit()
    _close(initial)

    first = make_unit_of_work()
    second = make_unit_of_work()
    first_execution = first.workflows.get(execution.workflow_run.id)
    second_execution = second.workflows.get(execution.workflow_run.id)
    assert first_execution is not None and second_execution is not None
    first_execution.workflow_run.set_outputs({"writer": "first"})
    second_execution.workflow_run.set_outputs({"writer": "second"})
    first.workflows.update_state(first_execution, expected_version=1)
    second.workflows.update_state(second_execution, expected_version=1)

    first.commit()
    with pytest.raises(StaleStateError):
        second.commit()
    _close(first)
    _close(second)

    observer = make_unit_of_work()
    restored = observer.workflows.get(execution.workflow_run.id)
    assert restored is not None
    assert restored.workflow_run.outputs == {"writer": "first"}
    assert observer.workflows.get_version(execution.workflow_run.id) == 2
    _close(observer)


def exercise_provider_operation_contract(
    make_unit_of_work: Callable[[], UnitOfWork],
) -> None:
    """Exercise reservation, restart visibility, settlement, and stale writes."""

    execution, _, _ = contract_execution("provider-operation")
    initial = make_unit_of_work()
    initial.workflows.save(execution, expected_version=None)
    save_contract_checkpoints(initial, execution)
    operation = contract_provider_operation(execution)
    service = ProviderOperationService(initial.provider_operations)
    reserved, replayed = service.reserve(
        operation,
        budget=ProviderBudget.fake_only_default(),
    )
    assert reserved == operation
    assert replayed is False
    repeated, replayed = service.reserve(
        operation,
        budget=ProviderBudget.fake_only_default(),
    )
    assert repeated == operation
    assert replayed is True
    initial.commit()
    _close(initial)

    first = make_unit_of_work()
    second = make_unit_of_work()
    assert first.provider_operations.list_unsettled(
        project_id=operation.project_id
    ) == (operation,)
    first_service = ProviderOperationService(first.provider_operations)
    second_service = ProviderOperationService(second.provider_operations)
    first_service.mark_running(operation.id, at=contract_clock() + timedelta(seconds=1))
    second_service.mark_running(operation.id, at=contract_clock() + timedelta(seconds=1))
    first.commit()
    with pytest.raises(StaleStateError):
        second.commit()
    _close(first)
    _close(second)

    settlement = make_unit_of_work()
    settlement_service = ProviderOperationService(settlement.provider_operations)
    settled = settlement_service.settle_success(
        operation.id,
        usage=ProviderUsage.zero_cost(
            provider="synthetic-paper-search",
            model_or_endpoint="synthetic-catalog/v1",
            operation_kind=ProviderOperationKind.SEARCH,
        ),
        at=contract_clock() + timedelta(seconds=2),
    )
    settlement.commit()
    _close(settlement)

    observer = make_unit_of_work()
    recovered = observer.provider_operations.get(operation.id)
    assert recovered == settled
    assert recovered is not None
    assert recovered.status is ProviderOperationStatus.SUCCEEDED
    assert recovered.settlement_state is SettlementState.SETTLED
    assert observer.provider_operations.get_version(operation.id) == 3
    assert observer.provider_operations.list_unsettled(
        project_id=operation.project_id
    ) == ()
    _close(observer)


def exercise_provider_operation_failure_and_budget_contract(
    make_unit_of_work: Callable[[], UnitOfWork],
) -> None:
    """Exercise release/settlement, diagnostics, budget, and idempotency rules."""

    execution, _, _ = contract_execution("provider-failure-budget")
    baseline = make_unit_of_work()
    baseline.workflows.save(execution, expected_version=None)
    save_contract_checkpoints(baseline, execution)
    baseline.commit()
    _close(baseline)

    released_operation = contract_provider_operation(execution, suffix="released")
    reservation = make_unit_of_work()
    reservation_service = ProviderOperationService(reservation.provider_operations)
    reservation_service.reserve(
        released_operation,
        budget=ProviderBudget.fake_only_default(),
    )
    reservation.commit()
    _close(reservation)

    preflight_failure = make_unit_of_work()
    released = ProviderOperationService(
        preflight_failure.provider_operations
    ).settle_failure(
        released_operation.id,
        category=ProviderFailureCategory.PROVIDER_AUTHENTICATION,
        at=contract_clock() + timedelta(seconds=1),
        provider_call_started=False,
        diagnostic_metadata={
            "diagnostic_code": "AUTH_CONFIGURATION_UNAVAILABLE",
            "provider_response_retained": False,
        },
    )
    preflight_failure.commit()
    _close(preflight_failure)

    assert released.status is ProviderOperationStatus.FAILED
    assert released.settlement_state is SettlementState.RELEASED
    assert released.actual_usage is None

    started_operation = contract_provider_operation(execution, suffix="started-failure")
    started_uow = make_unit_of_work()
    started_service = ProviderOperationService(started_uow.provider_operations)
    started_service.reserve(
        started_operation,
        budget=ProviderBudget.fake_only_default(),
    )
    started_service.mark_running(
        started_operation.id,
        at=contract_clock() + timedelta(seconds=2),
    )
    started_uow.commit()
    _close(started_uow)

    failed_usage = ProviderUsage(
        provider="synthetic-paper-search",
        model_or_endpoint="synthetic-catalog/v1",
        operation_kind=ProviderOperationKind.SEARCH,
        request_count=1,
        input_tokens=0,
        output_tokens=0,
        estimated_cost_minor_units=0,
        cost_currency="USD",
        latency_ms=25,
        retry_count=1,
        failure_category=ProviderFailureCategory.PROVIDER_TIMEOUT,
        provider_request_ids=("restricted-request-reference",),
    )
    failure_uow = make_unit_of_work()
    failed = ProviderOperationService(
        failure_uow.provider_operations
    ).settle_failure(
        started_operation.id,
        category=ProviderFailureCategory.PROVIDER_TIMEOUT,
        at=contract_clock() + timedelta(seconds=3),
        usage=failed_usage,
        provider_call_started=True,
        diagnostic_metadata={
            "diagnostic_code": "PROVIDER_DEADLINE_EXCEEDED",
            "raw_response_retained": False,
        },
    )
    failure_uow.commit()
    _close(failure_uow)

    observer = make_unit_of_work()
    persisted_released = observer.provider_operations.get(released_operation.id)
    persisted_failed = observer.provider_operations.get(started_operation.id)
    assert persisted_released == released
    assert persisted_failed == failed
    assert persisted_failed is not None
    assert persisted_failed.settlement_state is SettlementState.SETTLED
    assert persisted_failed.actual_usage == failed_usage
    assert dict(persisted_failed.diagnostic_metadata) == {
        "diagnostic_code": "PROVIDER_DEADLINE_EXCEEDED",
        "raw_response_retained": False,
    }

    conflicting = replace(
        started_operation,
        id="provider-operation-idempotency-conflict",
        request_fingerprint=canonical_hash({"query": "different"}),
    )
    observer_service = ProviderOperationService(observer.provider_operations)
    with pytest.raises(DuplicateEntityError):
        observer_service.reserve(
            conflicting,
            budget=ProviderBudget.fake_only_default(),
        )

    budget_limited_operation = contract_provider_operation(
        execution,
        suffix="budget-exceeded",
    )
    one_request_budget = ProviderBudget(
        max_provider_requests=1,
        max_llm_calls=0,
        max_input_tokens=0,
        max_output_tokens=0,
        max_cost_minor_units=0,
    )
    with pytest.raises(BudgetExceededError) as budget_error:
        observer_service.reserve(
            budget_limited_operation,
            budget=one_request_budget,
        )
    assert budget_error.value.dimension == "provider_requests"
    assert observer.provider_operations.get(budget_limited_operation.id) is None
    observer.rollback()
    _close(observer)


def exercise_provider_operation_logical_version_contract(
    make_unit_of_work: Callable[[], UnitOfWork],
) -> None:
    """Reject a logical update that does not advance the domain row version."""

    execution, _, _ = contract_execution("provider-logical-version")
    operation = contract_provider_operation(execution, suffix="logical-version")
    baseline = make_unit_of_work()
    baseline.workflows.save(execution, expected_version=None)
    save_contract_checkpoints(baseline, execution)
    ProviderOperationService(baseline.provider_operations).reserve(
        operation,
        budget=ProviderBudget.fake_only_default(),
    )
    baseline.commit()
    _close(baseline)

    stale = make_unit_of_work()
    current = stale.provider_operations.get(operation.id)
    version = stale.provider_operations.get_version(operation.id)
    assert current is not None and version == 1
    invalid_update = replace(
        current,
        updated_at=contract_clock() + timedelta(seconds=1),
    )
    with pytest.raises(StaleStateError):
        stale.provider_operations.save(invalid_update, expected_version=version)
    stale.rollback()
    _close(stale)


def exercise_provider_operation_update_rollback_contract(
    make_unit_of_work: Callable[[], UnitOfWork],
) -> None:
    """Rollback a provider transition and another repository update together."""

    execution, _, _ = contract_execution("provider-update-rollback")
    operation = contract_provider_operation(execution, suffix="update-rollback")
    baseline = make_unit_of_work()
    baseline.workflows.save(execution, expected_version=None)
    save_contract_checkpoints(baseline, execution)
    ProviderOperationService(baseline.provider_operations).reserve(
        operation,
        budget=ProviderBudget.fake_only_default(),
    )
    baseline.commit()
    _close(baseline)

    transaction = make_unit_of_work()
    loaded_execution = transaction.workflows.get(execution.workflow_run.id)
    assert loaded_execution is not None
    loaded_execution.workflow_run.set_outputs({"must": "rollback"})
    transaction.workflows.update_state(loaded_execution, expected_version=1)
    ProviderOperationService(transaction.provider_operations).mark_running(
        operation.id,
        at=contract_clock() + timedelta(seconds=1),
    )
    transaction.rollback()
    _close(transaction)

    observer = make_unit_of_work()
    restored_execution = observer.workflows.get(execution.workflow_run.id)
    restored_operation = observer.provider_operations.get(operation.id)
    assert restored_execution is not None and restored_operation is not None
    assert dict(restored_execution.workflow_run.outputs) == {}
    assert observer.workflows.get_version(execution.workflow_run.id) == 1
    assert restored_operation.status is ProviderOperationStatus.RESERVED
    assert restored_operation.row_version == 0
    assert observer.provider_operations.get_version(operation.id) == 1
    _close(observer)


def _close(unit_of_work: UnitOfWork) -> None:
    close = getattr(unit_of_work, "close", None)
    if callable(close):
        close()
