#!/usr/bin/env python3
"""Self-contained one-round Literature Search launcher copied into Packages."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import runpy
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

PROXY_CONTRACT_VERSION = "reagent.cloud-api-proxy/v0.1"
PROXY_CAPABILITY = "paper.search/v0.1"
OPENALEX_ADAPTER_ID = "reagent.openalex-paper-search/v0.1"
FAKE_ADAPTER_ID = "reagent.deterministic-fake-paper-search/v0.1"
MAXIMUM_QUERY_VARIANTS = 3
MINIMUM_QUERY_VARIANTS = 2
MAXIMUM_RESULTS_PER_QUERY = 5
MAXIMUM_RETAINED_CANDIDATES = 15
TARGET_SELECTED_MINIMUM = 3
TARGET_SELECTED_MAXIMUM = 6
HTTP_TIMEOUT_SECONDS = 15.0
MAXIMUM_LOCAL_RESPONSE_BYTES = 1024 * 1024
CODEX_TIMEOUT_SECONDS = 20 * 60
CLIENT_VERSION = "reagent-local-literature-search/0.1.0"
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


class LocalRoundError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _root(value: str | Path) -> Path:
    supplied = Path(value)
    if supplied.is_symlink():
        raise LocalRoundError("Package root must not be a symbolic link")
    root = supplied.resolve()
    if not root.is_dir():
        raise LocalRoundError("Package root must be a directory")
    return root


def _load_object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise LocalRoundError(f"{label} must be a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LocalRoundError(f"{label} must be valid UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise LocalRoundError(f"{label} must be a JSON object")
    return value


def _write_atomic(path: Path, value: dict[str, Any], *, overwrite: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise LocalRoundError(f"Refusing to overwrite existing local state: {path.name}")
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(canonical_json(value) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def _base_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    try:
        port = parsed.port
    except ValueError as error:
        raise LocalRoundError("Backend URL has an invalid port") from error
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or port is None
        or not 1 <= port <= 65535
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise LocalRoundError(
            "Backend URL must be literal http://127.0.0.1:<port>"
        )
    return f"http://127.0.0.1:{port}"


def _http_json(
    *,
    url: str,
    method: str,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
) -> tuple[int, dict[str, Any]]:
    data = None if payload is None else canonical_json(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            raw = response.read(MAXIMUM_LOCAL_RESPONSE_BYTES + 1)
            status = response.status
    except urllib.error.HTTPError as error:
        raw = error.read(MAXIMUM_LOCAL_RESPONSE_BYTES + 1)
        try:
            body = json.loads(raw.decode("utf-8"))
            code = body.get("error", {}).get("code", "HTTP_ERROR")
        except Exception:
            code = "HTTP_ERROR"
        raise LocalRoundError(
            f"Local ReAgent request failed closed with HTTP {error.code} ({code})"
        ) from None
    except urllib.error.URLError as error:
        raise LocalRoundError(
            "Local ReAgent request outcome is unknown; do not rerun research"
        ) from error
    if len(raw) > MAXIMUM_LOCAL_RESPONSE_BYTES:
        raise LocalRoundError("Local ReAgent response exceeded the safe size bound")
    if not raw and status == 204:
        return status, {}
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LocalRoundError("Local ReAgent response was not valid JSON") from error
    if not isinstance(body, dict):
        raise LocalRoundError("Local ReAgent response was not a JSON object")
    return status, body


def _identity_query(manifest: dict[str, Any]) -> str:
    return urllib.parse.urlencode(
        {
            "package_id": manifest["package_id"],
            "package_checksum": manifest["package_checksum"],
            "workflow_id": manifest["workflow_id"],
            "workflow_version": manifest["workflow_version"],
            "workflow_checksum": manifest["workflow_checksum"],
        }
    )


def _open_session(
    *,
    base_url: str,
    manifest: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    project_id = urllib.parse.quote(manifest["experimental_project_identity"], safe="")
    _, session = _http_json(
        url=f"{base_url}/projects/{project_id}/local-sessions",
        method="POST",
        payload={
            "package_id": manifest["package_id"],
            "package_checksum": manifest["package_checksum"],
            "workflow_id": manifest["workflow_id"],
            "workflow_version": manifest["workflow_version"],
            "workflow_checksum": manifest["workflow_checksum"],
            "mode": mode,
        },
    )
    required = {
        "session_id",
        "session_token",
        "mode",
        "expires_at",
        "maximum_query_variants",
        "maximum_results_per_query",
    }
    if not required <= set(session):
        raise LocalRoundError("Local session response is incomplete")
    if session["mode"] != mode:
        raise LocalRoundError("Local session mode does not match the request")
    return session


def _close_session(
    *,
    base_url: str,
    manifest: dict[str, Any],
    session: dict[str, Any],
) -> None:
    project = urllib.parse.quote(manifest["experimental_project_identity"], safe="")
    session_id = urllib.parse.quote(session["session_id"], safe="")
    _http_json(
        url=(
            f"{base_url}/projects/{project}/local-sessions/{session_id}?"
            f"{_identity_query(manifest)}"
        ),
        method="DELETE",
        token=session["session_token"],
    )


def _validate_package(root: Path) -> None:
    try:
        namespace = runpy.run_path(str(root / "validate_package.py"))
        namespace["validate"](root)
    except Exception as error:
        raise LocalRoundError(f"Package validation failed: {error}") from error


def _context_snapshot(root: Path) -> str:
    try:
        namespace = runpy.run_path(str(root / "progress_report.py"))
        return namespace["snapshot"](root)["context_before_checksum"]
    except Exception as error:
        raise LocalRoundError(f"Context snapshot failed: {error}") from error


def _reports(root: Path) -> list[Path]:
    return sorted((root / "memory/progress/reports").glob("prv2-*.json"))


def _receipts(root: Path) -> list[Path]:
    return sorted((root / "memory/progress/receipts").glob("*.json"))


def _partial_state(root: Path) -> bool:
    outputs = [
        path
        for path in (root / "outputs").iterdir()
        if path.is_file() and path.name != "README.md"
    ]
    operations = list((root / "memory/search/operations").glob("*.json"))
    query_plan = _load_object(
        root / "memory/search/query_plan.json",
        "query plan state",
    )
    return bool(outputs or operations or query_plan.get("status") != "PENDING")


def _codex_executable() -> str:
    configured = os.environ.get("REAGENT_CODEX_EXECUTABLE", "codex")
    if os.path.sep in configured:
        path = Path(configured)
        if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
            raise LocalRoundError("Configured Codex executable is unavailable")
        return str(path.resolve())
    resolved = shutil.which(configured)
    if resolved is None:
        raise LocalRoundError("Codex CLI is required for a normal local round")
    return resolved


def _invoke_codex(*, root: Path, instruction: str) -> None:
    environment = dict(os.environ)
    for key in (
        "REAGENT_PROXY_TOKEN",
        "REAGENT_LOCAL_SESSION_TOKEN",
        "REAGENT_OPENALEX_API_KEY",
        "REAGENT_DATABASE_URL",
    ):
        environment.pop(key, None)
    command = [
        _codex_executable(),
        "exec",
        "--ephemeral",
        "--skip-git-repo-check",
        "--sandbox",
        "workspace-write",
        "--config",
        'approval_policy="never"',
        "-C",
        str(root),
        instruction,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=CODEX_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise LocalRoundError("Codex stage exceeded the one-round time limit") from error
    if completed.returncode != 0:
        raise LocalRoundError("Codex did not complete the required local stage")


def _planning_instruction(mode: str) -> str:
    return f"""MVP-LS1 PLANNING_STAGE. Follow AGENT.md and the pinned Literature Search Skill.
This is exactly one local Workflow round in {mode} mode. Read the immutable topic.
Write outputs/search_plan.md with all required headings and write
memory/search/query_plan.json using its documented schema. Preserve the original
topic, derive 2-3 bounded query variants, set status READY, and do no network or
Provider work. Do not create candidates, selections, context changes, reports,
or receipts. Stop after those two planning files are valid."""


def _synthesis_instruction(mode: str, started_at: str) -> str:
    mode_rule = (
        "Every result is fictional. Label every output and summary FICTIONAL DEMO EVIDENCE."
        if mode == "DEMO"
        else "Use the real normalized OpenAlex metadata exactly as local evidence."
    )
    return f"""MVP-LS1 SYNTHESIS_STAGE. Follow AGENT.md and the pinned Literature Search Skill.
This is the completion half of the same round, started at {started_at}. {mode_rule}
Read the normalized responses under memory/search/operations in query-plan order.
Preserve Provider and author order, deduplicate by OpenAlex/provider identity and DOI,
screen for the immutable topic, and write candidate_papers.json, selected_papers.json,
and literature_search_report.md to their exact declared output paths. Never claim full
text was read. Update only the JSON state block in memory/context.md, preserve its
exact schema/Package identity, set all four completed_outputs, and recompute its
context_checksum using canonical sorted compact JSON after setting it to null. Replace
memory/progress/report-draft.json
with a valid round-1 draft. Its completed_work must contain the exact count lines
'Queries performed: N', 'Candidates retained: N', 'Papers selected: N', and
'Outputs generated: 4'. current_state must be a concise result summary. warnings must
contain the evidence limitation. Do not create a final Progress Report or upload it;
the deterministic launcher performs those mechanical steps. Stop after local files are complete."""


def _validate_query_plan(root: Path, topic: str) -> list[dict[str, str]]:
    plan = _load_object(root / "memory/search/query_plan.json", "query plan")
    if set(plan) != {"schema_version", "status", "original_topic", "queries"}:
        raise LocalRoundError("Query plan fields do not match the fixed contract")
    if (
        plan["schema_version"] != "literature-search-query-plan/v0.1"
        or plan["status"] != "READY"
        or plan["original_topic"] != topic
        or not isinstance(plan["queries"], list)
        or not MINIMUM_QUERY_VARIANTS <= len(plan["queries"]) <= MAXIMUM_QUERY_VARIANTS
    ):
        raise LocalRoundError("Query plan violates the bounded search policy")
    queries: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_queries: set[str] = set()
    for index, item in enumerate(plan["queries"], start=1):
        if not isinstance(item, dict) or set(item) != {"query_id", "query"}:
            raise LocalRoundError("Query plan entry fields are invalid")
        query_id = item["query_id"]
        query = item["query"]
        if query_id != f"query-{index}" or not isinstance(query, str):
            raise LocalRoundError("Query identity must preserve declared order")
        query = query.strip()
        if not query or len(query) > 500 or any(ord(char) < 32 for char in query):
            raise LocalRoundError("Query text is outside the Proxy contract")
        folded = query.casefold()
        if query_id in seen_ids or folded in seen_queries:
            raise LocalRoundError("Query variants must be unique")
        seen_ids.add(query_id)
        seen_queries.add(folded)
        queries.append({"query_id": query_id, "query": query})
    return queries


def _proxy_request(
    *,
    manifest: dict[str, Any],
    query: str,
    session_id: str,
) -> dict[str, Any]:
    semantic = {
        "proxy_contract_version": PROXY_CONTRACT_VERSION,
        "project_id": manifest["experimental_project_identity"],
        "package_id": manifest["package_id"],
        "package_checksum": manifest["package_checksum"],
        "workflow_id": manifest["workflow_id"],
        "workflow_version": manifest["workflow_version"],
        "workflow_checksum": manifest["workflow_checksum"],
        "capability": PROXY_CAPABILITY,
        "parameters": {"max_results": MAXIMUM_RESULTS_PER_QUERY, "query": query},
        "harness_type": "CODEX",
        "harness_version": None,
        "harness_session_id": session_id,
        "client_timestamp": _timestamp(),
    }
    return {
        **semantic,
        "idempotency_key": str(uuid.uuid4()),
        "request_content_checksum": canonical_hash(semantic),
    }


def _execute_queries(
    *,
    root: Path,
    base_url: str,
    manifest: dict[str, Any],
    session: dict[str, Any],
    mode: str,
    queries: list[dict[str, str]],
) -> None:
    expected_adapter = OPENALEX_ADAPTER_ID if mode == "NORMAL" else FAKE_ADAPTER_ID
    project = urllib.parse.quote(manifest["experimental_project_identity"], safe="")
    operations_root = root / "memory/search/operations"
    operations_root.mkdir(parents=True, exist_ok=True)
    for item in queries:
        request_payload = _proxy_request(
            manifest=manifest,
            query=item["query"],
            session_id=session["session_id"],
        )
        request_state = operations_root / f"{item['query_id']}.request.json"
        result_state = operations_root / f"{item['query_id']}.result.json"
        _write_atomic(
            request_state,
            {
                "schema_version": "literature-search-local-request/v0.1",
                "query_id": item["query_id"],
                "request": request_payload,
            },
        )
        _, delivery = _http_json(
            url=f"{base_url}/projects/{project}/proxy-operations",
            method="POST",
            payload=request_payload,
            token=session["session_token"],
        )
        if (
            delivery.get("operation_status") != "SUCCEEDED"
            or delivery.get("provider_adapter", {}).get("adapter_id") != expected_adapter
            or not isinstance(delivery.get("provider_data"), dict)
        ):
            raise LocalRoundError(
                "Provider operation did not return a successful response for the selected mode"
            )
        provider_data = delivery["provider_data"]
        if mode == "DEMO" and provider_data.get("source_classification") != "WHOLLY_FICTIONAL_SYNTHETIC_FIXTURE":
            raise LocalRoundError("Demo mode returned data without the fictional classification")
        if mode == "NORMAL" and expected_adapter != delivery["provider_adapter"]["adapter_id"]:
            raise LocalRoundError("Normal mode refuses a fake Provider result")
        _write_atomic(
            result_state,
            {
                "schema_version": "literature-search-normalized-query-result/v0.1",
                "mode": mode,
                "query_id": item["query_id"],
                "issued_query": item["query"],
                "operation_id": delivery.get("operation_id"),
                "request_content_checksum": delivery.get("request_content_checksum"),
                "provider_data_checksum": delivery.get("provider_data_checksum"),
                "response_content_checksum": delivery.get("response_content_checksum"),
                "provider_adapter": delivery.get("provider_adapter"),
                "usage": delivery.get("usage"),
                "provider_data": provider_data,
            },
        )


def _finalize_report(root: Path, context_before_checksum: str) -> Path:
    try:
        namespace = runpy.run_path(str(root / "progress_report.py"))
        result = namespace["finalize"](
            package_root=root,
            draft_path="memory/progress/report-draft.json",
            context_before_checksum=context_before_checksum,
        )
    except Exception as error:
        raise LocalRoundError(f"Progress Report finalization failed: {error}") from error
    return root.joinpath(*PurePosixPath(result["created"]).parts)


def _upload_envelope(
    *,
    root: Path,
    manifest: dict[str, Any],
    report_path: Path,
) -> dict[str, Any]:
    report_bytes = report_path.read_bytes()
    report = _load_object(report_path, "Progress Report")
    source_hint = report_path.relative_to(root).as_posix()
    base = {
        "upload_schema_version": "progress-report-upload/v0.1",
        "project_id": manifest["experimental_project_identity"],
        "package_id": manifest["package_id"],
        "package_checksum": manifest["package_checksum"],
        "report_schema_version": report["schema_version"],
        "report_id": report["report_id"],
        "report_checksum": report["report_checksum"],
        "original_report_media_type": "application/json",
        "original_report_base64": base64.b64encode(report_bytes).decode("ascii"),
        "original_report_checksum": sha256_bytes(report_bytes),
        "original_report_size": len(report_bytes),
        "uploaded_at": _timestamp(),
        "uploader_type": "local-cli",
        "client_version": CLIENT_VERSION,
        "source_path_hint": source_hint,
        "context_snapshot_metadata": None,
        "envelope_checksum": None,
    }
    base["envelope_checksum"] = canonical_hash(base)
    return base


def _upload_and_verify(
    *,
    root: Path,
    base_url: str,
    manifest: dict[str, Any],
    session: dict[str, Any],
    report_path: Path,
) -> dict[str, Any]:
    project = urllib.parse.quote(manifest["experimental_project_identity"], safe="")
    session_id = urllib.parse.quote(session["session_id"], safe="")
    workflow_query = urllib.parse.urlencode(
        {
            "workflow_id": manifest["workflow_id"],
            "workflow_version": manifest["workflow_version"],
            "workflow_checksum": manifest["workflow_checksum"],
        }
    )
    envelope = _upload_envelope(root=root, manifest=manifest, report_path=report_path)
    _, receipt = _http_json(
        url=(
            f"{base_url}/projects/{project}/local-sessions/{session_id}/"
            f"progress-reports?{workflow_query}"
        ),
        method="POST",
        payload=envelope,
        token=session["session_token"],
    )
    identity_query = _identity_query(manifest)
    _, history_response = _http_json_list_as_object(
        url=(
            f"{base_url}/projects/{project}/local-sessions/{session_id}/"
            f"progress-reports?{identity_query}"
        ),
        token=session["session_token"],
    )
    history = history_response["items"]
    _, projection = _http_json(
        url=(
            f"{base_url}/projects/{project}/local-sessions/{session_id}/"
            f"progress?{identity_query}"
        ),
        method="GET",
        token=session["session_token"],
    )
    if (
        receipt.get("validation_status") != "ACCEPTED"
        or not receipt.get("accepted_for_projection")
        or not any(
            item.get("receipt_id") == receipt.get("receipt_id")
            and item.get("report_id") == receipt.get("report_id")
            for item in history
        )
        or projection.get("latest_accepted_report_id") != receipt.get("report_id")
    ):
        raise LocalRoundError("Uploaded Progress Report could not be verified")
    local_receipt = {
        "schema_version": "local-progress-upload-receipt/v0.1",
        "report_id": receipt["report_id"],
        "report_checksum": receipt["report_checksum"],
        "receipt_id": receipt["receipt_id"],
        "receipt_checksum": receipt["receipt_checksum"],
        "validation_status": receipt["validation_status"],
        "chain_state": receipt["chain_state"],
        "accepted_for_projection": receipt["accepted_for_projection"],
        "idempotent_replay": receipt["idempotent_replay"],
        "projection_checksum": projection["projection_checksum"],
        "verified_at": _timestamp(),
    }
    receipt_path = root / "memory/progress/receipts" / f"{receipt['report_id']}.json"
    _write_atomic(receipt_path, local_receipt)
    return local_receipt


def _http_json_list_as_object(
    *,
    url: str,
    token: str,
) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            raw = response.read(MAXIMUM_LOCAL_RESPONSE_BYTES + 1)
            status = response.status
    except urllib.error.HTTPError as error:
        raise LocalRoundError(
            f"Local ReAgent verification failed with HTTP {error.code}"
        ) from None
    except urllib.error.URLError as error:
        raise LocalRoundError("Local ReAgent verification outcome is unknown") from error
    if len(raw) > MAXIMUM_LOCAL_RESPONSE_BYTES:
        raise LocalRoundError("Local ReAgent history exceeded the safe size bound")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LocalRoundError("Local ReAgent history was not valid JSON") from error
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise LocalRoundError("Local ReAgent history did not match the expected array")
    return status, {"items": value}


def _pending_upload(
    *,
    root: Path,
    base_url: str,
    manifest: dict[str, Any],
    report_path: Path,
) -> dict[str, Any]:
    session = _open_session(base_url=base_url, manifest=manifest, mode="UPLOAD_ONLY")
    try:
        return _upload_and_verify(
            root=root,
            base_url=base_url,
            manifest=manifest,
            session=session,
            report_path=report_path,
        )
    finally:
        _close_session(base_url=base_url, manifest=manifest, session=session)


def run_round(*, package_root: str | Path, base_url: str, mode: str) -> dict[str, Any]:
    root = _root(package_root)
    base_url = _base_url(base_url)
    if mode not in {"NORMAL", "DEMO"}:
        raise LocalRoundError("Run mode must be NORMAL or DEMO")
    _validate_package(root)
    manifest = _load_object(root / "package-manifest.json", "Package manifest")
    reports = _reports(root)
    receipts = _receipts(root)
    if len(reports) > 1:
        raise LocalRoundError("V0.1 stops after one Workflow round")
    if reports:
        if receipts:
            return {
                "status": "ROUND_ALREADY_UPLOADED",
                "report_id": _load_object(reports[0], "Progress Report")["report_id"],
            }
        receipt = _pending_upload(
            root=root,
            base_url=base_url,
            manifest=manifest,
            report_path=reports[0],
        )
        return {"status": "PENDING_UPLOAD_COMPLETED", **receipt}
    if receipts:
        raise LocalRoundError("A receipt exists without its local Progress Report")
    if _partial_state(root):
        raise LocalRoundError(
            "Partial local outputs exist without a valid report; preserve them and follow the recovery guide"
        )

    request = _load_object(root / "inputs/research_request.json", "research request")
    topic = request.get("topic")
    if not isinstance(topic, str) or not topic.strip():
        raise LocalRoundError("The immutable Package topic is invalid")
    context_before = _context_snapshot(root)
    started_at = _timestamp()
    session = _open_session(base_url=base_url, manifest=manifest, mode=mode)
    primary_error: BaseException | None = None
    try:
        if session["maximum_query_variants"] != MAXIMUM_QUERY_VARIANTS:
            raise LocalRoundError("Session query budget does not match the fixed policy")
        _invoke_codex(root=root, instruction=_planning_instruction(mode))
        queries = _validate_query_plan(root, topic)
        _execute_queries(
            root=root,
            base_url=base_url,
            manifest=manifest,
            session=session,
            mode=mode,
            queries=queries,
        )
        _invoke_codex(
            root=root,
            instruction=_synthesis_instruction(mode, started_at),
        )
        report_path = _finalize_report(root, context_before)
        _validate_package(root)
        receipt = _upload_and_verify(
            root=root,
            base_url=base_url,
            manifest=manifest,
            session=session,
            report_path=report_path,
        )
        return {
            "status": "ROUND_COMPLETED",
            "mode": mode,
            "report_id": receipt["report_id"],
            "receipt_id": receipt["receipt_id"],
            "queries": len(queries),
        }
    except BaseException as error:
        primary_error = error
        raise
    finally:
        try:
            _close_session(base_url=base_url, manifest=manifest, session=session)
        except LocalRoundError:
            if primary_error is None:
                raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run exactly one ReAgent Literature Search round with Codex."
    )
    parser.add_argument("command", choices=("run",))
    parser.add_argument("package_root", nargs="?", default=".")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("REAGENT_LOCAL_BASE_URL", "http://127.0.0.1:8000"),
    )
    parser.add_argument("--mode", choices=("normal", "demo"), default="normal")
    args = parser.parse_args(argv)
    try:
        result = run_round(
            package_root=args.package_root,
            base_url=args.base_url,
            mode=args.mode.upper(),
        )
    except LocalRoundError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
