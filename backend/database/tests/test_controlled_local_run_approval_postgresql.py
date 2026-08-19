"""PostgreSQL atomicity and migration evidence for controlled-local approval."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
import os
from threading import Barrier

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from backend.api import ApplicationContainer, create_app
from backend.controlled_local_run_approvals import (
    ControlledLocalRunApproval,
    ControlledLocalRunSummary,
)
from backend.database import SQLAlchemyUnitOfWork, create_session_factory
from backend.database.disposable import require_disposable_database
from backend.workflow_packages.generic_experiment_publication import (
    GENERIC_EXPERIMENT_CAPSULE_ID,
)

WORKFLOW_ID = "reproduction-experiment-local-experimental"
NOW = datetime(2026, 8, 17, 12, tzinfo=UTC)
SHA = tuple("sha256:" + character * 64 for character in "123456")


def _request(project_id: str, instance_id: str) -> ControlledLocalRunApproval:
    summary = ControlledLocalRunSummary(
        what_will_run="A bounded local categorical comparison.",
        research_objective="Compare two deterministic text transformations.",
        preparation_method="Reviewed synthetic textual preparation.",
        research_resources=(),
        execution_environment="Controlled non-Python text runtime.",
        network_policy="DISABLED",
        compute_limits=("At most 60 seconds.",),
        expected_outputs=("One bounded categorical result.",),
        evaluation_approach="Compare the declared categories for exact equality.",
        important_assumptions=("Input text is already verified.",),
        important_limitations=("The fixture is deliberately narrow.",),
    )
    return ControlledLocalRunApproval.create(
        project_id=project_id,
        workflow_instance_id=instance_id,
        research_objective_checksum=SHA[0],
        execution_plan_checksum=SHA[1],
        validated_package_checksum=SHA[2],
        runtime_compatibility_checksum=SHA[3],
        capability_checksum=SHA[4],
        summary=summary,
        created_at=NOW,
    )


def _fixture(client: TestClient) -> tuple[str, str]:
    project = client.post("/projects", json={
        "name": "Disposable controlled-local approval",
        "research_topic": "Exact one-use authorization",
        "selected_workflow": "LITERATURE_SEARCH",
    })
    assert project.status_code == 201, project.text
    project_id = project.json()["project_id"]
    instance = client.post(
        f"/projects/{project_id}/workflow-instances",
        json={
            "workflow_definition_id": WORKFLOW_ID,
            "workflow_version": "0.6.0",
            "capsule_id": GENERIC_EXPERIMENT_CAPSULE_ID,
            "capsule_version": "0.9.0",
            "base_revision": 1,
        },
    )
    assert instance.status_code == 201, instance.text
    return project_id, instance.json()["workflow_instance_id"]


def test_controlled_local_approval_migration_downgrade_and_reupgrade(
    postgres_engine,
) -> None:
    database_url = os.environ["REAGENT_TEST_DATABASE_URL"]
    require_disposable_database(
        postgres_engine,
        database_url=database_url,
        expected_identity=os.environ.get("REAGENT_TEST_DATABASE_IDENTITY"),
    )
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    assert "controlled_local_run_approvals" in inspect(postgres_engine).get_table_names()
    command.downgrade(config, "20260817_0029")
    try:
        assert "controlled_local_run_approvals" not in inspect(postgres_engine).get_table_names()
        command.upgrade(config, "20260817_0030")
        assert "controlled_local_run_approvals" in inspect(postgres_engine).get_table_names()
        with postgres_engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260817_0030"
    finally:
        command.upgrade(config, "head")


def test_exactly_one_attempt_consumes_and_state_survives_restart(
    postgres_engine, tmp_path,
) -> None:
    session_factory = create_session_factory(postgres_engine)
    container = ApplicationContainer(
        unit_of_work_factory=lambda: SQLAlchemyUnitOfWork(session_factory),
        local_package_root=str(tmp_path / "packages"),
        clock=lambda: NOW,
    )
    client = TestClient(create_app(container))
    project_id, instance_id = _fixture(client)
    path = f"/projects/{project_id}/workflow-instances/{instance_id}/run-approvals"
    request = _request(project_id, instance_id)
    try:
        with postgres_engine.connect() as connection:
            hosted_before = (
                connection.scalar(text("SELECT count(*) FROM approval_requests")),
                connection.scalar(text("SELECT count(*) FROM workflow_runs")),
            )
        created = client.post(path, json=request.request_dict())
        assert created.status_code == 201, created.text
        approved = client.post(
            f"{path}/{request.request_id}/approve",
            json={
                "execution_plan_checksum": request.execution_plan_checksum,
                "request_checksum": request.request_checksum,
                "idempotency_key": "postgres-owner-decision",
            },
        )
        assert approved.status_code == 200, approved.text

        barrier = Barrier(2)

        def consume(character: str):
            barrier.wait()
            return client.post(
                f"{path}/{request.request_id}/consume",
                json={
                    "execution_plan_checksum": request.execution_plan_checksum,
                    "attempt_id": "attempt-" + character * 32,
                },
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = tuple(pool.map(consume, ("a", "b")))
        assert sorted(response.status_code for response in responses) == [200, 409]
        winner = next(response for response in responses if response.status_code == 200)
        loser = next(response for response in responses if response.status_code == 409)
        assert loser.json()["error"]["code"] == "ALREADY_CONSUMED"

        attempt_id = winner.json()["receipt"]["attempt_id"]
        retry = client.post(
            f"{path}/{request.request_id}/consume",
            json={
                "execution_plan_checksum": request.execution_plan_checksum,
                "attempt_id": attempt_id,
            },
        )
        assert retry.status_code == 200
        assert retry.json() == winner.json()

        restarted = TestClient(create_app(container))
        observed = restarted.get(path.removesuffix("s"))
        assert observed.status_code == 200
        assert observed.json()["request"]["status"] == "CONSUMED"
        assert observed.json()["request"]["consumed_attempt_id"] == attempt_id
        with postgres_engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT count(*) FROM approval_requests")),
                connection.scalar(text("SELECT count(*) FROM workflow_runs")),
            ) == hosted_before
    finally:
        # The repository harness identity-verifies and drops this whole database.
        # Per-table cleanup would be both redundant and weaker than that boundary.
        pass
