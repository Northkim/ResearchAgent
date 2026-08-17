# Engineering change packet — GEN-D-R1 controlled-local Run Approval

## 1. Identity and authority

- Change: GEN-D-R1 controlled-local Run Approval handshake.
- Date/baseline: 2026-08-17 / `4abaec7146950db783b17b9cbc2f37b4cf770467`.
- Status: OWNER_AUTHORIZED_FOR_IMPLEMENTATION.
- Authority: the Owner's GEN-D-R1 directive; ADRs 0009, 0026, 0043, 0044;
  ODR-009, ODR-010, ODR-013, and ODR-014.

## 2. Intent and source recovery

The missing product primitive was an authentic authorization bridge from a
Local exact Experiment 0.6 plan to an Owner browser decision and back to Local
one-use consumption. Existing hosted `/approvals` was inspected and rejected:
its rows are foreign-keyed to hosted Workflow/Step Runs and its decision service
dispatches hosted execution. Project Workflow Instance routes, loopback-only
Workspace HTTP transport, SQL/in-memory UoW conventions, exact plan checksums,
and the existing injected bounded-runner boundary are safe reusable seams.

## 3. Contract and persistence

- Contract: `reagent.controlled-local-run-approval/v0.1`; bounded summary and
  consumption receipt have matching v0.1 identities.
- Request binds exact Project, Workflow Instance, objective, execution plan,
  validated package, optional runtime/Capability lineage, summary checksum,
  creation time, and request checksum. The full local plan is not stored.
- States are only REQUESTED, APPROVED, REJECTED, CONSUMED, and SUPERSEDED.
- Migration `20260817_0030` adds a dedicated table outside hosted
  WorkflowRun/WorkflowStepRun persistence. A partial unique index allows one
  active request per Project Workflow Instance; row locking and optimistic
  versioning protect decisions and consumption.

## 4. Transition semantics

- Exact request retransmission returns the existing row.
- A new exact request supersedes an active older plan; old authorization cannot
  approve or consume the new plan.
- Owner approve/reject is exact-checksum-bound and idempotent for the same
  decision key. It never invokes a dispatcher.
- Consumption requires APPROVED plus exact scope/plan/attempt. Same-attempt
  replay returns the same receipt; a second attempt fails `ALREADY_CONSUMED`.
- Local checks the current plan before consumption and again immediately before
  the existing bounded-runner collaborator. Drift never invokes the runner.
  Consumption remains consumed after post-consumption drift or launch failure.

## 5. API, Local, and security boundaries

Project-scoped REST operations report, observe, approve, reject, and consume.
The Workspace HTTP client exposes report/observe/consume, and its handoff helper
accepts only an injected existing-runner collaborator after receipt validation.
Current authorization is the accepted loopback, trusted-machine, single-Owner
profile (ODR-013); this does not claim multi-user authentication.

Summary data is typed, <=16 KiB, and plain bounded text/lists only. Validation
rejects HTML/code, raw logs, credentials, credentialed URLs, private keys, and
common absolute local paths. No source/package bytes, command output, local
launcher path, credentials, or raw plan bytes are stored. Controlled-profile
hosted routes remain hidden, and no hosted execution row is created.

## 6. Compatibility and non-goals

Experiment 0.4/0.7/v2, Experiment 0.5/0.8/v3, Experiment 0.6/0.9/v4, migrations
0027–0029, hosted approvals, Capability contracts, coordinator semantics, Full
Research, Path B, downstream compatibility, terminal UX, and D1 are unchanged.
GEN-D-C1 projection and final browser action wiring remain the next separate
phase.

## 7. Verification record

- Focused contract/API/Local suite: `9 passed`; controlled deployment/hosted
  approval regression included in the broader focused slice.
- PostgreSQL R1: marked disposable database, base→0030, Alembic check,
  0030→0029→0030, create/approve/consume, two-attempt race, same-attempt replay,
  restart/readback, hosted-row non-dispatch, cleanup: `2 passed`.
- Historical publication database slice: `9 passed`; presentation migration
  slice in a separately isolated database: `7 passed`.
- Broad backend partition excluding mandatory-database modules and the separately
  qualified macOS runner: `967 passed, 65 skipped`; three loopback-only tests
  passed separately. Historical macOS no-egress runner: `9 passed`.
- Compileall, `git diff --check`, Alembic sole head 0030, Alembic check, import
  scan, and immutable-source SHA-256 comparisons passed.

## 8. Evidence limits and stop conditions

Verifier independence is LIMITED. No real scientific experiment, Owner data,
D1 state, browser UX, hosted execution, or scientific dependency was used.
One attempted combined PostgreSQL test run was invalid because an established
test fixture truncates publication tables; all affected suites passed when run
in their policy-required separate disposable databases. No product defect was
inferred from that ordering artifact.
