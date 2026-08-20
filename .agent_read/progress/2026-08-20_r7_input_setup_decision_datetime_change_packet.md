# Engineering change packet

## 1. Identity and status

- Change ID / title: `R7-INPUT-SETUP-DECISION-TIMEZONE-01` — canonical durable input-setup decision instant
- Author / date / baseline: Codex / 2026-08-20 / `main` at `a6d44432c78ba9e2950bc468f283f9f6704cdfe3`
- Packet status: `READY_FOR_IMPLEMENTATION_REVIEW`
- Implementation authorization: `AUTHORIZED` by the Owner prompt dated 2026-08-20

## 2. Intent and baseline

- Objective, Owner intent, and user problem: preserve exact Owner input-setup
  decisions across PostgreSQL `timestamptz` reloads by treating `decided_at` as
  an instant and hashing one UTC representation.
- Current behavior and supported public path: POST input-setup decision returns
  201; PostgreSQL may reload the same instant with another offset; integrity
  validation rebuilds different bytes, hides the current decision, and blocks
  materialization.
- Authoritative sources and published identities: Owner repair authorization;
  ADR 0050; migration `20260820_0035`; current service/contract/repository/API;
  Alembic sole head `20260820_0039`. No Workflow, Capsule, Artifact, or Progress
  publication identity changes.

## 3. Decisions and scope

- Conflicts and authority levels: none. ADR 0050 requires durable exact decisions;
  representation-sensitive validation contradicts that accepted contract.
- Assumptions / unknowns: none affecting implementation. The public API controls
  `decided_at`; clients cannot submit it.
- Owner decisions required or already accepted: exact bounded repair explicitly
  authorized; no further decision required.
- In scope: canonical UTC serialization of this decision timestamp for identity,
  checksum, validation, and response projection; focused unit and PostgreSQL
  reload coverage; resume R7 at the first unmet gate.
- Non-goals: generic datetime refactor, schema migration, record rewrite, removal
  of timestamp integrity, binding/omission changes, frontend behavior, Owner data.
- Deferred findings: all unrelated D1/R7 findings.

## 4. Contract behavior

- Domain semantics: timezone-aware datetimes representing the same instant yield
  identical canonical bytes. Different instants remain different.
- State transitions, authority, idempotency, failure, and retry: accepted exact
  decision -> persisted `timestamptz` -> reload -> same valid/current decision ->
  materialization allowed. Binding or omission changes still make it non-current.
  Naive timestamps remain rejected. Idempotent replay retains the existing ID.
- Artifact impact: none.
- API impact: response schema unchanged; `decided_at` is projected canonically in
  UTC. Existing error and idempotency contracts remain unchanged.
- Persistence impact: none; the `timestamptz` column remains authoritative for the
  instant.

## 5. Product and safety boundaries

- Frontend impact: none.
- Security/privacy impact: no new data or reduced integrity; `decided_at` remains
  integrity-protected.
- Cloud/local boundary impact: none.

## 6. Compatibility and delivery

- Compatibility/versioning classification: unchanged-compatible source repair.
  The supported creation path already normalizes its clock through `_aware()`
  before ID/checksum derivation, so every valid API-created historical row used
  the canonical UTC `Z` payload. UTC-normalized reload validation reproduces those
  existing IDs/checksums without rewriting them. Representation-sensitive
  non-UTC IDs could only be manufactured by bypassing the service and are not a
  supported valid persisted Owner-decision path.
- Migration impact: none.
- Historical immutable versions affected: none.
- Rollback conditions: revert unpublished source/tests if canonical same-instant,
  tamper, idempotency, or PostgreSQL evidence fails. Never rewrite persisted rows.

## 7. Implementation budget

- Expected files/directories: `backend/artifact_references/service.py`;
  `backend/artifact_references/tests/test_service.py`;
  `backend/database/tests/test_workflow_input_setup_decisions_postgresql.py` or
  the existing R7 PostgreSQL product-width regression; governance progress files.
- New/modified/deleted file limits: production <= 1; tests <= 2; governance <= 3;
  migrations = 0.
- Net line or size limits: <= 300 repair lines excluding pre-existing R7 fixture
  alignment.
- Scope-expansion approval rule: stop if schema, generic decision framework,
  frontend, or more than one production module is required.

## 8. Alternatives and verification

- Rejected alternatives: remove `decided_at` from integrity; approximate compare;
  drop timezone; rewrite rows; add migration; accept arbitrary legacy encodings.
- Verification design and required evidence levels: unit same/different-instant and
  tamper checks (E1/E2); exact binding/omission/idempotency regressions (E2/E3);
  HTTP 201 -> PostgreSQL reload -> current decision -> materialization (E4); then
  resume the existing R7 matrix and E5/E6.
- Acceptance criteria: Owner cases A-H; no migration/publication/Owner-data change;
  previously blocked PostgreSQL product-width test passes.
- Stop conditions: another HIGH/CORE defect; compatibility conflict; migration or
  scope expansion; integrity weakening; protected data access.

## 9. Authorization gate

- Packet approval: explicit Owner authorization already supplied.
- Explicit implementation authorization: `AUTHORIZED` for this bounded repair.
- Remaining blockers: none before implementation.
