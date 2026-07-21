"""Run the reusable persistence contract suite against the in-memory adapter."""

from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork
from backend.persistence.tests.adapter_contracts import (
    exercise_event_and_approval_recovery,
    exercise_full_repository_round_trip,
    exercise_optimistic_concurrency,
    exercise_transaction_rollback,
)


def test_in_memory_full_repository_contract() -> None:
    database = InMemoryDatabase()
    exercise_full_repository_round_trip(lambda: InMemoryUnitOfWork(database))


def test_in_memory_rollback_contract() -> None:
    database = InMemoryDatabase()
    exercise_transaction_rollback(lambda: InMemoryUnitOfWork(database))


def test_in_memory_event_and_approval_recovery_contract() -> None:
    database = InMemoryDatabase()
    exercise_event_and_approval_recovery(lambda: InMemoryUnitOfWork(database))


def test_in_memory_optimistic_concurrency_contract() -> None:
    database = InMemoryDatabase()
    exercise_optimistic_concurrency(lambda: InMemoryUnitOfWork(database))
