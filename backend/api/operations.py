"""Minimal request diagnostics and resource boundaries without payload logging."""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any


REQUEST_ID_HEADER = b"x-request-id"
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_SECURITY_HEADERS = (
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-frame-options", b"DENY"),
    (b"content-security-policy", b"frame-ancestors 'none'; object-src 'none'; base-uri 'self'"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
    (b"cache-control", b"no-store"),
)

logger = logging.getLogger("uvicorn.error")


class RequestBodyTooLarge(RuntimeError):
    pass


def configure_operational_logging() -> None:
    """Attach metadata-only events to Uvicorn's operator-visible handler."""

    logger.disabled = False
    logger.setLevel(logging.INFO)


def log_unhandled_error(*, request_id: str, error_class: str) -> None:
    logger.error(
        json.dumps(
            {
                "event": "unhandled_application_error",
                "request_id": request_id,
                "error_code": "INTERNAL_SERVER_ERROR",
                "error_class": error_class,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


class OperationalBoundaryMiddleware:
    """Bound bodies and add correlation/security metadata to every HTTP response."""

    def __init__(self, app: Any, *, maximum_request_bytes: int) -> None:
        self.app = app
        self.maximum_request_bytes = maximum_request_bytes

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        request_id = _request_id(scope.get("headers", ()))
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.perf_counter()
        received = 0
        status_code = 500
        response_started = False

        for name, value in scope.get("headers", ()):
            if name.lower() == b"content-length":
                try:
                    if int(value) > self.maximum_request_bytes:
                        await _too_large(send, request_id, self.maximum_request_bytes)
                        _log(scope, request_id, 413, started, "REQUEST_BODY_TOO_LARGE")
                        return
                except ValueError:
                    pass

        async def bounded_receive() -> dict:
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body", b""))
                if received > self.maximum_request_bytes:
                    raise RequestBodyTooLarge
            return message

        async def enriched_send(message: dict) -> None:
            nonlocal response_started, status_code
            if message.get("type") == "http.response.start":
                response_started = True
                status_code = int(message.get("status", 500))
                headers = list(message.get("headers", ()))
                lower_names = {name.lower() for name, _ in headers}
                if REQUEST_ID_HEADER not in lower_names:
                    headers.append((REQUEST_ID_HEADER, request_id.encode("ascii")))
                for header in _SECURITY_HEADERS:
                    if header[0] not in lower_names:
                        headers.append(header)
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, bounded_receive, enriched_send)
        except RequestBodyTooLarge:
            await _too_large(send, request_id, self.maximum_request_bytes)
            status_code = 413
        except Exception as error:
            if response_started:
                raise
            status_code = 500
            log_unhandled_error(
                request_id=request_id,
                error_class=type(error).__name__,
            )
            await _internal_server_error(send, request_id)
        finally:
            _log(
                scope,
                request_id,
                status_code,
                started,
                "REQUEST_BODY_TOO_LARGE" if status_code == 413 else None,
            )


def request_id_from_scope(scope: dict) -> str:
    value = scope.get("state", {}).get("request_id")
    return value if isinstance(value, str) else "unavailable"


def operational_response_headers(request_id: str) -> dict[str, str]:
    return {
        "X-Request-ID": request_id,
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": "frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Cache-Control": "no-store",
    }


def _request_id(headers: Any) -> str:
    for name, value in headers:
        if name.lower() == REQUEST_ID_HEADER:
            try:
                candidate = value.decode("ascii")
            except UnicodeDecodeError:
                break
            if _REQUEST_ID.fullmatch(candidate):
                return candidate
            break
    return str(uuid.uuid4())


async def _too_large(send: Any, request_id: str, maximum: int) -> None:
    body = json.dumps(
        {
            "error": {
                "code": "REQUEST_BODY_TOO_LARGE",
                "message": f"Request body exceeds the configured {maximum}-byte limit",
                "request_id": request_id,
            }
        },
        separators=(",", ":"),
    ).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
                (REQUEST_ID_HEADER, request_id.encode("ascii")),
                *_SECURITY_HEADERS,
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


async def _internal_server_error(send: Any, request_id: str) -> None:
    body = json.dumps(
        {
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "The request could not be completed",
                "request_id": request_id,
            }
        },
        separators=(",", ":"),
    ).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 500,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
                (REQUEST_ID_HEADER, request_id.encode("ascii")),
                *_SECURITY_HEADERS,
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


def _log(
    scope: dict,
    request_id: str,
    status_code: int,
    started: float,
    error_code: str | None,
) -> None:
    route = scope.get("route")
    route_path = getattr(route, "path", None) or "unmatched"
    path_parameters = scope.get("path_params", {})
    payload: dict[str, object] = {
        "event": "http_request",
        "request_id": request_id,
        "method": scope.get("method", "unknown"),
        "route": route_path,
        "status": status_code,
        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
    }
    for source, destination in (
        ("project_id", "project_id"),
        ("instance_id", "workflow_instance_id"),
        ("workflow_instance_id", "workflow_instance_id"),
        ("operation_id", "operation_id"),
    ):
        value = path_parameters.get(source)
        if isinstance(value, str) and len(value) <= 255:
            payload[destination] = value
    if error_code is not None:
        payload["error_code"] = error_code
    logger.info(json.dumps(payload, sort_keys=True, separators=(",", ":")))
