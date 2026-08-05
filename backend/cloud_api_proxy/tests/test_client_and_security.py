from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from backend.cloud_api_proxy import CloudAPIProxyService, DeterministicFakePaperSearchAdapter, InMemoryProxyDatabase, InMemoryProxyUnitOfWork
from backend.cloud_api_proxy.contracts import OPENALEX_ADAPTER_ID, canonical_json
from backend.cloud_api_proxy.client import build_request, main, submit, validate_base_url
from backend.cloud_api_proxy import operator_cli
from backend.cloud_api_proxy.operator_cli import _write_once
from backend.cloud_api_proxy.package_identity import read_validated_package_identity
from backend.workflow_packages import build_literature_search_package

from .conftest import make_request


@pytest.mark.parametrize("url", [
    "https://127.0.0.1:8000", "http://localhost:8000", "http://127.0.0.2:8000",
    "http://user@127.0.0.1:8000", "http://127.0.0.1:8000/path",
    "http://127.0.0.1:8000/#fragment", "http://192.168.1.10:8000",
])
def test_client_rejects_nonliteral_or_credentialed_base_urls(url: str) -> None:
    with pytest.raises(ValueError):
        validate_base_url(url)


def test_client_requires_environment_token_before_http(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.chdir(tmp_path)
    built = build_literature_search_package(project_id="proxy-client-fixture", output_root=Path("build"))
    monkeypatch.delenv("REAGENT_PROXY_TOKEN", raising=False)
    code = main([
        "submit", "--package-root", str(built.package_root),
        "--base-url", "http://127.0.0.1:8099", "--query", "fictional",
    ])
    captured = capsys.readouterr()
    assert code == 2
    assert "REAGENT_PROXY_TOKEN" in captured.err
    assert captured.out == ""


def test_client_build_is_package_read_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    built = build_literature_search_package(project_id="proxy-readonly-fixture", output_root=Path("build"))
    before = {path.relative_to(built.package_root): path.read_bytes() for path in built.package_root.rglob("*") if path.is_file()}
    identity = read_validated_package_identity(built.package_root)
    request = build_request(
        identity=identity, query=" fictional query ", max_results=3,
        harness_type="CODEX", harness_version=None, harness_session_id="session",
        idempotency_key="3aef47d4-ecc1-48c8-9149-86c4cb88f4da",
        client_timestamp="2026-08-04T08:00:00Z",
    )
    after = {path.relative_to(built.package_root): path.read_bytes() for path in built.package_root.rglob("*") if path.is_file()}
    assert request.parameters.query == "fictional query"
    assert before == after


def test_client_accepts_delayed_exact_replay_response_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = make_request()
    calls: list[tuple[str, bytes | None, float]] = []
    response_body = json.dumps(
        {
            "operation_id": "proxyop-v1-" + "a" * 64,
            "operation_status": "SUCCEEDED",
            "idempotency_result": "REPLAYED",
        }
    ).encode()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def read(self) -> bytes:
            return response_body

    def urlopen(http_request: urllib.request.Request, *, timeout: float):
        calls.append((http_request.full_url, http_request.data, timeout))
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    result = submit(
        base_url="http://127.0.0.1:8099",
        token="x" * 43,
        request=request,
        timeout=3.0,
    )

    assert result["idempotency_result"] == "REPLAYED"
    assert len(calls) == 1
    assert calls[0][1] == canonical_json(request.to_dict()).encode()


def test_client_stale_new_admission_error_is_safe_and_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def urlopen(http_request: urllib.request.Request, *, timeout: float):
        nonlocal calls
        calls += 1
        raise urllib.error.HTTPError(
            http_request.full_url,
            422,
            "synthetic rejection",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    with pytest.raises(RuntimeError, match="HTTP 422"):
        submit(
            base_url="http://127.0.0.1:8099",
            token="x" * 43,
            request=make_request(),
            timeout=3.0,
        )

    assert calls == 1


def test_token_file_is_0600_and_never_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "capability-token"
    _write_once(path, "fictional-token-canary")
    assert path.read_text().strip() == "fictional-token-canary"
    assert os.stat(path).st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        _write_once(path, "changed")
    assert path.read_text().strip() == "fictional-token-canary"


def test_operator_issue_cli_never_prints_plaintext_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.chdir(tmp_path)
    built = build_literature_search_package(project_id="proxy-operator-fixture", output_root=Path("package-build"))
    database = InMemoryProxyDatabase()
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(database),
        adapter=DeterministicFakePaperSearchAdapter(),
    )

    class Engine:
        def dispose(self) -> None:
            return None

    monkeypatch.setattr(operator_cli, "_service_from_environment", lambda: (service, Engine()))
    output = tmp_path / "operator-token"
    code = operator_cli.main([
        "issue", "--project-id", "proxy-operator-fixture",
        "--package-root", str(built.package_root), "--tenant-id", "tenant",
        "--subject-id", "subject", "--output-file", str(output),
    ])
    captured = capsys.readouterr()
    plaintext = output.read_text().strip()
    assert code == 0
    assert len(plaintext) >= 43
    assert plaintext not in captured.out
    assert plaintext not in captured.err
    assert plaintext not in caplog.text
    assert all(item.token_digest_sha256 != plaintext for item in database.tokens.values())
    assert json.loads(captured.out)["output_file_created"] is True


def test_operator_openalex_issue_binds_exact_budget_without_provider_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    built = build_literature_search_package(
        project_id="proxy-openalex-operator-fixture",
        output_root=Path("package-build"),
    )
    database = InMemoryProxyDatabase()
    service = CloudAPIProxyService(
        unit_of_work_factory=lambda: InMemoryProxyUnitOfWork(database),
        adapter=DeterministicFakePaperSearchAdapter(),
    )

    class Engine:
        def dispose(self) -> None:
            return None

    monkeypatch.setattr(operator_cli, "_service_from_environment", lambda: (service, Engine()))
    output = tmp_path / "openalex-operator-token"
    code = operator_cli.main([
        "issue", "--project-id", "proxy-openalex-operator-fixture",
        "--package-root", str(built.package_root), "--tenant-id", "tenant",
        "--subject-id", "subject", "--output-file", str(output),
        "--adapter-id", OPENALEX_ADAPTER_ID,
    ])
    captured = capsys.readouterr()
    response = json.loads(captured.out)
    assert code == 0
    assert response["adapter_id"] == OPENALEX_ADAPTER_ID
    assert response["maximum_operations"] == 20
    assert response["maximum_provider_calls"] == 20
    assert response["maximum_provider_cost_microusd"] == 50_000
    assert "key" not in captured.out.lower()
    assert "key" not in captured.err.lower()


def test_fake_adapter_has_no_network_path(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def forbidden_socket(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("network attempted")

    monkeypatch.setattr(socket, "socket", forbidden_socket)
    adapter = DeterministicFakePaperSearchAdapter()
    from backend.cloud_api_proxy.contracts import PaperSearchV01Request

    first = adapter.search(PaperSearchV01Request("fictional", 2))
    second = adapter.search(PaperSearchV01Request("fictional", 2))
    assert first == second
    assert calls == []
    assert first["untrusted_provider_data"] is True


def test_proxy_source_has_no_hosted_runtime_or_hosted_openalex_imports() -> None:
    root = Path(__file__).resolve().parents[1]
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in root.glob("*.py")
        if path.name != "test_client_and_security.py"
    )
    for forbidden in (
        "backend.agent_runtime", "ExecutionDispatcher", "WorkflowRun",
        "ProviderOperationORM", "backend.research.adapters.openalex",
        "backend.research.skills", "LLMProvider", "StructuredGeneration",
    ):
        assert forbidden not in source
