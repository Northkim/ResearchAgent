from __future__ import annotations

import json

import pytest

from backend.progress_reports.client import build_envelope, main

from .factories import native_report, report_bytes


def _package(tmp_path):
    report = native_report()
    root = tmp_path / "fictional-package"
    report_path = root / "memory/progress/reports/round-001.json"
    report_path.parent.mkdir(parents=True)
    report_path.write_bytes(report_bytes(report))
    (root / "package-manifest.json").write_text(
        json.dumps(
            {
                "package_id": report.package_id,
                "package_checksum": report.package_checksum,
                "experimental_project_identity": report.project_id,
            }
        ),
        encoding="utf-8",
    )
    return root, report_path, report


def test_client_builds_valid_envelope_without_modifying_package(tmp_path) -> None:
    root, path, report = _package(tmp_path)
    before = path.read_bytes()

    envelope = build_envelope(
        package_root=root,
        report_path=path,
        uploaded_at="2026-08-03T11:00:00Z",
    )

    assert envelope.report_id == report.report_id
    assert envelope.source_path_hint == "memory/progress/reports/round-001.json"
    assert envelope.verify_checksum()
    assert path.read_bytes() == before


def test_client_validate_command_is_offline_and_prints_safe_metadata(
    tmp_path,
    capsys,
) -> None:
    root, path, report = _package(tmp_path)

    exit_code = main(
        [
            "validate",
            "--package-root",
            str(root),
            "--report",
            str(path),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["validation"] == "PASS"
    assert payload["report_id"] == report.report_id
    assert "original_report_base64" not in payload


def test_client_rejects_report_outside_package_and_manifest_mismatch(tmp_path) -> None:
    root, _, report = _package(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_bytes(report_bytes(report))

    with pytest.raises(ValueError, match="inside"):
        build_envelope(package_root=root, report_path=outside)

    (root / "package-manifest.json").write_text(
        json.dumps(
            {
                "package_id": "wrong-fictional-package",
                "package_checksum": report.package_checksum,
                "experimental_project_identity": report.project_id,
            }
        )
    )
    with pytest.raises(ValueError, match="package_id"):
        build_envelope(
            package_root=root,
            report_path="memory/progress/reports/round-001.json",
        )
