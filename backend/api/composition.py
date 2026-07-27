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
    CreateCatalogWorkflowRunService,
    CreateWorkflowRunService,
    GetArtifactService,
    GetWorkflowRunService,
    ListApprovalsService,
    ListExecutionEventsService,
    ListProviderUsageService,
    ListRunArtifactsService,
    ListWorkflowRunsService,
    ListWorkflowsService,
    ReadArtifactContentService,
    ResumeWorkflowRunService,
)
from backend.database import (
    SQLAlchemyUnitOfWork,
    create_postgres_engine,
    create_session_factory,
)
from backend.database.serialization import workflow_document_hash, workflow_to_document
from backend.domain.services import ExecutionCoordinator
from backend.domain.models._utils import utc_now
from backend.persistence.ports import UnitOfWork
from backend.skill_system.registry import SkillRegistry
from backend.skill_system.models import SkillCapabilities
from backend.skill_system.runtime import SkillExecutor, register_fake_skills
from backend.research.adapters import (
    FakeLLMProvider,
    FakePaperSearchProvider,
    FakeSourceContentProvider,
    LocalFilesystemArtifactStorage,
)
from backend.research.ports import ArtifactContentStorage
from backend.research.services import (
    ArtifactApplicationGateway,
    ProviderOperationService,
)
from backend.research.skills import register_research_skills
from backend.workflow_engine.services import WorkflowExecutionCoordinator

UnitOfWorkFactory = Callable[[], UnitOfWork]
DispatcherFactory = Callable[[AgentRuntime], ExecutionDispatcher]


@dataclass(frozen=True, slots=True)
class ApplicationServices:
    """Request-scoped services sharing one UnitOfWork and Runtime."""

    runtime: AgentRuntime
    dispatcher: ExecutionDispatcher
    create_workflow_run: CreateWorkflowRunService
    create_catalog_workflow_run: CreateCatalogWorkflowRunService
    get_workflow_run: GetWorkflowRunService
    resume_workflow_run: ResumeWorkflowRunService
    cancel_workflow_run: CancelWorkflowRunService
    decide_approval: ApprovalDecisionService
    list_workflow_runs: ListWorkflowRunsService
    list_execution_events: ListExecutionEventsService
    list_approvals: ListApprovalsService
    list_workflows: ListWorkflowsService
    list_run_artifacts: ListRunArtifactsService
    get_artifact: GetArtifactService
    read_artifact_content: ReadArtifactContentService
    list_provider_usage: ListProviderUsageService


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
        artifact_storage: ArtifactContentStorage | None = None,
        close_callback: Callable[[], None] | None = None,
    ) -> None:
        self.unit_of_work_factory = unit_of_work_factory
        self.skill_registry = skill_registry if skill_registry is not None else SkillRegistry()
        if skill_registry is None:
            register_fake_skills(self.skill_registry)
            register_research_skills(self.skill_registry)
        self.dispatcher_factory = dispatcher_factory or SyncExecutionDispatcher
        self.clock = clock
        self.approval_ttl = approval_ttl
        self.artifact_storage = (
            artifact_storage
            if artifact_storage is not None
            else LocalFilesystemArtifactStorage("runtime_data/artifacts")
        )
        self.paper_search_provider = FakePaperSearchProvider()
        self.source_content_provider = FakeSourceContentProvider()
        self.llm_provider = FakeLLMProvider()
        self._close_callback = close_callback

    def build_services(self, unit_of_work: UnitOfWork) -> ApplicationServices:
        domain = ExecutionCoordinator(clock=self.clock)
        workflow = WorkflowExecutionCoordinator(domain_coordinator=domain)
        provider_operations = ProviderOperationService(
            unit_of_work.provider_operations,
            commit_callback=unit_of_work.commit,
        )
        def capability_provider(_):
            return SkillCapabilities(
                paper_search=self.paper_search_provider,
                source_content=self.source_content_provider,
                llm=self.llm_provider,
                artifact_storage=self.artifact_storage,
                provider_operations=provider_operations,
            )

        runtime = AgentRuntime(
            workflow_coordinator=workflow,
            skill_executor=SkillExecutor(
                self.skill_registry,
                capability_provider=capability_provider,
            ),
            unit_of_work=unit_of_work,
            clock=self.clock,
            approval_ttl=self.approval_ttl,
        )
        dispatcher = self.dispatcher_factory(runtime)
        create_workflow_run = CreateWorkflowRunService(
            unit_of_work=unit_of_work,
            domain_coordinator=domain,
        )
        artifact_gateway = ArtifactApplicationGateway(
            unit_of_work=unit_of_work,
            content_storage=self.artifact_storage,
        )
        return ApplicationServices(
            runtime=runtime,
            dispatcher=dispatcher,
            create_workflow_run=create_workflow_run,
            create_catalog_workflow_run=CreateCatalogWorkflowRunService(
                unit_of_work=unit_of_work,
                create_service=create_workflow_run,
                definition_hash=lambda workflow: workflow_document_hash(
                    workflow_to_document(workflow)
                ),
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
                artifacts=artifact_gateway,
            ),
            list_workflow_runs=ListWorkflowRunsService(unit_of_work=unit_of_work),
            list_execution_events=ListExecutionEventsService(
                unit_of_work=unit_of_work
            ),
            list_approvals=ListApprovalsService(unit_of_work=unit_of_work),
            list_workflows=ListWorkflowsService(unit_of_work=unit_of_work),
            list_run_artifacts=ListRunArtifactsService(
                unit_of_work=unit_of_work,
                artifacts=artifact_gateway,
            ),
            get_artifact=GetArtifactService(artifacts=artifact_gateway),
            read_artifact_content=ReadArtifactContentService(
                artifacts=artifact_gateway
            ),
            list_provider_usage=ListProviderUsageService(
                unit_of_work=unit_of_work
            ),
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
            artifact_storage=LocalFilesystemArtifactStorage(
                os.environ.get(
                    "REAGENT_ARTIFACT_ROOT",
                    "runtime_data/artifacts",
                )
            ),
            close_callback=engine.dispose,
        )
