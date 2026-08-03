from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.workflow_packages import BuildResult, build_literature_search_package


@pytest.fixture
def built_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> BuildResult:
    monkeypatch.chdir(tmp_path)
    return build_literature_search_package(
        project_id="experimental-literature-search",
        output_root=Path("build"),
    )


@pytest.fixture
def manifest(built_package: BuildResult) -> dict[str, object]:
    return json.loads((built_package.package_root / "package-manifest.json").read_text())
