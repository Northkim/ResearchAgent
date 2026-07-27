"""Idempotently publish the frozen demo Workflow through an admin adapter."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.database import create_postgres_engine, create_session_factory
from backend.database.orm import WorkflowDefinitionORM
from backend.database.serialization import (
    workflow_document_hash,
    workflow_from_document,
    workflow_to_document,
)
from backend.domain.enums import WorkflowStepKind
from backend.domain.models import Workflow
from backend.domain.models._utils import utc_now
from backend.skill_system.models import SkillReference
from backend.skill_system.registry import SkillRegistry
from backend.skill_system.runtime import register_fake_skills
from backend.research.skills import register_research_skills
from backend.workflow_engine.models import WorkflowDefinition
from backend.workflow_engine.services import WorkflowValidator

DEMO_WORKFLOW_ID = "guided-literature-review"
DEMO_WORKFLOW_VERSION = "1.0.0"
DEMO_WORKFLOW_HASH = (
    "2e58bc1702f0393230c7f0e76d64f4b35684b709abf0597352498d508f45457f"
)
DEFAULT_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "demo"
    / "workflows"
    / "guided_literature_review.v1.json"
)
RESEARCH_WORKFLOW_ID = "guided-literature-review"
RESEARCH_WORKFLOW_VERSION = "2.0.0"
RESEARCH_WORKFLOW_HASH = (
    "af3dd76540cfb7b08a73a7fbffda76679375a8170f0099611016c57d4c9d856a"
)
RESEARCH_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "demo"
    / "workflows"
    / "guided_literature_review.v2.json"
)


class DemoSeedError(RuntimeError):
    """The frozen demo definition could not be validated or published safely."""


@dataclass(frozen=True, slots=True)
class DemoSeedResult:
    workflow_id: str
    version: str
    canonical_hash: str
    created: bool


def load_demo_workflow(fixture_path: Path = DEFAULT_FIXTURE_PATH) -> Workflow:
    """Load and validate the canonical fixture and every pinned fake Skill."""

    try:
        raw_document = json.loads(fixture_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DemoSeedError(f"Could not read demo fixture {fixture_path}: {error}") from error
    if not isinstance(raw_document, Mapping):
        raise DemoSeedError("Demo workflow fixture must contain one JSON object")

    try:
        workflow = workflow_from_document(raw_document)
        WorkflowValidator().validate(WorkflowDefinition.from_domain(workflow))
    except Exception as error:
        raise DemoSeedError(f"Demo workflow validation failed: {error}") from error

    normalized = workflow_to_document(workflow)
    canonical_hash = workflow_document_hash(normalized)
    if (
        workflow.id != DEMO_WORKFLOW_ID
        or workflow.version != DEMO_WORKFLOW_VERSION
        or canonical_hash != DEMO_WORKFLOW_HASH
    ):
        raise DemoSeedError(
            "Demo workflow identity or canonical hash differs from the frozen contract"
        )

    registry = SkillRegistry()
    register_fake_skills(registry)
    try:
        for step in workflow.steps:
            if step.kind is WorkflowStepKind.SKILL and step.uses is not None:
                registry.resolve(SkillReference.parse(step.uses))
    except Exception as error:
        raise DemoSeedError(f"Demo workflow references an unavailable Skill: {error}") from error
    return workflow


def load_research_workflow(
    fixture_path: Path = RESEARCH_FIXTURE_PATH,
) -> Workflow:
    """Load and fully validate the immutable v2 research catalog definition."""

    try:
        raw_document = json.loads(fixture_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DemoSeedError(
            f"Could not read research fixture {fixture_path}: {error}"
        ) from error
    if not isinstance(raw_document, Mapping):
        raise DemoSeedError("Research workflow fixture must contain one JSON object")
    try:
        workflow = workflow_from_document(raw_document)
        WorkflowValidator().validate(WorkflowDefinition.from_domain(workflow))
    except Exception as error:
        raise DemoSeedError(
            f"Research workflow validation failed: {error}"
        ) from error
    canonical_hash = workflow_document_hash(workflow_to_document(workflow))
    if (
        workflow.id != RESEARCH_WORKFLOW_ID
        or workflow.version != RESEARCH_WORKFLOW_VERSION
        or canonical_hash != RESEARCH_WORKFLOW_HASH
    ):
        raise DemoSeedError(
            "Research workflow identity or canonical hash differs from the frozen contract"
        )
    registry = SkillRegistry()
    register_fake_skills(registry)
    register_research_skills(registry)
    for step in workflow.steps:
        if step.kind is not WorkflowStepKind.SKILL or step.uses is None:
            continue
        try:
            registered = registry.resolve(SkillReference.parse(step.uses))
        except Exception as error:
            raise DemoSeedError(
                f"Research workflow references an unavailable Skill: {error}"
            ) from error
        declared = set(registered.definition.input_schema.fields)
        supplied = set(step.input_mapping)
        required = {
            name
            for name, field_schema in registered.definition.input_schema.fields.items()
            if field_schema.required
        }
        if required - supplied or (
            supplied - declared and not registered.definition.input_schema.allow_extra
        ):
            raise DemoSeedError(
                f"Research workflow step {step.id} does not match the pinned Skill "
                f"input schema; missing={sorted(required - supplied)}, "
                f"unknown={sorted(supplied - declared)}"
            )
    return workflow


def seed_demo_workflow(
    database_url: str,
    *,
    fixture_path: Path = DEFAULT_FIXTURE_PATH,
) -> DemoSeedResult:
    """Insert one immutable catalog definition, or verify the existing row."""

    workflow = load_demo_workflow(fixture_path)
    document = workflow_to_document(workflow)
    canonical_hash = workflow_document_hash(document)
    engine = create_postgres_engine(database_url)
    session_factory = create_session_factory(engine)
    created = False
    try:
        with session_factory() as session, session.begin():
            existing = session.get(
                WorkflowDefinitionORM,
                (workflow.id, workflow.version),
            )
            if existing is None:
                session.add(
                    WorkflowDefinitionORM(
                        workflow_id=workflow.id,
                        version=workflow.version,
                        schema_version=workflow.schema_version,
                        name=workflow.name,
                        definition_json=document,
                        definition_hash=canonical_hash,
                        created_at=utc_now(),
                    )
                )
                created = True
            elif (
                existing.definition_hash != canonical_hash
                or existing.definition_json != document
            ):
                raise DemoSeedError(
                    f"Workflow {workflow.id}@{workflow.version} already exists with "
                    "different immutable content"
                )
    finally:
        engine.dispose()

    return DemoSeedResult(
        workflow_id=workflow.id,
        version=workflow.version,
        canonical_hash=canonical_hash,
        created=created,
    )


def seed_research_workflow(
    database_url: str,
    *,
    fixture_path: Path = RESEARCH_FIXTURE_PATH,
) -> DemoSeedResult:
    """Insert v2 immutably, return unchanged on an identical repeat."""

    workflow = load_research_workflow(fixture_path)
    document = workflow_to_document(workflow)
    canonical_hash = workflow_document_hash(document)
    engine = create_postgres_engine(database_url)
    session_factory = create_session_factory(engine)
    created = False
    try:
        with session_factory() as session, session.begin():
            existing = session.get(
                WorkflowDefinitionORM,
                (workflow.id, workflow.version),
            )
            if existing is None:
                session.add(
                    WorkflowDefinitionORM(
                        workflow_id=workflow.id,
                        version=workflow.version,
                        schema_version=workflow.schema_version,
                        name=workflow.name,
                        definition_json=document,
                        definition_hash=canonical_hash,
                        created_at=utc_now(),
                    )
                )
                created = True
            elif (
                existing.definition_hash != canonical_hash
                or existing.definition_json != document
            ):
                raise DemoSeedError(
                    f"Workflow {workflow.id}@{workflow.version} already exists with "
                    "different immutable content"
                )
    finally:
        engine.dispose()
    return DemoSeedResult(
        workflow_id=workflow.id,
        version=workflow.version,
        canonical_hash=canonical_hash,
        created=created,
    )


def _result_document(result: DemoSeedResult) -> dict[str, Any]:
    return {
        "workflow_id": result.workflow_id,
        "version": result.version,
        "canonical_hash": result.canonical_hash,
        "status": "created" if result.created else "unchanged",
    }


def main() -> int:
    database_url = os.environ.get("REAGENT_DATABASE_URL")
    if not database_url:
        print("REAGENT_DATABASE_URL is required to seed the demo", file=sys.stderr)
        return 2
    try:
        results = (
            seed_demo_workflow(database_url),
            seed_research_workflow(database_url),
        )
    except Exception as error:
        print(f"Demo seed failed: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {"workflows": [_result_document(result) for result in results]},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
