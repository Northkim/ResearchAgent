# NIGHT-F1A Full Research Flow contract foundation

Date: 2026-08-09

Status: **PASS — OWNER REVIEW READY**

## Boundary

F1A continued from H2 commit `2fc5a01`. It does not add cloud research
execution, a persisted pipeline, a Full Research Flow preset, or production
Writing, Review, or Experiment Workflows. Local Workflow Capsules remain the
authority for research state and Artifact bytes; Cloud keeps only desired
configuration, Progress, and exact Artifact provenance metadata.

ADR 0030 is the accepted decision for this slice. The sole migration head is
now `20260806_0014`.

## Implemented

- Added canonical `core_capability_maturity` to immutable Workflow Definition
  Versions, constrained to `REVIEWED_CORE` or `SCAFFOLD_CORE`. Lifecycle,
  review status, and research-core maturity remain independent.
- Backfilled existing Literature Search and Idea Discovery 0.1.0 Versions as
  reviewed without changing their published Capsule bytes or identities.
- Published reviewed Idea Discovery Definition/Capsule 0.2.0 as a new immutable
  pin. Existing instances stay on their exact old version until the owner
  explicitly retires/adds/syncs a new instance.
- Added an explicit selection completion gate. Exactly one validated candidate
  must retain status `selected`; the finalizer publishes canonical
  `selected-research-idea/v1` bytes under a content-addressed path.
- Reused exact B6/B7 Progress promotion, producer Instance/Capsule identity,
  Artifact ID/checksum binding, idempotent replay, and changed-content
  conflict behavior. Cloud still stores no research Artifact bytes.
- Added strict code-level validators for `manuscript-draft/v1`,
  `review-report/v1`, and `experiment-record/v1`, plus their future exact
  dependency map. They are contracts only and seed no downstream Registry row.
- Enforced that a `SCAFFOLD_CORE` experiment can only publish
  `PLACEHOLDER_NOT_EXECUTED` with null actual results.
- Updated Catalog/API/frontend maturity typing, Workspace compiler/sync/run
  support for the new Idea pin, controlled readiness, and operator head docs.

## Closure qualification

- F1A/B6/B7/H2 focused backend and API tests: **57 passed**.
- Full backend against a fresh isolated PostgreSQL 18.1 cluster:
  **725 passed, 11 skipped**. Seven skips are dedicated migration gates,
  three are pre-existing isolated-environment gates, and one is the explicit
  live-Provider gate; `F1A_NEW_SKIP = 0`.
- Dedicated F1A empty/populated upgrade, downgrade, re-upgrade, retained real
  Project pins, Progress, Artifact, old-version identity, and deterministic
  new-version identity test: **1 passed**.
- Relevant real-PostgreSQL B6/B7/persistence regression: **19 passed**.
- Alembic: sole head/current `20260806_0014`; `alembic check` reported no new
  operations.
- Frontend Vitest: **16 files / 31 tests passed**; TypeScript and ESLint passed.
- Playwright: **5 passed** under the standard local-mode/fake-Provider
  configuration. Next.js optimized production build passed.
- Python compileall and `git diff --check` passed.

No `.env` value, real credential, owner database, live Provider, external
research network call, or Hosted AgentRuntime research execution was used.

## Boundaries and next gate

- The complete flow has schema contracts, not complete downstream research
  capabilities. Writing, Review, and Experiment remain unavailable.
- `SCAFFOLD_CORE` permits future end-to-end plumbing validation but never a
  claim of reviewed scientific execution. Replacement requires new immutable
  Definition/Capsule versions.
- Browser product E2E passed. No fresh external Harness acceptance was required
  because F1A changes immutable contracts and validation, not the external
  Harness boundary.
- Shared multi-user deployment, live Provider use, and public production remain
  closed under ADR 0029 and R3D.

The interruption-recovery audit found no repository damage, partial
implementation, unrelated user change, immutable-version drift, scope leak, or
blocking technical warning. The only corrective change strengthened the
dedicated migration test to retain real old pins, Progress, and Artifact rows
across `0013 -> 0014 -> 0013 -> 0014`; it changed no product semantics.

The next gate is owner acceptance. F1B or any production scaffold Workflow must
be separately authorized and must preserve ADR 0030 maturity and no-auto-latest
rules.
