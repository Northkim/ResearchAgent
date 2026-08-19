from __future__ import annotations

import json
import runpy
from pathlib import Path

from backend.workflow_packages.generic_experiment_v5_publication import (
    GENERIC_EXPERIMENT_V5_CAPSULE_CHECKSUM,
    GENERIC_EXPERIMENT_V5_CONTRACT_CHECKSUM,
)
from backend.workflow_packages.generic_harness_contracts import (
    GENERIC_HARNESS_CLASSIFICATION,
)
from backend.workflow_packages.generic_harness_publication import (
    GENERIC_HARNESS_ARTIFACT_TYPE,
    GENERIC_HARNESS_CAPSULE_CHECKSUM,
    GENERIC_HARNESS_CAPSULE_ID,
    GENERIC_HARNESS_CAPSULE_VERSION,
    GENERIC_HARNESS_CONTRACT_CHECKSUM,
    GENERIC_HARNESS_WORKFLOW_VERSION,
    build_generic_harness_v0_11_package,
    generic_harness_workflow_document,
)


def test_forward_generic_harness_publication_is_truthful_and_buildable(tmp_path: Path):
    package = build_generic_harness_v0_11_package(
        project_id="project-" + "1" * 32,
        project_name="Controlled Generic Harness",
        research_topic="Bounded controlled comparison",
        output_root=tmp_path,
        package_id="generic-harness-controlled-v0.11",
    )
    assert package.validation.valid
    assert package.archive_validation.valid
    root = package.package_root
    manifest = json.loads((root / "package-manifest.json").read_text())
    contract = json.loads((root / "workflow/generic-experiment.json").read_text())
    paths = json.loads((root / "workflow/implementation-paths.json").read_text())
    assert (manifest["workflow_version"], manifest["package_template_version"]) == (
        GENERIC_HARNESS_WORKFLOW_VERSION, GENERIC_HARNESS_CAPSULE_VERSION,
    )
    assert contract["workflow_checksum"] == GENERIC_HARNESS_CONTRACT_CHECKSUM
    assert contract["workflow_capsule"] == {
        "workflow_definition_id": "reproduction-experiment-local-experimental",
        "workflow_version": GENERIC_HARNESS_WORKFLOW_VERSION,
        "workflow_checksum": GENERIC_HARNESS_CONTRACT_CHECKSUM,
        "capsule_id": GENERIC_HARNESS_CAPSULE_ID,
        "capsule_version": GENERIC_HARNESS_CAPSULE_VERSION,
        "capsule_checksum": GENERIC_HARNESS_CAPSULE_CHECKSUM,
    }
    assert contract["output_artifact_type"] == GENERIC_HARNESS_ARTIFACT_TYPE
    assert paths["generic_fallback"]["classification"] == GENERIC_HARNESS_CLASSIFICATION
    assert paths["generic_fallback"]["reviewed_capability"] is False
    assert paths["generic_fallback"]["user_skill_authority"] is False
    assert (root / "runtime_lib/backend/workflow_packages/generic_harness_lifecycle.py").is_file()
    runtime = runpy.run_path(str(root / "validate_package.py"))
    assert runtime["validate"](root, pristine=True)["valid"] is True


def test_historical_v5_publication_identity_remains_frozen():
    assert GENERIC_EXPERIMENT_V5_CONTRACT_CHECKSUM == (
        "sha256:9854cf6b50d7982201a38d55649e18513f2e07d5dc0e6bdba6bd58311b5841e4"
    )
    assert GENERIC_EXPERIMENT_V5_CAPSULE_CHECKSUM == (
        "sha256:cd7ff18e9857b6d20fbe9ba2ccab7ba69a0883b3164627dcd12d07e6eb634ad4"
    )
    document = generic_harness_workflow_document()
    assert document["implementation_paths"]["user_skill_authority"] is False
    assert document["artifact_outputs"][0]["artifact_type"] == "experiment-record/v5"
