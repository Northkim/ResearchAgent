# ARCH-D1 Project Workspace and Workflow Capsule Design

Date: 2026-08-06

Status: **PASS_WITH_WARNINGS — DESIGN ONLY, OWNER REVIEW REQUIRED**

## Baseline and boundary

The phase used clean `main` at
`864c0a1c342f0646fe5b186307683d704bd5b37c`. The ignored owner `.env` and all
credentials were excluded. No Provider/network call, database/application
startup, source/runtime schema, test, migration, frontend, Package, API
behavior, Hosted Runtime, LLM, Idea Discovery, deployment, or R3D action
occurred.

## Ratified design

ADR 0022 defines a hybrid architecture: one logical Project Workspace and an
isolated, versioned Workflow Capsule for each Workflow Instance. The domain
supports multiple instances/type, while initial UI permits one active
instance/type. Desired Project Manifest and Installed Workspace Lock are
separate authorities. Pull sync uses explicit base revision, staged validation,
new-destination atomic install, append-only receipt, and idempotent cloud ack.
Nothing overwrites or deletes existing Capsules, Artifacts, reports, or history.

The current Literature Search Package remains runnable and checksum-identical
through V0.x. It maps deterministically to a legacy-compatible Capsule and
Workflow Instance outside historical report bytes. Existing local session and
capability scope versions are preserved; future Workspace scopes are new.

Artifact sharing is typed/checksum-bound reference plus verified copy, with no
symlink or shared writable state. Skills are future-safe but executable only as
built-in reviewed exact pins. External Resources are structured immutable-
revision metadata resolved by local tools and credentials. Cloud stores no
general Artifact bytes and no GitHub/Hugging Face credentials.

## Contract set

The design provides authoritative terminology/identity, additive logical SQL,
legacy compatibility, exact Workspace layout, eight closed JSON Schema drafts
with valid/invalid fictional examples, Capsule/Artifact/Skill/Resource
contracts, versioned API and CLI semantics, a complete pull-sync state machine,
atomic install/recovery rules, graph/list Progress continuity, initial frontend
information architecture, stable errors, a threat model, a cross-layer
consistency matrix, and ten dependency-ordered future phases.

The recommended maximum reliable first slice is Phase 1 only: additive
canonical Project, local Workflow catalog/version, Capsule version, and
Workflow Instance persistence; reviewed Literature Search compatibility seed;
deterministic legacy mapping; repository/migration tests. It excludes APIs,
manifest mutation, local filesystem sync, Progress changes, frontend, and Idea
Discovery.

## Validation

All eight schema drafts parsed as JSON. The repository's installed Ajv 6
validator exercised the draft-07-compatible subset of every draft: eight valid
examples were accepted and eight invalid examples were rejected. A native
draft-2020-12 validator is not installed, so formal draft-2020-12 meta-schema
validation remains a promotion-time check; no dependency was downloaded for a
documentation-only phase. Terminology, sync-state, data-entity, API-route, and
ten-phase-plan scans passed. Credential/private-path scan passed. Hashes for 112
pre-existing acceptance/progress/decision files matched their pre-change
values. The allowed-file audit and `git diff --check` passed. Production test
suites were intentionally not run for this documentation-only phase.

## State

```text
ARCH_D1_DESIGN = PASS_WITH_WARNINGS
ARCHITECTURE = HYBRID_WORKSPACE_AND_CAPSULES
LEGACY_LITERATURE_SEARCH_COMPATIBILITY = PASS
IDENTITY_MODEL_COMPLETE = PASS
DATA_MODEL_COMPLETE = PASS
LOCAL_SCHEMA_DESIGN_COMPLETE = PASS
SYNC_STATE_MACHINE_COMPLETE = PASS
ATOMIC_INSTALLATION_CONTRACT = PASS
ARTIFACT_REFERENCE_CONTRACT = PASS
SKILL_FUTURE_MODEL = PASS
EXTERNAL_RESOURCE_FUTURE_MODEL = PASS
API_DESIGN_COMPLETE = PASS
FRONTEND_INFORMATION_ARCHITECTURE = PASS
DESIGN_CONSISTENCY_AUDIT = PASS
OVERNIGHT_IMPLEMENTATION_READY = READY_FOR_OWNER_REVIEW
IMPLEMENTATION_AUTHORIZED = false
```

Warnings are design-promotion details, not critical contradictions: canonical
JSON implementation/Unicode policy, legacy ID namespace, migration copy/view
strategy, archive signature transport, future round identity envelope,
Workspace bootstrap distribution, and local Resource path mapping remain phase-
specific owner decisions. No implementation is authorized.
