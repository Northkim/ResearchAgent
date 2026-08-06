"""Compatibility identities derived from accepted Literature Search contracts."""

from __future__ import annotations

from backend.local_projects.contracts import LITERATURE_SEARCH_WORKFLOW
from backend.workflow_packages.contracts import PACKAGE_SCHEMA_VERSION
from backend.workflow_packages.serialization import canonical_hash
from backend.workflow_packages.template import (
    GENERATOR_VERSION,
    TEMPLATE_ID,
    TEMPLATE_VERSION,
    WORKFLOW_ID,
    WORKFLOW_VERSION,
    workflow_document,
)

LITERATURE_SEARCH_STABLE_KEY = LITERATURE_SEARCH_WORKFLOW
LITERATURE_SEARCH_DEFINITION_ID = WORKFLOW_ID
LITERATURE_SEARCH_DEFINITION_VERSION = WORKFLOW_VERSION
LITERATURE_SEARCH_CAPSULE_VERSION = TEMPLATE_VERSION


def literature_search_contract_checksum() -> str:
    return canonical_hash(workflow_document())


def _capsule_compatibility_identity() -> dict[str, str]:
    return {
        "generator_version": GENERATOR_VERSION,
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "package_template_id": TEMPLATE_ID,
        "package_template_version": TEMPLATE_VERSION,
        "workflow_checksum": literature_search_contract_checksum(),
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
    }


def literature_search_capsule_definition_checksum() -> str:
    return canonical_hash(_capsule_compatibility_identity())


LITERATURE_SEARCH_CAPSULE_ID = (
    "capsule-" + literature_search_capsule_definition_checksum()[7:39]
)
