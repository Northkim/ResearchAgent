"""Loopback-only FastAPI routes for explicit fake Proxy operations."""

from __future__ import annotations

import json
import urllib.parse

from fastapi import APIRouter, Query, Request, Response, status
from fastapi.responses import JSONResponse

from .composition import ProxyApplicationContainer
from .contracts import MAX_REQUEST_BYTES, CloudProxyRequestEnvelope
from .errors import ProxyError, invalid, unauthorized

router = APIRouter(prefix="/projects/{project_id}/proxy-operations", tags=["experimental-local-proxy"])


def _container(request: Request) -> ProxyApplicationContainer:
    value = getattr(request.app.state, "proxy_container", None)
    if not isinstance(value, ProxyApplicationContainer):
        raise ProxyError("PROXY_UNAVAILABLE", "Experimental Proxy is unavailable", http_status=503)
    return value


def _bearer(request: Request) -> str:
    value = request.headers.get("authorization")
    if value is None or not value.startswith("Bearer ") or value.count(" ") != 1:
        raise unauthorized()
    token = value.removeprefix("Bearer ")
    if not token:
        raise unauthorized()
    return token


def _require_loopback(request: Request) -> None:
    peer = request.client.host if request.client else None
    if peer != "127.0.0.1":
        raise ProxyError("LOOPBACK_REQUIRED", "Experimental Proxy accepts loopback clients only", http_status=403)
    host = request.headers.get("host", "")
    try:
        parsed = urllib.parse.urlsplit("//" + host)
        host_valid = parsed.hostname == "127.0.0.1" and parsed.username is None and parsed.password is None
    except ValueError:
        host_valid = False
    if not host_valid:
        raise ProxyError("LOOPBACK_HOST_REQUIRED", "Experimental Proxy requires a literal loopback Host", http_status=403)


def _json_object(content: bytes) -> dict:
    try:
        text = content.decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise invalid("request body must be strict UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise invalid("request body must be a JSON object")
    return value


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = item
    return value


def _error(error: ProxyError) -> JSONResponse:
    return JSONResponse(
        status_code=error.http_status,
        content={"error": {"code": error.code, "message": str(error)}},
        headers={"Cache-Control": "no-store"},
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_proxy_operation(project_id: str, request: Request, response: Response):
    try:
        _require_loopback(request)
        bearer = _bearer(request)
        content_type = request.headers.get("content-type", "")
        media_type, *parameters = [item.strip().lower() for item in content_type.split(";")]
        if media_type != "application/json":
            raise ProxyError("UNSUPPORTED_MEDIA_TYPE", "Content-Type must be application/json", http_status=415)
        if any(item.startswith("charset=") and item not in {"charset=utf-8", "charset=utf8"} for item in parameters):
            raise ProxyError("UNSUPPORTED_ENCODING", "Request encoding must be UTF-8", http_status=415)
        body = await request.body()
        if len(body) > MAX_REQUEST_BYTES:
            raise ProxyError("REQUEST_BODY_TOO_LARGE", "Request body exceeds 16 KiB", http_status=413)
        try:
            envelope = CloudProxyRequestEnvelope.from_dict(_json_object(body))
        except ValueError as error:
            raise invalid(str(error)) from error
        result = _container(request).service.submit(
            bearer_token=bearer,
            path_project_id=project_id,
            request=envelope,
        )
        if result["idempotency_result"] == "REPLAYED":
            response.status_code = status.HTTP_200_OK
        response.headers["Cache-Control"] = "no-store"
        return result
    except ProxyError as error:
        return _error(error)


@router.get("")
async def find_proxy_operation(
    project_id: str,
    request: Request,
    package_id: str = Query(...),
    idempotency_key: str = Query(...),
):
    try:
        _require_loopback(request)
        result = _container(request).service.find_operation(
            bearer_token=_bearer(request),
            path_project_id=project_id,
            package_id=package_id,
            idempotency_key=idempotency_key,
        )
        return JSONResponse(result, headers={"Cache-Control": "no-store"})
    except (ProxyError, ValueError) as error:
        failure = error if isinstance(error, ProxyError) else invalid(str(error))
        return _error(failure)


@router.get("/{operation_id}")
async def get_proxy_operation(project_id: str, operation_id: str, request: Request):
    try:
        _require_loopback(request)
        result = _container(request).service.get_operation(
            bearer_token=_bearer(request),
            path_project_id=project_id,
            operation_id=operation_id,
        )
        return JSONResponse(result, headers={"Cache-Control": "no-store"})
    except ProxyError as error:
        return _error(error)
