from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.workflow_packages.literature_consolidation import (
    LiteratureConsolidationError,
    _load_inputs,
    build_package,
    run,
    validate,
)
from backend.workflow_packages.serialization import canonical_json, sha256_bytes


PROJECT_ID = "project-" + "8" * 32
INSTANCE_ID = "wfi-" + "9" * 32


def _candidate(letter: str, *, doi: str) -> dict:
    return {
        "candidate_id": "candidate-" + letter * 16,
        "provider_id": "https://openalex.org/W" + letter.upper() * 8,
        "openalex_id": "https://openalex.org/W" + letter.upper() * 8,
        "title": f"Paper {letter.upper()}",
        "authors": ["Researcher"],
        "publication_year": 2024,
        "doi": doi,
        "source": "Journal",
        "language": "en",
        "abstract": "Bounded abstract evidence.",
        "source_query_ids": ["query-1"],
        "provenance_checksum": "sha256:" + letter * 64,
        "deduplication_status": "UNIQUE",
    }


def _library(*papers: dict) -> dict:
    return {
        "schema": "selected-paper-library/v1",
        "source_schemas": {
            "candidate_papers": "candidate-papers/v0.2",
            "selected_papers": "selected-papers/v0.2",
        },
        "source_checksums": {
            "candidate_papers_sha256": "sha256:" + "1" * 64,
            "selected_papers_sha256": "sha256:" + "2" * 64,
        },
        "papers": [
            {
                "candidate_id": paper["candidate_id"],
                "paper": paper,
                "selection": {
                    "candidate_id": paper["candidate_id"],
                    "relevance_decision": "INCLUDE",
                    "inclusion_reason": "Owner-selected exact source evidence.",
                    "evidence_availability": "METADATA_AND_ABSTRACT",
                },
            }
            for paper in papers
        ],
    }


def _write_json(path: Path, value: object) -> str:
    content = (canonical_json(value) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return sha256_bytes(content)


def _materialize(package: Path) -> dict[str, str]:
    duplicate = _candidate("a", doi="10.1000/a")
    base = _library(duplicate, _candidate("b", doi="10.1000/b"))
    additional = _library(duplicate, _candidate("c", doi="10.1000/c"))
    base_checksum = _write_json(package / "inputs/base-paper-library.json", base)
    additional_checksum = _write_json(
        package / "inputs/additional-paper-library.json", additional
    )
    records = {
        "base_library": {
            "artifact_id": "artifact-" + "1" * 32,
            "artifact_type": "selected-paper-library/v1",
            "sha256": base_checksum,
        },
        "additional_library": {
            "artifact_id": "artifact-" + "2" * 32,
            "artifact_type": "selected-paper-library/v1",
            "sha256": additional_checksum,
        },
    }
    _write_json(package / "memory/input-provenance.json", {
        "schema_version": "reagent.literature-consolidation-input-provenance/v0.1",
        "workflow_instance_id": INSTANCE_ID,
        "artifacts": records,
    })
    return {key: value["sha256"] for key, value in records.items()}


def _fake_harness(path: Path) -> Path:
    script = path / "fake-consolidation-harness"
    script.write_text("""#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
root=Path.cwd()
def dump(path,value): path.write_text(json.dumps(value,sort_keys=True,separators=(',',':'))+'\\n')
candidates=json.loads((root/'outputs/candidate_papers.json').read_text())
rows=candidates['candidates']
selected=[{'candidate_id':item['candidate_id'],'relevance_decision':'INCLUDE','inclusion_reason':'Owner retained exact complementary evidence.','evidence_availability':'METADATA_AND_ABSTRACT'} for item in rows]
dump(root/'outputs/selected_papers.json',{'schema_version':'selected-papers/v0.2','mode':'NORMAL','selection_status':'SUFFICIENT','selected':selected,'exclusions':[],'exclusion_summary':'No candidates withheld.'})
checksum='sha256:'+hashlib.sha256((root/'outputs/candidate_papers.json').read_bytes()).hexdigest()
dump(root/'memory/owner-decisions.json',{'schema_version':'reagent.owner-decision-snapshot.literature/v0.1','candidate_set_checksum':checksum,'decision_revision':1,'decisions':[{'candidate_id':item['candidate_id'],'disposition':'SELECTED','reason':'Owner retained exact complementary evidence.'} for item in rows]})
(root/'outputs/literature_search_report.md').write_text('# Consolidated Literature\\n\\nTwo exact libraries were combined; no new evidence was retrieved.\\n')
""")
    script.chmod(0o755)
    return script


def test_two_exact_libraries_consolidate_deterministically_and_recursively(
    tmp_path: Path,
) -> None:
    result = build_package(
        project_id=PROJECT_ID,
        project_name="Iterative Literature",
        research_topic="Controlled topic",
        output_root=tmp_path / "capsule",
        package_id="r4-literature-consolidation",
    )
    package = result.package_root
    identities = _materialize(package)
    records, _base, _additional = _load_inputs(package)
    assert records["base_library"]["sha256"] == identities["base_library"]
    assert records["additional_library"]["sha256"] == identities["additional_library"]

    completed = run(
        package,
        INSTANCE_ID,
        codex_executable=str(_fake_harness(tmp_path)),
    )
    assert completed["status"] == "COMPLETED"
    candidates = json.loads((package / "outputs/candidate_papers.json").read_text())
    assert [item["candidate_id"] for item in candidates["candidates"]] == [
        "candidate-" + "a" * 16,
        "candidate-" + "b" * 16,
        "candidate-" + "c" * 16,
    ]
    report = json.loads((package / completed["progress_report"]).read_text())
    artifact = next(
        item for item in report["output_artifacts"]
        if item["artifact_kind"] == "selected-paper-library/v1"
    )
    assert sha256_bytes((package / artifact["relative_path"]).read_bytes()) == artifact["checksum"]
    assert validate(package, pristine=False)["valid"] is True


def test_same_exact_source_twice_is_rejected(tmp_path: Path) -> None:
    result = build_package(
        project_id=PROJECT_ID,
        project_name="Iterative Literature",
        research_topic="Controlled topic",
        output_root=tmp_path / "capsule",
        package_id="r4-literature-consolidation",
    )
    package = result.package_root
    _materialize(package)
    provenance = json.loads((package / "memory/input-provenance.json").read_text())
    provenance["artifacts"]["additional_library"] = provenance["artifacts"]["base_library"]
    _write_json(package / "memory/input-provenance.json", provenance)
    with pytest.raises(LiteratureConsolidationError, match="must be distinct"):
        _load_inputs(package)
