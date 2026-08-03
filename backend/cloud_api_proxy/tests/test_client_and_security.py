from __future__ import annotations

import json
import os
import socket
from pathlib import Path

import pytest

from backend.cloud_api_proxy import CloudAPIProxyService, DeterministicFakePaperSearchAdapter, InMemoryProxyDatabase, InMemoryProxyUnitOfWork
from backend.cloud_api_proxy.client import build_request, main, validate_base_url
from backend.cloud_api_proxy import operator_cli
from backend.cloud_api_proxy.operator_cli import _write_once
from backend.cloud_api_proxy.package_identity import read_validated_package_identity
from backend.workflow_packages import build_literature_search_package


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


def test_proxy_source_has_no_hosted_or_live_provider_imports() -> None:
    root = Path(__file__).resolve().parents[1]
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in root.glob("*.py")
        if path.name != "test_client_and_security.py"
    )
    for forbidden in (
        "backend.agent_runtime", "ExecutionDispatcher", "WorkflowRun",
        "ProviderOperationORM", "OpenAlex", "LLMProvider", "StructuredGeneration",
    ):
        assert forbidden not in source
