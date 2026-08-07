"""Explicit, credential-free local Progress Report validation and upload CLI."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.workflow_packages.serialization import canonical_json

from .contracts import (
    ACCEPTED_REPORT_MEDIA_TYPE,
    MAX_REPORT_BYTES,
    ProgressReportUploadEnvelope,
)
from .normalization import ProgressReportNormalizer

CLIENT_VERSION = "reagent-progress-upload/0.2.0"
DEFAULT_TIMEOUT_SECONDS = 15.0
_SAFE_RECEIPT_FIELDS = {
    "receipt_id",
    "project_id",
    "workflow_instance_id",
    "package_id",
    "report_id",
    "report_checksum",
    "original_report_checksum",
    "validation_status",
    "chain_state",
    "accepted_for_projection",
    "idempotent_replay",
    "uploaded_at",
    "received_at",
    "warning_count",
    "error_count",
    "receipt_checksum",
}


def build_envelope(
    *,
    package_root: str | Path,
    report_path: str | Path,
    uploaded_at: str | None = None,
) -> ProgressReportUploadEnvelope:
    supplied_root = Path(package_root)
    if supplied_root.is_symlink():
        raise ValueError("package root must not be a symbolic link")
    root = supplied_root.resolve()
    manifest_path = root / "package-manifest.json"
    if root.is_symlink() or manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("package root must contain a regular package-manifest.json")
    report = Path(report_path)
    candidate = report if report.is_absolute() else root / report
    if candidate.is_symlink():
        raise ValueError("report must not be a symbolic link")
    candidate = candidate.resolve()
    try:
        source_hint = candidate.relative_to(root).as_posix()
    except ValueError as error:
        raise ValueError("report must be located inside the selected package") from error
    if not candidate.is_file():
        raise ValueError("report must be a regular file and not a symbolic link")
    if not source_hint.startswith("memory/progress/reports/"):
        raise ValueError("report must be under memory/progress/reports/")
    content = candidate.read_bytes()
    if not content or len(content) > MAX_REPORT_BYTES:
        raise ValueError("report is empty or exceeds the upload size bound")
    record = ProgressReportNormalizer().normalize(content)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("package manifest must be valid UTF-8 JSON") from error
    if not isinstance(manifest, dict):
        raise ValueError("package manifest must be a JSON object")
    for field, report_value in (
        ("package_id", record.package_id),
        ("package_checksum", record.package_checksum),
        ("experimental_project_identity", record.project_id),
    ):
        if manifest.get(field) != report_value:
            raise ValueError(f"report does not match manifest {field}")
    timestamp = uploaded_at or datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    return ProgressReportUploadEnvelope.create(
        original_report_bytes=content,
        project_id=record.project_id,
        package_id=record.package_id,
        package_checksum=record.package_checksum,
        report_schema_version=record.source_schema_version,
        report_id=record.report_id,
        report_checksum=record.report_checksum,
        original_report_media_type=ACCEPTED_REPORT_MEDIA_TYPE,
        uploaded_at=timestamp,
        uploader_type="local-cli",
        client_version=CLIENT_VERSION,
        source_path_hint=source_hint,
        context_snapshot_metadata=None,
    )


def upload_envelope(
    *,
    base_url: str,
    envelope: ProgressReportUploadEnvelope,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    if not base_url.startswith(("http://", "https://")):
        raise ValueError("cloud base URL must use http or https")
    if timeout_seconds <= 0 or timeout_seconds > 60:
        raise ValueError("timeout must be greater than zero and at most 60 seconds")
    project = urllib.parse.quote(envelope.project_id, safe="")
    url = base_url.rstrip("/") + f"/projects/{project}/progress-reports"
    request = urllib.request.Request(
        url,
        data=(canonical_json(envelope) + "\n").encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    # Deliberately one attempt: ambiguous transmission is never retried silently.
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"upload rejected with HTTP {error.code}") from error
    except urllib.error.URLError as error:
        raise RuntimeError("upload outcome is unknown; inspect cloud history before retry") from error
    if not isinstance(payload, dict):
        raise RuntimeError("cloud receipt was not a JSON object")
    unsafe_fields = set(payload) - _SAFE_RECEIPT_FIELDS
    missing = {"receipt_id", "validation_status", "report_id"} - set(payload)
    if unsafe_fields or missing:
        raise RuntimeError("cloud receipt did not match the safe receipt contract")
    return payload


def _safe_validation_summary(envelope: ProgressReportUploadEnvelope) -> dict[str, Any]:
    return {
        "validation": "PASS",
        "project_id": envelope.project_id,
        "package_id": envelope.package_id,
        "report_id": envelope.report_id,
        "report_checksum": envelope.report_checksum,
        "original_report_checksum": envelope.original_report_checksum,
        "report_schema_version": envelope.report_schema_version,
        "source_path_hint": envelope.source_path_hint,
        "upload_ready": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate or explicitly upload one local Progress Report."
    )
    parser.add_argument("command", choices=("validate", "upload"))
    parser.add_argument("--package-root", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args(argv)
    try:
        envelope = build_envelope(
            package_root=args.package_root,
            report_path=args.report,
        )
        if args.command == "validate":
            result = _safe_validation_summary(envelope)
        else:
            if not args.base_url:
                parser.error("upload requires --base-url")
            result = upload_envelope(
                base_url=args.base_url,
                envelope=envelope,
                timeout_seconds=args.timeout,
            )
    except (ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
