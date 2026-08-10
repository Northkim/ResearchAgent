from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.application.errors import (
    ApplicationUnavailableError,
    ApplicationValidationError,
)
from backend.cloud_api_proxy import (
    DeterministicFakePaperSearchAdapter,
    InMemoryProxyDatabase,
    InMemoryProxyUnitOfWork,
)
from backend.cloud_api_proxy.contracts import (
    LOCAL_PROGRESS_ADAPTER_ID,
    LOCAL_PROGRESS_SESSION_CAPABILITY,
    LOCAL_PROGRESS_READ_CAPABILITY,
    OPENALEX_ADAPTER_ID,
)
from backend.cloud_api_proxy.errors import ProxyError
from backend.cloud_api_proxy.service import CloudAPIProxyService
from backend.local_projects import LITERATURE_SEARCH_WORKFLOW
from backend.local_projects.service import LocalProjectService
from backend.local_sessions import LocalSessionMode, LocalWorkflowSessionService
from backend.persistence.adapters import InMemoryDatabase, InMemoryUnitOfWork


class NetworkCanaryOpenAlexAdapter:
    adapter_id = OPENALEX_ADAPTER_ID
    invocation_count = 0

    def search(self, request):
        raise AssertionError("opening or authorizing a local session invoked transport")


def _setup(tmp_path, *, include_openalex: bool = True):
    application_db = InMemoryDatabase()
    application_uow = InMemoryUnitOfWork(application_db)
    project_service = LocalProjectService(
        repository=application_uow.local_projects,
        commit_callback=application_uow.commit,
        package_root=tmp_path / "packages",
        clock=lambda: datetime(2026, 8, 6, 8, 0, tzinfo=UTC),
        project_id_factory=lambda: "project-0123456789abcdef0123456789abcdef",
    )
    project = project_service.create(
        name="Fictional session project",
        research_topic="A fictional public local-session topic",
        selected_workflow=LITERATURE_SEARCH_WORKFLOW,
    )
    project = project_service.generate_package(project.project_id)
    package = project.current_package
    assert package is not None
    proxy_db = InMemoryProxyDatabase()
    fake = DeterministicFakePaperSearchAdapter()
    adapters = {fake.adapter_id: fake}
    canary = NetworkCanaryOpenAlexAdapter()
    if include_openalex:
        adapters[canary.adapter_id] = canary
    now = [datetime(2026, 8, 6, 8, 0, tzinfo=UTC)]
    proxy = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(proxy_db),
        adapters=adapters,
        clock=lambda: now[0],
    )
    sessions = LocalWorkflowSessionService(
        local_projects=project_service,
        proxy=proxy,
    )
    identity = {
        "project_id": project.project_id,
        "package_id": package.package_id,
        "package_checksum": package.package_checksum,
        "workflow_id": package.workflow_id,
        "workflow_version": package.workflow_version,
        "workflow_checksum": package.workflow_checksum,
    }
    return sessions, proxy_db, fake, canary, now, identity, tmp_path / "packages"


def test_normal_demo_and_upload_only_sessions_are_bounded(tmp_path) -> None:
    sessions, database, fake, canary, _, identity, package_root = _setup(tmp_path)
    assert sessions.search_mode(**identity) is LocalSessionMode.NORMAL
    normal = sessions.open(mode=LocalSessionMode.NORMAL, **identity)
    demo = sessions.open(mode=LocalSessionMode.DEMO, **identity)
    upload = sessions.open(
        mode=LocalSessionMode.UPLOAD_ONLY,
        execution_round=1,
        report_id="prv2-" + "a" * 64,
        report_content_checksum="sha256:" + "b" * 64,
        **identity,
    )
    assert normal.maximum_provider_calls == 3
    assert normal.maximum_query_variants == 3
    assert demo.maximum_provider_calls == 0
    assert upload.maximum_query_variants == 0
    assert fake.invocation_count == canary.invocation_count == 0
    normal_token = database.tokens[normal.session_id]
    demo_token = database.tokens[demo.session_id]
    upload_token = database.tokens[upload.session_id]
    assert normal_token.scope.local_session_capabilities == ()
    assert demo_token.scope.local_session_capabilities == ()
    assert upload_token.scope.adapter_id == LOCAL_PROGRESS_ADAPTER_ID
    assert upload_token.scope.maximum_operations == 0
    assert upload_token.scope.maximum_provider_calls == 0
    assert upload_token.scope.maximum_provider_cost_microusd == 0
    assert upload_token.scope.capability == LOCAL_PROGRESS_SESSION_CAPABILITY
    assert set(upload_token.scope.local_session_capabilities) == {
        "progress.upload/v0.2",
        "progress.read/v0.1",
    }
    assert upload_token.scope.local_progress_report_scope is not None
    package_bytes = b"".join(
        path.read_bytes() for path in package_root.rglob("*") if path.is_file()
    )
    assert normal.session_token.encode() not in package_bytes
    assert demo.session_token.encode() not in package_bytes
    assert upload.session_token.encode() not in package_bytes


def test_normal_mode_never_falls_back_to_fake(tmp_path) -> None:
    sessions, _, fake, _, _, identity, _ = _setup(
        tmp_path, include_openalex=False
    )
    with pytest.raises(ApplicationUnavailableError, match="OpenAlex Proxy"):
        sessions.open(mode=LocalSessionMode.NORMAL, **identity)
    assert fake.invocation_count == 0


def test_controlled_search_mode_is_server_enforced_and_checksum_bound(tmp_path) -> None:
    sessions, _, fake, canary, _, identity, _ = _setup(tmp_path)
    controlled = LocalWorkflowSessionService(
        local_projects=sessions._projects,
        proxy=sessions._proxy,
        enforced_search_mode=LocalSessionMode.DEMO,
    )

    assert controlled.search_mode(**identity) is LocalSessionMode.DEMO
    demo = controlled.open(mode=LocalSessionMode.DEMO, **identity)
    assert demo.mode is LocalSessionMode.DEMO
    with pytest.raises(ApplicationValidationError, match="controlled server"):
        controlled.open(mode=LocalSessionMode.NORMAL, **identity)
    with pytest.raises(ApplicationValidationError, match="identity"):
        controlled.search_mode(
            **{**identity, "workflow_checksum": "sha256:" + "f" * 64}
        )
    assert fake.invocation_count == canary.invocation_count == 0


def test_exact_scope_expiry_revocation_and_cross_project_denial(tmp_path) -> None:
    sessions, _, _, _, now, identity, _ = _setup(tmp_path)
    session = sessions.open(
        mode=LocalSessionMode.UPLOAD_ONLY,
        execution_round=1,
        report_id="prv2-" + "a" * 64,
        report_content_checksum="sha256:" + "b" * 64,
        **identity,
    )
    authorized = sessions.authorize(
        bearer_token=session.session_token,
        session_id=session.session_id,
        capability=LOCAL_PROGRESS_READ_CAPABILITY,
        **identity,
    )
    assert authorized.scope.project_id == identity["project_id"]
    with pytest.raises(ProxyError) as wrong_scope:
        sessions.authorize(
            bearer_token=session.session_token,
            session_id=session.session_id,
            capability=LOCAL_PROGRESS_READ_CAPABILITY,
            **{**identity, "project_id": "project-ffffffffffffffffffffffffffffffff"},
        )
    assert wrong_scope.value.http_status == 403
    sessions.close(session.session_id)
    with pytest.raises(ProxyError) as revoked:
        sessions.authorize(
            bearer_token=session.session_token,
            session_id=session.session_id,
            capability=LOCAL_PROGRESS_READ_CAPABILITY,
            **identity,
        )
    assert revoked.value.http_status == 401

    expiring = sessions.open(
        mode=LocalSessionMode.UPLOAD_ONLY,
        execution_round=1,
        report_id="prv2-" + "c" * 64,
        report_content_checksum="sha256:" + "d" * 64,
        **identity,
    )
    now[0] += timedelta(minutes=3)
    with pytest.raises(ProxyError) as expired:
        sessions.authorize(
            bearer_token=expiring.session_token,
            session_id=expiring.session_id,
            capability=LOCAL_PROGRESS_READ_CAPABILITY,
            **identity,
        )
    assert expired.value.http_status == 401
    assert expired.value.code == "SESSION_EXPIRED"


def test_search_session_has_no_progress_capability_but_can_be_revoked(tmp_path) -> None:
    sessions, _, _, _, _, identity, _ = _setup(tmp_path)
    search = sessions.open(mode=LocalSessionMode.DEMO, **identity)
    with pytest.raises(ProxyError) as denied:
        sessions.authorize(
            bearer_token=search.session_token,
            session_id=search.session_id,
            capability=LOCAL_PROGRESS_READ_CAPABILITY,
            **identity,
        )
    assert denied.value.http_status == 403
    sessions.authorize_identity(
        bearer_token=search.session_token,
        session_id=search.session_id,
        **identity,
    )
    sessions.close(search.session_id)
