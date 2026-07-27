"""Fail-closed provider budget reservation and settlement services."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from backend.persistence.ports import (
    DuplicateEntityError,
    ProviderOperationRepository,
    StaleStateError,
)
from backend.research.contracts import (
    ProviderBudget,
    ProviderCategory,
    ProviderFailureCategory,
    ProviderOperation,
    ProviderOperationStatus,
    ProviderReservation,
    ProviderUsage,
    SettlementState,
)


class BudgetExceededError(RuntimeError):
    def __init__(self, dimension: str) -> None:
        self.dimension = dimension
        super().__init__(f"Provider budget exceeded: {dimension}")


@dataclass(frozen=True, slots=True)
class BudgetTotals:
    request_count: int = 0
    llm_call_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_minor_units: int = 0

    def plus(
        self,
        reservation: ProviderReservation,
        *,
        llm_call_count: int = 0,
    ) -> BudgetTotals:
        return BudgetTotals(
            request_count=self.request_count + reservation.request_count,
            llm_call_count=self.llm_call_count + llm_call_count,
            input_tokens=self.input_tokens + reservation.input_tokens,
            output_tokens=self.output_tokens + reservation.output_tokens,
            cost_minor_units=self.cost_minor_units + reservation.cost_minor_units,
        )


class ProviderBudgetEvaluator:
    """Pure calculation over persisted operations; unknowns stay conservative."""

    def totals(self, operations: tuple[ProviderOperation, ...]) -> BudgetTotals:
        totals = BudgetTotals()
        for operation in operations:
            amount = self._accounted_amount(operation)
            totals = totals.plus(
                amount,
                llm_call_count=(
                    amount.request_count
                    if operation.provider_category is ProviderCategory.LLM
                    else 0
                ),
            )
        return totals

    def assert_can_reserve(
        self,
        *,
        budget: ProviderBudget,
        operations: tuple[ProviderOperation, ...],
        reservation: ProviderReservation,
        provider_category: ProviderCategory,
    ) -> None:
        if reservation.cost_currency != budget.cost_currency:
            raise BudgetExceededError("cost_currency")
        projected = self.totals(operations).plus(
            reservation,
            llm_call_count=(
                reservation.request_count
                if provider_category is ProviderCategory.LLM
                else 0
            ),
        )
        checks = (
            ("provider_requests", projected.request_count, budget.max_provider_requests),
            ("llm_calls", projected.llm_call_count, budget.max_llm_calls),
            ("input_tokens", projected.input_tokens, budget.max_input_tokens),
            ("output_tokens", projected.output_tokens, budget.max_output_tokens),
            ("estimated_cost", projected.cost_minor_units, budget.max_cost_minor_units),
        )
        for dimension, actual, limit in checks:
            if actual > limit:
                raise BudgetExceededError(dimension)

    @staticmethod
    def _accounted_amount(operation: ProviderOperation) -> ProviderReservation:
        if operation.settlement_state is SettlementState.RELEASED:
            return ProviderReservation(
                request_count=0,
                input_tokens=0,
                output_tokens=0,
                cost_minor_units=0,
                cost_currency=operation.reservation.cost_currency,
            )
        usage = operation.actual_usage
        if usage is None:
            return operation.reservation
        return ProviderReservation(
            request_count=max(operation.reservation.request_count, usage.request_count),
            input_tokens=(
                operation.reservation.input_tokens
                if usage.input_tokens is None
                else usage.input_tokens
            ),
            output_tokens=(
                operation.reservation.output_tokens
                if usage.output_tokens is None
                else usage.output_tokens
            ),
            cost_minor_units=(
                operation.reservation.cost_minor_units
                if usage.estimated_cost_minor_units is None
                else usage.estimated_cost_minor_units
            ),
            cost_currency=usage.cost_currency or operation.reservation.cost_currency,
        )


class ProviderOperationService:
    """Application service that stages idempotent budgeted operation changes."""

    def __init__(
        self,
        repository: ProviderOperationRepository,
        *,
        evaluator: ProviderBudgetEvaluator | None = None,
    ) -> None:
        self.repository = repository
        self.evaluator = evaluator or ProviderBudgetEvaluator()

    def reserve(
        self,
        operation: ProviderOperation,
        *,
        budget: ProviderBudget,
    ) -> tuple[ProviderOperation, bool]:
        if operation.status is not ProviderOperationStatus.RESERVED:
            raise ValueError("New provider operation must be RESERVED")
        existing = self.repository.get_by_idempotency_key(
            operation.project_id,
            operation.idempotency_key,
        )
        if existing is not None:
            if (
                existing.request_fingerprint != operation.request_fingerprint
                or existing.workflow_run_id != operation.workflow_run_id
                or existing.logical_step_id != operation.logical_step_id
                or existing.step_run_id != operation.step_run_id
                or existing.provider_category is not operation.provider_category
                or existing.operation_kind is not operation.operation_kind
                or existing.provider_identity != operation.provider_identity
                or existing.adapter_version != operation.adapter_version
                or existing.model_or_endpoint != operation.model_or_endpoint
                or existing.reservation != operation.reservation
                or existing.is_live_provider is not operation.is_live_provider
            ):
                raise DuplicateEntityError(
                    "Provider operation idempotency key has conflicting request identity"
                )
            return existing, True
        if operation.is_live_provider and not budget.live_provider_enabled:
            raise BudgetExceededError("live_provider_disabled")
        current = self.repository.list_for_run(
            operation.project_id,
            operation.workflow_run_id,
        )
        self.evaluator.assert_can_reserve(
            budget=budget,
            operations=current,
            reservation=operation.reservation,
            provider_category=operation.provider_category,
        )
        self.repository.save(operation, expected_version=None)
        return operation, False

    def mark_running(self, operation_id: str, *, at: datetime) -> ProviderOperation:
        operation, version = self._load_versioned(operation_id)
        updated = operation.mark_running(at=at)
        self.repository.save(updated, expected_version=version)
        return updated

    def settle_success(
        self,
        operation_id: str,
        *,
        usage: ProviderUsage,
        at: datetime,
    ) -> ProviderOperation:
        operation, version = self._load_versioned(operation_id)
        updated = operation.settle_success(usage, at=at)
        self.repository.save(updated, expected_version=version)
        return updated

    def settle_failure(
        self,
        operation_id: str,
        *,
        category: ProviderFailureCategory,
        at: datetime,
        usage: ProviderUsage | None = None,
        provider_call_started: bool,
        diagnostic_metadata: Mapping[str, Any] | None = None,
    ) -> ProviderOperation:
        operation, version = self._load_versioned(operation_id)
        if provider_call_started and operation.status is not ProviderOperationStatus.RUNNING:
            raise ValueError("A started provider call must have a RUNNING reservation")
        if not provider_call_started and operation.status is not ProviderOperationStatus.RESERVED:
            raise ValueError("Only an unstarted RESERVED operation can release budget")
        updated = operation.settle_failure(
            failure_category=category,
            at=at,
            usage=usage,
            release_reservation=not provider_call_started,
            diagnostic_metadata=diagnostic_metadata,
        )
        self.repository.save(updated, expected_version=version)
        return updated

    def cancel(
        self,
        operation_id: str,
        *,
        at: datetime,
        provider_call_started: bool,
    ) -> ProviderOperation:
        operation, version = self._load_versioned(operation_id)
        if provider_call_started and operation.status is not ProviderOperationStatus.RUNNING:
            raise ValueError("A started provider call must have a RUNNING reservation")
        if not provider_call_started and operation.status is not ProviderOperationStatus.RESERVED:
            raise ValueError("Only an unstarted RESERVED operation can release budget")
        updated = operation.cancel(
            at=at,
            release_reservation=not provider_call_started,
        )
        self.repository.save(updated, expected_version=version)
        return updated

    def _load_versioned(self, operation_id: str) -> tuple[ProviderOperation, int]:
        operation = self.repository.get(operation_id)
        version = self.repository.get_version(operation_id)
        if operation is None or version is None:
            raise StaleStateError(f"ProviderOperation {operation_id} does not exist")
        return operation, version
