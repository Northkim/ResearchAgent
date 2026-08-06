from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

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


def _record_results(root: Path, mode: str, queries: list[dict[str, str]]) -> None:
    adapter = (
        local_runner.FAKE_ADAPTER_ID
        if mode == "DEMO"
        else local_runner.OPENALEX_ADAPTER_ID
    )
    for item in queries:
        local_runner._write_atomic(
            root / "memory/search/operations" / f"{item['query_id']}.result.json",
            {
                "schema_version": "literature-search-normalized-query-result/v0.1",
                "mode": mode,
                "query_id": item["query_id"],
                "issued_query": item["query"],
                "provider_adapter": {"adapter_id": adapter},
                "provider_data": {"papers": []},
            },
        )


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

    class Process:
        returncode = 0

        def __init__(self, command, **kwargs):
            captured["command"] = command
            captured["environment"] = kwargs["env"]

        def poll(self):
            return 0

    monkeypatch.setattr(local_runner, "_codex_preflight", lambda *args, **kwargs: "codex-cli 0.146.0")
    monkeypatch.setattr(local_runner.subprocess, "Popen", Process)
    local_runner._invoke_codex(
        root=tmp_path,
        instruction="fixed-stage",
        interactive=False,
    )
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


def test_default_cli_selects_interactive_and_auto_is_explicit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        local_runner,
        "run_round",
        lambda **kwargs: calls.append(kwargs) or {"status": "FIXTURE"},
    )
    assert local_runner.main(["run", str(tmp_path)]) == 0
    assert calls[-1]["auto"] is False
    assert local_runner.main(["run", str(tmp_path), "--auto"]) == 0
    assert calls[-1]["auto"] is True


def test_interactive_codex_inherits_terminal_and_passes_fixed_instruction_as_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class Process:
        returncode = 0

        def __init__(self, command, **kwargs):
            captured["command"] = command
            captured["kwargs"] = kwargs

        def poll(self):
            return 0

    terminal = SimpleNamespace(isatty=lambda: True)
    monkeypatch.setattr(local_runner.sys, "stdin", terminal)
    monkeypatch.setattr(local_runner.sys, "stdout", terminal)
    monkeypatch.setattr(local_runner.sys, "stderr", terminal)
    monkeypatch.setattr(local_runner, "_codex_executable", lambda: "/safe/codex")
    monkeypatch.setattr(local_runner, "_codex_preflight", lambda *args, **kwargs: "codex-cli 0.146.0")
    monkeypatch.setattr(local_runner.subprocess, "Popen", Process)
    instruction = "fixed instruction; topic remains in Package data"
    local_runner._invoke_codex(
        root=tmp_path,
        instruction=instruction,
        interactive=True,
    )
    command = captured["command"]
    assert isinstance(command, list)
    assert command[0] == "/safe/codex"
    assert "exec" not in command
    assert command[-1] == instruction
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["stdin"] is None
    assert "stdout" not in kwargs and "stderr" not in kwargs


def test_interactive_codex_requires_a_real_terminal_before_process_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = SimpleNamespace(isatty=lambda: False)
    monkeypatch.setattr(local_runner.sys, "stdin", terminal)
    monkeypatch.setattr(local_runner.sys, "stdout", terminal)
    monkeypatch.setattr(local_runner.sys, "stderr", terminal)
    monkeypatch.setattr(
        local_runner,
        "_codex_executable",
        lambda: (_ for _ in ()).throw(AssertionError("must not resolve Codex")),
    )
    with pytest.raises(
        local_runner.LocalRoundError,
        match=r"Stage \[4/6\].*requires a terminal.*--auto",
    ):
        local_runner._invoke_codex(
            root=tmp_path,
            instruction="fixed",
            interactive=True,
        )


@pytest.mark.parametrize(
    ("version", "login_code", "expected"),
    (
        ("codex-cli 0.145.0", 0, "version is not supported"),
        ("codex-cli 0.146.0", 1, "not authenticated"),
    ),
)
def test_codex_preflight_reports_safe_stage_specific_errors(
    monkeypatch: pytest.MonkeyPatch,
    version: str,
    login_code: int,
    expected: str,
) -> None:
    results = iter(
        (
            SimpleNamespace(returncode=0, stdout=version),
            SimpleNamespace(
                returncode=0,
                stdout="--ask-for-approval --sandbox --cd --no-alt-screen",
            ),
            SimpleNamespace(returncode=login_code, stdout="sensitive fixture detail"),
        )
    )
    monkeypatch.setattr(
        local_runner.subprocess,
        "run",
        lambda *args, **kwargs: next(results),
    )
    with pytest.raises(local_runner.LocalRoundError, match=expected) as captured:
        local_runner._codex_preflight("/safe/codex", auto=False)
    assert "sensitive fixture detail" not in str(captured.value)


def test_interactive_instruction_declares_all_owner_checkpoints_without_topic_data() -> None:
    instruction = local_runner._interactive_instruction("NORMAL", resume=False)
    for phrase in (
        "SEARCH-PLAN CHECKPOINT",
        "CANDIDATE-SCREENING CHECKPOINT",
        "FINALIZATION CHECKPOINT",
        "explicit proceed",
        "command finish",
        "Do not create the final Progress",
    ):
        assert phrase in instruction
    assert "A fictional public topic about transparent continuity" not in instruction


def test_provider_controller_waits_for_machine_plan_confirmation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _package(tmp_path)
    manifest = json.loads((root / "package-manifest.json").read_text())
    calls = {"queries": 0}
    monkeypatch.setattr(
        local_runner,
        "_execute_queries",
        lambda **kwargs: calls.__setitem__("queries", calls["queries"] + len(kwargs["queries"])),
    )
    local_runner._initialize_control(
        root=root,
        manifest=manifest,
        mode="DEMO",
        execution_style="INTERACTIVE",
    )
    stop = threading.Event()
    errors: list[BaseException] = []
    controller = threading.Thread(
        target=local_runner._provider_controller,
        kwargs={
            "root": root,
            "base_url": "http://127.0.0.1:8000",
            "manifest": manifest,
            "session": _session("DEMO"),
            "mode": "DEMO",
            "topic": json.loads((root / "inputs/research_request.json").read_text())["topic"],
            "stop": stop,
            "errors": errors,
        },
    )
    controller.start()
    time.sleep(local_runner.CONTROL_POLL_SECONDS * 3)
    assert calls["queries"] == 0
    _planning(root)
    local_runner._mark_plan_confirmed(root)
    deadline = time.monotonic() + 2
    while calls["queries"] == 0 and time.monotonic() < deadline:
        time.sleep(0.02)
    stop.set()
    controller.join(timeout=2)
    assert not errors
    assert calls["queries"] == 2
    assert local_runner._load_control(root)["state"] == "SEARCH_COMPLETED"


def test_interruption_revokes_session_and_never_uploads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _package(tmp_path)
    calls = {"close": 0, "upload": 0}
    monkeypatch.setattr(local_runner, "_check_backend", lambda base_url: None)
    monkeypatch.setattr(local_runner, "_open_session", lambda **kwargs: _session(kwargs["mode"]))
    monkeypatch.setattr(
        local_runner,
        "_run_interactive_codex",
        lambda **kwargs: (_ for _ in ()).throw(local_runner.RoundInterrupted("fixture")),
    )
    monkeypatch.setattr(
        local_runner,
        "_upload_and_verify",
        lambda **kwargs: calls.__setitem__("upload", calls["upload"] + 1),
    )
    monkeypatch.setattr(
        local_runner,
        "_close_session",
        lambda **kwargs: calls.__setitem__("close", calls["close"] + 1),
    )
    with pytest.raises(local_runner.RoundInterrupted):
        local_runner.run_round(
            package_root=root,
            base_url="http://127.0.0.1:8000",
            mode="DEMO",
        )
    control = local_runner._load_control(root)
    assert control["state"] == "INTERRUPTED"
    assert control["failure_code"] == "OWNER_INTERRUPTED"
    assert calls == {"close": 1, "upload": 0}
    assert not local_runner._reports(root)


def test_keyboard_interrupt_is_forwarded_and_child_is_reaped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class Process:
        returncode = None

        def __init__(self, command, **kwargs):
            self.polls = 0

        def poll(self):
            self.polls += 1
            if self.polls == 1:
                raise KeyboardInterrupt
            return self.returncode

        def send_signal(self, value):
            calls.append(f"signal:{value}")
            self.returncode = 130

        def wait(self, timeout=None):
            calls.append("wait")
            return 130

    terminal = SimpleNamespace(isatty=lambda: True)
    monkeypatch.setattr(local_runner.sys, "stdin", terminal)
    monkeypatch.setattr(local_runner.sys, "stdout", terminal)
    monkeypatch.setattr(local_runner.sys, "stderr", terminal)
    monkeypatch.setattr(local_runner, "_codex_executable", lambda: "/safe/codex")
    monkeypatch.setattr(local_runner, "_codex_preflight", lambda *args, **kwargs: "codex-cli 0.146.0")
    monkeypatch.setattr(local_runner.subprocess, "Popen", Process)
    with pytest.raises(local_runner.RoundInterrupted):
        local_runner._invoke_codex(
            root=tmp_path,
            instruction="fixed",
            interactive=True,
        )
    assert calls == [f"signal:{local_runner.signal.SIGINT}", "wait"]


def test_termination_signal_is_converted_to_cleanup_and_reaps_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    handlers: dict[int, object] = {}

    class Process:
        returncode = None

        def __init__(self, command, **kwargs):
            self.polls = 0

        def poll(self):
            self.polls += 1
            if self.polls == 1:
                handler = handlers[local_runner.signal.SIGTERM]
                assert callable(handler)
                handler(local_runner.signal.SIGTERM, None)
            return self.returncode

        def send_signal(self, value):
            calls.append(f"signal:{value}")
            self.returncode = 143

        def wait(self, timeout=None):
            calls.append("wait")
            return 143

    terminal = SimpleNamespace(isatty=lambda: True)
    monkeypatch.setattr(local_runner.sys, "stdin", terminal)
    monkeypatch.setattr(local_runner.sys, "stdout", terminal)
    monkeypatch.setattr(local_runner.sys, "stderr", terminal)
    monkeypatch.setattr(local_runner, "_codex_executable", lambda: "/safe/codex")
    monkeypatch.setattr(local_runner, "_codex_preflight", lambda *args, **kwargs: "codex-cli 0.146.0")
    monkeypatch.setattr(local_runner.subprocess, "Popen", Process)
    monkeypatch.setattr(local_runner.signal, "getsignal", lambda signum: "previous")
    monkeypatch.setattr(
        local_runner.signal,
        "signal",
        lambda signum, handler: handlers.__setitem__(signum, handler),
    )
    with pytest.raises(local_runner.RoundInterrupted, match="termination signal"):
        local_runner._invoke_codex(
            root=tmp_path,
            instruction="fixed",
            interactive=True,
        )
    assert calls == [f"signal:{local_runner.signal.SIGINT}", "wait"]
    assert handlers[local_runner.signal.SIGTERM] == "previous"


def test_explicit_restart_removes_only_round_mutable_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _package(tmp_path)
    manifest = json.loads((root / "package-manifest.json").read_text())
    immutable = sha256_bytes((root / "inputs/research_request.json").read_bytes())
    _planning(root)
    (root / "memory/search/operations/query-1.request.json").write_text("{}\n")
    monkeypatch.setattr("builtins.input", lambda prompt: "restart-round")
    local_runner._reset_round(root, manifest)
    assert not (root / "outputs/search_plan.md").exists()
    assert not list((root / "memory/search/operations").glob("*.json"))
    assert local_runner._load_control(root)["state"] == "NOT_STARTED"
    assert sha256_bytes((root / "inputs/research_request.json").read_bytes()) == immutable


def test_explicit_resume_preserves_plan_and_completes_same_round(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _package(tmp_path)
    manifest = json.loads((root / "package-manifest.json").read_text())
    local_runner._initialize_control(
        root=root,
        manifest=manifest,
        mode="DEMO",
        execution_style="INTERACTIVE",
    )
    _planning(root)
    local_runner._mark_plan_confirmed(root)
    queries = local_runner._validate_query_plan(
        root,
        json.loads((root / "inputs/research_request.json").read_text())["topic"],
    )
    _record_results(root, "DEMO", queries)
    local_runner._mark_search_completed(root)
    local_runner._mark_interrupted(root, "CANDIDATE_SCREENING")
    plan_checksum = sha256_bytes((root / "outputs/search_plan.md").read_bytes())
    observed = {"resume": False}
    monkeypatch.setattr(local_runner, "_check_backend", lambda base_url: None)
    monkeypatch.setattr(local_runner, "_open_session", lambda **kwargs: _session(kwargs["mode"]))
    monkeypatch.setattr(local_runner, "_close_session", lambda **kwargs: None)

    def resume_codex(**kwargs) -> None:
        observed["resume"] = kwargs["resume"]
        _synthesis(kwargs["root"], "DEMO")
        local_runner._mark_finalized(kwargs["root"])

    monkeypatch.setattr(local_runner, "_run_interactive_codex", resume_codex)
    monkeypatch.setattr(
        local_runner,
        "_upload_and_verify",
        lambda **kwargs: _write_receipt(kwargs["root"], kwargs["report_path"]),
    )
    result = local_runner.run_round(
        package_root=root,
        base_url="http://127.0.0.1:8000",
        mode="DEMO",
        resume=True,
    )
    assert result["status"] == "ROUND_COMPLETED"
    assert observed["resume"] is True
    assert sha256_bytes((root / "outputs/search_plan.md").read_bytes()) == plan_checksum
    assert len(local_runner._reports(root)) == 1
    assert len(local_runner._receipts(root)) == 1


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


def test_upload_session_request_is_exact_report_bound_and_contains_no_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _package(tmp_path)
    manifest = json.loads((root / "package-manifest.json").read_text())
    report = {
        "execution_round": 1,
        "report_id": "prv2-" + "a" * 64,
        "report_content_checksum": "sha256:" + "b" * 64,
    }
    report_path = root / "memory/progress/reports" / f"{report['report_id']}.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    captured: dict[str, object] = {}

    def request(**kwargs):
        captured.update(kwargs)
        return 201, _session("UPLOAD_ONLY")

    monkeypatch.setattr(local_runner, "_http_json", request)
    local_runner._open_session(
        base_url="http://127.0.0.1:8000",
        manifest=manifest,
        mode="UPLOAD_ONLY",
        report_path=report_path,
    )
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["execution_round"] == 1
    assert payload["report_id"] == report["report_id"]
    assert payload["report_content_checksum"] == report["report_content_checksum"]
    assert "session_token" not in payload
    assert "token" not in payload


def test_one_command_round_generates_four_outputs_and_uploads_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _package(tmp_path)
    calls = {"codex": 0, "queries": 0, "upload": 0, "close": 0}
    monkeypatch.setattr(local_runner, "_check_backend", lambda base_url: None)
    monkeypatch.setattr(
        local_runner,
        "_open_session",
        lambda **kwargs: _session(kwargs["mode"]),
    )

    def codex(*, root: Path, instruction: str, interactive: bool) -> None:
        assert interactive is False
        calls["codex"] += 1
        if "PLANNING_STAGE" in instruction:
            _planning(root)
        else:
            _synthesis(root, "DEMO")

    def queries(**kwargs) -> None:
        calls["queries"] += len(kwargs["queries"])
        _record_results(kwargs["root"], kwargs["mode"], kwargs["queries"])

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
        auto=True,
    )
    assert result["status"] == "ROUND_COMPLETED"
    assert calls == {"codex": 2, "queries": 2, "upload": 1, "close": 2}
    assert len(list((root / "memory/progress/reports").glob("prv2-*.json"))) == 1
    assert validate_package(root).valid

    replay = local_runner.run_round(
        package_root=root,
        base_url="http://127.0.0.1:8000",
        mode="DEMO",
        auto=True,
    )
    assert replay["status"] == "ROUND_ALREADY_UPLOADED"
    assert calls == {"codex": 2, "queries": 2, "upload": 1, "close": 2}


def test_upload_failure_preserves_report_and_next_run_is_upload_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _package(tmp_path)
    opened: list[str] = []
    monkeypatch.setattr(local_runner, "_check_backend", lambda base_url: None)
    monkeypatch.setattr(
        local_runner,
        "_open_session",
        lambda **kwargs: opened.append(kwargs["mode"]) or _session(kwargs["mode"]),
    )
    monkeypatch.setattr(
        local_runner,
        "_invoke_codex",
        lambda *, root, instruction, interactive: (
            _planning(root) if "PLANNING_STAGE" in instruction else _synthesis(root, "DEMO")
        ),
    )
    monkeypatch.setattr(
        local_runner,
        "_execute_queries",
        lambda **kwargs: _record_results(kwargs["root"], kwargs["mode"], kwargs["queries"]),
    )
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
            auto=True,
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
        auto=True,
    )
    assert result["status"] == "PENDING_UPLOAD_COMPLETED"
    output = capsys.readouterr().out
    assert "Upload-only recovery selected" in output
    assert "Codex and Provider search will be skipped" in output
    assert opened == ["DEMO", "UPLOAD_ONLY", "UPLOAD_ONLY"]
    assert output_checksums == {
        path.name: sha256_bytes(path.read_bytes())
        for path in (root / "outputs").iterdir()
        if path.name != "README.md"
    }
    receipt = json.loads(
        next((root / "memory/progress/receipts").glob("*.json")).read_text()
    )
    assert receipt["idempotent_replay"] is True


def test_expired_search_session_does_not_block_fresh_first_upload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _package(tmp_path)
    opened: list[str] = []
    uploaded_with: list[str] = []
    monkeypatch.setattr(local_runner, "_check_backend", lambda base_url: None)
    monkeypatch.setattr(
        local_runner,
        "_open_session",
        lambda **kwargs: opened.append(kwargs["mode"]) or _session(kwargs["mode"]),
    )
    monkeypatch.setattr(
        local_runner,
        "_invoke_codex",
        lambda *, root, instruction, interactive: (
            _planning(root) if "PLANNING_STAGE" in instruction else _synthesis(root, "DEMO")
        ),
    )
    monkeypatch.setattr(
        local_runner,
        "_execute_queries",
        lambda **kwargs: _record_results(kwargs["root"], kwargs["mode"], kwargs["queries"]),
    )

    def close(**kwargs) -> None:
        if kwargs["session"]["mode"] == "DEMO":
            raise local_runner.LocalHTTPError(
                stage="SESSION_REVOCATION", code="SESSION_EXPIRED", http_status=401
            )

    def upload(**kwargs):
        uploaded_with.append(kwargs["session"]["mode"])
        return _write_receipt(kwargs["root"], kwargs["report_path"])

    monkeypatch.setattr(local_runner, "_close_session", close)
    monkeypatch.setattr(local_runner, "_upload_and_verify", upload)
    result = local_runner.run_round(
        package_root=root,
        base_url="http://127.0.0.1:8000",
        mode="DEMO",
        auto=True,
    )
    assert result["status"] == "ROUND_COMPLETED"
    assert opened == ["DEMO", "UPLOAD_ONLY"]
    assert uploaded_with == ["UPLOAD_ONLY"]


@pytest.mark.parametrize(
    ("failure_code", "expected_upload_attempts"),
    [("SESSION_EXPIRED", 2), ("TOKEN_UNKNOWN", 1), ("PACKAGE_SCOPE_MISMATCH", 1)],
)
def test_upload_refreshes_only_explicit_expiry_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_code: str,
    expected_upload_attempts: int,
) -> None:
    root = _package(tmp_path)
    attempts: list[str] = []
    monkeypatch.setattr(local_runner, "_check_backend", lambda base_url: None)
    monkeypatch.setattr(local_runner, "_open_session", lambda **kwargs: _session(kwargs["mode"]))
    monkeypatch.setattr(local_runner, "_close_session", lambda **kwargs: None)
    monkeypatch.setattr(
        local_runner,
        "_invoke_codex",
        lambda *, root, instruction, interactive: (
            _planning(root) if "PLANNING_STAGE" in instruction else _synthesis(root, "DEMO")
        ),
    )
    monkeypatch.setattr(
        local_runner,
        "_execute_queries",
        lambda **kwargs: _record_results(kwargs["root"], kwargs["mode"], kwargs["queries"]),
    )

    def upload(**kwargs):
        attempts.append(kwargs["envelope"]["envelope_checksum"])
        if len(attempts) == 1 or expected_upload_attempts == 1:
            raise local_runner.LocalHTTPError(
                stage="PROGRESS_REPORT_UPLOAD", code=failure_code, http_status=401
            )
        return _write_receipt(kwargs["root"], kwargs["report_path"], replay=True)

    monkeypatch.setattr(local_runner, "_upload_and_verify", upload)
    if expected_upload_attempts == 1:
        with pytest.raises(local_runner.LocalHTTPError) as captured:
            local_runner.run_round(
                package_root=root,
                base_url="http://127.0.0.1:8000",
                mode="DEMO",
                auto=True,
            )
        assert captured.value.code == failure_code
    else:
        result = local_runner.run_round(
            package_root=root,
            base_url="http://127.0.0.1:8000",
            mode="DEMO",
            auto=True,
        )
        assert result["status"] == "ROUND_COMPLETED"
    assert len(attempts) == expected_upload_attempts
    assert len(set(attempts)) == 1


def test_unknown_response_reconciles_exact_report_without_duplicate_local_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _package(tmp_path)
    attempts: list[str] = []
    monkeypatch.setattr(local_runner, "_check_backend", lambda base_url: None)
    monkeypatch.setattr(local_runner, "_open_session", lambda **kwargs: _session(kwargs["mode"]))
    monkeypatch.setattr(local_runner, "_close_session", lambda **kwargs: None)
    monkeypatch.setattr(
        local_runner,
        "_invoke_codex",
        lambda *, root, instruction, interactive: (
            _planning(root) if "PLANNING_STAGE" in instruction else _synthesis(root, "DEMO")
        ),
    )
    monkeypatch.setattr(
        local_runner,
        "_execute_queries",
        lambda **kwargs: _record_results(kwargs["root"], kwargs["mode"], kwargs["queries"]),
    )

    def upload(**kwargs):
        attempts.append(kwargs["envelope"]["envelope_checksum"])
        if len(attempts) == 1:
            raise local_runner.LocalHTTPError(
                stage="PROGRESS_REPORT_UPLOAD",
                code="RESPONSE_OUTCOME_UNKNOWN",
                http_status=None,
            )
        return _write_receipt(kwargs["root"], kwargs["report_path"], replay=True)

    monkeypatch.setattr(local_runner, "_upload_and_verify", upload)
    result = local_runner.run_round(
        package_root=root,
        base_url="http://127.0.0.1:8000",
        mode="DEMO",
        auto=True,
    )
    assert result["status"] == "ROUND_COMPLETED"
    assert attempts[0] == attempts[1]
    assert len(local_runner._reports(root)) == 1
    assert len(local_runner._receipts(root)) == 1


def test_cleanup_failure_does_not_mask_primary_round_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _package(tmp_path)
    monkeypatch.setattr(local_runner, "_check_backend", lambda base_url: None)
    monkeypatch.setattr(local_runner, "_open_session", lambda **kwargs: _session(kwargs["mode"]))
    monkeypatch.setattr(
        local_runner,
        "_run_auto_codex",
        lambda **kwargs: (_ for _ in ()).throw(local_runner.LocalRoundError("primary round failure")),
    )
    monkeypatch.setattr(
        local_runner,
        "_close_session",
        lambda **kwargs: (_ for _ in ()).throw(
            local_runner.LocalHTTPError(
                stage="SESSION_REVOCATION", code="TOKEN_UNKNOWN", http_status=401
            )
        ),
    )
    with pytest.raises(local_runner.LocalRoundError, match="primary round failure"):
        local_runner.run_round(
            package_root=root,
            base_url="http://127.0.0.1:8000",
            mode="DEMO",
            auto=True,
        )


def test_interruption_before_report_stops_recovery_without_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _package(tmp_path)
    monkeypatch.setattr(local_runner, "_check_backend", lambda base_url: None)
    monkeypatch.setattr(
        local_runner,
        "_open_session",
        lambda **kwargs: _session(kwargs["mode"]),
    )
    monkeypatch.setattr(local_runner, "_close_session", lambda **kwargs: None)
    monkeypatch.setattr(
        local_runner,
        "_invoke_codex",
        lambda *, root, instruction, interactive: (
            _planning(root)
            if "PLANNING_STAGE" in instruction
            else (_ for _ in ()).throw(local_runner.LocalRoundError("synthesis interrupted"))
        ),
    )
    monkeypatch.setattr(
        local_runner,
        "_execute_queries",
        lambda **kwargs: _record_results(kwargs["root"], kwargs["mode"], kwargs["queries"]),
    )
    with pytest.raises(local_runner.LocalRoundError, match="synthesis interrupted"):
        local_runner.run_round(
            package_root=root,
            base_url="http://127.0.0.1:8000",
            mode="DEMO",
            auto=True,
        )
    plan_checksum = sha256_bytes((root / "outputs/search_plan.md").read_bytes())
    with pytest.raises(local_runner.LocalRoundError, match="Partial local work"):
        local_runner.run_round(
            package_root=root,
            base_url="http://127.0.0.1:8000",
            mode="DEMO",
            auto=True,
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
