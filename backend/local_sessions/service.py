"""Bounded local-session bootstrap without Hosted research execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from collections.abc import Callable

from backend.application.errors import (
    ApplicationUnavailableError,
    ApplicationValidationError,
)
from backend.cloud_api_proxy.contracts import (
    ADAPTER_ID,
    CAPABILITY,
    LOCAL_PROGRESS_ADAPTER_ID,
    LOCAL_PROGRESS_SESSION_CAPABILITY,
    LOCAL_PROGRESS_READ_CAPABILITY,
    LOCAL_PROGRESS_UPLOAD_CAPABILITY,
    LocalProgressReportScope,
    OPENALEX_ADAPTER_ID,
    ProxyCapabilityToken,
)
from backend.cloud_api_proxy.service import CloudAPIProxyService
from backend.local_projects.service import LocalProjectService

SESSION_LIFETIME_MINUTES = 15
UPLOAD_SESSION_LIFETIME_MINUTES = 2
MAXIMUM_QUERY_VARIANTS = 3
MAXIMUM_RESULTS_PER_QUERY = 5


class LocalSessionMode(str, Enum):
    NORMAL = "NORMAL"
    DEMO = "DEMO"
    UPLOAD_ONLY = "UPLOAD_ONLY"


@dataclass(frozen=True, slots=True)
class LocalWorkflowSession:
    session_id: str
    session_token: str
    mode: LocalSessionMode
    expires_at: str
    project_id: str
    package_id: str
    workflow_id: str
    maximum_query_variants: int
    maximum_results_per_query: int
    maximum_provider_calls: int
    maximum_provider_cost_microusd: int


class LocalWorkflowSessionService:
    """Issue exact-Package capabilities; never run or synthesize research."""

    def __init__(
        self,
        *,
        local_projects: LocalProjectService,
        proxy: CloudAPIProxyService,
        package_identity_resolver: Callable[
            [str, str], tuple[str, str, str, str, str] | None
        ] | None = None,
    ) -> None:
        self._projects = local_projects
        self._proxy = proxy
        self._package_identity_resolver = package_identity_resolver

    def open(
        self,
        *,
        project_id: str,
        package_id: str,
        package_checksum: str,
        workflow_id: str,
        workflow_version: str,
        workflow_checksum: str,
        mode: LocalSessionMode,
        execution_round: int | None = None,
        report_id: str | None = None,
        report_content_checksum: str | None = None,
    ) -> LocalWorkflowSession:
        project = self._projects.get(project_id)
        supplied = (
            package_id,
            package_checksum,
            workflow_id,
            workflow_version,
            workflow_checksum,
        )
        package = project.current_package
        expected = None
        if package is not None and package.package_id == package_id:
            expected = (
                package.package_id,
                package.package_checksum,
                package.workflow_id,
                package.workflow_version,
                package.workflow_checksum,
            )
        elif self._package_identity_resolver is not None:
            expected = self._package_identity_resolver(project_id, package_id)
        if expected is None:
            raise ApplicationValidationError(
                "Workflow Package or Capsule artifact is not registered for this Project"
            )
        if supplied != expected:
            raise ApplicationValidationError(
                "Local session identity does not match the project's current Package"
            )
        supplied_report_scope = (
            execution_round,
            report_id,
            report_content_checksum,
        )
        if mode is not LocalSessionMode.UPLOAD_ONLY and any(
            value is not None for value in supplied_report_scope
        ):
            raise ApplicationValidationError(
                "Search sessions cannot receive a Progress Report scope"
            )

        if mode is LocalSessionMode.NORMAL:
            adapter_id = OPENALEX_ADAPTER_ID
            maximum_operations = MAXIMUM_QUERY_VARIANTS
            lifetime_minutes = SESSION_LIFETIME_MINUTES
            local_capabilities: tuple[str, ...] = ()
            report_scope = None
        elif mode is LocalSessionMode.DEMO:
            adapter_id = ADAPTER_ID
            maximum_operations = MAXIMUM_QUERY_VARIANTS
            lifetime_minutes = SESSION_LIFETIME_MINUTES
            local_capabilities = ()
            report_scope = None
        else:
            if execution_round is None or report_id is None or report_content_checksum is None:
                raise ApplicationValidationError(
                    "Upload-only sessions require an exact Progress Report scope"
                )
            adapter_id = LOCAL_PROGRESS_ADAPTER_ID
            maximum_operations = 0
            lifetime_minutes = UPLOAD_SESSION_LIFETIME_MINUTES
            local_capabilities = (
                LOCAL_PROGRESS_UPLOAD_CAPABILITY,
                LOCAL_PROGRESS_READ_CAPABILITY,
            )
            report_scope = LocalProgressReportScope(
                execution_round=execution_round,
                report_id=report_id,
                report_content_checksum=report_content_checksum,
            )
        if mode is not LocalSessionMode.UPLOAD_ONLY and adapter_id not in self._proxy.adapters:
            if mode is LocalSessionMode.NORMAL:
                raise ApplicationUnavailableError(
                    "Normal Literature Search requires the explicitly enabled OpenAlex Proxy"
                )
            raise ApplicationUnavailableError(
                "The local fake Proxy scope required for this session is unavailable"
            )

        token, plaintext = self._proxy.issue_token(
            tenant_id="local-v0-1",
            subject_id="local-owner",
            project_id=project_id,
            package_id=package_id,
            package_checksum=package_checksum,
            workflow_id=workflow_id,
            workflow_version=workflow_version,
            workflow_checksum=workflow_checksum,
            lifetime_minutes=lifetime_minutes,
            maximum_operations=maximum_operations,
            adapter_id=adapter_id,
            local_session_capabilities=local_capabilities,
            local_progress_report_scope=report_scope,
            capability=(
                LOCAL_PROGRESS_SESSION_CAPABILITY
                if mode is LocalSessionMode.UPLOAD_ONLY
                else CAPABILITY
            ),
        )
        scope = token.scope
        return LocalWorkflowSession(
            session_id=scope.token_id,
            session_token=plaintext,
            mode=mode,
            expires_at=token.expires_at,
            project_id=scope.project_id,
            package_id=scope.package_id,
            workflow_id=scope.workflow_id,
            maximum_query_variants=(
                0 if mode is LocalSessionMode.UPLOAD_ONLY else MAXIMUM_QUERY_VARIANTS
            ),
            maximum_results_per_query=(
                0 if mode is LocalSessionMode.UPLOAD_ONLY else MAXIMUM_RESULTS_PER_QUERY
            ),
            maximum_provider_calls=scope.maximum_provider_calls,
            maximum_provider_cost_microusd=scope.maximum_provider_cost_microusd,
        )

    def authorize(
        self,
        *,
        bearer_token: str,
        session_id: str,
        project_id: str,
        package_id: str,
        package_checksum: str,
        workflow_id: str,
        workflow_version: str,
        workflow_checksum: str,
        capability: str,
    ) -> ProxyCapabilityToken:
        return self._proxy.authorize_local_session_capability(
            bearer_token=bearer_token,
            token_id=session_id,
            project_id=project_id,
            package_id=package_id,
            package_checksum=package_checksum,
            workflow_id=workflow_id,
            workflow_version=workflow_version,
            workflow_checksum=workflow_checksum,
            capability=capability,
        )

    def close(self, session_id: str) -> None:
        self._proxy.revoke_token(session_id)

    def authorize_identity(
        self,
        *,
        bearer_token: str,
        session_id: str,
        project_id: str,
        package_id: str,
        package_checksum: str,
        workflow_id: str,
        workflow_version: str,
        workflow_checksum: str,
    ) -> ProxyCapabilityToken:
        return self._proxy.authorize_local_session_identity(
            bearer_token=bearer_token,
            token_id=session_id,
            project_id=project_id,
            package_id=package_id,
            package_checksum=package_checksum,
            workflow_id=workflow_id,
            workflow_version=workflow_version,
            workflow_checksum=workflow_checksum,
        )
