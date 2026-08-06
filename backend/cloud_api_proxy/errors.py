"""Secret-safe failures for the experimental Proxy boundary."""

from __future__ import annotations


class ProxyError(RuntimeError):
    def __init__(self, code: str, message: str, *, http_status: int) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def invalid(message: str, code: str = "INVALID_REQUEST") -> ProxyError:
    return ProxyError(code, message, http_status=422)


def unauthorized(
    message: str = "Bearer capability token is not valid",
    *,
    code: str = "TOKEN_UNKNOWN",
) -> ProxyError:
    return ProxyError(code, message, http_status=401)


def forbidden(message: str = "Capability token scope does not authorize this request") -> ProxyError:
    return ProxyError("AUTHORIZATION_SCOPE_MISMATCH", message, http_status=403)


def not_found(message: str = "Proxy operation was not found") -> ProxyError:
    return ProxyError("PROXY_OPERATION_NOT_FOUND", message, http_status=404)


def conflict(message: str = "Idempotency key was already used for different content") -> ProxyError:
    return ProxyError("IDEMPOTENCY_CONFLICT", message, http_status=409)


def limited(code: str, message: str) -> ProxyError:
    return ProxyError(code, message, http_status=429)


def unavailable(message: str) -> ProxyError:
    return ProxyError("PROXY_UNAVAILABLE", message, http_status=503)
