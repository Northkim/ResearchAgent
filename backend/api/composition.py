"""Composition root wiring ports to adapters and application use cases."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.agent_runtime import AgentRuntime
from backend.application.errors import ApplicationUnavailableError
from backend.application.execution import ExecutionDispatcher, SyncExecutionDispatcher
from backend.application.services import (
    ApprovalDecisionService,
    CancelWorkflowRunService,
    CreateWorkflowRunService,
    GetWorkflowRunService,
    ListApprovalsService,
    ListExecutionEventsService,
    ListWorkflowRunsService,
    ListWorkflowsService,
    ResumeWorkflowRunService,
)
from backend.database import (
    SQLAlchemyUnitOfWork,
    create_postgres_engine,
    create_session_factory,
)
from backend.domain.services import ExecutionCoordinator
from backend.domain.models._utils import utc_now
from backend.persistence.ports import UnitOfWork
from backend.skill_system.registry import SkillRegistry
from backend.skill_system.runtime import SkillExecutor, register_fake_skills
from backend.workflow_engine.services import WorkflowExecutionCoordinator

UnitOfWorkFactory = Callable[[], UnitOfWork]
DispatcherFactory = Callable[[AgentRuntime], ExecutionDispatcher]


@dataclass(frozen=True, slots=True)
class ApplicationServices:
    """Request-scoped services sharing one UnitOfWork and Runtime."""

    runtime: AgentRuntime
    dispatcher: ExecutionDispatcher
    create_workflow_run: CreateWorkflowRunService
    get_workflow_run: GetWorkflowRunService
    resume_workflow_run: ResumeWorkflowRunService
    cancel_workflow_run: CancelWorkflowRunService
    decide_approval: ApprovalDecisionService
    list_workflow_runs: ListWorkflowRunsService
    list_execution_events: ListExecutionEventsService
    list_approvals: ListApprovalsService
    list_workflows: ListWorkflowsService


class ApplicationContainer:
    """Own process-scoped factories; build request-scoped service graphs."""

    def __init__(
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        skill_registry: SkillRegistry | None = None,
        dispatcher_factory: DispatcherFactory | None = None,
        clock: Callable[[], datetime] = utc_now,
        approval_ttl: timedelta = timedelta(hours=24),
        close_callback: Callable[[], None] | None = None,
    ) -> None:
        self.unit_of_work_factory = unit_of_work_factory
        self.skill_registry = skill_registry if skill_registry is not None else SkillRegistry()
        if skill_registry is None:
            register_fake_skills(self.skill_registry)
        self.dispatcher_factory = dispatcher_factory or SyncExecutionDispatcher
        self.clock = clock
        self.approval_ttl = approval_ttl
        self._close_callback = close_callback

    def build_services(self, unit_of_work: UnitOfWork) -> ApplicationServices:
        domain = ExecutionCoordinator(clock=self.clock)
        workflow = WorkflowExecutionCoordinator(domain_coordinator=domain)
        runtime = AgentRuntime(
            workflow_coordinator=workflow,
            skill_executor=SkillExecutor(self.skill_registry),
            unit_of_work=unit_of_work,
            clock=self.clock,
            approval_ttl=self.approval_ttl,
        )
        dispatcher = self.dispatcher_factory(runtime)
        return ApplicationServices(
            runtime=runtime,
            dispatcher=dispatcher,
            create_workflow_run=CreateWorkflowRunService(
                unit_of_work=unit_of_work,
                domain_coordinator=domain,
            ),
            get_workflow_run=GetWorkflowRunService(unit_of_work=unit_of_work),
            resume_workflow_run=ResumeWorkflowRunService(
                unit_of_work=unit_of_work,
                dispatcher=dispatcher,
            ),
            cancel_workflow_run=CancelWorkflowRunService(
                unit_of_work=unit_of_work,
                domain_coordinator=domain,
            ),
            decide_approval=ApprovalDecisionService(
                unit_of_work=unit_of_work,
                dispatcher=dispatcher,
                clock=self.clock,
            ),
            list_workflow_runs=ListWorkflowRunsService(unit_of_work=unit_of_work),
            list_execution_events=ListExecutionEventsService(
                unit_of_work=unit_of_work
            ),
            list_approvals=ListApprovalsService(unit_of_work=unit_of_work),
            list_workflows=ListWorkflowsService(unit_of_work=unit_of_work),
        )

    def close(self) -> None:
        if self._close_callback is not None:
            self._close_callback()

    @classmethod
    def from_environment(cls) -> ApplicationContainer:
        database_url = os.environ.get("REAGENT_DATABASE_URL")
        if not database_url:
            def unavailable_factory() -> UnitOfWork:
                raise ApplicationUnavailableError(
                    "REAGENT_DATABASE_URL is required for persistence endpoints"
                )

            return cls(unit_of_work_factory=unavailable_factory)

        engine = create_postgres_engine(database_url)
        session_factory = create_session_factory(engine)
        return cls(
            unit_of_work_factory=lambda: SQLAlchemyUnitOfWork(session_factory),
            close_callback=engine.dispose,
        )
