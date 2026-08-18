from __future__ import annotations

import json
import runpy

from backend.workflow_packages.forward_downstream_publication import (
    INITIAL_WRITING_CAPSULE_ID, INITIAL_WRITING_CAPSULE_VERSION,
    INITIAL_WRITING_VERSION, MANUSCRIPT_V4, MANUSCRIPT_V5,
    REVIEW_CAPSULE_ID, REVIEW_CAPSULE_VERSION, REVIEW_V3, REVIEW_VERSION,
    WRITING_REVISION_CAPSULE_ID, WRITING_REVISION_CAPSULE_VERSION,
    WRITING_REVISION_VERSION, build_initial_writing_v0_7_package,
    build_review_v0_6_package, build_writing_revision_v0_8_package,
)
from backend.workflow_packages.production_workflows import (
    REAL_REVIEW_CAPSULE_CHECKSUM, REAL_WRITING_CAPSULE_CHECKSUM,
    WRITING_REVISION_CAPSULE_CHECKSUM as HISTORICAL_REVISION_CHECKSUM,
)


def test_forward_capsules_compile_with_exact_v5_roles_and_real_initial_messages(tmp_path) -> None:
    cases = (
        (build_initial_writing_v0_7_package, INITIAL_WRITING_VERSION, INITIAL_WRITING_CAPSULE_VERSION, INITIAL_WRITING_CAPSULE_ID, MANUSCRIPT_V4, "experiment_record", "experiment-record/v5"),
        (build_review_v0_6_package, REVIEW_VERSION, REVIEW_CAPSULE_VERSION, REVIEW_CAPSULE_ID, REVIEW_V3, "manuscript", MANUSCRIPT_V4),
        (build_writing_revision_v0_8_package, WRITING_REVISION_VERSION, WRITING_REVISION_CAPSULE_VERSION, WRITING_REVISION_CAPSULE_ID, MANUSCRIPT_V5, "causal_review", REVIEW_V3),
    )
    for index, (builder, version, capsule_version, capsule_id, output, requirement_key, input_type) in enumerate(cases):
        built = builder(
            project_id="project-" + str(index + 1) * 32,
            project_name="Forward downstream qualification", research_topic="Bounded evidence",
            output_root=tmp_path / str(index), package_id=f"forward-downstream-{index}",
        )
        assert built.validation.valid and built.archive_validation.valid
        root = built.package_root
        manifest = json.loads((root / "package-manifest.json").read_text())
        workflow = json.loads((root / "workflow/workflow.json").read_text())
        descriptor_name = "real-writing.json" if index == 0 else "real-review.json" if index == 1 else "writing-revision.json"
        descriptor = json.loads((root / "workflow" / descriptor_name).read_text())
        assert (manifest["workflow_version"], manifest["package_template_version"]) == (version, capsule_version)
        assert (descriptor["capsule_id"], descriptor["output_artifact_type"]) == (capsule_id, output)
        assert next(item for item in workflow["input_requirements"] if item["requirement_key"] == requirement_key)["artifact_type"] == input_type
        assert "exact materialized experiment-record/v5" in (root / "AGENT.md").read_text()
        assert "codex" in (root / "reagent_local.py").read_text().casefold()
        assert runpy.run_path(str(root / "validate_package.py"))["validate"](root)["valid"] is True


def test_historical_capsule_identities_remain_frozen() -> None:
    assert REAL_WRITING_CAPSULE_CHECKSUM == "sha256:3f94b97702190efed2a4fcd2c0e5f770eaf64020a56ec5f14eaf41412314e8ad"
    assert REAL_REVIEW_CAPSULE_CHECKSUM == "sha256:d8565c18f6d0c5d540d4d0ff63b90d7e7c2cf844e3f3d954c22cca2af5622262"
    assert HISTORICAL_REVISION_CHECKSUM == "sha256:d10eeb323d17944c6ef8b4ed9bfb149751ee96bbf6cac6b6bd41b45629c327c3"

