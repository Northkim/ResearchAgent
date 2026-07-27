"""Workflow-run application use cases and their transaction boundaries."""

from __future__ import annotations

from backend.agent_runtime.runtime import AgentRuntimeError
from backend.domain.exceptions import DomainError, ExecutionNotResumableError
from collections.abc import Callable

from backend.domain.models import Workflow, WorkflowStep
from backend.domain.services import ExecutionCoordinator
from backend.persistence.models import CheckpointBoundary
from backend.persistence.ports import (
    DuplicateEntityError,
    PersistenceError,
    StaleStateError,
    UnitOfWork,
)
from backend.workflow_engine.exceptions import WorkflowEngineError
from backend.workflow_engine.models import WorkflowDefinition
from backend.workflow_engine.services import WorkflowValidator

from ..commands import (
    CreateCatalogWorkflowRunCommand,
    CreateWorkflowRunCommand,
    StepSpec,
    WorkflowSpec,
)
from ..errors import ApplicationConflictError, ApplicationValidationError
from ..execution import ExecutionDispatcher, ExecutionRequest
from ..views import WorkflowRunView
from ._shared import load_execution, load_run_view


class CreateWorkflowRunService:
    """Validate, create, and atomically persist an unstarted execution."""

    def __init__(
        self,
        *,
        unit_of_work: UnitOfWork,
        domain_coordinator: ExecutionCoordinator,
        validator: WorkflowValidator | None = None,
    ) -> None:
        self.uow = unit_of_work
        self.domain = domain_coordinator
        self.validator = validator or WorkflowValidator()

    def execute(self, command: CreateWorkflowRunCommand) -> WorkflowRunView:
        try:
            workflow = self._build_workflow(command)
            self.validator.validate(WorkflowDefinition.from_domain(workflow))
        except (DomainError, WorkflowEngineError) as error:
            self.uow.rollback()
            raise ApplicationValidationError(str(error)) from error

        existing = self.uow.workflows.get_by_idempotency_key(
            command.project_id,
            command.idempotency_key,
        )
        if existing is not None:
            self._verify_idempotent_request(existing, command, workflow)
            existing.checkpoints.extend(
                self.uow.checkpoints.list(existing.workflow_run.id)
            )
            return WorkflowRunView.from_execution(existing)

        try:
            execution = self.domain.create_workflow_run(
                workflow=workflow,
                project_id=command.project_id,
                actor_user_id=command.actor_user_id,
                idempotency_key=command.idempotency_key,
                inputs=command.inputs,
                agent_profile_ref=command.agent_profile_ref,
            )
            self.uow.workflows.save(execution, expected_version=None)
            self.uow.checkpoints.save(
                execution.latest_checkpoint,
                boundary=CheckpointBoundary.BASELINE,
            )
            self.uow.commit()
            return WorkflowRunView.from_execution(execution)
        except (DomainError, WorkflowEngineError) as error:
            self.uow.rollback()
            raise ApplicationValidationError(str(error)) from error
        except (DuplicateEntityError, StaleStateError) as error:
            self.uow.rollback()
            raise ApplicationConflictError(str(error)) from error
        except Exception:
            self.uow.rollback()
            raise

    @staticmethod
    def _build_workflow(command: CreateWorkflowRunCommand) -> Workflow:
        specification = command.workflow
        return Workflow(
            id=specification.id,
            version=specification.version,
            name=specification.name,
            schema_version=specification.schema_version,
            input_schema=specification.input_schema,
            outputs=specification.outputs,
            steps=tuple(
                WorkflowStep(
                    id=step.id,
                    kind=step.kind,
                    needs=step.needs,
                    uses=step.uses,
                    input_mapping=step.input_mapping,
                    timeout_seconds=step.timeout_seconds,
                    max_attempts=step.max_attempts,
                    retry_backoff=step.retry_backoff,
                    retry_initial_seconds=step.retry_initial_seconds,
                    retry_max_seconds=step.retry_max_seconds,
                    checkpoint_policy=step.checkpoint_policy,
                    approval_policy=step.approval_policy,
                )
                for step in specification.steps
            ),
        )

    @staticmethod
    def _verify_idempotent_request(
        execution,
        command: CreateWorkflowRunCommand,
        workflow: Workflow,
    ) -> None:
        run = execution.workflow_run
        if (
            execution.workflow != workflow
            or run.actor_user_id != command.actor_user_id
            or execution.agent_session.agent_profile_ref != command.agent_profile_ref
            or dict(run.inputs) != dict(command.inputs)
        ):
            raise ApplicationConflictError(
                "Idempotency key is already associated with a different run request"
            )


class CreateCatalogWorkflowRunService:
    """Create from one immutable catalog definition; clients cannot edit its DAG."""

    def __init__(
        self,
        *,
        unit_of_work: UnitOfWork,
        create_service: CreateWorkflowRunService,
        definition_hash: Callable[[Workflow], str],
    ) -> None:
        self.uow = unit_of_work
        self.create_service = create_service
        self.definition_hash = definition_hash

    def execute(
        self,
        command: CreateCatalogWorkflowRunCommand,
    ) -> WorkflowRunView:
        workflow = next(
            (
                item
                for item in self.uow.workflows.list_definitions()
                if item.id == command.workflow_id
                and item.version == command.workflow_version
            ),
            None,
        )
        if workflow is None:
            raise ApplicationValidationError(
                f"Catalog workflow {command.workflow_id}@"
                f"{command.workflow_version} was not found"
            )
        inputs = dict(command.inputs)
        if "workflow_hash" in inputs:
            raise ApplicationValidationError(
                "workflow_hash is server-owned and cannot be supplied by clients"
            )
        definition_hash = self.definition_hash(workflow)
        inputs["workflow_hash"] = (
            definition_hash
            if definition_hash.startswith("sha256:")
            else f"sha256:{definition_hash}"
        )
        return self.create_service.execute(
            CreateWorkflowRunCommand(
                project_id=command.project_id,
                actor_user_id=command.actor_user_id,
                idempotency_key=command.idempotency_key,
                agent_profile_ref=command.agent_profile_ref,
                workflow=WorkflowSpec(
                    id=workflow.id,
                    version=workflow.version,
                    name=workflow.name,
                    schema_version=workflow.schema_version,
                    input_schema=workflow.input_schema,
                    outputs=workflow.outputs,
                    steps=tuple(
                        StepSpec(
                            id=step.id,
                            kind=step.kind,
                            needs=step.needs,
                            uses=step.uses,
                            input_mapping=step.input_mapping,
                            timeout_seconds=step.timeout_seconds,
                            max_attempts=step.max_attempts,
                            retry_backoff=step.retry_backoff,
                            retry_initial_seconds=step.retry_initial_seconds,
                            retry_max_seconds=step.retry_max_seconds,
                            checkpoint_policy=step.checkpoint_policy,
                            approval_policy=step.approval_policy,
                        )
                        for step in workflow.steps
                    ),
                ),
                inputs=inputs,
            )
        )


class GetWorkflowRunService:
    def __init__(self, *, unit_of_work: UnitOfWork) -> None:
        self.uow = unit_of_work

    def execute(self, workflow_run_id: str) -> WorkflowRunView:
        return load_run_view(self.uow, workflow_run_id)


class ResumeWorkflowRunService:
    """Delegate execution orchestration to AgentRuntime and return a read model."""

    def __init__(
        self,
        *,
        unit_of_work: UnitOfWork,
        dispatcher: ExecutionDispatcher,
    ) -> None:
        self.uow = unit_of_work
        self.dispatcher = dispatcher

    async def execute(self, workflow_run_id: str) -> WorkflowRunView:
        # Give callers a stable 404 rather than exposing a Runtime error.
        load_execution(self.uow, workflow_run_id)
        try:
            await self.dispatcher.submit(
                ExecutionRequest(workflow_run_id=workflow_run_id)
            )
            return load_run_view(self.uow, workflow_run_id)
        except ApplicationConflictError:
            raise
        except (ExecutionNotResumableError, WorkflowEngineError, AgentRuntimeError) as error:
            self.uow.rollback()
            raise ApplicationConflictError(str(error)) from error
        except PersistenceError as error:
            self.uow.rollback()
            raise ApplicationConflictError(str(error)) from error
        except Exception:
            self.uow.rollback()
            raise


class CancelWorkflowRunService:
    """Cancel through Domain lifecycle rules and persist recovery boundaries."""

    def __init__(
        self,
        *,
        unit_of_work: UnitOfWork,
        domain_coordinator: ExecutionCoordinator,
    ) -> None:
        self.uow = unit_of_work
        self.domain = domain_coordinator

    def execute(self, workflow_run_id: str) -> WorkflowRunView:
        execution = load_execution(self.uow, workflow_run_id)
        if execution.workflow_run.status.is_terminal:
            return WorkflowRunView.from_execution(execution)

        expected_version = self.uow.workflows.get_version(workflow_run_id)
        if expected_version is None:
            raise ApplicationConflictError(
                f"WorkflowRun {workflow_run_id} has no persistence version"
            )
        try:
            before = self.domain.create_checkpoint(execution)
            self.uow.checkpoints.save(
                before,
                boundary=CheckpointBoundary.BEFORE_TERMINAL,
            )
            terminal = self.domain.cancel_execution(execution)
            self.uow.checkpoints.save(
                terminal,
                boundary=CheckpointBoundary.TERMINAL,
            )
            self.uow.workflows.update_state(
                execution,
                expected_version=expected_version,
            )
            self.uow.commit()
            return WorkflowRunView.from_execution(execution)
        except ExecutionNotResumableError as error:
            self.uow.rollback()
            raise ApplicationConflictError(str(error)) from error
        except (DomainError, WorkflowEngineError) as error:
            self.uow.rollback()
            raise ApplicationValidationError(str(error)) from error
        except (DuplicateEntityError, StaleStateError) as error:
            self.uow.rollback()
            raise ApplicationConflictError(str(error)) from error
        except Exception:
            self.uow.rollback()
            raise
