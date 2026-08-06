from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from backend.workflow_packages import build_literature_search_package, validate_package
from backend.workflow_packages import local_runner
from backend.workflow_packages.serialization import sha256_bytes


HASH = "sha256:" + "a" * 64


def _planning(root: Path) -> None:
    topic = json.loads((root / "inputs/research_request.json").read_text())["topic"]
    (root / "outputs/search_plan.md").write_text(
        """# Search plan
## Interpreted topic
Portable research state.
## Concepts and synonyms
continuity, handoff
## Query variants
Two variants.
## Search bounds
Two calls, five records per call.
## Screening rules
Direct topical relation.
## Evidence limitations
Metadata and abstracts only.
""",
        encoding="utf-8",
    )
    (root / "memory/search/query_plan.json").write_text(
        json.dumps(
            {
                "schema_version": "literature-search-query-plan/v0.1",
                "status": "READY",
                "original_topic": topic,
                "queries": [
                    {"query_id": "query-1", "query": topic},
                    {"query_id": "query-2", "query": f"{topic} evidence"},
                ],
            }
        ),
        encoding="utf-8",
    )


def _synthesis(root: Path, mode: str) -> None:
    records = [
        {
            "candidate_id": f"candidate-{index:016x}",
            "provider_id": f"fictional-provider-{index}",
            "openalex_id": None if mode == "DEMO" else f"W{index}",
            "title": f"Fictional result {index}",
            "authors": [f"Fictional Author {index}"],
            "publication_year": 2026,
            "doi": None,
            "source": "Fictional venue",
            "language": "en",
            "abstract": "Abstract-only evidence.",
            "source_query_ids": ["query-1", "query-2"],
            "provenance_checksum": "sha256:" + f"{index:064x}",
            "deduplication_status": "MERGED" if index == 1 else "UNIQUE",
        }
        for index in range(1, 4)
    ]
    (root / "outputs/candidate_papers.json").write_text(
        json.dumps(
            {
                "schema_version": "candidate-papers/v0.2",
                "mode": mode,
                "candidates": records,
            }
        ),
        encoding="utf-8",
    )
    (root / "outputs/selected_papers.json").write_text(
        json.dumps(
            {
                "schema_version": "selected-papers/v0.2",
                "mode": mode,
                "selection_status": "SUFFICIENT",
                "selected": [
                    {
                        "candidate_id": item["candidate_id"],
                        "relevance_decision": "INCLUDE",
                        "inclusion_reason": "Direct evidence for the topic.",
                        "evidence_availability": "METADATA_AND_ABSTRACT",
                    }
                    for item in records
                ],
                "exclusions": [],
                "exclusion_summary": "No exclusions.",
            }
        ),
        encoding="utf-8",
    )
    demo = "FICTIONAL DEMO EVIDENCE.\n" if mode == "DEMO" else ""
    (root / "outputs/literature_search_report.md").write_text(
        demo
        + """# Literature search report
## Executive summary
Local synthesis.
## Search coverage
Two bounded queries.
## Main research themes
Continuity.
## Common methods
Metadata comparison.
## Representative works
Three representative records.
## Trends
Transparent handoffs.
## Limitations
Metadata and abstract-only evidence; full text was not read.
## Potential research gaps
Longitudinal validation.
## Recommended next research action
Review the local evidence.
## Selected-paper references
Records 1-3.
""",
        encoding="utf-8",
    )
    context = root / "memory/context.md"
    payload = json.loads(
        context.read_text().split("```json\n", 1)[1].split("\n```", 1)[0]
    )
    payload.update(
        {
            "current_workflow_state": "COMPLETED",
            "completed_outputs": [
                "outputs/search_plan.md",
                "outputs/candidate_papers.json",
                "outputs/selected_papers.json",
                "outputs/literature_search_report.md",
            ],
            "next_action": "Review local outputs.",
            "updated_at": "2026-08-06T01:02:00Z",
            "context_checksum": None,
        }
    )
    payload["context_checksum"] = local_runner.canonical_hash(payload)
    context.write_text(
        "# Local Task Context\n\n```json\n"
        + local_runner.canonical_json(payload)
        + "\n```\n",
        encoding="utf-8",
    )
    draft_path = root / "memory/progress/report-draft.json"
    draft = json.loads(draft_path.read_text())
    draft.update(
        {
            "started_at": "2026-08-06T01:00:00Z",
            "completed_at": "2026-08-06T01:02:00Z",
            "status": "COMPLETED",
            "completed_work": [
                "Queries performed: 2",
                "Candidates retained: 3",
                "Papers selected: 3",
                "Outputs generated: 4",
            ],
            "current_state": "Three locally screened papers support the bounded summary.",
            "next_recommended_action": "Review the complete local report.",
            "warnings": ["Metadata and abstract-only evidence; no full text."],
        }
    )
    draft_path.write_text(json.dumps(draft), encoding="utf-8")


def _package(tmp_path: Path) -> Path:
    return build_literature_search_package(
        project_id="project-0123456789abcdef0123456789abcdef",
        research_topic="A fictional public topic about transparent continuity",
        output_root=tmp_path / "build",
        allow_absolute_output_root=True,
    ).package_root


def test_codex_invocation_uses_supported_noninteractive_policy_and_strips_secrets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(local_runner, "_codex_executable", lambda: "/safe/codex")
    for key in (
        "REAGENT_PROXY_TOKEN",
        "REAGENT_LOCAL_SESSION_TOKEN",
        "REAGENT_OPENALEX_API_KEY",
        "REAGENT_DATABASE_URL",
    ):
        monkeypatch.setenv(key, "must-not-reach-codex")

    def run(command, **kwargs):
        captured["command"] = command
        captured["environment"] = kwargs["env"]
        return CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(local_runner.subprocess, "run", run)
    local_runner._invoke_codex(root=tmp_path, instruction="fixed-stage")

    command = captured["command"]
    assert isinstance(command, list)
    assert "--ask-for-approval" not in command
    assert command[command.index("--config") + 1] == 'approval_policy="never"'
    environment = captured["environment"]
    assert isinstance(environment, dict)
    assert all(
        key not in environment
        for key in (
            "REAGENT_PROXY_TOKEN",
            "REAGENT_LOCAL_SESSION_TOKEN",
            "REAGENT_OPENALEX_API_KEY",
            "REAGENT_DATABASE_URL",
        )
    )


def _session(mode: str) -> dict:
    return {
        "session_id": "proxytok-v1-" + "b" * 64,
        "session_token": "process-local-fictional-token",
        "mode": mode,
        "expires_at": "2026-08-06T01:15:00Z",
        "maximum_query_variants": 0 if mode == "UPLOAD_ONLY" else 3,
        "maximum_results_per_query": 0 if mode == "UPLOAD_ONLY" else 5,
    }


def _write_receipt(root: Path, report_path: Path, *, replay: bool = False) -> dict:
    report = json.loads(report_path.read_text())
    receipt = {
        "schema_version": "local-progress-upload-receipt/v0.1",
        "report_id": report["report_id"],
        "report_checksum": report["report_checksum"],
        "receipt_id": "receipt-fictional-round-1",
        "receipt_checksum": HASH,
        "validation_status": "ACCEPTED",
        "chain_state": "VALID",
        "accepted_for_projection": True,
        "idempotent_replay": replay,
        "projection_checksum": HASH,
        "verified_at": "2026-08-06T01:03:00Z",
    }
    local_runner._write_atomic(
        root / "memory/progress/receipts" / f"{report['report_id']}.json",
        receipt,
    )
    return receipt


def test_one_command_round_generates_four_outputs_and_uploads_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _package(tmp_path)
    calls = {"codex": 0, "queries": 0, "upload": 0, "close": 0}
    monkeypatch.setattr(
        local_runner,
        "_open_session",
        lambda **kwargs: _session(kwargs["mode"]),
    )

    def codex(*, root: Path, instruction: str) -> None:
        calls["codex"] += 1
        if "PLANNING_STAGE" in instruction:
            _planning(root)
        else:
            _synthesis(root, "DEMO")

    def queries(**kwargs) -> None:
        calls["queries"] += len(kwargs["queries"])

    def upload(**kwargs):
        calls["upload"] += 1
        return _write_receipt(kwargs["root"], kwargs["report_path"])

    monkeypatch.setattr(local_runner, "_invoke_codex", codex)
    monkeypatch.setattr(local_runner, "_execute_queries", queries)
    monkeypatch.setattr(local_runner, "_upload_and_verify", upload)
    monkeypatch.setattr(
        local_runner,
        "_close_session",
        lambda **kwargs: calls.__setitem__("close", calls["close"] + 1),
    )
    result = local_runner.run_round(
        package_root=root,
        base_url="http://127.0.0.1:8000",
        mode="DEMO",
    )
    assert result["status"] == "ROUND_COMPLETED"
    assert calls == {"codex": 2, "queries": 2, "upload": 1, "close": 1}
    assert len(list((root / "memory/progress/reports").glob("prv2-*.json"))) == 1
    assert validate_package(root).valid

    replay = local_runner.run_round(
        package_root=root,
        base_url="http://127.0.0.1:8000",
        mode="DEMO",
    )
    assert replay["status"] == "ROUND_ALREADY_UPLOADED"
    assert calls == {"codex": 2, "queries": 2, "upload": 1, "close": 1}


def test_upload_failure_preserves_report_and_next_run_is_upload_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _package(tmp_path)
    opened: list[str] = []
    monkeypatch.setattr(
        local_runner,
        "_open_session",
        lambda **kwargs: opened.append(kwargs["mode"]) or _session(kwargs["mode"]),
    )
    monkeypatch.setattr(
        local_runner,
        "_invoke_codex",
        lambda *, root, instruction: (
            _planning(root) if "PLANNING_STAGE" in instruction else _synthesis(root, "DEMO")
        ),
    )
    monkeypatch.setattr(local_runner, "_execute_queries", lambda **kwargs: None)
    monkeypatch.setattr(local_runner, "_close_session", lambda **kwargs: None)
    server_persisted = {"value": False}

    def persisted_before_receipt(**kwargs):
        server_persisted["value"] = True
        raise local_runner.LocalRoundError("upload unavailable")

    monkeypatch.setattr(local_runner, "_upload_and_verify", persisted_before_receipt)
    with pytest.raises(local_runner.LocalRoundError, match="upload unavailable"):
        local_runner.run_round(
            package_root=root,
            base_url="http://127.0.0.1:8000",
            mode="DEMO",
        )
    report_path = next((root / "memory/progress/reports").glob("prv2-*.json"))
    assert server_persisted["value"] is True
    output_checksums = {
        path.name: sha256_bytes(path.read_bytes())
        for path in (root / "outputs").iterdir()
        if path.name != "README.md"
    }

    monkeypatch.setattr(
        local_runner,
        "_upload_and_verify",
        lambda **kwargs: _write_receipt(root, report_path, replay=True),
    )
    result = local_runner.run_round(
        package_root=root,
        base_url="http://127.0.0.1:8000",
        mode="DEMO",
    )
    assert result["status"] == "PENDING_UPLOAD_COMPLETED"
    assert opened == ["DEMO", "UPLOAD_ONLY"]
    assert output_checksums == {
        path.name: sha256_bytes(path.read_bytes())
        for path in (root / "outputs").iterdir()
        if path.name != "README.md"
    }
    receipt = json.loads(
        next((root / "memory/progress/receipts").glob("*.json")).read_text()
    )
    assert receipt["idempotent_replay"] is True


def test_interruption_before_report_stops_recovery_without_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _package(tmp_path)
    monkeypatch.setattr(
        local_runner,
        "_open_session",
        lambda **kwargs: _session(kwargs["mode"]),
    )
    monkeypatch.setattr(local_runner, "_close_session", lambda **kwargs: None)
    monkeypatch.setattr(
        local_runner,
        "_invoke_codex",
        lambda *, root, instruction: (
            _planning(root)
            if "PLANNING_STAGE" in instruction
            else (_ for _ in ()).throw(local_runner.LocalRoundError("synthesis interrupted"))
        ),
    )
    monkeypatch.setattr(local_runner, "_execute_queries", lambda **kwargs: None)
    with pytest.raises(local_runner.LocalRoundError, match="synthesis interrupted"):
        local_runner.run_round(
            package_root=root,
            base_url="http://127.0.0.1:8000",
            mode="DEMO",
        )
    plan_checksum = sha256_bytes((root / "outputs/search_plan.md").read_bytes())
    with pytest.raises(local_runner.LocalRoundError, match="Partial local outputs"):
        local_runner.run_round(
            package_root=root,
            base_url="http://127.0.0.1:8000",
            mode="DEMO",
        )
    assert sha256_bytes((root / "outputs/search_plan.md").read_bytes()) == plan_checksum


def test_normal_query_executor_refuses_fake_adapter_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _package(tmp_path)
    manifest = json.loads((root / "package-manifest.json").read_text())
    monkeypatch.setattr(
        local_runner,
        "_http_json",
        lambda **kwargs: (
            201,
            {
                "operation_status": "SUCCEEDED",
                "provider_adapter": {"adapter_id": local_runner.FAKE_ADAPTER_ID},
                "provider_data": {
                    "source_classification": "WHOLLY_FICTIONAL_SYNTHETIC_FIXTURE",
                    "papers": [],
                },
            },
        ),
    )
    with pytest.raises(local_runner.LocalRoundError, match="selected mode"):
        local_runner._execute_queries(
            root=root,
            base_url="http://127.0.0.1:8000",
            manifest=manifest,
            session=_session("NORMAL"),
            mode="NORMAL",
            queries=[{"query_id": "query-1", "query": "fictional public query"}],
        )


def test_normal_query_executor_accepts_only_openalex_proxy_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _package(tmp_path)
    manifest = json.loads((root / "package-manifest.json").read_text())
    provider_data = {
        "schema_version": "paper-search-result/v0.1",
        "source_classification": "OPENALEX_NORMALIZED_METADATA",
        "untrusted_provider_data": True,
        "papers": [],
    }
    monkeypatch.setattr(
        local_runner,
        "_http_json",
        lambda **kwargs: (
            201,
            {
                "operation_status": "SUCCEEDED",
                "operation_id": "proxyop-v1-" + "1" * 64,
                "request_content_checksum": HASH,
                "provider_data_checksum": HASH,
                "response_content_checksum": HASH,
                "provider_adapter": {"adapter_id": local_runner.OPENALEX_ADAPTER_ID},
                "provider_data": provider_data,
                "usage": {"provider_http_calls": 1, "reported_cost_microusd": 1000},
            },
        ),
    )
    local_runner._execute_queries(
        root=root,
        base_url="http://127.0.0.1:8000",
        manifest=manifest,
        session=_session("NORMAL"),
        mode="NORMAL",
        queries=[{"query_id": "query-1", "query": "fictional public query"}],
    )
    stored = json.loads(
        (root / "memory/search/operations/query-1.result.json").read_text()
    )
    assert stored["mode"] == "NORMAL"
    assert stored["provider_adapter"]["adapter_id"] == local_runner.OPENALEX_ADAPTER_ID
    assert stored["provider_data"] == provider_data
