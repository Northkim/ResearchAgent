from __future__ import annotations

import ast
from pathlib import Path


FORBIDDEN_IMPORTS = {
    "backend.agent_runtime",
    "backend.application.execution",
    "backend.research.adapters.openalex",
    "backend.research.ports.structured_generation",
}
FORBIDDEN_NAMES = {
    "AgentRuntime",
    "ExecutionDispatcher",
    "OpenAlexPaperSearchProvider",
    "StructuredGenerationProvider",
}


def _source(relative: str) -> str:
    root = Path(__file__).resolve().parents[3]
    return (root / relative).read_text(encoding="utf-8")


def test_progress_application_service_has_no_execution_or_provider_import() -> None:
    tree = ast.parse(_source("backend/progress_reports/service.py"))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert not (imported_modules & FORBIDDEN_IMPORTS)
    assert not (imported_names & FORBIDDEN_NAMES)


def test_upload_router_has_no_run_resume_or_dispatch_call() -> None:
    source = _source("backend/api/routers/progress_reports.py")
    tree = ast.parse(source)
    call_names = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert "dispatch" not in call_names
    assert "resume" not in call_names
    assert "run" not in call_names
    assert "ExecutionDispatcher" not in source
    assert "AgentRuntime" not in source


def test_projection_contains_no_llm_or_research_inference_hook() -> None:
    source = _source("backend/progress_reports/projection.py")

    assert "llm" not in source.lower()
    assert "provider" not in source.lower()
    assert "AgentRuntime" not in source
