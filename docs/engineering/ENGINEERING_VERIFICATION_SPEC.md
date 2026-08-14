# Engineering verification specification

Status: Owner-ratified specification; capability not implemented

Future capability name: `engineering-verification`

The verifier combines pre-implementation test design, requirement-to-test
traceability, negative and recovery analysis, compatibility qualification,
public-path testing, historical goldens, and architecture-drift review.

## Inputs

- approved engineering change packet;
- requirement ledger entries;
- affected authoritative contracts and owner decisions;
- current and historical version identities;
- test inventory and environment gates;
- known owner-state evidence;
- expected release claim and required evidence level.

## Required qualification labels

Every test/evidence item declares exactly one primary level and any supporting
levels:

- `UNIT`
- `SCHEMA`
- `CONTRACT`
- `SERVICE_INTEGRATION`
- `POSTGRESQL_INTEGRATION`
- `MIGRATION`
- `PUBLIC_API`
- `PUBLIC_WORKSPACE_COMMAND`
- `PTY`
- `FAKE_HARNESS`
- `REAL_CODEX`
- `CONTROLLED_BROWSER`
- `OWNER_MANUAL_UX`
- `LONG_LIVED_WORKSPACE`

These labels are not interchangeable and are mapped to ranked evidence levels
in `docs/testing/QUALIFICATION_LEVELS.md`.

## Non-substitution rules

- Fake finalizer PASS does not imply real Codex completion PASS.
- Real Codex startup PASS does not imply real Codex completion PASS.
- Internal helper PASS does not imply public Workspace-command PASS.
- In-memory service PASS does not imply PostgreSQL transaction/concurrency PASS.
- Synthetic legacy fixture PASS does not imply owner long-lived Workspace PASS.
- Component mock PASS does not imply frontend/backend integration PASS.
- Controlled browser PASS does not imply owner UX acceptance PASS.
- A skipped database or browser suite is `NOT_QUALIFIED`, never PASS.
- A test that duplicates implementation logic cannot be the only evidence for
  an immutable or security-critical contract.

## Verification packet

For every requirement, report:

1. requirement ID and contract source;
2. risk and release-blocking classification;
3. implementation symbols/files;
4. positive, negative, failure, recovery, compatibility, security, and browser
   cases;
5. test IDs and qualification levels;
6. fixture type: independent golden, production-derived, synthetic,
   implementation-coupled, owner-observed, or manual;
7. environment and data-isolation proof;
8. actual result, skipped levels, and highest achieved evidence level;
9. known gaps and overclaim risks;
10. release claim permitted by the evidence.

## Mandatory risk dimensions

- identity/scope spoofing;
- checksum and byte tampering;
- stale/duplicate/out-of-order operations;
- crash windows and response loss;
- concurrent retries and idempotency conflicts;
- cross-Project and cross-Instance access;
- old-version preservation;
- long-lived Workspace evolution;
- frontend loading/error/blocked/empty states;
- credential and private-data leakage;
- path traversal, symlink, hardlink, and special files;
- Cloud/local disagreement;
- partial deployment and restart.

## Public-path qualification

Where a product contract names a public command or route, at least one test
must invoke that exact surface. Direct helper tests remain useful but cannot be
the highest release evidence. Workspace recovery tests must prove zero Harness
launch and no new round. Browser tests must use a verified disposable dataset
and real controlled API unless explicitly classified as component-only.

## Historical compatibility

For every published version affected by a shared compiler/client change:

- rebuild or verify the historical release through an independent checksum
  fixture;
- assert the exact published identity and manifest;
- test current-client handling of preserved historical state;
- distinguish synthetic history from a real long-lived Workspace;
- fail closed when the real state cannot be explained by the fixture.

## Architecture drift review

The verifier records whether the implementation adds:

- a forbidden dependency;
- browser-local filesystem mutation;
- hidden cross-Workflow reads;
- a second source of installed or Progress truth;
- implicit Artifact/Resource selection;
- hosted concrete research execution;
- an undocumented status or state transition;
- new schema/version semantics without migration/version review.

## Completion outcomes

- `PASS_AT_DECLARED_LEVEL`
- `PASS_WITH_UNQUALIFIED_LEVELS`
- `FAIL_CONTRACT`
- `BLOCKED_ENVIRONMENT`
- `BLOCKED_OWNER_EVIDENCE`
- `BLOCKED_SOURCE_CONFLICT`

The report must never compress these outcomes into an unqualified `PASS`.
