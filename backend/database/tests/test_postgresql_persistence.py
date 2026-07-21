"""PostgreSQL repository, transaction, migration, and Runtime recovery tests."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from sqlalchemy import Engine, inspect, text

from backend.agent_runtime import AgentRuntime
from backend.database import SQLAlchemyUnitOfWork, create_async_postgres_engine
from backend.persistence.tests.adapter_contracts import (
    ContractIds,
    contract_clock,
    contract_execution,
    exercise_event_and_approval_recovery,
    exercise_full_repository_round_trip,
    exercise_optimistic_concurrency,
    exercise_transaction_rollback,
)
from backend.skill_system import SkillExecutor, SkillRegistry
from backend.skill_system.runtime import register_fake_skills
from backend.workflow_engine.services import WorkflowExecutionCoordinator


def test_postgresql_schema_is_at_head(postgres_engine: Engine) -> None:
    with postgres_engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20260721_0001"
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
