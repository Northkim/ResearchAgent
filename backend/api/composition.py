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
from backend.progress_reports import ProgressReportService
from backend.artifact_references.service import ArtifactReferenceService
from backend.progress_reports.identity import ProgressWorkflowIdentityResolver
from backend.progress_reports.aggregation import ProjectProgressAggregationService
from backend.local_projects.service import LocalProjectService
from backend.project_workspaces.application import ProjectWorkspaceApplicationService
from backend.project_workspaces.sync import WorkspaceSyncApplicationService
from backend.skill_system.registry import SkillRegistry
from backend.skill_system.models import SkillCapabilities
from backend.skill_system.runtime import SkillExecutor, register_fake_skills
from backend.research.adapters import (
    FakeLLMProvider,
    FakePaperSearchProvider,
    FakeSourceContentProvider,
    LocalFilesystemArtifactStorage,
    OpenAlexConfiguration,
    OpenAlexPaperSearchProvider,
    SyntheticGroundedPaperSearchProvider,
    SyntheticGroundedProvider,
)
from backend.research.ports import (
    ArtifactContentStorage,
    PaperSearchProvider,
    StructuredGenerationProvider,
)
from backend.research.services import (
    ArtifactApplicationGateway,
    ProviderExecutionPolicy,
    ProviderOperationService,
)
from backend.research.skills import register_research_skills
from backend.research.grounded_skills import register_grounded_research_skills
from backend.research.synthetic_grounded_fixtures import provider_responses
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


@dataclass(frozen=True, slots=True)
class ProgressApplicationServices:
    """Cloud progress services with no research-execution dependency."""

    progress_reports: ProgressReportService
    project_progress: ProjectProgressAggregationService
    artifact_references: ArtifactReferenceService


@dataclass(frozen=True, slots=True)
class LocalProductApplicationServices:
    """Local project/Package/progress graph with no Hosted Runtime."""

    local_projects: LocalProjectService
    progress_reports: ProgressReportService
    project_workspaces: ProjectWorkspaceApplicationService
    workspace_sync: WorkspaceSyncApplicationService
    project_progress: ProjectProgressAggregationService
    artifact_references: ArtifactReferenceService


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
        paper_search_provider: PaperSearchProvider | None = None,
        provider_execution_policy: ProviderExecutionPolicy | None = None,
        structured_generation_provider: StructuredGenerationProvider | None = None,
        grounded_paper_search_provider: PaperSearchProvider | None = None,
        close_callback: Callable[[], None] | None = None,
        local_package_root: str = "runtime_data/local_packages",
        project_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.unit_of_work_factory = unit_of_work_factory
        self.skill_registry = skill_registry if skill_registry is not None else SkillRegistry()
        if skill_registry is None:
            register_fake_skills(self.skill_registry)
            register_research_skills(self.skill_registry)
            register_grounded_research_skills(self.skill_registry)
        self.dispatcher_factory = dispatcher_factory or SyncExecutionDispatcher
        self.clock = clock
        self.approval_ttl = approval_ttl
        self.artifact_storage = (
            artifact_storage
            if artifact_storage is not None
            else LocalFilesystemArtifactStorage("runtime_data/artifacts")
        )
        self.paper_search_provider = (
            paper_search_provider
            if paper_search_provider is not None
            else FakePaperSearchProvider()
        )
        self.provider_execution_policy = (
            provider_execution_policy
            if provider_execution_policy is not None
            else ProviderExecutionPolicy.fake_only()
        )
        self.structured_generation_provider = (
            structured_generation_provider
            if structured_generation_provider is not None
            else SyntheticGroundedProvider(provider_responses())
        )
        self.grounded_paper_search_provider = (
            grounded_paper_search_provider
            if grounded_paper_search_provider is not None
            else SyntheticGroundedPaperSearchProvider()
        )
        self.source_content_provider = FakeSourceContentProvider()
        self.llm_provider = FakeLLMProvider()
        self._close_callback = close_callback
        self.local_package_root = local_package_root
        self.project_id_factory = project_id_factory

    def build_services(self, unit_of_work: UnitOfWork) -> ApplicationServices:
        domain = ExecutionCoordinator(clock=self.clock)
        workflow = WorkflowExecutionCoordinator(domain_coordinator=domain)
        provider_operations = ProviderOperationService(
            unit_of_work.provider_operations,
            commit_callback=unit_of_work.commit,
        )
        def capability_provider(decision):
            grounded = decision.workflow_version == "3.0.0"
            return SkillCapabilities(
                paper_search=(
                    self.grounded_paper_search_provider
                    if grounded
                    else self.paper_search_provider
                ),
                source_content=self.source_content_provider,
                llm=self.llm_provider,
                structured_generation=(
                    self.structured_generation_provider if grounded else None
                ),
                artifact_storage=self.artifact_storage,
                provider_operations=provider_operations,
                provider_execution_policy=(
                    ProviderExecutionPolicy.synthetic_grounded_report()
                    if grounded
                    else self.provider_execution_policy
                ),
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

    def build_progress_services(
        self,
        unit_of_work: UnitOfWork,
    ) -> ProgressApplicationServices:
        artifact_references = ArtifactReferenceService(
            unit_of_work=unit_of_work, clock=self.clock
        )
        return ProgressApplicationServices(
            progress_reports=self._progress_report_service(
                unit_of_work, artifact_references=artifact_references
            ),
            project_progress=ProjectProgressAggregationService(
                unit_of_work=unit_of_work,
                clock=self.clock,
            ),
            artifact_references=artifact_references,
        )

    def build_local_product_services(
        self,
        unit_of_work: UnitOfWork,
    ) -> LocalProductApplicationServices:
        project_workspaces = ProjectWorkspaceApplicationService(
            unit_of_work=unit_of_work,
            clock=self.clock,
        )
        artifact_references = ArtifactReferenceService(
            unit_of_work=unit_of_work, clock=self.clock
        )
        workspace_sync = WorkspaceSyncApplicationService(
            unit_of_work=unit_of_work,
            package_root=self.local_package_root,
            clock=self.clock,
        )
        return LocalProductApplicationServices(
            local_projects=LocalProjectService(
                repository=unit_of_work.local_projects,
                commit_callback=unit_of_work.commit,
                package_root=self.local_package_root,
                clock=self.clock,
                project_id_factory=self.project_id_factory,
                workspace_initializer=project_workspaces.initialize_new_project,
                package_pin_resolver=workspace_sync.standalone_literature_package_pin,
                package_artifact_registrar=(
                    workspace_sync.register_standalone_package_artifact
                ),
                rollback_callback=unit_of_work.rollback,
            ),
            progress_reports=self._progress_report_service(
                unit_of_work, artifact_references=artifact_references
            ),
            project_workspaces=project_workspaces,
            workspace_sync=workspace_sync,
            project_progress=ProjectProgressAggregationService(
                unit_of_work=unit_of_work,
                clock=self.clock,
            ),
            artifact_references=artifact_references,
        )

    def _progress_report_service(
        self,
        unit_of_work: UnitOfWork,
        *,
        artifact_references: ArtifactReferenceService | None = None,
    ) -> ProgressReportService:
        artifact_references = artifact_references or ArtifactReferenceService(
            unit_of_work=unit_of_work, clock=self.clock
        )
        return ProgressReportService(
            repository=unit_of_work.progress_reports,
            content_storage=self.artifact_storage,
            commit_callback=unit_of_work.commit,
            workflow_identity_resolver=ProgressWorkflowIdentityResolver(
                unit_of_work
            ).resolve,
            artifact_reference_service=artifact_references,
            clock=self.clock,
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
        provider_name = os.environ.get(
            "REAGENT_PAPER_SEARCH_PROVIDER",
            "fake",
        ).strip().lower()
        if provider_name == "fake":
            paper_search_provider: PaperSearchProvider = FakePaperSearchProvider()
            execution_policy = ProviderExecutionPolicy.fake_only()
        elif provider_name == "openalex":
            live_enabled = os.environ.get(
                "REAGENT_OPENALEX_LIVE_ENABLED",
                "",
            ).strip().lower() in {"1", "true", "yes"}
            if not live_enabled:
                engine.dispose()
                raise ValueError(
                    "OpenAlex selection requires REAGENT_OPENALEX_LIVE_ENABLED=true"
                )
            api_key = os.environ.get("REAGENT_OPENALEX_API_KEY")
            if not api_key:
                engine.dispose()
                raise ValueError(
                    "Supervised OpenAlex mode requires REAGENT_OPENALEX_API_KEY "
                    "for the free-credit preflight"
                )
            paper_search_provider = OpenAlexPaperSearchProvider(
                OpenAlexConfiguration(
                    api_key=api_key,
                )
            )
            execution_policy = ProviderExecutionPolicy.supervised_openalex()
        else:
            engine.dispose()
            raise ValueError(
                "REAGENT_PAPER_SEARCH_PROVIDER must be 'fake' or 'openalex'"
            )
        return cls(
            unit_of_work_factory=lambda: SQLAlchemyUnitOfWork(session_factory),
            artifact_storage=LocalFilesystemArtifactStorage(
                os.environ.get(
                    "REAGENT_ARTIFACT_ROOT",
                    "runtime_data/artifacts",
                )
            ),
            paper_search_provider=paper_search_provider,
            provider_execution_policy=execution_policy,
            close_callback=engine.dispose,
            local_package_root=os.environ.get(
                "REAGENT_LOCAL_PACKAGE_ROOT",
                "runtime_data/local_packages",
            ),
        )
