"""Path and content policy shared by the compiler and validator."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_PATTERNS = (
    re.compile(b"sk-" + rb"ant-[A-Za-z0-9_-]{8,}"),
    re.compile(b"sk-" + rb"proj-[A-Za-z0-9_-]{8,}"),
    re.compile(b"-----BEGIN " + rb"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"(?:ANTHROPIC|OPENAI)" + rb"_API_KEY\s*=[^\s<]+"),
    re.compile(
        rb"(?:REAGENT_)?OPENALEX_API_KEY\s*=\s*(?!['\"]?<)[^\s]+"
    ),
    re.compile(b"postgres" + rb"(?:ql)?://[^\s/:]+:[^\s/@]+@"),
)
_MACHINE_PATH_PATTERNS = (
    re.compile(b"/" + b"Users/"),
    re.compile(b"/" + b"Volumes/"),
    re.compile(rb"[A-Za-z]:\\\\"),
)
_RAW_PROVIDER_PATTERNS = (
    re.compile(b'"raw_provider_' + rb'response"\s*:'),
    re.compile(b'"raw_response_' + rb'body"\s*:'),
)
_FORBIDDEN_SUFFIXES = (".sqlite", ".sqlite3", ".db", ".pem", ".key")


def require_relative_path(value: str, field_name: str = "path") -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty relative path")
    if "\\" in value or "\x00" in value:
        raise ValueError(f"{field_name} must use safe POSIX separators")
    path = PurePosixPath(value)
    parts = value.split("/")
    if path.is_absolute() or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"{field_name} must be a clean relative path")
    if re.match(r"^[A-Za-z]:", value):
        raise ValueError(f"{field_name} must not be a Windows absolute path")
    if any(part == ".env" or part.startswith(".env.") for part in parts):
        raise ValueError(f"{field_name} must not contain an environment file")
    if value.lower().endswith(_FORBIDDEN_SUFFIXES):
        raise ValueError(f"{field_name} has a forbidden sensitive/runtime suffix")
    return value


def require_sha256(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{field_name} must be sha256:<64 lowercase hex>")
    return value


def reject_sensitive_content(content: bytes, *, path: str) -> None:
    for pattern in (*_SECRET_PATTERNS, *_MACHINE_PATH_PATTERNS, *_RAW_PROVIDER_PATTERNS):
        if pattern.search(content):
            raise ValueError(f"sensitive or machine-specific content rejected in {path}")


def reject_duplicate_paths(paths: tuple[str, ...] | list[str]) -> None:
    normalized = [require_relative_path(path) for path in paths]
    if len(normalized) != len(set(normalized)):
        raise ValueError("duplicate relative paths are not permitted")
