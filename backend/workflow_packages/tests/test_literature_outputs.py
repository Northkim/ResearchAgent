from __future__ import annotations

import json

import pytest

from backend.workflow_packages.compiler import BuildResult
from backend.workflow_packages.validator import PackageValidationError, validate_package

from .test_state_and_boundary import _valid_outputs


def test_candidate_identity_and_doi_deduplication_are_required(
    built_package: BuildResult,
) -> None:
    _valid_outputs(built_package, mode="NORMAL")
    path = built_package.package_root / "outputs/candidate_papers.json"
    candidates = json.loads(path.read_text())
    candidates["candidates"][0]["doi"] = "10.5555/FICTIONAL.DUPLICATE"
    candidates["candidates"][1]["doi"] = "10.5555/fictional.duplicate"
    path.write_text(json.dumps(candidates), encoding="utf-8")
    with pytest.raises(PackageValidationError, match="DOI was not deduplicated"):
        validate_package(built_package.package_root)


def test_insufficient_evidence_is_an_honest_valid_completion(
    built_package: BuildResult,
) -> None:
    _valid_outputs(built_package, mode="NORMAL")
    path = built_package.package_root / "outputs/selected_papers.json"
    selected = json.loads(path.read_text())
    candidates = json.loads(
        (built_package.package_root / "outputs/candidate_papers.json").read_text()
    )["candidates"]
    selected["selection_status"] = "INSUFFICIENT"
    selected["selected"] = []
    selected["exclusions"] = [
        {"candidate_id": item["candidate_id"], "reason": "Insufficient topical evidence."}
        for item in candidates
    ]
    selected["exclusion_summary"] = "No candidate had sufficient topical evidence."
    path.write_text(json.dumps(selected), encoding="utf-8")
    assert validate_package(built_package.package_root).valid


def test_report_must_disclose_metadata_abstract_and_full_text_limit(
    built_package: BuildResult,
) -> None:
    _valid_outputs(built_package, mode="NORMAL")
    path = built_package.package_root / "outputs/literature_search_report.md"
    path.write_text(path.read_text().replace("full text", "complete documents"))
    with pytest.raises(PackageValidationError, match="metadata/abstract-only"):
        validate_package(built_package.package_root)


def test_demo_outputs_require_explicit_fictional_label(
    built_package: BuildResult,
) -> None:
    _valid_outputs(built_package, mode="DEMO")
    path = built_package.package_root / "outputs/literature_search_report.md"
    path.write_text(path.read_text().replace("FICTIONAL DEMO EVIDENCE", "Demo"))
    with pytest.raises(PackageValidationError, match="fictional evidence label"):
        validate_package(built_package.package_root)
