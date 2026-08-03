"""Fail-closed validation for untrusted uploaded Progress Report bytes."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import MAX_REPORT_BYTES

_SECRET_PATTERNS = (
    re.compile(r"sk-ant-[A-Za-z0-9_-]{8,}"),
    re.compile(r"sk-proj-[A-Za-z0-9_-]{8,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?:ANTHROPIC|OPENAI)_API_KEY\s*[:=]\s*[^\s<]+", re.IGNORECASE),
    re.compile(r"postgres(?:ql)?://[^\s/:]+:[^\s/@]+@", re.IGNORECASE),
    re.compile(r"authorization\s*[:=]\s*bearer\s+[^\s]+", re.IGNORECASE),
)
_ABSOLUTE_PATHS = (
    re.compile(r"/(?:Users|Volumes|private|tmp|home)/"),
    re.compile(r"[A-Za-z]:\\"),
    re.compile(r"file://", re.IGNORECASE),
)
_HOSTILE_PRESENTATION = re.compile(
    r"<\s*script\b|javascript\s*:|on(?:error|load|click)\s*=",
    re.IGNORECASE,
)
_FORBIDDEN_KEYS = {
    "raw_provider_response",
    "raw_response_body",
    "authorization",
    "api_key",
    "private_key",
    "password",
    "access_token",
    "refresh_token",
    "client_secret",
    "credential",
    "credentials",
    "secret",
}


class UnsafeProgressReportError(ValueError):
    pass


def parse_safe_json_document(content: bytes) -> dict[str, Any]:
    if not isinstance(content, bytes):
        raise UnsafeProgressReportError("uploaded report must be bytes")
    if not content or len(content) > MAX_REPORT_BYTES:
        raise UnsafeProgressReportError("uploaded report is empty or oversized")
    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise UnsafeProgressReportError("uploaded report must use UTF-8") from error
    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            raise UnsafeProgressReportError("uploaded report contains secret-like data")
    for pattern in _ABSOLUTE_PATHS:
        if pattern.search(text):
            raise UnsafeProgressReportError("uploaded report contains an absolute path")
    if _HOSTILE_PRESENTATION.search(text):
        raise UnsafeProgressReportError("uploaded report contains hostile script content")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise UnsafeProgressReportError("uploaded report must be valid JSON") from error
    if not isinstance(value, dict):
        raise UnsafeProgressReportError("uploaded report must be a JSON object")
    _validate_value(value, path="$")
    return value


def _validate_value(value: Any, *, path: str) -> None:
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        raise UnsafeProgressReportError(f"{path} must not contain floating-point values")
    if isinstance(value, str):
        if len(value) > 32_768:
            raise UnsafeProgressReportError(f"{path} contains an oversized string")
        for character in value:
            if character in {"\n", "\t"}:
                continue
            if unicodedata.category(character).startswith("C"):
                raise UnsafeProgressReportError(
                    f"{path} contains a control or invalid Unicode character"
                )
        if value.startswith(("/", "~/")) or re.match(r"^[A-Za-z]:\\", value):
            raise UnsafeProgressReportError(f"{path} contains an absolute path")
        return
    if isinstance(value, Mapping):
        if len(value) > 256:
            raise UnsafeProgressReportError(f"{path} contains too many fields")
        for key, item in value.items():
            if not isinstance(key, str):
                raise UnsafeProgressReportError(f"{path} contains a non-string key")
            lowered = key.lower()
            if lowered in _FORBIDDEN_KEYS or "provider_response" in lowered:
                raise UnsafeProgressReportError(f"{path}.{key} is forbidden")
            _validate_value(item, path=f"{path}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if len(value) > 1_000:
            raise UnsafeProgressReportError(f"{path} contains too many items")
        for index, item in enumerate(value):
            _validate_value(item, path=f"{path}[{index}]")
        return
    raise UnsafeProgressReportError(f"{path} contains unsupported data")
