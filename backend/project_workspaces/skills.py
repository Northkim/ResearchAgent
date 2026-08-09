"""Reviewed declarative Skill assets for the teacher-aligned local product."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Mapping

from backend.workflow_packages.serialization import (
    canonical_hash,
    canonical_json,
    sha256_bytes,
)

from .contracts import (
    SkillDefinition,
    SkillLifecycle,
    SkillReviewStatus,
    SkillSourceClass,
    SkillTrustTier,
    SkillVersion,
    WorkflowDefinitionVersionSkillPin,
)

SKILL_SCHEMA_VERSION = "local-skill/v0.1"
SKILL_VERSION = "0.1.0"
RESEARCH_ARTIFACT_PROVENANCE_SKILL_ID = (
    "research-artifact-provenance-local-builtin"
)
SCAFFOLD_CORE_SAFETY_SKILL_ID = "scaffold-core-safety-local-builtin"

_ALLOWED_SUFFIXES = {".md", ".json", ".txt"}
_MAX_FILES = 32
_MAX_TOTAL_BYTES = 1_048_576


@dataclass(frozen=True, slots=True)
class BuiltInSkillAsset:
    skill_id: str
    display_name: str
    description: str
    purpose: str
    instructions: str
    required_capabilities: tuple[str, ...]
    content_source_identity: str
    version: str = SKILL_VERSION

    def content_files(self) -> Mapping[str, bytes]:
        instruction_bytes = self.instructions.encode("utf-8")
        contract = {
            "schema_version": SKILL_SCHEMA_VERSION,
            "name": self.skill_id,
            "version": self.version,
            "trust": "BUILT_IN_REVIEWED_ONLY",
            "required_capabilities": list(self.required_capabilities),
            "files": [{
                "path": "SKILL.md",
                "sha256": sha256_bytes(instruction_bytes),
            }],
        }
        files = {
            "SKILL.md": instruction_bytes,
            "skill.json": (canonical_json(contract) + "\n").encode("utf-8"),
        }
        validate_skill_content_files(files)
        return MappingProxyType(files)

    @property
    def content_checksum(self) -> str:
        files = self.content_files()
        return canonical_hash({
            "instructions": sha256_bytes(files["SKILL.md"]),
            "contract": sha256_bytes(files["skill.json"]),
        })

    @property
    def content_manifest(self) -> dict[str, object]:
        files = self.content_files()
        return {
            "schema_version": SKILL_SCHEMA_VERSION,
            "files": [
                {
                    "path": path,
                    "media_type": (
                        "text/markdown" if path.endswith(".md") else "application/json"
                    ),
                    "sha256": sha256_bytes(content),
                    "byte_size": len(content),
                }
                for path, content in sorted(files.items())
            ],
        }

    def definition(self, now: datetime) -> SkillDefinition:
        return SkillDefinition(
            skill_id=self.skill_id,
            display_name=self.display_name,
            description=self.description,
            lifecycle=SkillLifecycle.AVAILABLE,
            source_class=SkillSourceClass.PLATFORM_BUILT_IN,
            trust_tier=SkillTrustTier.BUILT_IN_REVIEWED,
            created_at=now,
            updated_at=now,
        )

    def skill_version(self, now: datetime) -> SkillVersion:
        return SkillVersion(
            skill_id=self.skill_id,
            skill_version=self.version,
            content_checksum=self.content_checksum,
            manifest_schema_version=SKILL_SCHEMA_VERSION,
            content_manifest=self.content_manifest,
            trust_tier=SkillTrustTier.BUILT_IN_REVIEWED,
            review_status=SkillReviewStatus.REVIEWED,
            content_source_identity=self.content_source_identity,
            published_at=now,
            created_at=now,
            updated_at=now,
        )


RESEARCH_ARTIFACT_PROVENANCE_SKILL = BuiltInSkillAsset(
    skill_id=RESEARCH_ARTIFACT_PROVENANCE_SKILL_ID,
    display_name="Research Artifact Provenance",
    description=(
        "Preserve exact Artifact identity and checksum provenance while using "
        "materialized Workflow inputs."
    ),
    purpose="Use exact materialized inputs and preserve Artifact provenance.",
    instructions="""# Research Artifact Provenance

This is a reviewed, declarative built-in Skill.

1. Use only inputs materialized into this Capsule and declared by its Workflow contract.
2. Treat every file under `inputs/` as read-only.
3. Preserve the exact source Artifact ID and checksum in output provenance.
4. Never select an implicit latest, first, or display-name-matched Artifact.
5. Never read a sibling Capsule's outputs directly.
6. Never invent missing sources or provenance. Stop when required evidence is absent.
7. Write only to the current Capsule's declared mutable roots.
""",
    required_capabilities=(
        "read_materialized_input",
        "preserve_artifact_identity",
        "write_declared_outputs",
    ),
    content_source_identity="reagent-f1d-research-artifact-provenance",
)

SCAFFOLD_CORE_SAFETY_SKILL = BuiltInSkillAsset(
    skill_id=SCAFFOLD_CORE_SAFETY_SKILL_ID,
    display_name="Scaffold Core Safety",
    description=(
        "Keep scaffold outputs visibly provisional and prevent fabricated "
        "scientific evidence or conclusions."
    ),
    purpose="Preserve scaffold markers and prohibit fabricated research claims.",
    instructions="""# Scaffold Core Safety

This is a reviewed, declarative built-in Skill for `SCAFFOLD_CORE` Workflows.

1. Keep the required scaffold marker in every human-facing and canonical output.
2. Do not fabricate citations, DOI values, papers, novelty, metrics, benchmarks, statistics, or results.
3. Do not claim publication-quality writing, substantive peer review, acceptance, or successful reproduction.
4. Experiment output must remain `PLACEHOLDER_NOT_EXECUTED` with `actual_results` null.
5. Missing research capability is represented by explicit placeholder text, never plausible-looking evidence.
6. Preserve `SCAFFOLD_CORE` provenance; this Skill does not upgrade Workflow maturity.
""",
    required_capabilities=(
        "preserve_scaffold_markers",
        "reject_fabricated_research_claims",
        "write_declared_outputs",
    ),
    content_source_identity="reagent-f1d-scaffold-core-safety",
)

PRODUCTION_SKILLS = (
    RESEARCH_ARTIFACT_PROVENANCE_SKILL,
    SCAFFOLD_CORE_SAFETY_SKILL,
)


def validate_skill_content_files(files: Mapping[str, bytes]) -> None:
    if not files or len(files) > _MAX_FILES:
        raise ValueError("Skill content file count is outside the reviewed bound")
    normalized: set[str] = set()
    casefolded: set[str] = set()
    total = 0
    for relative_path, content in files.items():
        if not isinstance(relative_path, str) or not isinstance(content, bytes):
            raise ValueError("Skill content must map relative text paths to bytes")
        path = PurePosixPath(relative_path)
        if (
            path.is_absolute()
            or not path.parts
            or any(part in {"", ".", ".."} for part in path.parts)
            or "\\" in relative_path
            or path.suffix.lower() not in _ALLOWED_SUFFIXES
        ):
            raise ValueError("Skill content contains an unsafe or unsupported path")
        canonical = path.as_posix()
        folded = canonical.casefold()
        if canonical in normalized or folded in casefolded:
            raise ValueError("Skill content contains a duplicate normalized path")
        normalized.add(canonical)
        casefolded.add(folded)
        total += len(content)
        if total > _MAX_TOTAL_BYTES:
            raise ValueError("Skill content exceeds the reviewed size bound")


def production_skill_pins(
    workflow_definition_id: str, workflow_version: str, now: datetime
) -> tuple[WorkflowDefinitionVersionSkillPin, ...]:
    return tuple(
        WorkflowDefinitionVersionSkillPin(
            workflow_definition_id=workflow_definition_id,
            workflow_version=workflow_version,
            pin_order=index,
            skill_id=asset.skill_id,
            skill_version=asset.version,
            skill_checksum=asset.content_checksum,
            purpose=asset.purpose,
            created_at=now,
        )
        for index, asset in enumerate(PRODUCTION_SKILLS)
    )


def production_skill_asset(skill_id: str, version: str) -> BuiltInSkillAsset:
    for asset in PRODUCTION_SKILLS:
        if asset.skill_id == skill_id and asset.version == version:
            return asset
    raise KeyError(f"unknown reviewed built-in Skill {skill_id}@{version}")
