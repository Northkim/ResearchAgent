"""SQLAlchemy WorkflowRepository adapter."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database.orm import (
    AgentSessionORM,
    StepRunORM,
    WorkflowDefinitionORM,
    WorkflowRunORM,
)
from backend.database.serialization import (
    workflow_document_hash,
    workflow_from_document,
    workflow_to_document,
)
from backend.domain.enums import AgentSessionStatus, StepRunStatus, WorkflowRunStatus
from backend.domain.models import Workflow
from backend.domain.services import ExecutionState
from backend.persistence.models._immutability import thaw_json
from backend.persistence.models.execution_record import (
    AgentSessionRecord,
    StepRunRecord,
    WorkflowExecutionRecord,
    WorkflowRunRecord,
)
from backend.persistence.ports import (
    DuplicateEntityError,
    PersistenceError,
    StaleStateError,
    WorkflowRepository,
)

from ._helpers import pending_by_composite_key, pending_by_id, pending_instances


class SQLAlchemyWorkflowRepository(WorkflowRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(
        self,
        execution: ExecutionState,
        *,
        expected_version: int | None,
    ) -> int:
        run = execution.workflow_run
        row = pending_by_id(self.session, WorkflowRunORM, run.id)
        if row is None:
            row = self.session.get(WorkflowRunORM, run.id)

        if expected_version is None:
            if row is not None:
                raise StaleStateError(
                    f"WorkflowRun {run.id} already exists at persistence version "
                    f"{row.persistence_version}"
                )
            conflicting = self._find_idempotency_owner(
                run.project_id,
                run.idempotency_key,
            )
            if conflicting is not None:
                raise DuplicateEntityError(
                    "Workflow execution idempotency key is already owned by "
                    f"WorkflowRun {conflicting}"
                )
            next_version = 1
            self._ensure_workflow_definition(execution)
            row = WorkflowRunORM(id=run.id)
            self._apply_run(row, execution, next_version)
            self.session.add(row)
        else:
            if row is None:
                raise StaleStateError(f"WorkflowRun {run.id} does not exist")
            if row.persistence_version != expected_version:
                raise StaleStateError(
                    f"WorkflowRun {run.id} expected persistence version "
                    f"{expected_version}; found {row.persistence_version}"
                )
            if (row.workflow_id, row.workflow_version) != (
                execution.workflow.id,
                execution.workflow.version,
            ):
                raise DuplicateEntityError(
                    f"WorkflowRun {run.id} cannot change its pinned workflow"
                )
            self._ensure_workflow_definition(execution)
            next_version = expected_version + 1
            self._apply_run(row, execution, next_version)

        self._upsert_agent_session(execution)
        self._upsert_step_runs(execution)
        return next_version

    def get(self, workflow_run_id: str) -> ExecutionState | None:
        row = pending_by_id(self.session, WorkflowRunORM, workflow_run_id)
        if row is None:
            row = self.session.get(WorkflowRunORM, workflow_run_id)
        if row is None:
            return None

        definition = pending_by_composite_key(
            self.session,
            WorkflowDefinitionORM,
            (row.workflow_id, row.workflow_version),
            ("workflow_id", "version"),
        )
        if definition is None:
            definition = self.session.get(
                WorkflowDefinitionORM,
                (row.workflow_id, row.workflow_version),
            )
        if definition is None:
            raise PersistenceError(
                f"WorkflowRun {row.id} references a missing workflow definition"
            )

        agent_rows = list(
            self.session.scalars(
                select(AgentSessionORM)
                .where(AgentSessionORM.workflow_run_id == row.id)
                .order_by(AgentSessionORM.role, AgentSessionORM.id)
            )
        )
        agent_rows.extend(
            instance
            for instance in pending_instances(self.session, AgentSessionORM)
            if instance.workflow_run_id == row.id and instance not in agent_rows
        )
        if not agent_rows:
            raise PersistenceError(f"WorkflowRun {row.id} has no AgentSession")
        primary = next(
            (candidate for candidate in agent_rows if candidate.role == "primary"),
            agent_rows[0],
        )

        step_rows = list(
            self.session.scalars(
                select(StepRunORM)
                .where(StepRunORM.workflow_run_id == row.id)
                .order_by(StepRunORM.ordinal, StepRunORM.id)
            )
        )
        step_rows.extend(
            instance
            for instance in pending_instances(self.session, StepRunORM)
            if instance.workflow_run_id == row.id and instance not in step_rows
        )
        step_rows.sort(key=lambda candidate: (candidate.ordinal, candidate.id))

        record = WorkflowExecutionRecord(
            persistence_version=row.persistence_version,
            workflow=workflow_from_document(definition.definition_json),
            workflow_run=self._run_record(row),
            agent_session=self._agent_record(primary),
            step_runs=tuple(self._step_record(candidate) for candidate in step_rows),
        )
        return record.to_execution()

    def get_version(self, workflow_run_id: str) -> int | None:
        row = pending_by_id(self.session, WorkflowRunORM, workflow_run_id)
        if row is None:
            row = self.session.get(WorkflowRunORM, workflow_run_id)
        return row.persistence_version if row is not None else None

    def get_by_idempotency_key(
        self,
        project_id: str,
        idempotency_key: str,
    ) -> ExecutionState | None:
        pending = sorted(
            (
                row
                for row in pending_instances(self.session, WorkflowRunORM)
                if row.project_id == project_id
                and row.idempotency_key == idempotency_key
            ),
            key=lambda candidate: candidate.id,
        )
        if pending:
            return self.get(pending[0].id)
        row = self.session.scalar(
            select(WorkflowRunORM)
            .where(
                WorkflowRunORM.project_id == project_id,
                WorkflowRunORM.idempotency_key == idempotency_key,
            )
            .order_by(WorkflowRunORM.id)
            .limit(1)
        )
        return self.get(row.id) if row is not None else None

    def list_runs(
        self,
        *,
        status: WorkflowRunStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[ExecutionState, ...]:
        statement = select(WorkflowRunORM.id)
        if status is not None:
            statement = statement.where(WorkflowRunORM.status == status.value)
        statement = statement.order_by(
            WorkflowRunORM.created_at.desc(),
            WorkflowRunORM.id.desc(),
        ).offset(offset).limit(limit)
        executions = []
        for workflow_run_id in self.session.scalars(statement):
            execution = self.get(workflow_run_id)
            if execution is not None:
                executions.append(execution)
        return tuple(executions)

    def count_runs(self, *, status: WorkflowRunStatus | None = None) -> int:
        statement = select(func.count()).select_from(WorkflowRunORM)
        if status is not None:
            statement = statement.where(WorkflowRunORM.status == status.value)
        return int(self.session.scalar(statement) or 0)

    def list_definitions(self) -> tuple[Workflow, ...]:
        rows = self.session.scalars(
            select(WorkflowDefinitionORM).order_by(
                WorkflowDefinitionORM.workflow_id,
                WorkflowDefinitionORM.version,
            )
        )
        return tuple(workflow_from_document(row.definition_json) for row in rows)

    def _ensure_workflow_definition(self, execution: ExecutionState) -> None:
        workflow = execution.workflow
        document = workflow_to_document(workflow)
        definition_hash = workflow_document_hash(document)
        row = pending_by_composite_key(
            self.session,
            WorkflowDefinitionORM,
            (workflow.id, workflow.version),
            ("workflow_id", "version"),
        )
        if row is None:
            row = self.session.get(
                WorkflowDefinitionORM,
                (workflow.id, workflow.version),
            )
        if row is not None:
            if row.definition_hash != definition_hash or row.definition_json != document:
                raise DuplicateEntityError(
                    f"Workflow {workflow.id}@{workflow.version} has conflicting content"
                )
            return
        self.session.add(
            WorkflowDefinitionORM(
                workflow_id=workflow.id,
                version=workflow.version,
                schema_version=workflow.schema_version,
                name=workflow.name,
                definition_json=document,
                definition_hash=definition_hash,
                created_at=execution.workflow_run.created_at,
            )
        )

    def _find_idempotency_owner(
        self,
        project_id: str,
        idempotency_key: str,
    ) -> str | None:
        pending = next(
            (
                row.id
                for row in pending_instances(self.session, WorkflowRunORM)
                if row.project_id == project_id
                and row.idempotency_key == idempotency_key
            ),
            None,
        )
        if pending is not None:
            return pending
        return self.session.scalar(
            select(WorkflowRunORM.id)
            .where(
                WorkflowRunORM.project_id == project_id,
                WorkflowRunORM.idempotency_key == idempotency_key,
            )
            .order_by(WorkflowRunORM.id)
            .limit(1)
        )

    @staticmethod
    def _apply_run(
        row: WorkflowRunORM,
        execution: ExecutionState,
        persistence_version: int,
    ) -> None:
        run = execution.workflow_run
        row.project_id = run.project_id
        row.workflow_id = execution.workflow.id
        row.workflow_version = execution.workflow.version
        row.actor_user_id = run.actor_user_id
        row.idempotency_key = run.idempotency_key
        row.inputs_json = thaw_json(run.inputs)
        row.status = run.status.value
        row.outputs_json = thaw_json(run.outputs)
        row.wait_reason = run.wait_reason
        row.error_code = run.error_code
        row.row_version = run.row_version
        row.persistence_version = persistence_version
        row.created_at = run.created_at
        row.updated_at = run.updated_at

    def _upsert_agent_session(self, execution: ExecutionState) -> None:
        agent = execution.agent_session
        row = pending_by_id(self.session, AgentSessionORM, agent.id)
        if row is None:
            row = self.session.get(AgentSessionORM, agent.id)
        if row is None:
            row = AgentSessionORM(id=agent.id)
            self.session.add(row)
        elif row.workflow_run_id != agent.workflow_run_id:
            raise DuplicateEntityError(
                f"AgentSession ID {agent.id} belongs to another WorkflowRun"
            )
        row.project_id = agent.project_id
        row.workflow_run_id = agent.workflow_run_id
        row.agent_profile_ref = agent.agent_profile_ref
        row.role = agent.role
        row.status = agent.status.value
        row.state_json = thaw_json(agent.state)
        row.row_version = agent.row_version
        row.created_at = agent.created_at
        row.updated_at = agent.updated_at

    def _upsert_step_runs(self, execution: ExecutionState) -> None:
        for ordinal, step in enumerate(execution.step_runs, start=1):
            row = pending_by_id(self.session, StepRunORM, step.id)
            if row is None:
                row = self.session.get(StepRunORM, step.id)
            if row is None:
                row = StepRunORM(id=step.id)
                self.session.add(row)
            elif row.workflow_run_id != step.workflow_run_id:
                raise DuplicateEntityError(
                    f"StepRun ID {step.id} belongs to another WorkflowRun"
                )
            row.workflow_run_id = step.workflow_run_id
            row.ordinal = ordinal
            row.step_id = step.step_id
            row.attempt = step.attempt
            row.idempotency_key = step.idempotency_key
            row.inputs_json = thaw_json(step.inputs)
            row.status = step.status.value
            row.outputs_json = thaw_json(step.outputs)
            row.error_code = step.error_code
            row.row_version = step.row_version
            row.created_at = step.created_at
            row.updated_at = step.updated_at
            row.started_at = step.started_at
            row.finished_at = step.finished_at

    @staticmethod
    def _run_record(row: WorkflowRunORM) -> WorkflowRunRecord:
        return WorkflowRunRecord(
            id=row.id,
            project_id=row.project_id,
            workflow_id=row.workflow_id,
            workflow_version=row.workflow_version,
            actor_user_id=row.actor_user_id,
            idempotency_key=row.idempotency_key,
            inputs=row.inputs_json,
            status=WorkflowRunStatus(row.status),
            outputs=row.outputs_json,
            wait_reason=row.wait_reason,
            error_code=row.error_code,
            row_version=row.row_version,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _agent_record(row: AgentSessionORM) -> AgentSessionRecord:
        return AgentSessionRecord(
            id=row.id,
            project_id=row.project_id,
            workflow_run_id=row.workflow_run_id,
            agent_profile_ref=row.agent_profile_ref,
            role=row.role,
            status=AgentSessionStatus(row.status),
            state=row.state_json,
            row_version=row.row_version,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _step_record(row: StepRunORM) -> StepRunRecord:
        return StepRunRecord(
            id=row.id,
            workflow_run_id=row.workflow_run_id,
            step_id=row.step_id,
            attempt=row.attempt,
            idempotency_key=row.idempotency_key,
            inputs=row.inputs_json,
            status=StepRunStatus(row.status),
            outputs=row.outputs_json,
            error_code=row.error_code,
            row_version=row.row_version,
            created_at=row.created_at,
            updated_at=row.updated_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
        )
