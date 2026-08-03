"""PostgreSQL repository, transaction, migration, and Runtime recovery tests."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import replace

import pytest
from sqlalchemy import Engine, inspect, text

from backend.agent_runtime import AgentRuntime
from backend.database import SQLAlchemyUnitOfWork, create_async_postgres_engine
from backend.persistence.ports import DuplicateEntityError
from backend.persistence.tests.adapter_contracts import (
    ContractIds,
    contract_clock,
    contract_execution,
    contract_provider_operation,
    exercise_event_and_approval_recovery,
    exercise_full_repository_round_trip,
    exercise_optimistic_concurrency,
    exercise_provider_operation_contract,
    exercise_provider_operation_failure_and_budget_contract,
    exercise_provider_operation_logical_version_contract,
    exercise_provider_operation_update_rollback_contract,
    exercise_transaction_rollback,
    save_contract_checkpoints,
)
from backend.research.contracts import ProviderBudget
from backend.research.services import ProviderOperationService, ProvenanceValidator
from backend.research.tests.fixtures import valid_manifest
from backend.skill_system import SkillExecutor, SkillRegistry
from backend.skill_system.runtime import register_fake_skills
from backend.workflow_engine.services import WorkflowExecutionCoordinator


def test_postgresql_schema_is_at_head(postgres_engine: Engine) -> None:
    with postgres_engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20260803_0003"
        )
    assert set(inspect(postgres_engine).get_table_names()) >= {
        "workflow_definitions",
        "workflow_runs",
        "workflow_step_runs",
        "agent_sessions",
        "checkpoints",
        "checkpoint_records",
        "memory_revisions",
        "artifacts",
        "approval_requests",
        "execution_events",
        "provider_operations",
        "uploaded_progress_reports",
        "project_progress_projections",
    }


def test_psycopg_async_engine_connects(postgres_engine: Engine) -> None:
    async def verify() -> None:
        engine = create_async_postgres_engine(
            postgres_engine.url.render_as_string(hide_password=False)
        )
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT 1")) == 1
        await engine.dispose()

    asyncio.run(verify())


def test_postgresql_full_repository_contract(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
) -> None:
    exercise_full_repository_round_trip(sql_uow_factory)


def test_postgresql_rollback_contract(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
) -> None:
    exercise_transaction_rollback(sql_uow_factory)


def test_postgresql_event_and_approval_recovery_contract(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
) -> None:
    exercise_event_and_approval_recovery(sql_uow_factory)


def test_postgresql_concurrent_update_contract(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
) -> None:
    exercise_optimistic_concurrency(sql_uow_factory)


def test_postgresql_provider_operation_contract(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
) -> None:
    exercise_provider_operation_contract(sql_uow_factory)


def test_postgresql_provider_operation_failure_and_budget_contract(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
) -> None:
    exercise_provider_operation_failure_and_budget_contract(sql_uow_factory)


def test_postgresql_provider_operation_logical_version_contract(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
) -> None:
    exercise_provider_operation_logical_version_contract(sql_uow_factory)


def test_postgresql_provider_operation_update_rollback_contract(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
) -> None:
    exercise_provider_operation_update_rollback_contract(sql_uow_factory)


def test_postgresql_provider_operation_foreign_key_protection(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
) -> None:
    first_execution, _, _ = contract_execution("provider-fk-first")
    second_execution, _, _ = contract_execution("provider-fk-second")
    baseline = sql_uow_factory()
    baseline.workflows.save(first_execution, expected_version=None)
    baseline.workflows.save(second_execution, expected_version=None)
    save_contract_checkpoints(baseline, first_execution)
    save_contract_checkpoints(baseline, second_execution)
    baseline.commit()
    baseline.close()

    cross_project = replace(
        contract_provider_operation(first_execution, suffix="cross-project"),
        project_id=second_execution.workflow_run.project_id,
    )
    project_scope = sql_uow_factory()
    ProviderOperationService(project_scope.provider_operations).reserve(
        cross_project,
        budget=ProviderBudget.fake_only_default(),
    )
    with pytest.raises(DuplicateEntityError):
        project_scope.commit()
    project_scope.close()

    cross_step = replace(
        contract_provider_operation(first_execution, suffix="cross-step"),
        step_run_id=second_execution.latest_step_run("search").id,
    )
    step_scope = sql_uow_factory()
    ProviderOperationService(step_scope.provider_operations).reserve(
        cross_step,
        budget=ProviderBudget.fake_only_default(),
    )
    with pytest.raises(DuplicateEntityError):
        step_scope.commit()
    step_scope.close()

    observer = sql_uow_factory()
    assert observer.provider_operations.list_for_run(
        first_execution.workflow_run.project_id,
        first_execution.workflow_run.id,
    ) == ()
    observer.close()


def test_postgresql_unsettled_operation_blocks_provenance_publication(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
) -> None:
    execution, _, _ = contract_execution("provider-provenance")
    operation = contract_provider_operation(execution, suffix="provenance")
    writer = sql_uow_factory()
    writer.workflows.save(execution, expected_version=None)
    save_contract_checkpoints(writer, execution)
    ProviderOperationService(writer.provider_operations).reserve(
        operation,
        budget=ProviderBudget.fake_only_default(),
    )
    writer.commit()
    writer.close()

    restarted = sql_uow_factory()
    persisted = restarted.provider_operations.get(operation.id)
    assert persisted is not None
    validation = ProvenanceValidator().validate(
        replace(valid_manifest(), provider_operations=(persisted,))
    )
    assert not validation.publishable
    assert "UNSETTLED_PROVIDER_OPERATION" in {
        issue.code for issue in validation.errors
    }
    restarted.close()


def test_postgresql_runtime_restart_recovery(
    sql_uow_factory: Callable[[], SQLAlchemyUnitOfWork],
) -> None:
    execution, _, _ = contract_execution("runtime-restart")
    registry = SkillRegistry()
    register_fake_skills(registry)

    first_ids = ContractIds("runtime-first")
    first_runtime = AgentRuntime(
        workflow_coordinator=WorkflowExecutionCoordinator(
            domain_coordinator=execution_coordinator(first_ids)
        ),
        skill_executor=SkillExecutor(registry),
        unit_of_work=sql_uow_factory(),
    )
    first_result = asyncio.run(first_runtime.run(execution))
    run_id = execution.workflow_run.id
    first_runtime.uow.close()

    restarted_runtime = AgentRuntime(
        workflow_coordinator=WorkflowExecutionCoordinator(
            domain_coordinator=execution_coordinator(
                ContractIds("runtime-restarted")
            )
        ),
        skill_executor=SkillExecutor(registry),
        unit_of_work=sql_uow_factory(),
    )
    repeated_result = asyncio.run(restarted_runtime.run(run_id))
    assert repeated_result == first_result
    assert restarted_runtime.uow.workflows.get_version(run_id) is not None
    restarted_runtime.uow.close()


def execution_coordinator(ids: ContractIds):
    from backend.domain.services import ExecutionCoordinator

    return ExecutionCoordinator(clock=contract_clock, id_factory=ids)
