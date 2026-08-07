"""API routers."""

from .approvals import router as approvals_router
from .artifacts import router as artifacts_router
from .artifact_references import router as artifact_references_router
from .health import router as health_router
from .local_client import router as local_client_router
from .progress_reports import router as progress_reports_router
from .local_projects import router as local_projects_router
from .local_sessions import router as local_sessions_router
from .runs import router as runs_router
from .workflows import router as workflows_router
from .project_workspaces import router as project_workspaces_router

__all__ = [
    "artifacts_router",
    "artifact_references_router",
    "approvals_router",
    "health_router",
    "local_client_router",
    "progress_reports_router",
    "local_projects_router",
    "local_sessions_router",
    "runs_router",
    "workflows_router",
    "project_workspaces_router",
]
