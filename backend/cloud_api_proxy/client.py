"""Explicit one-attempt local client for the experimental fake Proxy."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .contracts import CAPABILITY, PROXY_CONTRACT_VERSION, CloudProxyRequestEnvelope, canonical_json, format_timestamp, parse_uuid4
from .package_identity import PackageIdentity, read_validated_package_identity

CLIENT_VERSION = "reagent-fake-proxy-client/0.1.0"


def validate_base_url(base_url: str) -> str:
    parsed = urllib.parse.urlsplit(base_url)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("R3B base URL must be literal loopback HTTP without userinfo, path, query or fragment")
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("R3B base URL has an invalid port") from error
    if port is None or not 1 <= port <= 65535:
        raise ValueError("R3B base URL must include an explicit port")
    return f"http://127.0.0.1:{port}"


def build_request(
    *,
    identity: PackageIdentity,
    query: str,
    max_results: int,
    harness_type: str,
    harness_version: str | None,
    harness_session_id: str,
    idempotency_key: str | None = None,
    client_timestamp: str | None = None,
) -> CloudProxyRequestEnvelope:
    from .contracts import PaperSearchV01Request

    return CloudProxyRequestEnvelope.create(
        proxy_contract_version=PROXY_CONTRACT_VERSION,
        idempotency_key=parse_uuid4(idempotency_key or str(uuid4())),
        project_id=identity.project_id,
        package_id=identity.package_id,
        package_checksum=identity.package_checksum,
        workflow_id=identity.workflow_id,
        workflow_version=identity.workflow_version,
        workflow_checksum=identity.workflow_checksum,
        capability=CAPABILITY,
        parameters=PaperSearchV01Request(query=query, max_results=max_results),
        harness_type=harness_type,
        harness_version=harness_version,
        harness_session_id=harness_session_id,
        client_timestamp=client_timestamp or format_timestamp(datetime.now(UTC)),
    )


def _token() -> str:
    value = os.environ.get("REAGENT_PROXY_TOKEN")
    if not value:
        raise ValueError("REAGENT_PROXY_TOKEN is required in the process environment")
    return value


def _request_json(*, url: str, token: str, method: str, data: bytes | None, timeout: float) -> dict[str, Any]:
    if not 0 < timeout <= 10:
        raise ValueError("timeout must be greater than zero and at most 10 seconds")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Proxy request rejected with HTTP {error.code}") from None
    except urllib.error.URLError:
        raise RuntimeError("Proxy outcome is unknown; use an explicit status command before any retry") from None
    if not isinstance(result, dict):
        raise RuntimeError("Proxy response was not a JSON object")
    return result


def submit(*, base_url: str, token: str, request: CloudProxyRequestEnvelope, timeout: float) -> dict[str, Any]:
    if not 0 < timeout <= 10:
        raise ValueError("timeout must be greater than zero and at most 10 seconds")
    base = validate_base_url(base_url)
    project = urllib.parse.quote(request.project_id, safe="")
    return _request_json(
        url=f"{base}/projects/{project}/proxy-operations",
        token=token,
        method="POST",
        data=canonical_json(request.to_dict()).encode("utf-8"),
        timeout=timeout,
    )


def status_by_operation(*, base_url: str, token: str, identity: PackageIdentity, operation_id: str, timeout: float) -> dict[str, Any]:
    base = validate_base_url(base_url)
    project = urllib.parse.quote(identity.project_id, safe="")
    operation = urllib.parse.quote(operation_id, safe="")
    return _request_json(url=f"{base}/projects/{project}/proxy-operations/{operation}", token=token, method="GET", data=None, timeout=timeout)


def status_by_idempotency(*, base_url: str, token: str, identity: PackageIdentity, idempotency_key: str, timeout: float) -> dict[str, Any]:
    base = validate_base_url(base_url)
    project = urllib.parse.quote(identity.project_id, safe="")
    query = urllib.parse.urlencode({"package_id": identity.package_id, "idempotency_key": parse_uuid4(idempotency_key)})
    return _request_json(url=f"{base}/projects/{project}/proxy-operations?{query}", token=token, method="GET", data=None, timeout=timeout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Explicit local client for the disabled-by-default R3B fake Proxy.")
    parser.add_argument("command", choices=("submit", "status"))
    parser.add_argument("--package-root", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--query")
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--idempotency-key")
    parser.add_argument("--operation-id")
    parser.add_argument("--harness-type", choices=("CODEX", "CLAUDE_CODE"), default="CODEX")
    parser.add_argument("--harness-version")
    parser.add_argument("--harness-session-id", default="explicit-local-proxy-session")
    args = parser.parse_args(argv)
    try:
        token = _token()
        identity = read_validated_package_identity(args.package_root)
        if args.command == "submit":
            if not args.query:
                raise ValueError("submit requires --query")
            request = build_request(
                identity=identity,
                query=args.query,
                max_results=args.max_results,
                harness_type=args.harness_type,
                harness_version=args.harness_version,
                harness_session_id=args.harness_session_id,
                idempotency_key=args.idempotency_key,
            )
            result = submit(base_url=args.base_url, token=token, request=request, timeout=args.timeout)
        elif args.operation_id:
            result = status_by_operation(base_url=args.base_url, token=token, identity=identity, operation_id=args.operation_id, timeout=args.timeout)
        elif args.idempotency_key:
            result = status_by_idempotency(base_url=args.base_url, token=token, identity=identity, idempotency_key=args.idempotency_key, timeout=args.timeout)
        else:
            raise ValueError("status requires --operation-id or --idempotency-key")
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return 0
    except (ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
