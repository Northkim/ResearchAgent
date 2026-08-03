# R2B External Progress Upload Acceptance

Date: 2026-08-03
Status: **PASS_WITH_WARNINGS**
R2 state: **UPLOAD_ACCEPTED**

## Outcome

R2B proved the committed R2A path end to end with a fresh fictional Workflow
Package outside Git, the committed explicit client, real loopback HTTP, the
real FastAPI application, a dedicated temporary PostgreSQL 18.1 cluster,
separate live/test databases, persistent filesystem artifact storage, chain and
conflict validation, deterministic projection, and actual FastAPI/PostgreSQL
restart.

The exact required baseline was
`6fa19476c6effe58f58ade2cd294a89b77df8807` on clean `main`. No production or
frontend source changed.

## Core evidence

- PostgreSQL databases were named
  `reagent_r2b_acceptance_20260803_50769` and
  `reagent_r2b_tests_20260803_50769`; ProjectDB did not exist in the isolated
  cluster and was not accessed.
- Alembic upgraded to sole head `20260803_0003`; `current` and `check` passed
  before/after restart with no drift.
- The external package ID was
  `literature-search-fictional-r2b-native-20260803-v0.2`, package checksum
  `sha256:0818f17646d2176b1f900b030db8e5d424160261e591c34abc233d67c7bb6a62`.
- Its two native v0.2 reports formed `VALID_CHAIN`; round 2 named round 1 and
  continued the exact context checksum.
- Both originals were byte-identical through HTTP reads. Native projection
  advanced deterministically to round 2 with checksum
  `sha256:8313cd40459aa9ba4fd40df353f4ff5818dbe8285f088e5e15569748cd50b52b`.
- The 29-file package manifest was identical before/after every operation:
  `sha256:e07b471a2bf818e3ee7ba7e4207169becb8f87ab369635f915f932f13af62927`.
- Sequential, concurrent, and post-restart exact replay returned the original
  accepted receipt and created no duplicate effective history or artifact.
- A fictional v0.1 report was accepted as `LEGACY_CHAIN_WITH_WARNINGS`; exact
  bytes were retained and no context transition, Workflow checksum, Harness
  session/version, or pins were fabricated.
- Same-ID bytes, duplicate-round branch, predecessor-checksum conflict, context
  discontinuity, and missing-predecessor evidence were retained as rejected
  immutable evidence and excluded from projection. Unsafe content was rejected
  before retention.
- The missing child stayed rejected after its predecessor arrived; replay
  returned the original rejected receipt. There is no automatic re-evaluation
  or explicit recovery endpoint.
- The complete canonical HTTP snapshot was exactly equal before/after backend
  plus PostgreSQL restart. All nine retained originals verified by receipt.
  The persistent artifact manifest remained nine files with aggregate checksum
  `sha256:a7a4836bc62761fa5ee07e4ec829a051162b2b96f3acd1b1f7c469e344e06f4c`.
- Hosted/runtime tables stayed empty: no execution event, checkpoint,
  memory revision, Workflow run/step run, or provider operation was created.

## Verification

- Progress Report PostgreSQL: 1 passed, 0 skipped;
- PostgreSQL persistence: 13 passed, 0 skipped;
- focused Progress Reports: 38 passed;
- focused boundary: 3 passed;
- Workflow Packages: 43 passed;
- full backend with isolated PostgreSQL: 297 passed, 4 unrelated optional-live
  integration skips;
- compileall: exit 0;
- Alembic: one current head `20260803_0003`, no drift.

The detailed command, receipt, checksum, conflict, row-count, restart, cleanup,
and skip evidence is in
`docs/acceptance/R2B_PROGRESS_UPLOAD_ACCEPTANCE_REPORT.md`.

## Boundary and warnings

No AgentRuntime, ExecutionDispatcher, Workflow run/resume, OpenAlex, provider,
LLM, structured generation, research execution, or local-package mutation
occurred. Concrete task state stayed authoritative in the external folder.

Warnings: optional frontend deferred; Claude Code untested; authentication,
signing, and multi-user authorization undecided; cloud cannot prove no-op
context bytes without snapshots; missing-predecessor evidence is permanently
non-reevaluated under the committed contract.

```text
R2B_ACCEPTANCE = PASS_WITH_WARNINGS
POSTGRESQL_ACCEPTANCE = PASS
EXTERNAL_HTTP_UPLOAD_ACCEPTANCE = PASS
ORIGINAL_BYTE_RETENTION_ACCEPTANCE = PASS
PACKAGE_IMMUTABILITY_ACCEPTANCE = PASS
IDEMPOTENCY_ACCEPTANCE = PASS
CONFLICT_RETENTION_ACCEPTANCE = PASS
RESTART_ACCEPTANCE = PASS
RUNTIME_PROVIDER_BOUNDARY = PASS
R2B_GIT_CLOSURE = PASS
R2_STATE = UPLOAD_ACCEPTED
R2_COMPLETE = PASS_WITH_WARNINGS
```

R3 has not begun. Wait for owner review.
